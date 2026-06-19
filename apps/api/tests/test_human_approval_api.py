from collections.abc import Callable, Iterator
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, update
from sqlalchemy import event as sqlalchemy_event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from agent_governance_api.auth import ActorContext, get_current_actor
from agent_governance_api.database import Base, get_db_session
from agent_governance_api.main import app
from agent_governance_api.models import (
    ActorType,
    Agent,
    AgentStatus,
    AuditLog,
    CheckResult,
    CheckResultConfidence,
    CheckResultOutcome,
    CheckResultTargetType,
    CheckTool,
    CheckToolStatus,
    CheckToolType,
    Environment,
    HumanApproval,
    HumanApprovalStatus,
    OwnerType,
    PolicyDecision,
    PolicyDecisionValue,
    RiskLevel,
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
    try:
        with TestClient(app) as client:
            yield client, testing_session_factory
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_create_pending_human_approval(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)

    response = client.post(
        "/human-approvals",
        json={
            "agent_id": str(agent_id),
            "reason": "High-risk action requires review.",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert UUID(body["id"])
    assert body["agent_id"] == str(agent_id)
    assert body["policy_decision_id"] is None
    assert body["status"] == "pending"
    assert body["requested_by_actor_type"] == "development"
    assert body["requested_by_actor_id"] == "dev-placeholder"
    assert body["reviewed_by_actor_type"] is None
    assert body["reviewed_by_actor_id"] is None
    assert body["reviewed_at"] is None
    assert body["reason"] == "High-risk action requires review."


def test_create_human_approval_with_policy_decision(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    policy_decision_id = create_policy_decision(session_factory, agent_id)

    response = client.post(
        "/human-approvals",
        json={
            "agent_id": str(agent_id),
            "policy_decision_id": str(policy_decision_id),
        },
    )

    assert response.status_code == 201
    assert response.json()["policy_decision_id"] == str(policy_decision_id)


def test_create_human_approval_with_mismatched_policy_decision_fails(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    approval_agent_id = create_agent(session_factory, name="Support assistant")
    decision_agent_id = create_agent(session_factory, name="Risk review assistant")
    policy_decision_id = create_policy_decision(session_factory, decision_agent_id)

    response = client.post(
        "/human-approvals",
        json={
            "agent_id": str(approval_agent_id),
            "policy_decision_id": str(policy_decision_id),
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Policy decision does not belong to the requested agent."
    )
    assert fetch_all_human_approval_audit_logs(session_factory) == []


def test_get_human_approval(api_client: tuple[TestClient, SessionFactory]) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    approval_id = create_human_approval(client, agent_id)

    response = client.get(f"/human-approvals/{approval_id}")

    assert response.status_code == 200
    assert response.json()["id"] == str(approval_id)
    assert response.json()["agent_id"] == str(agent_id)


def test_list_human_approvals_for_agent(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory, name="Support assistant")
    other_agent_id = create_agent(session_factory, name="Risk review assistant")
    first_approval_id = create_human_approval(client, agent_id)
    second_approval_id = create_human_approval(client, agent_id)
    create_human_approval(client, other_agent_id)

    response = client.get(f"/agents/{agent_id}/human-approvals")

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [
        str(first_approval_id),
        str(second_approval_id),
    ]


def test_platform_admin_can_list_human_approvals(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    approval_id = create_human_approval(client, agent_id)
    set_current_actor(
        ActorContext(
            actor_type=ActorType.USER,
            actor_id="user:platform-admin",
            roles=("platform_admin",),
        )
    )

    response = client.get("/human-approvals")

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [str(approval_id)]


@pytest.mark.parametrize("role", ["reviewer", "auditor"])
def test_reviewer_and_auditor_can_list_human_approvals(
    api_client: tuple[TestClient, SessionFactory],
    role: str,
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    approval_id = create_human_approval(client, agent_id)
    set_current_actor(
        ActorContext(
            actor_type=ActorType.USER,
            actor_id=f"user:{role}-1",
            roles=(role,),
        )
    )

    response = client.get("/human-approvals")

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [str(approval_id)]


def test_list_human_approvals_includes_safe_metadata_check_results(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    policy_decision_id = create_policy_decision(session_factory, agent_id)
    approval_id = insert_human_approval(
        session_factory,
        agent_id,
        policy_decision_id=policy_decision_id,
    )
    seed_policy_decision_check_result(
        session_factory,
        agent_id=agent_id,
        policy_decision_id=policy_decision_id,
    )
    set_current_actor(auditor_actor())

    response = client.get("/human-approvals")

    assert response.status_code == 200
    [approval] = response.json()
    assert approval["id"] == str(approval_id)
    [check_result] = approval["check_results"]
    assert check_result["check_type"] == "source_classification"
    assert check_result["outcome"] == "pass"
    assert check_result["confidence"] == "high"
    assert check_result["target_type"] == "source"
    assert check_result["target_id"] is not None
    assert check_result["policy_decision_id"] == str(policy_decision_id)
    assert check_result["created_at"]
    assert check_result["metadata"] == {
        "policy_check_step_check_type": "source_classification",
        "data_classification": "restricted",
    }
    assert "raw_content" not in response.text
    assert "prompt" not in response.text
    assert "api_key" not in response.text
    assert "do-not-export" not in response.text


def test_actor_without_read_role_cannot_list_human_approvals(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    create_human_approval(client, agent_id)
    set_current_actor(
        ActorContext(
            actor_type=ActorType.USER,
            actor_id="user:viewer-1",
            roles=("viewer",),
        )
    )

    response = client.get("/human-approvals")

    assert response.status_code == 403
    assert response.json()["detail"] == (
        "Actor requires one of these roles: reviewer, auditor, platform_admin."
    )


def test_service_actor_cannot_list_human_approvals_by_default(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    create_human_approval(client, agent_id)
    set_current_actor(
        ActorContext(
            actor_type=ActorType.SERVICE,
            actor_id="service:runtime-adapter",
            roles=("reviewer", "auditor", "platform_admin"),
        )
    )

    response = client.get("/human-approvals")

    assert response.status_code == 403
    assert response.json()["detail"] == "Service actors cannot list human approvals."


def test_list_human_approvals_filters_by_status(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    approved_id = insert_human_approval(
        session_factory,
        agent_id,
        status=HumanApprovalStatus.APPROVED,
    )
    insert_human_approval(
        session_factory,
        agent_id,
        status=HumanApprovalStatus.PENDING,
    )
    set_current_actor(auditor_actor())

    response = client.get("/human-approvals", params={"status": "approved"})

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [str(approved_id)]
    assert all(item["status"] == "approved" for item in response.json())


def test_list_human_approvals_filters_by_agent_id(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory, name="Support assistant")
    other_agent_id = create_agent(session_factory, name="Risk review assistant")
    approval_id = insert_human_approval(session_factory, agent_id)
    insert_human_approval(session_factory, other_agent_id)
    set_current_actor(auditor_actor())

    response = client.get("/human-approvals", params={"agent_id": str(agent_id)})

    assert response.status_code == 200
    body = response.json()
    assert [item["id"] for item in body] == [str(approval_id)]
    assert body[0]["agent_id"] == str(agent_id)


def test_list_human_approvals_filters_by_policy_decision_id(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    policy_decision_id = create_policy_decision(session_factory, agent_id)
    other_policy_decision_id = create_policy_decision(session_factory, agent_id)
    approval_id = insert_human_approval(
        session_factory,
        agent_id,
        policy_decision_id=policy_decision_id,
    )
    insert_human_approval(
        session_factory,
        agent_id,
        policy_decision_id=other_policy_decision_id,
    )
    set_current_actor(auditor_actor())

    response = client.get(
        "/human-approvals",
        params={"policy_decision_id": str(policy_decision_id)},
    )

    assert response.status_code == 200
    body = response.json()
    assert [item["id"] for item in body] == [str(approval_id)]
    assert body[0]["policy_decision_id"] == str(policy_decision_id)


def test_list_human_approvals_orders_newest_first(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    base_time = datetime(2026, 1, 1, tzinfo=UTC)
    oldest_id = insert_human_approval(
        session_factory,
        agent_id,
        created_at=base_time,
    )
    newest_id = insert_human_approval(
        session_factory,
        agent_id,
        created_at=base_time + timedelta(minutes=2),
    )
    middle_id = insert_human_approval(
        session_factory,
        agent_id,
        created_at=base_time + timedelta(minutes=1),
    )
    set_current_actor(auditor_actor())

    response = client.get("/human-approvals")

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [
        str(newest_id),
        str(middle_id),
        str(oldest_id),
    ]


def test_list_human_approvals_returns_empty_list(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, _ = api_client
    set_current_actor(auditor_actor())

    response = client.get("/human-approvals")

    assert response.status_code == 200
    assert response.json() == []


def test_approve_pending_human_approval(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    approval_id = create_human_approval(client, agent_id)
    set_current_actor(
        ActorContext(
            actor_type=ActorType.USER,
            actor_id="user:reviewer-1",
            roles=("reviewer",),
        )
    )

    response = client.post(
        f"/human-approvals/{approval_id}/approve",
        json={"decision_note": "Approved for this governed action."},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "approved"
    assert body["reviewed_by_actor_type"] == "user"
    assert body["reviewed_by_actor_id"] == "user:reviewer-1"
    assert body["reviewed_at"] is not None
    assert body["decision_note"] == "Approved for this governed action."


def test_reject_pending_human_approval(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    approval_id = create_human_approval(client, agent_id)
    set_current_actor(
        ActorContext(
            actor_type=ActorType.USER,
            actor_id="user:reviewer-1",
            roles=("reviewer",),
        )
    )

    response = client.post(
        f"/human-approvals/{approval_id}/reject",
        json={
            "reason": "The requested tool is too broad.",
            "decision_note": "Rejected pending narrower scope.",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "rejected"
    assert body["reviewed_by_actor_type"] == "user"
    assert body["reviewed_by_actor_id"] == "user:reviewer-1"
    assert body["reviewed_at"] is not None
    assert body["reason"] == "The requested tool is too broad."
    assert body["decision_note"] == "Rejected pending narrower scope."


def test_cancel_pending_human_approval(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    set_current_actor(
        ActorContext(
            actor_type=ActorType.USER,
            actor_id="user:requester-1",
            roles=(),
        )
    )
    approval_id = create_human_approval(client, agent_id)

    response = client.post(f"/human-approvals/{approval_id}/cancel")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "cancelled"
    assert body["reviewed_by_actor_type"] is None
    assert body["reviewed_by_actor_id"] is None
    assert body["reviewed_at"] is None


def test_approve_already_approved_human_approval_is_rejected(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    approval_id = create_human_approval(client, agent_id)
    set_current_actor(
        ActorContext(
            actor_type=ActorType.USER,
            actor_id="user:reviewer-1",
            roles=("reviewer",),
        )
    )
    first_response = client.post(f"/human-approvals/{approval_id}/approve", json={})

    second_response = client.post(f"/human-approvals/{approval_id}/approve", json={})

    assert first_response.status_code == 200
    assert second_response.status_code == 409
    assert second_response.json()["detail"] == (
        "Only pending human approvals can transition."
    )


def test_create_human_approval_unknown_agent_returns_404(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, _ = api_client

    response = client.post(
        "/human-approvals",
        json={"agent_id": "00000000-0000-0000-0000-000000000001"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Agent not found."


def test_create_human_approval_unknown_policy_decision_returns_404(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)

    response = client.post(
        "/human-approvals",
        json={
            "agent_id": str(agent_id),
            "policy_decision_id": "00000000-0000-0000-0000-000000000001",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Policy decision not found."


@pytest.mark.parametrize("transition_path", ["approve", "reject"])
def test_actor_without_reviewer_or_platform_admin_cannot_approve_or_reject(
    api_client: tuple[TestClient, SessionFactory],
    transition_path: str,
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    approval_id = create_human_approval(client, agent_id)
    set_current_actor(
        ActorContext(
            actor_type=ActorType.USER,
            actor_id="user:viewer-1",
            roles=("viewer",),
        )
    )

    response = client.post(f"/human-approvals/{approval_id}/{transition_path}", json={})

    assert response.status_code == 403
    assert response.json()["detail"] == (
        "Actor requires one of these roles: reviewer, platform_admin."
    )
    assert_human_approval_status(
        session_factory,
        approval_id,
        HumanApprovalStatus.PENDING,
    )
    assert [
        log.event_type
        for log in fetch_human_approval_audit_logs(
            session_factory,
            approval_id,
        )
    ] == ["human_approval_requested"]


@pytest.mark.parametrize("transition_path", ["approve", "reject"])
def test_service_actor_cannot_approve_or_reject_by_default(
    api_client: tuple[TestClient, SessionFactory],
    transition_path: str,
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    approval_id = create_human_approval(client, agent_id)
    set_current_actor(
        ActorContext(
            actor_type=ActorType.SERVICE,
            actor_id="service:runtime-adapter",
            roles=("reviewer",),
        )
    )

    response = client.post(f"/human-approvals/{approval_id}/{transition_path}", json={})

    assert response.status_code == 403
    assert response.json()["detail"] == "Service actors cannot review human approvals."
    assert_human_approval_status(
        session_factory,
        approval_id,
        HumanApprovalStatus.PENDING,
    )


@pytest.mark.parametrize("transition_path", ["approve", "reject"])
def test_requester_self_approval_is_denied(
    api_client: tuple[TestClient, SessionFactory],
    transition_path: str,
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    requester = ActorContext(
        actor_type=ActorType.USER,
        actor_id="user:requester-reviewer",
        roles=("reviewer",),
    )
    set_current_actor(requester)
    approval_id = create_human_approval(client, agent_id)

    response = client.post(f"/human-approvals/{approval_id}/{transition_path}", json={})

    assert response.status_code == 403
    assert response.json()["detail"] == (
        "Requester cannot approve or reject their own human approval."
    )
    assert_human_approval_status(
        session_factory,
        approval_id,
        HumanApprovalStatus.PENDING,
    )


def test_platform_admin_can_approve_even_if_requester(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    admin = ActorContext(
        actor_type=ActorType.USER,
        actor_id="user:platform-admin",
        roles=("platform_admin",),
    )
    set_current_actor(admin)
    approval_id = create_human_approval(client, agent_id)

    response = client.post(f"/human-approvals/{approval_id}/approve", json={})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "approved"
    assert body["reviewed_by_actor_type"] == "user"
    assert body["reviewed_by_actor_id"] == "user:platform-admin"


def test_unrelated_actor_cannot_cancel_human_approval(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    set_current_actor(
        ActorContext(
            actor_type=ActorType.USER,
            actor_id="user:requester-1",
            roles=(),
        )
    )
    approval_id = create_human_approval(client, agent_id)
    set_current_actor(
        ActorContext(
            actor_type=ActorType.USER,
            actor_id="user:unrelated-1",
            roles=("reviewer",),
        )
    )

    response = client.post(f"/human-approvals/{approval_id}/cancel")

    assert response.status_code == 403
    assert response.json()["detail"] == (
        "Human approval cancellation requires platform_admin or requester."
    )
    assert_human_approval_status(
        session_factory,
        approval_id,
        HumanApprovalStatus.PENDING,
    )
    assert [
        log.event_type
        for log in fetch_human_approval_audit_logs(
            session_factory,
            approval_id,
        )
    ] == ["human_approval_requested"]


def test_platform_admin_can_cancel_human_approval(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    approval_id = create_human_approval(client, agent_id)
    set_current_actor(
        ActorContext(
            actor_type=ActorType.USER,
            actor_id="user:platform-admin",
            roles=("platform_admin",),
        )
    )

    response = client.post(f"/human-approvals/{approval_id}/cancel")

    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"


@pytest.mark.parametrize(
    ("transition_path", "event_type"),
    [
        ("approve", "human_approval_approved"),
        ("reject", "human_approval_rejected"),
        ("cancel", "human_approval_cancelled"),
    ],
)
def test_human_approval_transition_audit_logs_are_created(
    api_client: tuple[TestClient, SessionFactory],
    transition_path: str,
    event_type: str,
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    approval_id = create_human_approval(client, agent_id)
    expected_actor_type = ActorType.DEVELOPMENT
    expected_actor_id = "dev-placeholder"
    if transition_path in {"approve", "reject"}:
        expected_actor_type = ActorType.USER
        expected_actor_id = "user:reviewer-1"
        set_current_actor(
            ActorContext(
                actor_type=expected_actor_type,
                actor_id=expected_actor_id,
                roles=("reviewer",),
            )
        )

    response = client.post(f"/human-approvals/{approval_id}/{transition_path}", json={})

    assert response.status_code == 200
    audit_logs = fetch_human_approval_audit_logs(session_factory, approval_id)
    assert [log.event_type for log in audit_logs] == [
        "human_approval_requested",
        event_type,
    ]
    transition_log = audit_logs[-1]
    assert transition_log.actor_type is expected_actor_type
    assert transition_log.actor_id == expected_actor_id
    assert transition_log.entity_type == "human_approval"
    assert transition_log.entity_id == str(approval_id)
    assert transition_log.metadata_["agent_id"] == str(agent_id)


def test_human_approval_create_audit_log_is_created(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)

    approval_id = create_human_approval(client, agent_id)

    [audit_log] = fetch_human_approval_audit_logs(session_factory, approval_id)
    assert audit_log.event_type == "human_approval_requested"
    assert audit_log.actor_type is ActorType.DEVELOPMENT
    assert audit_log.actor_id == "dev-placeholder"
    assert audit_log.entity_type == "human_approval"
    assert audit_log.entity_id == str(approval_id)
    assert audit_log.metadata_ == {
        "agent_id": str(agent_id),
        "status": "pending",
    }


def test_human_approval_api_exposes_no_generic_update_or_delete_routes() -> None:
    forbidden_routes = [
        (route.path, sorted(route.methods))
        for route in app.routes
        if getattr(route, "path", "").startswith("/human-approvals")
        and ({"PATCH", "PUT", "DELETE"} & set(getattr(route, "methods", set())))
    ]

    assert forbidden_routes == []


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


def create_policy_decision(session_factory: SessionFactory, agent_id: UUID) -> UUID:
    with session_factory() as session:
        policy_decision = PolicyDecision(
            agent_id=agent_id,
            decision=PolicyDecisionValue.REQUIRE_HUMAN_REVIEW,
            reason="The requested action requires review.",
        )
        session.add(policy_decision)
        session.commit()
        return policy_decision.id


def seed_policy_decision_check_result(
    session_factory: SessionFactory,
    *,
    agent_id: UUID,
    policy_decision_id: UUID,
) -> None:
    with session_factory() as session:
        check_tool = CheckTool(
            name="source_classification_checker",
            description="Metadata-only source classification check.",
            tool_type=CheckToolType.METADATA_LOOKUP,
            status=CheckToolStatus.ACTIVE,
            owner_type=OwnerType.TEAM,
            owner_id="team:governance",
            owner_name="Governance",
            metadata_={},
        )
        session.add(check_tool)
        session.flush()
        check_result = CheckResult(
            check_tool_id=check_tool.id,
            agent_id=agent_id,
            policy_decision_id=policy_decision_id,
            target_type=CheckResultTargetType.SOURCE,
            target_id=agent_id,
            outcome=CheckResultOutcome.PASS,
            confidence=CheckResultConfidence.HIGH,
            summary="Source classification metadata is available.",
            reason="The Source Data Usage Profile declares restricted data.",
            metadata_={
                "policy_check_step_check_type": "source_classification",
                "data_classification": "restricted",
            },
        )
        session.add(check_result)
        session.flush()
        session.execute(
            update(CheckResult.__table__)
            .where(CheckResult.__table__.c.id == check_result.id)
            .values(
                metadata={
                    "policy_check_step_check_type": "source_classification",
                    "data_classification": "restricted",
                    "raw_content": "do-not-export",
                    "prompt": "do-not-export",
                    "api_key": "do-not-export",
                },
            )
        )
        session.commit()


def create_human_approval(client: TestClient, agent_id: UUID) -> UUID:
    response = client.post("/human-approvals", json={"agent_id": str(agent_id)})

    assert response.status_code == 201
    return UUID(response.json()["id"])


def insert_human_approval(
    session_factory: SessionFactory,
    agent_id: UUID,
    *,
    status: HumanApprovalStatus = HumanApprovalStatus.PENDING,
    policy_decision_id: UUID | None = None,
    created_at: datetime | None = None,
) -> UUID:
    with session_factory() as session:
        approval = HumanApproval(
            agent_id=agent_id,
            policy_decision_id=policy_decision_id,
            status=status,
            requested_by_actor_type=ActorType.DEVELOPMENT,
            requested_by_actor_id="dev-placeholder",
            reviewed_by_actor_type=(
                ActorType.USER
                if status
                in {
                    HumanApprovalStatus.APPROVED,
                    HumanApprovalStatus.REJECTED,
                }
                else None
            ),
            reviewed_by_actor_id=(
                "user:reviewer-1"
                if status
                in {
                    HumanApprovalStatus.APPROVED,
                    HumanApprovalStatus.REJECTED,
                }
                else None
            ),
            created_at=created_at or datetime.now(UTC),
            reviewed_at=(
                datetime.now(UTC)
                if status
                in {
                    HumanApprovalStatus.APPROVED,
                    HumanApprovalStatus.REJECTED,
                }
                else None
            ),
        )
        session.add(approval)
        session.commit()
        return approval.id


def set_current_actor(actor: ActorContext) -> None:
    app.dependency_overrides[get_current_actor] = lambda: actor


def auditor_actor() -> ActorContext:
    return ActorContext(
        actor_type=ActorType.USER,
        actor_id="user:auditor-1",
        roles=("auditor",),
    )


def assert_human_approval_status(
    session_factory: SessionFactory,
    approval_id: UUID,
    expected_status: HumanApprovalStatus,
) -> None:
    with session_factory() as session:
        approval = session.get(HumanApproval, approval_id)

    assert approval is not None
    assert approval.status is expected_status


def fetch_human_approval_audit_logs(
    session_factory: SessionFactory,
    approval_id: UUID,
) -> list[AuditLog]:
    with session_factory() as session:
        statement = (
            select(AuditLog)
            .where(
                AuditLog.entity_type == "human_approval",
                AuditLog.entity_id == str(approval_id),
            )
            .order_by(AuditLog.created_at, AuditLog.id)
        )
        return list(session.scalars(statement).all())


def fetch_all_human_approval_audit_logs(
    session_factory: SessionFactory,
) -> list[AuditLog]:
    with session_factory() as session:
        statement = (
            select(AuditLog)
            .where(AuditLog.entity_type == "human_approval")
            .order_by(AuditLog.created_at, AuditLog.id)
        )
        return list(session.scalars(statement).all())
