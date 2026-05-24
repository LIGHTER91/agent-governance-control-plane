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


def test_create_capability(api_client: tuple[TestClient, SessionFactory]) -> None:
    client, _ = api_client

    response = client.post(
        "/capabilities",
        json=capability_payload(name="Send support email"),
    )

    assert response.status_code == 201
    body = response.json()
    assert UUID(body["id"])
    assert body["name"] == "Send support email"
    assert body["capability_type"] == "tool"
    assert body["external_ref"] == "tool:send_email"
    assert body["status"] == "active"
    assert body["risk_level"] == "medium"
    assert body["metadata"] == {"domain": "support", "operation": "send_email"}
    assert "metadata_" not in body


def test_list_capabilities(api_client: tuple[TestClient, SessionFactory]) -> None:
    client, _ = api_client
    client.post("/capabilities", json=capability_payload(name="Send support email"))
    client.post("/capabilities", json=capability_payload(name="Open ticket"))

    response = client.get("/capabilities")

    assert response.status_code == 200
    assert {capability["name"] for capability in response.json()} == {
        "Send support email",
        "Open ticket",
    }


def test_get_capability_by_id(api_client: tuple[TestClient, SessionFactory]) -> None:
    client, _ = api_client
    created = client.post(
        "/capabilities",
        json=capability_payload(name="Send support email"),
    )
    capability_id = created.json()["id"]

    response = client.get(f"/capabilities/{capability_id}")

    assert response.status_code == 200
    assert response.json()["id"] == capability_id
    assert response.json()["name"] == "Send support email"


def test_update_capability(api_client: tuple[TestClient, SessionFactory]) -> None:
    client, _ = api_client
    created = client.post("/capabilities", json=capability_payload())
    capability_id = created.json()["id"]

    response = client.patch(
        f"/capabilities/{capability_id}",
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


def test_empty_capability_update_is_rejected(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, _ = api_client
    created = client.post("/capabilities", json=capability_payload())
    capability_id = created.json()["id"]

    response = client.patch(f"/capabilities/{capability_id}", json={})

    assert response.status_code == 400
    assert response.json()["detail"] == "No update fields provided."


def test_capability_not_found_behavior(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, _ = api_client
    missing_id = "00000000-0000-0000-0000-000000000001"

    response = client.get(f"/capabilities/{missing_id}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Capability not found."


def test_capability_create_rejects_unsafe_metadata(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, _ = api_client

    response = client.post(
        "/capabilities",
        json={
            **capability_payload(),
            "metadata": {"api_key_ref": "do-not-store"},
        },
    )

    assert response.status_code == 422


def test_capability_update_rejects_unsafe_metadata(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, _ = api_client
    created = client.post("/capabilities", json=capability_payload())
    capability_id = created.json()["id"]

    response = client.patch(
        f"/capabilities/{capability_id}",
        json={"metadata": {"client_secret": "do-not-store"}},
    )

    assert response.status_code == 422


def test_audit_log_created_on_capability_create(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client

    response = client.post("/capabilities", json=capability_payload())

    assert response.status_code == 201
    [audit_log] = fetch_audit_logs(session_factory)
    assert audit_log.event_type == "capability_created"
    assert audit_log.actor_type is ActorType.DEVELOPMENT
    assert audit_log.actor_id == "dev-placeholder"
    assert audit_log.entity_type == "capability"
    assert audit_log.entity_id == response.json()["id"]
    assert audit_log.metadata_ == {
        "operation": "create",
        "capability_type": "tool",
        "status": "active",
        "risk_level": "medium",
    }


def test_audit_log_created_on_capability_update(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    created = client.post("/capabilities", json=capability_payload())
    capability_id = created.json()["id"]

    response = client.patch(
        f"/capabilities/{capability_id}",
        json={
            "metadata": {"domain": "support", "review_status": "paused"},
        },
    )

    assert response.status_code == 200
    update_log = fetch_audit_logs(session_factory)[-1]
    assert update_log.event_type == "capability_updated"
    assert update_log.actor_type is ActorType.DEVELOPMENT
    assert update_log.actor_id == "dev-placeholder"
    assert update_log.entity_type == "capability"
    assert update_log.entity_id == capability_id
    assert update_log.metadata_ == {"updated_fields": "metadata"}
    assert "review_status" not in str(update_log.metadata_)


def test_audit_log_created_on_capability_status_change(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    created = client.post("/capabilities", json=capability_payload(status="active"))
    capability_id = created.json()["id"]

    response = client.patch(
        f"/capabilities/{capability_id}",
        json={"status": "disabled"},
    )

    assert response.status_code == 200
    status_log = fetch_audit_logs(session_factory)[-1]
    assert status_log.event_type == "capability_status_changed"
    assert status_log.actor_type is ActorType.DEVELOPMENT
    assert status_log.actor_id == "dev-placeholder"
    assert status_log.entity_type == "capability"
    assert status_log.entity_id == capability_id
    assert status_log.metadata_ == {
        "updated_fields": "status",
        "status_from": "active",
        "status_to": "disabled",
    }


def fetch_audit_logs(session_factory: SessionFactory) -> list[AuditLog]:
    with session_factory() as session:
        statement = select(AuditLog).order_by(AuditLog.created_at, AuditLog.id)
        return list(session.scalars(statement).all())


def capability_payload(
    *,
    name: str = "Send support email",
    status: str = "active",
) -> dict[str, object]:
    return {
        "name": name,
        "description": "Send a governed support follow-up email.",
        "capability_type": "tool",
        "external_ref": "tool:send_email",
        "status": status,
        "risk_level": "medium",
        "metadata": {"domain": "support", "operation": "send_email"},
    }
