from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from agent_governance_api.metadata_safety import (
    filter_safe_metadata,
    redact_sensitive_text,
)
from agent_governance_api.models import (
    Agent,
    AuditLog,
    HumanApproval,
    HumanApprovalStatus,
    PolicyDecision,
    PolicyDecisionValue,
    TraceEventRecord,
    TraceEventType,
)
from agent_governance_api.schemas import AgentActivityItemRead


def build_agent_activity(
    session: Session,
    *,
    agent: Agent,
) -> list[AgentActivityItemRead]:
    human_approvals = _load_human_approvals(session, agent.id)
    items = [
        *[
            _trace_event_activity_item(trace_event)
            for trace_event in _load_trace_events(session, agent.id)
        ],
        *[
            _policy_decision_activity_item(policy_decision)
            for policy_decision in _load_policy_decisions(session, agent.id)
        ],
        *[
            _human_approval_activity_item(human_approval)
            for human_approval in human_approvals
        ],
        *[
            _audit_log_activity_item(audit_log)
            for audit_log in _load_agent_audit_logs(
                session,
                agent.id,
                human_approvals=human_approvals,
            )
        ],
    ]
    return sorted(
        items,
        key=lambda item: (item.timestamp, str(item.id)),
        reverse=True,
    )


def _load_trace_events(session: Session, agent_id: UUID) -> list[TraceEventRecord]:
    statement = select(TraceEventRecord).where(TraceEventRecord.agent_id == agent_id)
    return list(session.scalars(statement).all())


def _load_policy_decisions(session: Session, agent_id: UUID) -> list[PolicyDecision]:
    statement = select(PolicyDecision).where(PolicyDecision.agent_id == agent_id)
    return list(session.scalars(statement).all())


def _load_human_approvals(session: Session, agent_id: UUID) -> list[HumanApproval]:
    statement = select(HumanApproval).where(HumanApproval.agent_id == agent_id)
    return list(session.scalars(statement).all())


def _load_agent_audit_logs(
    session: Session,
    agent_id: UUID,
    *,
    human_approvals: list[HumanApproval],
) -> list[AuditLog]:
    related_conditions = [
        and_(
            AuditLog.entity_type == "agent",
            AuditLog.entity_id == str(agent_id),
        )
    ]
    human_approval_entity_ids = [
        str(human_approval.id) for human_approval in human_approvals
    ]
    if human_approval_entity_ids:
        related_conditions.append(
            and_(
                AuditLog.entity_type == "human_approval",
                AuditLog.entity_id.in_(human_approval_entity_ids),
            )
        )

    statement = select(AuditLog).where(or_(*related_conditions))
    return list(session.scalars(statement).all())


def _trace_event_activity_item(
    trace_event: TraceEventRecord,
) -> AgentActivityItemRead:
    related_ids = _related_ids(
        trace_event_id=trace_event.id,
        run_id=trace_event.run_id,
    )
    return AgentActivityItemRead(
        id=trace_event.id,
        type="trace_event",
        timestamp=trace_event.timestamp,
        title=f"Trace event: {_display_value(trace_event.event_type)}",
        summary=_safe_text(trace_event.summary),
        severity=_trace_event_severity(trace_event),
        trace_event_id=trace_event.id,
        run_id=trace_event.run_id,
        related_ids=related_ids,
        metadata=filter_safe_metadata(trace_event.metadata_),
    )


def _policy_decision_activity_item(
    policy_decision: PolicyDecision,
) -> AgentActivityItemRead:
    related_ids = _related_ids(
        trace_event_id=policy_decision.trace_event_id,
        policy_decision_id=policy_decision.id,
    )
    return AgentActivityItemRead(
        id=policy_decision.id,
        type="policy_decision",
        timestamp=policy_decision.created_at,
        title=f"Policy decision: {_display_value(policy_decision.decision)}",
        summary=_safe_text(policy_decision.reason),
        severity=_policy_decision_severity(policy_decision),
        trace_event_id=policy_decision.trace_event_id,
        policy_decision_id=policy_decision.id,
        related_ids=related_ids,
    )


def _human_approval_activity_item(
    human_approval: HumanApproval,
) -> AgentActivityItemRead:
    related_ids = _related_ids(
        policy_decision_id=human_approval.policy_decision_id,
        human_approval_id=human_approval.id,
    )
    return AgentActivityItemRead(
        id=human_approval.id,
        type="human_approval",
        timestamp=human_approval.created_at,
        title=f"Human approval: {_display_value(human_approval.status)}",
        summary=_human_approval_summary(human_approval),
        severity=_human_approval_severity(human_approval),
        policy_decision_id=human_approval.policy_decision_id,
        human_approval_id=human_approval.id,
        related_ids=related_ids,
    )


def _audit_log_activity_item(audit_log: AuditLog) -> AgentActivityItemRead:
    safe_metadata = filter_safe_metadata(audit_log.metadata_)
    trace_event_id = _metadata_uuid(safe_metadata, "trace_event_id")
    policy_decision_id = _metadata_uuid(safe_metadata, "policy_decision_id")
    human_approval_id = _audit_log_human_approval_id(audit_log) or _metadata_uuid(
        safe_metadata,
        "human_approval_id",
    )
    run_id = _metadata_uuid(safe_metadata, "run_id")
    related_ids = _related_ids(
        trace_event_id=trace_event_id,
        policy_decision_id=policy_decision_id,
        human_approval_id=human_approval_id,
        audit_log_id=audit_log.id,
        run_id=run_id,
    )
    return AgentActivityItemRead(
        id=audit_log.id,
        type="audit_log",
        timestamp=audit_log.created_at,
        title=f"Audit log: {_display_value(audit_log.event_type)}",
        summary=_safe_text(audit_log.summary),
        severity=_audit_log_severity(audit_log),
        trace_event_id=trace_event_id,
        policy_decision_id=policy_decision_id,
        human_approval_id=human_approval_id,
        audit_log_id=audit_log.id,
        run_id=run_id,
        related_ids=related_ids,
        metadata=safe_metadata,
    )


def _human_approval_summary(human_approval: HumanApproval) -> str:
    summary = human_approval.decision_note or human_approval.reason
    if summary:
        return _safe_text(summary)
    return f"Human approval status is {human_approval.status.value}."


def _audit_log_human_approval_id(audit_log: AuditLog) -> UUID | None:
    if audit_log.entity_type != "human_approval":
        return None
    return _parse_uuid(audit_log.entity_id)


def _metadata_uuid(metadata: dict[str, object], key: str) -> UUID | None:
    return _parse_uuid(metadata.get(key))


def _related_ids(**ids: UUID | None) -> dict[str, UUID]:
    return {key: value for key, value in ids.items() if value is not None}


def _trace_event_severity(trace_event: TraceEventRecord) -> str:
    if trace_event.event_type is TraceEventType.ERROR:
        return "error"
    if trace_event.event_type in {
        TraceEventType.TOOL_CALL_DENIED,
        TraceEventType.HUMAN_REVIEW_REQUESTED,
    }:
        return "warning"
    return "info"


def _policy_decision_severity(policy_decision: PolicyDecision) -> str:
    if policy_decision.decision in {
        PolicyDecisionValue.DENY,
        PolicyDecisionValue.REQUIRE_HUMAN_REVIEW,
    }:
        return "warning"
    return "info"


def _human_approval_severity(human_approval: HumanApproval) -> str:
    if human_approval.status in {
        HumanApprovalStatus.REJECTED,
        HumanApprovalStatus.EXPIRED,
        HumanApprovalStatus.CANCELLED,
    }:
        return "warning"
    return "info"


def _audit_log_severity(audit_log: AuditLog) -> str:
    event_type = audit_log.event_type.lower()
    if "error" in event_type or "failed" in event_type:
        return "error"
    if any(term in event_type for term in ("denied", "rejected", "cancelled")):
        return "warning"
    return "info"


def _parse_uuid(value: object) -> UUID | None:
    if not isinstance(value, str):
        return None
    try:
        return UUID(value)
    except ValueError:
        return None


def _safe_text(value: str) -> str:
    return redact_sensitive_text(value)


def _display_value(value: object) -> str:
    raw_value = getattr(value, "value", value)
    return str(raw_value).replace("_", " ").title()
