from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine, select
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Session
from sqlalchemy.schema import CreateTable

from agent_governance_api.database import Base
from agent_governance_api.models import (
    CheckTool,
    CheckToolStatus,
    CheckToolType,
    OwnerType,
    Policy,
    PolicyCheckStep,
    PolicyCheckStepCheckType,
    PolicyCheckStepEvidenceRetention,
    PolicyCheckStepFailureBehavior,
    PolicyCheckStepStatus,
    PolicyCheckStepTargetSelector,
    PolicyRule,
    PolicyStatus,
)
from agent_governance_api.schemas import (
    PolicyCheckStepCreate,
    PolicyCheckStepRead,
    PolicyCheckStepUpdate,
)


def test_policy_check_step_enums_have_expected_values() -> None:
    assert [item.value for item in PolicyCheckStepCheckType] == [
        "access_grant_status",
        "data_usage_profile_status",
        "source_status",
        "source_classification",
        "capability_status",
        "model_asset_status",
        "model_provider_type",
    ]
    assert [item.value for item in PolicyCheckStepTargetSelector] == [
        "agent",
        "source_ids",
        "model_id",
        "capability_id",
        "access_grants",
    ]
    assert [item.value for item in PolicyCheckStepFailureBehavior] == [
        "record_only",
        "require_human_review",
        "fail_closed",
        "ignore_if_unavailable",
    ]
    assert [item.value for item in PolicyCheckStepStatus] == [
        "active",
        "disabled",
        "retired",
    ]
    assert [item.value for item in PolicyCheckStepEvidenceRetention] == [
        "decision_only",
        "evidence_bundle",
        "none",
    ]


def test_policy_check_step_create_schema_accepts_valid_values() -> None:
    policy_rule_id = uuid4()
    check_tool_id = uuid4()

    step = PolicyCheckStepCreate(
        **policy_check_step_payload(
            policy_rule_id=policy_rule_id,
            check_tool_id=check_tool_id,
        )
    )

    assert step.policy_rule_id == policy_rule_id
    assert step.check_tool_id == check_tool_id
    assert step.check_type is PolicyCheckStepCheckType.DATA_USAGE_PROFILE_STATUS
    assert step.target_selector is PolicyCheckStepTargetSelector.SOURCE_IDS
    assert step.failure_behavior is PolicyCheckStepFailureBehavior.REQUIRE_HUMAN_REVIEW
    assert step.status is PolicyCheckStepStatus.ACTIVE
    assert step.evidence_retention is PolicyCheckStepEvidenceRetention.EVIDENCE_BUNDLE
    assert step.metadata == {"purpose": "runtime_metadata_pre_check"}


@pytest.mark.parametrize(
    ("check_type", "target_selector"),
    [
        ("source_classification", "source_ids"),
        ("model_provider_type", "model_id"),
    ],
)
def test_policy_check_step_create_schema_accepts_metadata_only_check_types(
    check_type: str,
    target_selector: str,
) -> None:
    step = PolicyCheckStepCreate(
        **{
            **policy_check_step_payload(policy_rule_id=uuid4()),
            "check_type": check_type,
            "target_selector": target_selector,
            "check_tool_id": None,
        }
    )

    assert step.check_type.value == check_type
    assert step.target_selector.value == target_selector


def test_policy_check_step_update_schema_accepts_partial_updates() -> None:
    update = PolicyCheckStepUpdate(
        status="disabled",
        min_confidence=None,
        check_tool_id=None,
    )

    assert update.status is PolicyCheckStepStatus.DISABLED
    assert update.min_confidence is None
    assert update.check_tool_id is None


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("check_type", "secret_scan"),
        ("target_selector", "each_source"),
        ("failure_behavior", "execute_workflow"),
        ("status", "archived"),
        ("evidence_retention", "forever"),
    ],
)
def test_policy_check_step_schema_rejects_invalid_enum_values(
    field: str,
    value: str,
) -> None:
    payload = policy_check_step_payload(policy_rule_id=uuid4())
    payload[field] = value

    with pytest.raises(ValidationError):
        PolicyCheckStepCreate(**payload)


def test_policy_check_step_schema_rejects_unsupported_target_selector() -> None:
    payload = policy_check_step_payload(policy_rule_id=uuid4())
    payload["check_type"] = "source_status"
    payload["target_selector"] = "model_id"

    with pytest.raises(ValidationError, match="target_selector"):
        PolicyCheckStepCreate(**payload)


@pytest.mark.parametrize("min_confidence", [-0.1, 1.1])
def test_policy_check_step_schema_rejects_invalid_min_confidence(
    min_confidence: float,
) -> None:
    payload = policy_check_step_payload(policy_rule_id=uuid4())
    payload["min_confidence"] = min_confidence

    with pytest.raises(ValidationError):
        PolicyCheckStepCreate(**payload)


def test_policy_check_step_schema_rejects_unsafe_metadata() -> None:
    payload = policy_check_step_payload(policy_rule_id=uuid4())
    payload["metadata"] = {"raw_payload_ref": "do-not-store"}

    with pytest.raises(ValidationError):
        PolicyCheckStepCreate(**payload)


def test_policy_check_step_schema_rejects_extra_fields() -> None:
    payload = policy_check_step_payload(policy_rule_id=uuid4())
    payload["tool_name"] = "external_scanner"

    with pytest.raises(ValidationError):
        PolicyCheckStepCreate(**payload)


@pytest.mark.parametrize(
    "payload",
    [
        {"policy_rule_id": None},
        {"check_type": None},
        {"target_selector": None},
        {"required": None},
        {"failure_behavior": None},
        {"status": None},
        {"evidence_retention": None},
        {"metadata": None},
    ],
)
def test_policy_check_step_update_rejects_null_required_fields(
    payload: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        PolicyCheckStepUpdate(**payload)


def test_policy_check_step_read_schema_filters_unsafe_metadata_from_records() -> None:
    timestamp = datetime.now(UTC)
    step_record = SimpleNamespace(
        id=uuid4(),
        policy_rule_id=uuid4(),
        check_tool_id=None,
        check_type=PolicyCheckStepCheckType.DATA_USAGE_PROFILE_STATUS,
        target_selector=PolicyCheckStepTargetSelector.SOURCE_IDS,
        required=True,
        failure_behavior=PolicyCheckStepFailureBehavior.REQUIRE_HUMAN_REVIEW,
        min_confidence=0.8,
        status=PolicyCheckStepStatus.ACTIVE,
        evidence_retention=PolicyCheckStepEvidenceRetention.EVIDENCE_BUNDLE,
        metadata_={"safe_label": "kept", "scanner_payload": "do-not-export"},
        created_at=timestamp,
        updated_at=timestamp,
    )

    schema = PolicyCheckStepRead.model_validate(step_record)

    assert schema.metadata == {"safe_label": "kept"}
    assert "metadata_" not in schema.model_dump()


def test_policy_check_step_model_rejects_unsafe_metadata_keys() -> None:
    with pytest.raises(ValueError, match="unsafe key"):
        PolicyCheckStep(
            policy_rule_id=uuid4(),
            check_type=PolicyCheckStepCheckType.DATA_USAGE_PROFILE_STATUS,
            target_selector=PolicyCheckStepTargetSelector.SOURCE_IDS,
            required=True,
            failure_behavior=PolicyCheckStepFailureBehavior.REQUIRE_HUMAN_REVIEW,
            status=PolicyCheckStepStatus.ACTIVE,
            evidence_retention=PolicyCheckStepEvidenceRetention.EVIDENCE_BUNDLE,
            metadata_={"api_key_ref": "do-not-store"},
        )


def test_policy_check_step_table_compiles_for_postgresql() -> None:
    ddl = str(
        CreateTable(PolicyCheckStep.__table__).compile(dialect=postgresql.dialect())
    )

    assert "CREATE TABLE policy_check_steps" in ddl
    assert "policy_rule_id UUID NOT NULL" in ddl
    assert "check_tool_id UUID" in ddl
    assert "policy_check_step_type" in ddl
    assert "policy_check_step_target_selector" in ddl
    assert "policy_check_step_failure_behavior" in ddl
    assert "policy_check_step_status" in ddl
    assert "policy_check_step_evidence_retention" in ddl
    assert "min_confidence FLOAT" in ddl
    assert "metadata JSON DEFAULT '{}'" in ddl
    assert "FOREIGN KEY(policy_rule_id) REFERENCES policy_rules" in ddl
    assert "FOREIGN KEY(check_tool_id) REFERENCES check_tools" in ddl


def test_policy_check_step_migration_declares_expected_table() -> None:
    migration_path = (
        Path(__file__).resolve().parents[1]
        / "migrations"
        / "versions"
        / "202605280001_create_policy_check_steps_table.py"
    )
    migration_text = migration_path.read_text(encoding="utf-8")

    assert 'revision: str = "202605280001"' in migration_text
    assert 'down_revision: str | None = "202605260002"' in migration_text
    assert '"policy_check_steps"' in migration_text
    assert '"policy_rule_id"' in migration_text
    assert '"check_tool_id"' in migration_text
    assert '"check_type"' in migration_text
    assert '"target_selector"' in migration_text
    assert '"failure_behavior"' in migration_text
    assert '"min_confidence"' in migration_text
    assert '"metadata"' in migration_text


def test_policy_check_step_metadata_check_type_migration_declares_new_values() -> None:
    migration_path = (
        Path(__file__).resolve().parents[1]
        / "migrations"
        / "versions"
        / "202606180001_add_policy_check_step_metadata_types.py"
    )
    migration_text = migration_path.read_text(encoding="utf-8")

    assert "source_classification" in migration_text
    assert "model_provider_type" in migration_text
    assert "policy_check_step_type" in migration_text


def test_policy_check_step_persists_with_rule_and_check_tool_relationships() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    try:
        with Session(engine) as session:
            policy = Policy(
                name="Contextual source review",
                description=None,
                status=PolicyStatus.ACTIVE,
            )
            check_tool = CheckTool(
                name="data_usage_profile_checker",
                description="Checks declared Source usage metadata.",
                tool_type=CheckToolType.DATA_USAGE_PROFILE_CHECK,
                status=CheckToolStatus.ACTIVE,
                owner_type=OwnerType.TEAM,
                owner_id="team:governance",
                owner_name="Governance",
                metadata_={"source": "internal_metadata"},
            )
            session.add_all([policy, check_tool])
            session.flush()

            policy_rule = PolicyRule(
                policy_id=policy.id,
                name="Require profile review evidence",
                description=None,
                condition=(
                    '{"decision":"require_human_review",'
                    '"reason":"Profile evidence is required."}'
                ),
            )
            session.add(policy_rule)
            session.flush()

            step = PolicyCheckStep(
                policy_rule_id=policy_rule.id,
                check_tool_id=check_tool.id,
                check_type=PolicyCheckStepCheckType.DATA_USAGE_PROFILE_STATUS,
                target_selector=PolicyCheckStepTargetSelector.SOURCE_IDS,
                required=True,
                failure_behavior=(PolicyCheckStepFailureBehavior.REQUIRE_HUMAN_REVIEW),
                min_confidence=0.8,
                status=PolicyCheckStepStatus.ACTIVE,
                evidence_retention=PolicyCheckStepEvidenceRetention.EVIDENCE_BUNDLE,
                metadata_={"purpose": "runtime_metadata_pre_check"},
            )
            session.add(step)
            session.commit()

            saved_step = session.scalars(select(PolicyCheckStep)).one()

            assert saved_step.policy_rule_id == policy_rule.id
            assert saved_step.policy_rule.name == "Require profile review evidence"
            assert saved_step.check_tool_id == check_tool.id
            assert saved_step.check_tool is not None
            assert saved_step.check_tool.name == "data_usage_profile_checker"
            assert saved_step.metadata_ == {"purpose": "runtime_metadata_pre_check"}
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


def policy_check_step_payload(
    *,
    policy_rule_id: object,
    check_tool_id: object | None = None,
) -> dict[str, object]:
    return {
        "policy_rule_id": str(policy_rule_id),
        "check_tool_id": None if check_tool_id is None else str(check_tool_id),
        "check_type": "data_usage_profile_status",
        "target_selector": "source_ids",
        "required": True,
        "failure_behavior": "require_human_review",
        "min_confidence": 0.8,
        "status": "active",
        "evidence_retention": "evidence_bundle",
        "metadata": {"purpose": "runtime_metadata_pre_check"},
    }
