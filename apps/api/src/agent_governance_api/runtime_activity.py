from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from agent_governance_api.metadata_safety import (
    filter_safe_metadata,
    redact_sensitive_text,
)
from agent_governance_api.models import (
    AgentRunRecord,
    HumanApproval,
    PolicyDecision,
    PolicyDecisionValue,
    TraceEventRecord,
    TraceEventType,
)
from agent_governance_api.runtime_gateway import (
    RuntimeDecisionMode,
    RuntimeToolCallActivityItem,
    RuntimeToolCallActivityType,
)

SIMULATED_RUN_STATUS = "simulated"
ENFORCED_RUN_STATUS = "enforced"
RUNTIME_TOOL_CALL_ACTIVITY_EVENT_TYPES = (
    TraceEventType.TOOL_CALL_REQUESTED,
    TraceEventType.TOOL_CALL_RESUME_REQUESTED,
)


def build_runtime_tool_call_activity(
    session: Session,
) -> list[RuntimeToolCallActivityItem]:
    """Build Runtime Gateway tool-call activity sorted newest first."""

    items = [
        item
        for trace_event in _load_runtime_trace_events(session)
        if (item := _runtime_activity_item(session, trace_event)) is not None
    ]
    return sorted(
        items,
        key=lambda item: (item.timestamp, str(item.trace_event_id)),
        reverse=True,
    )


def _load_runtime_trace_events(session: Session) -> list[TraceEventRecord]:
    statement = (
        select(TraceEventRecord)
        .where(TraceEventRecord.event_type.in_(RUNTIME_TOOL_CALL_ACTIVITY_EVENT_TYPES))
        .order_by(TraceEventRecord.timestamp.desc(), TraceEventRecord.id.desc())
    )
    return list(session.scalars(statement).all())


def _runtime_activity_item(
    session: Session,
    trace_event: TraceEventRecord,
) -> RuntimeToolCallActivityItem | None:
    if trace_event.event_type is TraceEventType.TOOL_CALL_REQUESTED:
        return _runtime_decision_activity_item(session, trace_event)
    if trace_event.event_type is TraceEventType.TOOL_CALL_RESUME_REQUESTED:
        return _runtime_resume_activity_item(trace_event)
    return None


def _runtime_decision_activity_item(
    session: Session,
    trace_event: TraceEventRecord,
) -> RuntimeToolCallActivityItem | None:
    run = _agent_run_for_trace_event(session, trace_event)

    safe_metadata = filter_safe_metadata(trace_event.metadata_)
    policy_decision = _policy_decision_for_trace_event(session, trace_event)
    human_approval = (
        _human_approval_for_policy_decision(session, policy_decision)
        if policy_decision is not None
        else None
    )
    decision = policy_decision.decision if policy_decision is not None else None
    proceed = _proceed_for_decision(decision) if decision is not None else None
    reason = _safe_text(policy_decision.reason) if policy_decision is not None else None

    if decision is None and _is_record_only_policy_evaluation_failure(safe_metadata):
        decision = PolicyDecisionValue.NOT_APPLICABLE
        proceed = False

    return RuntimeToolCallActivityItem(
        id=trace_event.id,
        type=RuntimeToolCallActivityType.TOOL_CALL_DECISION,
        agent_id=trace_event.agent_id,
        run_id=trace_event.run_id,
        request_id=trace_event.external_event_id,
        timestamp=trace_event.timestamp,
        tool_name=_metadata_str(safe_metadata, "tool_name"),
        mode=_mode_for_run_status(run.status) if run is not None else None,
        decision=decision,
        proceed=proceed,
        reason=reason,
        trace_event_id=trace_event.id,
        policy_decision_id=(
            policy_decision.id if policy_decision is not None else None
        ),
        human_approval_id=human_approval.id if human_approval is not None else None,
        related_ids=_related_ids(
            trace_event_id=trace_event.id,
            policy_decision_id=(
                policy_decision.id if policy_decision is not None else None
            ),
            human_approval_id=(
                human_approval.id if human_approval is not None else None
            ),
            run_id=trace_event.run_id,
        ),
    )


def _runtime_resume_activity_item(
    trace_event: TraceEventRecord,
) -> RuntimeToolCallActivityItem:
    safe_metadata = filter_safe_metadata(trace_event.metadata_)
    policy_decision_id = _metadata_uuid(safe_metadata, "policy_decision_id")
    human_approval_id = _metadata_uuid(safe_metadata, "human_approval_id")
    original_request_id = _metadata_str(safe_metadata, "original_request_id")

    return RuntimeToolCallActivityItem(
        id=trace_event.id,
        type=RuntimeToolCallActivityType.TOOL_CALL_RESUME,
        agent_id=trace_event.agent_id,
        run_id=trace_event.run_id,
        request_id=trace_event.external_event_id,
        timestamp=trace_event.timestamp,
        tool_name=_metadata_str(safe_metadata, "tool_name"),
        mode=None,
        decision=_metadata_policy_decision(safe_metadata, "resume_decision"),
        proceed=_metadata_bool_or_none(safe_metadata, "proceed"),
        reason=_safe_optional_text(_metadata_str(safe_metadata, "resume_reason")),
        trace_event_id=trace_event.id,
        policy_decision_id=policy_decision_id,
        human_approval_id=human_approval_id,
        related_ids=_related_ids(
            trace_event_id=trace_event.id,
            policy_decision_id=policy_decision_id,
            human_approval_id=human_approval_id,
            run_id=trace_event.run_id,
            original_request_id=original_request_id,
        ),
    )


def _agent_run_for_trace_event(
    session: Session,
    trace_event: TraceEventRecord,
) -> AgentRunRecord | None:
    return session.scalar(
        select(AgentRunRecord).where(
            AgentRunRecord.agent_id == trace_event.agent_id,
            AgentRunRecord.run_id == trace_event.run_id,
        )
    )


def _policy_decision_for_trace_event(
    session: Session,
    trace_event: TraceEventRecord,
) -> PolicyDecision | None:
    return session.scalar(
        select(PolicyDecision)
        .where(PolicyDecision.trace_event_id == trace_event.id)
        .order_by(PolicyDecision.created_at.desc(), PolicyDecision.id.desc())
    )


def _human_approval_for_policy_decision(
    session: Session,
    policy_decision: PolicyDecision,
) -> HumanApproval | None:
    return session.scalar(
        select(HumanApproval)
        .where(HumanApproval.policy_decision_id == policy_decision.id)
        .order_by(HumanApproval.created_at.desc(), HumanApproval.id.desc())
    )


def _mode_for_run_status(status: str) -> RuntimeDecisionMode | None:
    if status == SIMULATED_RUN_STATUS:
        return RuntimeDecisionMode.SIMULATION
    if status == ENFORCED_RUN_STATUS:
        return RuntimeDecisionMode.ENFORCEMENT
    return None


def _proceed_for_decision(decision: PolicyDecisionValue) -> bool:
    return decision is PolicyDecisionValue.ALLOW


def _metadata_str(metadata: dict[str, object], key: str) -> str | None:
    value = metadata.get(key)
    if isinstance(value, str) and value.strip():
        return value
    return None


def _metadata_bool_or_none(metadata: dict[str, object], key: str) -> bool | None:
    value = metadata.get(key)
    if isinstance(value, bool):
        return value
    return None


def _metadata_uuid(metadata: dict[str, object], key: str) -> UUID | None:
    value = metadata.get(key)
    if isinstance(value, UUID):
        return value
    if not isinstance(value, str):
        return None
    try:
        return UUID(value)
    except ValueError:
        return None


def _metadata_policy_decision(
    metadata: dict[str, object],
    key: str,
) -> PolicyDecisionValue | None:
    value = metadata.get(key)
    if not isinstance(value, str):
        return None
    try:
        return PolicyDecisionValue(value)
    except ValueError:
        return None


def _is_record_only_policy_evaluation_failure(metadata: dict[str, object]) -> bool:
    return (
        metadata.get("runtime_failure_category") == "policy_evaluation"
        and metadata.get("runtime_failure_default") == "record_only"
    )


def _related_ids(**ids: UUID | str | None) -> dict[str, str]:
    return {key: str(value) for key, value in ids.items() if value is not None}


def _safe_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    return _safe_text(value)


def _safe_text(value: str) -> str:
    return redact_sensitive_text(value)
