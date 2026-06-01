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
    ActorType,
    Policy,
    PolicyStatus,
    PolicyVersion,
    PolicyVersionStatus,
)
from agent_governance_api.schemas import (
    PolicyVersionCreate,
    PolicyVersionRead,
    PolicyVersionReviewRequest,
)


def test_policy_version_status_enum_has_expected_values() -> None:
    assert [item.value for item in PolicyVersionStatus] == [
        "draft",
        "under_review",
        "approved",
        "rejected",
        "active",
        "superseded",
        "archived",
    ]


def test_policy_version_create_schema_requires_change_summary() -> None:
    request = PolicyVersionCreate(change_summary="Initial reviewed policy bundle.")

    assert request.change_summary == "Initial reviewed policy bundle."

    with pytest.raises(ValidationError):
        PolicyVersionCreate(change_summary="   ")


def test_policy_version_review_schema_rejects_blank_note() -> None:
    request = PolicyVersionReviewRequest(review_note="Reviewed with owner.")

    assert request.review_note == "Reviewed with owner."

    with pytest.raises(ValidationError):
        PolicyVersionReviewRequest(review_note=" ")


def test_policy_version_read_schema_validates_from_model_like_record() -> None:
    timestamp = datetime.now(UTC)
    record = SimpleNamespace(
        id=uuid4(),
        policy_id=uuid4(),
        source_version_id=None,
        version_number=1,
        status=PolicyVersionStatus.DRAFT,
        change_summary="Snapshot current policy state.",
        policy_snapshot={"name": "Email policy", "status": "draft"},
        rule_snapshots=[{"name": "Email review rule"}],
        check_step_snapshots=[{"check_type": "source_status"}],
        created_by_actor_type=ActorType.DEVELOPMENT,
        created_by_actor_id="dev-placeholder",
        review_requested_by_actor_type=None,
        review_requested_by_actor_id=None,
        reviewed_by_actor_type=None,
        reviewed_by_actor_id=None,
        review_note=None,
        created_at=timestamp,
        updated_at=timestamp,
        submitted_at=None,
        approved_at=None,
        rejected_at=None,
        activated_at=None,
        superseded_at=None,
        archived_at=None,
    )

    schema = PolicyVersionRead.model_validate(record)

    assert schema.status is PolicyVersionStatus.DRAFT
    assert schema.policy_snapshot["name"] == "Email policy"
    assert schema.created_by_actor_type is ActorType.DEVELOPMENT


def test_policy_version_model_rejects_unsafe_snapshot_keys() -> None:
    with pytest.raises(ValueError, match="check_step_snapshots contains unsafe"):
        PolicyVersion(
            policy_id=uuid4(),
            version_number=1,
            status=PolicyVersionStatus.DRAFT,
            change_summary="Unsafe metadata should be rejected.",
            policy_snapshot={"name": "Email policy"},
            rule_snapshots=[],
            check_step_snapshots=[
                {
                    "check_type": "source_status",
                    "metadata": {"raw_payload_ref": "do-not-store"},
                }
            ],
            created_by_actor_type=ActorType.DEVELOPMENT,
            created_by_actor_id="dev-placeholder",
        )


def test_policy_version_table_compiles_for_postgresql() -> None:
    ddl = str(
        CreateTable(PolicyVersion.__table__).compile(dialect=postgresql.dialect())
    )

    assert "CREATE TABLE policy_versions" in ddl
    assert "policy_id UUID NOT NULL" in ddl
    assert "source_version_id UUID" in ddl
    assert "version_number INTEGER NOT NULL" in ddl
    assert "policy_version_status" in ddl
    assert "policy_snapshot JSON DEFAULT '{}'" in ddl
    assert "rule_snapshots JSON DEFAULT '[]'" in ddl
    assert "check_step_snapshots JSON DEFAULT '[]'" in ddl
    assert "policy_version_created_actor_type" in ddl
    assert "FOREIGN KEY(policy_id) REFERENCES policies" in ddl
    assert "FOREIGN KEY(source_version_id) REFERENCES policy_versions" in ddl
    assert "uq_policy_versions_policy_version_number" in ddl


def test_policy_version_migration_declares_expected_table() -> None:
    migration_path = (
        Path(__file__).resolve().parents[1]
        / "migrations"
        / "versions"
        / "202606010001_create_policy_versions_table.py"
    )
    migration_text = migration_path.read_text(encoding="utf-8")

    assert 'revision: str = "202606010001"' in migration_text
    assert 'down_revision: str | None = "202605280001"' in migration_text
    assert '"policy_versions"' in migration_text
    assert '"policy_id"' in migration_text
    assert '"source_version_id"' in migration_text
    assert '"version_number"' in migration_text
    assert '"policy_snapshot"' in migration_text
    assert '"rule_snapshots"' in migration_text
    assert '"check_step_snapshots"' in migration_text
    assert '"policy_version_status"' in migration_text


def test_policy_decision_policy_version_migration_declares_expected_reference() -> None:
    migration_path = (
        Path(__file__).resolve().parents[1]
        / "migrations"
        / "versions"
        / "202606010002_add_policy_decision_policy_version_reference.py"
    )
    migration_text = migration_path.read_text(encoding="utf-8")

    assert 'revision: str = "202606010002"' in migration_text
    assert 'down_revision: str | None = "202606010001"' in migration_text
    assert '"policy_decisions"' in migration_text
    assert '"policy_version_id"' in migration_text
    assert '"fk_policy_decisions_policy_version"' in migration_text
    assert '"policy_versions"' in migration_text


def test_policy_version_persists_with_policy_relationship() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    try:
        with Session(engine) as session:
            policy = Policy(
                name="Email review policy",
                description="Governed email actions.",
                status=PolicyStatus.DRAFT,
            )
            session.add(policy)
            session.flush()
            version = PolicyVersion(
                policy_id=policy.id,
                version_number=1,
                status=PolicyVersionStatus.DRAFT,
                change_summary="Initial policy snapshot.",
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
            session.add(version)
            session.commit()

            saved_version = session.scalars(select(PolicyVersion)).one()

            assert saved_version.policy_id == policy.id
            assert saved_version.policy.name == "Email review policy"
            assert saved_version.status is PolicyVersionStatus.DRAFT
            assert saved_version.policy_snapshot["status"] == "draft"
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()
