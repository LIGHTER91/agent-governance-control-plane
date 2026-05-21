from collections.abc import Callable, Iterator
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy import event as sqlalchemy_event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from agent_governance_api.auth import ActorContext, get_current_actor
from agent_governance_api.database import Base, get_db_session
from agent_governance_api.main import app
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
    PolicyDecision,
    PolicyDecisionValue,
    RiskLevel,
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
    app.dependency_overrides[get_current_actor] = lambda: auditor_actor()
    try:
        with TestClient(app) as client:
            yield client, testing_session_factory
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_agent_activity_returns_empty_list_for_existing_agent(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)

    response = client.get(f"/agents/{agent_id}/activity")

    assert response.status_code == 200
    assert response.json() == []


def test_agent_activity_includes_trace_events(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    seeded = seed_activity_records(session_factory, agent_id)

    response = client.get(f"/agents/{agent_id}/activity")

    assert response.status_code == 200
    trace_items = [item for item in response.json() if item["type"] == "trace_event"]
    [trace_item] = trace_items
    assert trace_item["id"] == str(seeded.trace_event_id)
    assert trace_item["trace_event_id"] == str(seeded.trace_event_id)
    assert trace_item["run_id"] == str(seeded.run_id)
    assert trace_item["title"] == "Trace event: Tool Call Requested"
    assert trace_item["summary"] == "Tool call requested."
    assert trace_item["severity"] == "info"
    assert trace_item["related_ids"] == {
        "trace_event_id": str(seeded.trace_event_id),
        "run_id": str(seeded.run_id),
    }
    assert trace_item["metadata"] == {"tool_name": "send_email"}


def test_agent_activity_includes_policy_decisions(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    seeded = seed_activity_records(session_factory, agent_id)

    response = client.get(f"/agents/{agent_id}/activity")

    assert response.status_code == 200
    decision_items = [
        item for item in response.json() if item["type"] == "policy_decision"
    ]
    [decision_item] = decision_items
    assert decision_item["id"] == str(seeded.policy_decision_id)
    assert decision_item["policy_decision_id"] == str(seeded.policy_decision_id)
    assert decision_item["trace_event_id"] == str(seeded.trace_event_id)
    assert decision_item["title"] == "Policy decision: Deny"
    assert decision_item["summary"] == "Email tool is denied."
    assert decision_item["severity"] == "warning"
    assert decision_item["related_ids"] == {
        "trace_event_id": str(seeded.trace_event_id),
        "policy_decision_id": str(seeded.policy_decision_id),
    }
    assert decision_item["metadata"] == {}


def test_agent_activity_includes_human_approvals(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    seeded = seed_activity_records(session_factory, agent_id)

    response = client.get(f"/agents/{agent_id}/activity")

    assert response.status_code == 200
    approval_items = [
        item for item in response.json() if item["type"] == "human_approval"
    ]
    [approval_item] = approval_items
    assert approval_item["id"] == str(seeded.human_approval_id)
    assert approval_item["human_approval_id"] == str(seeded.human_approval_id)
    assert approval_item["policy_decision_id"] == str(seeded.policy_decision_id)
    assert approval_item["title"] == "Human approval: Pending"
    assert approval_item["summary"] == "Review required for email tool."
    assert approval_item["severity"] == "info"
    assert approval_item["related_ids"] == {
        "policy_decision_id": str(seeded.policy_decision_id),
        "human_approval_id": str(seeded.human_approval_id),
    }
    assert approval_item["metadata"] == {}


def test_agent_activity_includes_audit_logs(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    seeded = seed_activity_records(session_factory, agent_id)

    response = client.get(f"/agents/{agent_id}/activity")

    assert response.status_code == 200
    audit_items = [item for item in response.json() if item["type"] == "audit_log"]
    assert {item["audit_log_id"] for item in audit_items} == {
        str(seeded.agent_audit_log_id),
        str(seeded.human_approval_audit_log_id),
    }
    human_approval_audit_item = next(
        item
        for item in audit_items
        if item["audit_log_id"] == str(seeded.human_approval_audit_log_id)
    )
    assert human_approval_audit_item["human_approval_id"] == str(
        seeded.human_approval_id,
    )
    assert human_approval_audit_item["policy_decision_id"] == str(
        seeded.policy_decision_id,
    )
    assert human_approval_audit_item["severity"] == "info"
    assert human_approval_audit_item["related_ids"] == {
        "audit_log_id": str(seeded.human_approval_audit_log_id),
        "human_approval_id": str(seeded.human_approval_id),
        "policy_decision_id": str(seeded.policy_decision_id),
    }


def test_agent_activity_orders_newest_first(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    seed_activity_records(session_factory, agent_id)

    response = client.get(f"/agents/{agent_id}/activity")

    assert response.status_code == 200
    timestamps = [item["timestamp"] for item in response.json()]
    assert timestamps == sorted(timestamps, reverse=True)
    assert [item["type"] for item in response.json()] == [
        "audit_log",
        "audit_log",
        "human_approval",
        "policy_decision",
        "trace_event",
    ]


def test_agent_activity_unknown_agent_returns_404_for_authorized_actor(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, _ = api_client

    response = client.get(f"/agents/{uuid4()}/activity")

    assert response.status_code == 404
    assert response.json()["detail"] == "Agent not found."


def test_actor_without_required_role_gets_403(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    seed_activity_records(session_factory, agent_id)
    set_current_actor(
        ActorContext(
            actor_type=ActorType.USER,
            actor_id="user:viewer-1",
            roles=("viewer",),
        )
    )

    response = client.get(f"/agents/{agent_id}/activity")

    assert response.status_code == 403
    assert response.json()["detail"] == (
        "Actor requires one of these roles: reviewer, auditor, platform_admin."
    )


def test_service_actor_gets_403(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    seed_activity_records(session_factory, agent_id)
    set_current_actor(
        ActorContext(
            actor_type=ActorType.SERVICE,
            actor_id="service:runtime-adapter",
            roles=("reviewer", "auditor", "platform_admin"),
        )
    )

    response = client.get(f"/agents/{agent_id}/activity")

    assert response.status_code == 403
    assert response.json()["detail"] == "Service actors cannot view Agent activity."


def test_agent_activity_does_not_expose_unsafe_metadata(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    seeded = seed_activity_records(session_factory, agent_id)
    inject_unsafe_metadata(session_factory, seeded)

    response = client.get(f"/agents/{agent_id}/activity")

    assert response.status_code == 200
    trace_item = next(item for item in response.json() if item["type"] == "trace_event")
    audit_item = next(
        item
        for item in response.json()
        if item["audit_log_id"] == str(seeded.agent_audit_log_id)
    )
    assert trace_item["metadata"] == {"tool_name": "send_email"}
    assert audit_item["metadata"] == {"safe_note": "kept"}
    body_text = response.text
    assert "do-not-export" not in body_text
    assert "raw_payload" not in body_text
    assert "authorization" not in body_text
    assert "token" not in body_text


class SeededActivity:
    def __init__(
        self,
        *,
        run_id: UUID,
        trace_event_id: UUID,
        policy_decision_id: UUID,
        human_approval_id: UUID,
        agent_audit_log_id: UUID,
        human_approval_audit_log_id: UUID,
    ) -> None:
        self.run_id = run_id
        self.trace_event_id = trace_event_id
        self.policy_decision_id = policy_decision_id
        self.human_approval_id = human_approval_id
        self.agent_audit_log_id = agent_audit_log_id
        self.human_approval_audit_log_id = human_approval_audit_log_id


def create_agent(session_factory: SessionFactory) -> UUID:
    with session_factory() as session:
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
        return agent.id


def seed_activity_records(
    session_factory: SessionFactory,
    agent_id: UUID,
) -> SeededActivity:
    with session_factory() as session:
        base_time = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
        run_id = uuid4()
        run = AgentRunRecord(
            agent_id=agent_id,
            run_id=run_id,
            correlation_id="corr-activity",
            environment=Environment.DEVELOPMENT,
            status="observed",
            started_at=base_time,
            summary="Agent run observed.",
            metadata_={"source": "activity-test"},
            created_at=base_time,
        )
        session.add(run)
        session.flush()

        trace_event = TraceEventRecord(
            agent_id=agent_id,
            run_id=run_id,
            external_event_id="vendor-event-activity",
            correlation_id="corr-activity",
            event_type=TraceEventType.TOOL_CALL_REQUESTED,
            timestamp=base_time + timedelta(minutes=1),
            summary="Tool call requested.",
            metadata_={"tool_name": "send_email"},
            created_at=base_time + timedelta(minutes=1),
        )
        session.add(trace_event)
        session.flush()

        policy_decision = PolicyDecision(
            agent_id=agent_id,
            trace_event_id=trace_event.id,
            decision=PolicyDecisionValue.DENY,
            reason="Email tool is denied.",
            created_at=base_time + timedelta(minutes=2),
        )
        session.add(policy_decision)
        session.flush()

        human_approval = HumanApproval(
            agent_id=agent_id,
            policy_decision_id=policy_decision.id,
            status=HumanApprovalStatus.PENDING,
            requested_by_actor_type=ActorType.DEVELOPMENT,
            requested_by_actor_id="dev-placeholder",
            reason="Review required for email tool.",
            created_at=base_time + timedelta(minutes=3),
        )
        session.add(human_approval)
        session.flush()

        agent_audit_log = AuditLog(
            event_type="agent_updated",
            actor_type=ActorType.DEVELOPMENT,
            actor_id="dev-placeholder",
            entity_type="agent",
            entity_id=str(agent_id),
            summary="Agent updated.",
            metadata_={"updated_fields": "risk_level"},
            created_at=base_time + timedelta(minutes=4),
        )
        human_approval_audit_log = AuditLog(
            event_type="human_approval_requested",
            actor_type=ActorType.DEVELOPMENT,
            actor_id="dev-placeholder",
            entity_type="human_approval",
            entity_id=str(human_approval.id),
            summary="Human approval requested.",
            metadata_={
                "agent_id": str(agent_id),
                "policy_decision_id": str(policy_decision.id),
                "status": "pending",
            },
            created_at=base_time + timedelta(minutes=5),
        )
        session.add_all([agent_audit_log, human_approval_audit_log])
        session.commit()

        return SeededActivity(
            run_id=run_id,
            trace_event_id=trace_event.id,
            policy_decision_id=policy_decision.id,
            human_approval_id=human_approval.id,
            agent_audit_log_id=agent_audit_log.id,
            human_approval_audit_log_id=human_approval_audit_log.id,
        )


def inject_unsafe_metadata(
    session_factory: SessionFactory,
    seeded: SeededActivity,
) -> None:
    with session_factory() as session:
        session.execute(
            TraceEventRecord.__table__.update()
            .where(TraceEventRecord.id == seeded.trace_event_id)
            .values(
                {
                    "metadata": {
                        "tool_name": "send_email",
                        "raw_payload": "do-not-export",
                        "authorization": "Bearer do-not-export",
                    }
                }
            )
        )
        session.execute(
            AuditLog.__table__.update()
            .where(AuditLog.id == seeded.agent_audit_log_id)
            .values(
                {
                    "metadata": {
                        "safe_note": "kept",
                        "token": "do-not-export",
                    }
                }
            )
        )
        session.commit()


def set_current_actor(actor: ActorContext) -> None:
    app.dependency_overrides[get_current_actor] = lambda: actor


def auditor_actor() -> ActorContext:
    return ActorContext(
        actor_type=ActorType.USER,
        actor_id="user:auditor-1",
        roles=("auditor",),
    )
