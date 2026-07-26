from __future__ import annotations

import json
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
    AuditLog,
    Policy,
    PolicyCheckStep,
    PolicyRule,
    PolicyVersion,
    PolicyVersionReviewRequest,
    PolicyVersionReviewRequestStatus,
    PolicyVersionStatus,
)
from agent_governance_api.schemas import (
    PolicyVersionCheckStepChanges,
    PolicyVersionDiffChangedField,
    PolicyVersionDiffFieldChange,
    PolicyVersionDiffFieldValue,
    PolicyVersionPolicySnapshotChanges,
    PolicyVersionRead,
    PolicyVersionReviewActivationRequest,
    PolicyVersionReviewAssignmentRequest,
    PolicyVersionReviewAuditReference,
    PolicyVersionReviewDecisionRequest,
    PolicyVersionReviewDiffRead,
    PolicyVersionReviewEvidenceRead,
    PolicyVersionReviewRequestCreate,
    PolicyVersionReviewRequestRead,
    PolicyVersionReviewStateRead,
    PolicyVersionRuleConditionChanges,
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


@policy_versions_router.get(
    "/{policy_version_id}/review-state",
    response_model=PolicyVersionReviewStateRead,
)
def get_policy_version_review_state(
    policy_version_id: UUID,
    session: Session = Depends(get_db_session),
    actor: ActorContext = Depends(get_current_actor),
) -> PolicyVersionReviewStateRead:
    version = _get_policy_version_or_404(session, policy_version_id)
    review_request = _latest_review_request_for_policy_version(session, version.id)
    _require_policy_version_review_state_reader(actor, version, review_request)

    return _review_state_read(version, review_request)


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


@router.get(
    "/{review_request_id}/diff",
    response_model=PolicyVersionReviewDiffRead,
)
def get_policy_version_review_request_diff(
    review_request_id: UUID,
    session: Session = Depends(get_db_session),
    actor: ActorContext = Depends(get_current_actor),
) -> PolicyVersionReviewDiffRead:
    _require_policy_version_review_reader(actor)
    review_request = _get_policy_version_review_request_or_404(
        session,
        review_request_id,
    )
    version = _get_policy_version_or_404(session, review_request.policy_version_id)
    _require_review_request_policy_match(review_request, version)

    activation_audit = _activation_audit_for_review_request(
        session,
        review_request,
        version,
    )
    previous_active_version_id = _previous_active_version_id_from_audit(
        activation_audit
    )
    superseded_audit = _superseded_audit_for_activation(
        session,
        review_request,
        version,
        previous_active_version_id,
    )
    baseline = _diff_baseline_for_review_request(
        session,
        version,
        previous_active_version_id=previous_active_version_id,
    )

    policy_snapshot_changes = _policy_snapshot_changes(
        baseline.policy_snapshot,
        version.policy_snapshot,
    )
    rule_condition_changes = _rule_condition_changes(
        baseline.rule_snapshots,
        version.rule_snapshots,
    )
    check_step_changes = _check_step_changes(
        baseline.check_step_snapshots,
        version.check_step_snapshots,
    )
    can_activate = (
        review_request.status is PolicyVersionReviewRequestStatus.APPROVED
        and version.status in {PolicyVersionStatus.DRAFT, PolicyVersionStatus.APPROVED}
    )
    activation_requires_replace = (
        can_activate
        and baseline.baseline_type == "active_version"
        and baseline.policy_version_id is not None
    )

    return PolicyVersionReviewDiffRead(
        review_request_id=review_request.id,
        policy_id=review_request.policy_id,
        policy_version_id=review_request.policy_version_id,
        baseline_policy_version_id=baseline.policy_version_id,
        baseline_type=baseline.baseline_type,
        baseline_summary=baseline.summary,
        reviewed_version_status=version.status,
        review_status=review_request.status,
        can_activate=can_activate,
        activation_requires_replace=activation_requires_replace,
        policy_snapshot_changes=policy_snapshot_changes,
        rule_condition_changes=rule_condition_changes,
        check_step_changes=check_step_changes,
        plain_language_summary=_plain_language_summary(
            baseline,
            policy_snapshot_changes=policy_snapshot_changes,
            rule_condition_changes=rule_condition_changes,
            check_step_changes=check_step_changes,
            review_request=review_request,
            version=version,
        ),
        runtime_effect_summary=_runtime_effect_summary(
            review_request,
            version,
            can_activate=can_activate,
        ),
        evidence=_review_evidence(
            review_request,
            activation_audit=activation_audit,
            superseded_audit=superseded_audit,
            activated_policy_version_id=(
                version.id
                if activation_audit is not None
                or version.status is PolicyVersionStatus.ACTIVE
                else None
            ),
            previous_active_policy_version_id=previous_active_version_id,
        ),
    )


@router.post(
    "/{review_request_id}/assign",
    response_model=PolicyVersionReviewRequestRead,
)
def assign_policy_version_review_request(
    review_request_id: UUID,
    payload: PolicyVersionReviewAssignmentRequest,
    session: Session = Depends(get_db_session),
    actor: ActorContext = Depends(get_current_actor),
) -> PolicyVersionReviewRequestRead:
    review_request = _get_policy_version_review_request_or_404(
        session,
        review_request_id,
    )
    _require_pending_review_request(review_request)
    _require_policy_version_review_reviewer(actor)
    version = _get_policy_version_or_404(session, review_request.policy_version_id)
    _require_review_request_policy_match(review_request, version)

    now = datetime.now(UTC)
    review_request.assigned_reviewer_actor_type = payload.assigned_reviewer_actor_type
    review_request.assigned_reviewer_actor_id = payload.assigned_reviewer_actor_id
    review_request.assigned_reviewer_name = payload.assigned_reviewer_name
    review_request.assigned_at = now
    review_request.assigned_by_actor_type = actor.actor_type
    review_request.assigned_by_actor_id = actor.actor_id
    _append_policy_version_review_audit(
        session,
        review_request,
        version=version,
        event_type="policy_version_review_assigned",
        summary="PolicyVersion review assigned.",
        actor=actor,
        metadata={
            "assigned_reviewer_actor_type": (
                payload.assigned_reviewer_actor_type.value
            ),
            "assigned_reviewer_actor_id": payload.assigned_reviewer_actor_id,
            "assigned_reviewer_name": _audit_text(payload.assigned_reviewer_name),
            "assignment_note": _audit_text(payload.assignment_note),
        },
    )
    session.commit()
    session.refresh(review_request)

    return _review_request_read(review_request, version)


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


@router.post(
    "/{review_request_id}/activate",
    response_model=PolicyVersionRead,
)
def activate_approved_policy_version_review_request(
    review_request_id: UUID,
    payload: PolicyVersionReviewActivationRequest | None = None,
    session: Session = Depends(get_db_session),
    actor: ActorContext = Depends(get_current_actor),
) -> PolicyVersion:
    review_request = _get_policy_version_review_request_or_404(
        session,
        review_request_id,
    )
    _require_approved_review_request(review_request)
    _require_policy_version_review_reviewer(actor)
    version = _get_policy_version_or_404(session, review_request.policy_version_id)
    _require_review_request_policy_match(review_request, version)
    _require_activatable_policy_version(version)

    replace_active = payload.replace_active if payload is not None else False
    active_versions = _active_policy_versions_for_policy(session, version)
    if len(active_versions) > 1:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Policy has multiple active PolicyVersions. Resolve duplicate "
                "active versions before activating another."
            ),
        )

    active_version = active_versions[0] if active_versions else None
    if active_version is not None and not replace_active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Policy already has an active PolicyVersion. Set "
                "replace_active=true to supersede it explicitly."
            ),
        )

    now = datetime.now(UTC)
    superseded_version_id: str | None = None
    if active_version is not None:
        superseded_version_id = str(active_version.id)
        previous_active_status = active_version.status
        active_version.status = PolicyVersionStatus.SUPERSEDED
        active_version.superseded_at = now
        active_version.updated_at = now
        _append_policy_version_lifecycle_audit(
            session,
            active_version,
            event_type="policy_version_superseded",
            summary="PolicyVersion superseded by explicit reviewed activation.",
            actor=actor,
            metadata={
                "status_from": previous_active_status.value,
                "status_to": active_version.status.value,
                "replacement_policy_version_id": str(version.id),
                "review_request_id": str(review_request.id),
            },
        )
        session.flush()

    previous_status = version.status
    version.status = PolicyVersionStatus.ACTIVE
    version.activated_at = now
    version.updated_at = now
    _append_policy_version_lifecycle_audit(
        session,
        version,
        event_type="policy_version_activated",
        summary="PolicyVersion activated from approved review request.",
        actor=actor,
        metadata={
            "status_from": previous_status.value,
            "status_to": version.status.value,
            "review_request_id": str(review_request.id),
            "review_status": review_request.status.value,
            "replace_active": replace_active,
            "superseded_policy_version_id": superseded_version_id,
        },
    )
    session.commit()
    session.refresh(version)
    return version


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
    _ensure_assigned_reviewer_can_decide(actor, review_request)
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


def _latest_review_request_for_policy_version(
    session: Session,
    policy_version_id: UUID,
) -> PolicyVersionReviewRequest | None:
    return session.scalar(
        select(PolicyVersionReviewRequest)
        .where(PolicyVersionReviewRequest.policy_version_id == policy_version_id)
        .order_by(
            PolicyVersionReviewRequest.created_at.desc(),
            PolicyVersionReviewRequest.id.desc(),
        )
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


def _require_approved_review_request(
    review_request: PolicyVersionReviewRequest,
) -> None:
    if review_request.status is PolicyVersionReviewRequestStatus.APPROVED:
        return
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="Only approved PolicyVersion review requests can activate a version.",
    )


def _require_review_request_policy_match(
    review_request: PolicyVersionReviewRequest,
    version: PolicyVersion,
) -> None:
    if review_request.policy_id == version.policy_id:
        return
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="PolicyVersion review request does not match the reviewed Policy.",
    )


def _require_activatable_policy_version(version: PolicyVersion) -> None:
    if version.status is PolicyVersionStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="PolicyVersion is already active.",
        )
    if version.status in {PolicyVersionStatus.DRAFT, PolicyVersionStatus.APPROVED}:
        return
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="Only draft or approved PolicyVersions can be activated from review.",
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


def _require_policy_version_review_state_reader(
    actor: ActorContext,
    version: PolicyVersion,
    review_request: PolicyVersionReviewRequest | None,
) -> None:
    if (
        has_role(actor, ROLE_REVIEWER)
        or has_role(actor, ROLE_AUDITOR)
        or has_role(
            actor,
            ROLE_PLATFORM_ADMIN,
        )
    ):
        return
    if (
        actor.actor_type is version.created_by_actor_type
        and actor.actor_id == version.created_by_actor_id
    ):
        return
    if review_request is not None and (
        actor.actor_type is review_request.requested_by_actor_type
        and actor.actor_id == review_request.requested_by_actor_id
    ):
        return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Review state unavailable for current actor.",
    )


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


def _ensure_assigned_reviewer_can_decide(
    actor: ActorContext,
    review_request: PolicyVersionReviewRequest,
) -> None:
    if review_request.assigned_reviewer_actor_id is None:
        return
    if has_role(actor, ROLE_PLATFORM_ADMIN):
        return
    if (
        actor.actor_type is review_request.assigned_reviewer_actor_type
        and actor.actor_id == review_request.assigned_reviewer_actor_id
    ):
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=(
            "PolicyVersion review is assigned to another reviewer. Only the "
            "assigned reviewer or platform_admin can approve or reject it."
        ),
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


def _append_policy_version_lifecycle_audit(
    session: Session,
    version: PolicyVersion,
    *,
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
        entity_type="policy_version",
        entity_id=str(version.id),
        summary=summary,
        metadata={
            "policy_id": str(version.policy_id),
            "version_number": version.version_number,
            "status": version.status.value,
            **dict(metadata or {}),
        },
    )


def _active_policy_versions_for_policy(
    session: Session,
    version: PolicyVersion,
) -> list[PolicyVersion]:
    statement = (
        select(PolicyVersion)
        .where(
            PolicyVersion.policy_id == version.policy_id,
            PolicyVersion.status == PolicyVersionStatus.ACTIVE,
            PolicyVersion.id != version.id,
        )
        .order_by(
            PolicyVersion.version_number,
            PolicyVersion.activated_at,
            PolicyVersion.id,
        )
    )
    return list(session.scalars(statement).all())


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


def _review_state_read(
    version: PolicyVersion,
    review_request: PolicyVersionReviewRequest | None,
) -> PolicyVersionReviewStateRead:
    if review_request is None:
        can_submit = version.status is PolicyVersionStatus.DRAFT
        return PolicyVersionReviewStateRead(
            policy_version_id=version.id,
            review_status="not_submitted",
            can_submit_review=can_submit,
            message=(
                "Review request not submitted."
                if can_submit
                else "Only draft PolicyVersions can be submitted for review."
            ),
        )

    is_pending = review_request.status is PolicyVersionReviewRequestStatus.PENDING
    return PolicyVersionReviewStateRead(
        policy_version_id=version.id,
        latest_review_request_id=review_request.id,
        review_status=review_request.status.value,
        requested_at=review_request.created_at,
        decided_at=review_request.decided_at,
        reviewer_actor_id=review_request.reviewer_actor_id,
        can_submit_review=version.status is PolicyVersionStatus.DRAFT
        and not is_pending,
        message=_review_state_message(review_request.status),
    )


def _review_state_message(status_: PolicyVersionReviewRequestStatus) -> str:
    if status_ is PolicyVersionReviewRequestStatus.PENDING:
        return "Review request pending. Approval does not activate this version."
    if status_ is PolicyVersionReviewRequestStatus.APPROVED:
        return "Review request approved. Activation remains explicit."
    if status_ is PolicyVersionReviewRequestStatus.REJECTED:
        return "Review request rejected."
    return "Review request canceled."


def _audit_text(value: str | None, *, max_length: int = 512) -> str | None:
    if value is None:
        return None
    redacted = redact_sensitive_text(value)
    if len(redacted) <= max_length:
        return redacted
    return f"{redacted[: max_length - 3]}..."


class _DiffBaseline:
    def __init__(
        self,
        *,
        baseline_type: str,
        policy_snapshot: dict[str, object] | None,
        rule_snapshots: list[dict[str, object]],
        check_step_snapshots: list[dict[str, object]],
        summary: str,
        policy_version_id: UUID | None = None,
    ) -> None:
        self.baseline_type = baseline_type
        self.policy_snapshot = policy_snapshot
        self.rule_snapshots = rule_snapshots
        self.check_step_snapshots = check_step_snapshots
        self.summary = summary
        self.policy_version_id = policy_version_id


def _diff_baseline_for_review_request(
    session: Session,
    version: PolicyVersion,
    *,
    previous_active_version_id: UUID | None,
) -> _DiffBaseline:
    if version.status is PolicyVersionStatus.ACTIVE and previous_active_version_id:
        previous_active_version = session.get(PolicyVersion, previous_active_version_id)
        if previous_active_version is not None:
            return _baseline_from_policy_version(
                previous_active_version,
                summary=(
                    "Baseline active version was the previous active PolicyVersion "
                    "superseded by this activation."
                ),
            )

    active_version = session.scalar(
        select(PolicyVersion)
        .where(
            PolicyVersion.policy_id == version.policy_id,
            PolicyVersion.status == PolicyVersionStatus.ACTIVE,
            PolicyVersion.id != version.id,
        )
        .order_by(
            PolicyVersion.version_number.desc(),
            PolicyVersion.id.desc(),
        )
    )
    if active_version is not None:
        return _baseline_from_policy_version(
            active_version,
            summary="Baseline active version is the current active PolicyVersion.",
        )

    live_fallback = _live_fallback_baseline(session, version.policy_id)
    if live_fallback is not None:
        return live_fallback

    return _DiffBaseline(
        baseline_type="none",
        policy_snapshot=None,
        rule_snapshots=[],
        check_step_snapshots=[],
        summary="No active baseline found.",
    )


def _baseline_from_policy_version(
    version: PolicyVersion,
    *,
    summary: str,
) -> _DiffBaseline:
    return _DiffBaseline(
        baseline_type="active_version",
        policy_snapshot=dict(version.policy_snapshot),
        rule_snapshots=[dict(rule) for rule in version.rule_snapshots],
        check_step_snapshots=[dict(step) for step in version.check_step_snapshots],
        summary=summary,
        policy_version_id=version.id,
    )


def _live_fallback_baseline(
    session: Session,
    policy_id: UUID,
) -> _DiffBaseline | None:
    policy = session.get(Policy, policy_id)
    if policy is None:
        return None

    rules = list(
        session.scalars(
            select(PolicyRule)
            .where(PolicyRule.policy_id == policy_id)
            .order_by(PolicyRule.created_at, PolicyRule.id)
        ).all()
    )
    if not rules:
        return None

    rule_snapshots = [
        {
            "id": str(rule.id),
            "policy_id": str(rule.policy_id),
            "name": rule.name,
            "description": rule.description,
            "condition": rule.condition,
        }
        for rule in rules
    ]
    check_step_snapshots = _live_check_step_snapshots(
        session,
        [rule.id for rule in rules],
    )
    return _DiffBaseline(
        baseline_type="live_fallback",
        policy_snapshot={
            "id": str(policy.id),
            "name": policy.name,
            "description": policy.description,
            "status": policy.status.value,
        },
        rule_snapshots=rule_snapshots,
        check_step_snapshots=check_step_snapshots,
        summary=(
            "No active PolicyVersion baseline found; comparing against live "
            "unversioned Policy/PolicyRule fallback."
        ),
    )


def _live_check_step_snapshots(
    session: Session,
    rule_ids: list[UUID],
) -> list[dict[str, object]]:
    if not rule_ids:
        return []

    steps = list(
        session.scalars(
            select(PolicyCheckStep)
            .where(PolicyCheckStep.policy_rule_id.in_(rule_ids))
            .order_by(PolicyCheckStep.created_at, PolicyCheckStep.id)
        ).all()
    )
    return [
        {
            "id": str(step.id),
            "policy_rule_id": str(step.policy_rule_id),
            "check_tool_id": None
            if step.check_tool_id is None
            else str(step.check_tool_id),
            "check_type": step.check_type.value,
            "target_selector": step.target_selector.value,
            "required": step.required,
            "failure_behavior": step.failure_behavior.value,
            "min_confidence": step.min_confidence,
            "status": step.status.value,
            "evidence_retention": step.evidence_retention.value,
            "metadata": dict(step.metadata_ or {}),
        }
        for step in steps
    ]


def _policy_snapshot_changes(
    baseline: dict[str, object] | None,
    reviewed: dict[str, object],
) -> PolicyVersionPolicySnapshotChanges:
    return PolicyVersionPolicySnapshotChanges(
        name=_field_change(baseline, reviewed, "name"),
        description=_field_change(baseline, reviewed, "description"),
        status=_field_change(baseline, reviewed, "status"),
    )


def _field_change(
    baseline: dict[str, object] | None,
    reviewed: dict[str, object],
    field: str,
) -> PolicyVersionDiffFieldChange:
    baseline_value = baseline.get(field) if baseline is not None else None
    reviewed_value = reviewed.get(field)
    return PolicyVersionDiffFieldChange(
        changed=baseline_value != reviewed_value,
        baseline=baseline_value,
        reviewed=reviewed_value,
    )


def _rule_condition_changes(
    baseline_rules: list[dict[str, object]],
    reviewed_rules: list[dict[str, object]],
) -> PolicyVersionRuleConditionChanges:
    baseline_fields = _condition_fields(baseline_rules)
    reviewed_fields = _condition_fields(reviewed_rules)

    baseline_keys = set(baseline_fields)
    reviewed_keys = set(reviewed_fields)
    common_keys = baseline_keys & reviewed_keys
    return PolicyVersionRuleConditionChanges(
        added_fields=[
            PolicyVersionDiffFieldValue(field=field, value=reviewed_fields[field])
            for field in sorted(reviewed_keys - baseline_keys)
        ],
        removed_fields=[
            PolicyVersionDiffFieldValue(field=field, value=baseline_fields[field])
            for field in sorted(baseline_keys - reviewed_keys)
        ],
        changed_fields=[
            PolicyVersionDiffChangedField(
                field=field,
                baseline=baseline_fields[field],
                reviewed=reviewed_fields[field],
            )
            for field in sorted(common_keys)
            if baseline_fields[field] != reviewed_fields[field]
        ],
        unchanged_fields_count=sum(
            1
            for field in common_keys
            if baseline_fields[field] == reviewed_fields[field]
        ),
    )


def _condition_fields(rule_snapshots: list[dict[str, object]]) -> dict[str, object]:
    fields: dict[str, object] = {}
    use_prefix = len(rule_snapshots) > 1
    for index, rule_snapshot in enumerate(rule_snapshots):
        condition = _condition_object(rule_snapshot.get("condition"))
        prefix = ""
        if use_prefix:
            prefix = f"{_rule_snapshot_label(rule_snapshot, index)}."
        for key, value in condition.items():
            fields[f"{prefix}{key}"] = value
    return fields


def _condition_object(value: object) -> dict[str, object]:
    if not isinstance(value, str):
        return {}
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return {}
    if not isinstance(parsed, dict):
        return {}
    return dict(parsed)


def _rule_snapshot_label(rule_snapshot: dict[str, object], index: int) -> str:
    name = rule_snapshot.get("name")
    if isinstance(name, str) and name.strip():
        return name.strip().replace(" ", "_")
    rule_id = rule_snapshot.get("id")
    if isinstance(rule_id, str) and rule_id.strip():
        return rule_id.strip()
    return f"rule_{index + 1}"


def _check_step_changes(
    baseline_steps: list[dict[str, object]],
    reviewed_steps: list[dict[str, object]],
) -> PolicyVersionCheckStepChanges:
    baseline_map = _check_step_map(baseline_steps)
    reviewed_map = _check_step_map(reviewed_steps)
    baseline_keys = set(baseline_map)
    reviewed_keys = set(reviewed_map)
    common_keys = baseline_keys & reviewed_keys
    changed_fields: list[str] = []
    unchanged_count = 0
    changed_count = 0

    for key in sorted(common_keys):
        baseline_step = _check_step_diff_fields(baseline_map[key])
        reviewed_step = _check_step_diff_fields(reviewed_map[key])
        step_changed = False
        for field in sorted(set(baseline_step) | set(reviewed_step)):
            if baseline_step.get(field) != reviewed_step.get(field):
                changed_fields.append(f"{key}.{field}")
                step_changed = True
        if step_changed:
            changed_count += 1
        else:
            unchanged_count += 1

    return PolicyVersionCheckStepChanges(
        added_count=len(reviewed_keys - baseline_keys),
        removed_count=len(baseline_keys - reviewed_keys),
        changed_count=changed_count,
        unchanged_count=unchanged_count,
        changed_fields=changed_fields,
    )


def _check_step_diff_fields(
    check_step: dict[str, object],
) -> dict[str, object]:
    fields = {
        field: value for field, value in check_step.items() if field != "metadata"
    }
    metadata = check_step.get("metadata")
    if isinstance(metadata, dict):
        for field, value in metadata.items():
            fields[f"metadata.{field}"] = value
    return fields


def _check_step_map(
    check_step_snapshots: list[dict[str, object]],
) -> dict[str, dict[str, object]]:
    mapped: dict[str, dict[str, object]] = {}
    for index, check_step in enumerate(check_step_snapshots):
        check_step_id = check_step.get("id")
        key = check_step_id if isinstance(check_step_id, str) else f"step_{index + 1}"
        mapped[key] = dict(check_step)
    return mapped


def _plain_language_summary(
    baseline: _DiffBaseline,
    *,
    policy_snapshot_changes: PolicyVersionPolicySnapshotChanges,
    rule_condition_changes: PolicyVersionRuleConditionChanges,
    check_step_changes: PolicyVersionCheckStepChanges,
    review_request: PolicyVersionReviewRequest,
    version: PolicyVersion,
) -> list[str]:
    policy_change_count = sum(
        1
        for change in (
            policy_snapshot_changes.name,
            policy_snapshot_changes.description,
            policy_snapshot_changes.status,
        )
        if change.changed
    )
    changed_condition_count = (
        len(rule_condition_changes.added_fields)
        + len(rule_condition_changes.removed_fields)
        + len(rule_condition_changes.changed_fields)
    )
    check_change_count = (
        check_step_changes.added_count
        + check_step_changes.removed_count
        + check_step_changes.changed_count
    )
    summary = [
        baseline.summary,
        (
            f"Policy snapshot changes: {policy_change_count} field(s); "
            f"condition changes: {changed_condition_count} field(s); "
            f"check step changes: {check_change_count} item(s)."
        ),
        (
            f"Review request is {review_request.status.value}; reviewed "
            f"PolicyVersion is {version.status.value}."
        ),
    ]
    if baseline.baseline_type == "none":
        summary.append("No active baseline found.")
    return summary


def _runtime_effect_summary(
    review_request: PolicyVersionReviewRequest,
    version: PolicyVersion,
    *,
    can_activate: bool,
) -> list[str]:
    if version.status is PolicyVersionStatus.ACTIVE:
        return [
            "PolicyVersion is active. Future Runtime Gateway and telemetry "
            "policy evaluation use this snapshot.",
        ]

    if review_request.status in {
        PolicyVersionReviewRequestStatus.PENDING,
        PolicyVersionReviewRequestStatus.APPROVED,
    }:
        summary = ["No runtime effect until activation"]
        if can_activate:
            summary.append(
                "Activation will change future runtime and telemetry policy evaluation"
            )
        return summary

    return ["No runtime effect from this review request in its current state"]


def _review_evidence(
    review_request: PolicyVersionReviewRequest,
    *,
    activation_audit: AuditLog | None,
    superseded_audit: AuditLog | None,
    activated_policy_version_id: UUID | None,
    previous_active_policy_version_id: UUID | None,
) -> PolicyVersionReviewEvidenceRead:
    return PolicyVersionReviewEvidenceRead(
        review_status=review_request.status,
        review_requested_at=review_request.created_at,
        decided_at=review_request.decided_at,
        requested_by_actor_type=review_request.requested_by_actor_type,
        requested_by_actor_id=review_request.requested_by_actor_id,
        reviewer_actor_type=review_request.reviewer_actor_type,
        reviewer_actor_id=review_request.reviewer_actor_id,
        activation_audit_event=_audit_reference(activation_audit),
        superseded_audit_event=_audit_reference(superseded_audit),
        activated_policy_version_id=activated_policy_version_id,
        previous_active_policy_version_id=previous_active_policy_version_id,
    )


def _activation_audit_for_review_request(
    session: Session,
    review_request: PolicyVersionReviewRequest,
    version: PolicyVersion,
) -> AuditLog | None:
    statement = (
        select(AuditLog)
        .where(
            AuditLog.event_type == "policy_version_activated",
            AuditLog.entity_type == "policy_version",
            AuditLog.entity_id == str(version.id),
        )
        .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
    )
    for audit_log in session.scalars(statement).all():
        if audit_log.metadata_.get("review_request_id") == str(review_request.id):
            return audit_log
    return None


def _previous_active_version_id_from_audit(audit_log: AuditLog | None) -> UUID | None:
    if audit_log is None:
        return None
    value = audit_log.metadata_.get("superseded_policy_version_id")
    if not isinstance(value, str) or not value:
        return None
    try:
        return UUID(value)
    except ValueError:
        return None


def _superseded_audit_for_activation(
    session: Session,
    review_request: PolicyVersionReviewRequest,
    version: PolicyVersion,
    previous_active_version_id: UUID | None,
) -> AuditLog | None:
    if previous_active_version_id is None:
        return None
    statement = (
        select(AuditLog)
        .where(
            AuditLog.event_type == "policy_version_superseded",
            AuditLog.entity_type == "policy_version",
            AuditLog.entity_id == str(previous_active_version_id),
        )
        .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
    )
    for audit_log in session.scalars(statement).all():
        metadata = audit_log.metadata_
        if metadata.get("replacement_policy_version_id") == str(
            version.id
        ) and metadata.get("review_request_id") == str(review_request.id):
            return audit_log
    return None


def _audit_reference(
    audit_log: AuditLog | None,
) -> PolicyVersionReviewAuditReference | None:
    if audit_log is None:
        return None
    return PolicyVersionReviewAuditReference(
        id=audit_log.id,
        event_type=audit_log.event_type,
        entity_type=audit_log.entity_type,
        entity_id=audit_log.entity_id,
        summary=audit_log.summary,
        created_at=audit_log.created_at,
        metadata=dict(audit_log.metadata_ or {}),
    )
