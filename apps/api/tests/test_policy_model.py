from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine, select
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Session
from sqlalchemy.schema import CreateTable

from agent_governance_api.database import Base
from agent_governance_api.models import (
    Agent,
    AgentStatus,
    Environment,
    OwnerType,
    Policy,
    PolicyDecision,
    PolicyDecisionValue,
    PolicyRule,
    PolicyStatus,
    RiskLevel,
)
from agent_governance_api.schemas import (
    PolicyCreate,
    PolicyDecisionCreate,
    PolicyDecisionRead,
    PolicyRead,
)


def test_policy_enums_have_expected_values() -> None:
    assert [item.value for item in PolicyStatus] == [
        "draft",
        "active",
        "disabled",
        "archived",
    ]
    assert [item.value for item in PolicyDecisionValue] == [
        "allow",
        "deny",
        "require_human_review",
        "not_applicable",
    ]


def test_policy_schemas_accept_valid_enum_values() -> None:
    policy = PolicyCreate(
        name="Production ownership required",
        description="Production agents must have an accountable owner.",
        status="active",
    )
    decision = PolicyDecisionCreate(
        agent_id=None,
        policy_id=None,
        rule_id=None,
        decision="require_human_review",
        reason="High-risk action needs review.",
        context_hash="sha256:example",
    )

    assert policy.status is PolicyStatus.ACTIVE
    assert decision.decision is PolicyDecisionValue.REQUIRE_HUMAN_REVIEW


@pytest.mark.parametrize(
    ("schema_class", "payload"),
    [
        (
            PolicyCreate,
            {
                "name": "Production ownership required",
                "description": None,
                "status": "enabled",
            },
        ),
        (
            PolicyDecisionCreate,
            {
                "agent_id": None,
                "policy_id": None,
                "rule_id": None,
                "decision": "escalate",
                "reason": "Unsupported decision.",
                "context_hash": None,
            },
        ),
    ],
)
def test_policy_schemas_reject_invalid_enum_values(
    schema_class: type[PolicyCreate] | type[PolicyDecisionCreate],
    payload: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        schema_class(**payload)


def test_policy_decision_schema_validates_from_model_instance() -> None:
    policy_decision = PolicyDecision(
        id=uuid4(),
        agent_id=uuid4(),
        policy_id=uuid4(),
        rule_id=uuid4(),
        decision=PolicyDecisionValue.DENY,
        reason="Agent is not approved for this action.",
        context_hash=None,
        created_at=datetime.now(UTC),
    )

    schema = PolicyDecisionRead.model_validate(policy_decision)

    assert schema.decision is PolicyDecisionValue.DENY
    assert schema.reason == "Agent is not approved for this action."


def test_policy_read_schema_validates_from_model_instance() -> None:
    timestamp = datetime.now(UTC)
    policy = Policy(
        id=uuid4(),
        name="Production ownership required",
        description=None,
        status=PolicyStatus.DRAFT,
        created_at=timestamp,
        updated_at=timestamp,
    )

    schema = PolicyRead.model_validate(policy)

    assert schema.status is PolicyStatus.DRAFT
    assert schema.name == "Production ownership required"


def test_policy_tables_compile_for_postgresql() -> None:
    policies_ddl = str(
        CreateTable(Policy.__table__).compile(dialect=postgresql.dialect())
    )
    rules_ddl = str(
        CreateTable(PolicyRule.__table__).compile(dialect=postgresql.dialect())
    )
    decisions_ddl = str(
        CreateTable(PolicyDecision.__table__).compile(dialect=postgresql.dialect())
    )

    assert "CREATE TABLE policies" in policies_ddl
    assert "policy_status" in policies_ddl
    assert "CREATE TABLE policy_rules" in rules_ddl
    assert "FOREIGN KEY(policy_id) REFERENCES policies" in rules_ddl
    assert "CREATE TABLE policy_decisions" in decisions_ddl
    assert "policy_decision_value" in decisions_ddl
    assert "FOREIGN KEY(agent_id) REFERENCES agents" in decisions_ddl
    assert "FOREIGN KEY(policy_id) REFERENCES policies" in decisions_ddl
    assert "FOREIGN KEY(rule_id) REFERENCES policy_rules" in decisions_ddl


def test_policy_decision_persists_with_optional_domain_links() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    try:
        with Session(engine) as session:
            agent = build_agent()
            policy = Policy(
                name="Approved agents only",
                description="Only approved agents can perform governed actions.",
                status=PolicyStatus.ACTIVE,
            )
            session.add_all([agent, policy])
            session.flush()

            rule = PolicyRule(
                policy_id=policy.id,
                name="Agent must be approved",
                description=None,
                condition="agent.status == 'approved'",
            )
            session.add(rule)
            session.flush()

            decision = PolicyDecision(
                agent_id=agent.id,
                policy_id=policy.id,
                rule_id=rule.id,
                decision=PolicyDecisionValue.DENY,
                reason="Agent status is draft.",
                context_hash="sha256:agent-status-draft",
            )
            session.add(decision)
            session.commit()

            saved_decision = session.scalars(select(PolicyDecision)).one()

            assert saved_decision.agent_id == agent.id
            assert saved_decision.policy_id == policy.id
            assert saved_decision.rule_id == rule.id
            assert saved_decision.decision is PolicyDecisionValue.DENY
            assert saved_decision.context_hash == "sha256:agent-status-draft"
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


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
