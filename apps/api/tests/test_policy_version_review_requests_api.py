import json
from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from agent_governance_api.auth import ActorContext, get_current_actor
from agent_governance_api.database import Base, get_db_session
from agent_governance_api.main import app
from agent_governance_api.models import (
    ActorType,
    AuditLog,
    PolicyDecision,
    PolicyVersion,
)

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


def test_review_state_for_draft_without_request_is_not_submitted(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, _ = api_client
    policy_id = create_policy(client)
    version = create_policy_version_draft(client, policy_id=policy_id)

    response = client.get(f"/policy-versions/{version['id']}/review-state")

    assert response.status_code == 200
    body = response.json()
    assert body == {
        "policy_version_id": version["id"],
        "latest_review_request_id": None,
        "review_status": "not_submitted",
        "requested_at": None,
        "decided_at": None,
        "reviewer_actor_id": None,
        "can_submit_review": True,
        "message": "Review request not submitted.",
    }


def test_review_state_after_submit_is_pending(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, _ = api_client
    policy_id = create_policy(client)
    version = create_policy_version_draft(client, policy_id=policy_id)
    review_request = client.post(
        f"/policy-versions/{version['id']}/review-requests",
    ).json()

    response = client.get(f"/policy-versions/{version['id']}/review-state")

    assert response.status_code == 200
    body = response.json()
    assert body["policy_version_id"] == version["id"]
    assert body["latest_review_request_id"] == review_request["id"]
    assert body["review_status"] == "pending"
    assert body["requested_at"] is not None
    assert body["decided_at"] is None
    assert body["reviewer_actor_id"] is None
    assert body["can_submit_review"] is False
    assert body["message"] == (
        "Review request pending. Approval does not activate this version."
    )


def test_duplicate_submit_keeps_review_state_pending(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, _ = api_client
    policy_id = create_policy(client)
    version = create_policy_version_draft(client, policy_id=policy_id)
    review_request = client.post(
        f"/policy-versions/{version['id']}/review-requests",
    ).json()

    duplicate = client.post(f"/policy-versions/{version['id']}/review-requests")
    state_response = client.get(f"/policy-versions/{version['id']}/review-state")

    assert duplicate.status_code == 409
    assert state_response.status_code == 200
    body = state_response.json()
    assert body["latest_review_request_id"] == review_request["id"]
    assert body["review_status"] == "pending"
    assert body["can_submit_review"] is False


def test_assign_pending_policy_version_review_request_succeeds(
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
        f"/policy-version-review-requests/{review_request['id']}/assign",
        json={
            "assigned_reviewer_actor_type": "user",
            "assigned_reviewer_actor_id": "user:reviewer-1",
            "assigned_reviewer_name": "Reviewer One",
            "assignment_note": "Please review this rollback candidate.",
        },
    )
    refreshed_version = client.get(f"/policy-versions/{version['id']}")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "pending"
    assert body["assigned_reviewer_actor_type"] == "user"
    assert body["assigned_reviewer_actor_id"] == "user:reviewer-1"
    assert body["assigned_reviewer_name"] == "Reviewer One"
    assert body["assigned_at"] is not None
    assert body["assigned_by_actor_type"] == "user"
    assert body["assigned_by_actor_id"] == "user:reviewer-1"
    assert body["reviewer_actor_id"] is None
    assert body["decided_at"] is None
    assert refreshed_version.status_code == 200
    assert refreshed_version.json()["status"] == "draft"
    assert refreshed_version.json()["activated_at"] is None

    audit_log = fetch_audit_logs(session_factory)[-1]
    assert audit_log.event_type == "policy_version_review_assigned"
    assert audit_log.entity_type == "policy_version_review_request"
    assert audit_log.entity_id == review_request["id"]
    assert audit_log.metadata_ == {
        "policy_id": policy_id,
        "policy_version_id": version["id"],
        "policy_version_number": 1,
        "policy_version_status": "draft",
        "review_status": "pending",
        "assigned_reviewer_actor_type": "user",
        "assigned_reviewer_actor_id": "user:reviewer-1",
        "assigned_reviewer_name": "Reviewer One",
        "assignment_note": "Please review this rollback candidate.",
    }


def test_assign_non_pending_policy_version_review_request_fails(
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

    response = client.post(
        f"/policy-version-review-requests/{review_request['id']}/assign",
        json={
            "assigned_reviewer_actor_type": "user",
            "assigned_reviewer_actor_id": "user:reviewer-2",
        },
    )

    assert approved.status_code == 200
    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Only pending PolicyVersion review requests can transition."
    )


def test_assigned_reviewer_can_approve_policy_version_review_request(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, _ = api_client
    policy_id = create_policy(client)
    version = create_policy_version_draft(client, policy_id=policy_id)
    review_request = client.post(
        f"/policy-versions/{version['id']}/review-requests",
    ).json()
    set_current_actor(platform_admin_actor())
    assigned = client.post(
        f"/policy-version-review-requests/{review_request['id']}/assign",
        json={
            "assigned_reviewer_actor_type": "user",
            "assigned_reviewer_actor_id": "user:reviewer-1",
        },
    )
    set_current_actor(reviewer_actor())

    response = client.post(
        f"/policy-version-review-requests/{review_request['id']}/approve",
        json={"decision_note": "Assigned reviewer approved."},
    )

    assert assigned.status_code == 200
    assert response.status_code == 200
    assert response.json()["status"] == "approved"
    assert response.json()["reviewer_actor_id"] == "user:reviewer-1"
    assert response.json()["assigned_reviewer_actor_id"] == "user:reviewer-1"


def test_different_reviewer_cannot_approve_assigned_review_request(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, _ = api_client
    policy_id = create_policy(client)
    version = create_policy_version_draft(client, policy_id=policy_id)
    review_request = client.post(
        f"/policy-versions/{version['id']}/review-requests",
    ).json()
    set_current_actor(platform_admin_actor())
    assigned = client.post(
        f"/policy-version-review-requests/{review_request['id']}/assign",
        json={
            "assigned_reviewer_actor_type": "user",
            "assigned_reviewer_actor_id": "user:reviewer-1",
        },
    )
    set_current_actor(other_reviewer_actor())

    response = client.post(
        f"/policy-version-review-requests/{review_request['id']}/approve",
    )

    assert assigned.status_code == 200
    assert response.status_code == 403
    assert response.json()["detail"] == (
        "PolicyVersion review is assigned to another reviewer. Only the "
        "assigned reviewer or platform_admin can approve or reject it."
    )


def test_platform_admin_can_approve_assigned_review_request(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, _ = api_client
    policy_id = create_policy(client)
    version = create_policy_version_draft(client, policy_id=policy_id)
    review_request = client.post(
        f"/policy-versions/{version['id']}/review-requests",
    ).json()
    set_current_actor(reviewer_actor())
    assigned = client.post(
        f"/policy-version-review-requests/{review_request['id']}/assign",
        json={
            "assigned_reviewer_actor_type": "user",
            "assigned_reviewer_actor_id": "user:reviewer-1",
        },
    )
    set_current_actor(platform_admin_actor())

    response = client.post(
        f"/policy-version-review-requests/{review_request['id']}/approve",
    )

    assert assigned.status_code == 200
    assert response.status_code == 200
    assert response.json()["status"] == "approved"
    assert response.json()["reviewer_actor_id"] == "user:policy-admin"


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
    assign_response = client.post(
        f"/policy-version-review-requests/{review_request['id']}/assign",
        json={
            "assigned_reviewer_actor_type": "user",
            "assigned_reviewer_actor_id": "user:reviewer-1",
        },
    )
    approve_response = client.post(
        f"/policy-version-review-requests/{review_request['id']}/approve",
    )

    assert list_response.status_code == 403
    assert list_response.json()["detail"] == (
        "Actor requires one of these roles: reviewer, auditor, platform_admin."
    )
    assert assign_response.status_code == 403
    assert assign_response.json()["detail"] == (
        "Actor requires one of these roles: reviewer, platform_admin."
    )
    assert approve_response.status_code == 403
    assert approve_response.json()["detail"] == (
        "Actor requires one of these roles: reviewer, platform_admin."
    )


def test_narrow_review_state_does_not_leak_to_unrelated_actor(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, _ = api_client
    policy_id = create_policy(client)
    version = create_policy_version_draft(client, policy_id=policy_id)
    client.post(f"/policy-versions/{version['id']}/review-requests")
    set_current_actor(
        ActorContext(
            actor_type=ActorType.USER,
            actor_id="user:viewer-1",
            roles=("viewer",),
        )
    )

    response = client.get(f"/policy-versions/{version['id']}/review-state")

    assert response.status_code == 403
    assert response.json()["detail"] == "Review state unavailable for current actor."


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


def test_activation_fails_for_pending_or_rejected_review_request(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, _ = api_client
    policy_id = create_policy(client)
    pending_version = create_policy_version_draft(client, policy_id=policy_id)
    pending_request = client.post(
        f"/policy-versions/{pending_version['id']}/review-requests",
    ).json()
    set_current_actor(reviewer_actor())

    pending_activation = client.post(
        f"/policy-version-review-requests/{pending_request['id']}/activate",
    )

    rejected_version = create_policy_version_draft(client, policy_id=policy_id)
    set_current_actor(development_actor())
    rejected_request = client.post(
        f"/policy-versions/{rejected_version['id']}/review-requests",
    ).json()
    set_current_actor(reviewer_actor())
    rejected = client.post(
        f"/policy-version-review-requests/{rejected_request['id']}/reject",
    )
    rejected_activation = client.post(
        f"/policy-version-review-requests/{rejected_request['id']}/activate",
    )

    assert pending_activation.status_code == 409
    assert pending_activation.json()["detail"] == (
        "Only approved PolicyVersion review requests can activate a version."
    )
    assert rejected.status_code == 200
    assert rejected_activation.status_code == 409
    assert rejected_activation.json()["detail"] == (
        "Only approved PolicyVersion review requests can activate a version."
    )


def test_approved_review_activation_succeeds_without_auto_publish(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    policy_id = create_policy(client)
    version = create_policy_version_draft(client, policy_id=policy_id)
    review_request = create_and_approve_review_request(client, version)

    response = client.post(
        f"/policy-version-review-requests/{review_request['id']}/activate",
    )
    refreshed_version = client.get(f"/policy-versions/{version['id']}")

    assert response.status_code == 200
    assert response.json()["id"] == version["id"]
    assert response.json()["status"] == "active"
    assert response.json()["activated_at"] is not None
    assert refreshed_version.status_code == 200
    assert refreshed_version.json()["status"] == "active"
    assert count_active_policy_versions(session_factory, policy_id) == 1

    audit_logs = fetch_audit_logs(session_factory)
    activated_audit = audit_logs[-1]
    assert activated_audit.event_type == "policy_version_activated"
    assert activated_audit.entity_type == "policy_version"
    assert activated_audit.entity_id == version["id"]
    assert activated_audit.metadata_["review_request_id"] == review_request["id"]
    assert activated_audit.metadata_["review_status"] == "approved"
    assert activated_audit.metadata_["replace_active"] is False
    assert activated_audit.metadata_["superseded_policy_version_id"] is None


def test_activation_with_existing_active_requires_explicit_replacement(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    policy_id = create_policy(client)
    first_version = create_policy_version_draft(
        client,
        policy_id=policy_id,
        condition={"decision": "allow", "reason": "First reviewed version."},
    )
    first_request = create_and_approve_review_request(client, first_version)
    first_activation = client.post(
        f"/policy-version-review-requests/{first_request['id']}/activate",
    )
    assert first_activation.status_code == 200

    set_current_actor(development_actor())
    second_version = create_policy_version_draft(
        client,
        policy_id=policy_id,
        condition={"decision": "deny", "reason": "Replacement reviewed version."},
    )
    second_request = create_and_approve_review_request(client, second_version)

    blocked = client.post(
        f"/policy-version-review-requests/{second_request['id']}/activate",
    )
    replacement = client.post(
        f"/policy-version-review-requests/{second_request['id']}/activate",
        json={"replace_active": True},
    )

    assert blocked.status_code == 409
    assert blocked.json()["detail"] == (
        "Policy already has an active PolicyVersion. Set replace_active=true "
        "to supersede it explicitly."
    )
    assert replacement.status_code == 200
    assert replacement.json()["status"] == "active"
    assert count_active_policy_versions(session_factory, policy_id) == 1

    versions = fetch_policy_versions(session_factory, policy_id)
    statuses_by_id = {str(version.id): version.status.value for version in versions}
    assert statuses_by_id[first_version["id"]] == "superseded"
    assert statuses_by_id[second_version["id"]] == "active"

    audit_events = [log.event_type for log in fetch_audit_logs(session_factory)]
    assert "policy_version_superseded" in audit_events
    assert audit_events.count("policy_version_activated") == 2


def test_review_diff_against_active_policy_version(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, _ = api_client
    policy_id = create_policy(client)
    first_version = create_policy_version_draft(
        client,
        policy_id=policy_id,
        condition={
            "decision": "allow",
            "reason": "Baseline allows email.",
            "tool_name": "send_email",
            "action_type": "send",
        },
    )
    first_request = create_and_approve_review_request(client, first_version)
    assert (
        client.post(
            f"/policy-version-review-requests/{first_request['id']}/activate"
        ).status_code
        == 200
    )

    set_current_actor(development_actor())
    second_version = create_policy_version_draft(
        client,
        policy_id=policy_id,
        condition={
            "decision": "deny",
            "reason": "Reviewed version denies high-risk email.",
            "tool_name": "send_email",
            "risk_level": "high",
        },
    )
    review_request = client.post(
        f"/policy-versions/{second_version['id']}/review-requests",
    ).json()
    set_current_actor(reviewer_actor())

    response = client.get(
        f"/policy-version-review-requests/{review_request['id']}/diff"
    )

    assert response.status_code == 200
    body = response.json()
    assert body["review_request_id"] == review_request["id"]
    assert body["policy_id"] == policy_id
    assert body["policy_version_id"] == second_version["id"]
    assert body["baseline_policy_version_id"] == first_version["id"]
    assert body["baseline_type"] == "active_version"
    assert body["reviewed_version_status"] == "draft"
    assert body["review_status"] == "pending"
    assert body["can_activate"] is False
    assert body["activation_requires_replace"] is False
    assert [
        field["field"] for field in body["rule_condition_changes"]["added_fields"]
    ] == ["risk_level"]
    assert [
        field["field"] for field in body["rule_condition_changes"]["removed_fields"]
    ] == ["action_type"]
    assert {
        field["field"] for field in body["rule_condition_changes"]["changed_fields"]
    } == {"decision", "reason"}
    assert body["rule_condition_changes"]["unchanged_fields_count"] == 1
    assert "No runtime effect until activation" in body["runtime_effect_summary"]
    assert "matched_decisions" not in json.dumps(body)
    assert "compliance_score" not in json.dumps(body)


def test_review_diff_with_no_active_baseline(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, _ = api_client
    policy_id = create_policy(client)
    version = create_policy_version_draft(client, policy_id=policy_id)
    review_request = client.post(
        f"/policy-versions/{version['id']}/review-requests",
    ).json()
    set_current_actor(reviewer_actor())

    response = client.get(
        f"/policy-version-review-requests/{review_request['id']}/diff"
    )

    assert response.status_code == 200
    body = response.json()
    assert body["baseline_type"] == "none"
    assert body["baseline_policy_version_id"] is None
    assert body["baseline_summary"] == "No active baseline found."
    assert "No active baseline found." in body["plain_language_summary"]


def test_review_diff_against_live_fallback_policy_rules(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, _ = api_client
    policy_id = create_policy(client, status="active")
    create_policy_rule(
        client,
        policy_id=policy_id,
        condition={
            "decision": "allow",
            "reason": "Live fallback allows email.",
            "tool_name": "send_email",
        },
    )
    version = create_policy_version_draft(
        client,
        policy_id=policy_id,
        condition={
            "decision": "require_human_review",
            "reason": "Reviewed version escalates high-risk email.",
            "tool_name": "send_email",
            "risk_level": "high",
        },
    )
    review_request = client.post(
        f"/policy-versions/{version['id']}/review-requests",
    ).json()
    set_current_actor(reviewer_actor())

    response = client.get(
        f"/policy-version-review-requests/{review_request['id']}/diff"
    )

    assert response.status_code == 200
    body = response.json()
    assert body["baseline_type"] == "live_fallback"
    assert body["baseline_policy_version_id"] is None
    assert body["policy_snapshot_changes"]["status"]["baseline"] == "active"
    assert body["policy_snapshot_changes"]["status"]["reviewed"] == "draft"
    assert [
        field["field"] for field in body["rule_condition_changes"]["added_fields"]
    ] == ["risk_level"]
    assert {
        field["field"] for field in body["rule_condition_changes"]["changed_fields"]
    } == {"decision", "reason"}


def test_approved_review_diff_can_activate_and_requires_replace_when_active_exists(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, _ = api_client
    policy_id = create_policy(client)
    active_version = create_policy_version_draft(
        client,
        policy_id=policy_id,
        condition={"decision": "allow", "reason": "Baseline active version."},
    )
    active_request = create_and_approve_review_request(client, active_version)
    assert (
        client.post(
            f"/policy-version-review-requests/{active_request['id']}/activate"
        ).status_code
        == 200
    )

    set_current_actor(development_actor())
    reviewed_version = create_policy_version_draft(
        client,
        policy_id=policy_id,
        condition={"decision": "deny", "reason": "Reviewed replacement version."},
    )
    approved_request = create_and_approve_review_request(client, reviewed_version)

    response = client.get(
        f"/policy-version-review-requests/{approved_request['id']}/diff"
    )

    assert response.status_code == 200
    body = response.json()
    assert body["review_status"] == "approved"
    assert body["can_activate"] is True
    assert body["activation_requires_replace"] is True
    assert (
        "Activation will change future runtime and telemetry policy evaluation"
        in body["runtime_effect_summary"]
    )


def test_activated_review_diff_includes_activation_and_supersession_evidence(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, _ = api_client
    policy_id = create_policy(client)
    first_version = create_policy_version_draft(
        client,
        policy_id=policy_id,
        condition={"decision": "allow", "reason": "First active version."},
    )
    first_request = create_and_approve_review_request(client, first_version)
    assert (
        client.post(
            f"/policy-version-review-requests/{first_request['id']}/activate"
        ).status_code
        == 200
    )

    set_current_actor(development_actor())
    second_version = create_policy_version_draft(
        client,
        policy_id=policy_id,
        condition={"decision": "deny", "reason": "Second active version."},
    )
    second_request = create_and_approve_review_request(client, second_version)
    activation = client.post(
        f"/policy-version-review-requests/{second_request['id']}/activate",
        json={"replace_active": True},
    )
    assert activation.status_code == 200

    response = client.get(
        f"/policy-version-review-requests/{second_request['id']}/diff"
    )

    assert response.status_code == 200
    body = response.json()
    assert body["baseline_type"] == "active_version"
    assert body["baseline_policy_version_id"] == first_version["id"]
    assert body["can_activate"] is False
    assert body["evidence"]["activated_policy_version_id"] == second_version["id"]
    assert body["evidence"]["previous_active_policy_version_id"] == first_version["id"]
    assert (
        body["evidence"]["activation_audit_event"]["event_type"]
        == "policy_version_activated"
    )
    assert (
        body["evidence"]["superseded_audit_event"]["event_type"]
        == "policy_version_superseded"
    )
    assert "PolicyVersion is active" in body["runtime_effect_summary"][0]


def test_unknown_review_diff_returns_safe_not_found(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, _ = api_client
    set_current_actor(reviewer_actor())

    response = client.get(f"/policy-version-review-requests/{uuid4()}/diff")

    assert response.status_code == 404
    assert response.json()["detail"] == "PolicyVersion review request not found."


def test_activation_updates_runtime_and_telemetry_source_of_truth(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(client)
    policy_id = create_policy(client, status="active")
    create_policy_rule(
        client,
        policy_id=policy_id,
        condition={
            "decision": "allow",
            "reason": "Live fallback allows email before activation.",
            "tool_name": "send_email",
        },
    )
    version = create_policy_version_draft(
        client,
        policy_id=policy_id,
        condition={
            "decision": "deny",
            "reason": "Activated reviewed version denies email.",
            "tool_name": "send_email",
        },
    )
    review_request = create_and_approve_review_request(client, version)

    before_activation = client.post(
        "/runtime/tool-calls/decision",
        json=runtime_decision_payload(agent_id, request_id="before-activation"),
    )
    activation = client.post(
        f"/policy-version-review-requests/{review_request['id']}/activate",
    )
    runtime_after_activation = client.post(
        "/runtime/tool-calls/decision",
        json=runtime_decision_payload(agent_id, request_id="after-activation"),
    )
    telemetry_after_activation = client.post(
        "/telemetry/events",
        json=trace_event_payload(
            agent_id,
            external_event_id="telemetry-after-activation",
        ),
    )

    assert before_activation.status_code == 201
    assert before_activation.json()["decision"] == "allow"
    assert activation.status_code == 200
    assert runtime_after_activation.status_code == 201
    assert runtime_after_activation.json()["decision"] == "deny"
    assert telemetry_after_activation.status_code == 201
    telemetry_decision = telemetry_after_activation.json()["policy_decision"]
    assert telemetry_decision["decision"] == "deny"
    assert telemetry_decision["policy_version_id"] == version["id"]

    decisions = fetch_policy_decisions(session_factory)
    assert decisions[0].policy_version_id is None
    assert str(decisions[1].policy_version_id) == version["id"]
    assert str(decisions[2].policy_version_id) == version["id"]
    versioned_decisions = [
        decision for decision in decisions if decision.policy_version_id is not None
    ]
    assert {str(decision.policy_version_id) for decision in versioned_decisions} == {
        version["id"]
    }


def create_policy(
    client: TestClient,
    *,
    name: str = "Email policy",
    status: str = "draft",
) -> str:
    response = client.post(
        "/policies",
        json={
            "name": name,
            "description": "Governed email policy.",
            "status": status,
        },
    )

    assert response.status_code == 201
    return response.json()["id"]


def create_policy_version_draft(
    client: TestClient,
    *,
    policy_id: str,
    condition: dict[str, object] | None = None,
) -> dict[str, object]:
    rule_condition = condition or {
        "decision": "require_human_review",
        "reason": "Email tool use requires review in this draft.",
        "tool_name": "send_email",
    }
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
                    "condition": json.dumps(rule_condition),
                }
            ],
        },
    )

    assert response.status_code == 201
    return response.json()


def create_policy_rule(
    client: TestClient,
    *,
    policy_id: str,
    condition: dict[str, object],
) -> str:
    response = client.post(
        "/policy-rules",
        json={
            "policy_id": policy_id,
            "name": "Live fallback rule",
            "description": "Persisted live PolicyRule fallback.",
            "condition": json.dumps(condition),
        },
    )

    assert response.status_code == 201
    return response.json()["id"]


def create_and_approve_review_request(
    client: TestClient,
    version: dict[str, object],
) -> dict[str, object]:
    set_current_actor(development_actor())
    review_response = client.post(
        f"/policy-versions/{version['id']}/review-requests",
    )
    assert review_response.status_code == 201
    review_request = review_response.json()
    set_current_actor(reviewer_actor())
    approve_response = client.post(
        f"/policy-version-review-requests/{review_request['id']}/approve",
        json={"decision_note": "Approved for explicit activation."},
    )
    assert approve_response.status_code == 200
    return approve_response.json()


def approve_and_activate_policy_version(
    client: TestClient,
    version: dict[str, object],
) -> dict[str, object]:
    client.post(f"/policy-versions/{version['id']}/submit-review")
    client.post(f"/policy-versions/{version['id']}/approve")
    response = client.post(f"/policy-versions/{version['id']}/activate")

    assert response.status_code == 200
    return response.json()


def create_agent(client: TestClient) -> str:
    response = client.post(
        "/agents",
        json={
            "name": "Support assistant",
            "description": "Routes support requests.",
            "owner_type": "team",
            "owner_id": "team:ai-platform",
            "owner_name": "AI Platform",
            "owner_contact_email": "owner@example.com",
            "environment": "development",
            "status": "active",
            "risk_level": "low",
            "framework": "LangGraph",
        },
    )

    assert response.status_code == 201
    return response.json()["id"]


def runtime_decision_payload(
    agent_id: str,
    *,
    request_id: str,
) -> dict[str, object]:
    return {
        "request_id": request_id,
        "agent_id": agent_id,
        "run_id": str(uuid4()),
        "correlation_id": request_id,
        "tool_name": "send_email",
        "action_summary": "Send a support follow-up email.",
        "metadata": {"ticket_category": "support"},
        "mode": "simulation",
    }


def trace_event_payload(
    agent_id: str,
    *,
    external_event_id: str,
) -> dict[str, object]:
    return {
        "id": str(uuid4()),
        "agent_id": agent_id,
        "run_id": str(uuid4()),
        "correlation_id": external_event_id,
        "external_event_id": external_event_id,
        "event_type": "tool_call_requested",
        "timestamp": datetime.now(UTC).isoformat(),
        "summary": "Tool call requested.",
        "metadata": {"tool_name": "send_email"},
    }


def set_current_actor(actor: ActorContext) -> None:
    app.dependency_overrides[get_current_actor] = lambda: actor


def development_actor() -> ActorContext:
    return ActorContext(
        actor_type=ActorType.DEVELOPMENT,
        actor_id="dev-placeholder",
        roles=(),
    )


def reviewer_actor() -> ActorContext:
    return ActorContext(
        actor_type=ActorType.USER,
        actor_id="user:reviewer-1",
        roles=("reviewer",),
    )


def other_reviewer_actor() -> ActorContext:
    return ActorContext(
        actor_type=ActorType.USER,
        actor_id="user:reviewer-2",
        roles=("reviewer",),
    )


def platform_admin_actor() -> ActorContext:
    return ActorContext(
        actor_type=ActorType.USER,
        actor_id="user:policy-admin",
        roles=("platform_admin",),
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


def fetch_policy_versions(
    session_factory: SessionFactory,
    policy_id: str,
) -> list[PolicyVersion]:
    with session_factory() as session:
        statement = (
            select(PolicyVersion)
            .where(PolicyVersion.policy_id == UUID(policy_id))
            .order_by(PolicyVersion.version_number, PolicyVersion.id)
        )
        return list(session.scalars(statement).all())


def count_active_policy_versions(
    session_factory: SessionFactory,
    policy_id: str,
) -> int:
    return sum(
        1
        for version in fetch_policy_versions(session_factory, policy_id)
        if version.status.value == "active"
    )


def fetch_policy_decisions(
    session_factory: SessionFactory,
) -> list[PolicyDecision]:
    with session_factory() as session:
        statement = select(PolicyDecision).order_by(
            PolicyDecision.created_at,
            PolicyDecision.id,
        )
        return list(session.scalars(statement).all())
