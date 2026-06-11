from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine, select
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.schema import CreateIndex, CreateTable

from agent_governance_api.database import Base
from agent_governance_api.models import (
    ActorType,
    Policy,
    PolicyStatus,
    PolicyVersion,
    PolicyVersionReviewRequest,
    PolicyVersionReviewRequestStatus,
    PolicyVersionStatus,
)
from agent_governance_api.schemas import (
    PolicyVersionCreate,
    PolicyVersionDraftPayload,
    PolicyVersionRead,
    PolicyVersionReviewAssignmentRequest,
    PolicyVersionReviewDecisionRequest,
    PolicyVersionReviewRequestCreate,
    PolicyVersionReviewRequestRead,
)
from agent_governance_api.schemas import (
    PolicyVersionReviewRequest as PolicyVersionLifecycleReviewRequest,
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


def test_policy_version_review_request_status_enum_has_expected_values() -> None:
    assert [item.value for item in PolicyVersionReviewRequestStatus] == [
        "pending",
        "approved",
        "rejected",
        "canceled",
    ]


def test_policy_version_create_schema_requires_change_summary() -> None:
    request = PolicyVersionCreate(change_summary="Initial reviewed policy bundle.")

    assert request.change_summary == "Initial reviewed policy bundle."

    with pytest.raises(ValidationError):
        PolicyVersionCreate(change_summary="   ")


def test_policy_version_draft_schema_validates_editor_snapshot() -> None:
    request = PolicyVersionDraftPayload(
        change_summary="Policy Studio draft.",
        policy_snapshot={
            "name": "Policy Studio guard",
            "description": "Drafted in Policy Studio.",
            "status": "draft",
        },
        rule_snapshots=[
            {
                "name": "Policy Studio rule",
                "description": "Compiled from DSL.",
                "condition": (
                    '{"decision":"deny",'
                    '"reason":"Blocked by local draft.",'
                    '"tool_name":"send_email"}'
                ),
            }
        ],
    )

    assert request.change_summary == "Policy Studio draft."
    assert request.policy_snapshot is not None
    assert request.policy_snapshot.name == "Policy Studio guard"
    assert request.rule_snapshots[0].name == "Policy Studio rule"

    with pytest.raises(ValidationError):
        PolicyVersionDraftPayload(
            change_summary="Policy Studio draft.",
            rule_snapshots=[],
        )

    with pytest.raises(ValidationError):
        PolicyVersionDraftPayload(
            change_summary="Policy Studio draft.",
            rule_snapshots=[
                {
                    "name": "Broken rule",
                    "condition": '{"decision":"deny","tool_name":"send_email"}',
                }
            ],
        )


def test_policy_version_review_schema_rejects_blank_note() -> None:
    request = PolicyVersionLifecycleReviewRequest(review_note="Reviewed with owner.")

    assert request.review_note == "Reviewed with owner."

    with pytest.raises(ValidationError):
        PolicyVersionLifecycleReviewRequest(review_note=" ")


def test_policy_version_review_request_schemas_validate_notes() -> None:
    create_request = PolicyVersionReviewRequestCreate(
        request_note="Ready for review.",
    )
    assignment_request = PolicyVersionReviewAssignmentRequest(
        assigned_reviewer_actor_type=ActorType.USER,
        assigned_reviewer_actor_id="user:reviewer-1",
        assigned_reviewer_name="Reviewer One",
        assignment_note="Please review the rollback draft.",
    )
    decision_request = PolicyVersionReviewDecisionRequest(
        decision_note="Approved for activation planning.",
    )
    timestamp = datetime.now(UTC)
    read_record = SimpleNamespace(
        id=uuid4(),
        policy_version_id=uuid4(),
        policy_id=uuid4(),
        status=PolicyVersionReviewRequestStatus.PENDING,
        requested_by_actor_type=ActorType.DEVELOPMENT,
        requested_by_actor_id="dev-placeholder",
        reviewer_actor_type=None,
        reviewer_actor_id=None,
        assigned_reviewer_actor_type=ActorType.USER,
        assigned_reviewer_actor_id="user:reviewer-1",
        assigned_reviewer_name="Reviewer One",
        assigned_at=timestamp,
        assigned_by_actor_type=ActorType.USER,
        assigned_by_actor_id="user:review-lead",
        request_note="Ready for review.",
        decision_note=None,
        created_at=timestamp,
        decided_at=None,
        policy_name="Email policy",
        policy_version_number=1,
    )

    read_schema = PolicyVersionReviewRequestRead.model_validate(read_record)

    assert create_request.request_note == "Ready for review."
    assert assignment_request.assigned_reviewer_actor_id == "user:reviewer-1"
    assert assignment_request.assigned_reviewer_name == "Reviewer One"
    assert decision_request.decision_note == "Approved for activation planning."
    assert read_schema.status is PolicyVersionReviewRequestStatus.PENDING
    assert read_schema.assigned_reviewer_actor_id == "user:reviewer-1"
    assert read_schema.assigned_reviewer_name == "Reviewer One"
    assert read_schema.assigned_by_actor_id == "user:review-lead"
    assert read_schema.policy_name == "Email policy"
    assert read_schema.policy_version_number == 1

    with pytest.raises(ValidationError):
        PolicyVersionReviewRequestCreate(request_note=" ")

    with pytest.raises(ValidationError):
        PolicyVersionReviewAssignmentRequest(
            assigned_reviewer_actor_type=ActorType.USER,
            assigned_reviewer_actor_id=" ",
        )

    with pytest.raises(ValidationError):
        PolicyVersionReviewAssignmentRequest(
            assigned_reviewer_actor_type=ActorType.USER,
            assigned_reviewer_actor_id="user:reviewer-1",
            assignment_note=" ",
        )

    with pytest.raises(ValidationError):
        PolicyVersionReviewDecisionRequest(decision_note=" ")


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


def test_policy_version_single_active_index_compiles_for_postgresql() -> None:
    index = next(
        item
        for item in PolicyVersion.__table__.indexes
        if item.name == "uq_policy_versions_one_active_per_policy"
    )
    ddl = str(CreateIndex(index).compile(dialect=postgresql.dialect()))

    assert "CREATE UNIQUE INDEX uq_policy_versions_one_active_per_policy" in ddl
    assert "ON policy_versions (policy_id)" in ddl
    assert "WHERE status = 'active'" in ddl


def test_policy_version_review_request_table_compiles_for_postgresql() -> None:
    ddl = str(
        CreateTable(PolicyVersionReviewRequest.__table__).compile(
            dialect=postgresql.dialect()
        )
    )

    assert "CREATE TABLE policy_version_review_requests" in ddl
    assert "policy_version_id UUID NOT NULL" in ddl
    assert "policy_id UUID NOT NULL" in ddl
    assert "policy_version_review_request_status" in ddl
    assert "policy_version_review_requested_actor_type" in ddl
    assert "policy_version_review_reviewer_actor_type" in ddl
    assert "policy_version_review_assigned_actor_type" in ddl
    assert "policy_version_review_assigned_by_actor_type" in ddl
    assert "assigned_reviewer_actor_id VARCHAR(255)" in ddl
    assert "assigned_reviewer_name VARCHAR(255)" in ddl
    assert "assigned_at TIMESTAMP WITH TIME ZONE" in ddl
    assert "assigned_by_actor_id VARCHAR(255)" in ddl
    assert "request_note TEXT" in ddl
    assert "decision_note TEXT" in ddl
    assert "decided_at TIMESTAMP WITH TIME ZONE" in ddl
    assert "FOREIGN KEY(policy_version_id) REFERENCES policy_versions" in ddl
    assert "FOREIGN KEY(policy_id) REFERENCES policies" in ddl


def test_policy_version_review_request_pending_index_compiles_for_postgresql() -> None:
    index = next(
        item
        for item in PolicyVersionReviewRequest.__table__.indexes
        if item.name == "uq_policy_version_review_requests_one_pending_per_version"
    )
    ddl = str(CreateIndex(index).compile(dialect=postgresql.dialect()))

    assert (
        "CREATE UNIQUE INDEX uq_policy_version_review_requests_one_pending_per_version"
        in ddl
    )
    assert "ON policy_version_review_requests (policy_version_id)" in ddl
    assert "WHERE status = 'pending'" in ddl


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


def test_policy_version_single_active_guard_migration_declares_expected_index() -> None:
    migration_path = (
        Path(__file__).resolve().parents[1]
        / "migrations"
        / "versions"
        / "202606090001_add_policy_version_single_active_guard.py"
    )
    migration_text = migration_path.read_text(encoding="utf-8")

    assert 'revision: str = "202606090001"' in migration_text
    assert 'down_revision: str | None = "202606010002"' in migration_text
    assert '"uq_policy_versions_one_active_per_policy"' in migration_text
    assert '"policy_versions"' in migration_text
    assert '["policy_id"]' in migration_text
    assert "unique=True" in migration_text
    assert "postgresql_where=sa.text(\"status = 'active'\")" in migration_text


def test_policy_version_review_request_migration_declares_expected_table() -> None:
    migration_path = (
        Path(__file__).resolve().parents[1]
        / "migrations"
        / "versions"
        / "202606090002_create_policy_version_review_requests.py"
    )
    migration_text = migration_path.read_text(encoding="utf-8")

    assert 'revision: str = "202606090002"' in migration_text
    assert 'down_revision: str | None = "202606090001"' in migration_text
    assert '"policy_version_review_requests"' in migration_text
    assert '"policy_version_id"' in migration_text
    assert '"policy_id"' in migration_text
    assert '"policy_version_review_request_status"' in migration_text
    assert '"policy_version_review_requested_actor_type"' in migration_text
    assert '"policy_version_review_reviewer_actor_type"' in migration_text
    assert (
        '"uq_policy_version_review_requests_one_pending_per_version"' in migration_text
    )


def test_policy_version_review_assignment_migration_declares_expected_fields() -> None:
    migration_path = (
        Path(__file__).resolve().parents[1]
        / "migrations"
        / "versions"
        / "202606090003_add_policy_review_assignment_fields.py"
    )
    migration_text = migration_path.read_text(encoding="utf-8")

    assert 'revision: str = "202606090003"' in migration_text
    assert 'down_revision: str | None = "202606090002"' in migration_text
    assert '"policy_version_review_requests"' in migration_text
    assert '"assigned_reviewer_actor_type"' in migration_text
    assert '"policy_version_review_assigned_actor_type"' in migration_text
    assert '"assigned_reviewer_actor_id"' in migration_text
    assert '"assigned_reviewer_name"' in migration_text
    assert '"assigned_at"' in migration_text
    assert '"assigned_by_actor_type"' in migration_text
    assert '"policy_version_review_assigned_by_actor_type"' in migration_text
    assert '"assigned_by_actor_id"' in migration_text


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


def test_policy_version_single_active_guard_rejects_duplicate_active_versions() -> None:
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
            session.add(
                policy_version_record(
                    policy=policy,
                    version_number=1,
                    status=PolicyVersionStatus.ACTIVE,
                )
            )
            session.add(
                policy_version_record(
                    policy=policy,
                    version_number=2,
                    status=PolicyVersionStatus.ACTIVE,
                )
            )

            with pytest.raises(IntegrityError):
                session.commit()
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_single_active_guard_allows_active_versions_for_different_policies() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    try:
        with Session(engine) as session:
            first_policy = Policy(
                name="Email review policy",
                description="Governed email actions.",
                status=PolicyStatus.DRAFT,
            )
            second_policy = Policy(
                name="Payment review policy",
                description="Governed payment actions.",
                status=PolicyStatus.DRAFT,
            )
            session.add_all([first_policy, second_policy])
            session.flush()
            session.add(
                policy_version_record(
                    policy=first_policy,
                    version_number=1,
                    status=PolicyVersionStatus.ACTIVE,
                )
            )
            session.add(
                policy_version_record(
                    policy=second_policy,
                    version_number=1,
                    status=PolicyVersionStatus.ACTIVE,
                )
            )
            session.commit()

            versions = list(session.scalars(select(PolicyVersion)).all())
            assert len(versions) == 2
            assert {version.policy_id for version in versions} == {
                first_policy.id,
                second_policy.id,
            }
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


def policy_version_record(
    *,
    policy: Policy,
    version_number: int,
    status: PolicyVersionStatus,
) -> PolicyVersion:
    return PolicyVersion(
        policy_id=policy.id,
        version_number=version_number,
        status=status,
        change_summary="Reviewed policy snapshot.",
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
        activated_at=datetime.now(UTC)
        if status is PolicyVersionStatus.ACTIVE
        else None,
    )
