import json
from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy import event as sqlalchemy_event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import agent_governance_api.telemetry_api as telemetry_api
from agent_governance_api.auth import (
    ActorContext,
    get_current_actor,
    hash_service_actor_api_key,
)
from agent_governance_api.config import get_settings
from agent_governance_api.database import Base, get_db_session
from agent_governance_api.main import app
from agent_governance_api.models import (
    ActorType,
    Agent,
    AgentRunRecord,
    AgentStatus,
    AuditLog,
    Environment,
    HumanApproval,
    HumanApprovalStatus,
    OwnerType,
    Policy,
    PolicyDecision,
    PolicyDecisionValue,
    PolicyRule,
    PolicyStatus,
    PolicyVersion,
    PolicyVersionStatus,
    RiskLevel,
    TraceEventRecord,
    TraceEventType,
)

SessionFactory = Callable[[], Session]
SERVICE_ACTOR_ID = "service:telemetry-test"
SERVICE_API_KEY = "local-test-telemetry-key"


@pytest.fixture()
def api_client() -> Iterator[tuple[TestClient, SessionFactory]]:
    get_settings.cache_clear()
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @sqlalchemy_event.listens_for(engine, "connect")
    def enable_foreign_keys(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

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
        get_settings.cache_clear()
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_ingest_valid_trace_event(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    event_id = uuid4()
    run_id = uuid4()

    response = client.post(
        "/telemetry/events",
        json=trace_event_payload(agent_id, event_id=event_id, run_id=run_id),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["id"] == str(event_id)
    assert body["agent_id"] == str(agent_id)
    assert body["run_id"] == str(run_id)
    assert body["event_type"] == "tool_call_requested"
    assert body["created_at"]
    assert body["policy_decision"]["decision"] == "not_applicable"
    assert body["policy_decision"]["trace_event_id"] == str(event_id)
    assert body["human_approval_id"] is None

    [saved_event] = fetch_trace_events(session_factory)
    assert saved_event.id == event_id
    assert saved_event.agent_id == agent_id
    assert saved_event.run_id == run_id
    assert saved_event.external_event_id == str(event_id)
    assert saved_event.event_type is TraceEventType.TOOL_CALL_REQUESTED
    assert saved_event.metadata_ == {"tool_name": "send_email"}


def test_ingest_duplicate_trace_event_returns_existing_event(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    policy_id, rule_id = create_policy_rule(
        session_factory,
        condition={
            "decision": "allow",
            "reason": "The requested tool is allowed.",
            "tool_name": "send_email",
        },
    )
    run_id = uuid4()
    first_event_id = uuid4()
    external_event_id = "vendor-event-123"

    first_response = client.post(
        "/telemetry/events",
        json=trace_event_payload(
            agent_id,
            event_id=first_event_id,
            run_id=run_id,
            external_event_id=external_event_id,
        ),
    )
    duplicate_response = client.post(
        "/telemetry/events",
        json=trace_event_payload(
            agent_id,
            event_id=uuid4(),
            run_id=run_id,
            external_event_id=external_event_id,
            summary="Retried event with changed body.",
        ),
    )

    assert first_response.status_code == 201
    assert duplicate_response.status_code == 200
    assert duplicate_response.json() == first_response.json()
    assert first_response.json()["policy_decision"]["policy_id"] == str(policy_id)
    assert first_response.json()["policy_decision"]["rule_id"] == str(rule_id)
    [saved_event] = fetch_trace_events(session_factory)
    assert saved_event.id == first_event_id
    assert saved_event.external_event_id == external_event_id
    assert saved_event.summary == "Tool call requested."
    assert len(fetch_policy_decisions(session_factory)) == 1
    assert fetch_human_approvals(session_factory) == []
    [saved_decision] = fetch_policy_decisions(session_factory)
    assert saved_decision.trace_event_id == first_event_id


def test_ingest_duplicate_trace_event_does_not_create_second_record(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    run_id = uuid4()
    external_event_id = "vendor-event-123"

    client.post(
        "/telemetry/events",
        json=trace_event_payload(
            agent_id,
            run_id=run_id,
            external_event_id=external_event_id,
        ),
    )
    client.post(
        "/telemetry/events",
        json=trace_event_payload(
            agent_id,
            run_id=run_id,
            external_event_id=external_event_id,
        ),
    )

    assert len(fetch_trace_events(session_factory)) == 1
    assert len(fetch_policy_decisions(session_factory)) == 1
    assert fetch_human_approvals(session_factory) == []


def test_tool_call_requested_with_allow_policy_creates_policy_decision(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    policy_id, rule_id = create_policy_rule(
        session_factory,
        condition={
            "decision": "allow",
            "reason": "The requested tool is allowed.",
            "tool_name": "send_email",
        },
    )

    response = client.post("/telemetry/events", json=trace_event_payload(agent_id))

    assert response.status_code == 201
    decision_body = response.json()["policy_decision"]
    assert decision_body["decision"] == "allow"
    assert decision_body["reason"] == "The requested tool is allowed."
    assert decision_body["trace_event_id"] == response.json()["id"]
    assert decision_body["policy_id"] == str(policy_id)
    assert decision_body["rule_id"] == str(rule_id)
    assert response.json()["human_approval_id"] is None
    [saved_decision] = fetch_policy_decisions(session_factory)
    assert saved_decision.decision is PolicyDecisionValue.ALLOW
    assert saved_decision.trace_event_id == UUID(response.json()["id"])
    assert saved_decision.policy_id == policy_id
    assert saved_decision.rule_id == rule_id
    assert fetch_human_approvals(session_factory) == []


def test_tool_call_requested_uses_active_policy_version_snapshot(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    policy_id, rule_id = create_policy_rule(
        session_factory,
        condition={
            "decision": "allow",
            "reason": "Live mutable rule should not be used.",
            "tool_name": "send_email",
        },
    )
    version_id = create_policy_version(
        session_factory,
        policy_id=policy_id,
        rule_id=rule_id,
        status=PolicyVersionStatus.ACTIVE,
        condition={
            "decision": "deny",
            "reason": "Reviewed snapshot denies email.",
            "tool_name": "send_email",
        },
    )

    response = client.post("/telemetry/events", json=trace_event_payload(agent_id))

    assert response.status_code == 201
    decision_body = response.json()["policy_decision"]
    assert decision_body["decision"] == "deny"
    assert decision_body["reason"] == "Reviewed snapshot denies email."
    assert decision_body["policy_id"] == str(policy_id)
    assert decision_body["policy_version_id"] == str(version_id)
    assert decision_body["rule_id"] == str(rule_id)
    [saved_decision] = fetch_policy_decisions(session_factory)
    assert saved_decision.decision is PolicyDecisionValue.DENY
    assert saved_decision.policy_id == policy_id
    assert saved_decision.policy_version_id == version_id
    assert saved_decision.rule_id == rule_id
    assert fetch_human_approvals(session_factory) == []


def test_tool_call_requested_falls_back_to_unversioned_policy_without_active_version(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    policy_id, rule_id = create_policy_rule(
        session_factory,
        condition={
            "decision": "allow",
            "reason": "Live fallback rule is still used.",
            "tool_name": "send_email",
        },
    )

    response = client.post("/telemetry/events", json=trace_event_payload(agent_id))

    assert response.status_code == 201
    decision_body = response.json()["policy_decision"]
    assert decision_body["decision"] == "allow"
    assert decision_body["reason"] == "Live fallback rule is still used."
    assert decision_body["policy_id"] == str(policy_id)
    assert decision_body["policy_version_id"] is None
    assert decision_body["rule_id"] == str(rule_id)
    [saved_decision] = fetch_policy_decisions(session_factory)
    assert saved_decision.policy_id == policy_id
    assert saved_decision.policy_version_id is None
    assert saved_decision.rule_id == rule_id
    assert fetch_human_approvals(session_factory) == []


@pytest.mark.parametrize(
    "version_status",
    [
        PolicyVersionStatus.DRAFT,
        PolicyVersionStatus.UNDER_REVIEW,
        PolicyVersionStatus.APPROVED,
        PolicyVersionStatus.REJECTED,
        PolicyVersionStatus.SUPERSEDED,
        PolicyVersionStatus.ARCHIVED,
    ],
)
def test_tool_call_requested_ignores_non_active_policy_versions(
    api_client: tuple[TestClient, SessionFactory],
    version_status: PolicyVersionStatus,
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    policy_id, rule_id = create_policy_rule(
        session_factory,
        condition={
            "decision": "allow",
            "reason": "Live fallback rule is still used.",
            "tool_name": "send_email",
        },
    )
    create_policy_version(
        session_factory,
        policy_id=policy_id,
        rule_id=rule_id,
        status=version_status,
        condition={
            "decision": "deny",
            "reason": "Inactive snapshot should not be used.",
            "tool_name": "send_email",
        },
    )

    response = client.post("/telemetry/events", json=trace_event_payload(agent_id))

    assert response.status_code == 201
    decision_body = response.json()["policy_decision"]
    assert decision_body["decision"] == "allow"
    assert decision_body["reason"] == "Live fallback rule is still used."
    assert decision_body["policy_id"] == str(policy_id)
    assert decision_body["policy_version_id"] is None
    assert decision_body["rule_id"] == str(rule_id)


def test_tool_call_requested_ignores_policy_version_draft_saved_from_editor(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    policy_id, rule_id = create_policy_rule(
        session_factory,
        condition={
            "decision": "allow",
            "reason": "Live fallback rule is still used.",
            "tool_name": "send_email",
        },
    )

    draft_response = client.post(
        f"/policies/{policy_id}/versions/draft",
        json={
            "change_summary": "Policy Studio draft should not affect telemetry.",
            "policy_snapshot": {
                "name": "Draft telemetry guard",
                "description": "Drafted in Policy Studio.",
                "status": "active",
            },
            "rule_snapshots": [
                {
                    "id": str(rule_id),
                    "name": "Draft telemetry deny rule",
                    "description": "Compiled from Policy Studio.",
                    "condition": json.dumps(
                        {
                            "decision": "deny",
                            "reason": "Draft snapshot should not be used.",
                            "tool_name": "send_email",
                        }
                    ),
                }
            ],
        },
    )
    assert draft_response.status_code == 201
    assert draft_response.json()["status"] == "draft"

    response = client.post("/telemetry/events", json=trace_event_payload(agent_id))

    assert response.status_code == 201
    decision_body = response.json()["policy_decision"]
    assert decision_body["decision"] == "allow"
    assert decision_body["reason"] == "Live fallback rule is still used."
    assert decision_body["policy_id"] == str(policy_id)
    assert decision_body["policy_version_id"] is None
    assert decision_body["rule_id"] == str(rule_id)


def test_trace_event_to_policy_decision_navigation_is_available(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    create_policy_rule(
        session_factory,
        condition={
            "decision": "allow",
            "reason": "The requested tool is allowed.",
            "tool_name": "send_email",
        },
    )

    response = client.post("/telemetry/events", json=trace_event_payload(agent_id))

    assert response.status_code == 201
    with session_factory() as session:
        [trace_event] = session.scalars(select(TraceEventRecord)).all()
        [policy_decision] = trace_event.policy_decisions
        assert policy_decision.trace_event_id == trace_event.id
        assert policy_decision.decision is PolicyDecisionValue.ALLOW


def test_tool_call_requested_with_deny_policy_creates_policy_decision(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    create_policy_rule(
        session_factory,
        condition={
            "decision": "deny",
            "reason": "The requested tool is denied.",
            "tool_name": "send_email",
        },
    )

    response = client.post("/telemetry/events", json=trace_event_payload(agent_id))

    assert response.status_code == 201
    assert response.json()["policy_decision"]["decision"] == "deny"
    assert response.json()["human_approval_id"] is None
    [saved_decision] = fetch_policy_decisions(session_factory)
    assert saved_decision.decision is PolicyDecisionValue.DENY
    assert saved_decision.reason == "The requested tool is denied."
    assert fetch_human_approvals(session_factory) == []


def test_tool_call_requested_with_review_policy_creates_decision_and_approval(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    create_policy_rule(
        session_factory,
        condition={
            "decision": "require_human_review",
            "reason": "The requested tool requires human review.",
            "tool_name": "send_email",
        },
    )

    response = client.post("/telemetry/events", json=trace_event_payload(agent_id))

    assert response.status_code == 201
    body = response.json()
    assert body["policy_decision"]["decision"] == "require_human_review"
    assert body["human_approval_id"] is not None
    [saved_decision] = fetch_policy_decisions(session_factory)
    assert saved_decision.decision is PolicyDecisionValue.REQUIRE_HUMAN_REVIEW
    assert saved_decision.reason == "The requested tool requires human review."
    [approval] = fetch_human_approvals(session_factory)
    assert body["human_approval_id"] == str(approval.id)
    assert approval.status is HumanApprovalStatus.PENDING
    assert approval.agent_id == agent_id
    assert approval.policy_decision_id == saved_decision.id
    assert approval.requested_by_actor_type is ActorType.DEVELOPMENT
    assert approval.requested_by_actor_id == "dev-placeholder"
    [audit_log] = fetch_human_approval_audit_logs(session_factory)
    assert audit_log.event_type == "human_approval_requested"
    assert audit_log.actor_type is ActorType.DEVELOPMENT
    assert audit_log.actor_id == "dev-placeholder"
    assert audit_log.actor_type is approval.requested_by_actor_type
    assert audit_log.actor_id == approval.requested_by_actor_id
    assert audit_log.entity_id == str(approval.id)
    assert audit_log.metadata_["agent_id"] == str(agent_id)
    assert audit_log.metadata_["policy_decision_id"] == str(saved_decision.id)


def test_tool_call_requested_with_service_api_key_uses_service_actor(
    api_client: tuple[TestClient, SessionFactory],
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    configure_service_actor_api_key(monkeypatch, require_auth=True)
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    create_policy_rule(
        session_factory,
        condition={
            "decision": "require_human_review",
            "reason": "The requested tool requires human review.",
            "tool_name": "send_email",
        },
    )

    response = client.post(
        "/telemetry/events",
        json=trace_event_payload(agent_id),
        headers={"X-AGCP-API-Key": SERVICE_API_KEY},
    )
    set_evidence_export_actor()
    bundle_response = client.get(f"/agents/{agent_id}/evidence-bundle")

    assert response.status_code == 201
    assert bundle_response.status_code == 200
    [approval] = fetch_human_approvals(session_factory)
    assert approval.requested_by_actor_type is ActorType.SERVICE
    assert approval.requested_by_actor_id == SERVICE_ACTOR_ID
    [audit_log] = fetch_human_approval_audit_logs(session_factory)
    assert audit_log.actor_type is ActorType.SERVICE
    assert audit_log.actor_id == SERVICE_ACTOR_ID
    [trace_event] = fetch_trace_events(session_factory)
    assert SERVICE_API_KEY not in str(trace_event.metadata_)
    assert SERVICE_API_KEY not in response.text
    assert SERVICE_API_KEY not in bundle_response.text
    assert SERVICE_API_KEY not in str(audit_log.metadata_)
    assert SERVICE_API_KEY not in caplog.text


def test_ingest_missing_api_key_when_service_auth_required_rejects_without_records(
    api_client: tuple[TestClient, SessionFactory],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AGCP_REQUIRE_SERVICE_AUTH", "true")
    get_settings.cache_clear()
    client, session_factory = api_client
    agent_id = create_agent(session_factory)

    response = client.post("/telemetry/events", json=trace_event_payload(agent_id))

    assert response.status_code == 401
    assert response.json()["detail"] == "AGCP service actor API key is required."
    assert fetch_agent_runs(session_factory) == []
    assert fetch_trace_events(session_factory) == []
    assert fetch_policy_decisions(session_factory) == []
    assert fetch_human_approvals(session_factory) == []
    assert fetch_human_approval_audit_logs(session_factory) == []


def test_ingest_service_api_key_without_telemetry_scope_is_rejected_without_records(
    api_client: tuple[TestClient, SessionFactory],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configure_service_actor_api_key(
        monkeypatch,
        scopes=("runtime:decision",),
        require_auth=True,
    )
    client, session_factory = api_client
    agent_id = create_agent(session_factory)

    response = client.post(
        "/telemetry/events",
        json=trace_event_payload(agent_id),
        headers={"X-AGCP-API-Key": SERVICE_API_KEY},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == (
        "Service actor requires scope: telemetry:write."
    )
    assert SERVICE_API_KEY not in response.text
    assert fetch_agent_runs(session_factory) == []
    assert fetch_trace_events(session_factory) == []
    assert fetch_policy_decisions(session_factory) == []
    assert fetch_human_approvals(session_factory) == []
    assert fetch_human_approval_audit_logs(session_factory) == []


def test_ingest_service_scope_rule_allows_matching_agent_environment_and_tool(
    api_client: tuple[TestClient, SessionFactory],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    configure_service_actor_api_key(
        monkeypatch,
        require_auth=True,
        scope_rule={
            "agent_ids": [str(agent_id)],
            "environments": ["development"],
            "tool_names": ["send_email"],
        },
    )

    response = client.post(
        "/telemetry/events",
        json=trace_event_payload(agent_id),
        headers={"X-AGCP-API-Key": SERVICE_API_KEY},
    )

    assert response.status_code == 201
    assert len(fetch_agent_runs(session_factory)) == 1
    assert len(fetch_trace_events(session_factory)) == 1


def test_ingest_service_scope_rule_denies_non_matching_tool_without_records(
    api_client: tuple[TestClient, SessionFactory],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    configure_service_actor_api_key(
        monkeypatch,
        require_auth=True,
        scope_rule={
            "agent_ids": [str(agent_id)],
            "environments": ["development"],
            "tool_names": ["send_payment"],
        },
    )

    response = client.post(
        "/telemetry/events",
        json=trace_event_payload(agent_id),
        headers={"X-AGCP-API-Key": SERVICE_API_KEY},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == (
        "Service actor is not permitted for this tool name."
    )
    assert SERVICE_API_KEY not in response.text
    assert fetch_agent_runs(session_factory) == []
    assert fetch_trace_events(session_factory) == []
    assert fetch_policy_decisions(session_factory) == []


def test_ingest_missing_fine_grained_rule_in_strict_mode_denies_without_records(
    api_client: tuple[TestClient, SessionFactory],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configure_service_actor_api_key(
        monkeypatch,
        require_auth=True,
        include_scope_rule=False,
    )
    client, session_factory = api_client
    agent_id = create_agent(session_factory)

    response = client.post(
        "/telemetry/events",
        json=trace_event_payload(agent_id),
        headers={"X-AGCP-API-Key": SERVICE_API_KEY},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == (
        "Service actor requires a fine-grained scope rule."
    )
    assert SERVICE_API_KEY not in response.text
    assert fetch_agent_runs(session_factory) == []
    assert fetch_trace_events(session_factory) == []
    assert fetch_policy_decisions(session_factory) == []


def test_ingest_invalid_service_api_key_is_rejected_without_records(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)

    response = client.post(
        "/telemetry/events",
        json=trace_event_payload(agent_id),
        headers={"X-AGCP-API-Key": "invalid-local-test-key"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid AGCP service actor API key."
    assert fetch_agent_runs(session_factory) == []
    assert fetch_trace_events(session_factory) == []
    assert fetch_policy_decisions(session_factory) == []
    assert fetch_human_approvals(session_factory) == []
    assert fetch_human_approval_audit_logs(session_factory) == []


def test_duplicate_review_event_returns_existing_approval(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    run_id = uuid4()
    external_event_id = "vendor-event-456"
    create_policy_rule(
        session_factory,
        condition={
            "decision": "require_human_review",
            "reason": "The requested tool requires human review.",
            "tool_name": "send_email",
        },
    )

    first_response = client.post(
        "/telemetry/events",
        json=trace_event_payload(
            agent_id,
            run_id=run_id,
            external_event_id=external_event_id,
        ),
    )
    duplicate_response = client.post(
        "/telemetry/events",
        json=trace_event_payload(
            agent_id,
            run_id=run_id,
            external_event_id=external_event_id,
            summary="Retried event with changed body.",
        ),
    )

    assert first_response.status_code == 201
    assert duplicate_response.status_code == 200
    assert duplicate_response.json() == first_response.json()
    assert first_response.json()["human_approval_id"] is not None
    assert len(fetch_trace_events(session_factory)) == 1
    assert len(fetch_policy_decisions(session_factory)) == 1
    assert len(fetch_human_approvals(session_factory)) == 1
    assert len(fetch_human_approval_audit_logs(session_factory)) == 1


def test_duplicate_review_event_with_active_policy_version_keeps_idempotency(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    run_id = uuid4()
    external_event_id = "vendor-versioned-review-event"
    policy_id, rule_id = create_policy_rule(
        session_factory,
        condition={
            "decision": "allow",
            "reason": "Live mutable rule should not be used.",
            "tool_name": "send_email",
        },
    )
    version_id = create_policy_version(
        session_factory,
        policy_id=policy_id,
        rule_id=rule_id,
        status=PolicyVersionStatus.ACTIVE,
        condition={
            "decision": "require_human_review",
            "reason": "Reviewed snapshot requires human review.",
            "tool_name": "send_email",
        },
    )

    first_response = client.post(
        "/telemetry/events",
        json=trace_event_payload(
            agent_id,
            run_id=run_id,
            external_event_id=external_event_id,
        ),
    )
    duplicate_response = client.post(
        "/telemetry/events",
        json=trace_event_payload(
            agent_id,
            run_id=run_id,
            external_event_id=external_event_id,
            summary="Retried event with changed body.",
        ),
    )

    assert first_response.status_code == 201
    assert duplicate_response.status_code == 200
    assert duplicate_response.json() == first_response.json()
    first_body = first_response.json()
    assert first_body["policy_decision"]["decision"] == "require_human_review"
    assert first_body["policy_decision"]["policy_version_id"] == str(version_id)
    assert first_body["human_approval_id"] is not None
    assert len(fetch_trace_events(session_factory)) == 1
    [saved_decision] = fetch_policy_decisions(session_factory)
    assert saved_decision.policy_id == policy_id
    assert saved_decision.policy_version_id == version_id
    assert saved_decision.rule_id == rule_id
    assert saved_decision.decision is PolicyDecisionValue.REQUIRE_HUMAN_REVIEW
    [approval] = fetch_human_approvals(session_factory)
    assert approval.id == UUID(first_body["human_approval_id"])
    assert approval.policy_decision_id == saved_decision.id
    assert approval.status is HumanApprovalStatus.PENDING
    assert len(fetch_human_approval_audit_logs(session_factory)) == 1


def test_tool_call_requested_without_matching_policy_creates_not_applicable_decision(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    create_policy_rule(
        session_factory,
        condition={
            "decision": "deny",
            "reason": "Only payment tools are denied.",
            "tool_name": "send_payment",
        },
    )

    response = client.post("/telemetry/events", json=trace_event_payload(agent_id))

    assert response.status_code == 201
    assert response.json()["policy_decision"]["decision"] == "not_applicable"
    assert response.json()["human_approval_id"] is None
    [saved_decision] = fetch_policy_decisions(session_factory)
    assert saved_decision.decision is PolicyDecisionValue.NOT_APPLICABLE
    assert saved_decision.policy_id is None
    assert saved_decision.rule_id is None
    assert fetch_human_approvals(session_factory) == []


def test_non_tool_call_requested_event_does_not_create_policy_decision(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    create_policy_rule(
        session_factory,
        condition={
            "decision": "deny",
            "reason": "The requested tool is denied.",
            "tool_name": "send_email",
        },
    )

    response = client.post(
        "/telemetry/events",
        json=trace_event_payload(
            agent_id,
            event_type="model_call_started",
            metadata={},
            summary="Model call started.",
        ),
    )

    assert response.status_code == 201
    assert response.json()["policy_decision"] is None
    assert response.json()["human_approval_id"] is None
    assert fetch_policy_decisions(session_factory) == []
    assert fetch_human_approvals(session_factory) == []


def test_tool_call_requested_missing_tool_name_is_rejected(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)

    response = client.post(
        "/telemetry/events",
        json=trace_event_payload(agent_id, metadata={}),
    )

    assert response.status_code == 422
    assert response.json()["detail"] == (
        "metadata.tool_name is required for tool_call_requested events."
    )
    assert fetch_trace_events(session_factory) == []
    assert fetch_policy_decisions(session_factory) == []


def test_tool_call_policy_decision_and_trace_event_are_atomic(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    create_policy_rule(
        session_factory,
        condition={
            "decision": "deny",
            "reason": "Unsupported matching field.",
            "model_name": "gpt-example",
        },
    )

    response = client.post("/telemetry/events", json=trace_event_payload(agent_id))

    assert response.status_code == 422
    assert response.json()["detail"] == (
        "Unsupported PolicyRule condition fields: model_name."
    )
    assert fetch_agent_runs(session_factory) == []
    assert fetch_trace_events(session_factory) == []
    assert fetch_policy_decisions(session_factory) == []
    assert fetch_human_approvals(session_factory) == []


def test_review_approval_creation_is_atomic(
    api_client: tuple[TestClient, SessionFactory],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    create_policy_rule(
        session_factory,
        condition={
            "decision": "require_human_review",
            "reason": "The requested tool requires human review.",
            "tool_name": "send_email",
        },
    )

    def fail_audit_append(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("audit append failed")

    monkeypatch.setattr(telemetry_api, "append_audit_log", fail_audit_append)

    with pytest.raises(RuntimeError, match="audit append failed"):
        client.post("/telemetry/events", json=trace_event_payload(agent_id))

    assert fetch_agent_runs(session_factory) == []
    assert fetch_trace_events(session_factory) == []
    assert fetch_policy_decisions(session_factory) == []
    assert fetch_human_approvals(session_factory) == []
    assert fetch_human_approval_audit_logs(session_factory) == []


def test_ingest_allows_same_external_event_id_for_different_run(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    external_event_id = "vendor-event-123"

    first_response = client.post(
        "/telemetry/events",
        json=trace_event_payload(agent_id, external_event_id=external_event_id),
    )
    second_response = client.post(
        "/telemetry/events",
        json=trace_event_payload(agent_id, external_event_id=external_event_id),
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 201
    assert len(fetch_trace_events(session_factory)) == 2
    assert len(fetch_agent_runs(session_factory)) == 2


def test_ingest_auto_creates_agent_run_record(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    run_id = uuid4()

    response = client.post(
        "/telemetry/events",
        json=trace_event_payload(agent_id, run_id=run_id),
    )

    assert response.status_code == 201
    [saved_run] = fetch_agent_runs(session_factory)
    assert saved_run.agent_id == agent_id
    assert saved_run.run_id == run_id
    assert saved_run.correlation_id == "corr-123"
    assert saved_run.environment is Environment.DEVELOPMENT
    assert saved_run.status == "observed"
    assert saved_run.metadata_ == {}


def test_ingest_attaches_event_to_existing_agent_run_record(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    run_id = uuid4()
    create_agent_run(session_factory, agent_id, run_id)

    response = client.post(
        "/telemetry/events",
        json=trace_event_payload(agent_id, run_id=run_id),
    )

    assert response.status_code == 201
    assert len(fetch_agent_runs(session_factory)) == 1
    [saved_event] = fetch_trace_events(session_factory)
    assert saved_event.agent_id == agent_id
    assert saved_event.run_id == run_id


def test_ingest_rejects_unknown_agent(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client

    response = client.post(
        "/telemetry/events",
        json=trace_event_payload(uuid4()),
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Agent not found."
    assert fetch_agent_runs(session_factory) == []
    assert fetch_trace_events(session_factory) == []


def test_ingest_rejects_unsafe_metadata(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)

    response = client.post(
        "/telemetry/events",
        json=trace_event_payload(agent_id, metadata={"api_key": "redacted"}),
    )

    assert response.status_code == 422
    assert fetch_agent_runs(session_factory) == []
    assert fetch_trace_events(session_factory) == []


def test_ingest_rejects_invalid_event_type(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)

    response = client.post(
        "/telemetry/events",
        json=trace_event_payload(agent_id, event_type="tool_call_finished"),
    )

    assert response.status_code == 422
    assert fetch_agent_runs(session_factory) == []
    assert fetch_trace_events(session_factory) == []


def test_ingest_preserves_agent_id_run_id_integrity(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_a_id = create_agent(session_factory, name="Support assistant")
    agent_b_id = create_agent(session_factory, name="Risk review assistant")
    shared_run_id = uuid4()
    create_agent_run(session_factory, agent_b_id, shared_run_id)

    response = client.post(
        "/telemetry/events",
        json=trace_event_payload(agent_a_id, run_id=shared_run_id),
    )

    assert response.status_code == 201
    runs = fetch_agent_runs(session_factory)
    assert {(run.agent_id, run.run_id) for run in runs} == {
        (agent_a_id, shared_run_id),
        (agent_b_id, shared_run_id),
    }
    [saved_event] = fetch_trace_events(session_factory)
    assert saved_event.agent_id == agent_a_id
    assert saved_event.run_id == shared_run_id


def create_agent(
    session_factory: SessionFactory,
    *,
    name: str = "Support assistant",
    environment: Environment = Environment.DEVELOPMENT,
) -> UUID:
    with session_factory() as session:
        agent = Agent(
            name=name,
            description=None,
            owner_type=OwnerType.TEAM,
            owner_id="team:ai-platform",
            owner_name="AI Platform",
            owner_contact_email="owner@example.com",
            environment=environment,
            status=AgentStatus.DRAFT,
            risk_level=RiskLevel.LOW,
            framework="LangGraph",
        )
        session.add(agent)
        session.commit()
        return agent.id


def set_evidence_export_actor() -> None:
    app.dependency_overrides[get_current_actor] = lambda: ActorContext(
        actor_type=ActorType.USER,
        actor_id="user:telemetry-auditor",
        roles=("auditor",),
    )


def create_agent_run(
    session_factory: SessionFactory,
    agent_id: UUID,
    run_id: UUID,
) -> None:
    with session_factory() as session:
        run = AgentRunRecord(
            agent_id=agent_id,
            run_id=run_id,
            correlation_id="corr-123",
            environment=Environment.DEVELOPMENT,
            status="started",
            started_at=datetime.now(UTC),
            summary="Agent run started.",
            metadata_={},
        )
        session.add(run)
        session.commit()


def fetch_agent_runs(session_factory: SessionFactory) -> list[AgentRunRecord]:
    with session_factory() as session:
        return list(session.scalars(select(AgentRunRecord)).all())


def fetch_trace_events(session_factory: SessionFactory) -> list[TraceEventRecord]:
    with session_factory() as session:
        return list(session.scalars(select(TraceEventRecord)).all())


def fetch_policy_decisions(session_factory: SessionFactory) -> list[PolicyDecision]:
    with session_factory() as session:
        return list(session.scalars(select(PolicyDecision)).all())


def fetch_human_approvals(session_factory: SessionFactory) -> list[HumanApproval]:
    with session_factory() as session:
        return list(session.scalars(select(HumanApproval)).all())


def fetch_human_approval_audit_logs(
    session_factory: SessionFactory,
) -> list[AuditLog]:
    with session_factory() as session:
        statement = (
            select(AuditLog)
            .where(AuditLog.entity_type == "human_approval")
            .order_by(AuditLog.created_at, AuditLog.id)
        )
        return list(session.scalars(statement).all())


def create_policy_rule(
    session_factory: SessionFactory,
    *,
    condition: dict[str, str],
    status: PolicyStatus = PolicyStatus.ACTIVE,
) -> tuple[UUID, UUID]:
    with session_factory() as session:
        policy = Policy(
            name="Tool access policy",
            description=None,
            status=status,
        )
        session.add(policy)
        session.flush()

        rule = PolicyRule(
            policy_id=policy.id,
            name="Tool access rule",
            description=None,
            condition=json.dumps(condition),
        )
        session.add(rule)
        session.commit()
        return policy.id, rule.id


def create_policy_version(
    session_factory: SessionFactory,
    *,
    policy_id: UUID,
    rule_id: UUID,
    condition: dict[str, str],
    status: PolicyVersionStatus,
) -> UUID:
    now = datetime.now(UTC)
    with session_factory() as session:
        policy = session.get(Policy, policy_id)
        rule = session.get(PolicyRule, rule_id)
        assert policy is not None
        assert rule is not None
        version = PolicyVersion(
            policy_id=policy_id,
            version_number=1,
            status=status,
            change_summary="Reviewed telemetry evaluation snapshot.",
            policy_snapshot={
                "id": str(policy.id),
                "name": policy.name,
                "description": policy.description,
                "status": policy.status.value,
            },
            rule_snapshots=[
                {
                    "id": str(rule.id),
                    "policy_id": str(policy_id),
                    "name": rule.name,
                    "description": rule.description,
                    "condition": json.dumps(condition),
                }
            ],
            check_step_snapshots=[],
            created_by_actor_type=ActorType.DEVELOPMENT,
            created_by_actor_id="dev-placeholder",
            activated_at=now if status is PolicyVersionStatus.ACTIVE else None,
            superseded_at=now if status is PolicyVersionStatus.SUPERSEDED else None,
            archived_at=now if status is PolicyVersionStatus.ARCHIVED else None,
        )
        session.add(version)
        session.commit()
        return version.id


def configure_service_actor_api_key(
    monkeypatch: pytest.MonkeyPatch,
    *,
    scopes: tuple[str, ...] = ("telemetry:write",),
    require_auth: bool = False,
    scope_rule: dict[str, object] | None = None,
    include_scope_rule: bool = True,
) -> None:
    monkeypatch.setenv(
        "AGCP_SERVICE_ACTOR_API_KEYS",
        f"{SERVICE_ACTOR_ID}={hash_service_actor_api_key(SERVICE_API_KEY)}",
    )
    monkeypatch.setenv(
        "AGCP_SERVICE_ACTOR_SCOPES",
        f"{SERVICE_ACTOR_ID}={','.join(scopes)}",
    )
    if include_scope_rule:
        monkeypatch.setenv(
            "AGCP_SERVICE_ACTOR_SCOPE_RULES",
            json.dumps(
                {
                    SERVICE_ACTOR_ID: scope_rule
                    or {
                        "agent_ids": ["*"],
                        "environments": ["*"],
                        "tool_names": ["*"],
                    }
                }
            ),
        )
    if require_auth:
        monkeypatch.setenv("AGCP_REQUIRE_SERVICE_AUTH", "true")
    get_settings.cache_clear()


def trace_event_payload(
    agent_id: UUID,
    *,
    event_id: UUID | None = None,
    run_id: UUID | None = None,
    external_event_id: str | None = None,
    event_type: str = "tool_call_requested",
    metadata: dict[str, object] | None = None,
    summary: str = "Tool call requested.",
) -> dict[str, object]:
    payload = {
        "id": str(event_id or uuid4()),
        "agent_id": str(agent_id),
        "run_id": str(run_id or uuid4()),
        "correlation_id": "corr-123",
        "event_type": event_type,
        "timestamp": datetime.now(UTC).isoformat(),
        "summary": summary,
        "metadata": metadata if metadata is not None else {"tool_name": "send_email"},
    }
    if external_event_id is not None:
        payload["external_event_id"] = external_event_id

    return payload
