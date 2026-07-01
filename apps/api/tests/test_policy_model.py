import json
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
    ActorType,
    Agent,
    AgentStatus,
    Environment,
    OwnerType,
    Policy,
    PolicyDecision,
    PolicyDecisionValue,
    PolicyFolder,
    PolicyRule,
    PolicyStatus,
    PolicyVersion,
    PolicyVersionStatus,
    RiskLevel,
)
from agent_governance_api.schemas import (
    PolicyCreate,
    PolicyDecisionCreate,
    PolicyDecisionRead,
    PolicyFolderCreate,
    PolicyFolderRead,
    PolicyFolderUpdate,
    PolicyRead,
    PolicyRuleCreate,
    PolicyRuleUpdate,
    PolicyUpdate,
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
    folder_id = uuid4()
    policy = PolicyCreate(
        name="Production ownership required",
        description="Production agents must have an accountable owner.",
        status="active",
        folder_id=folder_id,
    )
    folder = PolicyFolderCreate(
        name="Runtime controls",
        description=None,
        color="#8b78f6",
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
    assert policy.folder_id == folder_id
    assert folder.sort_order == 0
    assert decision.decision is PolicyDecisionValue.REQUIRE_HUMAN_REVIEW


def test_policy_update_schema_accepts_partial_updates() -> None:
    folder_id = uuid4()
    update = PolicyUpdate(description=None, folder_id=folder_id, status="archived")

    assert update.description is None
    assert update.folder_id == folder_id
    assert update.status is PolicyStatus.ARCHIVED


def test_policy_folder_update_schema_accepts_nullable_optional_fields() -> None:
    update = PolicyFolderUpdate(description=None, color=None, sort_order=2)

    assert update.description is None
    assert update.color is None
    assert update.sort_order == 2


def test_policy_rule_schemas_accept_deterministic_conditions() -> None:
    condition = json.dumps(
        {
            "decision": "deny",
            "reason": "Production email is denied.",
            "tool_name": "send_email",
            "environment": "production",
        }
    )
    create = PolicyRuleCreate(
        policy_id=uuid4(),
        name="Deny production email",
        description=None,
        condition=condition,
    )
    update = PolicyRuleUpdate(condition=condition)

    assert create.condition == condition
    assert update.condition == condition


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
                "trace_event_id": None,
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


@pytest.mark.parametrize(
    ("schema_class", "payload"),
    [
        (PolicyCreate, {"name": "", "description": None, "status": "draft"}),
        (PolicyCreate, {"name": "   ", "description": None, "status": "draft"}),
        (PolicyFolderCreate, {"name": "", "description": None}),
        (PolicyFolderUpdate, {"name": " "}),
        (PolicyFolderUpdate, {"sort_order": None}),
        (PolicyUpdate, {"name": ""}),
        (PolicyUpdate, {"name": "   "}),
        (PolicyUpdate, {"name": None}),
        (PolicyUpdate, {"status": None}),
    ],
)
def test_policy_schemas_reject_blank_or_null_required_fields(
    schema_class: (
        type[PolicyCreate]
        | type[PolicyFolderCreate]
        | type[PolicyFolderUpdate]
        | type[PolicyUpdate]
    ),
    payload: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        schema_class(**payload)


@pytest.mark.parametrize(
    ("schema_class", "payload"),
    [
        (
            PolicyRuleCreate,
            {
                "policy_id": uuid4(),
                "name": "",
                "description": None,
                "condition": '{"decision":"deny","reason":"Denied."}',
            },
        ),
        (
            PolicyRuleCreate,
            {
                "policy_id": uuid4(),
                "name": "Deny email",
                "description": None,
                "condition": "",
            },
        ),
        (
            PolicyRuleCreate,
            {
                "policy_id": uuid4(),
                "name": "Deny email",
                "description": None,
                "condition": '{"decision":"deny","reason":"Denied.","model":"gpt"}',
            },
        ),
        (PolicyRuleUpdate, {"name": ""}),
        (PolicyRuleUpdate, {"condition": ""}),
        (PolicyRuleUpdate, {"policy_id": None}),
        (PolicyRuleUpdate, {"name": None}),
        (PolicyRuleUpdate, {"condition": None}),
    ],
)
def test_policy_rule_schemas_reject_invalid_rule_fields(
    schema_class: type[PolicyRuleCreate] | type[PolicyRuleUpdate],
    payload: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        schema_class(**payload)


def test_policy_decision_schema_validates_from_model_instance() -> None:
    policy_decision = PolicyDecision(
        id=uuid4(),
        agent_id=uuid4(),
        policy_id=uuid4(),
        policy_version_id=uuid4(),
        rule_id=uuid4(),
        trace_event_id=uuid4(),
        decision=PolicyDecisionValue.DENY,
        reason="Agent is not approved for this action.",
        context_hash=None,
        created_at=datetime.now(UTC),
    )

    schema = PolicyDecisionRead.model_validate(policy_decision)

    assert schema.decision is PolicyDecisionValue.DENY
    assert schema.reason == "Agent is not approved for this action."
    assert schema.policy_version_id == policy_decision.policy_version_id
    assert schema.trace_event_id == policy_decision.trace_event_id


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
    assert schema.folder_id is None
    assert schema.folder_name is None


def test_policy_folder_read_schema_validates_from_model_instance() -> None:
    timestamp = datetime.now(UTC)
    folder = PolicyFolder(
        id=uuid4(),
        name="Runtime controls",
        description=None,
        color="#8b78f6",
        sort_order=1,
        created_at=timestamp,
        updated_at=timestamp,
    )

    schema = PolicyFolderRead.model_validate(folder)

    assert schema.name == "Runtime controls"
    assert schema.color == "#8b78f6"
    assert schema.sort_order == 1


def test_policy_tables_compile_for_postgresql() -> None:
    policies_ddl = str(
        CreateTable(Policy.__table__).compile(dialect=postgresql.dialect())
    )
    policy_folders_ddl = str(
        CreateTable(PolicyFolder.__table__).compile(dialect=postgresql.dialect())
    )
    rules_ddl = str(
        CreateTable(PolicyRule.__table__).compile(dialect=postgresql.dialect())
    )
    decisions_ddl = str(
        CreateTable(PolicyDecision.__table__).compile(dialect=postgresql.dialect())
    )

    assert "CREATE TABLE policy_folders" in policy_folders_ddl
    assert "CREATE TABLE policies" in policies_ddl
    assert "policy_status" in policies_ddl
    assert "FOREIGN KEY(folder_id) REFERENCES policy_folders" in policies_ddl
    assert "CREATE TABLE policy_rules" in rules_ddl
    assert "FOREIGN KEY(policy_id) REFERENCES policies" in rules_ddl
    assert "CREATE TABLE policy_decisions" in decisions_ddl
    assert "policy_decision_value" in decisions_ddl
    assert "FOREIGN KEY(agent_id) REFERENCES agents" in decisions_ddl
    assert "FOREIGN KEY(policy_id) REFERENCES policies" in decisions_ddl
    assert "FOREIGN KEY(policy_version_id) REFERENCES policy_versions" in decisions_ddl
    assert "FOREIGN KEY(rule_id) REFERENCES policy_rules" in decisions_ddl
    assert "FOREIGN KEY(trace_event_id) REFERENCES trace_events" in decisions_ddl


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

            policy_version = PolicyVersion(
                policy_id=policy.id,
                version_number=1,
                status=PolicyVersionStatus.ACTIVE,
                change_summary="Initial approved policy.",
                policy_snapshot={
                    "id": str(policy.id),
                    "name": policy.name,
                    "description": policy.description,
                    "status": policy.status.value,
                },
                rule_snapshots=[],
                check_step_snapshots=[],
                created_by_actor_type=ActorType.DEVELOPMENT,
                created_by_actor_id="dev-placeholder",
            )
            session.add(policy_version)
            session.flush()

            decision = PolicyDecision(
                agent_id=agent.id,
                policy_id=policy.id,
                policy_version_id=policy_version.id,
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
            assert saved_decision.policy_version_id == policy_version.id
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
