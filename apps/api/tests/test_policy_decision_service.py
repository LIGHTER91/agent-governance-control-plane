from collections.abc import Iterator
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from agent_governance_api.database import Base
from agent_governance_api.models import (
    Agent,
    AgentRunRecord,
    AgentStatus,
    Environment,
    OwnerType,
    PolicyDecision,
    PolicyDecisionValue,
    RiskLevel,
    TraceEventRecord,
    TraceEventType,
)
from agent_governance_api.policy_decision_service import persist_policy_decision
from agent_governance_api.policy_evaluator import PolicyEvaluationResult


@pytest.fixture()
def session() -> Iterator[Session]:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    try:
        with Session(engine) as session:
            yield session
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_persists_allow_decision(session: Session) -> None:
    agent = add_agent(session)
    result = policy_result(
        decision=PolicyDecisionValue.ALLOW,
        reason="The requested tool is allowed.",
    )

    decision = persist_policy_decision(
        session,
        agent_id=agent.id,
        evaluation_result=result,
        context_hash="sha256:allow-context",
    )

    [saved_decision] = fetch_policy_decisions(session)
    assert saved_decision.id == decision.id
    assert saved_decision.agent_id == agent.id
    assert saved_decision.decision is PolicyDecisionValue.ALLOW
    assert saved_decision.reason == "The requested tool is allowed."
    assert saved_decision.trace_event_id is None
    assert saved_decision.context_hash == "sha256:allow-context"


def test_persists_deny_decision(session: Session) -> None:
    agent = add_agent(session)
    result = policy_result(
        decision=PolicyDecisionValue.DENY,
        reason="The requested tool is denied.",
    )

    decision = persist_policy_decision(
        session,
        agent_id=agent.id,
        evaluation_result=result,
    )

    assert decision.decision is PolicyDecisionValue.DENY
    assert decision.reason == "The requested tool is denied."
    assert fetch_policy_decisions(session) == [decision]


def test_persists_require_human_review_decision(session: Session) -> None:
    agent = add_agent(session)
    result = policy_result(
        decision=PolicyDecisionValue.REQUIRE_HUMAN_REVIEW,
        reason="Human review is required.",
    )

    decision = persist_policy_decision(
        session,
        agent_id=agent.id,
        evaluation_result=result,
    )

    assert decision.decision is PolicyDecisionValue.REQUIRE_HUMAN_REVIEW
    assert decision.reason == "Human review is required."
    assert fetch_policy_decisions(session) == [decision]


def test_persists_not_applicable_decision(session: Session) -> None:
    agent = add_agent(session)
    result = policy_result(
        decision=PolicyDecisionValue.NOT_APPLICABLE,
        reason="No policy rule matched the request.",
    )

    decision = persist_policy_decision(
        session,
        agent_id=agent.id,
        evaluation_result=result,
    )

    assert decision.decision is PolicyDecisionValue.NOT_APPLICABLE
    assert decision.reason == "No policy rule matched the request."
    assert decision.policy_id is None
    assert decision.rule_id is None
    assert fetch_policy_decisions(session) == [decision]


def test_preserves_policy_and_rule_ids_when_available(session: Session) -> None:
    agent = add_agent(session)
    policy_id = uuid4()
    rule_id = uuid4()
    result = policy_result(
        decision=PolicyDecisionValue.DENY,
        reason="Matched persisted rule.",
        policy_id=policy_id,
        rule_id=rule_id,
    )

    decision = persist_policy_decision(
        session,
        agent_id=agent.id,
        evaluation_result=result,
    )

    assert decision.policy_id == policy_id
    assert decision.rule_id == rule_id


def test_preserves_trace_event_id_when_available(session: Session) -> None:
    agent = add_agent(session)
    trace_event = add_trace_event(session, agent)
    result = policy_result(
        decision=PolicyDecisionValue.DENY,
        reason="Matched telemetry event.",
    )

    decision = persist_policy_decision(
        session,
        agent_id=agent.id,
        evaluation_result=result,
        trace_event_id=trace_event.id,
    )

    assert decision.trace_event_id == trace_event.id


def test_optional_policy_and_rule_ids_override_result_values(session: Session) -> None:
    agent = add_agent(session)
    result_policy_id = uuid4()
    result_rule_id = uuid4()
    override_policy_id = uuid4()
    override_rule_id = uuid4()
    result = policy_result(
        decision=PolicyDecisionValue.ALLOW,
        reason="Matched rule with override.",
        policy_id=result_policy_id,
        rule_id=result_rule_id,
    )

    decision = persist_policy_decision(
        session,
        agent_id=agent.id,
        evaluation_result=result,
        policy_id=override_policy_id,
        rule_id=override_rule_id,
    )

    assert decision.policy_id == override_policy_id
    assert decision.rule_id == override_rule_id


def test_rejects_raw_sensitive_payload_in_context_hash(session: Session) -> None:
    agent = add_agent(session)
    result = policy_result(
        decision=PolicyDecisionValue.DENY,
        reason="Sensitive context must not be stored.",
    )

    with pytest.raises(
        ValueError,
        match="PolicyDecision context_hash must not contain raw sensitive payloads.",
    ):
        persist_policy_decision(
            session,
            agent_id=agent.id,
            evaluation_result=result,
            context_hash="api_key=raw-secret-value",
        )

    assert fetch_policy_decisions(session) == []


def test_caller_controls_commit_or_rollback(session: Session) -> None:
    agent = add_agent(session)
    result = policy_result(
        decision=PolicyDecisionValue.ALLOW,
        reason="The requested tool is allowed.",
    )

    decision = persist_policy_decision(
        session,
        agent_id=agent.id,
        evaluation_result=result,
    )

    assert decision.id is not None
    assert fetch_policy_decisions(session) == [decision]

    session.rollback()

    assert fetch_policy_decisions(session) == []


def add_agent(session: Session) -> Agent:
    agent = Agent(
        name="Support assistant",
        description=None,
        owner_type=OwnerType.TEAM,
        owner_id="team:ai-platform",
        owner_name="AI Platform",
        owner_contact_email="owner@example.com",
        environment=Environment.DEVELOPMENT,
        status=AgentStatus.DRAFT,
        risk_level=RiskLevel.LOW,
        framework="LangGraph",
    )
    session.add(agent)
    session.commit()
    return agent


def add_trace_event(session: Session, agent: Agent) -> TraceEventRecord:
    run_id = uuid4()
    run = AgentRunRecord(
        agent_id=agent.id,
        run_id=run_id,
        correlation_id="corr-123",
        environment=Environment.DEVELOPMENT,
        status="started",
        started_at=datetime.now(UTC),
        summary="Agent run started.",
        metadata_={},
    )
    trace_event = TraceEventRecord(
        agent_id=agent.id,
        run_id=run_id,
        external_event_id="vendor-event-123",
        correlation_id="corr-123",
        event_type=TraceEventType.TOOL_CALL_REQUESTED,
        timestamp=datetime.now(UTC),
        summary="Tool call requested.",
        metadata_={"tool_name": "send_email"},
    )
    session.add_all([run, trace_event])
    session.commit()
    return trace_event


def policy_result(
    *,
    decision: PolicyDecisionValue,
    reason: str,
    policy_id: str | UUID | None = None,
    rule_id: str | UUID | None = None,
) -> PolicyEvaluationResult:
    return PolicyEvaluationResult(
        decision=decision,
        reason=reason,
        agent_id="agent-1",
        policy_id=policy_id,
        rule_id=rule_id,
    )


def fetch_policy_decisions(session: Session) -> list[PolicyDecision]:
    return list(session.scalars(select(PolicyDecision)).all())
