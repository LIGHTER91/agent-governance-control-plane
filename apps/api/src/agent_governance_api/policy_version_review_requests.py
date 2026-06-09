from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from agent_governance_api.audit import append_audit_log
from agent_governance_api.auth import (
    ROLE_AUDITOR,
    ROLE_PLATFORM_ADMIN,
    ROLE_REVIEWER,
    ActorContext,
    get_current_actor,
    has_role,
    require_role,
)
from agent_governance_api.database import get_db_session
from agent_governance_api.metadata_safety import redact_sensitive_text
from agent_governance_api.models import (
    ActorType,
    PolicyVersion,
    PolicyVersionReviewRequest,
    PolicyVersionReviewRequestStatus,
    PolicyVersionStatus,
)
from agent_governance_api.schemas import (
    PolicyVersionReviewDecisionRequest,
    PolicyVersionReviewRequestCreate,
    PolicyVersionReviewRequestRead,
)

policy_versions_router = APIRouter(
    prefix="/policy-versions",
    tags=["policy version review requests"],
)
router = APIRouter(
    prefix="/policy-version-review-requests",
    tags=["policy version review requests"],
)


@policy_versions_router.post(
    "/{policy_version_id}/review-requests",
    response_model=PolicyVersionReviewRequestRead,
    status_code=status.HTTP_201_CREATED,
)
def create_policy_version_review_request(
    policy_version_id: UUID,
    payload: PolicyVersionReviewRequestCreate | None = None,
    session: Session = Depends(get_db_session),
    actor: ActorContext = Depends(get_current_actor),
) -> PolicyVersionReviewRequestRead:
    version = _get_policy_version_or_404(session, policy_version_id)
    _require_policy_version_draft(version)
    _require_no_pending_review_request(session, version.id)

    now = datetime.now(UTC)
    review_request = PolicyVersionReviewRequest(
        policy_version_id=version.id,
        policy_id=version.policy_id,
        status=PolicyVersionReviewRequestStatus.PENDING,
        requested_by_actor_type=actor.actor_type,
        requested_by_actor_id=actor.actor_id,
        request_note=payload.request_note if payload is not None else None,
        created_at=now,
    )
    session.add(review_request)
    session.flush()
    _append_policy_version_review_audit(
        session,
        review_request,
        version=version,
        event_type="policy_version_review_requested",
        summary="PolicyVersion review requested.",
        actor=actor,
        metadata={"request_note": _audit_text(review_request.request_note)},
    )
    session.commit()
    session.refresh(review_request)

    return _review_request_read(review_request, version)


@router.get("", response_model=list[PolicyVersionReviewRequestRead])
def list_policy_version_review_requests(
    request_status: PolicyVersionReviewRequestStatus | None = Query(
        default=PolicyVersionReviewRequestStatus.PENDING,
        alias="status",
    ),
    session: Session = Depends(get_db_session),
    actor: ActorContext = Depends(get_current_actor),
) -> list[PolicyVersionReviewRequestRead]:
    _require_policy_version_review_reader(actor)

    statement = select(PolicyVersionReviewRequest, PolicyVersion).join(
        PolicyVersion,
        PolicyVersion.id == PolicyVersionReviewRequest.policy_version_id,
    )
    if request_status is not None:
        statement = statement.where(PolicyVersionReviewRequest.status == request_status)
    statement = statement.order_by(
        PolicyVersionReviewRequest.created_at.desc(),
        PolicyVersionReviewRequest.id.desc(),
    )

    return [
        _review_request_read(review_request, version)
        for review_request, version in session.execute(statement).all()
    ]


@router.post(
    "/{review_request_id}/approve",
    response_model=PolicyVersionReviewRequestRead,
)
def approve_policy_version_review_request(
    review_request_id: UUID,
    payload: PolicyVersionReviewDecisionRequest | None = None,
    session: Session = Depends(get_db_session),
    actor: ActorContext = Depends(get_current_actor),
) -> PolicyVersionReviewRequestRead:
    return _decide_policy_version_review_request(
        review_request_id,
        PolicyVersionReviewRequestStatus.APPROVED,
        event_type="policy_version_review_approved",
        summary="PolicyVersion review approved.",
        payload=payload,
        session=session,
        actor=actor,
    )


@router.post(
    "/{review_request_id}/reject",
    response_model=PolicyVersionReviewRequestRead,
)
def reject_policy_version_review_request(
    review_request_id: UUID,
    payload: PolicyVersionReviewDecisionRequest | None = None,
    session: Session = Depends(get_db_session),
    actor: ActorContext = Depends(get_current_actor),
) -> PolicyVersionReviewRequestRead:
    return _decide_policy_version_review_request(
        review_request_id,
        PolicyVersionReviewRequestStatus.REJECTED,
        event_type="policy_version_review_rejected",
        summary="PolicyVersion review rejected.",
        payload=payload,
        session=session,
        actor=actor,
    )


def _decide_policy_version_review_request(
    review_request_id: UUID,
    decision_status: PolicyVersionReviewRequestStatus,
    *,
    event_type: str,
    summary: str,
    payload: PolicyVersionReviewDecisionRequest | None,
    session: Session,
    actor: ActorContext,
) -> PolicyVersionReviewRequestRead:
    review_request = _get_policy_version_review_request_or_404(
        session,
        review_request_id,
    )
    _require_pending_review_request(review_request)
    _require_policy_version_review_reviewer(actor)
    _ensure_not_self_review(actor, review_request)
    version = _get_policy_version_or_404(session, review_request.policy_version_id)

    now = datetime.now(UTC)
    review_request.status = decision_status
    review_request.reviewer_actor_type = actor.actor_type
    review_request.reviewer_actor_id = actor.actor_id
    review_request.decision_note = (
        payload.decision_note if payload is not None else None
    )
    review_request.decided_at = now
    _append_policy_version_review_audit(
        session,
        review_request,
        version=version,
        event_type=event_type,
        summary=summary,
        actor=actor,
        metadata={"decision_note": _audit_text(review_request.decision_note)},
    )
    session.commit()
    session.refresh(review_request)

    return _review_request_read(review_request, version)


def _get_policy_version_or_404(
    session: Session,
    policy_version_id: UUID,
) -> PolicyVersion:
    version = session.get(PolicyVersion, policy_version_id)
    if version is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PolicyVersion not found.",
        )
    return version


def _get_policy_version_review_request_or_404(
    session: Session,
    review_request_id: UUID,
) -> PolicyVersionReviewRequest:
    review_request = session.get(PolicyVersionReviewRequest, review_request_id)
    if review_request is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PolicyVersion review request not found.",
        )
    return review_request


def _require_policy_version_draft(version: PolicyVersion) -> None:
    if version.status is PolicyVersionStatus.DRAFT:
        return
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="Only draft PolicyVersions can be submitted for review.",
    )


def _require_no_pending_review_request(
    session: Session,
    policy_version_id: UUID,
) -> None:
    pending_request = session.scalar(
        select(PolicyVersionReviewRequest).where(
            PolicyVersionReviewRequest.policy_version_id == policy_version_id,
            PolicyVersionReviewRequest.status
            == PolicyVersionReviewRequestStatus.PENDING,
        )
    )
    if pending_request is None:
        return
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="PolicyVersion already has a pending review request.",
    )


def _require_pending_review_request(
    review_request: PolicyVersionReviewRequest,
) -> None:
    if review_request.status is PolicyVersionReviewRequestStatus.PENDING:
        return
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="Only pending PolicyVersion review requests can transition.",
    )


def _require_policy_version_review_reader(actor: ActorContext) -> None:
    if actor.actor_type is ActorType.SERVICE and not has_role(
        actor,
        ROLE_PLATFORM_ADMIN,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Service actors cannot list PolicyVersion review requests.",
        )

    require_role(actor, (ROLE_REVIEWER, ROLE_AUDITOR, ROLE_PLATFORM_ADMIN))


def _require_policy_version_review_reviewer(actor: ActorContext) -> None:
    if actor.actor_type is ActorType.SERVICE and not has_role(
        actor,
        ROLE_PLATFORM_ADMIN,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Service actors cannot review PolicyVersions.",
        )

    require_role(actor, (ROLE_REVIEWER, ROLE_PLATFORM_ADMIN))


def _ensure_not_self_review(
    actor: ActorContext,
    review_request: PolicyVersionReviewRequest,
) -> None:
    if has_role(actor, ROLE_PLATFORM_ADMIN):
        return
    if (
        actor.actor_type is review_request.requested_by_actor_type
        and actor.actor_id == review_request.requested_by_actor_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Requester cannot approve or reject their own PolicyVersion review.",
        )


def _append_policy_version_review_audit(
    session: Session,
    review_request: PolicyVersionReviewRequest,
    *,
    version: PolicyVersion,
    event_type: str,
    summary: str,
    actor: ActorContext,
    metadata: dict[str, str | int | bool | None] | None = None,
) -> None:
    append_audit_log(
        session,
        event_type=event_type,
        actor_type=actor.actor_type,
        actor_id=actor.actor_id,
        entity_type="policy_version_review_request",
        entity_id=str(review_request.id),
        summary=summary,
        metadata={
            "policy_id": str(review_request.policy_id),
            "policy_version_id": str(review_request.policy_version_id),
            "policy_version_number": version.version_number,
            "policy_version_status": version.status.value,
            "review_status": review_request.status.value,
            **dict(metadata or {}),
        },
    )


def _review_request_read(
    review_request: PolicyVersionReviewRequest,
    version: PolicyVersion,
) -> PolicyVersionReviewRequestRead:
    policy_name = version.policy_snapshot.get("name")
    return PolicyVersionReviewRequestRead.model_validate(review_request).model_copy(
        update={
            "policy_name": policy_name if isinstance(policy_name, str) else None,
            "policy_version_number": version.version_number,
        }
    )


def _audit_text(value: str | None, *, max_length: int = 512) -> str | None:
    if value is None:
        return None
    redacted = redact_sensitive_text(value)
    if len(redacted) <= max_length:
        return redacted
    return f"{redacted[: max_length - 3]}..."
