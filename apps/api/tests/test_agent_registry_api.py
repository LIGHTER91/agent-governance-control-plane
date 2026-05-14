from collections.abc import Callable, Iterator
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from agent_governance_api.database import Base, get_db_session
from agent_governance_api.main import app
from agent_governance_api.models import ActorType, AuditLog

SessionFactory = Callable[[], Session]


@pytest.fixture()
def api_client() -> Iterator[tuple[TestClient, SessionFactory]]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
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


def test_create_agent(api_client: tuple[TestClient, SessionFactory]) -> None:
    client, _ = api_client

    response = client.post("/agents", json=agent_payload(name="Support assistant"))

    assert response.status_code == 201
    body = response.json()
    assert UUID(body["id"])
    assert body["name"] == "Support assistant"
    assert body["owner_type"] == "team"
    assert body["owner_id"] == "team:ai-platform"
    assert body["status"] == "draft"


def test_list_agents(api_client: tuple[TestClient, SessionFactory]) -> None:
    client, _ = api_client
    client.post("/agents", json=agent_payload(name="Support assistant"))
    client.post("/agents", json=agent_payload(name="Risk review assistant"))

    response = client.get("/agents")

    assert response.status_code == 200
    assert {agent["name"] for agent in response.json()} == {
        "Support assistant",
        "Risk review assistant",
    }


def test_get_agent_by_id(api_client: tuple[TestClient, SessionFactory]) -> None:
    client, _ = api_client
    created = client.post("/agents", json=agent_payload(name="Support assistant"))
    agent_id = created.json()["id"]

    response = client.get(f"/agents/{agent_id}")

    assert response.status_code == 200
    assert response.json()["id"] == agent_id
    assert response.json()["name"] == "Support assistant"


def test_update_agent(api_client: tuple[TestClient, SessionFactory]) -> None:
    client, _ = api_client
    created = client.post("/agents", json=agent_payload(name="Support assistant"))
    agent_id = created.json()["id"]

    response = client.patch(
        f"/agents/{agent_id}",
        json={"description": "Handles support triage.", "risk_level": "medium"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["description"] == "Handles support triage."
    assert body["risk_level"] == "medium"


def test_invalid_enum_validation(api_client: tuple[TestClient, SessionFactory]) -> None:
    client, _ = api_client

    response = client.post(
        "/agents",
        json={**agent_payload(), "status": "running"},
    )

    assert response.status_code == 422


def test_not_found_behavior(api_client: tuple[TestClient, SessionFactory]) -> None:
    client, _ = api_client
    missing_id = "00000000-0000-0000-0000-000000000001"

    response = client.get(f"/agents/{missing_id}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Agent not found."


def test_audit_log_created_on_create(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client

    response = client.post("/agents", json=agent_payload())

    assert response.status_code == 201
    [audit_log] = fetch_audit_logs(session_factory)
    assert audit_log.event_type == "agent_created"
    assert audit_log.actor_type is ActorType.DEVELOPMENT
    assert audit_log.actor_id == "dev-placeholder"
    assert audit_log.entity_type == "agent"
    assert audit_log.entity_id == response.json()["id"]
    assert audit_log.metadata_ == {"operation": "create"}


def test_audit_log_created_on_update(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    created = client.post("/agents", json=agent_payload())
    agent_id = created.json()["id"]

    response = client.patch(
        f"/agents/{agent_id}",
        json={"owner_name": "AI Governance"},
    )

    assert response.status_code == 200
    audit_logs = fetch_audit_logs(session_factory)
    update_log = audit_logs[-1]
    assert update_log.event_type == "agent_updated"
    assert update_log.actor_type is ActorType.DEVELOPMENT
    assert update_log.actor_id == "dev-placeholder"
    assert update_log.entity_type == "agent"
    assert update_log.entity_id == agent_id
    assert update_log.metadata_ == {"updated_fields": "owner_name"}


def test_audit_log_created_on_status_change(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    created = client.post("/agents", json=agent_payload(status="draft"))
    agent_id = created.json()["id"]

    response = client.patch(f"/agents/{agent_id}", json={"status": "active"})

    assert response.status_code == 200
    audit_logs = fetch_audit_logs(session_factory)
    status_log = audit_logs[-1]
    assert status_log.event_type == "agent_status_changed"
    assert status_log.actor_type is ActorType.DEVELOPMENT
    assert status_log.actor_id == "dev-placeholder"
    assert status_log.entity_type == "agent"
    assert status_log.entity_id == agent_id
    assert status_log.metadata_ == {
        "updated_fields": "status",
        "status_from": "draft",
        "status_to": "active",
    }


def fetch_audit_logs(session_factory: SessionFactory) -> list[AuditLog]:
    with session_factory() as session:
        statement = select(AuditLog).order_by(AuditLog.created_at, AuditLog.id)
        return list(session.scalars(statement).all())


def agent_payload(
    *,
    name: str = "Support assistant",
    status: str = "draft",
) -> dict[str, object]:
    return {
        "name": name,
        "description": "Routes support requests.",
        "owner_type": "team",
        "owner_id": "team:ai-platform",
        "owner_name": "AI Platform",
        "owner_contact_email": "owner@example.com",
        "environment": "development",
        "status": status,
        "risk_level": "low",
        "framework": "LangGraph",
    }
