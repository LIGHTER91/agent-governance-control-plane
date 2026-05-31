from collections.abc import Callable
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from agent_governance_api.models import (
    AccessGrantTargetType,
    CheckResult,
    CheckResultConfidence,
    CheckResultOutcome,
    CheckResultTargetType,
    CheckTool,
    CheckToolStatus,
    CheckToolType,
    OwnerType,
    PolicyCheckStep,
    PolicyCheckStepCheckType,
    PolicyCheckStepStatus,
    PolicyCheckStepTargetSelector,
    TraceEventRecord,
)
from agent_governance_api.policy_pre_checks import (
    check_access_grant_status,
    check_capability_status,
    check_data_usage_profile_status,
    check_model_asset_status,
    check_source_status,
    persist_check_result,
    record_metadata_check_error,
)
from agent_governance_api.runtime_gateway import RuntimeToolCallDecisionRequest

INTERNAL_CHECK_TOOL_OWNER_ID = "service:agcp-runtime-metadata-pre-checks"
INTERNAL_CHECK_TOOL_OWNER_NAME = "AGCP Runtime Metadata Pre-Checks"


@dataclass(frozen=True, slots=True)
class RuntimeMetadataPreCheckToolSpec:
    name: str
    description: str
    tool_type: CheckToolType


ACCESS_GRANT_CHECK_TOOL = RuntimeMetadataPreCheckToolSpec(
    name="runtime_access_grant_status_checker",
    description="Runtime metadata-only AccessGrant status check.",
    tool_type=CheckToolType.ACCESS_GRANT_CHECK,
)
DATA_USAGE_PROFILE_CHECK_TOOL = RuntimeMetadataPreCheckToolSpec(
    name="runtime_data_usage_profile_status_checker",
    description="Runtime metadata-only Data Usage Profile status check.",
    tool_type=CheckToolType.DATA_USAGE_PROFILE_CHECK,
)
SOURCE_STATUS_CHECK_TOOL = RuntimeMetadataPreCheckToolSpec(
    name="runtime_source_status_checker",
    description="Runtime metadata-only Source status check.",
    tool_type=CheckToolType.SOURCE_STATUS_CHECK,
)
CAPABILITY_STATUS_CHECK_TOOL = RuntimeMetadataPreCheckToolSpec(
    name="runtime_capability_status_checker",
    description="Runtime metadata-only Capability status check.",
    tool_type=CheckToolType.CAPABILITY_STATUS_CHECK,
)
MODEL_ASSET_STATUS_CHECK_TOOL = RuntimeMetadataPreCheckToolSpec(
    name="runtime_model_asset_status_checker",
    description="Runtime metadata-only ModelAsset status check.",
    tool_type=CheckToolType.MODEL_STATUS_CHECK,
)

CHECK_TOOL_TYPES_BY_STEP_TYPE = {
    PolicyCheckStepCheckType.ACCESS_GRANT_STATUS: CheckToolType.ACCESS_GRANT_CHECK,
    PolicyCheckStepCheckType.DATA_USAGE_PROFILE_STATUS: (
        CheckToolType.DATA_USAGE_PROFILE_CHECK
    ),
    PolicyCheckStepCheckType.SOURCE_STATUS: CheckToolType.SOURCE_STATUS_CHECK,
    PolicyCheckStepCheckType.CAPABILITY_STATUS: CheckToolType.CAPABILITY_STATUS_CHECK,
    PolicyCheckStepCheckType.MODEL_ASSET_STATUS: CheckToolType.MODEL_STATUS_CHECK,
}

INTERNAL_CHECK_TOOL_SPECS_BY_STEP_TYPE = {
    PolicyCheckStepCheckType.ACCESS_GRANT_STATUS: ACCESS_GRANT_CHECK_TOOL,
    PolicyCheckStepCheckType.DATA_USAGE_PROFILE_STATUS: DATA_USAGE_PROFILE_CHECK_TOOL,
    PolicyCheckStepCheckType.SOURCE_STATUS: SOURCE_STATUS_CHECK_TOOL,
    PolicyCheckStepCheckType.CAPABILITY_STATUS: CAPABILITY_STATUS_CHECK_TOOL,
    PolicyCheckStepCheckType.MODEL_ASSET_STATUS: MODEL_ASSET_STATUS_CHECK_TOOL,
}

SUPPORTED_SELECTORS_BY_STEP_TYPE = {
    PolicyCheckStepCheckType.ACCESS_GRANT_STATUS: {
        PolicyCheckStepTargetSelector.ACCESS_GRANTS,
    },
    PolicyCheckStepCheckType.DATA_USAGE_PROFILE_STATUS: {
        PolicyCheckStepTargetSelector.SOURCE_IDS,
    },
    PolicyCheckStepCheckType.SOURCE_STATUS: {
        PolicyCheckStepTargetSelector.SOURCE_IDS,
    },
    PolicyCheckStepCheckType.CAPABILITY_STATUS: {
        PolicyCheckStepTargetSelector.CAPABILITY_ID,
    },
    PolicyCheckStepCheckType.MODEL_ASSET_STATUS: {
        PolicyCheckStepTargetSelector.MODEL_ID,
    },
}


def run_runtime_metadata_pre_checks(
    session: Session,
    *,
    payload: RuntimeToolCallDecisionRequest,
    trace_event: TraceEventRecord,
    policy_decision_id: UUID | None,
    policy_rule_ids: tuple[str | UUID, ...] = (),
) -> list[CheckResult]:
    """Run authored metadata-only check steps without changing the decision."""

    results: list[CheckResult] = []
    rule_ids = _dedupe_rule_ids(policy_rule_ids)
    if not rule_ids:
        return results

    steps = _load_active_policy_check_steps(session, rule_ids)
    for step in steps:
        _append_policy_check_step_results(
            results,
            session=session,
            step=step,
            payload=payload,
            trace_event=trace_event,
            policy_decision_id=policy_decision_id,
        )

    return results


def _dedupe_rule_ids(policy_rule_ids: tuple[str | UUID, ...]) -> tuple[UUID, ...]:
    rule_ids: list[UUID] = []
    seen: set[UUID] = set()
    for raw_rule_id in policy_rule_ids:
        rule_id = UUID(str(raw_rule_id))
        if rule_id in seen:
            continue
        rule_ids.append(rule_id)
        seen.add(rule_id)
    return tuple(rule_ids)


def _load_active_policy_check_steps(
    session: Session,
    policy_rule_ids: tuple[UUID, ...],
) -> list[PolicyCheckStep]:
    statement = (
        select(PolicyCheckStep)
        .where(
            PolicyCheckStep.policy_rule_id.in_(policy_rule_ids),
            PolicyCheckStep.status == PolicyCheckStepStatus.ACTIVE,
        )
        .order_by(PolicyCheckStep.created_at, PolicyCheckStep.id)
    )
    return list(session.scalars(statement).all())


def _append_policy_check_step_results(
    results: list[CheckResult],
    *,
    session: Session,
    step: PolicyCheckStep,
    payload: RuntimeToolCallDecisionRequest,
    trace_event: TraceEventRecord,
    policy_decision_id: UUID | None,
) -> None:
    check_tool = _runtime_check_tool_for_step(session, step)
    if check_tool is None:
        return

    if step.target_selector not in SUPPORTED_SELECTORS_BY_STEP_TYPE[step.check_type]:
        _append_unsupported_step_result(
            results,
            session=session,
            step=step,
            check_tool=check_tool,
            payload=payload,
            trace_event=trace_event,
            policy_decision_id=policy_decision_id,
        )
        return

    if step.check_type is PolicyCheckStepCheckType.ACCESS_GRANT_STATUS:
        _append_access_grant_step_results(
            results,
            session=session,
            step=step,
            check_tool=check_tool,
            payload=payload,
            trace_event=trace_event,
            policy_decision_id=policy_decision_id,
        )
        return

    if step.check_type is PolicyCheckStepCheckType.DATA_USAGE_PROFILE_STATUS:
        _append_data_usage_profile_step_results(
            results,
            session=session,
            step=step,
            check_tool=check_tool,
            payload=payload,
            trace_event=trace_event,
            policy_decision_id=policy_decision_id,
        )
        return

    if step.check_type is PolicyCheckStepCheckType.SOURCE_STATUS:
        _append_source_step_results(
            results,
            session=session,
            step=step,
            check_tool=check_tool,
            payload=payload,
            trace_event=trace_event,
            policy_decision_id=policy_decision_id,
        )
        return

    if step.check_type is PolicyCheckStepCheckType.CAPABILITY_STATUS:
        _append_capability_step_result(
            results,
            session=session,
            step=step,
            check_tool=check_tool,
            payload=payload,
            trace_event=trace_event,
            policy_decision_id=policy_decision_id,
        )
        return

    _append_model_asset_step_result(
        results,
        session=session,
        step=step,
        check_tool=check_tool,
        payload=payload,
        trace_event=trace_event,
        policy_decision_id=policy_decision_id,
    )


def _append_access_grant_step_results(
    results: list[CheckResult],
    *,
    session: Session,
    step: PolicyCheckStep,
    check_tool: CheckTool,
    payload: RuntimeToolCallDecisionRequest,
    trace_event: TraceEventRecord,
    policy_decision_id: UUID | None,
) -> None:
    targets: list[tuple[AccessGrantTargetType, UUID]] = []
    if payload.capability_id is not None:
        targets.append((AccessGrantTargetType.CAPABILITY, payload.capability_id))
    targets.extend(
        (AccessGrantTargetType.SOURCE, source_id) for source_id in payload.source_ids
    )
    if payload.model_id is not None:
        targets.append((AccessGrantTargetType.MODEL_ASSET, payload.model_id))

    if not targets:
        _append_not_applicable_result(
            results,
            session=session,
            check_tool=check_tool,
            step=step,
            payload=payload,
            trace_event=trace_event,
            policy_decision_id=policy_decision_id,
            target_type=CheckResultTargetType.ACCESS_GRANT,
            summary=(
                "PolicyCheckStep skipped because no access grant targets were declared."
            ),
            reason=(
                "The runtime request did not include capability_id, source_ids, "
                "or model_id references."
            ),
            metadata={"missing_context_field": "access_grants"},
        )
        return

    for target_type, target_id in targets:
        _append_access_grant_check(
            results,
            session=session,
            step=step,
            check_tool=check_tool,
            payload=payload,
            trace_event=trace_event,
            policy_decision_id=policy_decision_id,
            target_type=target_type,
            target_id=target_id,
        )


def _append_data_usage_profile_step_results(
    results: list[CheckResult],
    *,
    session: Session,
    step: PolicyCheckStep,
    check_tool: CheckTool,
    payload: RuntimeToolCallDecisionRequest,
    trace_event: TraceEventRecord,
    policy_decision_id: UUID | None,
) -> None:
    if not payload.source_ids:
        _append_not_applicable_result(
            results,
            session=session,
            check_tool=check_tool,
            step=step,
            payload=payload,
            trace_event=trace_event,
            policy_decision_id=policy_decision_id,
            target_type=CheckResultTargetType.DATA_USAGE_PROFILE,
            summary="PolicyCheckStep skipped because source_ids were not declared.",
            reason="DataUsageProfile checks require runtime source_ids context.",
            metadata={"missing_context_field": "source_ids"},
        )
        return

    for source_id in payload.source_ids:
        _append_checked_result(
            results,
            session=session,
            step=step,
            check_tool=check_tool,
            target_type=CheckResultTargetType.DATA_USAGE_PROFILE,
            target_id=None,
            check_type=step.check_type.value,
            agent_id=payload.agent_id,
            run_id=payload.run_id,
            trace_event_id=trace_event.id,
            policy_decision_id=policy_decision_id,
            run_check=lambda check_tool_id, source_id=source_id: (
                check_data_usage_profile_status(
                    session,
                    check_tool_id=check_tool_id,
                    source_id=source_id,
                    agent_id=payload.agent_id,
                    run_id=payload.run_id,
                    trace_event_id=trace_event.id,
                    policy_decision_id=policy_decision_id,
                )
            ),
        )


def _append_source_step_results(
    results: list[CheckResult],
    *,
    session: Session,
    step: PolicyCheckStep,
    check_tool: CheckTool,
    payload: RuntimeToolCallDecisionRequest,
    trace_event: TraceEventRecord,
    policy_decision_id: UUID | None,
) -> None:
    if not payload.source_ids:
        _append_not_applicable_result(
            results,
            session=session,
            check_tool=check_tool,
            step=step,
            payload=payload,
            trace_event=trace_event,
            policy_decision_id=policy_decision_id,
            target_type=CheckResultTargetType.SOURCE,
            summary="PolicyCheckStep skipped because source_ids were not declared.",
            reason="Source status checks require runtime source_ids context.",
            metadata={"missing_context_field": "source_ids"},
        )
        return

    for source_id in payload.source_ids:
        _append_checked_result(
            results,
            session=session,
            step=step,
            check_tool=check_tool,
            target_type=CheckResultTargetType.SOURCE,
            target_id=source_id,
            check_type=step.check_type.value,
            agent_id=payload.agent_id,
            run_id=payload.run_id,
            trace_event_id=trace_event.id,
            policy_decision_id=policy_decision_id,
            run_check=lambda check_tool_id, source_id=source_id: check_source_status(
                session,
                check_tool_id=check_tool_id,
                source_id=source_id,
                agent_id=payload.agent_id,
                run_id=payload.run_id,
                trace_event_id=trace_event.id,
                policy_decision_id=policy_decision_id,
            ),
        )


def _append_capability_step_result(
    results: list[CheckResult],
    *,
    session: Session,
    step: PolicyCheckStep,
    check_tool: CheckTool,
    payload: RuntimeToolCallDecisionRequest,
    trace_event: TraceEventRecord,
    policy_decision_id: UUID | None,
) -> None:
    if payload.capability_id is None:
        _append_not_applicable_result(
            results,
            session=session,
            check_tool=check_tool,
            step=step,
            payload=payload,
            trace_event=trace_event,
            policy_decision_id=policy_decision_id,
            target_type=CheckResultTargetType.CAPABILITY,
            summary="PolicyCheckStep skipped because capability_id was not declared.",
            reason="Capability status checks require runtime capability_id context.",
            metadata={"missing_context_field": "capability_id"},
        )
        return

    _append_checked_result(
        results,
        session=session,
        step=step,
        check_tool=check_tool,
        target_type=CheckResultTargetType.CAPABILITY,
        target_id=payload.capability_id,
        check_type=step.check_type.value,
        agent_id=payload.agent_id,
        run_id=payload.run_id,
        trace_event_id=trace_event.id,
        policy_decision_id=policy_decision_id,
        run_check=lambda check_tool_id: check_capability_status(
            session,
            check_tool_id=check_tool_id,
            capability_id=payload.capability_id,
            agent_id=payload.agent_id,
            run_id=payload.run_id,
            trace_event_id=trace_event.id,
            policy_decision_id=policy_decision_id,
        ),
    )


def _append_model_asset_step_result(
    results: list[CheckResult],
    *,
    session: Session,
    step: PolicyCheckStep,
    check_tool: CheckTool,
    payload: RuntimeToolCallDecisionRequest,
    trace_event: TraceEventRecord,
    policy_decision_id: UUID | None,
) -> None:
    if payload.model_id is None:
        _append_not_applicable_result(
            results,
            session=session,
            check_tool=check_tool,
            step=step,
            payload=payload,
            trace_event=trace_event,
            policy_decision_id=policy_decision_id,
            target_type=CheckResultTargetType.MODEL_ASSET,
            summary="PolicyCheckStep skipped because model_id was not declared.",
            reason="ModelAsset status checks require runtime model_id context.",
            metadata={"missing_context_field": "model_id"},
        )
        return

    _append_checked_result(
        results,
        session=session,
        step=step,
        check_tool=check_tool,
        target_type=CheckResultTargetType.MODEL_ASSET,
        target_id=payload.model_id,
        check_type=step.check_type.value,
        agent_id=payload.agent_id,
        run_id=payload.run_id,
        trace_event_id=trace_event.id,
        policy_decision_id=policy_decision_id,
        run_check=lambda check_tool_id: check_model_asset_status(
            session,
            check_tool_id=check_tool_id,
            model_asset_id=payload.model_id,
            agent_id=payload.agent_id,
            run_id=payload.run_id,
            trace_event_id=trace_event.id,
            policy_decision_id=policy_decision_id,
        ),
    )


def _append_access_grant_check(
    results: list[CheckResult],
    *,
    session: Session,
    step: PolicyCheckStep,
    check_tool: CheckTool,
    payload: RuntimeToolCallDecisionRequest,
    trace_event: TraceEventRecord,
    policy_decision_id: UUID | None,
    target_type: AccessGrantTargetType,
    target_id: UUID,
) -> None:
    _append_checked_result(
        results,
        session=session,
        step=step,
        check_tool=check_tool,
        target_type=CheckResultTargetType.ACCESS_GRANT,
        target_id=None,
        check_type="access_grant_status",
        agent_id=payload.agent_id,
        run_id=payload.run_id,
        trace_event_id=trace_event.id,
        policy_decision_id=policy_decision_id,
        run_check=lambda check_tool_id: check_access_grant_status(
            session,
            check_tool_id=check_tool_id,
            agent_id=payload.agent_id,
            target_type=target_type,
            target_id=target_id,
            run_id=payload.run_id,
            trace_event_id=trace_event.id,
            policy_decision_id=policy_decision_id,
        ),
    )


def _append_checked_result(
    results: list[CheckResult],
    *,
    session: Session,
    step: PolicyCheckStep,
    check_tool: CheckTool,
    target_type: CheckResultTargetType,
    target_id: UUID | None,
    check_type: str,
    agent_id: UUID,
    run_id: UUID,
    trace_event_id: UUID,
    policy_decision_id: UUID | None,
    run_check: Callable[[UUID], CheckResult],
) -> None:
    try:
        check_result = run_check(check_tool.id)
    except Exception:
        check_result = record_metadata_check_error(
            session,
            check_tool_id=check_tool.id,
            agent_id=agent_id,
            run_id=run_id,
            trace_event_id=trace_event_id,
            policy_decision_id=policy_decision_id,
            target_type=target_type,
            target_id=target_id,
            summary="Runtime metadata-only PolicyCheckStep failed.",
            reason=(
                "The authored metadata-only helper failed before completing. "
                "No raw runtime payload was stored."
            ),
            metadata={"check_type": f"{check_type}_error"},
        )
    _attach_policy_check_step_metadata(check_result, step)
    results.append(check_result)


def _append_not_applicable_result(
    results: list[CheckResult],
    *,
    session: Session,
    check_tool: CheckTool,
    step: PolicyCheckStep,
    payload: RuntimeToolCallDecisionRequest,
    trace_event: TraceEventRecord,
    policy_decision_id: UUID | None,
    target_type: CheckResultTargetType,
    summary: str,
    reason: str,
    metadata: dict[str, object],
) -> None:
    check_result = persist_check_result(
        session,
        check_tool_id=check_tool.id,
        agent_id=payload.agent_id,
        run_id=payload.run_id,
        trace_event_id=trace_event.id,
        policy_decision_id=policy_decision_id,
        target_type=target_type,
        outcome=CheckResultOutcome.NOT_APPLICABLE,
        confidence=CheckResultConfidence.HIGH,
        summary=summary,
        reason=reason,
        metadata={"check_type": step.check_type.value, **metadata},
    )
    _attach_policy_check_step_metadata(check_result, step)
    results.append(check_result)


def _append_unsupported_step_result(
    results: list[CheckResult],
    *,
    session: Session,
    step: PolicyCheckStep,
    check_tool: CheckTool,
    payload: RuntimeToolCallDecisionRequest,
    trace_event: TraceEventRecord,
    policy_decision_id: UUID | None,
) -> None:
    check_result = record_metadata_check_error(
        session,
        check_tool_id=check_tool.id,
        agent_id=payload.agent_id,
        run_id=payload.run_id,
        trace_event_id=trace_event.id,
        policy_decision_id=policy_decision_id,
        target_type=CheckResultTargetType.EXTERNAL,
        target_id=None,
        summary="PolicyCheckStep uses an unsupported target selector.",
        reason="The check step was skipped and did not affect the runtime decision.",
        metadata={
            "check_type": f"{step.check_type.value}_unsupported_target_selector",
            "target_selector": step.target_selector.value,
        },
    )
    _attach_policy_check_step_metadata(check_result, step)
    results.append(check_result)


def _runtime_check_tool_for_step(
    session: Session,
    step: PolicyCheckStep,
) -> CheckTool | None:
    if step.check_tool_id is not None:
        check_tool = session.get(CheckTool, step.check_tool_id)
        expected_type = CHECK_TOOL_TYPES_BY_STEP_TYPE[step.check_type]
        if check_tool is None or check_tool.status != CheckToolStatus.ACTIVE:
            return None
        if check_tool.tool_type != expected_type:
            return None
        return check_tool

    return _get_or_create_runtime_check_tool(
        session,
        INTERNAL_CHECK_TOOL_SPECS_BY_STEP_TYPE[step.check_type],
    )


def _attach_policy_check_step_metadata(
    check_result: CheckResult,
    step: PolicyCheckStep,
) -> None:
    metadata = {
        **(check_result.metadata_ or {}),
        "policy_check_step_id": str(step.id),
        "policy_check_step_rule_id": str(step.policy_rule_id),
        "policy_check_step_check_type": step.check_type.value,
        "policy_check_step_target_selector": step.target_selector.value,
        "policy_check_step_required": step.required,
        "policy_check_step_failure_behavior": step.failure_behavior.value,
        "policy_check_step_evidence_retention": step.evidence_retention.value,
    }
    if step.min_confidence is not None:
        metadata["policy_check_step_min_confidence"] = step.min_confidence
    check_result.metadata_ = metadata


def _get_or_create_runtime_check_tool(
    session: Session,
    spec: RuntimeMetadataPreCheckToolSpec,
) -> CheckTool | None:
    check_tool = session.scalar(select(CheckTool).where(CheckTool.name == spec.name))
    if check_tool is not None:
        if check_tool.status != CheckToolStatus.ACTIVE:
            return None
        return check_tool

    check_tool = CheckTool(
        name=spec.name,
        description=spec.description,
        tool_type=spec.tool_type,
        status=CheckToolStatus.ACTIVE,
        owner_type=OwnerType.SERVICE,
        owner_id=INTERNAL_CHECK_TOOL_OWNER_ID,
        owner_name=INTERNAL_CHECK_TOOL_OWNER_NAME,
        metadata_={"managed_by": "runtime_gateway"},
    )
    session.add(check_tool)
    session.flush()
    return check_tool
