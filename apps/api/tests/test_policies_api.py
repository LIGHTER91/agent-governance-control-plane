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


def test_create_policy(api_client: tuple[TestClient, SessionFactory]) -> None:
    client, _ = api_client

    response = client.post(
        "/policies",
        json=policy_payload(name="Email tool review policy"),
    )

    assert response.status_code == 201
    body = response.json()
    assert UUID(body["id"])
    assert body["name"] == "Email tool review policy"
    assert body["description"] == "Require review before governed email tool use."
    assert body["status"] == "draft"
    assert body["created_at"]
    assert body["updated_at"]


def test_list_policies(api_client: tuple[TestClient, SessionFactory]) -> None:
    client, _ = api_client
    client.post("/policies", json=policy_payload(name="Email tool review policy"))
    client.post("/policies", json=policy_payload(name="Payment tool deny policy"))

    response = client.get("/policies")

    assert response.status_code == 200
    assert {policy["name"] for policy in response.json()} == {
        "Email tool review policy",
        "Payment tool deny policy",
    }


def test_get_policy_by_id(api_client: tuple[TestClient, SessionFactory]) -> None:
    client, _ = api_client
    created = client.post(
        "/policies",
        json=policy_payload(name="Email tool review policy"),
    )
    policy_id = created.json()["id"]

    response = client.get(f"/policies/{policy_id}")

    assert response.status_code == 200
    assert response.json()["id"] == policy_id
    assert response.json()["name"] == "Email tool review policy"


def test_update_policy(api_client: tuple[TestClient, SessionFactory]) -> None:
    client, _ = api_client
    created = client.post("/policies", json=policy_payload())
    policy_id = created.json()["id"]

    response = client.patch(
        f"/policies/{policy_id}",
        json={
            "name": "Updated email review policy",
            "description": None,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Updated email review policy"
    assert body["description"] is None
    assert body["status"] == "draft"


def test_empty_policy_update_is_rejected(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, _ = api_client
    created = client.post("/policies", json=policy_payload())
    policy_id = created.json()["id"]

    response = client.patch(f"/policies/{policy_id}", json={})

    assert response.status_code == 400
    assert response.json()["detail"] == "No update fields provided."


def test_policy_not_found_behavior(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, _ = api_client
    missing_id = "00000000-0000-0000-0000-000000000001"

    response = client.get(f"/policies/{missing_id}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Policy not found."


def test_policy_create_rejects_invalid_status(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, _ = api_client

    response = client.post(
        "/policies",
        json={**policy_payload(), "status": "enabled"},
    )

    assert response.status_code == 422


@pytest.mark.parametrize("name", ["", "   "])
def test_policy_create_rejects_blank_name(
    api_client: tuple[TestClient, SessionFactory],
    name: str,
) -> None:
    client, _ = api_client

    response = client.post("/policies", json=policy_payload(name=name))

    assert response.status_code == 422


def test_policy_update_rejects_blank_name(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, _ = api_client
    created = client.post("/policies", json=policy_payload())
    policy_id = created.json()["id"]

    response = client.patch(f"/policies/{policy_id}", json={"name": " "})

    assert response.status_code == 422


@pytest.mark.parametrize("payload", [{"name": None}, {"status": None}])
def test_policy_update_rejects_null_required_fields(
    api_client: tuple[TestClient, SessionFactory],
    payload: dict[str, object],
) -> None:
    client, _ = api_client
    created = client.post("/policies", json=policy_payload())
    policy_id = created.json()["id"]

    response = client.patch(f"/policies/{policy_id}", json=payload)

    assert response.status_code == 422


def test_audit_log_created_on_policy_create(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client

    response = client.post("/policies", json=policy_payload(status="draft"))

    assert response.status_code == 201
    [audit_log] = fetch_audit_logs(session_factory)
    assert audit_log.event_type == "policy_created"
    assert audit_log.actor_type is ActorType.DEVELOPMENT
    assert audit_log.actor_id == "dev-placeholder"
    assert audit_log.entity_type == "policy"
    assert audit_log.entity_id == response.json()["id"]
    assert audit_log.metadata_ == {"operation": "create", "status": "draft"}


def test_audit_log_created_on_policy_update(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    created = client.post("/policies", json=policy_payload())
    policy_id = created.json()["id"]

    response = client.patch(
        f"/policies/{policy_id}",
        json={"description": "Updated policy description."},
    )

    assert response.status_code == 200
    update_log = fetch_audit_logs(session_factory)[-1]
    assert update_log.event_type == "policy_updated"
    assert update_log.actor_type is ActorType.DEVELOPMENT
    assert update_log.actor_id == "dev-placeholder"
    assert update_log.entity_type == "policy"
    assert update_log.entity_id == policy_id
    assert update_log.metadata_ == {"updated_fields": "description"}


def test_audit_log_created_on_policy_status_change(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    created = client.post("/policies", json=policy_payload(status="draft"))
    policy_id = created.json()["id"]

    response = client.patch(f"/policies/{policy_id}", json={"status": "active"})

    assert response.status_code == 200
    status_log = fetch_audit_logs(session_factory)[-1]
    assert status_log.event_type == "policy_status_changed"
    assert status_log.actor_type is ActorType.DEVELOPMENT
    assert status_log.actor_id == "dev-placeholder"
    assert status_log.entity_type == "policy"
    assert status_log.entity_id == policy_id
    assert status_log.metadata_ == {
        "updated_fields": "status",
        "status_from": "draft",
        "status_to": "active",
    }


def fetch_audit_logs(session_factory: SessionFactory) -> list[AuditLog]:
    with session_factory() as session:
        statement = select(AuditLog).order_by(AuditLog.created_at, AuditLog.id)
        return list(session.scalars(statement).all())


def policy_payload(
    *,
    name: str = "Email tool review policy",
    status: str = "draft",
) -> dict[str, object]:
    return {
        "name": name,
        "description": "Require review before governed email tool use.",
        "status": status,
    }
