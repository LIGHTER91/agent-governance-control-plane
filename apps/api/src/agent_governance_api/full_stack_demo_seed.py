from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy.orm import Session

from agent_governance_api.models import (
    ActorType,
    Agent,
    AgentRunRecord,
    AgentStatus,
    AuditLog,
    Environment,
    HumanApproval,
    HumanApprovalStatus,
    OwnerType,
    Policy,
    PolicyDecision,
    PolicyDecisionValue,
    PolicyRule,
    PolicyStatus,
    RiskLevel,
    TraceEventRecord,
    TraceEventType,
)

DEMO_AGENT_ID = UUID("00000000-0000-4000-8000-000000000101")
DEMO_POLICY_ID = UUID("00000000-0000-4000-8000-000000000201")
DEMO_POLICY_RULE_ID = UUID("00000000-0000-4000-8000-000000000301")
DEMO_AGENT_RUN_RECORD_ID = UUID("00000000-0000-4000-8000-000000000401")
DEMO_RUN_ID = UUID("00000000-0000-4000-8000-000000000402")
DEMO_TRACE_EVENT_ID = UUID("00000000-0000-4000-8000-000000000501")
DEMO_POLICY_DECISION_ID = UUID("00000000-0000-4000-8000-000000000601")
DEMO_HUMAN_APPROVAL_ID = UUID("00000000-0000-4000-8000-000000000701")
DEMO_AGENT_AUDIT_LOG_ID = UUID("00000000-0000-4000-8000-000000000801")
DEMO_HUMAN_APPROVAL_AUDIT_LOG_ID = UUID("00000000-0000-4000-8000-000000000802")
DEMO_BASE_TIME = datetime(2026, 1, 15, 10, 0, tzinfo=UTC)
DEMO_TOOL_NAME = "local_demo_review_tool"
DEMO_CORRELATION_ID = "local-full-stack-demo"
DEMO_ACTOR_ID = "development:local-demo-seed"


@dataclass(frozen=True, slots=True)
class FullStackDemoSeedResult:
    dry_run: bool
    created: tuple[str, ...]
    reused: tuple[str, ...]
    agent_id: UUID
    policy_id: UUID
    policy_rule_id: UUID
    run_id: UUID
    trace_event_id: UUID
    policy_decision_id: UUID
    human_approval_id: UUID


def seed_full_stack_demo(
    session: Session,
    *,
    dry_run: bool = True,
) -> FullStackDemoSeedResult:
    created: list[str] = []
    reused: list[str] = []

    def ensure(name: str, model: type[object], object_id: UUID) -> bool:
        if session.get(model, object_id) is not None:
            reused.append(name)
            return False
        created.append(name)
        return True

    if ensure("agent", Agent, DEMO_AGENT_ID) and not dry_run:
        session.add(_demo_agent())
        session.flush()

    if ensure("policy", Policy, DEMO_POLICY_ID) and not dry_run:
        session.add(_demo_policy())
        session.flush()

    if ensure("policy_rule", PolicyRule, DEMO_POLICY_RULE_ID) and not dry_run:
        session.add(_demo_policy_rule())
        session.flush()

    if ensure("agent_run", AgentRunRecord, DEMO_AGENT_RUN_RECORD_ID) and not dry_run:
        session.add(_demo_agent_run())
        session.flush()

    if ensure("trace_event", TraceEventRecord, DEMO_TRACE_EVENT_ID) and not dry_run:
        session.add(_demo_trace_event())
        session.flush()

    if (
        ensure("policy_decision", PolicyDecision, DEMO_POLICY_DECISION_ID)
        and not dry_run
    ):
        session.add(_demo_policy_decision())
        session.flush()

    if ensure("human_approval", HumanApproval, DEMO_HUMAN_APPROVAL_ID) and not dry_run:
        session.add(_demo_human_approval())
        session.flush()

    if ensure("agent_audit_log", AuditLog, DEMO_AGENT_AUDIT_LOG_ID) and not dry_run:
        session.add(_demo_agent_audit_log())
        session.flush()

    if (
        ensure("human_approval_audit_log", AuditLog, DEMO_HUMAN_APPROVAL_AUDIT_LOG_ID)
        and not dry_run
    ):
        session.add(_demo_human_approval_audit_log())
        session.flush()

    if not dry_run:
        session.commit()

    return FullStackDemoSeedResult(
        dry_run=dry_run,
        created=tuple(created),
        reused=tuple(reused),
        agent_id=DEMO_AGENT_ID,
        policy_id=DEMO_POLICY_ID,
        policy_rule_id=DEMO_POLICY_RULE_ID,
        run_id=DEMO_RUN_ID,
        trace_event_id=DEMO_TRACE_EVENT_ID,
        policy_decision_id=DEMO_POLICY_DECISION_ID,
        human_approval_id=DEMO_HUMAN_APPROVAL_ID,
    )


def format_full_stack_demo_seed_result(result: FullStackDemoSeedResult) -> str:
    mode = "DRY RUN" if result.dry_run else "APPLIED"
    lines = [
        f"Local full-stack demo seed: {mode}",
        f"created={_format_items(result.created)}",
        f"reused={_format_items(result.reused)}",
        f"agent_id={result.agent_id}",
        f"policy_id={result.policy_id}",
        f"policy_rule_id={result.policy_rule_id}",
        f"run_id={result.run_id}",
        f"trace_event_id={result.trace_event_id}",
        f"policy_decision_id={result.policy_decision_id}",
        f"human_approval_id={result.human_approval_id}",
    ]
    if result.dry_run:
        lines.append("Run again with --apply to write local demo records.")
    else:
        lines.append("Open the frontend at /agents to review the demo chain.")
    return "\n".join(lines)


def _demo_agent() -> Agent:
    return Agent(
        id=DEMO_AGENT_ID,
        name="Local Demo Review Agent",
        description=(
            "Safe local demo agent for exercising the full-stack governance UI."
        ),
        owner_type=OwnerType.TEAM,
        owner_id="team:local-governance",
        owner_name="Local Governance Team",
        owner_contact_email=None,
        environment=Environment.DEVELOPMENT,
        status=AgentStatus.ACTIVE,
        risk_level=RiskLevel.MEDIUM,
        framework="LangGraph-style demo",
        created_at=DEMO_BASE_TIME,
        updated_at=DEMO_BASE_TIME,
    )


def _demo_policy() -> Policy:
    return Policy(
        id=DEMO_POLICY_ID,
        name="Local demo runtime review policy",
        description=("Requires human review for the safe local demo tool action."),
        status=PolicyStatus.ACTIVE,
        created_at=DEMO_BASE_TIME + timedelta(minutes=1),
        updated_at=DEMO_BASE_TIME + timedelta(minutes=1),
    )


def _demo_policy_rule() -> PolicyRule:
    return PolicyRule(
        id=DEMO_POLICY_RULE_ID,
        policy_id=DEMO_POLICY_ID,
        name="Require review for local demo tool",
        description="Matches only the local demo tool name.",
        condition=json.dumps(
            {
                "tool_name": DEMO_TOOL_NAME,
                "decision": PolicyDecisionValue.REQUIRE_HUMAN_REVIEW.value,
                "reason": "Local demo tool use requires human review.",
            },
            sort_keys=True,
        ),
        created_at=DEMO_BASE_TIME + timedelta(minutes=2),
        updated_at=DEMO_BASE_TIME + timedelta(minutes=2),
    )


def _demo_agent_run() -> AgentRunRecord:
    return AgentRunRecord(
        id=DEMO_AGENT_RUN_RECORD_ID,
        agent_id=DEMO_AGENT_ID,
        run_id=DEMO_RUN_ID,
        correlation_id=DEMO_CORRELATION_ID,
        environment=Environment.DEVELOPMENT,
        status="observed",
        started_at=DEMO_BASE_TIME + timedelta(minutes=3),
        ended_at=None,
        summary="Local demo runtime event observed.",
        metadata_={"demo": "full_stack", "runtime_mode": "simulation"},
        created_at=DEMO_BASE_TIME + timedelta(minutes=3),
    )


def _demo_trace_event() -> TraceEventRecord:
    return TraceEventRecord(
        id=DEMO_TRACE_EVENT_ID,
        agent_id=DEMO_AGENT_ID,
        run_id=DEMO_RUN_ID,
        external_event_id="local-demo-tool-call-requested",
        correlation_id=DEMO_CORRELATION_ID,
        event_type=TraceEventType.TOOL_CALL_REQUESTED,
        timestamp=DEMO_BASE_TIME + timedelta(minutes=4),
        summary="Local demo agent requested a governed tool action.",
        metadata_={
            "tool_name": DEMO_TOOL_NAME,
            "action_type": "demo_review_action",
            "purpose": "local_full_stack_demo",
        },
        created_at=DEMO_BASE_TIME + timedelta(minutes=4),
    )


def _demo_policy_decision() -> PolicyDecision:
    return PolicyDecision(
        id=DEMO_POLICY_DECISION_ID,
        agent_id=DEMO_AGENT_ID,
        policy_id=DEMO_POLICY_ID,
        rule_id=DEMO_POLICY_RULE_ID,
        trace_event_id=DEMO_TRACE_EVENT_ID,
        decision=PolicyDecisionValue.REQUIRE_HUMAN_REVIEW,
        reason="Local demo tool use requires human review.",
        context_hash=None,
        created_at=DEMO_BASE_TIME + timedelta(minutes=5),
    )


def _demo_human_approval() -> HumanApproval:
    return HumanApproval(
        id=DEMO_HUMAN_APPROVAL_ID,
        agent_id=DEMO_AGENT_ID,
        policy_decision_id=DEMO_POLICY_DECISION_ID,
        status=HumanApprovalStatus.PENDING,
        requested_by_actor_type=ActorType.DEVELOPMENT,
        requested_by_actor_id=DEMO_ACTOR_ID,
        reason="Review the local demo governed tool request.",
        decision_note=None,
        reviewed_by_actor_type=None,
        reviewed_by_actor_id=None,
        reviewed_at=None,
        expires_at=None,
        created_at=DEMO_BASE_TIME + timedelta(minutes=6),
    )


def _demo_agent_audit_log() -> AuditLog:
    return AuditLog(
        id=DEMO_AGENT_AUDIT_LOG_ID,
        event_type="agent_seeded_for_local_demo",
        actor_type=ActorType.DEVELOPMENT,
        actor_id=DEMO_ACTOR_ID,
        entity_type="agent",
        entity_id=str(DEMO_AGENT_ID),
        summary="Local demo agent seeded for full-stack review.",
        metadata_={"agent_id": str(DEMO_AGENT_ID), "demo": "full_stack"},
        created_at=DEMO_BASE_TIME + timedelta(minutes=7),
    )


def _demo_human_approval_audit_log() -> AuditLog:
    return AuditLog(
        id=DEMO_HUMAN_APPROVAL_AUDIT_LOG_ID,
        event_type="human_approval_requested",
        actor_type=ActorType.DEVELOPMENT,
        actor_id=DEMO_ACTOR_ID,
        entity_type="human_approval",
        entity_id=str(DEMO_HUMAN_APPROVAL_ID),
        summary="Human approval requested for the local demo tool action.",
        metadata_={
            "agent_id": str(DEMO_AGENT_ID),
            "policy_decision_id": str(DEMO_POLICY_DECISION_ID),
            "status": HumanApprovalStatus.PENDING.value,
        },
        created_at=DEMO_BASE_TIME + timedelta(minutes=8),
    )


def _format_items(items: tuple[str, ...]) -> str:
    if not items:
        return "none"
    return ",".join(items)
