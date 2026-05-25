from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

from agent_governance_api.models import (
    ActorType,
    DataUsageClassification,
    DataUsageProfile,
    DataUsageReviewStatus,
)
from agent_governance_api.schemas import (
    DataUsageProfileCreate,
    DataUsageProfileRead,
)


def test_data_usage_profile_enums_have_expected_values() -> None:
    assert [item.value for item in DataUsageClassification] == [
        "public",
        "internal",
        "confidential",
        "restricted",
    ]
    assert [item.value for item in DataUsageReviewStatus] == [
        "draft",
        "approved",
        "rejected",
        "expired",
        "needs_review",
    ]


def test_data_usage_profile_create_schema_accepts_valid_values() -> None:
    profile = DataUsageProfileCreate(
        data_classification="confidential",
        contains_personal_data=True,
        contains_sensitive_data=False,
        data_categories=["customer_data", "customer_data", "financial_data"],
        legal_basis="declared_contractual_basis",
        allowed_purposes=["customer_support_answering"],
        prohibited_purposes=["training_data_generation"],
        allowed_processing=["search", "rag"],
        prohibited_processing=["training"],
        residency="eu",
        retention_policy="retention:standard-support",
        data_owner="team:support-ops",
        review_status="approved",
        reviewed_by_actor_type="user",
        reviewed_by_actor_id="user:dpo-1",
        reviewed_at=datetime.now(UTC),
        review_expires_at=datetime.now(UTC),
        dpia_required=True,
        dpia_reference="dpia:DPIA-123",
        metadata={"catalog_ref": "catalog:source-123"},
    )

    assert profile.data_classification is DataUsageClassification.CONFIDENTIAL
    assert profile.review_status is DataUsageReviewStatus.APPROVED
    assert profile.reviewed_by_actor_type is ActorType.USER
    assert profile.data_categories == ["customer_data", "financial_data"]
    assert profile.metadata == {"catalog_ref": "catalog:source-123"}


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("data_classification", "secret"),
        ("review_status", "certified"),
    ],
)
def test_data_usage_profile_create_schema_rejects_invalid_enum_values(
    field: str,
    value: str,
) -> None:
    payload = data_usage_profile_payload()
    payload[field] = value

    with pytest.raises(ValidationError):
        DataUsageProfileCreate(**payload)


def test_data_usage_profile_schema_rejects_unsafe_metadata_keys() -> None:
    payload = data_usage_profile_payload()
    payload["metadata"] = {"raw_payload_ref": "do-not-store"}

    with pytest.raises(ValidationError):
        DataUsageProfileCreate(**payload)


def test_data_usage_profile_schema_rejects_non_string_list_values() -> None:
    payload = data_usage_profile_payload()
    payload["allowed_purposes"] = ["support", ""]

    with pytest.raises(ValidationError):
        DataUsageProfileCreate(**payload)


def test_data_usage_profile_read_schema_validates_from_model_instance() -> None:
    timestamp = datetime.now(UTC)
    profile = DataUsageProfile(
        id=uuid4(),
        source_id=uuid4(),
        data_classification=DataUsageClassification.CONFIDENTIAL,
        contains_personal_data=True,
        contains_sensitive_data=False,
        data_categories=["customer_data"],
        legal_basis="declared_contractual_basis",
        allowed_purposes=["customer_support_answering"],
        prohibited_purposes=["training_data_generation"],
        allowed_processing=["search", "rag"],
        prohibited_processing=["training"],
        residency="eu",
        retention_policy="retention:standard-support",
        data_owner="team:support-ops",
        review_status=DataUsageReviewStatus.APPROVED,
        reviewed_by_actor_type=ActorType.USER,
        reviewed_by_actor_id="user:dpo-1",
        reviewed_at=timestamp,
        review_expires_at=timestamp,
        dpia_required=True,
        dpia_reference="dpia:DPIA-123",
        metadata_={"catalog_ref": "catalog:source-123"},
        created_at=timestamp,
        updated_at=timestamp,
    )

    schema = DataUsageProfileRead.model_validate(profile)

    assert schema.data_classification is DataUsageClassification.CONFIDENTIAL
    assert schema.review_status is DataUsageReviewStatus.APPROVED
    assert schema.reviewed_by_actor_type is ActorType.USER
    assert schema.metadata == {"catalog_ref": "catalog:source-123"}
    assert "metadata_" not in schema.model_dump()


def test_data_usage_profile_model_rejects_unsafe_metadata_keys() -> None:
    with pytest.raises(ValueError, match="unsafe key"):
        DataUsageProfile(
            source_id=uuid4(),
            data_classification=DataUsageClassification.INTERNAL,
            review_status=DataUsageReviewStatus.DRAFT,
            metadata_={"client_secret": "do-not-store"},
        )


def test_data_usage_profile_model_rejects_invalid_list_values() -> None:
    with pytest.raises(ValueError, match="data_categories"):
        DataUsageProfile(
            source_id=uuid4(),
            data_classification=DataUsageClassification.INTERNAL,
            review_status=DataUsageReviewStatus.DRAFT,
            data_categories=["customer_data", ""],
        )


def test_data_usage_profile_table_compiles_for_postgresql() -> None:
    ddl = str(
        CreateTable(DataUsageProfile.__table__).compile(dialect=postgresql.dialect())
    )

    assert "CREATE TABLE data_usage_profiles" in ddl
    assert "source_id UUID NOT NULL" in ddl
    assert "data_usage_classification" in ddl
    assert "data_usage_review_status" in ddl
    assert "data_categories JSON DEFAULT '[]' NOT NULL" in ddl
    assert "metadata JSON DEFAULT '{}'" in ddl
    assert "uq_data_usage_profiles_source_id" in ddl


def test_data_usage_profile_migration_declares_expected_table() -> None:
    migration_path = (
        Path(__file__).resolve().parents[1]
        / "migrations"
        / "versions"
        / "202605260001_create_data_usage_profiles_table.py"
    )
    migration_text = migration_path.read_text(encoding="utf-8")

    assert 'revision: str = "202605260001"' in migration_text
    assert 'down_revision: str | None = "202605240004"' in migration_text
    assert '"data_usage_profiles"' in migration_text
    assert '"source_id"' in migration_text
    assert '"data_classification"' in migration_text
    assert '"review_status"' in migration_text
    assert '"metadata"' in migration_text


def data_usage_profile_payload() -> dict[str, object]:
    return {
        "data_classification": "confidential",
        "contains_personal_data": True,
        "contains_sensitive_data": False,
        "data_categories": ["customer_data"],
        "legal_basis": "declared_contractual_basis",
        "allowed_purposes": ["customer_support_answering"],
        "prohibited_purposes": ["training_data_generation"],
        "allowed_processing": ["search", "rag"],
        "prohibited_processing": ["training"],
        "residency": "eu",
        "retention_policy": "retention:standard-support",
        "data_owner": "team:support-ops",
        "review_status": "approved",
        "reviewed_by_actor_type": "user",
        "reviewed_by_actor_id": "user:dpo-1",
        "reviewed_at": "2026-01-15T12:00:00Z",
        "review_expires_at": "2027-01-15T12:00:00Z",
        "dpia_required": True,
        "dpia_reference": "dpia:DPIA-123",
        "metadata": {"catalog_ref": "catalog:source-123"},
    }
