from collections.abc import Callable, Iterator
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
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


def create_human_approval(client: TestClient, agent_id: UUID) -> UUID:
    response = client.post("/human-approvals", json={"agent_id": str(agent_id)})

    assert response.status_code == 201
    return UUID(response.json()["id"])


def set_current_actor(actor: ActorContext) -> None:
    app.dependency_overrides[get_current_actor] = lambda: actor


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
