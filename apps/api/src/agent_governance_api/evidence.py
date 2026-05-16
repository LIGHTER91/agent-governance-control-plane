from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from agent_governance_api.metadata_safety import filter_safe_metadata
from agent_governance_api.models import (
    Agent,
    AgentRunRecord,
    AuditLog,
    HumanApproval,
    Policy,
    PolicyDecision,
    PolicyRule,
    TraceEventRecord,
)
from agent_governance_api.schemas import (
    AgentRead,
    EvidenceAgentRunRead,
    EvidenceAuditLogRead,
    EvidenceBundleRead,
    EvidenceHumanApprovalRead,
    EvidencePolicyDecisionRead,
    EvidencePolicyReferenceRead,
    EvidencePolicyRuleReferenceRead,
    EvidenceTraceEventRead,
)


def build_agent_evidence_bundle(
    session: Session,
    *,
    agent: Agent,
) -> EvidenceBundleRead:
    agent_runs = _load_agent_runs(session, agent.id)
    trace_events = _load_trace_events(session, agent.id)
    policy_decisions = _load_policy_decisions(session, agent.id)
    human_approvals = _load_human_approvals(session, agent.id)
    audit_logs = _load_agent_audit_logs(
        session,
        agent.id,
        human_approvals=human_approvals,
    )
    policy_references = _load_policy_references(session, policy_decisions)
    rule_references = _load_rule_references(session, policy_decisions)

    return EvidenceBundleRead(
        agent=AgentRead.model_validate(agent),
        audit_logs=[_audit_log_response(audit_log) for audit_log in audit_logs],
        agent_runs=[_agent_run_response(agent_run) for agent_run in agent_runs],
        trace_events=[
            _trace_event_response(trace_event) for trace_event in trace_events
        ],
        policy_decisions=[
            _policy_decision_response(
                policy_decision,
                policy_references=policy_references,
                rule_references=rule_references,
            )
            for policy_decision in policy_decisions
        ],
        human_approvals=[
            _human_approval_response(human_approval)
            for human_approval in human_approvals
        ],
    )


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

    statement = (
        select(AuditLog)
        .where(or_(*related_conditions))
        .order_by(AuditLog.created_at, AuditLog.id)
    )
    return list(session.scalars(statement).all())


def _load_agent_runs(session: Session, agent_id: UUID) -> list[AgentRunRecord]:
    statement = (
        select(AgentRunRecord)
        .where(AgentRunRecord.agent_id == agent_id)
        .order_by(AgentRunRecord.started_at, AgentRunRecord.id)
    )
    return list(session.scalars(statement).all())


def _load_trace_events(session: Session, agent_id: UUID) -> list[TraceEventRecord]:
    statement = (
        select(TraceEventRecord)
        .where(TraceEventRecord.agent_id == agent_id)
        .order_by(TraceEventRecord.timestamp, TraceEventRecord.id)
    )
    return list(session.scalars(statement).all())


def _load_policy_decisions(session: Session, agent_id: UUID) -> list[PolicyDecision]:
    statement = (
        select(PolicyDecision)
        .where(PolicyDecision.agent_id == agent_id)
        .order_by(PolicyDecision.created_at, PolicyDecision.id)
    )
    return list(session.scalars(statement).all())


def _load_human_approvals(session: Session, agent_id: UUID) -> list[HumanApproval]:
    statement = (
        select(HumanApproval)
        .where(HumanApproval.agent_id == agent_id)
        .order_by(HumanApproval.created_at, HumanApproval.id)
    )
    return list(session.scalars(statement).all())


def _load_policy_references(
    session: Session,
    policy_decisions: list[PolicyDecision],
) -> dict[UUID, EvidencePolicyReferenceRead]:
    policy_ids = {
        policy_decision.policy_id
        for policy_decision in policy_decisions
        if policy_decision.policy_id is not None
    }
    if not policy_ids:
        return {}

    statement = select(Policy).where(Policy.id.in_(policy_ids))
    return {
        policy.id: EvidencePolicyReferenceRead(
            id=policy.id,
            name=policy.name,
            status=policy.status,
        )
        for policy in session.scalars(statement).all()
    }


def _load_rule_references(
    session: Session,
    policy_decisions: list[PolicyDecision],
) -> dict[UUID, EvidencePolicyRuleReferenceRead]:
    rule_ids = {
        policy_decision.rule_id
        for policy_decision in policy_decisions
        if policy_decision.rule_id is not None
    }
    if not rule_ids:
        return {}

    statement = select(PolicyRule).where(PolicyRule.id.in_(rule_ids))
    return {
        rule.id: EvidencePolicyRuleReferenceRead(
            id=rule.id,
            policy_id=rule.policy_id,
            name=rule.name,
        )
        for rule in session.scalars(statement).all()
    }


def _audit_log_response(audit_log: AuditLog) -> EvidenceAuditLogRead:
    return EvidenceAuditLogRead(
        id=audit_log.id,
        event_type=audit_log.event_type,
        actor_type=audit_log.actor_type,
        actor_id=audit_log.actor_id,
        entity_type=audit_log.entity_type,
        entity_id=audit_log.entity_id,
        summary=audit_log.summary,
        metadata=filter_safe_metadata(audit_log.metadata_),
        created_at=audit_log.created_at,
    )


def _agent_run_response(agent_run: AgentRunRecord) -> EvidenceAgentRunRead:
    return EvidenceAgentRunRead(
        id=agent_run.id,
        agent_id=agent_run.agent_id,
        run_id=agent_run.run_id,
        correlation_id=agent_run.correlation_id,
        environment=agent_run.environment,
        status=agent_run.status,
        started_at=agent_run.started_at,
        ended_at=agent_run.ended_at,
        summary=agent_run.summary,
        metadata=filter_safe_metadata(agent_run.metadata_),
        created_at=agent_run.created_at,
    )


def _trace_event_response(trace_event: TraceEventRecord) -> EvidenceTraceEventRead:
    return EvidenceTraceEventRead(
        id=trace_event.id,
        agent_id=trace_event.agent_id,
        run_id=trace_event.run_id,
        external_event_id=trace_event.external_event_id,
        correlation_id=trace_event.correlation_id,
        event_type=trace_event.event_type,
        timestamp=trace_event.timestamp,
        summary=trace_event.summary,
        metadata=filter_safe_metadata(trace_event.metadata_),
        created_at=trace_event.created_at,
    )


def _policy_decision_response(
    policy_decision: PolicyDecision,
    *,
    policy_references: dict[UUID, EvidencePolicyReferenceRead],
    rule_references: dict[UUID, EvidencePolicyRuleReferenceRead],
) -> EvidencePolicyDecisionRead:
    policy = (
        policy_references.get(policy_decision.policy_id)
        if policy_decision.policy_id is not None
        else None
    )
    rule = (
        rule_references.get(policy_decision.rule_id)
        if policy_decision.rule_id is not None
        else None
    )

    return EvidencePolicyDecisionRead(
        id=policy_decision.id,
        agent_id=policy_decision.agent_id,
        policy_id=policy_decision.policy_id,
        rule_id=policy_decision.rule_id,
        trace_event_id=policy_decision.trace_event_id,
        decision=policy_decision.decision,
        reason=policy_decision.reason,
        context_hash=policy_decision.context_hash,
        policy=policy,
        rule=rule,
        created_at=policy_decision.created_at,
    )


def _human_approval_response(
    human_approval: HumanApproval,
) -> EvidenceHumanApprovalRead:
    return EvidenceHumanApprovalRead(
        id=human_approval.id,
        agent_id=human_approval.agent_id,
        policy_decision_id=human_approval.policy_decision_id,
        status=human_approval.status,
        requested_by_actor_type=human_approval.requested_by_actor_type,
        requested_by_actor_id=human_approval.requested_by_actor_id,
        reviewed_by_actor_type=human_approval.reviewed_by_actor_type,
        reviewed_by_actor_id=human_approval.reviewed_by_actor_id,
        reason=human_approval.reason,
        decision_note=human_approval.decision_note,
        created_at=human_approval.created_at,
        reviewed_at=human_approval.reviewed_at,
        expires_at=human_approval.expires_at,
    )
