import json
from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy import event as sqlalchemy_event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from agent_governance_api.auth import ActorContext, get_current_actor
from agent_governance_api.database import Base, get_db_session
from agent_governance_api.main import app
from agent_governance_api.models import (
    ActorType,
    Agent,
    AgentRunRecord,
    AgentStatus,
    Environment,
    HumanApproval,
    HumanApprovalStatus,
    OwnerType,
    Policy,
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
    app.dependency_overrides[get_current_actor] = lambda: auditor_actor()
    try:
        with TestClient(app) as client:
            yield client, testing_session_factory
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_runtime_activity_returns_empty_list(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, _ = api_client

    response = client.get("/runtime/tool-calls/activity")

    assert response.status_code == 200
    assert response.json() == []


def test_runtime_decision_activity_appears_after_decision_request(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    create_policy_rule(
        session_factory,
        decision=PolicyDecisionValue.ALLOW,
        reason="The requested tool is allowed.",
    )
    run_id = uuid4()

    decision_response = client.post(
        "/runtime/tool-calls/decision",
        json=runtime_decision_payload(agent_id, run_id=run_id),
    )
    activity_response = client.get("/runtime/tool-calls/activity")

    assert decision_response.status_code == 201
    decision_body = decision_response.json()
    assert activity_response.status_code == 200
    [activity] = activity_response.json()
    assert activity["type"] == "tool_call_decision"
    assert activity["agent_id"] == str(agent_id)
    assert activity["run_id"] == str(run_id)
    assert activity["request_id"] == "runtime-request-001"
    assert activity["tool_name"] == "send_email"
    assert activity["mode"] == "simulation"
    assert activity["decision"] == "allow"
    assert activity["proceed"] is True
    assert activity["reason"] == "The requested tool is allowed."
    assert activity["trace_event_id"] == decision_body["trace_event_id"]
    assert activity["policy_decision_id"] == decision_body["policy_decision_id"]
    assert activity["human_approval_id"] is None
    assert activity["related_ids"] == {
        "trace_event_id": decision_body["trace_event_id"],
        "policy_decision_id": decision_body["policy_decision_id"],
        "run_id": str(run_id),
    }


def test_runtime_review_decision_activity_links_to_human_approval(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    create_policy_rule(
        session_factory,
        decision=PolicyDecisionValue.REQUIRE_HUMAN_REVIEW,
        reason="The requested tool requires human review.",
    )

    decision_response = client.post(
        "/runtime/tool-calls/decision",
        json=runtime_decision_payload(agent_id),
    )
    activity_response = client.get("/runtime/tool-calls/activity")

    assert decision_response.status_code == 201
    decision_body = decision_response.json()
    assert decision_body["decision"] == "require_human_review"
    assert activity_response.status_code == 200
    [activity] = activity_response.json()
    assert activity["decision"] == "require_human_review"
    assert activity["proceed"] is False
    assert activity["human_approval_id"] == decision_body["human_approval_id"]
    assert (
        activity["related_ids"]["human_approval_id"]
        == (decision_body["human_approval_id"])
    )


def test_runtime_resume_activity_is_represented_when_records_exist(
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
    activity_response = client.get("/runtime/tool-calls/activity")

    assert resume_response.status_code == 201
    resume_body = resume_response.json()
    assert activity_response.status_code == 200
    resume_activity = next(
        item for item in activity_response.json() if item["type"] == "tool_call_resume"
    )
    assert resume_activity["request_id"] == "runtime-request-001:resume:001"
    assert resume_activity["agent_id"] == str(chain.agent_id)
    assert resume_activity["run_id"] == str(chain.run_id)
    assert resume_activity["tool_name"] == "send_email"
    assert resume_activity["mode"] is None
    assert resume_activity["decision"] == "allow"
    assert resume_activity["proceed"] is True
    assert resume_activity["reason"] == (
        "Human approval is approved and the resume context matches."
    )
    assert resume_activity["trace_event_id"] == resume_body["trace_event_id"]
    assert resume_activity["policy_decision_id"] == str(chain.policy_decision_id)
    assert resume_activity["human_approval_id"] == str(chain.human_approval_id)
    assert resume_activity["related_ids"] == {
        "trace_event_id": resume_body["trace_event_id"],
        "policy_decision_id": str(chain.policy_decision_id),
        "human_approval_id": str(chain.human_approval_id),
        "run_id": str(chain.run_id),
        "original_request_id": "runtime-request-001",
    }


def test_runtime_activity_does_not_expose_unsafe_metadata(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    create_policy_rule(
        session_factory,
        decision=PolicyDecisionValue.ALLOW,
        reason="The requested tool is allowed.",
    )
    decision_response = client.post(
        "/runtime/tool-calls/decision",
        json=runtime_decision_payload(agent_id),
    )
    assert decision_response.status_code == 201
    inject_unsafe_trace_metadata(session_factory, "runtime-request-001")

    response = client.get("/runtime/tool-calls/activity")

    assert response.status_code == 200
    [activity] = response.json()
    assert "metadata" not in activity
    assert activity["tool_name"] == "send_email"
    response_text = response.text
    assert "do-not-export" not in response_text
    assert "raw_payload" not in response_text
    assert "private_customer_data" not in response_text
    assert "token" not in response_text


def test_runtime_activity_includes_tool_call_records_with_unknown_mode_as_null(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    seed_telemetry_tool_call_trace(session_factory, agent_id)

    response = client.get("/runtime/tool-calls/activity")

    assert response.status_code == 200
    [activity] = response.json()
    assert activity["type"] == "tool_call_decision"
    assert activity["agent_id"] == str(agent_id)
    assert activity["request_id"] == "telemetry-event-001"
    assert activity["tool_name"] == "send_email"
    assert activity["mode"] is None
    assert activity["decision"] is None
    assert activity["proceed"] is None
    assert activity["reason"] is None


def test_runtime_activity_orders_newest_first(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    create_policy_rule(
        session_factory,
        decision=PolicyDecisionValue.ALLOW,
        reason="The requested tool is allowed.",
    )
    first_run_id = uuid4()
    second_run_id = uuid4()
    first_response = client.post(
        "/runtime/tool-calls/decision",
        json=runtime_decision_payload(
            agent_id,
            run_id=first_run_id,
            request_id="runtime-request-001",
        ),
    )
    second_response = client.post(
        "/runtime/tool-calls/decision",
        json=runtime_decision_payload(
            agent_id,
            run_id=second_run_id,
            request_id="runtime-request-002",
        ),
    )
    assert first_response.status_code == 201
    assert second_response.status_code == 201
    set_trace_timestamp(
        session_factory,
        request_id="runtime-request-001",
        timestamp=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
    )
    set_trace_timestamp(
        session_factory,
        request_id="runtime-request-002",
        timestamp=datetime(2026, 1, 1, 12, 5, tzinfo=UTC),
    )

    response = client.get("/runtime/tool-calls/activity")

    assert response.status_code == 200
    request_ids = [item["request_id"] for item in response.json()]
    assert request_ids == ["runtime-request-002", "runtime-request-001"]


class ReviewChain:
    def __init__(
        self,
        *,
        agent_id: UUID,
        run_id: UUID,
        policy_decision_id: UUID,
        human_approval_id: UUID,
    ) -> None:
        self.agent_id = agent_id
        self.run_id = run_id
        self.policy_decision_id = policy_decision_id
        self.human_approval_id = human_approval_id


def create_review_chain(
    client: TestClient,
    session_factory: SessionFactory,
    *,
    approval_status: HumanApprovalStatus = HumanApprovalStatus.PENDING,
) -> ReviewChain:
    agent_id = create_agent(session_factory)
    create_policy_rule(
        session_factory,
        decision=PolicyDecisionValue.REQUIRE_HUMAN_REVIEW,
        reason="The requested tool requires human review.",
    )
    run_id = uuid4()
    response = client.post(
        "/runtime/tool-calls/decision",
        json=runtime_decision_payload(agent_id, run_id=run_id),
    )
    assert response.status_code == 201
    body = response.json()
    chain = ReviewChain(
        agent_id=agent_id,
        run_id=run_id,
        policy_decision_id=UUID(body["policy_decision_id"]),
        human_approval_id=UUID(body["human_approval_id"]),
    )
    set_approval_status(session_factory, chain.human_approval_id, approval_status)
    return chain


def set_approval_status(
    session_factory: SessionFactory,
    approval_id: UUID,
    approval_status: HumanApprovalStatus,
) -> None:
    if approval_status is HumanApprovalStatus.PENDING:
        return

    with session_factory() as session:
        approval = session.get(HumanApproval, approval_id)
        assert approval is not None
        approval.status = approval_status
        approval.reviewed_by_actor_type = ActorType.USER
        approval.reviewed_by_actor_id = "user:runtime-activity-reviewer"
        approval.reviewed_at = datetime(2026, 1, 1, 12, 30, tzinfo=UTC)
        session.commit()


def create_agent(session_factory: SessionFactory) -> UUID:
    with session_factory() as session:
        agent = Agent(
            name="Support assistant",
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


def runtime_decision_payload(
    agent_id: UUID,
    *,
    run_id: UUID | None = None,
    request_id: str = "runtime-request-001",
) -> dict[str, object]:
    return {
        "request_id": request_id,
        "agent_id": str(agent_id),
        "run_id": str(run_id or uuid4()),
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
) -> dict[str, object]:
    return {
        "resume_id": resume_id,
        "original_request_id": "runtime-request-001",
        "agent_id": str(chain.agent_id),
        "run_id": str(chain.run_id),
        "tool_name": "send_email",
        "human_approval_id": str(chain.human_approval_id),
        "policy_decision_id": str(chain.policy_decision_id),
        "action_ref": "support-ticket-123:follow-up-email",
        "correlation_id": "support-run-001",
        "metadata": {"resume_channel": "polling"},
    }


def inject_unsafe_trace_metadata(
    session_factory: SessionFactory,
    request_id: str,
) -> None:
    with session_factory() as session:
        session.execute(
            TraceEventRecord.__table__.update()
            .where(TraceEventRecord.external_event_id == request_id)
            .values(
                {
                    "metadata": {
                        "tool_name": "send_email",
                        "raw_payload": "do-not-export",
                        "private_customer_data": "do-not-export",
                        "token": "do-not-export",
                    }
                }
            )
        )
        session.commit()


def seed_telemetry_tool_call_trace(
    session_factory: SessionFactory,
    agent_id: UUID,
) -> None:
    with session_factory() as session:
        now = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
        run_id = uuid4()
        session.add(
            AgentRunRecord(
                agent_id=agent_id,
                run_id=run_id,
                correlation_id="telemetry-correlation",
                environment=Environment.DEVELOPMENT,
                status="observed",
                started_at=now,
                summary="Telemetry run observed.",
                metadata_={},
                created_at=now,
            )
        )
        session.flush()
        session.add(
            TraceEventRecord(
                agent_id=agent_id,
                run_id=run_id,
                external_event_id="telemetry-event-001",
                correlation_id="telemetry-correlation",
                event_type=TraceEventType.TOOL_CALL_REQUESTED,
                timestamp=now,
                summary="Telemetry tool call requested.",
                metadata_={"tool_name": "send_email"},
                created_at=now,
            )
        )
        session.commit()


def set_trace_timestamp(
    session_factory: SessionFactory,
    *,
    request_id: str,
    timestamp: datetime,
) -> None:
    with session_factory() as session:
        session.execute(
            TraceEventRecord.__table__.update()
            .where(TraceEventRecord.external_event_id == request_id)
            .values({"timestamp": timestamp})
        )
        session.commit()


def auditor_actor() -> ActorContext:
    return ActorContext(
        actor_type=ActorType.USER,
        actor_id="user:runtime-activity-auditor",
        roles=("auditor",),
    )
