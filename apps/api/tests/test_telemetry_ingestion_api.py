from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy import event as sqlalchemy_event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from agent_governance_api.database import Base, get_db_session
from agent_governance_api.main import app
from agent_governance_api.models import (
    Agent,
    AgentRunRecord,
    AgentStatus,
    Environment,
    OwnerType,
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
    try:
        with TestClient(app) as client:
            yield client, testing_session_factory
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_ingest_valid_trace_event(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    event_id = uuid4()
    run_id = uuid4()

    response = client.post(
        "/telemetry/events",
        json=trace_event_payload(agent_id, event_id=event_id, run_id=run_id),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["id"] == str(event_id)
    assert body["agent_id"] == str(agent_id)
    assert body["run_id"] == str(run_id)
    assert body["event_type"] == "tool_call_requested"
    assert body["created_at"]

    [saved_event] = fetch_trace_events(session_factory)
    assert saved_event.id == event_id
    assert saved_event.agent_id == agent_id
    assert saved_event.run_id == run_id
    assert saved_event.external_event_id == str(event_id)
    assert saved_event.event_type is TraceEventType.TOOL_CALL_REQUESTED
    assert saved_event.metadata_ == {"tool_name": "send_email"}


def test_ingest_duplicate_trace_event_returns_existing_event(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    run_id = uuid4()
    first_event_id = uuid4()
    external_event_id = "vendor-event-123"

    first_response = client.post(
        "/telemetry/events",
        json=trace_event_payload(
            agent_id,
            event_id=first_event_id,
            run_id=run_id,
            external_event_id=external_event_id,
        ),
    )
    duplicate_response = client.post(
        "/telemetry/events",
        json=trace_event_payload(
            agent_id,
            event_id=uuid4(),
            run_id=run_id,
            external_event_id=external_event_id,
            summary="Retried event with changed body.",
        ),
    )

    assert first_response.status_code == 201
    assert duplicate_response.status_code == 200
    assert duplicate_response.json() == first_response.json()
    [saved_event] = fetch_trace_events(session_factory)
    assert saved_event.id == first_event_id
    assert saved_event.external_event_id == external_event_id
    assert saved_event.summary == "Tool call requested."


def test_ingest_duplicate_trace_event_does_not_create_second_record(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    run_id = uuid4()
    external_event_id = "vendor-event-123"

    client.post(
        "/telemetry/events",
        json=trace_event_payload(
            agent_id,
            run_id=run_id,
            external_event_id=external_event_id,
        ),
    )
    client.post(
        "/telemetry/events",
        json=trace_event_payload(
            agent_id,
            run_id=run_id,
            external_event_id=external_event_id,
        ),
    )

    assert len(fetch_trace_events(session_factory)) == 1


def test_ingest_allows_same_external_event_id_for_different_run(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    external_event_id = "vendor-event-123"

    first_response = client.post(
        "/telemetry/events",
        json=trace_event_payload(agent_id, external_event_id=external_event_id),
    )
    second_response = client.post(
        "/telemetry/events",
        json=trace_event_payload(agent_id, external_event_id=external_event_id),
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 201
    assert len(fetch_trace_events(session_factory)) == 2
    assert len(fetch_agent_runs(session_factory)) == 2


def test_ingest_auto_creates_agent_run_record(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    run_id = uuid4()

    response = client.post(
        "/telemetry/events",
        json=trace_event_payload(agent_id, run_id=run_id),
    )

    assert response.status_code == 201
    [saved_run] = fetch_agent_runs(session_factory)
    assert saved_run.agent_id == agent_id
    assert saved_run.run_id == run_id
    assert saved_run.correlation_id == "corr-123"
    assert saved_run.environment is Environment.DEVELOPMENT
    assert saved_run.status == "observed"
    assert saved_run.metadata_ == {}


def test_ingest_attaches_event_to_existing_agent_run_record(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    run_id = uuid4()
    create_agent_run(session_factory, agent_id, run_id)

    response = client.post(
        "/telemetry/events",
        json=trace_event_payload(agent_id, run_id=run_id),
    )

    assert response.status_code == 201
    assert len(fetch_agent_runs(session_factory)) == 1
    [saved_event] = fetch_trace_events(session_factory)
    assert saved_event.agent_id == agent_id
    assert saved_event.run_id == run_id


def test_ingest_rejects_unknown_agent(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client

    response = client.post(
        "/telemetry/events",
        json=trace_event_payload(uuid4()),
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Agent not found."
    assert fetch_agent_runs(session_factory) == []
    assert fetch_trace_events(session_factory) == []


def test_ingest_rejects_unsafe_metadata(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)

    response = client.post(
        "/telemetry/events",
        json=trace_event_payload(agent_id, metadata={"api_key": "redacted"}),
    )

    assert response.status_code == 422
    assert fetch_agent_runs(session_factory) == []
    assert fetch_trace_events(session_factory) == []


def test_ingest_rejects_invalid_event_type(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)

    response = client.post(
        "/telemetry/events",
        json=trace_event_payload(agent_id, event_type="tool_call_finished"),
    )

    assert response.status_code == 422
    assert fetch_agent_runs(session_factory) == []
    assert fetch_trace_events(session_factory) == []


def test_ingest_preserves_agent_id_run_id_integrity(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_a_id = create_agent(session_factory, name="Support assistant")
    agent_b_id = create_agent(session_factory, name="Risk review assistant")
    shared_run_id = uuid4()
    create_agent_run(session_factory, agent_b_id, shared_run_id)

    response = client.post(
        "/telemetry/events",
        json=trace_event_payload(agent_a_id, run_id=shared_run_id),
    )

    assert response.status_code == 201
    runs = fetch_agent_runs(session_factory)
    assert {(run.agent_id, run.run_id) for run in runs} == {
        (agent_a_id, shared_run_id),
        (agent_b_id, shared_run_id),
    }
    [saved_event] = fetch_trace_events(session_factory)
    assert saved_event.agent_id == agent_a_id
    assert saved_event.run_id == shared_run_id


def create_agent(
    session_factory: SessionFactory,
    *,
    name: str = "Support assistant",
) -> UUID:
    with session_factory() as session:
        agent = Agent(
            name=name,
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


def create_agent_run(
    session_factory: SessionFactory,
    agent_id: UUID,
    run_id: UUID,
) -> None:
    with session_factory() as session:
        run = AgentRunRecord(
            agent_id=agent_id,
            run_id=run_id,
            correlation_id="corr-123",
            environment=Environment.DEVELOPMENT,
            status="started",
            started_at=datetime.now(UTC),
            summary="Agent run started.",
            metadata_={},
        )
        session.add(run)
        session.commit()


def fetch_agent_runs(session_factory: SessionFactory) -> list[AgentRunRecord]:
    with session_factory() as session:
        return list(session.scalars(select(AgentRunRecord)).all())


def fetch_trace_events(session_factory: SessionFactory) -> list[TraceEventRecord]:
    with session_factory() as session:
        return list(session.scalars(select(TraceEventRecord)).all())


def trace_event_payload(
    agent_id: UUID,
    *,
    event_id: UUID | None = None,
    run_id: UUID | None = None,
    external_event_id: str | None = None,
    event_type: str = "tool_call_requested",
    metadata: dict[str, object] | None = None,
    summary: str = "Tool call requested.",
) -> dict[str, object]:
    payload = {
        "id": str(event_id or uuid4()),
        "agent_id": str(agent_id),
        "run_id": str(run_id or uuid4()),
        "correlation_id": "corr-123",
        "event_type": event_type,
        "timestamp": datetime.now(UTC).isoformat(),
        "summary": summary,
        "metadata": metadata or {"tool_name": "send_email"},
    }
    if external_event_id is not None:
        payload["external_event_id"] = external_event_id

    return payload
