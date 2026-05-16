import json
from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy import event as sqlalchemy_event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from agent_governance_api.database import Base, get_db_session
from agent_governance_api.main import app
from agent_governance_api.models import (
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

SessionFactory = Callable[[], Session]
DEMO_RUN_ID = UUID("11111111-1111-4111-8111-111111111111")
DEMO_TRACE_EVENT_ID = UUID("22222222-2222-4222-8222-222222222222")
DEMO_TIMESTAMP = datetime(2026, 1, 15, 12, 0, tzinfo=UTC)


@pytest.fixture()
def api_client() -> Iterator[tuple[TestClient, SessionFactory]]:
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
    testing_session_factory = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )

    def override_get_db_session() -> Iterator[Session]:
        with testing_session_factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_get_db_session
    try:
        with TestClient(app) as client:
            yield client, testing_session_factory
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_v0_governance_flow_demo(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client

    agent_response = client.post("/agents", json=agent_payload())
    assert agent_response.status_code == 201
    agent_id = UUID(agent_response.json()["id"])

    policy_id, rule_id = insert_active_human_review_policy(session_factory)

    telemetry_response = client.post(
        "/telemetry/events",
        json=tool_call_requested_payload(
            agent_id=agent_id,
            event_id=DEMO_TRACE_EVENT_ID,
            run_id=DEMO_RUN_ID,
        ),
    )

    assert telemetry_response.status_code == 201
    telemetry_body = telemetry_response.json()
    assert telemetry_body["id"] == str(DEMO_TRACE_EVENT_ID)
    assert telemetry_body["policy_decision"]["decision"] == "require_human_review"
    assert telemetry_body["policy_decision"]["policy_id"] == str(policy_id)
    assert telemetry_body["policy_decision"]["rule_id"] == str(rule_id)
    assert telemetry_body["human_approval_id"] is not None

    with session_factory() as session:
        [trace_event] = session.scalars(select(TraceEventRecord)).all()
        [policy_decision] = session.scalars(select(PolicyDecision)).all()
        [human_approval] = session.scalars(select(HumanApproval)).all()
        human_approval_audit_log = session.scalar(
            select(AuditLog).where(
                AuditLog.event_type == "human_approval_requested",
                AuditLog.entity_type == "human_approval",
            )
        )

        assert trace_event.id == DEMO_TRACE_EVENT_ID
        assert trace_event.agent_id == agent_id
        assert trace_event.run_id == DEMO_RUN_ID
        assert trace_event.event_type is TraceEventType.TOOL_CALL_REQUESTED

        assert policy_decision.agent_id == agent_id
        assert policy_decision.policy_id == policy_id
        assert policy_decision.rule_id == rule_id
        assert policy_decision.trace_event_id == trace_event.id
        assert policy_decision.decision is PolicyDecisionValue.REQUIRE_HUMAN_REVIEW

        assert human_approval.id == UUID(telemetry_body["human_approval_id"])
        assert human_approval.agent_id == agent_id
        assert human_approval.policy_decision_id == policy_decision.id
        assert human_approval.status is HumanApprovalStatus.PENDING

        assert human_approval_audit_log is not None
        assert human_approval_audit_log.entity_id == str(human_approval.id)
        assert human_approval_audit_log.metadata_ == {
            "agent_id": str(agent_id),
            "status": "pending",
            "policy_decision_id": str(policy_decision.id),
        }

    evidence_response = client.get(f"/agents/{agent_id}/evidence-bundle")

    assert evidence_response.status_code == 200
    evidence = evidence_response.json()
    [agent_run] = evidence["agent_runs"]
    [bundle_trace_event] = evidence["trace_events"]
    [bundle_policy_decision] = evidence["policy_decisions"]
    [bundle_human_approval] = evidence["human_approvals"]
    [bundle_human_approval_audit_log] = [
        audit_log
        for audit_log in evidence["audit_logs"]
        if audit_log["event_type"] == "human_approval_requested"
    ]

    assert agent_run["agent_id"] == str(agent_id)
    assert agent_run["run_id"] == str(DEMO_RUN_ID)
    assert bundle_trace_event["id"] == str(DEMO_TRACE_EVENT_ID)
    assert bundle_trace_event["run_id"] == agent_run["run_id"]
    assert bundle_policy_decision["trace_event_id"] == bundle_trace_event["id"]
    assert bundle_policy_decision["decision"] == "require_human_review"
    assert bundle_policy_decision["policy"]["id"] == str(policy_id)
    assert bundle_policy_decision["rule"]["id"] == str(rule_id)
    assert bundle_human_approval["policy_decision_id"] == bundle_policy_decision["id"]
    assert bundle_human_approval["status"] == "pending"
    assert bundle_human_approval_audit_log["entity_id"] == bundle_human_approval["id"]
    assert (
        bundle_human_approval_audit_log["metadata"]["policy_decision_id"]
        == bundle_policy_decision["id"]
    )


def insert_active_human_review_policy(
    session_factory: SessionFactory,
) -> tuple[UUID, UUID]:
    with session_factory() as session:
        policy = Policy(
            name="V0 email tool review policy",
            description="Requires review before email tool use.",
            status=PolicyStatus.ACTIVE,
        )
        session.add(policy)
        session.flush()

        rule = PolicyRule(
            policy_id=policy.id,
            name="Require review for send_email",
            description=None,
            condition=json.dumps(
                {
                    "tool_name": "send_email",
                    "decision": "require_human_review",
                    "reason": "Email tool use requires human review.",
                }
            ),
        )
        session.add(rule)
        session.commit()
        return policy.id, rule.id


def agent_payload() -> dict[str, object]:
    return {
        "name": "V0 Support Assistant",
        "description": "Routes support requests and can request email tool use.",
        "owner_type": "team",
        "owner_id": "team:ai-platform",
        "owner_name": "AI Platform",
        "owner_contact_email": "owner@example.com",
        "environment": "development",
        "status": "active",
        "risk_level": "medium",
        "framework": "LangGraph",
    }


def tool_call_requested_payload(
    *,
    agent_id: UUID,
    event_id: UUID,
    run_id: UUID,
) -> dict[str, object]:
    return {
        "id": str(event_id),
        "agent_id": str(agent_id),
        "run_id": str(run_id),
        "correlation_id": "v0-demo-correlation",
        "event_type": "tool_call_requested",
        "timestamp": DEMO_TIMESTAMP.isoformat(),
        "summary": "Agent requested send_email tool.",
        "metadata": {"tool_name": "send_email"},
    }
