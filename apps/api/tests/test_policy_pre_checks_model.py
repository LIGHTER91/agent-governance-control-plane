from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

from agent_governance_api.models import (
    CheckResult,
    CheckResultConfidence,
    CheckResultOutcome,
    CheckResultTargetType,
    CheckTool,
    CheckToolStatus,
    CheckToolType,
    OwnerType,
)
from agent_governance_api.schemas import (
    CheckResultCreate,
    CheckResultRead,
    CheckToolCreate,
    CheckToolRead,
)


def test_policy_pre_check_enums_have_expected_values() -> None:
    assert [item.value for item in CheckToolType] == [
        "metadata_lookup",
        "access_grant_check",
        "data_usage_profile_check",
        "source_status_check",
        "model_status_check",
        "capability_status_check",
    ]
    assert [item.value for item in CheckToolStatus] == [
        "active",
        "disabled",
        "retired",
    ]
    assert [item.value for item in CheckResultTargetType] == [
        "source",
        "capability",
        "model_asset",
        "access_grant",
        "data_usage_profile",
        "external",
    ]
    assert [item.value for item in CheckResultOutcome] == [
        "pass",
        "fail",
        "unknown",
        "error",
        "not_applicable",
    ]
    assert [item.value for item in CheckResultConfidence] == [
        "high",
        "medium",
        "low",
        "unknown",
    ]


def test_check_tool_create_schema_accepts_valid_values() -> None:
    check_tool = CheckToolCreate(**check_tool_payload())

    assert check_tool.name == "data_usage_profile_checker"
    assert check_tool.tool_type is CheckToolType.DATA_USAGE_PROFILE_CHECK
    assert check_tool.status is CheckToolStatus.ACTIVE
    assert check_tool.owner_type is OwnerType.TEAM
    assert check_tool.metadata == {"source": "internal_metadata"}


def test_check_result_create_schema_accepts_valid_values() -> None:
    check_result = CheckResultCreate(**check_result_payload())

    assert check_result.target_type is CheckResultTargetType.DATA_USAGE_PROFILE
    assert check_result.outcome is CheckResultOutcome.PASS
    assert check_result.confidence is CheckResultConfidence.HIGH
    assert check_result.metadata == {
        "data_usage_profile_id": "profile:123",
        "purpose": "customer_support_answering",
    }


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("tool_type", "scanner"),
        ("status", "draft"),
        ("owner_type", "person"),
    ],
)
def test_check_tool_create_schema_rejects_invalid_enum_values(
    field: str,
    value: str,
) -> None:
    payload = check_tool_payload()
    payload[field] = value

    with pytest.raises(ValidationError):
        CheckToolCreate(**payload)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("target_type", "document"),
        ("outcome", "certified"),
        ("confidence", "0.92"),
    ],
)
def test_check_result_create_schema_rejects_invalid_enum_values(
    field: str,
    value: str,
) -> None:
    payload = check_result_payload()
    payload[field] = value

    with pytest.raises(ValidationError):
        CheckResultCreate(**payload)


def test_check_tool_create_schema_rejects_blank_name() -> None:
    payload = check_tool_payload()
    payload["name"] = " "

    with pytest.raises(ValidationError, match="non-empty"):
        CheckToolCreate(**payload)


def test_check_result_create_schema_rejects_blank_summary() -> None:
    payload = check_result_payload()
    payload["summary"] = " "

    with pytest.raises(ValidationError, match="non-empty"):
        CheckResultCreate(**payload)


def test_check_tool_schema_rejects_unsafe_metadata_keys() -> None:
    payload = check_tool_payload()
    payload["metadata"] = {"api_key_ref": "do-not-store"}

    with pytest.raises(ValidationError):
        CheckToolCreate(**payload)


def test_check_result_schema_rejects_unsafe_metadata_keys() -> None:
    payload = check_result_payload()
    payload["metadata"] = {"raw_payload_ref": "do-not-store"}

    with pytest.raises(ValidationError):
        CheckResultCreate(**payload)


def test_check_tool_read_schema_filters_unsafe_metadata_from_records() -> None:
    timestamp = datetime.now(UTC)
    check_tool_record = SimpleNamespace(
        id=uuid4(),
        name="data_usage_profile_checker",
        description=None,
        tool_type=CheckToolType.DATA_USAGE_PROFILE_CHECK,
        status=CheckToolStatus.ACTIVE,
        owner_type=OwnerType.TEAM,
        owner_id="team:governance",
        owner_name="Governance",
        metadata_={"safe_label": "kept", "api_key": "do-not-export"},
        created_at=timestamp,
        updated_at=timestamp,
    )

    schema = CheckToolRead.model_validate(check_tool_record)

    assert schema.metadata == {"safe_label": "kept"}
    assert "metadata_" not in schema.model_dump()


def test_check_result_read_schema_filters_unsafe_metadata_from_records() -> None:
    timestamp = datetime.now(UTC)
    check_result_record = SimpleNamespace(
        id=uuid4(),
        check_tool_id=uuid4(),
        agent_id=uuid4(),
        run_id=uuid4(),
        trace_event_id=None,
        policy_decision_id=None,
        target_type=CheckResultTargetType.DATA_USAGE_PROFILE,
        target_id=uuid4(),
        outcome=CheckResultOutcome.PASS,
        confidence=CheckResultConfidence.HIGH,
        summary="Data Usage Profile allows purpose.",
        reason="Purpose is allowed.",
        metadata_={"safe_label": "kept", "scanner_payload": "do-not-export"},
        created_at=timestamp,
    )

    schema = CheckResultRead.model_validate(check_result_record)

    assert schema.metadata == {"safe_label": "kept"}
    assert "metadata_" not in schema.model_dump()


def test_check_tool_model_rejects_unsafe_metadata_keys() -> None:
    with pytest.raises(ValueError, match="unsafe key"):
        CheckTool(
            name="data_usage_profile_checker",
            tool_type=CheckToolType.DATA_USAGE_PROFILE_CHECK,
            status=CheckToolStatus.ACTIVE,
            owner_type=OwnerType.TEAM,
            owner_id="team:governance",
            owner_name="Governance",
            metadata_={"client_secret": "do-not-store"},
        )


def test_check_result_model_rejects_unsafe_metadata_keys() -> None:
    with pytest.raises(ValueError, match="unsafe key"):
        CheckResult(
            check_tool_id=uuid4(),
            target_type=CheckResultTargetType.DATA_USAGE_PROFILE,
            outcome=CheckResultOutcome.PASS,
            summary="Data Usage Profile allows purpose.",
            metadata_={"token": "do-not-store"},
        )


def test_policy_pre_check_tables_compile_for_postgresql() -> None:
    check_tool_ddl = str(
        CreateTable(CheckTool.__table__).compile(dialect=postgresql.dialect())
    )
    check_result_ddl = str(
        CreateTable(CheckResult.__table__).compile(dialect=postgresql.dialect())
    )

    assert "CREATE TABLE check_tools" in check_tool_ddl
    assert "check_tool_type" in check_tool_ddl
    assert "check_tool_status" in check_tool_ddl
    assert "check_tool_owner_type" in check_tool_ddl
    assert "metadata JSON DEFAULT '{}'" in check_tool_ddl
    assert "uq_check_tools_name" in check_tool_ddl
    assert "CREATE TABLE check_results" in check_result_ddl
    assert "check_tool_id UUID NOT NULL" in check_result_ddl
    assert "check_result_target_type" in check_result_ddl
    assert "check_result_outcome" in check_result_ddl
    assert "check_result_confidence" in check_result_ddl
    assert "metadata JSON DEFAULT '{}'" in check_result_ddl


def test_policy_pre_check_migration_declares_expected_tables() -> None:
    migration_path = (
        Path(__file__).resolve().parents[1]
        / "migrations"
        / "versions"
        / "202605260002_create_policy_pre_check_tables.py"
    )
    migration_text = migration_path.read_text(encoding="utf-8")

    assert 'revision: str = "202605260002"' in migration_text
    assert 'down_revision: str | None = "202605260001"' in migration_text
    assert '"check_tools"' in migration_text
    assert '"check_results"' in migration_text
    assert '"tool_type"' in migration_text
    assert '"outcome"' in migration_text
    assert '"policy_decision_id"' in migration_text
    assert '"metadata"' in migration_text


def check_tool_payload() -> dict[str, object]:
    return {
        "name": "data_usage_profile_checker",
        "description": "Checks declared Source usage metadata.",
        "tool_type": "data_usage_profile_check",
        "status": "active",
        "owner_type": "team",
        "owner_id": "team:governance",
        "owner_name": "Governance",
        "metadata": {"source": "internal_metadata"},
    }


def check_result_payload() -> dict[str, object]:
    return {
        "check_tool_id": str(uuid4()),
        "agent_id": str(uuid4()),
        "run_id": str(uuid4()),
        "trace_event_id": None,
        "policy_decision_id": None,
        "target_type": "data_usage_profile",
        "target_id": str(uuid4()),
        "outcome": "pass",
        "confidence": "high",
        "summary": "Data Usage Profile allows the requested purpose.",
        "reason": "Purpose is listed in allowed_purposes.",
        "metadata": {
            "data_usage_profile_id": "profile:123",
            "purpose": "customer_support_answering",
        },
    }
