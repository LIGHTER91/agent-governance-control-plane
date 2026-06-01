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


def test_create_policy_version_snapshots_policy_rules_and_check_steps(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    policy_id = create_policy(client)
    rule_id = create_policy_rule(client, policy_id=policy_id)
    step_id = create_policy_check_step(client, policy_rule_id=rule_id)

    response = client.post(
        f"/policies/{policy_id}/versions",
        json={"change_summary": "Initial reviewed policy bundle."},
    )

    assert response.status_code == 201
    body = response.json()
    assert UUID(body["id"])
    assert body["policy_id"] == policy_id
    assert body["source_version_id"] is None
    assert body["version_number"] == 1
    assert body["status"] == "draft"
    assert body["change_summary"] == "Initial reviewed policy bundle."
    assert body["policy_snapshot"] == {
        "id": policy_id,
        "name": "Email policy",
        "description": "Governed email policy.",
        "status": "draft",
    }
    assert body["rule_snapshots"] == [
        {
            "id": rule_id,
            "policy_id": policy_id,
            "name": "Email review rule",
            "description": "Require review before governed email tool use.",
            "condition": (
                '{"decision":"require_human_review",'
                '"reason":"Email tool use requires human review.",'
                '"tool_name":"send_email"}'
            ),
        }
    ]
    assert body["check_step_snapshots"] == [
        {
            "id": step_id,
            "policy_rule_id": rule_id,
            "check_tool_id": None,
            "check_type": "data_usage_profile_status",
            "target_selector": "source_ids",
            "required": True,
            "failure_behavior": "require_human_review",
            "min_confidence": 0.8,
            "status": "active",
            "evidence_retention": "evidence_bundle",
            "metadata": {"purpose": "runtime_metadata_pre_check"},
        }
    ]
    assert body["created_by_actor_type"] == "development"
    assert body["created_by_actor_id"] == "dev-placeholder"

    audit_log = fetch_audit_logs(session_factory)[-1]
    assert audit_log.event_type == "policy_version_created"
    assert audit_log.actor_type is ActorType.DEVELOPMENT
    assert audit_log.actor_id == "dev-placeholder"
    assert audit_log.entity_type == "policy_version"
    assert audit_log.entity_id == body["id"]
    assert audit_log.metadata_ == {
        "policy_id": policy_id,
        "version_number": 1,
        "status": "draft",
        "change_summary": "Initial reviewed policy bundle.",
    }
    assert "send_email" not in str(audit_log.metadata_)
    assert "runtime_metadata_pre_check" not in str(audit_log.metadata_)


def test_list_and_get_policy_versions(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, _ = api_client
    policy_id = create_policy(client)
    first = create_policy_version(client, policy_id=policy_id, change_summary="First.")
    second = create_policy_version(
        client,
        policy_id=policy_id,
        change_summary="Second.",
    )

    list_response = client.get(f"/policies/{policy_id}/versions")
    get_response = client.get(f"/policy-versions/{second['id']}")

    assert list_response.status_code == 200
    assert [version["id"] for version in list_response.json()] == [
        first["id"],
        second["id"],
    ]
    assert get_response.status_code == 200
    assert get_response.json()["id"] == second["id"]
    assert get_response.json()["version_number"] == 2


def test_policy_version_review_and_activation_lifecycle(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    policy_id = create_policy(client)
    version = create_policy_version(client, policy_id=policy_id)

    submitted = client.post(
        f"/policy-versions/{version['id']}/submit-review",
    )
    approved = client.post(
        f"/policy-versions/{version['id']}/approve",
        json={"review_note": "Reviewed with the Agent Owner."},
    )
    activated = client.post(f"/policy-versions/{version['id']}/activate")

    assert submitted.status_code == 200
    assert submitted.json()["status"] == "under_review"
    assert submitted.json()["review_requested_by_actor_type"] == "development"
    assert submitted.json()["submitted_at"] is not None
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"
    assert approved.json()["reviewed_by_actor_type"] == "development"
    assert approved.json()["review_note"] == "Reviewed with the Agent Owner."
    assert approved.json()["approved_at"] is not None
    assert activated.status_code == 200
    assert activated.json()["status"] == "active"
    assert activated.json()["activated_at"] is not None

    event_types = [log.event_type for log in fetch_audit_logs(session_factory)]
    assert event_types[-3:] == [
        "policy_version_submitted_for_review",
        "policy_version_approved",
        "policy_version_activated",
    ]


def test_activating_policy_version_supersedes_existing_active_version(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    policy_id = create_policy(client)
    first = approve_and_activate_policy_version(
        client,
        create_policy_version(client, policy_id=policy_id),
    )
    second = create_policy_version(client, policy_id=policy_id)

    client.post(f"/policy-versions/{second['id']}/submit-review")
    client.post(f"/policy-versions/{second['id']}/approve")
    activated_second = client.post(f"/policy-versions/{second['id']}/activate")
    refreshed_first = client.get(f"/policy-versions/{first['id']}")

    assert activated_second.status_code == 200
    assert activated_second.json()["status"] == "active"
    assert refreshed_first.status_code == 200
    assert refreshed_first.json()["status"] == "superseded"
    assert refreshed_first.json()["superseded_at"] is not None

    event_types = [log.event_type for log in fetch_audit_logs(session_factory)]
    assert "policy_version_superseded" in event_types
    assert event_types[-2:] == [
        "policy_version_superseded",
        "policy_version_activated",
    ]


def test_policy_version_invalid_transitions_return_conflict(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, _ = api_client
    policy_id = create_policy(client)
    version = create_policy_version(client, policy_id=policy_id)

    activate_draft = client.post(f"/policy-versions/{version['id']}/activate")
    submit = client.post(f"/policy-versions/{version['id']}/submit-review")
    archive_under_review = client.post(f"/policy-versions/{version['id']}/archive")
    approve = client.post(f"/policy-versions/{version['id']}/approve")
    reject_approved = client.post(f"/policy-versions/{version['id']}/reject")

    assert activate_draft.status_code == 409
    assert activate_draft.json()["detail"] == (
        "Only approved policy versions can be activated."
    )
    assert submit.status_code == 200
    assert archive_under_review.status_code == 409
    assert approve.status_code == 200
    assert reject_approved.status_code == 409


def test_policy_version_reject_archive_and_rollback_copy(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    policy_id = create_policy(client)
    version = create_policy_version(client, policy_id=policy_id)
    client.post(f"/policy-versions/{version['id']}/submit-review")
    rejected = client.post(
        f"/policy-versions/{version['id']}/reject",
        json={"review_note": "Needs clearer ownership."},
    )

    rollback_copy = client.post(
        f"/policy-versions/{version['id']}/rollback-copy",
        json={"change_summary": "Create corrective draft from rejected snapshot."},
    )
    archived = client.post(f"/policy-versions/{version['id']}/archive")

    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"
    assert rollback_copy.status_code == 201
    rollback_body = rollback_copy.json()
    assert rollback_body["status"] == "draft"
    assert rollback_body["source_version_id"] == version["id"]
    assert rollback_body["version_number"] == 2
    assert rollback_body["policy_snapshot"] == rejected.json()["policy_snapshot"]
    assert archived.status_code == 200
    assert archived.json()["status"] == "archived"

    event_types = [log.event_type for log in fetch_audit_logs(session_factory)]
    assert event_types[-3:] == [
        "policy_version_rejected",
        "policy_version_rollback_copy_created",
        "policy_version_archived",
    ]


def test_policy_version_rollback_copy_rejects_mutable_source_status(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, _ = api_client
    policy_id = create_policy(client)
    version = create_policy_version(client, policy_id=policy_id)

    response = client.post(
        f"/policy-versions/{version['id']}/rollback-copy",
        json={"change_summary": "Try to copy a draft."},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Only approved, rejected, active, or superseded policy versions can be copied "
        "to a new draft."
    )


def test_policy_version_unknown_policy_and_version_return_404(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, _ = api_client
    missing_id = "00000000-0000-0000-0000-000000000001"

    create_response = client.post(
        f"/policies/{missing_id}/versions",
        json={"change_summary": "Snapshot missing policy."},
    )
    list_response = client.get(f"/policies/{missing_id}/versions")
    get_response = client.get(f"/policy-versions/{missing_id}")

    assert create_response.status_code == 404
    assert create_response.json()["detail"] == "Policy not found."
    assert list_response.status_code == 404
    assert list_response.json()["detail"] == "Policy not found."
    assert get_response.status_code == 404
    assert get_response.json()["detail"] == "PolicyVersion not found."


def test_policy_version_create_rejects_blank_change_summary(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, _ = api_client
    policy_id = create_policy(client)

    response = client.post(
        f"/policies/{policy_id}/versions",
        json={"change_summary": " "},
    )

    assert response.status_code == 422


def approve_and_activate_policy_version(
    client: TestClient,
    version: dict[str, object],
) -> dict[str, object]:
    client.post(f"/policy-versions/{version['id']}/submit-review")
    client.post(f"/policy-versions/{version['id']}/approve")
    response = client.post(f"/policy-versions/{version['id']}/activate")

    assert response.status_code == 200
    return response.json()


def create_policy(client: TestClient, *, name: str = "Email policy") -> str:
    response = client.post(
        "/policies",
        json={
            "name": name,
            "description": "Governed email policy.",
            "status": "draft",
        },
    )

    assert response.status_code == 201
    return response.json()["id"]


def create_policy_rule(client: TestClient, *, policy_id: str) -> str:
    response = client.post(
        "/policy-rules",
        json={
            "policy_id": policy_id,
            "name": "Email review rule",
            "description": "Require review before governed email tool use.",
            "condition": (
                '{"decision":"require_human_review",'
                '"reason":"Email tool use requires human review.",'
                '"tool_name":"send_email"}'
            ),
        },
    )

    assert response.status_code == 201
    return response.json()["id"]


def create_policy_check_step(
    client: TestClient,
    *,
    policy_rule_id: str,
) -> str:
    response = client.post(
        "/policy-check-steps",
        json={
            "policy_rule_id": policy_rule_id,
            "check_tool_id": None,
            "check_type": "data_usage_profile_status",
            "target_selector": "source_ids",
            "required": True,
            "failure_behavior": "require_human_review",
            "min_confidence": 0.8,
            "status": "active",
            "evidence_retention": "evidence_bundle",
            "metadata": {"purpose": "runtime_metadata_pre_check"},
        },
    )

    assert response.status_code == 201
    return response.json()["id"]


def create_policy_version(
    client: TestClient,
    *,
    policy_id: str,
    change_summary: str = "Snapshot current policy state.",
) -> dict[str, object]:
    response = client.post(
        f"/policies/{policy_id}/versions",
        json={"change_summary": change_summary},
    )

    assert response.status_code == 201
    return response.json()


def fetch_audit_logs(session_factory: SessionFactory) -> list[AuditLog]:
    with session_factory() as session:
        statement = select(AuditLog).order_by(AuditLog.created_at, AuditLog.id)
        return list(session.scalars(statement).all())
