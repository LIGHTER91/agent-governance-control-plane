from collections.abc import Callable, Iterator
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from agent_governance_api.auth import ActorContext, get_current_actor
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


def test_submit_review_request_for_draft_version_succeeds(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    policy_id = create_policy(client)
    version = create_policy_version_draft(client, policy_id=policy_id)

    response = client.post(
        f"/policy-versions/{version['id']}/review-requests",
        json={"request_note": "Ready for governance review."},
    )
    refreshed_version = client.get(f"/policy-versions/{version['id']}")

    assert response.status_code == 201
    body = response.json()
    assert UUID(body["id"])
    assert body["policy_version_id"] == version["id"]
    assert body["policy_id"] == policy_id
    assert body["status"] == "pending"
    assert body["request_note"] == "Ready for governance review."
    assert body["decision_note"] is None
    assert body["requested_by_actor_type"] == "development"
    assert body["requested_by_actor_id"] == "dev-placeholder"
    assert body["policy_name"] == "Policy Studio email guard"
    assert body["policy_version_number"] == 1
    assert refreshed_version.status_code == 200
    assert refreshed_version.json()["status"] == "draft"
    assert refreshed_version.json()["activated_at"] is None

    audit_log = fetch_audit_logs(session_factory)[-1]
    assert audit_log.event_type == "policy_version_review_requested"
    assert audit_log.entity_type == "policy_version_review_request"
    assert audit_log.entity_id == body["id"]
    assert audit_log.metadata_ == {
        "policy_id": policy_id,
        "policy_version_id": version["id"],
        "policy_version_number": 1,
        "policy_version_status": "draft",
        "review_status": "pending",
        "request_note": "Ready for governance review.",
    }


def test_submit_review_request_for_active_version_fails(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, _ = api_client
    policy_id = create_policy(client)
    version = approve_and_activate_policy_version(
        client,
        create_policy_version_draft(client, policy_id=policy_id),
    )

    response = client.post(f"/policy-versions/{version['id']}/review-requests")

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Only draft PolicyVersions can be submitted for review."
    )


def test_duplicate_pending_review_request_fails(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, _ = api_client
    policy_id = create_policy(client)
    version = create_policy_version_draft(client, policy_id=policy_id)
    first = client.post(f"/policy-versions/{version['id']}/review-requests")

    second = client.post(f"/policy-versions/{version['id']}/review-requests")

    assert first.status_code == 201
    assert second.status_code == 409
    assert second.json()["detail"] == (
        "PolicyVersion already has a pending review request."
    )


def test_reviewer_can_approve_pending_review_without_activation(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    policy_id = create_policy(client)
    version = create_policy_version_draft(client, policy_id=policy_id)
    review_request = client.post(
        f"/policy-versions/{version['id']}/review-requests",
    ).json()
    set_current_actor(reviewer_actor())

    response = client.post(
        f"/policy-version-review-requests/{review_request['id']}/approve",
        json={"decision_note": "Approved for later activation planning."},
    )
    refreshed_version = client.get(f"/policy-versions/{version['id']}")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "approved"
    assert body["reviewer_actor_type"] == "user"
    assert body["reviewer_actor_id"] == "user:reviewer-1"
    assert body["decision_note"] == "Approved for later activation planning."
    assert body["decided_at"] is not None
    assert refreshed_version.status_code == 200
    assert refreshed_version.json()["status"] == "draft"
    assert refreshed_version.json()["activated_at"] is None

    audit_log = fetch_audit_logs(session_factory)[-1]
    assert audit_log.event_type == "policy_version_review_approved"
    assert audit_log.metadata_["review_status"] == "approved"
    assert audit_log.metadata_["policy_version_status"] == "draft"


def test_reviewer_can_reject_pending_review_without_activation(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    policy_id = create_policy(client)
    version = create_policy_version_draft(client, policy_id=policy_id)
    review_request = client.post(
        f"/policy-versions/{version['id']}/review-requests",
    ).json()
    set_current_actor(reviewer_actor())

    response = client.post(
        f"/policy-version-review-requests/{review_request['id']}/reject",
        json={"decision_note": "Needs clearer owner context."},
    )
    refreshed_version = client.get(f"/policy-versions/{version['id']}")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "rejected"
    assert body["decision_note"] == "Needs clearer owner context."
    assert refreshed_version.status_code == 200
    assert refreshed_version.json()["status"] == "draft"
    assert refreshed_version.json()["activated_at"] is None

    audit_log = fetch_audit_logs(session_factory)[-1]
    assert audit_log.event_type == "policy_version_review_rejected"
    assert audit_log.metadata_["review_status"] == "rejected"
    assert audit_log.metadata_["policy_version_status"] == "draft"


def test_approve_or_reject_non_pending_review_request_fails(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, _ = api_client
    policy_id = create_policy(client)
    version = create_policy_version_draft(client, policy_id=policy_id)
    review_request = client.post(
        f"/policy-versions/{version['id']}/review-requests",
    ).json()
    set_current_actor(reviewer_actor())
    approved = client.post(
        f"/policy-version-review-requests/{review_request['id']}/approve",
    )

    rejected = client.post(
        f"/policy-version-review-requests/{review_request['id']}/reject",
    )

    assert approved.status_code == 200
    assert rejected.status_code == 409
    assert rejected.json()["detail"] == (
        "Only pending PolicyVersion review requests can transition."
    )


def test_reviewer_and_auditor_can_list_policy_version_review_requests(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, _ = api_client
    policy_id = create_policy(client)
    version = create_policy_version_draft(client, policy_id=policy_id)
    review_request = client.post(
        f"/policy-versions/{version['id']}/review-requests",
    ).json()

    for actor in (reviewer_actor(), auditor_actor()):
        set_current_actor(actor)
        response = client.get("/policy-version-review-requests")
        assert response.status_code == 200
        assert [item["id"] for item in response.json()] == [review_request["id"]]


def test_actor_without_review_role_cannot_list_or_decide_reviews(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, _ = api_client
    policy_id = create_policy(client)
    version = create_policy_version_draft(client, policy_id=policy_id)
    review_request = client.post(
        f"/policy-versions/{version['id']}/review-requests",
    ).json()
    set_current_actor(
        ActorContext(
            actor_type=ActorType.USER,
            actor_id="user:viewer-1",
            roles=("viewer",),
        )
    )

    list_response = client.get("/policy-version-review-requests")
    approve_response = client.post(
        f"/policy-version-review-requests/{review_request['id']}/approve",
    )

    assert list_response.status_code == 403
    assert list_response.json()["detail"] == (
        "Actor requires one of these roles: reviewer, auditor, platform_admin."
    )
    assert approve_response.status_code == 403
    assert approve_response.json()["detail"] == (
        "Actor requires one of these roles: reviewer, platform_admin."
    )


def test_requester_cannot_review_own_policy_version_without_admin_role(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, _ = api_client
    requester = reviewer_actor()
    set_current_actor(requester)
    policy_id = create_policy(client)
    version = create_policy_version_draft(client, policy_id=policy_id)
    review_request = client.post(
        f"/policy-versions/{version['id']}/review-requests",
    ).json()

    response = client.post(
        f"/policy-version-review-requests/{review_request['id']}/approve",
    )

    assert response.status_code == 403
    assert response.json()["detail"] == (
        "Requester cannot approve or reject their own PolicyVersion review."
    )


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


def create_policy_version_draft(
    client: TestClient,
    *,
    policy_id: str,
) -> dict[str, object]:
    response = client.post(
        f"/policies/{policy_id}/versions/draft",
        json={
            "change_summary": "Policy Studio draft save.",
            "policy_snapshot": {
                "name": "Policy Studio email guard",
                "description": "Drafted in Policy Studio.",
                "status": "draft",
            },
            "rule_snapshots": [
                {
                    "name": "Studio email review rule",
                    "description": "Compiled from Policy Studio.",
                    "condition": (
                        '{"decision":"require_human_review",'
                        '"reason":"Email tool use requires review in this draft.",'
                        '"tool_name":"send_email"}'
                    ),
                }
            ],
        },
    )

    assert response.status_code == 201
    return response.json()


def approve_and_activate_policy_version(
    client: TestClient,
    version: dict[str, object],
) -> dict[str, object]:
    client.post(f"/policy-versions/{version['id']}/submit-review")
    client.post(f"/policy-versions/{version['id']}/approve")
    response = client.post(f"/policy-versions/{version['id']}/activate")

    assert response.status_code == 200
    return response.json()


def set_current_actor(actor: ActorContext) -> None:
    app.dependency_overrides[get_current_actor] = lambda: actor


def reviewer_actor() -> ActorContext:
    return ActorContext(
        actor_type=ActorType.USER,
        actor_id="user:reviewer-1",
        roles=("reviewer",),
    )


def auditor_actor() -> ActorContext:
    return ActorContext(
        actor_type=ActorType.USER,
        actor_id="user:auditor-1",
        roles=("auditor",),
    )


def fetch_audit_logs(session_factory: SessionFactory) -> list[AuditLog]:
    with session_factory() as session:
        statement = select(AuditLog).order_by(AuditLog.created_at, AuditLog.id)
        return list(session.scalars(statement).all())
