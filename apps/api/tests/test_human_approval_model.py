from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine, select
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Session
from sqlalchemy.schema import CreateTable

from agent_governance_api.database import Base
from agent_governance_api.models import (
    ActorType,
    Agent,
    AgentStatus,
    Environment,
    HumanApproval,
    HumanApprovalStatus,
    OwnerType,
    PolicyDecision,
    PolicyDecisionValue,
    RiskLevel,
)
from agent_governance_api.schemas import HumanApprovalCreate, HumanApprovalRead


def test_human_approval_status_enum_has_expected_values() -> None:
    assert [item.value for item in HumanApprovalStatus] == [
        "pending",
        "approved",
        "rejected",
        "expired",
        "cancelled",
    ]


def test_human_approval_schema_accepts_valid_status_values() -> None:
    payload = human_approval_payload(status="pending")

    approval = HumanApprovalCreate(**payload)

    assert approval.status is HumanApprovalStatus.PENDING
    assert approval.requested_by_actor_type is ActorType.DEVELOPMENT
    assert approval.reviewed_by_actor_type is None


def test_human_approval_schema_rejects_invalid_status() -> None:
    with pytest.raises(ValidationError):
        HumanApprovalCreate(**human_approval_payload(status="waiting"))


def test_human_approval_read_schema_validates_from_model_instance() -> None:
    timestamp = datetime.now(UTC)
    approval = HumanApproval(
        id=uuid4(),
        agent_id=uuid4(),
        policy_decision_id=None,
        status=HumanApprovalStatus.PENDING,
        requested_by_actor_type=ActorType.DEVELOPMENT,
        requested_by_actor_id="dev-placeholder",
        reviewed_by_actor_type=None,
        reviewed_by_actor_id=None,
        reason="High-risk tool call requires review.",
        decision_note=None,
        created_at=timestamp,
        reviewed_at=None,
        expires_at=timestamp + timedelta(hours=1),
    )

    schema = HumanApprovalRead.model_validate(approval)

    assert schema.status is HumanApprovalStatus.PENDING
    assert schema.reason == "High-risk tool call requires review."
    assert schema.expires_at == approval.expires_at


def test_human_approval_links_to_agent() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    try:
        with Session(engine) as session:
            agent = build_agent()
            session.add(agent)
            session.flush()

            approval = HumanApproval(
                agent_id=agent.id,
                policy_decision_id=None,
                status=HumanApprovalStatus.PENDING,
                requested_by_actor_type=ActorType.DEVELOPMENT,
                requested_by_actor_id="dev-placeholder",
                reason="Manual review requested.",
            )
            session.add(approval)
            session.commit()

            saved_approval = session.scalars(select(HumanApproval)).one()

            assert saved_approval.agent_id == agent.id
            assert saved_approval.policy_decision_id is None
            assert saved_approval.status is HumanApprovalStatus.PENDING
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_human_approval_links_to_policy_decision() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    try:
        with Session(engine) as session:
            agent = build_agent()
            session.add(agent)
            session.flush()

            policy_decision = PolicyDecision(
                agent_id=agent.id,
                decision=PolicyDecisionValue.REQUIRE_HUMAN_REVIEW,
                reason="The requested action requires review.",
            )
            session.add(policy_decision)
            session.flush()

            approval = HumanApproval(
                agent_id=agent.id,
                policy_decision_id=policy_decision.id,
                status=HumanApprovalStatus.PENDING,
                requested_by_actor_type=ActorType.DEVELOPMENT,
                requested_by_actor_id="dev-placeholder",
            )
            session.add(approval)
            session.commit()

            saved_approval = session.scalars(select(HumanApproval)).one()

            assert saved_approval.agent_id == agent.id
            assert saved_approval.policy_decision_id == policy_decision.id
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_pending_human_approval_can_exist_without_reviewer() -> None:
    approval = HumanApproval(
        agent_id=uuid4(),
        status=HumanApprovalStatus.PENDING,
        requested_by_actor_type=ActorType.DEVELOPMENT,
        requested_by_actor_id="dev-placeholder",
        reviewed_by_actor_type=None,
        reviewed_by_actor_id=None,
        reviewed_at=None,
    )

    assert approval.reviewed_by_actor_type is None
    assert approval.reviewed_by_actor_id is None
    assert approval.reviewed_at is None


@pytest.mark.parametrize(
    ("status", "decision_note"),
    [
        (HumanApprovalStatus.APPROVED, "Approved for this run."),
        (HumanApprovalStatus.REJECTED, "Rejected for this run."),
    ],
)
def test_reviewed_human_approval_supports_reviewer_fields(
    status: HumanApprovalStatus,
    decision_note: str,
) -> None:
    reviewed_at = datetime.now(UTC)

    approval = HumanApproval(
        agent_id=uuid4(),
        status=status,
        requested_by_actor_type=ActorType.DEVELOPMENT,
        requested_by_actor_id="dev-placeholder",
        reviewed_by_actor_type=ActorType.USER,
        reviewed_by_actor_id="user:reviewer-123",
        decision_note=decision_note,
        reviewed_at=reviewed_at,
    )

    assert approval.status is status
    assert approval.reviewed_by_actor_type is ActorType.USER
    assert approval.reviewed_by_actor_id == "user:reviewer-123"
    assert approval.decision_note == decision_note
    assert approval.reviewed_at == reviewed_at


def test_human_approval_table_compiles_for_postgresql() -> None:
    ddl = str(
        CreateTable(HumanApproval.__table__).compile(dialect=postgresql.dialect())
    )

    assert "CREATE TABLE human_approvals" in ddl
    assert "human_approval_status" in ddl
    assert "human_approval_requested_actor_type" in ddl
    assert "human_approval_reviewed_actor_type" in ddl
    assert "FOREIGN KEY(agent_id) REFERENCES agents" in ddl
    assert "FOREIGN KEY(policy_decision_id) REFERENCES policy_decisions" in ddl


def human_approval_payload(status: str) -> dict[str, object]:
    return {
        "agent_id": str(uuid4()),
        "policy_decision_id": None,
        "status": status,
        "requested_by_actor_type": "development",
        "requested_by_actor_id": "dev-placeholder",
        "reviewed_by_actor_type": None,
        "reviewed_by_actor_id": None,
        "reason": "High-risk tool call requires review.",
        "decision_note": None,
        "reviewed_at": None,
        "expires_at": datetime.now(UTC).isoformat(),
    }


def build_agent() -> Agent:
    return Agent(
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
