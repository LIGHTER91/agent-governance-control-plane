import json
from collections.abc import Callable, Iterator
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy import event as sqlalchemy_event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import agent_governance_api.runtime_gateway_api as runtime_gateway_api
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
    RiskLevel,
    TraceEventRecord,
    TraceEventType,
)

SessionFactory = Callable[[], Session]


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


def test_runtime_simulation_with_allow_policy_returns_allow(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    policy_id, rule_id = create_policy_rule(
        session_factory,
        decision=PolicyDecisionValue.ALLOW,
        reason="The requested tool is allowed.",
    )

    response = client.post(
        "/runtime/tool-calls/decision",
        json=runtime_decision_payload(agent_id),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["decision"] == "allow"
    assert body["proceed"] is True
    assert body["reason"] == "The requested tool is allowed."
    assert body["trace_event_id"] is not None
    assert body["policy_decision_id"] is not None
    assert body["human_approval_id"] is None

    [trace_event] = fetch_trace_events(session_factory)
    assert trace_event.external_event_id == "runtime-request-001"
    assert trace_event.event_type is TraceEventType.TOOL_CALL_REQUESTED
    assert trace_event.summary == "Send a support follow-up email."
    assert trace_event.metadata_ == {
        "ticket_category": "support",
        "tool_name": "send_email",
    }
    [policy_decision] = fetch_policy_decisions(session_factory)
    assert policy_decision.decision is PolicyDecisionValue.ALLOW
    assert policy_decision.policy_id == policy_id
    assert policy_decision.rule_id == rule_id
    assert policy_decision.trace_event_id == trace_event.id
    assert fetch_human_approvals(session_factory) == []


def test_runtime_simulation_behavior_is_unchanged_by_failure_policy_config(
    api_client: tuple[TestClient, SessionFactory],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AGCP_RUNTIME_FAILURE_DEFAULT", "record_only")
    get_settings.cache_clear()
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    create_policy_rule(
        session_factory,
        decision=PolicyDecisionValue.DENY,
        reason="The requested tool is denied.",
    )

    response = client.post(
        "/runtime/tool-calls/decision",
        json=runtime_decision_payload(agent_id),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["decision"] == "deny"
    assert body["proceed"] is False
    assert body["human_approval_id"] is None
    assert len(fetch_trace_events(session_factory)) == 1
    [policy_decision] = fetch_policy_decisions(session_factory)
    assert policy_decision.decision is PolicyDecisionValue.DENY


def test_runtime_simulation_with_deny_policy_returns_deny(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    create_policy_rule(
        session_factory,
        decision=PolicyDecisionValue.DENY,
        reason="The requested tool is denied.",
    )

    response = client.post(
        "/runtime/tool-calls/decision",
        json=runtime_decision_payload(agent_id),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["decision"] == "deny"
    assert body["proceed"] is False
    assert body["reason"] == "The requested tool is denied."
    assert body["human_approval_id"] is None
    [policy_decision] = fetch_policy_decisions(session_factory)
    assert policy_decision.decision is PolicyDecisionValue.DENY
    assert fetch_human_approvals(session_factory) == []


def test_runtime_simulation_with_review_policy_creates_human_approval(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    create_policy_rule(
        session_factory,
        decision=PolicyDecisionValue.REQUIRE_HUMAN_REVIEW,
        reason="The requested tool requires human review.",
    )

    response = client.post(
        "/runtime/tool-calls/decision",
        json=runtime_decision_payload(agent_id),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["decision"] == "require_human_review"
    assert body["proceed"] is False
    assert body["human_approval_id"] is not None

    [policy_decision] = fetch_policy_decisions(session_factory)
    [approval] = fetch_human_approvals(session_factory)
    assert approval.id == UUID(body["human_approval_id"])
    assert approval.agent_id == agent_id
    assert approval.policy_decision_id == policy_decision.id
    assert approval.status is HumanApprovalStatus.PENDING
    assert approval.requested_by_actor_type is ActorType.DEVELOPMENT
    assert approval.requested_by_actor_id == "dev-placeholder"

    [audit_log] = fetch_human_approval_audit_logs(session_factory)
    assert audit_log.event_type == "human_approval_requested"
    assert audit_log.actor_type is ActorType.DEVELOPMENT
    assert audit_log.actor_id == "dev-placeholder"
    assert audit_log.entity_id == str(approval.id)
    assert audit_log.metadata_ == {
        "agent_id": str(agent_id),
        "status": "pending",
        "policy_decision_id": str(policy_decision.id),
    }


def test_runtime_simulation_without_matching_policy_returns_not_applicable(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    create_policy_rule(
        session_factory,
        decision=PolicyDecisionValue.DENY,
        reason="Payment tool use is denied.",
        tool_name="send_payment",
    )

    response = client.post(
        "/runtime/tool-calls/decision",
        json=runtime_decision_payload(agent_id),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["decision"] == "not_applicable"
    assert body["proceed"] is False
    assert body["human_approval_id"] is None
    [policy_decision] = fetch_policy_decisions(session_factory)
    assert policy_decision.decision is PolicyDecisionValue.NOT_APPLICABLE
    assert policy_decision.policy_id is None
    assert policy_decision.rule_id is None
    assert fetch_human_approvals(session_factory) == []


def test_runtime_policy_evaluation_failure_defaults_to_fail_closed_deny(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    create_unsupported_policy_rule(session_factory)

    response = client.post(
        "/runtime/tool-calls/decision",
        json=runtime_decision_payload(agent_id),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["decision"] == "deny"
    assert body["proceed"] is False
    assert body["reason"] == (
        "Policy evaluation failed; runtime failure policy fail_closed_deny "
        "selected deny."
    )
    assert body["trace_event_id"] is not None
    assert body["policy_decision_id"] is not None
    assert body["human_approval_id"] is None

    [trace_event] = fetch_trace_events(session_factory)
    assert trace_event.metadata_ == {
        "ticket_category": "support",
        "tool_name": "send_email",
        "runtime_failure_category": "policy_evaluation",
        "runtime_failure_default": "fail_closed_deny",
    }
    [policy_decision] = fetch_policy_decisions(session_factory)
    assert policy_decision.decision is PolicyDecisionValue.DENY
    assert policy_decision.trace_event_id == trace_event.id
    assert policy_decision.policy_id is None
    assert policy_decision.rule_id is None
    assert fetch_human_approvals(session_factory) == []
    assert fetch_human_approval_audit_logs(session_factory) == []


def test_runtime_policy_evaluation_failure_can_fail_closed_to_human_review(
    api_client: tuple[TestClient, SessionFactory],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AGCP_RUNTIME_FAILURE_DEFAULT", "fail_closed_human_review")
    get_settings.cache_clear()
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    create_unsupported_policy_rule(session_factory)

    response = client.post(
        "/runtime/tool-calls/decision",
        json=runtime_decision_payload(agent_id),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["decision"] == "require_human_review"
    assert body["proceed"] is False
    assert body["reason"] == (
        "Policy evaluation failed; runtime failure policy "
        "fail_closed_human_review requested human review."
    )
    assert body["trace_event_id"] is not None
    assert body["policy_decision_id"] is not None
    assert body["human_approval_id"] is not None

    [trace_event] = fetch_trace_events(session_factory)
    assert trace_event.metadata_ == {
        "ticket_category": "support",
        "tool_name": "send_email",
        "runtime_failure_category": "policy_evaluation",
        "runtime_failure_default": "fail_closed_human_review",
    }
    [policy_decision] = fetch_policy_decisions(session_factory)
    [human_approval] = fetch_human_approvals(session_factory)
    [audit_log] = fetch_human_approval_audit_logs(session_factory)
    assert policy_decision.decision is PolicyDecisionValue.REQUIRE_HUMAN_REVIEW
    assert policy_decision.trace_event_id == trace_event.id
    assert human_approval.policy_decision_id == policy_decision.id
    assert human_approval.requested_by_actor_type is ActorType.DEVELOPMENT
    assert human_approval.requested_by_actor_id == "dev-placeholder"
    assert audit_log.event_type == "human_approval_requested"
    assert audit_log.actor_type is ActorType.DEVELOPMENT
    assert audit_log.actor_id == "dev-placeholder"
    assert audit_log.entity_id == str(human_approval.id)


def test_runtime_policy_evaluation_failure_can_record_only_in_simulation(
    api_client: tuple[TestClient, SessionFactory],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AGCP_RUNTIME_FAILURE_DEFAULT", "record_only")
    get_settings.cache_clear()
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    create_unsupported_policy_rule(session_factory)

    response = client.post(
        "/runtime/tool-calls/decision",
        json=runtime_decision_payload(agent_id),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["decision"] == "not_applicable"
    assert body["proceed"] is False
    assert body["reason"] == (
        "Policy evaluation failed; runtime failure policy record_only recorded "
        "the failure in simulation mode."
    )
    assert body["trace_event_id"] is not None
    assert body["policy_decision_id"] is None
    assert body["human_approval_id"] is None

    [trace_event] = fetch_trace_events(session_factory)
    assert trace_event.metadata_ == {
        "ticket_category": "support",
        "tool_name": "send_email",
        "runtime_failure_category": "policy_evaluation",
        "runtime_failure_default": "record_only",
    }
    assert fetch_policy_decisions(session_factory) == []
    assert fetch_human_approvals(session_factory) == []
    assert fetch_human_approval_audit_logs(session_factory) == []


def test_runtime_record_only_policy_failure_fails_closed_in_enforcement(
    api_client: tuple[TestClient, SessionFactory],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AGCP_RUNTIME_FAILURE_DEFAULT", "record_only")
    enable_runtime_enforcement(monkeypatch)
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    create_unsupported_policy_rule(session_factory)

    response = client.post(
        "/runtime/tool-calls/decision",
        json=runtime_decision_payload(agent_id, mode="enforcement"),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["decision"] == "deny"
    assert body["proceed"] is False
    assert body["reason"] == (
        "Policy evaluation failed; runtime failure policy fail_closed_deny "
        "selected deny."
    )
    assert body["policy_decision_id"] is not None
    assert body["human_approval_id"] is None

    [trace_event] = fetch_trace_events(session_factory)
    assert trace_event.metadata_["runtime_failure_default"] == "fail_closed_deny"
    [policy_decision] = fetch_policy_decisions(session_factory)
    assert policy_decision.decision is PolicyDecisionValue.DENY
    assert fetch_human_approvals(session_factory) == []


def test_duplicate_record_only_policy_failure_returns_existing_response(
    api_client: tuple[TestClient, SessionFactory],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AGCP_RUNTIME_FAILURE_DEFAULT", "record_only")
    get_settings.cache_clear()
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    run_id = uuid4()
    create_unsupported_policy_rule(session_factory)

    first_response = client.post(
        "/runtime/tool-calls/decision",
        json=runtime_decision_payload(agent_id, run_id=run_id),
    )
    duplicate_response = client.post(
        "/runtime/tool-calls/decision",
        json=runtime_decision_payload(
            agent_id,
            run_id=run_id,
            action_summary="Retried request with changed summary.",
        ),
    )

    assert first_response.status_code == 201
    assert duplicate_response.status_code == 200
    assert duplicate_response.json() == first_response.json()
    assert len(fetch_agent_runs(session_factory)) == 1
    assert len(fetch_trace_events(session_factory)) == 1
    assert fetch_policy_decisions(session_factory) == []
    assert fetch_human_approvals(session_factory) == []
    assert fetch_human_approval_audit_logs(session_factory) == []


def test_runtime_failure_policy_persistence_failure_rolls_back_trace_event(
    api_client: tuple[TestClient, SessionFactory],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    create_unsupported_policy_rule(session_factory)

    def fail_policy_decision_persistence(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("failure policy decision persistence failed")

    monkeypatch.setattr(
        runtime_gateway_api,
        "persist_policy_decision",
        fail_policy_decision_persistence,
    )

    with pytest.raises(
        RuntimeError,
        match="failure policy decision persistence failed",
    ):
        client.post(
            "/runtime/tool-calls/decision",
            json=runtime_decision_payload(agent_id),
        )

    assert fetch_agent_runs(session_factory) == []
    assert fetch_trace_events(session_factory) == []
    assert fetch_policy_decisions(session_factory) == []
    assert fetch_human_approvals(session_factory) == []
    assert fetch_human_approval_audit_logs(session_factory) == []


def test_runtime_failure_policy_audit_failure_rolls_back_human_review_records(
    api_client: tuple[TestClient, SessionFactory],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AGCP_RUNTIME_FAILURE_DEFAULT", "fail_closed_human_review")
    get_settings.cache_clear()
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    create_unsupported_policy_rule(session_factory)

    def fail_audit_log(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("failure policy audit log failed")

    monkeypatch.setattr(runtime_gateway_api, "append_audit_log", fail_audit_log)

    with pytest.raises(RuntimeError, match="failure policy audit log failed"):
        client.post(
            "/runtime/tool-calls/decision",
            json=runtime_decision_payload(agent_id),
        )

    assert fetch_agent_runs(session_factory) == []
    assert fetch_trace_events(session_factory) == []
    assert fetch_policy_decisions(session_factory) == []
    assert fetch_human_approvals(session_factory) == []
    assert fetch_human_approval_audit_logs(session_factory) == []


def test_runtime_enforcement_with_allow_policy_returns_allow(
    api_client: tuple[TestClient, SessionFactory],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    enable_runtime_enforcement(monkeypatch)
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    policy_id, rule_id = create_policy_rule(
        session_factory,
        decision=PolicyDecisionValue.ALLOW,
        reason="The requested tool is allowed.",
    )

    response = client.post(
        "/runtime/tool-calls/decision",
        json=runtime_decision_payload(agent_id, mode="enforcement"),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["decision"] == "allow"
    assert body["proceed"] is True
    assert body["human_approval_id"] is None
    [agent_run] = fetch_agent_runs(session_factory)
    assert agent_run.status == "enforced"
    [policy_decision] = fetch_policy_decisions(session_factory)
    assert policy_decision.decision is PolicyDecisionValue.ALLOW
    assert policy_decision.policy_id == policy_id
    assert policy_decision.rule_id == rule_id
    assert fetch_human_approvals(session_factory) == []


def test_runtime_enforcement_with_deny_policy_returns_deny(
    api_client: tuple[TestClient, SessionFactory],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    enable_runtime_enforcement(monkeypatch)
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    create_policy_rule(
        session_factory,
        decision=PolicyDecisionValue.DENY,
        reason="The requested tool is denied.",
    )

    response = client.post(
        "/runtime/tool-calls/decision",
        json=runtime_decision_payload(agent_id, mode="enforcement"),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["decision"] == "deny"
    assert body["proceed"] is False
    assert body["human_approval_id"] is None
    [policy_decision] = fetch_policy_decisions(session_factory)
    assert policy_decision.decision is PolicyDecisionValue.DENY
    assert fetch_human_approvals(session_factory) == []


def test_runtime_enforcement_with_review_policy_creates_human_approval(
    api_client: tuple[TestClient, SessionFactory],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    enable_runtime_enforcement(monkeypatch)
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    create_policy_rule(
        session_factory,
        decision=PolicyDecisionValue.REQUIRE_HUMAN_REVIEW,
        reason="The requested tool requires human review.",
    )

    response = client.post(
        "/runtime/tool-calls/decision",
        json=runtime_decision_payload(agent_id, mode="enforcement"),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["decision"] == "require_human_review"
    assert body["proceed"] is False
    assert body["human_approval_id"] is not None

    [policy_decision] = fetch_policy_decisions(session_factory)
    [approval] = fetch_human_approvals(session_factory)
    assert approval.id == UUID(body["human_approval_id"])
    assert approval.policy_decision_id == policy_decision.id
    assert approval.status is HumanApprovalStatus.PENDING
    [audit_log] = fetch_human_approval_audit_logs(session_factory)
    assert audit_log.event_type == "human_approval_requested"
    assert audit_log.entity_id == str(approval.id)


def test_runtime_enforcement_without_matching_policy_returns_not_applicable(
    api_client: tuple[TestClient, SessionFactory],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    enable_runtime_enforcement(monkeypatch)
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    create_policy_rule(
        session_factory,
        decision=PolicyDecisionValue.DENY,
        reason="Payment tool use is denied.",
        tool_name="send_payment",
    )

    response = client.post(
        "/runtime/tool-calls/decision",
        json=runtime_decision_payload(agent_id, mode="enforcement"),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["decision"] == "not_applicable"
    assert body["proceed"] is False
    assert body["human_approval_id"] is None
    [policy_decision] = fetch_policy_decisions(session_factory)
    assert policy_decision.decision is PolicyDecisionValue.NOT_APPLICABLE
    assert fetch_human_approvals(session_factory) == []


def test_runtime_simulation_unknown_agent_returns_404(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client

    response = client.post(
        "/runtime/tool-calls/decision",
        json=runtime_decision_payload(uuid4()),
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Agent not found."
    assert fetch_agent_runs(session_factory) == []
    assert fetch_trace_events(session_factory) == []
    assert fetch_policy_decisions(session_factory) == []
    assert fetch_human_approvals(session_factory) == []
    assert fetch_human_approval_audit_logs(session_factory) == []


def test_runtime_unknown_agent_still_fails_closed_with_record_only_config(
    api_client: tuple[TestClient, SessionFactory],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AGCP_RUNTIME_FAILURE_DEFAULT", "record_only")
    get_settings.cache_clear()
    client, session_factory = api_client

    response = client.post(
        "/runtime/tool-calls/decision",
        json=runtime_decision_payload(uuid4()),
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Agent not found."
    assert fetch_agent_runs(session_factory) == []
    assert fetch_trace_events(session_factory) == []
    assert fetch_policy_decisions(session_factory) == []
    assert fetch_human_approvals(session_factory) == []
    assert fetch_human_approval_audit_logs(session_factory) == []


def test_runtime_gateway_rejects_telemetry_mode(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    payload = runtime_decision_payload(agent_id)
    payload["mode"] = "telemetry"

    response = client.post("/runtime/tool-calls/decision", json=payload)

    assert response.status_code == 501
    assert response.json()["detail"] == (
        "Runtime Gateway telemetry mode is not implemented for this endpoint yet. "
        "Use POST /telemetry/events for telemetry ingestion."
    )
    assert fetch_agent_runs(session_factory) == []
    assert fetch_trace_events(session_factory) == []
    assert fetch_policy_decisions(session_factory) == []
    assert fetch_human_approvals(session_factory) == []
    assert fetch_human_approval_audit_logs(session_factory) == []


def test_runtime_gateway_rejects_enforcement_when_disabled(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    payload = runtime_decision_payload(agent_id, mode="enforcement")

    response = client.post("/runtime/tool-calls/decision", json=payload)

    assert response.status_code == 501
    assert response.json()["detail"] == (
        "Runtime Gateway enforcement mode is disabled. Set "
        "AGCP_RUNTIME_ENFORCEMENT_ENABLED=true to enable it."
    )
    assert fetch_agent_runs(session_factory) == []
    assert fetch_trace_events(session_factory) == []
    assert fetch_policy_decisions(session_factory) == []
    assert fetch_human_approvals(session_factory) == []
    assert fetch_human_approval_audit_logs(session_factory) == []


def test_runtime_request_missing_tool_name_is_rejected_by_schema(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    payload = runtime_decision_payload(agent_id)
    payload.pop("tool_name")

    response = client.post("/runtime/tool-calls/decision", json=payload)

    assert response.status_code == 422
    assert fetch_agent_runs(session_factory) == []
    assert fetch_trace_events(session_factory) == []
    assert fetch_policy_decisions(session_factory) == []
    assert fetch_human_approvals(session_factory) == []
    assert fetch_human_approval_audit_logs(session_factory) == []


def test_runtime_request_unsafe_metadata_is_rejected(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    payload = runtime_decision_payload(agent_id)
    payload["metadata"] = {"api_key": "redacted"}

    response = client.post("/runtime/tool-calls/decision", json=payload)

    assert response.status_code == 422
    assert fetch_agent_runs(session_factory) == []
    assert fetch_trace_events(session_factory) == []
    assert fetch_policy_decisions(session_factory) == []
    assert fetch_human_approvals(session_factory) == []
    assert fetch_human_approval_audit_logs(session_factory) == []


def test_runtime_unsafe_metadata_still_fails_closed_with_record_only_config(
    api_client: tuple[TestClient, SessionFactory],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AGCP_RUNTIME_FAILURE_DEFAULT", "record_only")
    get_settings.cache_clear()
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    payload = runtime_decision_payload(agent_id)
    payload["metadata"] = {"api_key": "redacted"}

    response = client.post("/runtime/tool-calls/decision", json=payload)

    assert response.status_code == 422
    assert fetch_agent_runs(session_factory) == []
    assert fetch_trace_events(session_factory) == []
    assert fetch_policy_decisions(session_factory) == []
    assert fetch_human_approvals(session_factory) == []
    assert fetch_human_approval_audit_logs(session_factory) == []


def test_duplicate_runtime_request_returns_existing_response(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    run_id = uuid4()
    create_policy_rule(
        session_factory,
        decision=PolicyDecisionValue.REQUIRE_HUMAN_REVIEW,
        reason="The requested tool requires human review.",
    )

    first_response = client.post(
        "/runtime/tool-calls/decision",
        json=runtime_decision_payload(agent_id, run_id=run_id),
    )
    duplicate_response = client.post(
        "/runtime/tool-calls/decision",
        json=runtime_decision_payload(
            agent_id,
            run_id=run_id,
            action_summary="Retried request with changed summary.",
        ),
    )

    assert first_response.status_code == 201
    assert duplicate_response.status_code == 200
    assert duplicate_response.json() == first_response.json()
    assert len(fetch_agent_runs(session_factory)) == 1
    assert len(fetch_trace_events(session_factory)) == 1
    assert len(fetch_policy_decisions(session_factory)) == 1
    assert len(fetch_human_approvals(session_factory)) == 1
    assert len(fetch_human_approval_audit_logs(session_factory)) == 1


def test_duplicate_runtime_enforcement_request_returns_existing_response(
    api_client: tuple[TestClient, SessionFactory],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    enable_runtime_enforcement(monkeypatch)
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    run_id = uuid4()
    create_policy_rule(
        session_factory,
        decision=PolicyDecisionValue.REQUIRE_HUMAN_REVIEW,
        reason="The requested tool requires human review.",
    )

    first_response = client.post(
        "/runtime/tool-calls/decision",
        json=runtime_decision_payload(agent_id, run_id=run_id, mode="enforcement"),
    )
    duplicate_response = client.post(
        "/runtime/tool-calls/decision",
        json=runtime_decision_payload(
            agent_id,
            run_id=run_id,
            action_summary="Retried request with changed summary.",
            mode="enforcement",
        ),
    )

    assert first_response.status_code == 201
    assert duplicate_response.status_code == 200
    assert duplicate_response.json() == first_response.json()
    assert len(fetch_agent_runs(session_factory)) == 1
    assert len(fetch_trace_events(session_factory)) == 1
    assert len(fetch_policy_decisions(session_factory)) == 1
    assert len(fetch_human_approvals(session_factory)) == 1
    assert len(fetch_human_approval_audit_logs(session_factory)) == 1


def test_runtime_decision_records_are_atomic_when_policy_persistence_fails(
    api_client: tuple[TestClient, SessionFactory],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    create_policy_rule(
        session_factory,
        decision=PolicyDecisionValue.DENY,
        reason="The requested tool is denied.",
    )

    def fail_policy_decision_persistence(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("policy decision persistence failed")

    monkeypatch.setattr(
        runtime_gateway_api,
        "persist_policy_decision",
        fail_policy_decision_persistence,
    )

    with pytest.raises(RuntimeError, match="policy decision persistence failed"):
        client.post(
            "/runtime/tool-calls/decision",
            json=runtime_decision_payload(agent_id),
        )

    assert fetch_agent_runs(session_factory) == []
    assert fetch_trace_events(session_factory) == []
    assert fetch_policy_decisions(session_factory) == []
    assert fetch_human_approvals(session_factory) == []
    assert fetch_human_approval_audit_logs(session_factory) == []


def test_runtime_enforcement_records_are_atomic_when_policy_persistence_fails(
    api_client: tuple[TestClient, SessionFactory],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    enable_runtime_enforcement(monkeypatch)
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    create_policy_rule(
        session_factory,
        decision=PolicyDecisionValue.DENY,
        reason="The requested tool is denied.",
    )

    def fail_policy_decision_persistence(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("policy decision persistence failed")

    monkeypatch.setattr(
        runtime_gateway_api,
        "persist_policy_decision",
        fail_policy_decision_persistence,
    )

    with pytest.raises(RuntimeError, match="policy decision persistence failed"):
        client.post(
            "/runtime/tool-calls/decision",
            json=runtime_decision_payload(agent_id, mode="enforcement"),
        )

    assert fetch_agent_runs(session_factory) == []
    assert fetch_trace_events(session_factory) == []
    assert fetch_policy_decisions(session_factory) == []
    assert fetch_human_approvals(session_factory) == []
    assert fetch_human_approval_audit_logs(session_factory) == []


def test_runtime_decision_records_are_atomic_when_human_approval_creation_fails(
    api_client: tuple[TestClient, SessionFactory],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    create_policy_rule(
        session_factory,
        decision=PolicyDecisionValue.REQUIRE_HUMAN_REVIEW,
        reason="The requested tool requires human review.",
    )

    def fail_human_approval_creation(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("human approval creation failed")

    monkeypatch.setattr(
        runtime_gateway_api,
        "_create_human_approval_for_policy_decision",
        fail_human_approval_creation,
    )

    with pytest.raises(RuntimeError, match="human approval creation failed"):
        client.post(
            "/runtime/tool-calls/decision",
            json=runtime_decision_payload(agent_id),
        )

    assert fetch_agent_runs(session_factory) == []
    assert fetch_trace_events(session_factory) == []
    assert fetch_policy_decisions(session_factory) == []
    assert fetch_human_approvals(session_factory) == []
    assert fetch_human_approval_audit_logs(session_factory) == []


def test_runtime_decision_records_are_atomic_when_audit_log_fails(
    api_client: tuple[TestClient, SessionFactory],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    create_policy_rule(
        session_factory,
        decision=PolicyDecisionValue.REQUIRE_HUMAN_REVIEW,
        reason="The requested tool requires human review.",
    )

    def fail_audit_log(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("audit log persistence failed")

    monkeypatch.setattr(runtime_gateway_api, "append_audit_log", fail_audit_log)

    with pytest.raises(RuntimeError, match="audit log persistence failed"):
        client.post(
            "/runtime/tool-calls/decision",
            json=runtime_decision_payload(agent_id),
        )

    assert fetch_agent_runs(session_factory) == []
    assert fetch_trace_events(session_factory) == []
    assert fetch_policy_decisions(session_factory) == []
    assert fetch_human_approvals(session_factory) == []
    assert fetch_human_approval_audit_logs(session_factory) == []


def test_evidence_bundle_includes_runtime_trace_event_and_policy_decision(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    create_policy_rule(
        session_factory,
        decision=PolicyDecisionValue.DENY,
        reason="The requested tool is denied.",
    )

    runtime_response = client.post(
        "/runtime/tool-calls/decision",
        json=runtime_decision_payload(agent_id),
    )
    bundle_response = client.get(f"/agents/{agent_id}/evidence-bundle")

    assert runtime_response.status_code == 201
    assert bundle_response.status_code == 200
    runtime_body = runtime_response.json()
    bundle_body = bundle_response.json()

    [trace_event] = bundle_body["trace_events"]
    [policy_decision] = bundle_body["policy_decisions"]
    assert trace_event["id"] == runtime_body["trace_event_id"]
    assert trace_event["agent_id"] == str(agent_id)
    assert trace_event["run_id"] == runtime_body["run_id"]
    assert trace_event["external_event_id"] == "runtime-request-001"
    assert trace_event["event_type"] == "tool_call_requested"
    assert trace_event["metadata"] == {
        "ticket_category": "support",
        "tool_name": "send_email",
    }

    assert policy_decision["id"] == runtime_body["policy_decision_id"]
    assert policy_decision["agent_id"] == str(agent_id)
    assert policy_decision["trace_event_id"] == trace_event["id"]
    assert policy_decision["decision"] == "deny"
    assert policy_decision["policy"]
    assert policy_decision["rule"]


def test_evidence_bundle_includes_runtime_review_evidence_chain(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    run_id = uuid4()
    policy_id, rule_id = create_policy_rule(
        session_factory,
        decision=PolicyDecisionValue.REQUIRE_HUMAN_REVIEW,
        reason="The requested tool requires human review.",
    )

    runtime_response = client.post(
        "/runtime/tool-calls/decision",
        json=runtime_decision_payload(agent_id, run_id=run_id),
    )

    assert runtime_response.status_code == 201
    runtime_body = runtime_response.json()
    assert runtime_body["decision"] == "require_human_review"
    assert runtime_body["proceed"] is False
    assert runtime_body["human_approval_id"] is not None

    [agent_run] = fetch_agent_runs(session_factory)
    [trace_event] = fetch_trace_events(session_factory)
    [policy_decision] = fetch_policy_decisions(session_factory)
    [human_approval] = fetch_human_approvals(session_factory)
    [audit_log] = fetch_human_approval_audit_logs(session_factory)

    assert agent_run.agent_id == agent_id
    assert agent_run.run_id == run_id
    assert agent_run.status == "simulated"

    assert trace_event.id == UUID(runtime_body["trace_event_id"])
    assert trace_event.agent_id == agent_id
    assert trace_event.run_id == run_id
    assert trace_event.external_event_id == "runtime-request-001"
    assert trace_event.event_type is TraceEventType.TOOL_CALL_REQUESTED

    assert policy_decision.id == UUID(runtime_body["policy_decision_id"])
    assert policy_decision.agent_id == agent_id
    assert policy_decision.policy_id == policy_id
    assert policy_decision.rule_id == rule_id
    assert policy_decision.trace_event_id == trace_event.id
    assert policy_decision.decision is PolicyDecisionValue.REQUIRE_HUMAN_REVIEW

    assert human_approval.id == UUID(runtime_body["human_approval_id"])
    assert human_approval.agent_id == agent_id
    assert human_approval.policy_decision_id == policy_decision.id
    assert human_approval.status is HumanApprovalStatus.PENDING

    assert audit_log.event_type == "human_approval_requested"
    assert audit_log.entity_type == "human_approval"
    assert audit_log.entity_id == str(human_approval.id)
    assert audit_log.metadata_ == {
        "agent_id": str(agent_id),
        "status": "pending",
        "policy_decision_id": str(policy_decision.id),
    }

    bundle_response = client.get(f"/agents/{agent_id}/evidence-bundle")

    assert bundle_response.status_code == 200
    bundle_body = bundle_response.json()
    [bundle_agent_run] = bundle_body["agent_runs"]
    [bundle_trace_event] = bundle_body["trace_events"]
    [bundle_policy_decision] = bundle_body["policy_decisions"]
    [bundle_human_approval] = bundle_body["human_approvals"]
    human_approval_audit_logs = [
        bundle_audit_log
        for bundle_audit_log in bundle_body["audit_logs"]
        if bundle_audit_log["event_type"] == "human_approval_requested"
    ]
    [bundle_audit_log] = human_approval_audit_logs

    assert bundle_agent_run["run_id"] == str(run_id)
    assert bundle_agent_run["status"] == "simulated"

    assert bundle_trace_event["id"] == str(trace_event.id)
    assert bundle_trace_event["agent_id"] == str(agent_id)
    assert bundle_trace_event["run_id"] == str(run_id)
    assert bundle_trace_event["external_event_id"] == "runtime-request-001"
    assert bundle_trace_event["event_type"] == "tool_call_requested"
    assert bundle_trace_event["metadata"] == {
        "ticket_category": "support",
        "tool_name": "send_email",
    }

    assert bundle_policy_decision["id"] == str(policy_decision.id)
    assert bundle_policy_decision["agent_id"] == str(agent_id)
    assert bundle_policy_decision["policy_id"] == str(policy_id)
    assert bundle_policy_decision["rule_id"] == str(rule_id)
    assert bundle_policy_decision["trace_event_id"] == bundle_trace_event["id"]
    assert bundle_policy_decision["decision"] == "require_human_review"
    assert bundle_policy_decision["policy"] == {
        "id": str(policy_id),
        "name": "Tool access policy",
        "status": "active",
    }
    assert bundle_policy_decision["rule"] == {
        "id": str(rule_id),
        "policy_id": str(policy_id),
        "name": "Tool access rule",
    }

    assert bundle_human_approval["id"] == str(human_approval.id)
    assert bundle_human_approval["agent_id"] == str(agent_id)
    assert bundle_human_approval["policy_decision_id"] == bundle_policy_decision["id"]
    assert bundle_human_approval["status"] == "pending"
    assert bundle_human_approval["requested_by_actor_type"] == "development"
    assert bundle_human_approval["requested_by_actor_id"] == "dev-placeholder"

    assert bundle_audit_log["entity_type"] == "human_approval"
    assert bundle_audit_log["entity_id"] == bundle_human_approval["id"]
    assert bundle_audit_log["metadata"] == {
        "agent_id": str(agent_id),
        "status": "pending",
        "policy_decision_id": bundle_policy_decision["id"],
    }


def create_agent(
    session_factory: SessionFactory,
    *,
    name: str = "Support assistant",
) -> UUID:
    with session_factory() as session:
        agent = Agent(
            name=name,
            description=None,
            owner_type=OwnerType.TEAM,
            owner_id="team:ai-platform",
            owner_name="AI Platform",
            owner_contact_email="owner@example.com",
            environment=Environment.DEVELOPMENT,
            status=AgentStatus.DRAFT,
            risk_level=RiskLevel.LOW,
            framework="LangGraph",
        )
        session.add(agent)
        session.commit()
        return agent.id


def create_policy_rule(
    session_factory: SessionFactory,
    *,
    decision: PolicyDecisionValue,
    reason: str,
    tool_name: str = "send_email",
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
            condition=json.dumps(
                {
                    "decision": decision.value,
                    "reason": reason,
                    "tool_name": tool_name,
                }
            ),
        )
        session.add(rule)
        session.commit()
        return policy.id, rule.id


def create_unsupported_policy_rule(
    session_factory: SessionFactory,
) -> tuple[UUID, UUID]:
    with session_factory() as session:
        policy = Policy(
            name="Unsupported condition policy",
            description=None,
            status=PolicyStatus.ACTIVE,
        )
        session.add(policy)
        session.flush()

        rule = PolicyRule(
            policy_id=policy.id,
            name="Unsupported condition rule",
            description=None,
            condition=json.dumps(
                {
                    "decision": "deny",
                    "reason": "Unsupported condition should trigger failure policy.",
                    "unsupported_field": "not-supported",
                }
            ),
        )
        session.add(rule)
        session.commit()
        return policy.id, rule.id


def runtime_decision_payload(
    agent_id: UUID,
    *,
    run_id: UUID | None = None,
    request_id: str = "runtime-request-001",
    action_summary: str = "Send a support follow-up email.",
    mode: str = "simulation",
) -> dict[str, object]:
    return {
        "request_id": request_id,
        "agent_id": str(agent_id),
        "run_id": str(run_id or uuid4()),
        "correlation_id": "support-run-001",
        "tool_name": "send_email",
        "action_summary": action_summary,
        "metadata": {"ticket_category": "support"},
        "mode": mode,
    }


def enable_runtime_enforcement(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGCP_RUNTIME_ENFORCEMENT_ENABLED", "true")
    get_settings.cache_clear()


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
