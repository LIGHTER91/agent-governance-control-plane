from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

from agent_governance_api.models import (
    Capability,
    CapabilityStatus,
    CapabilityType,
    RiskLevel,
)
from agent_governance_api.schemas import CapabilityCreate, CapabilityRead


def test_capability_enums_have_expected_values() -> None:
    assert [item.value for item in CapabilityType] == [
        "tool",
        "api",
        "integration",
        "workflow_action",
        "other",
    ]
    assert [item.value for item in CapabilityStatus] == [
        "active",
        "disabled",
        "retired",
    ]


def test_capability_create_schema_accepts_valid_values() -> None:
    capability = CapabilityCreate(
        name="Send support email",
        description="Send a governed support email.",
        capability_type="tool",
        external_ref="tool:send_email",
        status="active",
        risk_level="medium",
        metadata={"domain": "support", "operation": "send_email"},
    )

    assert capability.capability_type is CapabilityType.TOOL
    assert capability.status is CapabilityStatus.ACTIVE
    assert capability.risk_level is RiskLevel.MEDIUM
    assert capability.metadata == {"domain": "support", "operation": "send_email"}


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("capability_type", "database"),
        ("status", "draft"),
        ("risk_level", "severe"),
    ],
)
def test_capability_create_schema_rejects_invalid_enum_values(
    field: str,
    value: str,
) -> None:
    payload = {
        "name": "Send support email",
        "description": None,
        "capability_type": "tool",
        "external_ref": "tool:send_email",
        "status": "active",
        "risk_level": "medium",
        "metadata": {},
    }
    payload[field] = value

    with pytest.raises(ValidationError):
        CapabilityCreate(**payload)


def test_capability_schema_rejects_unsafe_metadata_keys() -> None:
    with pytest.raises(ValidationError):
        CapabilityCreate(
            name="Send support email",
            capability_type="tool",
            status="active",
            risk_level="medium",
            metadata={"api_key_ref": "do-not-store"},
        )


def test_capability_read_schema_validates_from_model_instance() -> None:
    timestamp = datetime.now(UTC)
    capability = Capability(
        id=uuid4(),
        name="Send support email",
        description=None,
        capability_type=CapabilityType.TOOL,
        external_ref="tool:send_email",
        status=CapabilityStatus.ACTIVE,
        risk_level=RiskLevel.MEDIUM,
        metadata_={"domain": "support"},
        created_at=timestamp,
        updated_at=timestamp,
    )

    schema = CapabilityRead.model_validate(capability)

    assert schema.capability_type is CapabilityType.TOOL
    assert schema.status is CapabilityStatus.ACTIVE
    assert schema.risk_level is RiskLevel.MEDIUM
    assert schema.metadata == {"domain": "support"}
    assert "metadata_" not in schema.model_dump()


def test_capability_model_rejects_unsafe_metadata_keys() -> None:
    with pytest.raises(ValueError, match="unsafe key"):
        Capability(
            name="Send support email",
            capability_type=CapabilityType.TOOL,
            status=CapabilityStatus.ACTIVE,
            risk_level=RiskLevel.MEDIUM,
            metadata_={"client_secret": "do-not-store"},
        )


def test_capability_table_compiles_for_postgresql() -> None:
    ddl = str(CreateTable(Capability.__table__).compile(dialect=postgresql.dialect()))

    assert "CREATE TABLE capabilities" in ddl
    assert "capability_type" in ddl
    assert "capability_status" in ddl
    assert "capability_risk_level" in ddl
    assert "metadata JSON DEFAULT '{}'" in ddl


def test_capability_migration_declares_expected_table() -> None:
    migration_path = (
        Path(__file__).resolve().parents[1]
        / "migrations"
        / "versions"
        / "202605240001_create_capabilities_table.py"
    )
    migration_text = migration_path.read_text(encoding="utf-8")

    assert 'revision: str = "202605240001"' in migration_text
    assert 'down_revision: str | None = "202605220001"' in migration_text
    assert '"capabilities"' in migration_text
    assert '"capability_type"' in migration_text
    assert '"external_ref"' in migration_text
    assert '"metadata"' in migration_text
