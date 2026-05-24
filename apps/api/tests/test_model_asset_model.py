from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

from agent_governance_api.models import (
    ModelAsset,
    ModelAssetStatus,
    ModelAssetType,
    ModelProvider,
    OwnerType,
    RiskLevel,
)
from agent_governance_api.schemas import ModelAssetCreate, ModelAssetRead


def test_model_asset_enums_have_expected_values() -> None:
    assert [item.value for item in ModelAssetType] == [
        "llm",
        "embedding",
        "reranker",
        "classifier",
        "vision",
        "audio",
        "other",
    ]
    assert [item.value for item in ModelProvider] == [
        "openai",
        "mistral",
        "anthropic",
        "local",
        "azure",
        "aws",
        "gcp",
        "other",
    ]
    assert [item.value for item in ModelAssetStatus] == [
        "active",
        "disabled",
        "retired",
    ]


def test_model_asset_create_schema_accepts_valid_values() -> None:
    model_asset = ModelAssetCreate(
        name="Support assistant chat model",
        description="Governed hosted language model.",
        model_type="llm",
        provider="openai",
        model_ref="support-chat-deployment",
        version="2026-01",
        owner_type="team",
        owner_id="team:ai-platform",
        owner_name="AI Platform",
        owner_contact_email="ai-platform@example.invalid",
        status="active",
        risk_level="medium",
        metadata={"domain": "support", "usage": "assistant_response"},
    )

    assert model_asset.model_type is ModelAssetType.LLM
    assert model_asset.provider is ModelProvider.OPENAI
    assert model_asset.owner_type is OwnerType.TEAM
    assert model_asset.status is ModelAssetStatus.ACTIVE
    assert model_asset.risk_level is RiskLevel.MEDIUM
    assert model_asset.metadata == {
        "domain": "support",
        "usage": "assistant_response",
    }


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("model_type", "chatbot"),
        ("provider", "vendor"),
        ("owner_type", "department"),
        ("status", "draft"),
        ("risk_level", "severe"),
    ],
)
def test_model_asset_create_schema_rejects_invalid_enum_values(
    field: str,
    value: str,
) -> None:
    payload = model_asset_payload()
    payload[field] = value

    with pytest.raises(ValidationError):
        ModelAssetCreate(**payload)


def test_model_asset_schema_rejects_unsafe_metadata_keys() -> None:
    with pytest.raises(ValidationError):
        ModelAssetCreate(
            name="Support assistant chat model",
            model_type="llm",
            provider="openai",
            owner_type="team",
            owner_id="team:ai-platform",
            owner_name="AI Platform",
            status="active",
            risk_level="medium",
            metadata={"api_key_ref": "do-not-store"},
        )


def test_model_asset_read_schema_validates_from_model_instance() -> None:
    timestamp = datetime.now(UTC)
    model_asset = ModelAsset(
        id=uuid4(),
        name="Support assistant chat model",
        description=None,
        model_type=ModelAssetType.LLM,
        provider=ModelProvider.OPENAI,
        model_ref="support-chat-deployment",
        version="2026-01",
        owner_type=OwnerType.TEAM,
        owner_id="team:ai-platform",
        owner_name="AI Platform",
        owner_contact_email=None,
        status=ModelAssetStatus.ACTIVE,
        risk_level=RiskLevel.MEDIUM,
        metadata_={"domain": "support"},
        created_at=timestamp,
        updated_at=timestamp,
    )

    schema = ModelAssetRead.model_validate(model_asset)

    assert schema.model_type is ModelAssetType.LLM
    assert schema.provider is ModelProvider.OPENAI
    assert schema.owner_type is OwnerType.TEAM
    assert schema.status is ModelAssetStatus.ACTIVE
    assert schema.risk_level is RiskLevel.MEDIUM
    assert schema.metadata == {"domain": "support"}
    assert "metadata_" not in schema.model_dump()


def test_model_asset_model_rejects_unsafe_metadata_keys() -> None:
    with pytest.raises(ValueError, match="unsafe key"):
        ModelAsset(
            name="Support assistant chat model",
            model_type=ModelAssetType.LLM,
            provider=ModelProvider.OPENAI,
            owner_type=OwnerType.TEAM,
            owner_id="team:ai-platform",
            owner_name="AI Platform",
            status=ModelAssetStatus.ACTIVE,
            risk_level=RiskLevel.MEDIUM,
            metadata_={"client_secret": "do-not-store"},
        )


def test_model_asset_table_compiles_for_postgresql() -> None:
    ddl = str(CreateTable(ModelAsset.__table__).compile(dialect=postgresql.dialect()))

    assert "CREATE TABLE model_assets" in ddl
    assert "model_asset_type" in ddl
    assert "model_asset_provider" in ddl
    assert "model_asset_owner_type" in ddl
    assert "model_asset_status" in ddl
    assert "model_asset_risk_level" in ddl
    assert "metadata JSON DEFAULT '{}'" in ddl


def test_model_asset_migration_declares_expected_table() -> None:
    migration_path = (
        Path(__file__).resolve().parents[1]
        / "migrations"
        / "versions"
        / "202605240003_create_model_assets_table.py"
    )
    migration_text = migration_path.read_text(encoding="utf-8")

    assert 'revision: str = "202605240003"' in migration_text
    assert 'down_revision: str | None = "202605240002"' in migration_text
    assert '"model_assets"' in migration_text
    assert '"model_type"' in migration_text
    assert '"provider"' in migration_text
    assert '"model_ref"' in migration_text
    assert '"metadata"' in migration_text


def model_asset_payload() -> dict[str, object]:
    return {
        "name": "Support assistant chat model",
        "description": "Governed hosted language model.",
        "model_type": "llm",
        "provider": "openai",
        "model_ref": "support-chat-deployment",
        "version": "2026-01",
        "owner_type": "team",
        "owner_id": "team:ai-platform",
        "owner_name": "AI Platform",
        "owner_contact_email": "ai-platform@example.invalid",
        "status": "active",
        "risk_level": "medium",
        "metadata": {"domain": "support", "usage": "assistant_response"},
    }
