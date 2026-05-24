from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

from agent_governance_api.models import (
    DataSource,
    DataSourceStatus,
    DataSourceType,
    OwnerType,
    RiskLevel,
)
from agent_governance_api.schemas import DataSourceCreate, DataSourceRead


def test_source_enums_have_expected_values() -> None:
    assert [item.value for item in DataSourceType] == [
        "knowledge_base",
        "database",
        "document_store",
        "api",
        "bucket",
        "filesystem",
        "other",
    ]
    assert [item.value for item in DataSourceStatus] == [
        "active",
        "disabled",
        "retired",
    ]


def test_source_create_schema_accepts_valid_values() -> None:
    source = DataSourceCreate(
        name="Support knowledge base",
        description="Governed source for support runbooks.",
        source_type="knowledge_base",
        external_ref="kb:support-runbooks",
        owner_type="team",
        owner_id="team:support-ops",
        owner_name="Support Operations",
        owner_contact_email="support-ops@example.invalid",
        status="active",
        risk_level="medium",
        metadata={"domain": "support", "system": "runbook_index"},
    )

    assert source.source_type is DataSourceType.KNOWLEDGE_BASE
    assert source.owner_type is OwnerType.TEAM
    assert source.status is DataSourceStatus.ACTIVE
    assert source.risk_level is RiskLevel.MEDIUM
    assert source.metadata == {"domain": "support", "system": "runbook_index"}


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("source_type", "spreadsheet"),
        ("owner_type", "department"),
        ("status", "draft"),
        ("risk_level", "severe"),
    ],
)
def test_source_create_schema_rejects_invalid_enum_values(
    field: str,
    value: str,
) -> None:
    payload = source_payload()
    payload[field] = value

    with pytest.raises(ValidationError):
        DataSourceCreate(**payload)


def test_source_schema_rejects_unsafe_metadata_keys() -> None:
    with pytest.raises(ValidationError):
        DataSourceCreate(
            name="Support knowledge base",
            source_type="knowledge_base",
            owner_type="team",
            owner_id="team:support-ops",
            owner_name="Support Operations",
            status="active",
            risk_level="medium",
            metadata={"access_token_ref": "do-not-store"},
        )


def test_source_read_schema_validates_from_model_instance() -> None:
    timestamp = datetime.now(UTC)
    source = DataSource(
        id=uuid4(),
        name="Support knowledge base",
        description=None,
        source_type=DataSourceType.KNOWLEDGE_BASE,
        external_ref="kb:support-runbooks",
        owner_type=OwnerType.TEAM,
        owner_id="team:support-ops",
        owner_name="Support Operations",
        owner_contact_email=None,
        status=DataSourceStatus.ACTIVE,
        risk_level=RiskLevel.MEDIUM,
        metadata_={"domain": "support"},
        created_at=timestamp,
        updated_at=timestamp,
    )

    schema = DataSourceRead.model_validate(source)

    assert schema.source_type is DataSourceType.KNOWLEDGE_BASE
    assert schema.owner_type is OwnerType.TEAM
    assert schema.status is DataSourceStatus.ACTIVE
    assert schema.risk_level is RiskLevel.MEDIUM
    assert schema.metadata == {"domain": "support"}
    assert "metadata_" not in schema.model_dump()


def test_source_model_rejects_unsafe_metadata_keys() -> None:
    with pytest.raises(ValueError, match="unsafe key"):
        DataSource(
            name="Support knowledge base",
            source_type=DataSourceType.KNOWLEDGE_BASE,
            owner_type=OwnerType.TEAM,
            owner_id="team:support-ops",
            owner_name="Support Operations",
            status=DataSourceStatus.ACTIVE,
            risk_level=RiskLevel.MEDIUM,
            metadata_={"client_secret": "do-not-store"},
        )


def test_source_table_compiles_for_postgresql() -> None:
    ddl = str(CreateTable(DataSource.__table__).compile(dialect=postgresql.dialect()))

    assert "CREATE TABLE sources" in ddl
    assert "source_type" in ddl
    assert "source_owner_type" in ddl
    assert "source_status" in ddl
    assert "source_risk_level" in ddl
    assert "metadata JSON DEFAULT '{}'" in ddl


def test_source_migration_declares_expected_table() -> None:
    migration_path = (
        Path(__file__).resolve().parents[1]
        / "migrations"
        / "versions"
        / "202605240002_create_sources_table.py"
    )
    migration_text = migration_path.read_text(encoding="utf-8")

    assert 'revision: str = "202605240002"' in migration_text
    assert 'down_revision: str | None = "202605240001"' in migration_text
    assert '"sources"' in migration_text
    assert '"source_type"' in migration_text
    assert '"owner_type"' in migration_text
    assert '"metadata"' in migration_text


def source_payload() -> dict[str, object]:
    return {
        "name": "Support knowledge base",
        "description": "Governed source for support runbooks.",
        "source_type": "knowledge_base",
        "external_ref": "kb:support-runbooks",
        "owner_type": "team",
        "owner_id": "team:support-ops",
        "owner_name": "Support Operations",
        "owner_contact_email": "support-ops@example.invalid",
        "status": "active",
        "risk_level": "medium",
        "metadata": {"domain": "support", "system": "runbook_index"},
    }
