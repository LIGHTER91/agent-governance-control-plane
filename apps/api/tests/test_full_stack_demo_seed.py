import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy import event as sqlalchemy_event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from agent_governance_api.activity import build_agent_activity
from agent_governance_api.database import Base
from agent_governance_api.evidence import build_agent_evidence_bundle
from agent_governance_api.full_stack_demo_seed import (
    DEMO_AGENT_ID,
    DEMO_HUMAN_APPROVAL_AUDIT_LOG_ID,
    DEMO_HUMAN_APPROVAL_ID,
    DEMO_POLICY_DECISION_ID,
    DEMO_POLICY_ID,
    DEMO_POLICY_RULE_ID,
    DEMO_TOOL_NAME,
    format_full_stack_demo_seed_result,
    seed_full_stack_demo,
)
from agent_governance_api.models import (
    Agent,
    AgentRunRecord,
    AuditLog,
    HumanApproval,
    HumanApprovalStatus,
    Policy,
    PolicyDecision,
    PolicyDecisionValue,
    PolicyRule,
    PolicyStatus,
    TraceEventRecord,
    TraceEventType,
)

API_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture()
def session() -> Iterator[Session]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @sqlalchemy_event.listens_for(engine, "connect")
    def enable_foreign_keys(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    session_factory = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )
    try:
        with session_factory() as db_session:
            yield db_session
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_seed_full_stack_demo_creates_safe_backend_demo_chain(
    session: Session,
) -> None:
    result = seed_full_stack_demo(session, dry_run=False)

    assert result.created == (
        "agent",
        "policy",
        "policy_rule",
        "agent_run",
        "trace_event",
        "policy_decision",
        "human_approval",
        "agent_audit_log",
        "human_approval_audit_log",
    )
    assert result.reused == ()

    agent = session.get(Agent, DEMO_AGENT_ID)
    assert agent is not None
    assert agent.owner_contact_email is None

    policy = session.get(Policy, DEMO_POLICY_ID)
    assert policy is not None
    assert policy.status is PolicyStatus.ACTIVE

    rule = session.get(PolicyRule, DEMO_POLICY_RULE_ID)
    assert rule is not None
    assert DEMO_TOOL_NAME in rule.condition

    trace_event = session.scalar(select(TraceEventRecord))
    assert trace_event is not None
    assert trace_event.event_type is TraceEventType.TOOL_CALL_REQUESTED
    assert trace_event.metadata_ == {
        "tool_name": DEMO_TOOL_NAME,
        "action_type": "demo_review_action",
        "purpose": "local_full_stack_demo",
    }

    decision = session.get(PolicyDecision, DEMO_POLICY_DECISION_ID)
    assert decision is not None
    assert decision.policy_id == DEMO_POLICY_ID
    assert decision.rule_id == DEMO_POLICY_RULE_ID
    assert decision.trace_event_id == trace_event.id
    assert decision.decision is PolicyDecisionValue.REQUIRE_HUMAN_REVIEW

    approval = session.get(HumanApproval, DEMO_HUMAN_APPROVAL_ID)
    assert approval is not None
    assert approval.status is HumanApprovalStatus.PENDING
    assert approval.policy_decision_id == DEMO_POLICY_DECISION_ID

    approval_audit_log = session.get(AuditLog, DEMO_HUMAN_APPROVAL_AUDIT_LOG_ID)
    assert approval_audit_log is not None
    assert approval_audit_log.metadata_ == {
        "agent_id": str(DEMO_AGENT_ID),
        "policy_decision_id": str(DEMO_POLICY_DECISION_ID),
        "status": "pending",
    }


def test_seed_full_stack_demo_populates_activity_and_evidence_bundle(
    session: Session,
) -> None:
    seed_full_stack_demo(session, dry_run=False)
    agent = session.get(Agent, DEMO_AGENT_ID)
    assert agent is not None

    activity_items = build_agent_activity(session, agent=agent)
    assert {item.type for item in activity_items} == {
        "trace_event",
        "policy_decision",
        "human_approval",
        "audit_log",
    }

    evidence_bundle = build_agent_evidence_bundle(session, agent=agent)
    assert evidence_bundle.agent.id == DEMO_AGENT_ID
    assert len(evidence_bundle.agent_runs) == 1
    assert len(evidence_bundle.trace_events) == 1
    assert len(evidence_bundle.policy_decisions) == 1
    assert len(evidence_bundle.human_approvals) == 1
    assert len(evidence_bundle.audit_logs) == 2
    assert evidence_bundle.policy_decisions[0].policy is not None
    assert evidence_bundle.policy_decisions[0].rule is not None


def test_seed_full_stack_demo_is_idempotent(session: Session) -> None:
    seed_full_stack_demo(session, dry_run=False)
    result = seed_full_stack_demo(session, dry_run=False)

    assert result.created == ()
    assert result.reused == (
        "agent",
        "policy",
        "policy_rule",
        "agent_run",
        "trace_event",
        "policy_decision",
        "human_approval",
        "agent_audit_log",
        "human_approval_audit_log",
    )
    assert session.scalar(select(func.count()).select_from(Agent)) == 1
    assert session.scalar(select(func.count()).select_from(Policy)) == 1
    assert session.scalar(select(func.count()).select_from(PolicyRule)) == 1
    assert session.scalar(select(func.count()).select_from(AgentRunRecord)) == 1
    assert session.scalar(select(func.count()).select_from(TraceEventRecord)) == 1
    assert session.scalar(select(func.count()).select_from(PolicyDecision)) == 1
    assert session.scalar(select(func.count()).select_from(HumanApproval)) == 1
    assert session.scalar(select(func.count()).select_from(AuditLog)) == 2


def test_seed_full_stack_demo_dry_run_does_not_write(session: Session) -> None:
    result = seed_full_stack_demo(session, dry_run=True)

    assert result.dry_run is True
    assert result.created
    assert session.scalar(select(func.count()).select_from(Agent)) == 0
    assert "Run again with --apply" in format_full_stack_demo_seed_result(result)


def test_seed_full_stack_demo_records_do_not_include_unsafe_metadata_keys(
    session: Session,
) -> None:
    seed_full_stack_demo(session, dry_run=False)

    unsafe_parts = ("secret", "token", "credential", "authorization", "raw_payload")
    metadata_values = [
        *session.scalars(select(AgentRunRecord.metadata_)).all(),
        *session.scalars(select(TraceEventRecord.metadata_)).all(),
        *session.scalars(select(AuditLog.metadata_)).all(),
    ]
    metadata_text = repr(metadata_values).lower()
    assert not any(part in metadata_text for part in unsafe_parts)


def test_seed_full_stack_demo_script_supports_direct_execution_help() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/seed_full_stack_demo.py", "--help"],
        cwd=API_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "Seed safe local-only demo data" in result.stdout
    assert "ModuleNotFoundError" not in result.stderr
