from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from agent_governance_api.audit import append_audit_log
from agent_governance_api.auth import ActorContext, get_current_actor
from agent_governance_api.database import get_db_session
from agent_governance_api.models import (
    CheckTool,
    CheckToolType,
    PolicyCheckStep,
    PolicyCheckStepCheckType,
    PolicyRule,
)
from agent_governance_api.openapi_examples import (
    POLICY_CHECK_STEP_CREATE_OPENAPI,
    POLICY_CHECK_STEP_GET_OPENAPI,
    POLICY_CHECK_STEP_LIST_OPENAPI,
    POLICY_CHECK_STEP_UPDATE_OPENAPI,
    POLICY_CHECK_STEPS_FOR_RULE_OPENAPI,
)
from agent_governance_api.schemas import (
    PolicyCheckStepCreate,
    PolicyCheckStepRead,
    PolicyCheckStepUpdate,
    validate_policy_check_step_target_selector,
)

router = APIRouter(prefix="/policy-check-steps", tags=["policy check steps"])
policy_rules_router = APIRouter(prefix="/policy-rules", tags=["policy check steps"])

CHECK_TOOL_TYPES_BY_STEP_TYPE = {
    PolicyCheckStepCheckType.ACCESS_GRANT_STATUS: CheckToolType.ACCESS_GRANT_CHECK,
    PolicyCheckStepCheckType.DATA_USAGE_PROFILE_STATUS: (
        CheckToolType.DATA_USAGE_PROFILE_CHECK
    ),
    PolicyCheckStepCheckType.SOURCE_STATUS: CheckToolType.SOURCE_STATUS_CHECK,
    PolicyCheckStepCheckType.SOURCE_CLASSIFICATION: CheckToolType.METADATA_LOOKUP,
    PolicyCheckStepCheckType.CAPABILITY_STATUS: (CheckToolType.CAPABILITY_STATUS_CHECK),
    PolicyCheckStepCheckType.MODEL_ASSET_STATUS: CheckToolType.MODEL_STATUS_CHECK,
    PolicyCheckStepCheckType.MODEL_PROVIDER_TYPE: CheckToolType.METADATA_LOOKUP,
}


@router.post(
    "",
    response_model=PolicyCheckStepRead,
    status_code=status.HTTP_201_CREATED,
    openapi_extra=POLICY_CHECK_STEP_CREATE_OPENAPI,
)
def create_policy_check_step(
    payload: PolicyCheckStepCreate,
    session: Session = Depends(get_db_session),
    actor: ActorContext = Depends(get_current_actor),
) -> PolicyCheckStep:
    _get_policy_rule_or_404(session, payload.policy_rule_id)
    _validate_check_tool_reference(
        session,
        check_tool_id=payload.check_tool_id,
        check_type=payload.check_type,
    )

    now = datetime.now(UTC)
    step = PolicyCheckStep(
        id=uuid4(),
        policy_rule_id=payload.policy_rule_id,
        check_tool_id=payload.check_tool_id,
        check_type=payload.check_type,
        target_selector=payload.target_selector,
        required=payload.required,
        failure_behavior=payload.failure_behavior,
        min_confidence=payload.min_confidence,
        status=payload.status,
        evidence_retention=payload.evidence_retention,
        metadata_=payload.metadata,
        created_at=now,
        updated_at=now,
    )
    session.add(step)
    append_audit_log(
        session,
        event_type="policy_check_step_created",
        actor_type=actor.actor_type,
        actor_id=actor.actor_id,
        entity_type="policy_check_step",
        entity_id=str(step.id),
        summary="PolicyCheckStep created.",
        metadata={
            "operation": "create",
            "policy_rule_id": str(step.policy_rule_id),
            "check_type": step.check_type.value,
            "target_selector": step.target_selector.value,
        },
    )
    session.commit()
    session.refresh(step)
    return step


@router.get(
    "",
    response_model=list[PolicyCheckStepRead],
    openapi_extra=POLICY_CHECK_STEP_LIST_OPENAPI,
)
def list_policy_check_steps(
    session: Session = Depends(get_db_session),
) -> list[PolicyCheckStep]:
    statement = select(PolicyCheckStep).order_by(
        PolicyCheckStep.created_at,
        PolicyCheckStep.id,
    )
    return list(session.scalars(statement).all())


@router.get(
    "/{step_id}",
    response_model=PolicyCheckStepRead,
    openapi_extra=POLICY_CHECK_STEP_GET_OPENAPI,
)
def get_policy_check_step(
    step_id: UUID,
    session: Session = Depends(get_db_session),
) -> PolicyCheckStep:
    return _get_policy_check_step_or_404(session, step_id)


@router.patch(
    "/{step_id}",
    response_model=PolicyCheckStepRead,
    openapi_extra=POLICY_CHECK_STEP_UPDATE_OPENAPI,
)
def update_policy_check_step(
    step_id: UUID,
    payload: PolicyCheckStepUpdate,
    session: Session = Depends(get_db_session),
    actor: ActorContext = Depends(get_current_actor),
) -> PolicyCheckStep:
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No update fields provided.",
        )

    step = _get_policy_check_step_or_404(session, step_id)
    if "policy_rule_id" in updates:
        _get_policy_rule_or_404(session, updates["policy_rule_id"])

    check_type = updates.get("check_type", step.check_type)
    target_selector = updates.get("target_selector", step.target_selector)
    validate_policy_check_step_target_selector(check_type, target_selector)
    check_tool_id = updates.get("check_tool_id", step.check_tool_id)
    _validate_check_tool_reference(
        session,
        check_tool_id=check_tool_id,
        check_type=check_type,
    )

    previous_status = step.status
    for field, value in updates.items():
        if field == "metadata":
            setattr(step, "metadata_", value)
            continue
        setattr(step, field, value)
    step.updated_at = datetime.now(UTC)

    status_changed = "status" in updates and step.status != previous_status
    event_type = (
        "policy_check_step_status_changed"
        if status_changed
        else "policy_check_step_updated"
    )
    metadata = {"updated_fields": ",".join(sorted(updates))}
    if status_changed:
        metadata["status_from"] = _value(previous_status)
        metadata["status_to"] = _value(step.status)

    append_audit_log(
        session,
        event_type=event_type,
        actor_type=actor.actor_type,
        actor_id=actor.actor_id,
        entity_type="policy_check_step",
        entity_id=str(step.id),
        summary=(
            "PolicyCheckStep status changed."
            if status_changed
            else "PolicyCheckStep updated."
        ),
        metadata=metadata,
    )
    session.commit()
    session.refresh(step)
    return step


@policy_rules_router.get(
    "/{rule_id}/check-steps",
    response_model=list[PolicyCheckStepRead],
    openapi_extra=POLICY_CHECK_STEPS_FOR_RULE_OPENAPI,
)
def list_policy_check_steps_for_rule(
    rule_id: UUID,
    session: Session = Depends(get_db_session),
) -> list[PolicyCheckStep]:
    _get_policy_rule_or_404(session, rule_id)
    statement = (
        select(PolicyCheckStep)
        .where(PolicyCheckStep.policy_rule_id == rule_id)
        .order_by(PolicyCheckStep.created_at, PolicyCheckStep.id)
    )
    return list(session.scalars(statement).all())


def _get_policy_rule_or_404(session: Session, rule_id: UUID) -> PolicyRule:
    rule = session.get(PolicyRule, rule_id)
    if rule is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PolicyRule not found.",
        )
    return rule


def _get_policy_check_step_or_404(
    session: Session,
    step_id: UUID,
) -> PolicyCheckStep:
    step = session.get(PolicyCheckStep, step_id)
    if step is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PolicyCheckStep not found.",
        )
    return step


def _validate_check_tool_reference(
    session: Session,
    *,
    check_tool_id: UUID | None,
    check_type: PolicyCheckStepCheckType,
) -> None:
    if check_tool_id is None:
        return

    check_tool = session.get(CheckTool, check_tool_id)
    if check_tool is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="CheckTool not found.",
        )

    expected_tool_type = CHECK_TOOL_TYPES_BY_STEP_TYPE[check_type]
    if check_tool.tool_type != expected_tool_type:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                "CheckTool type does not match PolicyCheckStep check_type. "
                f"Expected {expected_tool_type.value}."
            ),
        )


def _value(value: object) -> str:
    enum_value = getattr(value, "value", None)
    if isinstance(enum_value, str):
        return enum_value
    return str(value)
