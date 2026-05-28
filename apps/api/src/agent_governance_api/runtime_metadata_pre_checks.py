from collections.abc import Callable
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from agent_governance_api.models import (
    AccessGrantTargetType,
    CheckResult,
    CheckResultTargetType,
    CheckTool,
    CheckToolStatus,
    CheckToolType,
    OwnerType,
    TraceEventRecord,
)
from agent_governance_api.policy_pre_checks import (
    check_access_grant_status,
    check_capability_status,
    check_data_usage_profile_status,
    check_model_asset_status,
    check_source_status,
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


def run_runtime_metadata_pre_checks(
    session: Session,
    *,
    payload: RuntimeToolCallDecisionRequest,
    trace_event: TraceEventRecord,
    policy_decision_id: UUID | None,
) -> list[CheckResult]:
    """Run safe metadata-only runtime checks without changing the decision."""

    results: list[CheckResult] = []
    access_grant_tool: CheckTool | None = None

    def get_access_grant_tool() -> CheckTool | None:
        nonlocal access_grant_tool
        if access_grant_tool is None:
            access_grant_tool = _get_or_create_runtime_check_tool(
                session,
                ACCESS_GRANT_CHECK_TOOL,
            )
        return access_grant_tool

    if payload.capability_id is not None:
        capability_tool = _get_or_create_runtime_check_tool(
            session,
            CAPABILITY_STATUS_CHECK_TOOL,
        )
        _append_checked_result(
            results,
            session=session,
            check_tool=capability_tool,
            target_type=CheckResultTargetType.CAPABILITY,
            target_id=payload.capability_id,
            check_type="capability_status",
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
        _append_access_grant_check(
            results,
            session=session,
            check_tool=get_access_grant_tool(),
            payload=payload,
            trace_event=trace_event,
            policy_decision_id=policy_decision_id,
            target_type=AccessGrantTargetType.CAPABILITY,
            target_id=payload.capability_id,
        )

    for source_id in payload.source_ids:
        source_tool = _get_or_create_runtime_check_tool(
            session,
            SOURCE_STATUS_CHECK_TOOL,
        )
        _append_checked_result(
            results,
            session=session,
            check_tool=source_tool,
            target_type=CheckResultTargetType.SOURCE,
            target_id=source_id,
            check_type="source_status",
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

        data_usage_tool = _get_or_create_runtime_check_tool(
            session,
            DATA_USAGE_PROFILE_CHECK_TOOL,
        )
        _append_checked_result(
            results,
            session=session,
            check_tool=data_usage_tool,
            target_type=CheckResultTargetType.DATA_USAGE_PROFILE,
            target_id=None,
            check_type="data_usage_profile_status",
            agent_id=payload.agent_id,
            run_id=payload.run_id,
            trace_event_id=trace_event.id,
            policy_decision_id=policy_decision_id,
            run_check=(
                lambda check_tool_id, source_id=source_id: (
                    check_data_usage_profile_status(
                        session,
                        check_tool_id=check_tool_id,
                        source_id=source_id,
                        agent_id=payload.agent_id,
                        run_id=payload.run_id,
                        trace_event_id=trace_event.id,
                        policy_decision_id=policy_decision_id,
                    )
                )
            ),
        )

        _append_access_grant_check(
            results,
            session=session,
            check_tool=get_access_grant_tool(),
            payload=payload,
            trace_event=trace_event,
            policy_decision_id=policy_decision_id,
            target_type=AccessGrantTargetType.SOURCE,
            target_id=source_id,
        )

    if payload.model_id is not None:
        model_tool = _get_or_create_runtime_check_tool(
            session,
            MODEL_ASSET_STATUS_CHECK_TOOL,
        )
        _append_checked_result(
            results,
            session=session,
            check_tool=model_tool,
            target_type=CheckResultTargetType.MODEL_ASSET,
            target_id=payload.model_id,
            check_type="model_asset_status",
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
        _append_access_grant_check(
            results,
            session=session,
            check_tool=get_access_grant_tool(),
            payload=payload,
            trace_event=trace_event,
            policy_decision_id=policy_decision_id,
            target_type=AccessGrantTargetType.MODEL_ASSET,
            target_id=payload.model_id,
        )

    return results


def _append_access_grant_check(
    results: list[CheckResult],
    *,
    session: Session,
    check_tool: CheckTool | None,
    payload: RuntimeToolCallDecisionRequest,
    trace_event: TraceEventRecord,
    policy_decision_id: UUID | None,
    target_type: AccessGrantTargetType,
    target_id: UUID,
) -> None:
    _append_checked_result(
        results,
        session=session,
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
    check_tool: CheckTool | None,
    target_type: CheckResultTargetType,
    target_id: UUID | None,
    check_type: str,
    agent_id: UUID,
    run_id: UUID,
    trace_event_id: UUID,
    policy_decision_id: UUID | None,
    run_check: Callable[[UUID], CheckResult],
) -> None:
    if check_tool is None:
        return

    try:
        results.append(run_check(check_tool.id))
    except Exception:
        results.append(
            record_metadata_check_error(
                session,
                check_tool_id=check_tool.id,
                agent_id=agent_id,
                run_id=run_id,
                trace_event_id=trace_event_id,
                policy_decision_id=policy_decision_id,
                target_type=target_type,
                target_id=target_id,
                summary="Runtime metadata-only pre-check failed.",
                reason=(
                    "The metadata-only helper failed before completing. "
                    "No raw runtime payload was stored."
                ),
                metadata={"check_type": f"{check_type}_error"},
            )
        )


def _get_or_create_runtime_check_tool(
    session: Session,
    spec: RuntimeMetadataPreCheckToolSpec,
) -> CheckTool | None:
    check_tool = session.scalar(select(CheckTool).where(CheckTool.name == spec.name))
    if check_tool is not None:
        if check_tool.status is not CheckToolStatus.ACTIVE:
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
