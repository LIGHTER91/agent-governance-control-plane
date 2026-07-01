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
    PolicyFolder,
    PolicyVersion,
    PolicyVersionStatus,
)
from agent_governance_api.policy_folders import POLICY_FOLDER_NOT_EMPTY_DETAIL

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


def test_create_and_list_policy_folders(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client

    first = client.post(
        "/policy-folders",
        json=folder_payload(name="Runtime controls", sort_order=20),
    )
    second = client.post(
        "/policy-folders",
        json=folder_payload(name="Access governance", sort_order=10),
    )
    response = client.get("/policy-folders")

    assert first.status_code == 201
    assert second.status_code == 201
    body = first.json()
    assert UUID(body["id"])
    assert body["name"] == "Runtime controls"
    assert body["description"] == "Policies grouped for authoring workflow."
    assert body["color"] == "#8b78f6"
    assert body["sort_order"] == 20
    assert body["created_at"]
    assert body["updated_at"]
    assert response.status_code == 200
    assert [folder["name"] for folder in response.json()] == [
        "Access governance",
        "Runtime controls",
    ]

    audit_logs = fetch_audit_logs(session_factory)
    assert [log.event_type for log in audit_logs] == [
        "policy_folder_created",
        "policy_folder_created",
    ]
    assert audit_logs[0].actor_type is ActorType.DEVELOPMENT
    assert audit_logs[0].actor_id == "dev-placeholder"


def test_update_and_delete_empty_policy_folder(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    created = client.post("/policy-folders", json=folder_payload())
    folder_id = created.json()["id"]

    update_response = client.patch(
        f"/policy-folders/{folder_id}",
        json={
            "name": "Reviewed policies",
            "description": None,
            "color": "#65d88f",
            "sort_order": 3,
        },
    )
    delete_response = client.delete(f"/policy-folders/{folder_id}")

    assert update_response.status_code == 200
    assert update_response.json()["name"] == "Reviewed policies"
    assert update_response.json()["description"] is None
    assert update_response.json()["color"] == "#65d88f"
    assert update_response.json()["sort_order"] == 3
    assert delete_response.status_code == 204
    assert delete_response.content == b""

    with session_factory() as session:
        assert session.get(PolicyFolder, UUID(folder_id)) is None

    assert [log.event_type for log in fetch_audit_logs(session_factory)] == [
        "policy_folder_created",
        "policy_folder_updated",
        "policy_folder_deleted",
    ]


def test_delete_non_empty_policy_folder_fails(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    folder = client.post("/policy-folders", json=folder_payload()).json()
    policy = client.post(
        "/policies",
        json=policy_payload(folder_id=folder["id"]),
    )

    response = client.delete(f"/policy-folders/{folder['id']}")

    assert policy.status_code == 201
    assert response.status_code == 409
    assert response.json()["detail"] == POLICY_FOLDER_NOT_EMPTY_DETAIL
    with session_factory() as session:
        assert session.get(PolicyFolder, UUID(folder["id"])) is not None


def test_policy_folder_create_move_and_null_folder_behavior(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    initial_folder = client.post(
        "/policy-folders",
        json=folder_payload(name="Access governance"),
    ).json()
    target_folder = client.post(
        "/policy-folders",
        json=folder_payload(name="Runtime controls", color="#65d88f"),
    ).json()

    created_policy = client.post(
        "/policies",
        json=policy_payload(folder_id=initial_folder["id"]),
    )
    policy_id = created_policy.json()["id"]
    uncategorized_policy = client.post(
        "/policies",
        json=policy_payload(name="No folder policy", folder_id=None),
    )

    move_response = client.patch(
        f"/policies/{policy_id}",
        json={"folder_id": target_folder["id"]},
    )
    null_move_response = client.patch(
        f"/policies/{policy_id}",
        json={"folder_id": None},
    )
    list_response = client.get("/policies")

    assert created_policy.status_code == 201
    assert created_policy.json()["folder_id"] == initial_folder["id"]
    assert created_policy.json()["folder_name"] == "Access governance"
    assert uncategorized_policy.status_code == 201
    assert uncategorized_policy.json()["folder_id"] is None
    assert uncategorized_policy.json()["folder_name"] is None
    assert move_response.status_code == 200
    assert move_response.json()["folder_id"] == target_folder["id"]
    assert move_response.json()["folder_name"] == "Runtime controls"
    assert null_move_response.status_code == 200
    assert null_move_response.json()["folder_id"] is None
    assert null_move_response.json()["folder_name"] is None

    policies_by_name = {policy["name"]: policy for policy in list_response.json()}
    assert policies_by_name["Email tool review policy"]["folder_id"] is None
    assert policies_by_name["Email tool review policy"]["folder_name"] is None
    assert policies_by_name["No folder policy"]["folder_id"] is None
    assert policies_by_name["No folder policy"]["folder_name"] is None

    with session_factory() as session:
        policy = session.get(Policy, UUID(policy_id))
        assert policy is not None
        assert policy.folder_id is None

    move_logs = [
        log
        for log in fetch_audit_logs(session_factory)
        if log.event_type == "policy_moved_to_folder"
    ]
    assert [log.metadata_["folder_id_to"] for log in move_logs] == [
        target_folder["id"],
        None,
    ]


def test_folder_only_move_is_allowed_for_policy_with_active_version(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    folder = client.post(
        "/policy-folders",
        json=folder_payload(name="Runtime controls"),
    ).json()
    created_policy = client.post(
        "/policies",
        json=policy_payload(name="Versioned policy", folder_id=None),
    ).json()
    policy_id = created_policy["id"]
    now = datetime.now(UTC)

    with session_factory() as session:
        version = PolicyVersion(
            id=uuid4(),
            policy_id=UUID(policy_id),
            version_number=1,
            status=PolicyVersionStatus.ACTIVE,
            change_summary="Reviewed active version.",
            policy_snapshot={
                "name": created_policy["name"],
                "description": created_policy["description"],
                "status": created_policy["status"],
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

    move_response = client.patch(
        f"/policies/{policy_id}",
        json={"folder_id": folder["id"]},
    )
    content_response = client.patch(
        f"/policies/{policy_id}",
        json={"description": "Runtime-affecting edit remains blocked."},
    )

    assert move_response.status_code == 200
    assert move_response.json()["folder_id"] == folder["id"]
    assert move_response.json()["folder_name"] == "Runtime controls"
    assert content_response.status_code == 409
    with session_factory() as session:
        policy = session.get(Policy, UUID(policy_id))
        assert policy is not None
        assert policy.folder_id == UUID(folder["id"])
        move_log = session.scalar(
            select(AuditLog).where(AuditLog.event_type == "policy_moved_to_folder")
        )
        assert move_log is not None
        assert move_log.metadata_ == {
            "updated_fields": "folder_id",
            "folder_id_from": None,
            "folder_id_to": folder["id"],
        }


def test_create_policy_rejects_unknown_folder(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, _ = api_client

    response = client.post(
        "/policies",
        json=policy_payload(folder_id="00000000-0000-4000-8000-000000000001"),
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "PolicyFolder not found."


def fetch_audit_logs(session_factory: SessionFactory) -> list[AuditLog]:
    with session_factory() as session:
        statement = select(AuditLog).order_by(AuditLog.created_at, AuditLog.id)
        return list(session.scalars(statement).all())


def folder_payload(
    *,
    name: str = "Policy folder",
    color: str | None = "#8b78f6",
    sort_order: int = 0,
) -> dict[str, object]:
    return {
        "name": name,
        "description": "Policies grouped for authoring workflow.",
        "color": color,
        "sort_order": sort_order,
    }


def policy_payload(
    *,
    name: str = "Email tool review policy",
    folder_id: str | None,
) -> dict[str, object]:
    return {
        "name": name,
        "description": "Require review before governed email tool use.",
        "status": "draft",
        "folder_id": folder_id,
    }
