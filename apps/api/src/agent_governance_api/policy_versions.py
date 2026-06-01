from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from agent_governance_api.audit import append_audit_log
from agent_governance_api.auth import ActorContext, get_current_actor
from agent_governance_api.database import get_db_session
from agent_governance_api.metadata_safety import (
    filter_safe_metadata,
    redact_sensitive_text,
)
from agent_governance_api.models import (
    Policy,
    PolicyCheckStep,
    PolicyRule,
    PolicyVersion,
    PolicyVersionStatus,
)
from agent_governance_api.schemas import (
    PolicyVersionCreate,
    PolicyVersionRead,
    PolicyVersionReviewRequest,
)

policies_router = APIRouter(prefix="/policies", tags=["policy versions"])
router = APIRouter(prefix="/policy-versions", tags=["policy versions"])

ROLLBACK_COPY_SOURCE_STATUSES = {
    PolicyVersionStatus.APPROVED,
    PolicyVersionStatus.REJECTED,
    PolicyVersionStatus.ACTIVE,
    PolicyVersionStatus.SUPERSEDED,
}
ARCHIVABLE_STATUSES = {
    PolicyVersionStatus.DRAFT,
    PolicyVersionStatus.APPROVED,
    PolicyVersionStatus.REJECTED,
    PolicyVersionStatus.ACTIVE,
    PolicyVersionStatus.SUPERSEDED,
}


@policies_router.post(
    "/{policy_id}/versions",
    response_model=PolicyVersionRead,
    status_code=status.HTTP_201_CREATED,
)
def create_policy_version(
    policy_id: UUID,
    payload: PolicyVersionCreate,
    session: Session = Depends(get_db_session),
    actor: ActorContext = Depends(get_current_actor),
) -> PolicyVersion:
    policy = _get_policy_or_404(session, policy_id)
    now = datetime.now(UTC)
    policy_snapshot, rule_snapshots, check_step_snapshots = _snapshot_policy(
        session,
        policy,
    )
    version = PolicyVersion(
        id=uuid4(),
        policy_id=policy.id,
        version_number=_next_version_number(session, policy.id),
        status=PolicyVersionStatus.DRAFT,
        change_summary=payload.change_summary,
        policy_snapshot=policy_snapshot,
        rule_snapshots=rule_snapshots,
        check_step_snapshots=check_step_snapshots,
        created_by_actor_type=actor.actor_type,
        created_by_actor_id=actor.actor_id,
        created_at=now,
        updated_at=now,
    )
    session.add(version)
    session.flush()
    _append_policy_version_audit(
        session,
        version,
        event_type="policy_version_created",
        actor=actor,
        summary="PolicyVersion created.",
        metadata={"change_summary": _audit_text(payload.change_summary)},
    )
    session.commit()
    session.refresh(version)
    return version


@policies_router.get(
    "/{policy_id}/versions",
    response_model=list[PolicyVersionRead],
)
def list_policy_versions_for_policy(
    policy_id: UUID,
    session: Session = Depends(get_db_session),
) -> list[PolicyVersion]:
    _get_policy_or_404(session, policy_id)
    statement = (
        select(PolicyVersion)
        .where(PolicyVersion.policy_id == policy_id)
        .order_by(PolicyVersion.version_number, PolicyVersion.id)
    )
    return list(session.scalars(statement).all())


@router.get(
    "/{version_id}",
    response_model=PolicyVersionRead,
)
def get_policy_version(
    version_id: UUID,
    session: Session = Depends(get_db_session),
) -> PolicyVersion:
    return _get_policy_version_or_404(session, version_id)


@router.post(
    "/{version_id}/submit-review",
    response_model=PolicyVersionRead,
)
def submit_policy_version_for_review(
    version_id: UUID,
    session: Session = Depends(get_db_session),
    actor: ActorContext = Depends(get_current_actor),
) -> PolicyVersion:
    version = _get_policy_version_or_404(session, version_id)
    _require_status(
        version,
        {PolicyVersionStatus.DRAFT},
        "Only draft policy versions can be submitted for review.",
    )

    now = datetime.now(UTC)
    previous_status = version.status
    version.status = PolicyVersionStatus.UNDER_REVIEW
    version.review_requested_by_actor_type = actor.actor_type
    version.review_requested_by_actor_id = actor.actor_id
    version.submitted_at = now
    version.updated_at = now
    _append_policy_version_audit(
        session,
        version,
        event_type="policy_version_submitted_for_review",
        actor=actor,
        summary="PolicyVersion submitted for review.",
        metadata=_transition_metadata(previous_status, version.status),
    )
    session.commit()
    session.refresh(version)
    return version


@router.post(
    "/{version_id}/approve",
    response_model=PolicyVersionRead,
)
def approve_policy_version(
    version_id: UUID,
    payload: PolicyVersionReviewRequest | None = None,
    session: Session = Depends(get_db_session),
    actor: ActorContext = Depends(get_current_actor),
) -> PolicyVersion:
    version = _get_policy_version_or_404(session, version_id)
    _require_status(
        version,
        {PolicyVersionStatus.UNDER_REVIEW},
        "Only policy versions under review can be approved.",
    )

    now = datetime.now(UTC)
    previous_status = version.status
    version.status = PolicyVersionStatus.APPROVED
    version.reviewed_by_actor_type = actor.actor_type
    version.reviewed_by_actor_id = actor.actor_id
    version.review_note = payload.review_note if payload is not None else None
    version.approved_at = now
    version.updated_at = now
    _append_policy_version_audit(
        session,
        version,
        event_type="policy_version_approved",
        actor=actor,
        summary="PolicyVersion approved.",
        metadata=_transition_metadata(previous_status, version.status),
    )
    session.commit()
    session.refresh(version)
    return version


@router.post(
    "/{version_id}/reject",
    response_model=PolicyVersionRead,
)
def reject_policy_version(
    version_id: UUID,
    payload: PolicyVersionReviewRequest | None = None,
    session: Session = Depends(get_db_session),
    actor: ActorContext = Depends(get_current_actor),
) -> PolicyVersion:
    version = _get_policy_version_or_404(session, version_id)
    _require_status(
        version,
        {PolicyVersionStatus.UNDER_REVIEW},
        "Only policy versions under review can be rejected.",
    )

    now = datetime.now(UTC)
    previous_status = version.status
    version.status = PolicyVersionStatus.REJECTED
    version.reviewed_by_actor_type = actor.actor_type
    version.reviewed_by_actor_id = actor.actor_id
    version.review_note = payload.review_note if payload is not None else None
    version.rejected_at = now
    version.updated_at = now
    _append_policy_version_audit(
        session,
        version,
        event_type="policy_version_rejected",
        actor=actor,
        summary="PolicyVersion rejected.",
        metadata=_transition_metadata(previous_status, version.status),
    )
    session.commit()
    session.refresh(version)
    return version


@router.post(
    "/{version_id}/activate",
    response_model=PolicyVersionRead,
)
def activate_policy_version(
    version_id: UUID,
    session: Session = Depends(get_db_session),
    actor: ActorContext = Depends(get_current_actor),
) -> PolicyVersion:
    version = _get_policy_version_or_404(session, version_id)
    _require_status(
        version,
        {PolicyVersionStatus.APPROVED},
        "Only approved policy versions can be activated.",
    )

    now = datetime.now(UTC)
    active_versions = list(
        session.scalars(
            select(PolicyVersion)
            .where(
                PolicyVersion.policy_id == version.policy_id,
                PolicyVersion.status == PolicyVersionStatus.ACTIVE,
                PolicyVersion.id != version.id,
            )
            .order_by(PolicyVersion.version_number, PolicyVersion.id)
        ).all()
    )
    for active_version in active_versions:
        previous_status = active_version.status
        active_version.status = PolicyVersionStatus.SUPERSEDED
        active_version.superseded_at = now
        active_version.updated_at = now
        _append_policy_version_audit(
            session,
            active_version,
            event_type="policy_version_superseded",
            actor=actor,
            summary="PolicyVersion superseded.",
            metadata={
                **_transition_metadata(previous_status, active_version.status),
                "superseded_by_version_id": str(version.id),
                "superseded_by_version_number": version.version_number,
            },
        )

    previous_status = version.status
    version.status = PolicyVersionStatus.ACTIVE
    version.activated_at = now
    version.updated_at = now
    _append_policy_version_audit(
        session,
        version,
        event_type="policy_version_activated",
        actor=actor,
        summary="PolicyVersion activated.",
        metadata=_transition_metadata(previous_status, version.status),
    )
    session.commit()
    session.refresh(version)
    return version


@router.post(
    "/{version_id}/archive",
    response_model=PolicyVersionRead,
)
def archive_policy_version(
    version_id: UUID,
    session: Session = Depends(get_db_session),
    actor: ActorContext = Depends(get_current_actor),
) -> PolicyVersion:
    version = _get_policy_version_or_404(session, version_id)
    _require_status(
        version,
        ARCHIVABLE_STATUSES,
        "Only draft, approved, rejected, active, or superseded policy versions "
        "can be archived.",
    )

    now = datetime.now(UTC)
    previous_status = version.status
    version.status = PolicyVersionStatus.ARCHIVED
    version.archived_at = now
    version.updated_at = now
    _append_policy_version_audit(
        session,
        version,
        event_type="policy_version_archived",
        actor=actor,
        summary="PolicyVersion archived.",
        metadata=_transition_metadata(previous_status, version.status),
    )
    session.commit()
    session.refresh(version)
    return version


@router.post(
    "/{version_id}/rollback-copy",
    response_model=PolicyVersionRead,
    status_code=status.HTTP_201_CREATED,
)
def create_policy_version_rollback_copy(
    version_id: UUID,
    payload: PolicyVersionCreate,
    session: Session = Depends(get_db_session),
    actor: ActorContext = Depends(get_current_actor),
) -> PolicyVersion:
    source_version = _get_policy_version_or_404(session, version_id)
    _require_status(
        source_version,
        ROLLBACK_COPY_SOURCE_STATUSES,
        "Only approved, rejected, active, or superseded policy versions can be copied "
        "to a new draft.",
    )

    now = datetime.now(UTC)
    new_version = PolicyVersion(
        id=uuid4(),
        policy_id=source_version.policy_id,
        source_version_id=source_version.id,
        version_number=_next_version_number(session, source_version.policy_id),
        status=PolicyVersionStatus.DRAFT,
        change_summary=payload.change_summary,
        policy_snapshot=deepcopy(source_version.policy_snapshot),
        rule_snapshots=deepcopy(source_version.rule_snapshots),
        check_step_snapshots=deepcopy(source_version.check_step_snapshots),
        created_by_actor_type=actor.actor_type,
        created_by_actor_id=actor.actor_id,
        created_at=now,
        updated_at=now,
    )
    session.add(new_version)
    session.flush()
    _append_policy_version_audit(
        session,
        new_version,
        event_type="policy_version_rollback_copy_created",
        actor=actor,
        summary="PolicyVersion rollback copy created.",
        metadata={
            "source_version_id": str(source_version.id),
            "source_version_number": source_version.version_number,
            "source_version_status": source_version.status.value,
            "change_summary": _audit_text(payload.change_summary),
        },
    )
    session.commit()
    session.refresh(new_version)
    return new_version


def _get_policy_or_404(session: Session, policy_id: UUID) -> Policy:
    policy = session.get(Policy, policy_id)
    if policy is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Policy not found.",
        )
    return policy


def _get_policy_version_or_404(
    session: Session,
    version_id: UUID,
) -> PolicyVersion:
    version = session.get(PolicyVersion, version_id)
    if version is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PolicyVersion not found.",
        )
    return version


def _next_version_number(session: Session, policy_id: UUID) -> int:
    latest_version_number = session.scalar(
        select(func.max(PolicyVersion.version_number)).where(
            PolicyVersion.policy_id == policy_id
        )
    )
    return int(latest_version_number or 0) + 1


def _snapshot_policy(
    session: Session,
    policy: Policy,
) -> tuple[dict[str, object], list[dict[str, object]], list[dict[str, object]]]:
    rules = list(
        session.scalars(
            select(PolicyRule)
            .where(PolicyRule.policy_id == policy.id)
            .order_by(PolicyRule.created_at, PolicyRule.id)
        ).all()
    )
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

    steps_by_rule_id: defaultdict[UUID, list[PolicyCheckStep]] = defaultdict(list)
    rule_ids = [rule.id for rule in rules]
    if rule_ids:
        steps = list(
            session.scalars(
                select(PolicyCheckStep)
                .where(PolicyCheckStep.policy_rule_id.in_(rule_ids))
                .order_by(PolicyCheckStep.created_at, PolicyCheckStep.id)
            ).all()
        )
        for step in steps:
            steps_by_rule_id[step.policy_rule_id].append(step)

    check_step_snapshots = [
        _snapshot_check_step(step)
        for rule in rules
        for step in steps_by_rule_id[rule.id]
    ]
    policy_snapshot = {
        "id": str(policy.id),
        "name": policy.name,
        "description": policy.description,
        "status": policy.status.value,
    }
    return policy_snapshot, rule_snapshots, check_step_snapshots


def _snapshot_check_step(step: PolicyCheckStep) -> dict[str, object]:
    return {
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
        "metadata": filter_safe_metadata(step.metadata_),
    }


def _require_status(
    version: PolicyVersion,
    allowed_statuses: set[PolicyVersionStatus],
    detail: str,
) -> None:
    if version.status in allowed_statuses:
        return
    raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)


def _append_policy_version_audit(
    session: Session,
    version: PolicyVersion,
    *,
    event_type: str,
    actor: ActorContext,
    summary: str,
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


def _transition_metadata(
    status_from: PolicyVersionStatus,
    status_to: PolicyVersionStatus,
) -> dict[str, str]:
    return {
        "status_from": status_from.value,
        "status_to": status_to.value,
    }


def _audit_text(value: str, *, max_length: int = 512) -> str:
    redacted = redact_sensitive_text(value)
    if len(redacted) <= max_length:
        return redacted
    return f"{redacted[: max_length - 3]}..."
