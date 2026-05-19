import json
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy import event as sqlalchemy_event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from agent_governance_api.auth import hash_service_actor_api_key
from agent_governance_api.config import get_settings
from agent_governance_api.database import Base, get_db_session
from agent_governance_api.main import app
from agent_governance_api.models import (
    ActorType,
    Agent,
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
SERVICE_ACTOR_ID = "service:runtime-resume-test"
SERVICE_API_KEY = "local-test-runtime-resume-key"


@dataclass(frozen=True)
class ReviewChain:
    agent_id: UUID
    run_id: UUID
    original_request_id: str
    trace_event_id: UUID
    policy_decision_id: UUID
    human_approval_id: UUID


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


def test_runtime_resume_approved_approval_returns_allow_and_records_evidence(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    chain = create_review_chain(
        client,
        session_factory,
        approval_status=HumanApprovalStatus.APPROVED,
    )

    response = client.post(
        "/runtime/tool-calls/resume",
        json=runtime_resume_payload(chain),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["resume_id"] == "runtime-request-001:resume:001"
    assert body["original_request_id"] == "runtime-request-001"
    assert body["agent_id"] == str(chain.agent_id)
    assert body["run_id"] == str(chain.run_id)
    assert body["tool_name"] == "send_email"
    assert body["decision"] == "allow"
    assert body["proceed"] is True
    assert body["human_approval_status"] == "approved"
    assert body["policy_decision_id"] == str(chain.policy_decision_id)
    assert body["human_approval_id"] == str(chain.human_approval_id)
    assert body["trace_event_id"] is not None

    resume_trace = resume_trace_event(session_factory)
    assert resume_trace.external_event_id == "runtime-request-001:resume:001"
    assert resume_trace.event_type is TraceEventType.TOOL_CALL_RESUME_REQUESTED
    assert resume_trace.metadata_ == {
        "resume_channel": "polling",
        "tool_name": "send_email",
        "action_ref": "support-ticket-123:follow-up-email",
        "original_request_id": "runtime-request-001",
        "human_approval_id": str(chain.human_approval_id),
        "policy_decision_id": str(chain.policy_decision_id),
        "resume_decision": "allow",
        "proceed": True,
        "resume_reason": ("Human approval is approved and the resume context matches."),
        "human_approval_status": "approved",
    }

    [resume_audit_log] = fetch_resume_audit_logs(session_factory)
    assert resume_audit_log.event_type == "runtime_tool_call_resume_checked"
    assert resume_audit_log.actor_type is ActorType.DEVELOPMENT
    assert resume_audit_log.actor_id == "dev-placeholder"
    assert resume_audit_log.entity_type == "agent"
    assert resume_audit_log.entity_id == str(chain.agent_id)
    assert resume_audit_log.metadata_["trace_event_id"] == str(resume_trace.id)
    assert resume_audit_log.metadata_["decision"] == "allow"
    assert resume_audit_log.metadata_["proceed"] is True


def test_runtime_resume_with_service_api_key_uses_service_actor(
    api_client: tuple[TestClient, SessionFactory],
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    client, session_factory = api_client
    chain = create_review_chain(
        client,
        session_factory,
        approval_status=HumanApprovalStatus.APPROVED,
    )
    configure_service_actor_api_key(monkeypatch, require_auth=True)

    response = client.post(
        "/runtime/tool-calls/resume",
        json=runtime_resume_payload(chain),
        headers={"X-AGCP-API-Key": SERVICE_API_KEY},
    )
    bundle_response = client.get(f"/agents/{chain.agent_id}/evidence-bundle")

    assert response.status_code == 201
    assert bundle_response.status_code == 200
    [resume_audit_log] = fetch_resume_audit_logs(session_factory)
    assert resume_audit_log.actor_type is ActorType.SERVICE
    assert resume_audit_log.actor_id == SERVICE_ACTOR_ID
    [resume_trace] = fetch_resume_trace_events(session_factory)
    assert SERVICE_API_KEY not in str(resume_trace.metadata_)
    assert SERVICE_API_KEY not in response.text
    assert SERVICE_API_KEY not in bundle_response.text
    assert SERVICE_API_KEY not in str(resume_audit_log.metadata_)
    assert SERVICE_API_KEY not in caplog.text


def test_runtime_resume_missing_key_when_service_auth_required_rejects_without_records(
    api_client: tuple[TestClient, SessionFactory],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, session_factory = api_client
    chain = create_review_chain(
        client,
        session_factory,
        approval_status=HumanApprovalStatus.APPROVED,
    )
    monkeypatch.setenv("AGCP_REQUIRE_SERVICE_AUTH", "true")
    get_settings.cache_clear()

    response = client.post(
        "/runtime/tool-calls/resume",
        json=runtime_resume_payload(chain),
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "AGCP service actor API key is required."
    assert fetch_resume_trace_events(session_factory) == []
    assert fetch_resume_audit_logs(session_factory) == []


def test_runtime_resume_service_key_without_resume_scope_rejects_without_records(
    api_client: tuple[TestClient, SessionFactory],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, session_factory = api_client
    chain = create_review_chain(
        client,
        session_factory,
        approval_status=HumanApprovalStatus.APPROVED,
    )
    configure_service_actor_api_key(
        monkeypatch,
        scopes=("runtime:decision",),
        require_auth=True,
    )

    response = client.post(
        "/runtime/tool-calls/resume",
        json=runtime_resume_payload(chain),
        headers={"X-AGCP-API-Key": SERVICE_API_KEY},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == (
        "Service actor requires scope: runtime:resume."
    )
    assert SERVICE_API_KEY not in response.text
    assert fetch_resume_trace_events(session_factory) == []
    assert fetch_resume_audit_logs(session_factory) == []


def test_runtime_resume_invalid_service_api_key_is_rejected_without_records(
    api_client: tuple[TestClient, SessionFactory],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, session_factory = api_client
    chain = create_review_chain(
        client,
        session_factory,
        approval_status=HumanApprovalStatus.APPROVED,
    )
    monkeypatch.setenv("AGCP_REQUIRE_SERVICE_AUTH", "true")
    get_settings.cache_clear()

    response = client.post(
        "/runtime/tool-calls/resume",
        json=runtime_resume_payload(chain),
        headers={"X-AGCP-API-Key": "invalid-local-test-key"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid AGCP service actor API key."
    assert fetch_resume_trace_events(session_factory) == []
    assert fetch_resume_audit_logs(session_factory) == []


@pytest.mark.parametrize(
    ("approval_status", "expected_decision", "expected_reason"),
    [
        (
            HumanApprovalStatus.PENDING,
            "require_human_review",
            "Human approval is still pending.",
        ),
        (
            HumanApprovalStatus.REJECTED,
            "deny",
            "Human approval was rejected.",
        ),
        (
            HumanApprovalStatus.CANCELLED,
            "deny",
            "Human approval was cancelled.",
        ),
        (
            HumanApprovalStatus.EXPIRED,
            "deny",
            "Human approval is expired.",
        ),
    ],
)
def test_runtime_resume_blocks_non_approved_approval_statuses(
    api_client: tuple[TestClient, SessionFactory],
    approval_status: HumanApprovalStatus,
    expected_decision: str,
    expected_reason: str,
) -> None:
    client, session_factory = api_client
    chain = create_review_chain(
        client,
        session_factory,
        approval_status=approval_status,
    )

    response = client.post(
        "/runtime/tool-calls/resume",
        json=runtime_resume_payload(chain),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["decision"] == expected_decision
    assert body["proceed"] is False
    assert body["reason"] == expected_reason
    assert body["human_approval_status"] == approval_status.value
    assert len(fetch_resume_trace_events(session_factory)) == 1
    assert len(fetch_resume_audit_logs(session_factory)) == 1


def test_runtime_resume_unknown_agent_returns_404_without_resume_records(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    chain = create_review_chain(client, session_factory)
    payload = runtime_resume_payload(chain)
    payload["agent_id"] = str(uuid4())

    response = client.post("/runtime/tool-calls/resume", json=payload)

    assert response.status_code == 404
    assert response.json()["detail"] == "Agent not found."
    assert fetch_resume_trace_events(session_factory) == []
    assert fetch_resume_audit_logs(session_factory) == []


def test_runtime_resume_unknown_human_approval_returns_404_without_resume_records(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    chain = create_review_chain(client, session_factory)
    payload = runtime_resume_payload(chain)
    payload["human_approval_id"] = str(uuid4())

    response = client.post("/runtime/tool-calls/resume", json=payload)

    assert response.status_code == 404
    assert response.json()["detail"] == "Human approval not found."
    assert fetch_resume_trace_events(session_factory) == []
    assert fetch_resume_audit_logs(session_factory) == []


def test_runtime_resume_unknown_policy_decision_returns_404_without_resume_records(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    chain = create_review_chain(client, session_factory)
    payload = runtime_resume_payload(chain)
    payload["policy_decision_id"] = str(uuid4())

    response = client.post("/runtime/tool-calls/resume", json=payload)

    assert response.status_code == 404
    assert response.json()["detail"] == "Policy decision not found."
    assert fetch_resume_trace_events(session_factory) == []
    assert fetch_resume_audit_logs(session_factory) == []


def test_runtime_resume_mismatched_agent_id_returns_conflict(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    chain = create_review_chain(client, session_factory)
    other_agent_id = create_agent(session_factory, name="Other assistant")
    payload = runtime_resume_payload(chain)
    payload["agent_id"] = str(other_agent_id)

    response = client.post("/runtime/tool-calls/resume", json=payload)

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Human approval does not belong to the requested agent."
    )
    assert fetch_resume_trace_events(session_factory) == []
    assert fetch_resume_audit_logs(session_factory) == []


def test_runtime_resume_mismatched_policy_decision_returns_conflict(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    chain = create_review_chain(client, session_factory)
    other_policy_decision_id = create_manual_policy_decision(
        session_factory,
        agent_id=chain.agent_id,
        trace_event_id=chain.trace_event_id,
    )
    payload = runtime_resume_payload(chain)
    payload["policy_decision_id"] = str(other_policy_decision_id)

    response = client.post("/runtime/tool-calls/resume", json=payload)

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Human approval is not linked to the requested policy decision."
    )
    assert fetch_resume_trace_events(session_factory) == []
    assert fetch_resume_audit_logs(session_factory) == []


def test_runtime_resume_mismatched_human_approval_returns_conflict(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    chain = create_review_chain(client, session_factory)
    other_chain = create_review_chain(
        client,
        session_factory,
        request_id="runtime-request-002",
    )
    payload = runtime_resume_payload(chain)
    payload["human_approval_id"] = str(other_chain.human_approval_id)

    response = client.post("/runtime/tool-calls/resume", json=payload)

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Human approval does not belong to the requested agent."
    )
    assert fetch_resume_trace_events(session_factory) == []
    assert fetch_resume_audit_logs(session_factory) == []


def test_runtime_resume_mismatched_tool_name_returns_conflict(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    chain = create_review_chain(client, session_factory)
    payload = runtime_resume_payload(chain, tool_name="send_payment")

    response = client.post("/runtime/tool-calls/resume", json=payload)

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Tool name does not match the original trace event."
    )
    assert fetch_resume_trace_events(session_factory) == []
    assert fetch_resume_audit_logs(session_factory) == []


def test_runtime_resume_mismatched_original_request_id_returns_conflict(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    chain = create_review_chain(client, session_factory)
    payload = runtime_resume_payload(chain, original_request_id="wrong-request-id")

    response = client.post("/runtime/tool-calls/resume", json=payload)

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Original request id does not match the original trace event."
    )
    assert fetch_resume_trace_events(session_factory) == []
    assert fetch_resume_audit_logs(session_factory) == []


def test_duplicate_runtime_resume_id_returns_existing_response_without_duplicates(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    chain = create_review_chain(
        client,
        session_factory,
        approval_status=HumanApprovalStatus.APPROVED,
    )

    first_response = client.post(
        "/runtime/tool-calls/resume",
        json=runtime_resume_payload(chain),
    )
    duplicate_payload = runtime_resume_payload(chain)
    duplicate_payload["metadata"] = {"resume_channel": "retry"}
    duplicate_response = client.post(
        "/runtime/tool-calls/resume",
        json=duplicate_payload,
    )

    assert first_response.status_code == 201
    assert duplicate_response.status_code == 200
    assert duplicate_response.json() == first_response.json()
    assert len(fetch_resume_trace_events(session_factory)) == 1
    assert len(fetch_resume_audit_logs(session_factory)) == 1


def test_runtime_resume_unsafe_metadata_is_rejected_without_resume_records(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    chain = create_review_chain(client, session_factory)
    payload = runtime_resume_payload(chain)
    payload["metadata"] = {"api_key": "redacted"}

    response = client.post("/runtime/tool-calls/resume", json=payload)

    assert response.status_code == 422
    assert fetch_resume_trace_events(session_factory) == []
    assert fetch_resume_audit_logs(session_factory) == []


def test_evidence_bundle_includes_runtime_resume_trace_and_audit(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    chain = create_review_chain(
        client,
        session_factory,
        approval_status=HumanApprovalStatus.APPROVED,
    )
    resume_response = client.post(
        "/runtime/tool-calls/resume",
        json=runtime_resume_payload(chain),
    )

    bundle_response = client.get(f"/agents/{chain.agent_id}/evidence-bundle")

    assert resume_response.status_code == 201
    assert bundle_response.status_code == 200
    resume_body = resume_response.json()
    bundle_body = bundle_response.json()
    resume_trace_events = [
        trace_event
        for trace_event in bundle_body["trace_events"]
        if trace_event["event_type"] == "tool_call_resume_requested"
    ]
    [resume_trace_event] = resume_trace_events
    assert resume_trace_event["id"] == resume_body["trace_event_id"]
    assert resume_trace_event["external_event_id"] == "runtime-request-001:resume:001"
    assert resume_trace_event["metadata"]["original_request_id"] == (
        "runtime-request-001"
    )
    assert resume_trace_event["metadata"]["human_approval_id"] == (
        str(chain.human_approval_id)
    )
    assert resume_trace_event["metadata"]["policy_decision_id"] == (
        str(chain.policy_decision_id)
    )

    resume_audit_logs = [
        audit_log
        for audit_log in bundle_body["audit_logs"]
        if audit_log["event_type"] == "runtime_tool_call_resume_checked"
    ]
    [resume_audit_log] = resume_audit_logs
    assert resume_audit_log["entity_type"] == "agent"
    assert resume_audit_log["entity_id"] == str(chain.agent_id)
    assert (
        resume_audit_log["metadata"]["trace_event_id"] == resume_body["trace_event_id"]
    )
    assert resume_audit_log["metadata"]["decision"] == "allow"


def create_review_chain(
    client: TestClient,
    session_factory: SessionFactory,
    *,
    approval_status: HumanApprovalStatus = HumanApprovalStatus.PENDING,
    request_id: str = "runtime-request-001",
) -> ReviewChain:
    agent_id = create_agent(session_factory, name=f"Support assistant {request_id}")
    create_policy_rule(
        session_factory,
        decision=PolicyDecisionValue.REQUIRE_HUMAN_REVIEW,
        reason="The requested tool requires human review.",
    )
    run_id = uuid4()
    response = client.post(
        "/runtime/tool-calls/decision",
        json=runtime_decision_payload(
            agent_id,
            run_id=run_id,
            request_id=request_id,
        ),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["decision"] == "require_human_review"
    assert body["human_approval_id"] is not None

    chain = ReviewChain(
        agent_id=agent_id,
        run_id=run_id,
        original_request_id=request_id,
        trace_event_id=UUID(body["trace_event_id"]),
        policy_decision_id=UUID(body["policy_decision_id"]),
        human_approval_id=UUID(body["human_approval_id"]),
    )
    set_approval_status(client, session_factory, chain, approval_status)

    return chain


def set_approval_status(
    client: TestClient,
    session_factory: SessionFactory,
    chain: ReviewChain,
    approval_status: HumanApprovalStatus,
) -> None:
    if approval_status is HumanApprovalStatus.PENDING:
        return
    if approval_status is HumanApprovalStatus.APPROVED:
        response = client.post(
            f"/human-approvals/{chain.human_approval_id}/approve",
            json={"decision_note": "Approved for resume test."},
        )
        assert response.status_code == 200
        return
    if approval_status is HumanApprovalStatus.REJECTED:
        response = client.post(
            f"/human-approvals/{chain.human_approval_id}/reject",
            json={"decision_note": "Rejected for resume test."},
        )
        assert response.status_code == 200
        return
    if approval_status is HumanApprovalStatus.CANCELLED:
        response = client.post(f"/human-approvals/{chain.human_approval_id}/cancel")
        assert response.status_code == 200
        return

    with session_factory() as session:
        approval = session.get(HumanApproval, chain.human_approval_id)
        assert approval is not None
        approval.status = HumanApprovalStatus.EXPIRED
        session.commit()


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


def create_manual_policy_decision(
    session_factory: SessionFactory,
    *,
    agent_id: UUID,
    trace_event_id: UUID,
) -> UUID:
    with session_factory() as session:
        decision = PolicyDecision(
            agent_id=agent_id,
            decision=PolicyDecisionValue.DENY,
            reason="Manual mismatch decision.",
            trace_event_id=trace_event_id,
        )
        session.add(decision)
        session.commit()
        return decision.id


def runtime_decision_payload(
    agent_id: UUID,
    *,
    run_id: UUID,
    request_id: str = "runtime-request-001",
) -> dict[str, object]:
    return {
        "request_id": request_id,
        "agent_id": str(agent_id),
        "run_id": str(run_id),
        "correlation_id": "support-run-001",
        "tool_name": "send_email",
        "action_summary": "Send a support follow-up email.",
        "metadata": {"ticket_category": "support"},
        "mode": "simulation",
    }


def runtime_resume_payload(
    chain: ReviewChain,
    *,
    resume_id: str = "runtime-request-001:resume:001",
    tool_name: str = "send_email",
    original_request_id: str | None = None,
) -> dict[str, object]:
    return {
        "resume_id": resume_id,
        "original_request_id": original_request_id or chain.original_request_id,
        "agent_id": str(chain.agent_id),
        "run_id": str(chain.run_id),
        "tool_name": tool_name,
        "human_approval_id": str(chain.human_approval_id),
        "policy_decision_id": str(chain.policy_decision_id),
        "action_ref": "support-ticket-123:follow-up-email",
        "correlation_id": "support-run-001",
        "metadata": {"resume_channel": "polling"},
    }


def configure_service_actor_api_key(
    monkeypatch: pytest.MonkeyPatch,
    *,
    scopes: tuple[str, ...] = ("runtime:resume",),
    require_auth: bool = False,
) -> None:
    monkeypatch.setenv(
        "AGCP_SERVICE_ACTOR_API_KEYS",
        f"{SERVICE_ACTOR_ID}={hash_service_actor_api_key(SERVICE_API_KEY)}",
    )
    monkeypatch.setenv(
        "AGCP_SERVICE_ACTOR_SCOPES",
        f"{SERVICE_ACTOR_ID}={','.join(scopes)}",
    )
    if require_auth:
        monkeypatch.setenv("AGCP_REQUIRE_SERVICE_AUTH", "true")
    get_settings.cache_clear()


def fetch_trace_events(session_factory: SessionFactory) -> list[TraceEventRecord]:
    with session_factory() as session:
        return list(session.scalars(select(TraceEventRecord)).all())


def fetch_resume_trace_events(
    session_factory: SessionFactory,
) -> list[TraceEventRecord]:
    return [
        trace_event
        for trace_event in fetch_trace_events(session_factory)
        if trace_event.event_type is TraceEventType.TOOL_CALL_RESUME_REQUESTED
    ]


def resume_trace_event(session_factory: SessionFactory) -> TraceEventRecord:
    [trace_event] = fetch_resume_trace_events(session_factory)
    return trace_event


def fetch_resume_audit_logs(session_factory: SessionFactory) -> list[AuditLog]:
    with session_factory() as session:
        statement = (
            select(AuditLog)
            .where(AuditLog.event_type == "runtime_tool_call_resume_checked")
            .order_by(AuditLog.created_at, AuditLog.id)
        )
        return list(session.scalars(statement).all())
