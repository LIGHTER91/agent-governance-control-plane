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
    POLICY_RULE_CREATE_OPENAPI,
    POLICY_RULE_GET_OPENAPI,
    POLICY_RULE_LIST_OPENAPI,
    POLICY_RULE_UPDATE_OPENAPI,
)
from agent_governance_api.policy_live_edit_guard import (
    POLICY_RULE_LIVE_EDIT_BLOCKED_DETAIL,
    block_policy_live_edit_if_active_version_exists,
)
from agent_governance_api.schemas import (
    PolicyRuleCreate,
    PolicyRuleRead,
    PolicyRuleUpdate,
)

router = APIRouter(prefix="/policy-rules", tags=["policy rules"])


@router.post(
    "",
    response_model=PolicyRuleRead,
    status_code=status.HTTP_201_CREATED,
    openapi_extra=POLICY_RULE_CREATE_OPENAPI,
)
def create_policy_rule(
    payload: PolicyRuleCreate,
    session: Session = Depends(get_db_session),
    actor: ActorContext = Depends(get_current_actor),
) -> PolicyRule:
    policy = _get_policy_or_404(session, payload.policy_id)
    block_policy_live_edit_if_active_version_exists(
        session,
        policy_id=policy.id,
        actor=actor,
        operation="create_policy_rule",
        entity_type="policy",
        entity_id=str(policy.id),
        detail=POLICY_RULE_LIVE_EDIT_BLOCKED_DETAIL,
    )
    now = datetime.now(UTC)
    rule = PolicyRule(
        id=uuid4(),
        policy_id=payload.policy_id,
        name=payload.name,
        description=payload.description,
        condition=payload.condition,
        created_at=now,
        updated_at=now,
    )

    session.add(rule)
    append_audit_log(
        session,
        event_type="policy_rule_created",
        actor_type=actor.actor_type,
        actor_id=actor.actor_id,
        entity_type="policy_rule",
        entity_id=str(rule.id),
        summary="PolicyRule created.",
        metadata={"operation": "create", "policy_id": str(rule.policy_id)},
    )
    session.commit()
    session.refresh(rule)

    return rule


@router.get(
    "",
    response_model=list[PolicyRuleRead],
    openapi_extra=POLICY_RULE_LIST_OPENAPI,
)
def list_policy_rules(session: Session = Depends(get_db_session)) -> list[PolicyRule]:
    statement = select(PolicyRule).order_by(PolicyRule.created_at, PolicyRule.id)
    return list(session.scalars(statement).all())


@router.get(
    "/{rule_id}",
    response_model=PolicyRuleRead,
    openapi_extra=POLICY_RULE_GET_OPENAPI,
)
def get_policy_rule(
    rule_id: UUID,
    session: Session = Depends(get_db_session),
) -> PolicyRule:
    return _get_policy_rule_or_404(session, rule_id)


@router.patch(
    "/{rule_id}",
    response_model=PolicyRuleRead,
    openapi_extra=POLICY_RULE_UPDATE_OPENAPI,
)
def update_policy_rule(
    rule_id: UUID,
    payload: PolicyRuleUpdate,
    session: Session = Depends(get_db_session),
    actor: ActorContext = Depends(get_current_actor),
) -> PolicyRule:
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No update fields provided.",
        )

    rule = _get_policy_rule_or_404(session, rule_id)
    previous_policy_id = rule.policy_id
    block_policy_live_edit_if_active_version_exists(
        session,
        policy_id=rule.policy_id,
        actor=actor,
        operation="patch_policy_rule",
        entity_type="policy_rule",
        entity_id=str(rule.id),
        detail=POLICY_RULE_LIVE_EDIT_BLOCKED_DETAIL,
    )
    if "policy_id" in updates:
        target_policy = _get_policy_or_404(session, updates["policy_id"])
        if target_policy.id != rule.policy_id:
            block_policy_live_edit_if_active_version_exists(
                session,
                policy_id=target_policy.id,
                actor=actor,
                operation="move_policy_rule",
                entity_type="policy_rule",
                entity_id=str(rule.id),
                detail=POLICY_RULE_LIVE_EDIT_BLOCKED_DETAIL,
            )

    for field, value in updates.items():
        setattr(rule, field, value)
    rule.updated_at = datetime.now(UTC)

    metadata = {"updated_fields": ",".join(sorted(updates))}
    if "policy_id" in updates and rule.policy_id != previous_policy_id:
        metadata["policy_id_from"] = str(previous_policy_id)
        metadata["policy_id_to"] = str(rule.policy_id)

    append_audit_log(
        session,
        event_type="policy_rule_updated",
        actor_type=actor.actor_type,
        actor_id=actor.actor_id,
        entity_type="policy_rule",
        entity_id=str(rule.id),
        summary="PolicyRule updated.",
        metadata=metadata,
    )
    session.commit()
    session.refresh(rule)

    return rule


def _get_policy_or_404(session: Session, policy_id: UUID) -> Policy:
    policy = session.get(Policy, policy_id)
    if policy is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Policy not found.",
        )
    return policy


def _get_policy_rule_or_404(session: Session, rule_id: UUID) -> PolicyRule:
    rule = session.get(PolicyRule, rule_id)
    if rule is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PolicyRule not found.",
        )
    return rule
