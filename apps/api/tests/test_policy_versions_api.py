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
    PolicyDecision,
    PolicyVersion,
    PolicyVersionStatus,
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


def test_create_policy_version_draft_from_editor_payload(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    policy_id = create_policy(client)
    rule_id = create_policy_rule(client, policy_id=policy_id)
    step_id = create_policy_check_step(client, policy_rule_id=rule_id)

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
                    "id": rule_id,
                    "name": "Studio email deny rule",
                    "description": "Compiled from Policy Studio.",
                    "condition": (
                        '{"decision":"deny",'
                        '"reason":"Email tool use is blocked in this draft.",'
                        '"tool_name":"send_email"}'
                    ),
                }
            ],
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["policy_id"] == policy_id
    assert body["version_number"] == 1
    assert body["status"] == "draft"
    assert body["activated_at"] is None
    assert body["policy_snapshot"] == {
        "id": policy_id,
        "name": "Policy Studio email guard",
        "description": "Drafted in Policy Studio.",
        "status": "draft",
    }
    assert body["rule_snapshots"] == [
        {
            "id": rule_id,
            "policy_id": policy_id,
            "name": "Studio email deny rule",
            "description": "Compiled from Policy Studio.",
            "condition": (
                '{"decision":"deny",'
                '"reason":"Email tool use is blocked in this draft.",'
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

    audit_log = fetch_audit_logs(session_factory)[-1]
    assert audit_log.event_type == "policy_version_created"
    assert audit_log.metadata_ == {
        "policy_id": policy_id,
        "version_number": 1,
        "status": "draft",
        "change_summary": "Policy Studio draft save.",
        "snapshot_source": "policy_studio",
        "rule_snapshot_count": 1,
        "check_step_snapshot_count": 1,
    }


def test_update_policy_version_draft_from_editor_payload(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    policy_id = create_policy(client)
    draft = create_policy_version_draft(client, policy_id=policy_id)

    response = client.patch(
        f"/policy-versions/{draft['id']}/draft",
        json={
            "change_summary": "Updated Policy Studio draft.",
            "policy_snapshot": {
                "name": "Updated email guard",
                "description": "Updated in Policy Studio.",
                "status": "draft",
            },
            "rule_snapshots": [
                {
                    "name": "Updated email rule",
                    "description": "Compiled from updated editor state.",
                    "condition": (
                        '{"decision":"allow",'
                        '"reason":"Email tool use is allowed in this draft.",'
                        '"tool_name":"send_email"}'
                    ),
                }
            ],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == draft["id"]
    assert body["version_number"] == draft["version_number"]
    assert body["status"] == "draft"
    assert body["change_summary"] == "Updated Policy Studio draft."
    assert body["policy_snapshot"]["name"] == "Updated email guard"
    assert body["rule_snapshots"][0]["name"] == "Updated email rule"
    assert body["rule_snapshots"][0]["policy_id"] == policy_id
    assert UUID(body["rule_snapshots"][0]["id"])
    assert body["activated_at"] is None

    audit_log = fetch_audit_logs(session_factory)[-1]
    assert audit_log.event_type == "policy_version_draft_updated"
    assert audit_log.metadata_["snapshot_source"] == "policy_studio"
    assert audit_log.metadata_["rule_snapshot_count"] == 1
    assert audit_log.metadata_["check_step_snapshot_count"] == 0


def test_update_non_draft_policy_version_fails(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, _ = api_client
    policy_id = create_policy(client)
    draft = create_policy_version_draft(client, policy_id=policy_id)
    client.post(f"/policy-versions/{draft['id']}/submit-review")

    response = client.patch(
        f"/policy-versions/{draft['id']}/draft",
        json=policy_version_draft_payload(),
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Only draft policy versions can be updated."


def test_policy_version_draft_rejects_rule_id_from_another_policy(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, _ = api_client
    policy_id = create_policy(client, name="Email policy")
    other_policy_id = create_policy(client, name="Payment policy")
    other_rule_id = create_policy_rule(client, policy_id=other_policy_id)

    payload = policy_version_draft_payload()
    payload["rule_snapshots"][0]["id"] = other_rule_id
    response = client.post(f"/policies/{policy_id}/versions/draft", json=payload)

    assert response.status_code == 422
    assert response.json()["detail"] == (
        "PolicyVersion draft rule snapshot id must belong to the target Policy."
    )


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


def test_activating_second_policy_version_for_same_policy_fails(
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

    assert activated_second.status_code == 409
    assert activated_second.json()["detail"] == (
        "Policy already has an active PolicyVersion. Archive the active version "
        "before activating another."
    )
    assert refreshed_first.status_code == 200
    assert refreshed_first.json()["status"] == "active"
    assert refreshed_first.json()["superseded_at"] is None

    event_types = [log.event_type for log in fetch_audit_logs(session_factory)]
    assert "policy_version_superseded" not in event_types
    assert event_types.count("policy_version_activated") == 1


def test_active_policy_versions_for_different_policies_are_allowed(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, _ = api_client
    first_policy_id = create_policy(client, name="Email policy")
    second_policy_id = create_policy(client, name="Payment policy")

    first = approve_and_activate_policy_version(
        client,
        create_policy_version(client, policy_id=first_policy_id),
    )
    second = approve_and_activate_policy_version(
        client,
        create_policy_version(client, policy_id=second_policy_id),
    )

    assert first["status"] == "active"
    assert second["status"] == "active"
    assert first["policy_id"] != second["policy_id"]


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


def test_policy_version_rollback_draft_from_superseded_version_copies_snapshot(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    policy_id = create_policy(client)
    rule_id = create_policy_rule(client, policy_id=policy_id)
    create_policy_check_step(client, policy_rule_id=rule_id)
    source = create_policy_version(client, policy_id=policy_id)
    mark_policy_version_status(
        session_factory,
        source["id"],
        PolicyVersionStatus.SUPERSEDED,
    )

    response = client.post(
        f"/policy-versions/{source['id']}/rollback-draft",
        json={"change_summary": "Create rollback candidate from prior version."},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "draft"
    assert body["source_version_id"] == source["id"]
    assert body["version_number"] == 2
    assert body["policy_snapshot"] == source["policy_snapshot"]
    assert body["rule_snapshots"] == source["rule_snapshots"]
    assert body["check_step_snapshots"] == source["check_step_snapshots"]
    assert body["activated_at"] is None
    assert body["submitted_at"] is None
    assert body["approved_at"] is None

    refreshed_source = client.get(f"/policy-versions/{source['id']}")
    assert refreshed_source.status_code == 200
    assert refreshed_source.json()["status"] == "superseded"
    assert refreshed_source.json()["rule_snapshots"] == source["rule_snapshots"]
    assert (
        refreshed_source.json()["check_step_snapshots"]
        == source["check_step_snapshots"]
    )

    audit_log = fetch_audit_logs(session_factory)[-1]
    assert audit_log.event_type == "policy_version_rollback_draft_created"
    assert audit_log.entity_type == "policy_version"
    assert audit_log.entity_id == body["id"]
    assert audit_log.metadata_ == {
        "policy_id": policy_id,
        "version_number": 2,
        "status": "draft",
        "source_version_id": source["id"],
        "source_version_number": 1,
        "source_version_status": "superseded",
        "change_summary": "Create rollback candidate from prior version.",
    }


def test_policy_version_rollback_draft_from_active_version_does_not_affect_runtime(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    policy_id = create_policy(client)
    create_policy_rule(client, policy_id=policy_id)
    active = approve_and_activate_policy_version(
        client,
        create_policy_version(client, policy_id=policy_id),
    )
    agent_id = create_agent(client)

    rollback_response = client.post(
        f"/policy-versions/{active['id']}/rollback-draft",
        json={"change_summary": "Copy current active version to a rollback draft."},
    )
    runtime_response = client.post(
        "/runtime/tool-calls/decision",
        json=runtime_decision_payload(agent_id),
    )
    telemetry_response = client.post(
        "/telemetry/events",
        json=trace_event_payload(agent_id),
    )
    refreshed_active = client.get(f"/policy-versions/{active['id']}")

    assert rollback_response.status_code == 201
    rollback_body = rollback_response.json()
    assert rollback_body["status"] == "draft"
    assert rollback_body["source_version_id"] == active["id"]
    assert rollback_body["activated_at"] is None
    assert rollback_body["submitted_at"] is None

    assert runtime_response.status_code == 201
    assert runtime_response.json()["policy_decision_id"] is not None

    assert telemetry_response.status_code == 201
    assert (
        telemetry_response.json()["policy_decision"]["policy_version_id"]
        == active["id"]
    )
    assert (
        telemetry_response.json()["policy_decision"]["policy_version_id"]
        != rollback_body["id"]
    )

    assert refreshed_active.status_code == 200
    assert refreshed_active.json()["status"] == "active"

    policy_decisions = fetch_policy_decisions(session_factory)
    assert [str(decision.policy_version_id) for decision in policy_decisions] == [
        active["id"],
        active["id"],
    ]
    assert rollback_body["id"] not in [
        str(decision.policy_version_id) for decision in policy_decisions
    ]


def test_policy_version_rollback_draft_rejects_mutable_source_status(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, _ = api_client
    policy_id = create_policy(client)
    source = create_policy_version(client, policy_id=policy_id)

    response = client.post(
        f"/policy-versions/{source['id']}/rollback-draft",
        json={"change_summary": "Try to copy a draft."},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Only approved, active, superseded, or archived PolicyVersions can create "
        "a rollback draft."
    )


def test_policy_version_rollback_draft_unknown_source_returns_safe_404(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, _ = api_client
    missing_id = "00000000-0000-0000-0000-000000000001"

    response = client.post(
        f"/policy-versions/{missing_id}/rollback-draft",
        json={"change_summary": "Try to copy a missing version."},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "PolicyVersion not found."


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


def mark_policy_version_status(
    session_factory: SessionFactory,
    version_id: str,
    status: PolicyVersionStatus,
) -> None:
    now = datetime.now(UTC)
    with session_factory() as session:
        version = session.get(PolicyVersion, UUID(version_id))
        assert version is not None
        version.status = status
        version.updated_at = now
        if status is PolicyVersionStatus.APPROVED:
            version.approved_at = now
        if status is PolicyVersionStatus.ACTIVE:
            version.activated_at = now
        if status is PolicyVersionStatus.SUPERSEDED:
            version.approved_at = version.approved_at or now
            version.activated_at = version.activated_at or now
            version.superseded_at = now
        if status is PolicyVersionStatus.ARCHIVED:
            version.archived_at = now
        session.commit()


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


def create_agent(client: TestClient) -> str:
    response = client.post(
        "/agents",
        json={
            "name": "Rollback validation agent",
            "description": "Safe local test agent for rollback draft validation.",
            "owner_type": "team",
            "owner_id": "team:governance",
            "owner_name": "Governance Team",
            "owner_contact_email": None,
            "environment": "development",
            "status": "active",
            "risk_level": "medium",
            "framework": "LangGraph-style test",
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


def runtime_decision_payload(agent_id: str) -> dict[str, object]:
    return {
        "request_id": "rollback-runtime-request-001",
        "agent_id": agent_id,
        "run_id": str(uuid4()),
        "correlation_id": "rollback-runtime-correlation-001",
        "tool_name": "send_email",
        "action_summary": "Validate rollback draft does not affect runtime.",
        "metadata": {"ticket_category": "support"},
        "mode": "simulation",
    }


def trace_event_payload(agent_id: str) -> dict[str, object]:
    return {
        "id": str(uuid4()),
        "agent_id": agent_id,
        "run_id": str(uuid4()),
        "correlation_id": "rollback-telemetry-correlation-001",
        "external_event_id": "rollback-telemetry-event-001",
        "event_type": "tool_call_requested",
        "timestamp": datetime.now(UTC).isoformat(),
        "summary": "Validate rollback draft does not affect telemetry.",
        "metadata": {"tool_name": "send_email"},
    }


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


def create_policy_version_draft(
    client: TestClient,
    *,
    policy_id: str,
    change_summary: str = "Policy Studio draft save.",
) -> dict[str, object]:
    response = client.post(
        f"/policies/{policy_id}/versions/draft",
        json=policy_version_draft_payload(change_summary=change_summary),
    )

    assert response.status_code == 201
    return response.json()


def policy_version_draft_payload(
    *,
    change_summary: str = "Policy Studio draft save.",
) -> dict[str, object]:
    return {
        "change_summary": change_summary,
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
    }


def fetch_audit_logs(session_factory: SessionFactory) -> list[AuditLog]:
    with session_factory() as session:
        statement = select(AuditLog).order_by(AuditLog.created_at, AuditLog.id)
        return list(session.scalars(statement).all())


def fetch_policy_decisions(session_factory: SessionFactory) -> list[PolicyDecision]:
    with session_factory() as session:
        statement = select(PolicyDecision).order_by(
            PolicyDecision.created_at,
            PolicyDecision.id,
        )
        return list(session.scalars(statement).all())
