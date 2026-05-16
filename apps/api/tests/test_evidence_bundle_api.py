from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy import event as sqlalchemy_event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from agent_governance_api.database import Base, get_db_session
from agent_governance_api.main import app
from agent_governance_api.models import (
    ActorType,
    AgentRunRecord,
    AuditLog,
    Environment,
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


def test_successful_evidence_bundle_export(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(client)
    seed_evidence_records(session_factory, agent_id)

    response = client.get(f"/agents/{agent_id}/evidence-bundle")

    assert response.status_code == 200
    body = response.json()
    assert body["agent"]["id"] == str(agent_id)
    assert body["agent"]["owner_id"] == "team:ai-platform"
    assert set(body) == {
        "agent",
        "audit_logs",
        "agent_runs",
        "trace_events",
        "policy_decisions",
        "human_approvals",
    }


def test_evidence_bundle_unknown_agent_returns_404(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, _ = api_client
    missing_agent_id = uuid4()

    response = client.get(f"/agents/{missing_agent_id}/evidence-bundle")

    assert response.status_code == 404
    assert response.json()["detail"] == "Agent not found."


def test_evidence_bundle_includes_audit_logs(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(client)
    seed_evidence_records(session_factory, agent_id)

    response = client.get(f"/agents/{agent_id}/evidence-bundle")

    assert response.status_code == 200
    audit_logs = response.json()["audit_logs"]
    assert [log["event_type"] for log in audit_logs] == [
        "agent_created",
        "agent_updated",
    ]
    assert audit_logs[0]["entity_id"] == str(agent_id)
    assert audit_logs[1]["metadata"] == {"updated_fields": "risk_level"}


def test_evidence_bundle_includes_trace_events(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(client)
    seeded = seed_evidence_records(session_factory, agent_id)

    response = client.get(f"/agents/{agent_id}/evidence-bundle")

    assert response.status_code == 200
    body = response.json()
    [agent_run] = body["agent_runs"]
    [trace_event] = body["trace_events"]
    assert agent_run["run_id"] == str(seeded.run_id)
    assert agent_run["metadata"] == {"source": "api-test"}
    assert trace_event["id"] == str(seeded.trace_event_id)
    assert trace_event["external_event_id"] == "vendor-event-123"
    assert trace_event["metadata"] == {"tool_name": "send_email"}


def test_evidence_bundle_includes_policy_decisions_with_references(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(client)
    seeded = seed_evidence_records(session_factory, agent_id)

    response = client.get(f"/agents/{agent_id}/evidence-bundle")

    assert response.status_code == 200
    [decision] = response.json()["policy_decisions"]
    assert decision["id"] == str(seeded.policy_decision_id)
    assert decision["decision"] == "deny"
    assert decision["policy_id"] == str(seeded.policy_id)
    assert decision["rule_id"] == str(seeded.rule_id)
    assert decision["policy"] == {
        "id": str(seeded.policy_id),
        "name": "Tool access policy",
        "status": "active",
    }
    assert decision["rule"] == {
        "id": str(seeded.rule_id),
        "policy_id": str(seeded.policy_id),
        "name": "Deny email tool",
    }


def test_evidence_bundle_represents_policy_decisions_linked_to_trace_events(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(client)
    seeded = seed_evidence_records(session_factory, agent_id)

    response = client.get(f"/agents/{agent_id}/evidence-bundle")

    assert response.status_code == 200
    [decision] = response.json()["policy_decisions"]
    assert decision["trace_event_id"] == str(seeded.trace_event_id)


def test_evidence_bundle_includes_human_approvals(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(client)
    seeded = seed_evidence_records(session_factory, agent_id)

    response = client.get(f"/agents/{agent_id}/evidence-bundle")

    assert response.status_code == 200
    [approval] = response.json()["human_approvals"]
    assert approval["id"] == str(seeded.human_approval_id)
    assert approval["agent_id"] == str(agent_id)
    assert approval["status"] == "approved"
    assert approval["requested_by_actor_type"] == "development"
    assert approval["requested_by_actor_id"] == "dev-placeholder"
    assert approval["reviewed_by_actor_type"] == "development"
    assert approval["reviewed_by_actor_id"] == "dev-placeholder"
    assert approval["reason"] == "High-risk action requires review."
    assert approval["decision_note"] == "Approved for evidence test."
    assert approval["created_at"]
    assert approval["reviewed_at"]
    assert approval["expires_at"] is None


def test_evidence_bundle_represents_approvals_linked_to_policy_decisions(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(client)
    seeded = seed_evidence_records(session_factory, agent_id)

    response = client.get(f"/agents/{agent_id}/evidence-bundle")

    assert response.status_code == 200
    [approval] = response.json()["human_approvals"]
    assert approval["policy_decision_id"] == str(seeded.policy_decision_id)


def test_evidence_bundle_filters_unsafe_metadata_fields(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(client)
    seeded = seed_evidence_records(session_factory, agent_id)
    inject_unsafe_metadata(session_factory, agent_id, seeded)

    response = client.get(f"/agents/{agent_id}/evidence-bundle")

    assert response.status_code == 200
    body = response.json()
    unsafe_audit_log = body["audit_logs"][-1]
    [agent_run] = body["agent_runs"]
    [trace_event] = body["trace_events"]
    assert unsafe_audit_log["metadata"] == {"safe_note": "kept"}
    assert agent_run["metadata"] == {"source": "api-test"}
    assert trace_event["metadata"] == {"tool_name": "send_email"}
    assert "api_key" not in str(body)
    assert "token" not in str(body)
    assert "raw_payload" not in str(body)
    assert "private_customer_data" not in str(body)


class SeededEvidence:
    def __init__(
        self,
        *,
        run_id: UUID,
        trace_event_id: UUID,
        policy_id: UUID,
        rule_id: UUID,
        policy_decision_id: UUID,
        human_approval_id: UUID,
    ) -> None:
        self.run_id = run_id
        self.trace_event_id = trace_event_id
        self.policy_id = policy_id
        self.rule_id = rule_id
        self.policy_decision_id = policy_decision_id
        self.human_approval_id = human_approval_id


def create_agent(client: TestClient) -> UUID:
    response = client.post("/agents", json=agent_payload())

    assert response.status_code == 201
    return UUID(response.json()["id"])


def seed_evidence_records(
    session_factory: SessionFactory,
    agent_id: UUID,
) -> SeededEvidence:
    with session_factory() as session:
        created_at = datetime.now(UTC)
        audit_log = AuditLog(
            event_type="agent_updated",
            actor_type=ActorType.DEVELOPMENT,
            actor_id="dev-placeholder",
            entity_type="agent",
            entity_id=str(agent_id),
            summary="Agent risk level updated.",
            metadata_={"updated_fields": "risk_level"},
            created_at=created_at,
        )
        run_id = uuid4()
        run = AgentRunRecord(
            agent_id=agent_id,
            run_id=run_id,
            correlation_id="corr-123",
            environment=Environment.DEVELOPMENT,
            status="observed",
            started_at=created_at,
            summary="Agent run observed.",
            metadata_={"source": "api-test"},
            created_at=created_at,
        )
        trace_event = TraceEventRecord(
            agent_id=agent_id,
            run_id=run_id,
            external_event_id="vendor-event-123",
            correlation_id="corr-123",
            event_type=TraceEventType.TOOL_CALL_REQUESTED,
            timestamp=created_at,
            summary="Tool call requested.",
            metadata_={"tool_name": "send_email"},
            created_at=created_at,
        )
        policy = Policy(
            name="Tool access policy",
            description=None,
            status=PolicyStatus.ACTIVE,
            created_at=created_at,
            updated_at=created_at,
        )
        session.add_all([audit_log, run, trace_event, policy])
        session.flush()

        rule = PolicyRule(
            policy_id=policy.id,
            name="Deny email tool",
            description=None,
            condition='{"decision":"deny","reason":"Email is denied."}',
            created_at=created_at,
            updated_at=created_at,
        )
        session.add(rule)
        session.flush()

        decision = PolicyDecision(
            agent_id=agent_id,
            policy_id=policy.id,
            rule_id=rule.id,
            trace_event_id=trace_event.id,
            decision=PolicyDecisionValue.DENY,
            reason="Email is denied.",
            context_hash="sha256:evidence-test",
            created_at=created_at,
        )
        session.add(decision)
        session.flush()

        approval = HumanApproval(
            agent_id=agent_id,
            policy_decision_id=decision.id,
            status=HumanApprovalStatus.APPROVED,
            requested_by_actor_type=ActorType.DEVELOPMENT,
            requested_by_actor_id="dev-placeholder",
            reviewed_by_actor_type=ActorType.DEVELOPMENT,
            reviewed_by_actor_id="dev-placeholder",
            reason="High-risk action requires review.",
            decision_note="Approved for evidence test.",
            created_at=created_at,
            reviewed_at=created_at,
            expires_at=None,
        )
        session.add(approval)
        session.commit()
        return SeededEvidence(
            run_id=run_id,
            trace_event_id=trace_event.id,
            policy_id=policy.id,
            rule_id=rule.id,
            policy_decision_id=decision.id,
            human_approval_id=approval.id,
        )


def inject_unsafe_metadata(
    session_factory: SessionFactory,
    agent_id: UUID,
    seeded: SeededEvidence,
) -> None:
    with session_factory() as session:
        unsafe_audit_log = AuditLog(
            event_type="agent_reviewed",
            actor_type=ActorType.DEVELOPMENT,
            actor_id="dev-placeholder",
            entity_type="agent",
            entity_id=str(agent_id),
            summary="Agent reviewed.",
            metadata_={
                "safe_note": "kept",
                "api_key": "do-not-export",
                "password": "do-not-export",
                "private_customer_data": "do-not-export",
            },
            created_at=datetime.now(UTC),
        )
        session.add(unsafe_audit_log)
        session.execute(
            AgentRunRecord.__table__.update()
            .where(AgentRunRecord.run_id == seeded.run_id)
            .values(
                {
                    "metadata": {
                        "source": "api-test",
                        "raw_payload": "do-not-export",
                    }
                }
            )
        )
        session.execute(
            TraceEventRecord.__table__.update()
            .where(TraceEventRecord.id == seeded.trace_event_id)
            .values(
                {
                    "metadata": {
                        "tool_name": "send_email",
                        "token": "do-not-export",
                        "authorization": "Bearer do-not-export",
                        "nested": {"secret": "do-not-export"},
                    }
                }
            )
        )
        session.commit()


def agent_payload() -> dict[str, object]:
    return {
        "name": "Support assistant",
        "description": "Routes support requests.",
        "owner_type": "team",
        "owner_id": "team:ai-platform",
        "owner_name": "AI Platform",
        "owner_contact_email": "owner@example.com",
        "environment": "development",
        "status": "draft",
        "risk_level": "low",
        "framework": "LangGraph",
    }
