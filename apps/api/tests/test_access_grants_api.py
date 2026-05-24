from collections.abc import Callable, Iterator
from uuid import UUID, uuid4

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


def test_create_access_grant(api_client: tuple[TestClient, SessionFactory]) -> None:
    client, _ = api_client

    response = client.post(
        "/access-grants",
        json=access_grant_payload(name="Support email capability access"),
    )

    assert response.status_code == 201
    body = response.json()
    assert UUID(body["id"])
    assert body["name"] == "Support email capability access"
    assert body["grant_type"] == "capability"
    assert body["subject_type"] == "agent"
    assert UUID(body["subject_id"])
    assert body["target_type"] == "capability"
    assert UUID(body["target_id"])
    assert body["external_ref"] is None
    assert body["status"] == "active"
    assert body["granted_by_actor_type"] == "development"
    assert body["granted_by_actor_id"] == "dev-placeholder"
    assert body["reason"] == "Support workflow reviewed."
    assert body["expires_at"] is not None
    assert body["risk_level"] == "medium"
    assert body["metadata"] == {
        "approval_ticket": "GOV-123",
        "review_status": "approved",
    }
    assert "metadata_" not in body


def test_list_access_grants(api_client: tuple[TestClient, SessionFactory]) -> None:
    client, _ = api_client
    client.post(
        "/access-grants",
        json=access_grant_payload(name="Support email capability access"),
    )
    client.post(
        "/access-grants",
        json=access_grant_payload(name="Support knowledge source access"),
    )

    response = client.get("/access-grants")

    assert response.status_code == 200
    assert {access_grant["name"] for access_grant in response.json()} == {
        "Support email capability access",
        "Support knowledge source access",
    }


def test_get_access_grant_by_id(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, _ = api_client
    created = client.post(
        "/access-grants",
        json=access_grant_payload(name="Support email capability access"),
    )
    access_grant_id = created.json()["id"]

    response = client.get(f"/access-grants/{access_grant_id}")

    assert response.status_code == 200
    assert response.json()["id"] == access_grant_id
    assert response.json()["name"] == "Support email capability access"


def test_update_access_grant(api_client: tuple[TestClient, SessionFactory]) -> None:
    client, _ = api_client
    created = client.post("/access-grants", json=access_grant_payload())
    access_grant_id = created.json()["id"]

    response = client.patch(
        f"/access-grants/{access_grant_id}",
        json={
            "description": "Temporarily paused.",
            "risk_level": "high",
            "metadata": {"approval_ticket": "GOV-123", "review_status": "paused"},
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["description"] == "Temporarily paused."
    assert body["risk_level"] == "high"
    assert body["metadata"] == {
        "approval_ticket": "GOV-123",
        "review_status": "paused",
    }
    assert body["granted_by_actor_id"] == "dev-placeholder"


def test_empty_access_grant_update_is_rejected(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, _ = api_client
    created = client.post("/access-grants", json=access_grant_payload())
    access_grant_id = created.json()["id"]

    response = client.patch(f"/access-grants/{access_grant_id}", json={})

    assert response.status_code == 400
    assert response.json()["detail"] == "No update fields provided."


def test_access_grant_not_found_behavior(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, _ = api_client
    missing_id = "00000000-0000-0000-0000-000000000001"

    response = client.get(f"/access-grants/{missing_id}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Access grant not found."


def test_access_grant_create_rejects_unsafe_metadata(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, _ = api_client

    response = client.post(
        "/access-grants",
        json={
            **access_grant_payload(),
            "metadata": {"api_key_ref": "do-not-store"},
        },
    )

    assert response.status_code == 422


def test_access_grant_update_rejects_unsafe_metadata(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, _ = api_client
    created = client.post("/access-grants", json=access_grant_payload())
    access_grant_id = created.json()["id"]

    response = client.patch(
        f"/access-grants/{access_grant_id}",
        json={"metadata": {"client_secret": "do-not-store"}},
    )

    assert response.status_code == 422


def test_access_grant_create_requires_target_id_for_inventory_target(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, _ = api_client
    payload = access_grant_payload()
    payload["target_id"] = None

    response = client.post("/access-grants", json=payload)

    assert response.status_code == 422


def test_audit_log_created_on_access_grant_create(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    payload = access_grant_payload()

    response = client.post("/access-grants", json=payload)

    assert response.status_code == 201
    [audit_log] = fetch_audit_logs(session_factory)
    assert audit_log.event_type == "access_grant_created"
    assert audit_log.actor_type is ActorType.DEVELOPMENT
    assert audit_log.actor_id == "dev-placeholder"
    assert audit_log.entity_type == "access_grant"
    assert audit_log.entity_id == response.json()["id"]
    assert audit_log.metadata_ == {
        "operation": "create",
        "grant_type": "capability",
        "subject_type": "agent",
        "subject_id": payload["subject_id"],
        "target_type": "capability",
        "target_id": payload["target_id"],
        "status": "active",
        "risk_level": "medium",
    }


def test_audit_log_created_on_access_grant_update(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    created = client.post("/access-grants", json=access_grant_payload())
    access_grant_id = created.json()["id"]

    response = client.patch(
        f"/access-grants/{access_grant_id}",
        json={
            "metadata": {"approval_ticket": "GOV-123", "review_status": "paused"},
        },
    )

    assert response.status_code == 200
    update_log = fetch_audit_logs(session_factory)[-1]
    assert update_log.event_type == "access_grant_updated"
    assert update_log.actor_type is ActorType.DEVELOPMENT
    assert update_log.actor_id == "dev-placeholder"
    assert update_log.entity_type == "access_grant"
    assert update_log.entity_id == access_grant_id
    assert update_log.metadata_ == {"updated_fields": "metadata"}
    assert "review_status" not in str(update_log.metadata_)


def test_audit_log_created_on_access_grant_status_change(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    created = client.post(
        "/access-grants",
        json=access_grant_payload(status="active"),
    )
    access_grant_id = created.json()["id"]

    response = client.patch(
        f"/access-grants/{access_grant_id}",
        json={"status": "suspended"},
    )

    assert response.status_code == 200
    status_log = fetch_audit_logs(session_factory)[-1]
    assert status_log.event_type == "access_grant_status_changed"
    assert status_log.actor_type is ActorType.DEVELOPMENT
    assert status_log.actor_id == "dev-placeholder"
    assert status_log.entity_type == "access_grant"
    assert status_log.entity_id == access_grant_id
    assert status_log.metadata_ == {
        "updated_fields": "status",
        "status_from": "active",
        "status_to": "suspended",
    }


def fetch_audit_logs(session_factory: SessionFactory) -> list[AuditLog]:
    with session_factory() as session:
        statement = select(AuditLog).order_by(AuditLog.created_at, AuditLog.id)
        return list(session.scalars(statement).all())


def access_grant_payload(
    *,
    name: str = "Support email capability access",
    status: str = "active",
) -> dict[str, object]:
    return {
        "name": name,
        "description": "Allow the V0 Support Assistant to use the support email tool.",
        "grant_type": "capability",
        "subject_type": "agent",
        "subject_id": str(uuid4()),
        "target_type": "capability",
        "target_id": str(uuid4()),
        "external_ref": None,
        "status": status,
        "reason": "Support workflow reviewed.",
        "expires_at": "2026-12-31T23:59:59Z",
        "risk_level": "medium",
        "metadata": {
            "approval_ticket": "GOV-123",
            "review_status": "approved",
        },
    }
