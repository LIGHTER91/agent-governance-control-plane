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


def test_create_source(api_client: tuple[TestClient, SessionFactory]) -> None:
    client, _ = api_client

    response = client.post(
        "/sources",
        json=source_payload(name="Support knowledge base"),
    )

    assert response.status_code == 201
    body = response.json()
    assert UUID(body["id"])
    assert body["name"] == "Support knowledge base"
    assert body["source_type"] == "knowledge_base"
    assert body["external_ref"] == "kb:support-runbooks"
    assert body["owner_type"] == "team"
    assert body["owner_id"] == "team:support-ops"
    assert body["owner_name"] == "Support Operations"
    assert body["owner_contact_email"] == "support-ops@example.invalid"
    assert body["status"] == "active"
    assert body["risk_level"] == "medium"
    assert body["metadata"] == {"domain": "support", "system": "runbook_index"}
    assert "metadata_" not in body


def test_list_sources(api_client: tuple[TestClient, SessionFactory]) -> None:
    client, _ = api_client
    client.post("/sources", json=source_payload(name="Support knowledge base"))
    client.post("/sources", json=source_payload(name="Policy document store"))

    response = client.get("/sources")

    assert response.status_code == 200
    assert {source["name"] for source in response.json()} == {
        "Support knowledge base",
        "Policy document store",
    }


def test_get_source_by_id(api_client: tuple[TestClient, SessionFactory]) -> None:
    client, _ = api_client
    created = client.post(
        "/sources",
        json=source_payload(name="Support knowledge base"),
    )
    source_id = created.json()["id"]

    response = client.get(f"/sources/{source_id}")

    assert response.status_code == 200
    assert response.json()["id"] == source_id
    assert response.json()["name"] == "Support knowledge base"


def test_update_source(api_client: tuple[TestClient, SessionFactory]) -> None:
    client, _ = api_client
    created = client.post("/sources", json=source_payload())
    source_id = created.json()["id"]

    response = client.patch(
        f"/sources/{source_id}",
        json={
            "description": "Temporarily paused.",
            "risk_level": "high",
            "metadata": {"domain": "support", "review_status": "paused"},
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["description"] == "Temporarily paused."
    assert body["risk_level"] == "high"
    assert body["metadata"] == {"domain": "support", "review_status": "paused"}


def test_empty_source_update_is_rejected(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, _ = api_client
    created = client.post("/sources", json=source_payload())
    source_id = created.json()["id"]

    response = client.patch(f"/sources/{source_id}", json={})

    assert response.status_code == 400
    assert response.json()["detail"] == "No update fields provided."


def test_source_not_found_behavior(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, _ = api_client
    missing_id = "00000000-0000-0000-0000-000000000001"

    response = client.get(f"/sources/{missing_id}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Source not found."


def test_source_create_rejects_unsafe_metadata(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, _ = api_client

    response = client.post(
        "/sources",
        json={
            **source_payload(),
            "metadata": {"api_key_ref": "do-not-store"},
        },
    )

    assert response.status_code == 422


def test_source_update_rejects_unsafe_metadata(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, _ = api_client
    created = client.post("/sources", json=source_payload())
    source_id = created.json()["id"]

    response = client.patch(
        f"/sources/{source_id}",
        json={"metadata": {"client_secret": "do-not-store"}},
    )

    assert response.status_code == 422


def test_audit_log_created_on_source_create(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client

    response = client.post("/sources", json=source_payload())

    assert response.status_code == 201
    [audit_log] = fetch_audit_logs(session_factory)
    assert audit_log.event_type == "source_created"
    assert audit_log.actor_type is ActorType.DEVELOPMENT
    assert audit_log.actor_id == "dev-placeholder"
    assert audit_log.entity_type == "source"
    assert audit_log.entity_id == response.json()["id"]
    assert audit_log.metadata_ == {
        "operation": "create",
        "source_type": "knowledge_base",
        "owner_type": "team",
        "status": "active",
        "risk_level": "medium",
    }


def test_audit_log_created_on_source_update(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    created = client.post("/sources", json=source_payload())
    source_id = created.json()["id"]

    response = client.patch(
        f"/sources/{source_id}",
        json={
            "metadata": {"domain": "support", "review_status": "paused"},
        },
    )

    assert response.status_code == 200
    update_log = fetch_audit_logs(session_factory)[-1]
    assert update_log.event_type == "source_updated"
    assert update_log.actor_type is ActorType.DEVELOPMENT
    assert update_log.actor_id == "dev-placeholder"
    assert update_log.entity_type == "source"
    assert update_log.entity_id == source_id
    assert update_log.metadata_ == {"updated_fields": "metadata"}
    assert "review_status" not in str(update_log.metadata_)


def test_audit_log_created_on_source_status_change(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    created = client.post("/sources", json=source_payload(status="active"))
    source_id = created.json()["id"]

    response = client.patch(
        f"/sources/{source_id}",
        json={"status": "disabled"},
    )

    assert response.status_code == 200
    status_log = fetch_audit_logs(session_factory)[-1]
    assert status_log.event_type == "source_status_changed"
    assert status_log.actor_type is ActorType.DEVELOPMENT
    assert status_log.actor_id == "dev-placeholder"
    assert status_log.entity_type == "source"
    assert status_log.entity_id == source_id
    assert status_log.metadata_ == {
        "updated_fields": "status",
        "status_from": "active",
        "status_to": "disabled",
    }


def fetch_audit_logs(session_factory: SessionFactory) -> list[AuditLog]:
    with session_factory() as session:
        statement = select(AuditLog).order_by(AuditLog.created_at, AuditLog.id)
        return list(session.scalars(statement).all())


def source_payload(
    *,
    name: str = "Support knowledge base",
    status: str = "active",
) -> dict[str, object]:
    return {
        "name": name,
        "description": "Governed source for support runbooks.",
        "source_type": "knowledge_base",
        "external_ref": "kb:support-runbooks",
        "owner_type": "team",
        "owner_id": "team:support-ops",
        "owner_name": "Support Operations",
        "owner_contact_email": "support-ops@example.invalid",
        "status": status,
        "risk_level": "medium",
        "metadata": {"domain": "support", "system": "runbook_index"},
    }
