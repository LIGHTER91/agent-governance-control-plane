from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from agent_governance_api.audit import append_audit_log
from agent_governance_api.auth import ActorContext, get_current_actor
from agent_governance_api.database import get_db_session
from agent_governance_api.models import Policy, PolicyRule
from agent_governance_api.openapi_examples import (
    POLICY_CREATE_OPENAPI,
    POLICY_GET_OPENAPI,
    POLICY_LIST_OPENAPI,
    POLICY_RULES_FOR_POLICY_OPENAPI,
    POLICY_UPDATE_OPENAPI,
)
from agent_governance_api.policy_live_edit_guard import (
    POLICY_LIVE_EDIT_BLOCKED_DETAIL,
    block_policy_live_edit_if_active_version_exists,
)
from agent_governance_api.schemas import (
    PolicyCreate,
    PolicyRead,
    PolicyRuleRead,
    PolicyUpdate,
)

router = APIRouter(prefix="/policies", tags=["policies"])


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
    policy = Policy(
        id=uuid4(),
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
        metadata={"operation": "create", "status": policy.status.value},
    )
    session.commit()
    session.refresh(policy)

    return policy


@router.get("", response_model=list[PolicyRead], openapi_extra=POLICY_LIST_OPENAPI)
def list_policies(session: Session = Depends(get_db_session)) -> list[Policy]:
    statement = select(Policy).order_by(Policy.created_at, Policy.id)
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

    for field, value in updates.items():
        setattr(policy, field, value)
    policy.updated_at = datetime.now(UTC)

    status_changed = "status" in updates and policy.status != previous_status
    event_type = "policy_status_changed" if status_changed else "policy_updated"
    metadata = {"updated_fields": ",".join(sorted(updates))}
    if status_changed:
        metadata["status_from"] = _value(previous_status)
        metadata["status_to"] = _value(policy.status)

    append_audit_log(
        session,
        event_type=event_type,
        actor_type=actor.actor_type,
        actor_id=actor.actor_id,
        entity_type="policy",
        entity_id=str(policy.id),
        summary="Policy status changed." if status_changed else "Policy updated.",
        metadata=metadata,
    )
    session.commit()
    session.refresh(policy)

    return policy


def _get_policy_or_404(session: Session, policy_id: UUID) -> Policy:
    policy = session.get(Policy, policy_id)
    if policy is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Policy not found.",
        )
    return policy


def _value(value: object) -> str:
    enum_value = getattr(value, "value", None)
    if isinstance(enum_value, str):
        return enum_value
    return str(value)
