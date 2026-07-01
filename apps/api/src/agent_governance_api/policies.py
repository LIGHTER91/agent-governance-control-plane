from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from agent_governance_api.audit import append_audit_log
from agent_governance_api.auth import ActorContext, get_current_actor
from agent_governance_api.database import get_db_session
from agent_governance_api.models import (
    AuditLog,
    HumanApproval,
    Policy,
    PolicyCheckStep,
    PolicyDecision,
    PolicyFolder,
    PolicyRule,
    PolicyStatus,
    PolicyVersion,
)
from agent_governance_api.models import (
    PolicyVersionReviewRequest as PolicyVersionReviewRequestModel,
)
from agent_governance_api.openapi_examples import (
    POLICY_CREATE_OPENAPI,
    POLICY_GET_OPENAPI,
    POLICY_LIST_OPENAPI,
    POLICY_RULES_FOR_POLICY_OPENAPI,
    POLICY_UPDATE_OPENAPI,
)
from agent_governance_api.policy_live_edit_guard import (
    POLICY_LIVE_EDIT_BLOCKED_DETAIL,
    active_policy_version_for_policy,
    block_policy_live_edit_if_active_version_exists,
)
from agent_governance_api.schemas import (
    PolicyCreate,
    PolicyRead,
    PolicyRuleRead,
    PolicyUpdate,
)

router = APIRouter(prefix="/policies", tags=["policies"])

POLICY_ARCHIVE_ACTIVE_VERSION_DETAIL = (
    "Deactivate or supersede the active PolicyVersion before archiving this policy."
)
POLICY_DELETE_GOVERNANCE_HISTORY_DETAIL = (
    "This policy has governance history and cannot be deleted. Archive it instead."
)
POLICY_DELETE_DRAFT_ONLY_DETAIL = (
    "Delete is only available for draft-only policies with no governance history."
)

_DELETABLE_POLICY_AUDIT_EVENTS = {"policy_created", "policy_updated"}
_DELETABLE_POLICY_RULE_AUDIT_EVENTS = {
    "policy_rule_created",
    "policy_rule_updated",
}


@router.post(
    "",
    response_model=PolicyRead,
    status_code=status.HTTP_201_CREATED,
    openapi_extra=POLICY_CREATE_OPENAPI,
)
def create_policy(
    payload: PolicyCreate,
    session: Session = Depends(get_db_session),
    actor: ActorContext = Depends(get_current_actor),
) -> Policy:
    now = datetime.now(UTC)
    if payload.folder_id is not None:
        _get_policy_folder_or_404(session, payload.folder_id)

    policy = Policy(
        id=uuid4(),
        folder_id=payload.folder_id,
        name=payload.name,
        description=payload.description,
        status=payload.status,
        created_at=now,
        updated_at=now,
    )

    session.add(policy)
    append_audit_log(
        session,
        event_type="policy_created",
        actor_type=actor.actor_type,
        actor_id=actor.actor_id,
        entity_type="policy",
        entity_id=str(policy.id),
        summary="Policy created.",
        metadata={
            "operation": "create",
            "status": policy.status.value,
            "folder_id": str(policy.folder_id) if policy.folder_id else None,
        },
    )
    session.commit()
    session.refresh(policy)

    return policy


@router.get("", response_model=list[PolicyRead], openapi_extra=POLICY_LIST_OPENAPI)
def list_policies(session: Session = Depends(get_db_session)) -> list[Policy]:
    statement = (
        select(Policy)
        .options(selectinload(Policy.folder))
        .order_by(Policy.created_at, Policy.id)
    )
    return list(session.scalars(statement).all())


@router.get(
    "/{policy_id}",
    response_model=PolicyRead,
    openapi_extra=POLICY_GET_OPENAPI,
)
def get_policy(
    policy_id: UUID,
    session: Session = Depends(get_db_session),
) -> Policy:
    return _get_policy_or_404(session, policy_id)


@router.get(
    "/{policy_id}/rules",
    response_model=list[PolicyRuleRead],
    openapi_extra=POLICY_RULES_FOR_POLICY_OPENAPI,
)
def list_policy_rules_for_policy(
    policy_id: UUID,
    session: Session = Depends(get_db_session),
) -> list[PolicyRule]:
    _get_policy_or_404(session, policy_id)
    statement = (
        select(PolicyRule)
        .where(PolicyRule.policy_id == policy_id)
        .order_by(PolicyRule.created_at, PolicyRule.id)
    )
    return list(session.scalars(statement).all())


@router.patch(
    "/{policy_id}",
    response_model=PolicyRead,
    openapi_extra=POLICY_UPDATE_OPENAPI,
)
def update_policy(
    policy_id: UUID,
    payload: PolicyUpdate,
    session: Session = Depends(get_db_session),
    actor: ActorContext = Depends(get_current_actor),
) -> Policy:
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No update fields provided.",
        )

    policy = _get_policy_or_404(session, policy_id)
    if set(updates) - {"folder_id"}:
        block_policy_live_edit_if_active_version_exists(
            session,
            policy_id=policy.id,
            actor=actor,
            operation="patch_policy",
            entity_type="policy",
            entity_id=str(policy.id),
            detail=POLICY_LIVE_EDIT_BLOCKED_DETAIL,
        )
    previous_status = policy.status
    previous_folder_id = policy.folder_id
    if "folder_id" in updates and updates["folder_id"] is not None:
        _get_policy_folder_or_404(session, updates["folder_id"])

    for field, value in updates.items():
        setattr(policy, field, value)
    policy.updated_at = datetime.now(UTC)

    status_changed = "status" in updates and policy.status != previous_status
    folder_changed = "folder_id" in updates and policy.folder_id != previous_folder_id
    event_type = (
        "policy_status_changed"
        if status_changed
        else "policy_moved_to_folder"
        if folder_changed
        else "policy_updated"
    )
    metadata = {"updated_fields": ",".join(sorted(updates))}
    if status_changed:
        metadata["status_from"] = _value(previous_status)
        metadata["status_to"] = _value(policy.status)
    if folder_changed:
        metadata["folder_id_from"] = (
            str(previous_folder_id) if previous_folder_id else None
        )
        metadata["folder_id_to"] = str(policy.folder_id) if policy.folder_id else None

    append_audit_log(
        session,
        event_type=event_type,
        actor_type=actor.actor_type,
        actor_id=actor.actor_id,
        entity_type="policy",
        entity_id=str(policy.id),
        summary=(
            "Policy status changed."
            if status_changed
            else "Policy moved to folder."
            if folder_changed
            else "Policy updated."
        ),
        metadata=metadata,
    )
    if status_changed and folder_changed:
        append_audit_log(
            session,
            event_type="policy_moved_to_folder",
            actor_type=actor.actor_type,
            actor_id=actor.actor_id,
            entity_type="policy",
            entity_id=str(policy.id),
            summary="Policy moved to folder.",
            metadata={
                "folder_id_from": (
                    str(previous_folder_id) if previous_folder_id else None
                ),
                "folder_id_to": str(policy.folder_id) if policy.folder_id else None,
            },
        )
    session.commit()
    session.refresh(policy)

    return policy


@router.post(
    "/{policy_id}/archive",
    response_model=PolicyRead,
)
def archive_policy(
    policy_id: UUID,
    session: Session = Depends(get_db_session),
    actor: ActorContext = Depends(get_current_actor),
) -> Policy:
    policy = _get_policy_or_404(session, policy_id)
    active_version = active_policy_version_for_policy(session, policy.id)
    if active_version is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=POLICY_ARCHIVE_ACTIVE_VERSION_DETAIL,
        )

    if policy.status is PolicyStatus.ARCHIVED:
        return policy

    previous_status = policy.status
    policy.status = PolicyStatus.ARCHIVED
    policy.updated_at = datetime.now(UTC)
    append_audit_log(
        session,
        event_type="policy_archived",
        actor_type=actor.actor_type,
        actor_id=actor.actor_id,
        entity_type="policy",
        entity_id=str(policy.id),
        summary="Policy archived. Evidence and history were retained.",
        metadata={
            "status_from": _value(previous_status),
            "status_to": policy.status.value,
            "history_retained": True,
        },
    )
    session.commit()
    session.refresh(policy)
    return policy


@router.delete(
    "/{policy_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_policy(
    policy_id: UUID,
    session: Session = Depends(get_db_session),
    actor: ActorContext = Depends(get_current_actor),
) -> Response:
    policy = _get_policy_or_404(session, policy_id)
    _require_policy_can_be_deleted(session, policy)

    rules = _policy_rules(session, policy.id)
    rule_ids = [rule.id for rule in rules]
    check_steps = _policy_check_steps_for_rule_ids(session, rule_ids)

    append_audit_log(
        session,
        event_type="policy_deleted",
        actor_type=actor.actor_type,
        actor_id=actor.actor_id,
        entity_type="policy",
        entity_id=str(policy.id),
        summary="Draft-only Policy deleted.",
        metadata={
            "status": policy.status.value,
            "rule_count": len(rules),
            "check_step_count": len(check_steps),
            "history_retained": True,
        },
    )
    for check_step in check_steps:
        session.delete(check_step)
    for rule in rules:
        session.delete(rule)
    session.delete(policy)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _get_policy_or_404(session: Session, policy_id: UUID) -> Policy:
    policy = session.get(Policy, policy_id)
    if policy is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Policy not found.",
        )
    return policy


def _get_policy_folder_or_404(session: Session, folder_id: UUID) -> PolicyFolder:
    folder = session.get(PolicyFolder, folder_id)
    if folder is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PolicyFolder not found.",
        )
    return folder


def _require_policy_can_be_deleted(session: Session, policy: Policy) -> None:
    if policy.status is not PolicyStatus.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=POLICY_DELETE_DRAFT_ONLY_DETAIL,
        )
    if (
        _policy_has_versions(session, policy.id)
        or _policy_has_review_requests(session, policy.id)
        or _policy_has_policy_decisions(session, policy.id)
        or _policy_has_human_approval_history(session, policy.id)
        or _policy_has_meaningful_audit_history(session, policy)
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=POLICY_DELETE_GOVERNANCE_HISTORY_DETAIL,
        )


def _policy_has_versions(session: Session, policy_id: UUID) -> bool:
    return (
        session.scalar(
            select(PolicyVersion.id).where(PolicyVersion.policy_id == policy_id)
        )
        is not None
    )


def _policy_has_review_requests(session: Session, policy_id: UUID) -> bool:
    return (
        session.scalar(
            select(PolicyVersionReviewRequestModel.id).where(
                PolicyVersionReviewRequestModel.policy_id == policy_id
            )
        )
        is not None
    )


def _policy_has_policy_decisions(session: Session, policy_id: UUID) -> bool:
    return (
        session.scalar(
            select(PolicyDecision.id).where(PolicyDecision.policy_id == policy_id)
        )
        is not None
    )


def _policy_has_human_approval_history(session: Session, policy_id: UUID) -> bool:
    return (
        session.scalar(
            select(HumanApproval.id)
            .join(PolicyDecision, HumanApproval.policy_decision_id == PolicyDecision.id)
            .where(PolicyDecision.policy_id == policy_id)
        )
        is not None
    )


def _policy_has_meaningful_audit_history(
    session: Session,
    policy: Policy,
) -> bool:
    policy_audit_events = list(
        session.scalars(
            select(AuditLog.event_type).where(
                AuditLog.entity_type == "policy",
                AuditLog.entity_id == str(policy.id),
            )
        ).all()
    )
    if any(
        event_type not in _DELETABLE_POLICY_AUDIT_EVENTS
        for event_type in policy_audit_events
    ):
        return True

    rule_ids = [str(rule.id) for rule in _policy_rules(session, policy.id)]
    if not rule_ids:
        return False

    rule_audit_events = list(
        session.scalars(
            select(AuditLog.event_type).where(
                AuditLog.entity_type == "policy_rule",
                AuditLog.entity_id.in_(rule_ids),
            )
        ).all()
    )
    return any(
        event_type not in _DELETABLE_POLICY_RULE_AUDIT_EVENTS
        for event_type in rule_audit_events
    )


def _policy_rules(session: Session, policy_id: UUID) -> list[PolicyRule]:
    return list(
        session.scalars(
            select(PolicyRule)
            .where(PolicyRule.policy_id == policy_id)
            .order_by(PolicyRule.created_at, PolicyRule.id)
        ).all()
    )


def _policy_check_steps_for_rule_ids(
    session: Session,
    rule_ids: list[UUID],
) -> list[PolicyCheckStep]:
    if not rule_ids:
        return []
    return list(
        session.scalars(
            select(PolicyCheckStep)
            .where(PolicyCheckStep.policy_rule_id.in_(rule_ids))
            .order_by(PolicyCheckStep.created_at, PolicyCheckStep.id)
        ).all()
    )


def _value(value: object) -> str:
    enum_value = getattr(value, "value", None)
    if isinstance(enum_value, str):
        return enum_value
    return str(value)
