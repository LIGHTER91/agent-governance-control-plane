from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

from agent_governance_api.models import (
    AccessGrant,
    AccessGrantStatus,
    AccessGrantSubjectType,
    AccessGrantTargetType,
    AccessGrantType,
    ActorType,
    RiskLevel,
)
from agent_governance_api.schemas import (
    AccessGrantCreate,
    AccessGrantRead,
    AccessGrantTransitionRequest,
)


def test_access_grant_enums_have_expected_values() -> None:
    assert [item.value for item in AccessGrantType] == [
        "capability",
        "source",
        "model",
        "permission",
        "other",
    ]
    assert [item.value for item in AccessGrantSubjectType] == ["agent"]
    assert [item.value for item in AccessGrantTargetType] == [
        "capability",
        "source",
        "model_asset",
        "external",
        "other",
    ]
    assert [item.value for item in AccessGrantStatus] == [
        "pending_review",
        "active",
        "suspended",
        "revoked",
        "expired",
    ]


def test_access_grant_create_schema_accepts_valid_values() -> None:
    access_grant = AccessGrantCreate(**access_grant_payload())

    assert access_grant.grant_type is AccessGrantType.CAPABILITY
    assert access_grant.subject_type is AccessGrantSubjectType.AGENT
    assert access_grant.target_type is AccessGrantTargetType.CAPABILITY
    assert access_grant.status is AccessGrantStatus.ACTIVE
    assert access_grant.risk_level is RiskLevel.MEDIUM
    assert access_grant.metadata == {
        "approval_ticket": "GOV-123",
        "review_status": "approved",
    }


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("grant_type", "role"),
        ("subject_type", "team"),
        ("target_type", "database"),
        ("status", "draft"),
        ("risk_level", "severe"),
    ],
)
def test_access_grant_create_schema_rejects_invalid_enum_values(
    field: str,
    value: str,
) -> None:
    payload = access_grant_payload()
    payload[field] = value

    with pytest.raises(ValidationError):
        AccessGrantCreate(**payload)


def test_access_grant_transition_schema_accepts_optional_note() -> None:
    request = AccessGrantTransitionRequest(
        transition_note="Owner requested temporary pause."
    )

    assert request.transition_note == "Owner requested temporary pause."


def test_access_grant_transition_schema_rejects_blank_note() -> None:
    with pytest.raises(ValidationError, match="transition_note must be non-empty"):
        AccessGrantTransitionRequest(transition_note=" ")


def test_access_grant_schema_requires_target_id_for_inventory_targets() -> None:
    payload = access_grant_payload()
    payload["target_id"] = None

    with pytest.raises(ValidationError, match="target_id is required"):
        AccessGrantCreate(**payload)


def test_access_grant_schema_requires_external_ref_for_external_targets() -> None:
    payload = access_grant_payload()
    payload["target_type"] = "external"
    payload["target_id"] = None
    payload["external_ref"] = None

    with pytest.raises(ValidationError, match="external_ref is required"):
        AccessGrantCreate(**payload)


def test_access_grant_schema_rejects_unsafe_metadata_keys() -> None:
    payload = access_grant_payload()
    payload["metadata"] = {"access_token_ref": "do-not-store"}

    with pytest.raises(ValidationError):
        AccessGrantCreate(**payload)


def test_access_grant_read_schema_validates_from_model_instance() -> None:
    timestamp = datetime.now(UTC)
    subject_id = uuid4()
    target_id = uuid4()
    access_grant = AccessGrant(
        id=uuid4(),
        name="Support email capability access",
        description=None,
        grant_type=AccessGrantType.CAPABILITY,
        subject_type=AccessGrantSubjectType.AGENT,
        subject_id=subject_id,
        target_type=AccessGrantTargetType.CAPABILITY,
        target_id=target_id,
        external_ref=None,
        status=AccessGrantStatus.ACTIVE,
        granted_by_actor_type=ActorType.DEVELOPMENT,
        granted_by_actor_id="dev-placeholder",
        reason="Support workflow reviewed.",
        expires_at=None,
        risk_level=RiskLevel.MEDIUM,
        metadata_={"approval_ticket": "GOV-123"},
        created_at=timestamp,
        updated_at=timestamp,
    )

    schema = AccessGrantRead.model_validate(access_grant)

    assert schema.grant_type is AccessGrantType.CAPABILITY
    assert schema.subject_type is AccessGrantSubjectType.AGENT
    assert schema.subject_id == subject_id
    assert schema.target_type is AccessGrantTargetType.CAPABILITY
    assert schema.target_id == target_id
    assert schema.status is AccessGrantStatus.ACTIVE
    assert schema.granted_by_actor_type is ActorType.DEVELOPMENT
    assert schema.granted_by_actor_id == "dev-placeholder"
    assert schema.risk_level is RiskLevel.MEDIUM
    assert schema.metadata == {"approval_ticket": "GOV-123"}
    assert "metadata_" not in schema.model_dump()


def test_access_grant_model_rejects_unsafe_metadata_keys() -> None:
    with pytest.raises(ValueError, match="unsafe key"):
        AccessGrant(
            name="Support email capability access",
            grant_type=AccessGrantType.CAPABILITY,
            subject_type=AccessGrantSubjectType.AGENT,
            subject_id=uuid4(),
            target_type=AccessGrantTargetType.CAPABILITY,
            target_id=uuid4(),
            status=AccessGrantStatus.ACTIVE,
            granted_by_actor_type=ActorType.DEVELOPMENT,
            granted_by_actor_id="dev-placeholder",
            risk_level=RiskLevel.MEDIUM,
            metadata_={"client_secret": "do-not-store"},
        )


def test_access_grant_table_compiles_for_postgresql() -> None:
    ddl = str(CreateTable(AccessGrant.__table__).compile(dialect=postgresql.dialect()))

    assert "CREATE TABLE access_grants" in ddl
    assert "access_grant_type" in ddl
    assert "access_grant_subject_type" in ddl
    assert "access_grant_target_type" in ddl
    assert "access_grant_status" in ddl
    assert "access_grant_granted_by_actor_type" in ddl
    assert "access_grant_risk_level" in ddl
    assert "metadata JSON DEFAULT '{}'" in ddl


def test_access_grant_migration_declares_expected_table() -> None:
    migration_path = (
        Path(__file__).resolve().parents[1]
        / "migrations"
        / "versions"
        / "202605240004_create_access_grants_table.py"
    )
    migration_text = migration_path.read_text(encoding="utf-8")

    assert 'revision: str = "202605240004"' in migration_text
    assert 'down_revision: str | None = "202605240003"' in migration_text
    assert '"access_grants"' in migration_text
    assert '"grant_type"' in migration_text
    assert '"subject_id"' in migration_text
    assert '"target_id"' in migration_text
    assert '"granted_by_actor_type"' in migration_text
    assert '"metadata"' in migration_text


def access_grant_payload() -> dict[str, object]:
    return {
        "name": "Support email capability access",
        "description": "Allow the V0 Support Assistant to use the support email tool.",
        "grant_type": "capability",
        "subject_type": "agent",
        "subject_id": str(uuid4()),
        "target_type": "capability",
        "target_id": str(uuid4()),
        "external_ref": None,
        "status": "active",
        "reason": "Support workflow reviewed.",
        "expires_at": "2026-12-31T23:59:59Z",
        "risk_level": "medium",
        "metadata": {
            "approval_ticket": "GOV-123",
            "review_status": "approved",
        },
    }
