import json
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy import event as sqlalchemy_event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from agent_governance_api.activity import build_agent_activity
from agent_governance_api.config import get_settings
from agent_governance_api.database import Base, get_db_session
from agent_governance_api.evidence import build_agent_evidence_bundle
from agent_governance_api.full_stack_demo_seed import (
    DEMO_AGENT_ID,
    DEMO_HUMAN_APPROVAL_AUDIT_LOG_ID,
    DEMO_HUMAN_APPROVAL_ID,
    DEMO_POLICY_DECISION_ID,
    DEMO_POLICY_ID,
    DEMO_POLICY_RULE_ID,
    DEMO_TOOL_NAME,
    METADATA_PRE_CHECK_DEMO_AGENT_ID,
    METADATA_PRE_CHECK_DEMO_CAPABILITY_ID,
    METADATA_PRE_CHECK_DEMO_MODEL_ID,
    METADATA_PRE_CHECK_DEMO_POLICY_VERSION_ID,
    METADATA_PRE_CHECK_DEMO_SOURCE_ID,
    format_full_stack_demo_seed_result,
    metadata_pre_check_demo_runtime_payload,
    seed_full_stack_demo,
)
from agent_governance_api.main import app
from agent_governance_api.models import (
    Agent,
    AgentRunRecord,
    AuditLog,
    CheckResult,
    CheckResultOutcome,
    CheckResultTargetType,
    DataSource,
    DataUsageClassification,
    DataUsageProfile,
    HumanApproval,
    HumanApprovalStatus,
    ModelAsset,
    ModelProvider,
    Policy,
    PolicyCheckStep,
    PolicyCheckStepCheckType,
    PolicyDecision,
    PolicyDecisionValue,
    PolicyRule,
    PolicyStatus,
    PolicyVersion,
    PolicyVersionStatus,
    TraceEventRecord,
    TraceEventType,
)

API_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture()
def session() -> Iterator[Session]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @sqlalchemy_event.listens_for(engine, "connect")
    def enable_foreign_keys(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    session_factory = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )
    try:
        with session_factory() as db_session:
            yield db_session
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture()
def api_client() -> Iterator[tuple[TestClient, sessionmaker[Session]]]:
    get_settings.cache_clear()
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @sqlalchemy_event.listens_for(engine, "connect")
    def enable_foreign_keys(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    testing_session_factory = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )

    def override_get_db_session() -> Iterator[Session]:
        with testing_session_factory() as db_session:
            yield db_session

    app.dependency_overrides[get_db_session] = override_get_db_session
    try:
        with TestClient(app) as client:
            yield client, testing_session_factory
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_seed_full_stack_demo_creates_safe_backend_demo_chain(
    session: Session,
) -> None:
    result = seed_full_stack_demo(session, dry_run=False)

    assert result.created[:9] == (
        "agent",
        "policy",
        "policy_rule",
        "agent_run",
        "trace_event",
        "policy_decision",
        "human_approval",
        "agent_audit_log",
        "human_approval_audit_log",
    )
    assert "metadata_pre_check_policy_version" in result.created
    assert result.reused == ()

    agent = session.get(Agent, DEMO_AGENT_ID)
    assert agent is not None
    assert agent.owner_contact_email is None

    policy = session.get(Policy, DEMO_POLICY_ID)
    assert policy is not None
    assert policy.status is PolicyStatus.ACTIVE

    rule = session.get(PolicyRule, DEMO_POLICY_RULE_ID)
    assert rule is not None
    assert DEMO_TOOL_NAME in rule.condition

    trace_event = session.scalar(select(TraceEventRecord))
    assert trace_event is not None
    assert trace_event.event_type is TraceEventType.TOOL_CALL_REQUESTED
    assert trace_event.metadata_ == {
        "tool_name": DEMO_TOOL_NAME,
        "action_type": "demo_review_action",
        "purpose": "local_full_stack_demo",
    }

    decision = session.get(PolicyDecision, DEMO_POLICY_DECISION_ID)
    assert decision is not None
    assert decision.policy_id == DEMO_POLICY_ID
    assert decision.rule_id == DEMO_POLICY_RULE_ID
    assert decision.trace_event_id == trace_event.id
    assert decision.decision is PolicyDecisionValue.REQUIRE_HUMAN_REVIEW

    approval = session.get(HumanApproval, DEMO_HUMAN_APPROVAL_ID)
    assert approval is not None
    assert approval.status is HumanApprovalStatus.PENDING
    assert approval.policy_decision_id == DEMO_POLICY_DECISION_ID

    approval_audit_log = session.get(AuditLog, DEMO_HUMAN_APPROVAL_AUDIT_LOG_ID)
    assert approval_audit_log is not None
    assert approval_audit_log.metadata_ == {
        "agent_id": str(DEMO_AGENT_ID),
        "policy_decision_id": str(DEMO_POLICY_DECISION_ID),
        "status": "pending",
    }


def test_seed_full_stack_demo_populates_activity_and_evidence_bundle(
    session: Session,
) -> None:
    seed_full_stack_demo(session, dry_run=False)
    agent = session.get(Agent, DEMO_AGENT_ID)
    assert agent is not None

    activity_items = build_agent_activity(session, agent=agent)
    assert {item.type for item in activity_items} == {
        "trace_event",
        "policy_decision",
        "human_approval",
        "audit_log",
    }

    evidence_bundle = build_agent_evidence_bundle(session, agent=agent)
    assert evidence_bundle.agent.id == DEMO_AGENT_ID
    assert len(evidence_bundle.agent_runs) == 1
    assert len(evidence_bundle.trace_events) == 1
    assert len(evidence_bundle.policy_decisions) == 1
    assert len(evidence_bundle.human_approvals) == 1
    assert len(evidence_bundle.audit_logs) == 2
    assert evidence_bundle.policy_decisions[0].policy is not None
    assert evidence_bundle.policy_decisions[0].rule is not None


def test_seed_full_stack_demo_is_idempotent(session: Session) -> None:
    seed_full_stack_demo(session, dry_run=False)
    result = seed_full_stack_demo(session, dry_run=False)

    assert result.created == ()
    assert result.reused[:9] == (
        "agent",
        "policy",
        "policy_rule",
        "agent_run",
        "trace_event",
        "policy_decision",
        "human_approval",
        "agent_audit_log",
        "human_approval_audit_log",
    )
    assert "metadata_pre_check_policy_version" in result.reused
    assert session.scalar(select(func.count()).select_from(Agent)) == 2
    assert session.scalar(select(func.count()).select_from(Policy)) == 2
    assert session.scalar(select(func.count()).select_from(PolicyRule)) == 2
    assert session.scalar(select(func.count()).select_from(PolicyVersion)) == 1
    assert session.scalar(select(func.count()).select_from(PolicyCheckStep)) == 7
    assert session.scalar(select(func.count()).select_from(AgentRunRecord)) == 1
    assert session.scalar(select(func.count()).select_from(TraceEventRecord)) == 1
    assert session.scalar(select(func.count()).select_from(PolicyDecision)) == 1
    assert session.scalar(select(func.count()).select_from(HumanApproval)) == 1
    assert session.scalar(select(func.count()).select_from(AuditLog)) == 2


def test_seed_full_stack_demo_creates_metadata_pre_check_scenario(
    session: Session,
) -> None:
    result = seed_full_stack_demo(session, dry_run=False)

    agent = session.get(Agent, METADATA_PRE_CHECK_DEMO_AGENT_ID)
    assert agent is not None
    assert agent.environment.value == "production"

    source = session.get(DataSource, METADATA_PRE_CHECK_DEMO_SOURCE_ID)
    assert source is not None
    profile = session.scalar(
        select(DataUsageProfile).where(DataUsageProfile.source_id == source.id)
    )
    assert profile is not None
    assert profile.data_classification is DataUsageClassification.CONFIDENTIAL
    assert profile.contains_sensitive_data is True

    model = session.get(ModelAsset, METADATA_PRE_CHECK_DEMO_MODEL_ID)
    assert model is not None
    assert model.provider is ModelProvider.OPENAI

    version = session.get(PolicyVersion, result.metadata_pre_check_policy_version_id)
    assert version is not None
    assert version.status is PolicyVersionStatus.ACTIVE
    assert version.policy_id == result.metadata_pre_check_policy_id
    assert version.rule_snapshots
    assert len(version.check_step_snapshots) == 7
    check_types = {snapshot["check_type"] for snapshot in version.check_step_snapshots}
    assert {
        PolicyCheckStepCheckType.SOURCE_CLASSIFICATION.value,
        PolicyCheckStepCheckType.MODEL_PROVIDER_TYPE.value,
        PolicyCheckStepCheckType.ACCESS_GRANT_STATUS.value,
    } <= check_types

    condition = version.rule_snapshots[0]["condition"]
    assert isinstance(condition, str)
    assert "model_provider_type" in condition
    assert "require_human_review" in condition


def test_seed_full_stack_demo_dry_run_does_not_write(session: Session) -> None:
    result = seed_full_stack_demo(session, dry_run=True)

    assert result.dry_run is True
    assert result.created
    assert session.scalar(select(func.count()).select_from(Agent)) == 0
    assert "Run again with --apply" in format_full_stack_demo_seed_result(result)


def test_seed_full_stack_demo_records_do_not_include_unsafe_metadata_keys(
    session: Session,
) -> None:
    seed_full_stack_demo(session, dry_run=False)

    unsafe_parts = ("secret", "token", "credential", "authorization", "raw_payload")
    metadata_values = [
        *session.scalars(select(AgentRunRecord.metadata_)).all(),
        *session.scalars(select(TraceEventRecord.metadata_)).all(),
        *session.scalars(select(AuditLog.metadata_)).all(),
    ]
    metadata_text = repr(metadata_values).lower()
    assert not any(part in metadata_text for part in unsafe_parts)


def test_metadata_pre_check_demo_runtime_flow_creates_review_evidence(
    api_client: tuple[TestClient, sessionmaker[Session]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AGCP_RUNTIME_METADATA_PRE_CHECKS_ENABLED", "true")
    get_settings.cache_clear()
    client, session_factory = api_client
    with session_factory() as db_session:
        seed_full_stack_demo(db_session, dry_run=False)

    response = client.post(
        "/runtime/tool-calls/decision",
        json=metadata_pre_check_demo_runtime_payload(),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["decision"] == "require_human_review"
    assert body["proceed"] is False
    assert body["human_approval_id"] is not None

    with session_factory() as db_session:
        [policy_decision] = db_session.scalars(
            select(PolicyDecision).where(
                PolicyDecision.agent_id == METADATA_PRE_CHECK_DEMO_AGENT_ID,
            )
        ).all()
        assert policy_decision.policy_version_id == (
            METADATA_PRE_CHECK_DEMO_POLICY_VERSION_ID
        )

        [approval] = db_session.scalars(
            select(HumanApproval).where(
                HumanApproval.policy_decision_id == policy_decision.id,
            )
        ).all()
        assert approval.status is HumanApprovalStatus.PENDING

        check_results = db_session.scalars(
            select(CheckResult).where(
                CheckResult.agent_id == METADATA_PRE_CHECK_DEMO_AGENT_ID,
            )
        ).all()
        check_types = {
            result.metadata_["policy_check_step_check_type"] for result in check_results
        }
        assert {
            "source_status",
            "source_classification",
            "data_usage_profile_status",
            "capability_status",
            "model_asset_status",
            "model_provider_type",
            "access_grant_status",
        } <= check_types

        model_provider_results = [
            result
            for result in check_results
            if result.metadata_.get("policy_check_step_check_type")
            == "model_provider_type"
        ]
        assert len(model_provider_results) == 1
        model_provider_result = model_provider_results[0]
        assert model_provider_result.outcome is CheckResultOutcome.PASS
        assert model_provider_result.target_type is CheckResultTargetType.MODEL_ASSET
        assert model_provider_result.target_id == METADATA_PRE_CHECK_DEMO_MODEL_ID
        assert model_provider_result.policy_decision_id == policy_decision.id
        assert model_provider_result.metadata_["policy_version_id"] == (
            str(METADATA_PRE_CHECK_DEMO_POLICY_VERSION_ID)
        )
        assert model_provider_result.metadata_["model_provider"] == "openai"
        assert model_provider_result.metadata_["model_provider_type"] == "external"

        classification_results = [
            result
            for result in check_results
            if result.metadata_.get("policy_check_step_check_type")
            == "source_classification"
        ]
        assert len(classification_results) == 1
        classification_result = classification_results[0]
        assert classification_result.target_type is (
            CheckResultTargetType.DATA_USAGE_PROFILE
        )
        assert classification_result.outcome is CheckResultOutcome.PASS
        assert classification_result.metadata_["data_classification"] == "confidential"
        assert "raw_content" not in repr(classification_result.metadata_).lower()
        assert "prompt" not in repr(classification_result.metadata_).lower()

        agent = db_session.get(Agent, METADATA_PRE_CHECK_DEMO_AGENT_ID)
        assert agent is not None
        evidence_bundle = build_agent_evidence_bundle(db_session, agent=agent)
        evidence_check_types = {
            item.check_type for item in evidence_bundle.check_results
        }
        assert "source_classification" in evidence_check_types
        assert "model_provider_type" in evidence_check_types
        assert any(
            item.policy_version_id == METADATA_PRE_CHECK_DEMO_POLICY_VERSION_ID
            for item in evidence_bundle.check_results
        )


def test_seed_full_stack_demo_script_supports_direct_execution_help() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/seed_full_stack_demo.py", "--help"],
        cwd=API_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "Seed safe local-only demo data" in result.stdout
    assert "ModuleNotFoundError" not in result.stderr


def test_seed_full_stack_demo_script_prints_runtime_payload_json_only() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "scripts/seed_full_stack_demo.py",
            "--print-runtime-payload",
        ],
        cwd=API_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert result.stderr == ""
    payload = json.loads(result.stdout)
    assert result.stdout.strip().startswith("{")
    assert result.stdout.strip().endswith("}")
    assert "Local full-stack demo seed" not in result.stdout
    assert "ModuleNotFoundError" not in result.stderr
    assert payload["agent_id"] == str(METADATA_PRE_CHECK_DEMO_AGENT_ID)
    assert payload["capability_id"] == str(METADATA_PRE_CHECK_DEMO_CAPABILITY_ID)
    assert payload["source_ids"] == [str(METADATA_PRE_CHECK_DEMO_SOURCE_ID)]
    assert payload["model_id"] == str(METADATA_PRE_CHECK_DEMO_MODEL_ID)
    assert payload["tool_name"] == "vectorize_source"
    assert payload["mode"] == "simulation"
    assert payload["metadata"] == {"demo": "metadata_pre_check"}
