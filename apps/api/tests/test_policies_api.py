from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from agent_governance_api.database import Base, get_db_session
from agent_governance_api.main import app
from agent_governance_api.models import (
    ActorType,
    AuditLog,
    Policy,
    PolicyDecision,
    PolicyDecisionValue,
    PolicyVersion,
    PolicyVersionReviewRequest,
    PolicyVersionReviewRequestStatus,
    PolicyVersionStatus,
)
from agent_governance_api.policies import (
    POLICY_ARCHIVE_ACTIVE_VERSION_DETAIL,
    POLICY_DELETE_GOVERNANCE_HISTORY_DETAIL,
)
from agent_governance_api.policy_live_edit_guard import POLICY_LIVE_EDIT_BLOCKED_DETAIL

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


def test_update_policy_is_blocked_when_active_policy_version_exists(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    created = client.post("/policies", json=policy_payload())
    policy_id = created.json()["id"]
    active_version_id = create_active_policy_version(
        session_factory,
        policy_id=policy_id,
    )

    response = client.patch(
        f"/policies/{policy_id}",
        json={"description": "Bypass the reviewed version."},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == POLICY_LIVE_EDIT_BLOCKED_DETAIL
    with session_factory() as session:
        policy = session.get(Policy, UUID(policy_id))
        assert policy is not None
        assert policy.description == "Require review before governed email tool use."

    blocked_log = fetch_audit_logs(session_factory)[-1]
    assert blocked_log.event_type == "policy_live_edit_blocked"
    assert blocked_log.entity_type == "policy"
    assert blocked_log.entity_id == policy_id
    assert blocked_log.metadata_ == {
        "operation": "patch_policy",
        "policy_id": policy_id,
        "active_policy_version_id": str(active_version_id),
        "active_policy_version_number": 1,
        "reason": POLICY_LIVE_EDIT_BLOCKED_DETAIL,
    }


def test_archive_draft_policy_succeeds(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    created = client.post("/policies", json=policy_payload(status="draft"))
    policy_id = created.json()["id"]

    response = client.post(f"/policies/{policy_id}/archive")

    assert response.status_code == 200
    assert response.json()["status"] == "archived"
    with session_factory() as session:
        policy = session.get(Policy, UUID(policy_id))
        assert policy is not None
        assert policy.status.value == "archived"

    archive_log = fetch_audit_logs(session_factory)[-1]
    assert archive_log.event_type == "policy_archived"
    assert archive_log.actor_type is ActorType.DEVELOPMENT
    assert archive_log.actor_id == "dev-placeholder"
    assert archive_log.entity_type == "policy"
    assert archive_log.entity_id == policy_id
    assert archive_log.metadata_ == {
        "status_from": "draft",
        "status_to": "archived",
        "history_retained": True,
    }


def test_archive_policy_with_active_policy_version_is_blocked(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    created = client.post("/policies", json=policy_payload(status="draft"))
    policy_id = created.json()["id"]
    create_active_policy_version(session_factory, policy_id=policy_id)

    response = client.post(f"/policies/{policy_id}/archive")

    assert response.status_code == 409
    assert response.json()["detail"] == POLICY_ARCHIVE_ACTIVE_VERSION_DETAIL
    with session_factory() as session:
        policy = session.get(Policy, UUID(policy_id))
        assert policy is not None
        assert policy.status.value == "draft"


def test_delete_draft_only_policy_succeeds(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    created = client.post("/policies", json=policy_payload(status="draft"))
    policy_id = created.json()["id"]

    response = client.delete(f"/policies/{policy_id}")

    assert response.status_code == 204
    assert response.content == b""
    with session_factory() as session:
        assert session.get(Policy, UUID(policy_id)) is None

    delete_log = fetch_audit_logs(session_factory)[-1]
    assert delete_log.event_type == "policy_deleted"
    assert delete_log.entity_type == "policy"
    assert delete_log.entity_id == policy_id
    assert delete_log.metadata_ == {
        "status": "draft",
        "rule_count": 0,
        "check_step_count": 0,
        "history_retained": True,
    }


def test_delete_policy_with_policy_version_fails(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    created = client.post("/policies", json=policy_payload(status="draft"))
    policy_id = created.json()["id"]
    create_active_policy_version(session_factory, policy_id=policy_id)

    response = client.delete(f"/policies/{policy_id}")

    assert response.status_code == 409
    assert response.json()["detail"] == POLICY_DELETE_GOVERNANCE_HISTORY_DETAIL
    with session_factory() as session:
        assert session.get(Policy, UUID(policy_id)) is not None


def test_delete_policy_with_review_request_fails(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    created = client.post("/policies", json=policy_payload(status="draft"))
    policy_id = created.json()["id"]
    create_policy_version_review_request(session_factory, policy_id=policy_id)

    response = client.delete(f"/policies/{policy_id}")

    assert response.status_code == 409
    assert response.json()["detail"] == POLICY_DELETE_GOVERNANCE_HISTORY_DETAIL
    with session_factory() as session:
        assert session.get(Policy, UUID(policy_id)) is not None


def test_delete_policy_with_policy_decision_fails(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    created = client.post("/policies", json=policy_payload(status="draft"))
    policy_id = created.json()["id"]
    create_policy_decision(session_factory, policy_id=policy_id)

    response = client.delete(f"/policies/{policy_id}")

    assert response.status_code == 409
    assert response.json()["detail"] == POLICY_DELETE_GOVERNANCE_HISTORY_DETAIL
    with session_factory() as session:
        assert session.get(Policy, UUID(policy_id)) is not None


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


def create_active_policy_version(
    session_factory: SessionFactory,
    *,
    policy_id: str,
) -> UUID:
    now = datetime.now(UTC)
    version_id = uuid4()
    with session_factory() as session:
        policy = session.get(Policy, UUID(policy_id))
        assert policy is not None
        version = PolicyVersion(
            id=version_id,
            policy_id=policy.id,
            version_number=1,
            status=PolicyVersionStatus.ACTIVE,
            change_summary="Reviewed active version.",
            policy_snapshot={
                "name": policy.name,
                "description": policy.description,
                "status": policy.status.value,
            },
            rule_snapshots=[],
            check_step_snapshots=[],
            created_by_actor_type=ActorType.DEVELOPMENT,
            created_by_actor_id="dev-placeholder",
            created_at=now,
            updated_at=now,
            activated_at=now,
        )
        session.add(version)
        session.commit()
    return version_id


def create_policy_version_review_request(
    session_factory: SessionFactory,
    *,
    policy_id: str,
) -> UUID:
    now = datetime.now(UTC)
    version_id = uuid4()
    request_id = uuid4()
    with session_factory() as session:
        policy = session.get(Policy, UUID(policy_id))
        assert policy is not None
        version = PolicyVersion(
            id=version_id,
            policy_id=policy.id,
            version_number=1,
            status=PolicyVersionStatus.DRAFT,
            change_summary="Draft under review.",
            policy_snapshot={
                "name": policy.name,
                "description": policy.description,
                "status": policy.status.value,
            },
            rule_snapshots=[],
            check_step_snapshots=[],
            created_by_actor_type=ActorType.DEVELOPMENT,
            created_by_actor_id="dev-placeholder",
            created_at=now,
            updated_at=now,
        )
        review_request = PolicyVersionReviewRequest(
            id=request_id,
            policy_version_id=version.id,
            policy_id=policy.id,
            status=PolicyVersionReviewRequestStatus.PENDING,
            requested_by_actor_type=ActorType.DEVELOPMENT,
            requested_by_actor_id="dev-placeholder",
            created_at=now,
        )
        session.add_all([version, review_request])
        session.commit()
    return request_id


def create_policy_decision(
    session_factory: SessionFactory,
    *,
    policy_id: str,
) -> UUID:
    decision_id = uuid4()
    with session_factory() as session:
        session.add(
            PolicyDecision(
                id=decision_id,
                policy_id=UUID(policy_id),
                decision=PolicyDecisionValue.ALLOW,
                reason="Draft policy has runtime decision history.",
                created_at=datetime.now(UTC),
            )
        )
        session.commit()
    return decision_id


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
