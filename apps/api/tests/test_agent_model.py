from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

from agent_governance_api.models import (
    Agent,
    AgentStatus,
    Environment,
    OwnerType,
    RiskLevel,
)
from agent_governance_api.schemas import AgentCreate, AgentRead


def test_agent_enums_have_expected_values() -> None:
    assert [item.value for item in Environment] == [
        "development",
        "staging",
        "production",
    ]
    assert [item.value for item in AgentStatus] == [
        "draft",
        "under_review",
        "approved",
        "active",
        "suspended",
        "retired",
    ]
    assert [item.value for item in RiskLevel] == ["low", "medium", "high", "critical"]
    assert [item.value for item in OwnerType] == [
        "user",
        "team",
        "service",
        "organization_unit",
    ]


def test_agent_create_schema_accepts_valid_enum_values() -> None:
    agent = AgentCreate(
        name="Support assistant",
        description="Routes support requests.",
        owner_type="team",
        owner_id="ai-platform",
        owner_name="AI Platform",
        owner_contact_email="owner@example.com",
        environment="production",
        status="active",
        risk_level="high",
        framework="LangGraph",
    )

    assert agent.owner_type is OwnerType.TEAM
    assert agent.environment is Environment.PRODUCTION
    assert agent.status is AgentStatus.ACTIVE
    assert agent.risk_level is RiskLevel.HIGH


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("owner_type", "department"),
        ("environment", "sandbox"),
        ("status", "running"),
        ("risk_level", "severe"),
    ],
)
def test_agent_create_schema_rejects_invalid_enum_values(
    field: str,
    value: str,
) -> None:
    payload = {
        "name": "Support assistant",
        "description": None,
        "owner_type": "team",
        "owner_id": "ai-platform",
        "owner_name": "AI Platform",
        "owner_contact_email": "owner@example.com",
        "environment": "production",
        "status": "active",
        "risk_level": "high",
        "framework": None,
    }
    payload[field] = value

    with pytest.raises(ValidationError):
        AgentCreate(**payload)


def test_agent_read_schema_validates_from_model_instance() -> None:
    timestamp = datetime.now(UTC)
    agent = Agent(
        id=uuid4(),
        name="Support assistant",
        description=None,
        owner_type=OwnerType.TEAM,
        owner_id="ai-platform",
        owner_name="AI Platform",
        owner_contact_email="owner@example.com",
        environment=Environment.STAGING,
        status=AgentStatus.DRAFT,
        risk_level=RiskLevel.MEDIUM,
        framework=None,
        created_at=timestamp,
        updated_at=timestamp,
    )

    schema = AgentRead.model_validate(agent)

    assert schema.environment is Environment.STAGING
    assert schema.status is AgentStatus.DRAFT
    assert schema.risk_level is RiskLevel.MEDIUM
    assert schema.owner_type is OwnerType.TEAM
    assert schema.owner_id == "ai-platform"
    assert schema.owner_contact_email == "owner@example.com"


def test_agent_table_compiles_for_postgresql() -> None:
    ddl = str(CreateTable(Agent.__table__).compile(dialect=postgresql.dialect()))

    assert "CREATE TABLE agents" in ddl
    assert "owner_type" in ddl
    assert "owner_contact_email" in ddl
    assert "agent_owner_type" in ddl
    assert "agent_environment" in ddl
