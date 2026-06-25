import json
from collections.abc import Callable, Iterator
from copy import deepcopy
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy import event as sqlalchemy_event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import agent_governance_api.runtime_gateway_api as runtime_gateway_api
from agent_governance_api.auth import (
    ActorContext,
    get_current_actor,
    hash_service_actor_api_key,
)
from agent_governance_api.config import get_settings
from agent_governance_api.database import Base, get_db_session
from agent_governance_api.main import app
from agent_governance_api.models import (
    AccessGrant,
    AccessGrantStatus,
    AccessGrantSubjectType,
    AccessGrantTargetType,
    AccessGrantType,
    ActorType,
    Agent,
    AgentRunRecord,
    AgentStatus,
    AuditLog,
    Capability,
    CapabilityStatus,
    CapabilityType,
    CheckResult,
    CheckResultOutcome,
    CheckResultTargetType,
    DataSource,
    DataSourceStatus,
    DataSourceType,
    DataUsageClassification,
    DataUsageProfile,
    DataUsageReviewStatus,
    Environment,
    HumanApproval,
    HumanApprovalStatus,
    ModelAsset,
    ModelAssetStatus,
    ModelAssetType,
    ModelProvider,
    OwnerType,
    Policy,
    PolicyCheckStep,
    PolicyCheckStepCheckType,
    PolicyCheckStepEvidenceRetention,
    PolicyCheckStepFailureBehavior,
    PolicyCheckStepStatus,
    PolicyCheckStepTargetSelector,
    PolicyDecision,
    PolicyDecisionValue,
    PolicyRule,
    PolicyStatus,
    PolicyVersion,
    PolicyVersionStatus,
    RiskLevel,
    ServiceActor,
    ServiceActorApiKey,
    ServiceActorApiKeyStatus,
    ServiceActorScope,
    ServiceActorScopeRule,
    ServiceActorStatus,
    TraceEventRecord,
    TraceEventType,
)

SessionFactory = Callable[[], Session]
SERVICE_ACTOR_ID = "service:runtime-test"
SERVICE_API_KEY = "local-test-runtime-key"


@pytest.fixture()
def api_client() -> Iterator[tuple[TestClient, SessionFactory]]:
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
        with testing_session_factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_get_db_session
    try:
        with TestClient(app) as client:
            yield client, testing_session_factory
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_runtime_simulation_with_allow_policy_returns_allow(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    policy_id, rule_id = create_policy_rule(
        session_factory,
        decision=PolicyDecisionValue.ALLOW,
        reason="The requested tool is allowed.",
    )

    response = client.post(
        "/runtime/tool-calls/decision",
        json=runtime_decision_payload(agent_id),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["decision"] == "allow"
    assert body["proceed"] is True
    assert body["reason"] == "The requested tool is allowed."
    assert body["trace_event_id"] is not None
    assert body["policy_decision_id"] is not None
    assert body["human_approval_id"] is None

    [trace_event] = fetch_trace_events(session_factory)
    assert trace_event.external_event_id == "runtime-request-001"
    assert trace_event.event_type is TraceEventType.TOOL_CALL_REQUESTED
    assert trace_event.summary == "Send a support follow-up email."
    assert trace_event.metadata_ == {
        "ticket_category": "support",
        "tool_name": "send_email",
    }
    [policy_decision] = fetch_policy_decisions(session_factory)
    assert policy_decision.decision is PolicyDecisionValue.ALLOW
    assert policy_decision.policy_id == policy_id
    assert policy_decision.rule_id == rule_id
    assert policy_decision.policy_version_id is None
    assert policy_decision.trace_event_id == trace_event.id
    assert fetch_human_approvals(session_factory) == []


def test_runtime_uses_active_policy_version_snapshot_when_present(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    policy_id, rule_id = create_policy_rule(
        session_factory,
        decision=PolicyDecisionValue.ALLOW,
        reason="Live mutable rule should not be used.",
    )
    version_id = create_policy_version(
        session_factory,
        policy_id=policy_id,
        status=PolicyVersionStatus.ACTIVE,
        rule_snapshots=[
            policy_rule_snapshot(
                policy_id=policy_id,
                rule_id=rule_id,
                condition={
                    "decision": "deny",
                    "reason": "Reviewed snapshot denies email.",
                    "tool_name": "send_email",
                },
            )
        ],
    )
    before_snapshot = deepcopy(fetch_policy_version(session_factory, version_id))

    response = client.post(
        "/runtime/tool-calls/decision",
        json=runtime_decision_payload(agent_id),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["decision"] == "deny"
    assert body["reason"] == "Reviewed snapshot denies email."
    [policy_decision] = fetch_policy_decisions(session_factory)
    assert policy_decision.policy_id == policy_id
    assert policy_decision.policy_version_id == version_id
    assert policy_decision.rule_id == rule_id
    assert fetch_policy_version(session_factory, version_id) == before_snapshot


@pytest.mark.parametrize(
    "status",
    [
        PolicyVersionStatus.DRAFT,
        PolicyVersionStatus.UNDER_REVIEW,
        PolicyVersionStatus.APPROVED,
        PolicyVersionStatus.REJECTED,
        PolicyVersionStatus.SUPERSEDED,
        PolicyVersionStatus.ARCHIVED,
    ],
)
def test_runtime_ignores_policy_versions_that_are_not_active(
    api_client: tuple[TestClient, SessionFactory],
    status: PolicyVersionStatus,
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    policy_id, rule_id = create_policy_rule(
        session_factory,
        decision=PolicyDecisionValue.ALLOW,
        reason="Live fallback rule is still used.",
    )
    create_policy_version(
        session_factory,
        policy_id=policy_id,
        status=status,
        rule_snapshots=[
            policy_rule_snapshot(
                policy_id=policy_id,
                rule_id=rule_id,
                condition={
                    "decision": "deny",
                    "reason": "Inactive snapshot should not be used.",
                    "tool_name": "send_email",
                },
            )
        ],
    )

    response = client.post(
        "/runtime/tool-calls/decision",
        json=runtime_decision_payload(agent_id),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["decision"] == "allow"
    assert body["reason"] == "Live fallback rule is still used."
    [policy_decision] = fetch_policy_decisions(session_factory)
    assert policy_decision.policy_id == policy_id
    assert policy_decision.policy_version_id is None
    assert policy_decision.rule_id == rule_id


def test_runtime_ignores_policy_version_draft_saved_from_editor(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    policy_id, rule_id = create_policy_rule(
        session_factory,
        decision=PolicyDecisionValue.ALLOW,
        reason="Live fallback rule is still used.",
    )

    draft_response = client.post(
        f"/policies/{policy_id}/versions/draft",
        json={
            "change_summary": "Policy Studio draft should not affect runtime.",
            "policy_snapshot": {
                "name": "Draft runtime guard",
                "description": "Drafted in Policy Studio.",
                "status": "active",
            },
            "rule_snapshots": [
                {
                    "id": str(rule_id),
                    "name": "Draft runtime deny rule",
                    "description": "Compiled from Policy Studio.",
                    "condition": json.dumps(
                        {
                            "decision": "deny",
                            "reason": "Draft snapshot should not be used.",
                            "tool_name": "send_email",
                        }
                    ),
                }
            ],
        },
    )
    assert draft_response.status_code == 201
    assert draft_response.json()["status"] == "draft"

    response = client.post(
        "/runtime/tool-calls/decision",
        json=runtime_decision_payload(agent_id),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["decision"] == "allow"
    assert body["reason"] == "Live fallback rule is still used."
    [policy_decision] = fetch_policy_decisions(session_factory)
    assert policy_decision.policy_id == policy_id
    assert policy_decision.policy_version_id is None
    assert policy_decision.rule_id == rule_id


def test_runtime_active_policy_version_preserves_decision_precedence(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(
        session_factory,
        environment=Environment.PRODUCTION,
    )
    policy_id, allow_rule_id = create_policy_rule(
        session_factory,
        decision=PolicyDecisionValue.ALLOW,
        reason="Live mutable rule should not be used.",
    )
    review_rule_id = create_policy_rule_for_policy(
        session_factory,
        policy_id=policy_id,
        condition={
            "decision": "allow",
            "reason": "Live mutable review rule should not be used.",
            "tool_name": "send_email",
        },
    )
    deny_rule_id = create_policy_rule_for_policy(
        session_factory,
        policy_id=policy_id,
        condition={
            "decision": "allow",
            "reason": "Live mutable deny rule should not be used.",
            "tool_name": "send_email",
        },
    )
    version_id = create_policy_version(
        session_factory,
        policy_id=policy_id,
        status=PolicyVersionStatus.ACTIVE,
        rule_snapshots=[
            policy_rule_snapshot(
                policy_id=policy_id,
                rule_id=allow_rule_id,
                condition={
                    "decision": "allow",
                    "reason": "Email is generally allowed.",
                    "tool_name": "send_email",
                },
            ),
            policy_rule_snapshot(
                policy_id=policy_id,
                rule_id=review_rule_id,
                condition={
                    "decision": "require_human_review",
                    "reason": "High risk requires review.",
                    "risk_level": "high",
                },
            ),
            policy_rule_snapshot(
                policy_id=policy_id,
                rule_id=deny_rule_id,
                condition={
                    "decision": "deny",
                    "reason": "Production email is denied.",
                    "environment": "production",
                },
            ),
        ],
    )

    response = client.post(
        "/runtime/tool-calls/decision",
        json=runtime_decision_payload(agent_id),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["decision"] == "deny"
    assert body["reason"] == "Production email is denied."
    [policy_decision] = fetch_policy_decisions(session_factory)
    assert policy_decision.policy_version_id == version_id
    assert policy_decision.rule_id == deny_rule_id


def test_runtime_active_policy_version_matches_contextual_fields(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    capability_id = uuid4()
    source_id = uuid4()
    policy_id, rule_id = create_policy_rule(
        session_factory,
        decision=PolicyDecisionValue.ALLOW,
        reason="Live mutable rule should not be used.",
        tool_name="vectorize_source",
    )
    version_id = create_policy_version(
        session_factory,
        policy_id=policy_id,
        status=PolicyVersionStatus.ACTIVE,
        rule_snapshots=[
            policy_rule_snapshot(
                policy_id=policy_id,
                rule_id=rule_id,
                condition={
                    "decision": "deny",
                    "reason": "Reviewed snapshot denies governed vectorization.",
                    "tool_name": "vectorize_source",
                    "action_type": "vectorize",
                    "capability_id": str(capability_id),
                    "source_ids": [str(source_id)],
                    "purpose": "semantic_search_indexing",
                    "data_classification": "confidential",
                    "contains_personal_data": True,
                },
            )
        ],
    )
    payload = runtime_decision_payload(
        agent_id,
        action_summary="Vectorize a governed source for semantic search.",
        tool_name="vectorize_source",
    )
    payload.update(
        {
            "action_type": "vectorize",
            "capability_id": str(capability_id),
            "source_ids": [str(uuid4()), str(source_id)],
            "purpose": "semantic_search_indexing",
            "data_classification": "confidential",
            "contains_personal_data": True,
        }
    )

    response = client.post("/runtime/tool-calls/decision", json=payload)

    assert response.status_code == 201
    body = response.json()
    assert body["decision"] == "deny"
    assert body["reason"] == "Reviewed snapshot denies governed vectorization."
    [policy_decision] = fetch_policy_decisions(session_factory)
    assert policy_decision.policy_version_id == version_id
    assert policy_decision.rule_id == rule_id


def test_runtime_active_policy_version_matches_check_result_fields(
    api_client: tuple[TestClient, SessionFactory],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    enable_runtime_metadata_pre_checks(monkeypatch)
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    inventory = seed_runtime_inventory_context(session_factory, agent_id=agent_id)
    policy_id, rule_id = create_policy_rule(
        session_factory,
        decision=PolicyDecisionValue.ALLOW,
        reason="Live mutable rule should not be used.",
        tool_name="vectorize_source",
    )
    check_step_id = create_policy_check_step(
        session_factory,
        policy_rule_id=rule_id,
        check_type=PolicyCheckStepCheckType.SOURCE_STATUS,
        target_selector=PolicyCheckStepTargetSelector.SOURCE_IDS,
    )
    disable_policy_check_step(session_factory, check_step_id)
    version_id = create_policy_version(
        session_factory,
        policy_id=policy_id,
        status=PolicyVersionStatus.ACTIVE,
        rule_snapshots=[
            policy_rule_snapshot(
                policy_id=policy_id,
                rule_id=rule_id,
                condition={
                    "decision": "deny",
                    "reason": "Reviewed snapshot denies after source check.",
                    "tool_name": "vectorize_source",
                    "check_type": "source_status",
                    "check_outcome": "pass",
                    "check_target_type": "source",
                    "check_target_id": str(inventory["source_id"]),
                },
            )
        ],
        check_step_snapshots=[
            policy_check_step_snapshot(
                check_step_id=check_step_id,
                policy_rule_id=rule_id,
                check_type=PolicyCheckStepCheckType.SOURCE_STATUS,
                target_selector=PolicyCheckStepTargetSelector.SOURCE_IDS,
            )
        ],
    )
    payload = runtime_decision_payload(
        agent_id,
        action_summary="Vectorize a governed source for semantic search.",
        tool_name="vectorize_source",
    )
    payload.update({"source_ids": [str(inventory["source_id"])]})

    response = client.post("/runtime/tool-calls/decision", json=payload)

    assert response.status_code == 201
    body = response.json()
    assert body["decision"] == "deny"
    assert body["reason"] == "Reviewed snapshot denies after source check."
    [policy_decision] = fetch_policy_decisions(session_factory)
    assert policy_decision.policy_version_id == version_id
    assert policy_decision.rule_id == rule_id
    [check_result] = fetch_check_results(session_factory)
    assert check_result.policy_decision_id == policy_decision.id
    assert check_result.outcome is CheckResultOutcome.PASS
    assert check_result.metadata_["policy_version_id"] == str(version_id)
    assert check_result.metadata_["execution_mode"] == "metadata_only"


def test_runtime_contextual_fields_are_accepted_and_safely_persisted(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    create_policy_rule(
        session_factory,
        decision=PolicyDecisionValue.ALLOW,
        reason="The requested contextual action is allowed.",
        tool_name="vectorize_source",
    )
    capability_id = uuid4()
    source_id = uuid4()
    model_id = uuid4()
    payload = runtime_decision_payload(
        agent_id,
        action_summary="Vectorize a governed source for semantic search.",
        tool_name="vectorize_source",
    )
    payload.update(
        {
            "action_type": "vectorize",
            "capability_id": str(capability_id),
            "source_ids": [str(source_id)],
            "model_id": str(model_id),
            "purpose": "semantic_search_indexing",
            "data_classification": "confidential",
            "contains_personal_data": True,
            "contains_sensitive_data": False,
        }
    )

    response = client.post("/runtime/tool-calls/decision", json=payload)

    assert response.status_code == 201
    assert response.json()["decision"] == "allow"
    [trace_event] = fetch_trace_events(session_factory)
    assert trace_event.metadata_ == {
        "ticket_category": "support",
        "tool_name": "vectorize_source",
        "action_type": "vectorize",
        "capability_id": str(capability_id),
        "resolved_capability_status": "missing",
        "resolved_missing_capability_id": str(capability_id),
        "source_ids": str(source_id),
        "resolved_source_statuses": "missing",
        "resolved_missing_source_ids": str(source_id),
        "resolved_data_usage_review_statuses": "missing",
        "model_id": str(model_id),
        "resolved_model_status": "missing",
        "resolved_missing_model_id": str(model_id),
        "resolved_access_grant_statuses": "missing",
        "resolved_missing_access_grant_targets": (
            f"capability:{capability_id},source:{source_id},model_asset:{model_id}"
        ),
        "purpose": "semantic_search_indexing",
        "data_classification": "confidential",
        "contains_personal_data": True,
        "contains_sensitive_data": False,
    }
    assert "raw_content" not in str(trace_event.metadata_)
    assert "chunks" not in str(trace_event.metadata_)
    assert "prompt" not in str(trace_event.metadata_)


def test_runtime_contextual_policy_rule_matches_request_context(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    capability_id = uuid4()
    source_id = uuid4()
    other_source_id = uuid4()
    model_id = uuid4()
    policy_id, rule_id = create_policy_rule(
        session_factory,
        decision=PolicyDecisionValue.DENY,
        reason="Declared confidential vectorization is denied.",
        condition={
            "decision": "deny",
            "reason": "Declared confidential vectorization is denied.",
            "tool_name": "vectorize_source",
            "action_type": "vectorize",
            "capability_id": str(capability_id),
            "source_id": str(source_id),
            "model_id": str(model_id),
            "purpose": "semantic_search_indexing",
            "data_classification": "confidential",
            "contains_personal_data": True,
            "contains_sensitive_data": False,
        },
    )
    payload = runtime_decision_payload(
        agent_id,
        action_summary="Vectorize a governed source for semantic search.",
        tool_name="vectorize_source",
    )
    payload.update(
        {
            "action_type": "vectorize",
            "capability_id": str(capability_id),
            "source_ids": [str(other_source_id), str(source_id)],
            "model_id": str(model_id),
            "purpose": "semantic_search_indexing",
            "data_classification": "confidential",
            "contains_personal_data": True,
            "contains_sensitive_data": False,
        }
    )

    response = client.post("/runtime/tool-calls/decision", json=payload)

    assert response.status_code == 201
    body = response.json()
    assert body["decision"] == "deny"
    assert body["reason"] == "Declared confidential vectorization is denied."
    [policy_decision] = fetch_policy_decisions(session_factory)
    assert policy_decision.policy_id == policy_id
    assert policy_decision.rule_id == rule_id


def test_runtime_resolves_inventory_context_and_matches_resolved_policy_rule(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    inventory = seed_runtime_inventory_context(session_factory, agent_id=agent_id)
    policy_id, rule_id = create_policy_rule(
        session_factory,
        decision=PolicyDecisionValue.DENY,
        reason="Resolved restricted external vectorization is denied.",
        condition={
            "decision": "deny",
            "reason": "Resolved restricted external vectorization is denied.",
            "tool_name": "vectorize_source",
            "source_data_classification": "restricted",
            "model_provider_type": "external",
            "capability_type": "tool",
            "access_grant_status": "active",
            "data_usage_review_status": "approved",
            "data_usage_prohibited_purpose": "model_training",
        },
    )
    payload = runtime_decision_payload(
        agent_id,
        action_summary="Vectorize a governed source for semantic search.",
        tool_name="vectorize_source",
    )
    payload.update(
        {
            "action_type": "vectorize",
            "capability_id": str(inventory["capability_id"]),
            "source_ids": [str(inventory["source_id"])],
            "model_id": str(inventory["model_id"]),
            "purpose": "semantic_search_indexing",
            "data_classification": "public",
            "contains_personal_data": False,
            "contains_sensitive_data": False,
        }
    )

    response = client.post("/runtime/tool-calls/decision", json=payload)

    assert response.status_code == 201
    body = response.json()
    assert body["decision"] == "deny"
    assert body["reason"] == "Resolved restricted external vectorization is denied."
    [policy_decision] = fetch_policy_decisions(session_factory)
    assert policy_decision.policy_id == policy_id
    assert policy_decision.rule_id == rule_id
    [trace_event] = fetch_trace_events(session_factory)
    assert trace_event.metadata_["data_classification"] == "public"
    assert trace_event.metadata_["resolved_capability_type"] == "tool"
    assert trace_event.metadata_["resolved_source_data_classifications"] == "restricted"
    assert trace_event.metadata_["resolved_model_provider"] == "openai"
    assert trace_event.metadata_["resolved_model_provider_type"] == "external"
    assert trace_event.metadata_["resolved_access_grant_statuses"] == "active"
    assert trace_event.metadata_["resolved_data_usage_review_statuses"] == "approved"
    assert (
        trace_event.metadata_["resolved_data_usage_prohibited_purposes"]
        == "model_training"
    )


def test_runtime_missing_inventory_context_can_be_matched(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    capability_id = uuid4()
    source_id = uuid4()
    model_id = uuid4()
    create_policy_rule(
        session_factory,
        decision=PolicyDecisionValue.REQUIRE_HUMAN_REVIEW,
        reason="Missing inventory context requires human review.",
        condition={
            "decision": "require_human_review",
            "reason": "Missing inventory context requires human review.",
            "tool_name": "vectorize_source",
            "capability_status": "missing",
            "source_status": "missing",
            "model_status": "missing",
            "access_grant_status": "missing",
            "data_usage_review_status": "missing",
        },
    )
    payload = runtime_decision_payload(
        agent_id,
        action_summary="Vectorize an unknown source.",
        tool_name="vectorize_source",
    )
    payload.update(
        {
            "capability_id": str(capability_id),
            "source_ids": [str(source_id)],
            "model_id": str(model_id),
        }
    )

    response = client.post("/runtime/tool-calls/decision", json=payload)

    assert response.status_code == 201
    body = response.json()
    assert body["decision"] == "require_human_review"
    assert body["reason"] == "Missing inventory context requires human review."
    [trace_event] = fetch_trace_events(session_factory)
    assert trace_event.metadata_["resolved_capability_status"] == "missing"
    assert trace_event.metadata_["resolved_source_statuses"] == "missing"
    assert trace_event.metadata_["resolved_model_status"] == "missing"
    assert trace_event.metadata_["resolved_access_grant_statuses"] == "missing"
    assert trace_event.metadata_["resolved_data_usage_review_statuses"] == "missing"


def test_runtime_metadata_pre_checks_disabled_keeps_behavior_unchanged(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    inventory = seed_runtime_inventory_context(session_factory, agent_id=agent_id)
    _, rule_id = create_policy_rule(
        session_factory,
        decision=PolicyDecisionValue.ALLOW,
        reason="The requested contextual action is allowed.",
        tool_name="vectorize_source",
    )
    create_policy_check_step(
        session_factory,
        policy_rule_id=rule_id,
        check_type=PolicyCheckStepCheckType.SOURCE_STATUS,
        target_selector=PolicyCheckStepTargetSelector.SOURCE_IDS,
    )
    create_policy_check_step(
        session_factory,
        policy_rule_id=rule_id,
        check_type=PolicyCheckStepCheckType.SOURCE_CLASSIFICATION,
        target_selector=PolicyCheckStepTargetSelector.SOURCE_IDS,
    )
    create_policy_check_step(
        session_factory,
        policy_rule_id=rule_id,
        check_type=PolicyCheckStepCheckType.DATA_USAGE_PROFILE_STATUS,
        target_selector=PolicyCheckStepTargetSelector.SOURCE_IDS,
    )
    create_policy_check_step(
        session_factory,
        policy_rule_id=rule_id,
        check_type=PolicyCheckStepCheckType.ACCESS_GRANT_STATUS,
        target_selector=PolicyCheckStepTargetSelector.ACCESS_GRANTS,
    )
    payload = runtime_decision_payload(
        agent_id,
        action_summary="Vectorize a governed source for semantic search.",
        tool_name="vectorize_source",
    )
    payload.update(
        {
            "capability_id": str(inventory["capability_id"]),
            "source_ids": [str(inventory["source_id"])],
            "model_id": str(inventory["model_id"]),
        }
    )

    response = client.post("/runtime/tool-calls/decision", json=payload)

    assert response.status_code == 201
    assert response.json()["decision"] == "allow"
    assert fetch_check_results(session_factory) == []


def test_runtime_metadata_pre_checks_create_source_and_data_usage_results(
    api_client: tuple[TestClient, SessionFactory],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    enable_runtime_metadata_pre_checks(monkeypatch)
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    inventory = seed_runtime_inventory_context(session_factory, agent_id=agent_id)
    _, rule_id = create_policy_rule(
        session_factory,
        decision=PolicyDecisionValue.ALLOW,
        reason="The requested contextual action is allowed.",
        tool_name="vectorize_source",
    )
    create_policy_check_step(
        session_factory,
        policy_rule_id=rule_id,
        check_type=PolicyCheckStepCheckType.SOURCE_STATUS,
        target_selector=PolicyCheckStepTargetSelector.SOURCE_IDS,
    )
    create_policy_check_step(
        session_factory,
        policy_rule_id=rule_id,
        check_type=PolicyCheckStepCheckType.SOURCE_CLASSIFICATION,
        target_selector=PolicyCheckStepTargetSelector.SOURCE_IDS,
    )
    create_policy_check_step(
        session_factory,
        policy_rule_id=rule_id,
        check_type=PolicyCheckStepCheckType.DATA_USAGE_PROFILE_STATUS,
        target_selector=PolicyCheckStepTargetSelector.SOURCE_IDS,
    )
    create_policy_check_step(
        session_factory,
        policy_rule_id=rule_id,
        check_type=PolicyCheckStepCheckType.ACCESS_GRANT_STATUS,
        target_selector=PolicyCheckStepTargetSelector.ACCESS_GRANTS,
    )
    run_id = uuid4()
    payload = runtime_decision_payload(
        agent_id,
        run_id=run_id,
        action_summary="Vectorize a governed source for semantic search.",
        tool_name="vectorize_source",
    )
    payload.update({"source_ids": [str(inventory["source_id"])]})

    response = client.post("/runtime/tool-calls/decision", json=payload)

    assert response.status_code == 201
    [trace_event] = fetch_trace_events(session_factory)
    [policy_decision] = fetch_policy_decisions(session_factory)
    check_results = fetch_check_results(session_factory)
    results_by_type = {result.target_type: result for result in check_results}
    assert results_by_type[CheckResultTargetType.SOURCE].outcome is (
        CheckResultOutcome.PASS
    )
    assert results_by_type[CheckResultTargetType.DATA_USAGE_PROFILE].outcome is (
        CheckResultOutcome.PASS
    )
    assert results_by_type[CheckResultTargetType.ACCESS_GRANT].outcome is (
        CheckResultOutcome.PASS
    )
    for check_result in check_results:
        assert check_result.agent_id == agent_id
        assert check_result.run_id == run_id
        assert check_result.trace_event_id == trace_event.id
        assert check_result.policy_decision_id == policy_decision.id
        assert check_result.metadata_["policy_check_step_rule_id"] == str(rule_id)
        assert check_result.metadata_["policy_check_step_failure_behavior"] == (
            PolicyCheckStepFailureBehavior.RECORD_ONLY.value
        )
        assert check_result.metadata_["execution_mode"] == "metadata_only"
        assert "raw_content" not in str(check_result.metadata_)
        assert "prompt" not in str(check_result.metadata_)
    classification_results = [
        result
        for result in check_results
        if result.metadata_.get("policy_check_step_check_type")
        == "source_classification"
    ]
    assert len(classification_results) == 1
    assert classification_results[0].target_type is (
        CheckResultTargetType.DATA_USAGE_PROFILE
    )
    assert classification_results[0].metadata_["data_classification"] == "restricted"


def test_runtime_metadata_pre_checks_create_capability_and_model_results(
    api_client: tuple[TestClient, SessionFactory],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    enable_runtime_metadata_pre_checks(monkeypatch)
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    inventory = seed_runtime_inventory_context(session_factory, agent_id=agent_id)
    _, rule_id = create_policy_rule(
        session_factory,
        decision=PolicyDecisionValue.ALLOW,
        reason="The requested contextual action is allowed.",
        tool_name="vectorize_source",
    )
    create_policy_check_step(
        session_factory,
        policy_rule_id=rule_id,
        check_type=PolicyCheckStepCheckType.CAPABILITY_STATUS,
        target_selector=PolicyCheckStepTargetSelector.CAPABILITY_ID,
    )
    create_policy_check_step(
        session_factory,
        policy_rule_id=rule_id,
        check_type=PolicyCheckStepCheckType.MODEL_ASSET_STATUS,
        target_selector=PolicyCheckStepTargetSelector.MODEL_ID,
    )
    create_policy_check_step(
        session_factory,
        policy_rule_id=rule_id,
        check_type=PolicyCheckStepCheckType.MODEL_PROVIDER_TYPE,
        target_selector=PolicyCheckStepTargetSelector.MODEL_ID,
    )
    create_policy_check_step(
        session_factory,
        policy_rule_id=rule_id,
        check_type=PolicyCheckStepCheckType.ACCESS_GRANT_STATUS,
        target_selector=PolicyCheckStepTargetSelector.ACCESS_GRANTS,
    )
    payload = runtime_decision_payload(
        agent_id,
        action_summary="Vectorize with governed capability and model.",
        tool_name="vectorize_source",
    )
    payload.update(
        {
            "capability_id": str(inventory["capability_id"]),
            "model_id": str(inventory["model_id"]),
        }
    )

    response = client.post("/runtime/tool-calls/decision", json=payload)

    assert response.status_code == 201
    check_results = fetch_check_results(session_factory)
    capability_results = [
        result
        for result in check_results
        if result.target_type is CheckResultTargetType.CAPABILITY
    ]
    model_results = [
        result
        for result in check_results
        if result.target_type is CheckResultTargetType.MODEL_ASSET
    ]
    access_grant_results = [
        result
        for result in check_results
        if result.target_type is CheckResultTargetType.ACCESS_GRANT
    ]
    assert [result.outcome for result in capability_results] == [
        CheckResultOutcome.PASS
    ]
    assert [result.outcome for result in model_results] == [
        CheckResultOutcome.PASS,
        CheckResultOutcome.PASS,
    ]
    provider_results = [
        result
        for result in model_results
        if result.metadata_.get("policy_check_step_check_type") == "model_provider_type"
    ]
    assert len(provider_results) == 1
    assert provider_results[0].metadata_["model_provider"] == "openai"
    assert provider_results[0].metadata_["model_provider_type"] == "external"
    assert [result.outcome for result in access_grant_results] == [
        CheckResultOutcome.PASS,
        CheckResultOutcome.PASS,
    ]


def test_runtime_metadata_pre_checks_do_not_change_final_decision(
    api_client: tuple[TestClient, SessionFactory],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    enable_runtime_metadata_pre_checks(monkeypatch)
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    inventory = seed_runtime_inventory_context(session_factory, agent_id=agent_id)
    disable_runtime_source_and_revoke_grant(
        session_factory,
        source_id=inventory["source_id"],
    )
    _, rule_id = create_policy_rule(
        session_factory,
        decision=PolicyDecisionValue.ALLOW,
        reason="PolicyRules still govern the final decision.",
        tool_name="vectorize_source",
    )
    create_policy_check_step(
        session_factory,
        policy_rule_id=rule_id,
        check_type=PolicyCheckStepCheckType.SOURCE_STATUS,
        target_selector=PolicyCheckStepTargetSelector.SOURCE_IDS,
        failure_behavior=PolicyCheckStepFailureBehavior.FAIL_CLOSED,
    )
    create_policy_check_step(
        session_factory,
        policy_rule_id=rule_id,
        check_type=PolicyCheckStepCheckType.ACCESS_GRANT_STATUS,
        target_selector=PolicyCheckStepTargetSelector.ACCESS_GRANTS,
        failure_behavior=PolicyCheckStepFailureBehavior.FAIL_CLOSED,
    )
    payload = runtime_decision_payload(
        agent_id,
        action_summary="Vectorize source containing secret-token.",
        tool_name="vectorize_source",
    )
    payload.update({"source_ids": [str(inventory["source_id"])]})

    response = client.post("/runtime/tool-calls/decision", json=payload)

    assert response.status_code == 201
    body = response.json()
    assert body["decision"] == "allow"
    assert body["reason"] == "PolicyRules still govern the final decision."
    check_results = fetch_check_results(session_factory)
    assert any(result.outcome is CheckResultOutcome.FAIL for result in check_results)
    for check_result in check_results:
        serialized_result = (
            f"{check_result.summary} {check_result.reason} {check_result.metadata_}"
        )
        assert "secret-token" not in serialized_result
        assert "prompt" not in serialized_result
        assert "chunks" not in serialized_result
        assert "raw_content" not in serialized_result


def test_runtime_check_result_rule_matches_authored_pre_check_outcome(
    api_client: tuple[TestClient, SessionFactory],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    enable_runtime_metadata_pre_checks(monkeypatch)
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    inventory = seed_runtime_inventory_context(session_factory, agent_id=agent_id)
    disable_runtime_source_and_revoke_grant(
        session_factory,
        source_id=inventory["source_id"],
    )
    create_policy_rule(
        session_factory,
        decision=PolicyDecisionValue.ALLOW,
        reason="Fallback policy would otherwise allow vectorization.",
        tool_name="vectorize_source",
    )
    policy_id, rule_id = create_policy_rule(
        session_factory,
        decision=PolicyDecisionValue.DENY,
        reason="Failed source pre-check denies vectorization.",
        condition={
            "decision": "deny",
            "reason": "Failed source pre-check denies vectorization.",
            "tool_name": "vectorize_source",
            "check_type": "source_status",
            "check_outcome": "fail",
            "check_target_type": "source",
            "check_min_confidence": 0.5,
        },
    )
    create_policy_check_step(
        session_factory,
        policy_rule_id=rule_id,
        check_type=PolicyCheckStepCheckType.SOURCE_STATUS,
        target_selector=PolicyCheckStepTargetSelector.SOURCE_IDS,
    )
    run_id = uuid4()
    payload = runtime_decision_payload(
        agent_id,
        run_id=run_id,
        action_summary="Vectorize a governed source for semantic search.",
        tool_name="vectorize_source",
    )
    payload.update({"source_ids": [str(inventory["source_id"])]})

    response = client.post("/runtime/tool-calls/decision", json=payload)

    assert response.status_code == 201
    body = response.json()
    assert body["decision"] == "deny"
    assert body["reason"] == "Failed source pre-check denies vectorization."
    [policy_decision] = fetch_policy_decisions(session_factory)
    assert policy_decision.policy_id == policy_id
    assert policy_decision.rule_id == rule_id
    [check_result] = fetch_check_results(session_factory)
    assert check_result.outcome is CheckResultOutcome.FAIL
    assert check_result.target_type is CheckResultTargetType.SOURCE
    assert check_result.target_id == inventory["source_id"]
    assert check_result.run_id == run_id
    assert check_result.policy_decision_id == policy_decision.id
    assert check_result.metadata_["policy_check_step_check_type"] == "source_status"


def test_runtime_check_result_rule_matches_model_provider_type_pre_check(
    api_client: tuple[TestClient, SessionFactory],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    enable_runtime_metadata_pre_checks(monkeypatch)
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    inventory = seed_runtime_inventory_context(session_factory, agent_id=agent_id)
    create_policy_rule(
        session_factory,
        decision=PolicyDecisionValue.ALLOW,
        reason="Fallback policy would otherwise allow model use.",
        tool_name="vectorize_source",
    )
    policy_id, rule_id = create_policy_rule(
        session_factory,
        decision=PolicyDecisionValue.REQUIRE_HUMAN_REVIEW,
        reason="External model provider metadata requires review.",
        condition={
            "decision": "require_human_review",
            "reason": "External model provider metadata requires review.",
            "tool_name": "vectorize_source",
            "check_type": "model_provider_type",
            "check_outcome": "pass",
            "check_target_type": "model_asset",
        },
    )
    create_policy_check_step(
        session_factory,
        policy_rule_id=rule_id,
        check_type=PolicyCheckStepCheckType.MODEL_PROVIDER_TYPE,
        target_selector=PolicyCheckStepTargetSelector.MODEL_ID,
    )
    payload = runtime_decision_payload(
        agent_id,
        action_summary="Vectorize a governed source for semantic search.",
        tool_name="vectorize_source",
    )
    payload.update({"model_id": str(inventory["model_id"])})

    response = client.post("/runtime/tool-calls/decision", json=payload)

    assert response.status_code == 201
    body = response.json()
    assert body["decision"] == "require_human_review"
    assert body["reason"] == "External model provider metadata requires review."
    [policy_decision] = fetch_policy_decisions(session_factory)
    assert policy_decision.policy_id == policy_id
    assert policy_decision.rule_id == rule_id
    [check_result] = fetch_check_results(session_factory)
    assert check_result.target_type is CheckResultTargetType.MODEL_ASSET
    assert check_result.outcome is CheckResultOutcome.PASS
    assert check_result.metadata_["policy_check_step_check_type"] == (
        "model_provider_type"
    )
    assert check_result.metadata_["model_provider"] == "openai"
    assert check_result.metadata_["model_provider_type"] == "external"


def test_runtime_check_result_rule_does_not_match_without_check_results(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    inventory = seed_runtime_inventory_context(session_factory, agent_id=agent_id)
    disable_runtime_source_and_revoke_grant(
        session_factory,
        source_id=inventory["source_id"],
    )
    create_policy_rule(
        session_factory,
        decision=PolicyDecisionValue.ALLOW,
        reason="Fallback policy allows vectorization.",
        tool_name="vectorize_source",
    )
    _, rule_id = create_policy_rule(
        session_factory,
        decision=PolicyDecisionValue.DENY,
        reason="Failed source pre-check denies vectorization.",
        condition={
            "decision": "deny",
            "reason": "Failed source pre-check denies vectorization.",
            "tool_name": "vectorize_source",
            "check_type": "source_status",
            "check_outcome": "fail",
            "check_target_type": "source",
        },
    )
    create_policy_check_step(
        session_factory,
        policy_rule_id=rule_id,
        check_type=PolicyCheckStepCheckType.SOURCE_STATUS,
        target_selector=PolicyCheckStepTargetSelector.SOURCE_IDS,
    )
    payload = runtime_decision_payload(
        agent_id,
        action_summary="Vectorize a governed source for semantic search.",
        tool_name="vectorize_source",
    )
    payload.update({"source_ids": [str(inventory["source_id"])]})

    response = client.post("/runtime/tool-calls/decision", json=payload)

    assert response.status_code == 201
    body = response.json()
    assert body["decision"] == "allow"
    assert body["reason"] == "Fallback policy allows vectorization."
    assert fetch_check_results(session_factory) == []


def test_runtime_metadata_pre_checks_skip_disabled_and_retired_policy_check_steps(
    api_client: tuple[TestClient, SessionFactory],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    enable_runtime_metadata_pre_checks(monkeypatch)
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    inventory = seed_runtime_inventory_context(session_factory, agent_id=agent_id)
    _, rule_id = create_policy_rule(
        session_factory,
        decision=PolicyDecisionValue.ALLOW,
        reason="The requested contextual action is allowed.",
        tool_name="vectorize_source",
    )
    create_policy_check_step(
        session_factory,
        policy_rule_id=rule_id,
        check_type=PolicyCheckStepCheckType.SOURCE_STATUS,
        target_selector=PolicyCheckStepTargetSelector.SOURCE_IDS,
        status=PolicyCheckStepStatus.DISABLED,
    )
    create_policy_check_step(
        session_factory,
        policy_rule_id=rule_id,
        check_type=PolicyCheckStepCheckType.DATA_USAGE_PROFILE_STATUS,
        target_selector=PolicyCheckStepTargetSelector.SOURCE_IDS,
        status=PolicyCheckStepStatus.RETIRED,
    )
    payload = runtime_decision_payload(
        agent_id,
        action_summary="Vectorize a governed source for semantic search.",
        tool_name="vectorize_source",
    )
    payload.update({"source_ids": [str(inventory["source_id"])]})

    response = client.post("/runtime/tool-calls/decision", json=payload)

    assert response.status_code == 201
    assert response.json()["decision"] == "allow"
    assert fetch_check_results(session_factory) == []


def test_runtime_simulation_behavior_is_unchanged_by_failure_policy_config(
    api_client: tuple[TestClient, SessionFactory],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AGCP_RUNTIME_FAILURE_DEFAULT", "record_only")
    get_settings.cache_clear()
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    create_policy_rule(
        session_factory,
        decision=PolicyDecisionValue.DENY,
        reason="The requested tool is denied.",
    )

    response = client.post(
        "/runtime/tool-calls/decision",
        json=runtime_decision_payload(agent_id),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["decision"] == "deny"
    assert body["proceed"] is False
    assert body["human_approval_id"] is None
    assert len(fetch_trace_events(session_factory)) == 1
    [policy_decision] = fetch_policy_decisions(session_factory)
    assert policy_decision.decision is PolicyDecisionValue.DENY


def test_runtime_simulation_with_deny_policy_returns_deny(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    create_policy_rule(
        session_factory,
        decision=PolicyDecisionValue.DENY,
        reason="The requested tool is denied.",
    )

    response = client.post(
        "/runtime/tool-calls/decision",
        json=runtime_decision_payload(agent_id),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["decision"] == "deny"
    assert body["proceed"] is False
    assert body["reason"] == "The requested tool is denied."
    assert body["human_approval_id"] is None
    [policy_decision] = fetch_policy_decisions(session_factory)
    assert policy_decision.decision is PolicyDecisionValue.DENY
    assert fetch_human_approvals(session_factory) == []


def test_runtime_simulation_with_review_policy_creates_human_approval(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    create_policy_rule(
        session_factory,
        decision=PolicyDecisionValue.REQUIRE_HUMAN_REVIEW,
        reason="The requested tool requires human review.",
    )

    response = client.post(
        "/runtime/tool-calls/decision",
        json=runtime_decision_payload(agent_id),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["decision"] == "require_human_review"
    assert body["proceed"] is False
    assert body["human_approval_id"] is not None

    [policy_decision] = fetch_policy_decisions(session_factory)
    [approval] = fetch_human_approvals(session_factory)
    assert approval.id == UUID(body["human_approval_id"])
    assert approval.agent_id == agent_id
    assert approval.policy_decision_id == policy_decision.id
    assert approval.status is HumanApprovalStatus.PENDING
    assert approval.requested_by_actor_type is ActorType.DEVELOPMENT
    assert approval.requested_by_actor_id == "dev-placeholder"

    [audit_log] = fetch_human_approval_audit_logs(session_factory)
    assert audit_log.event_type == "human_approval_requested"
    assert audit_log.actor_type is ActorType.DEVELOPMENT
    assert audit_log.actor_id == "dev-placeholder"
    assert audit_log.entity_id == str(approval.id)
    assert audit_log.metadata_ == {
        "agent_id": str(agent_id),
        "status": "pending",
        "policy_decision_id": str(policy_decision.id),
    }


def test_runtime_simulation_with_service_api_key_uses_service_actor(
    api_client: tuple[TestClient, SessionFactory],
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    configure_service_actor_api_key(monkeypatch, require_auth=True)
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    create_policy_rule(
        session_factory,
        decision=PolicyDecisionValue.REQUIRE_HUMAN_REVIEW,
        reason="The requested tool requires human review.",
    )

    response = client.post(
        "/runtime/tool-calls/decision",
        json=runtime_decision_payload(agent_id),
        headers={"X-AGCP-API-Key": SERVICE_API_KEY},
    )
    set_evidence_export_actor()
    bundle_response = client.get(f"/agents/{agent_id}/evidence-bundle")

    assert response.status_code == 201
    assert bundle_response.status_code == 200
    [approval] = fetch_human_approvals(session_factory)
    assert approval.requested_by_actor_type is ActorType.SERVICE
    assert approval.requested_by_actor_id == SERVICE_ACTOR_ID
    [audit_log] = fetch_human_approval_audit_logs(session_factory)
    assert audit_log.actor_type is ActorType.SERVICE
    assert audit_log.actor_id == SERVICE_ACTOR_ID
    [trace_event] = fetch_trace_events(session_factory)
    assert SERVICE_API_KEY not in str(trace_event.metadata_)
    assert SERVICE_API_KEY not in response.text
    assert SERVICE_API_KEY not in bundle_response.text
    assert SERVICE_API_KEY not in str(audit_log.metadata_)
    assert SERVICE_API_KEY not in caplog.text


def test_runtime_simulation_with_registry_service_api_key_uses_service_actor(
    api_client: tuple[TestClient, SessionFactory],
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    client, session_factory = api_client
    configure_service_actor_registry_api_key(
        monkeypatch,
        session_factory,
        require_auth=True,
    )
    agent_id = create_agent(session_factory)
    create_policy_rule(
        session_factory,
        decision=PolicyDecisionValue.REQUIRE_HUMAN_REVIEW,
        reason="The requested tool requires human review.",
    )

    response = client.post(
        "/runtime/tool-calls/decision",
        json=runtime_decision_payload(agent_id),
        headers={"X-AGCP-API-Key": SERVICE_API_KEY},
    )
    set_evidence_export_actor()
    bundle_response = client.get(f"/agents/{agent_id}/evidence-bundle")

    assert response.status_code == 201
    assert bundle_response.status_code == 200
    [approval] = fetch_human_approvals(session_factory)
    assert approval.requested_by_actor_type is ActorType.SERVICE
    assert approval.requested_by_actor_id == SERVICE_ACTOR_ID
    [audit_log] = fetch_human_approval_audit_logs(session_factory)
    assert audit_log.actor_type is ActorType.SERVICE
    assert audit_log.actor_id == SERVICE_ACTOR_ID
    [trace_event] = fetch_trace_events(session_factory)
    assert SERVICE_API_KEY not in str(trace_event.metadata_)
    assert SERVICE_API_KEY not in response.text
    assert SERVICE_API_KEY not in bundle_response.text
    assert SERVICE_API_KEY not in str(audit_log.metadata_)
    assert SERVICE_API_KEY not in caplog.text
    with session_factory() as session:
        [api_key] = session.scalars(select(ServiceActorApiKey)).all()
        assert api_key.key_hash == hash_service_actor_api_key(SERVICE_API_KEY)
        assert SERVICE_API_KEY not in str(api_key.__dict__)


def test_runtime_missing_api_key_when_service_auth_required_rejects_without_records(
    api_client: tuple[TestClient, SessionFactory],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AGCP_REQUIRE_SERVICE_AUTH", "true")
    get_settings.cache_clear()
    client, session_factory = api_client
    agent_id = create_agent(session_factory)

    response = client.post(
        "/runtime/tool-calls/decision",
        json=runtime_decision_payload(agent_id),
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "AGCP service actor API key is required."
    assert fetch_agent_runs(session_factory) == []
    assert fetch_trace_events(session_factory) == []
    assert fetch_policy_decisions(session_factory) == []
    assert fetch_human_approvals(session_factory) == []
    assert fetch_human_approval_audit_logs(session_factory) == []


def test_runtime_registry_service_api_key_without_decision_scope_is_rejected(
    api_client: tuple[TestClient, SessionFactory],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, session_factory = api_client
    configure_service_actor_registry_api_key(
        monkeypatch,
        session_factory,
        scopes=("telemetry:write",),
        require_auth=True,
    )
    agent_id = create_agent(session_factory)

    response = client.post(
        "/runtime/tool-calls/decision",
        json=runtime_decision_payload(agent_id),
        headers={"X-AGCP-API-Key": SERVICE_API_KEY},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == (
        "Service actor requires scope: runtime:decision."
    )
    assert SERVICE_API_KEY not in response.text
    assert fetch_agent_runs(session_factory) == []
    assert fetch_trace_events(session_factory) == []
    assert fetch_policy_decisions(session_factory) == []


def test_runtime_registry_scope_rule_allows_matching_context(
    api_client: tuple[TestClient, SessionFactory],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    configure_service_actor_registry_api_key(
        monkeypatch,
        session_factory,
        require_auth=True,
        scope_rule={
            "agent_ids": [str(agent_id)],
            "environments": ["development"],
            "runtime_modes": ["simulation"],
            "tool_names": ["send_email"],
        },
    )

    response = client.post(
        "/runtime/tool-calls/decision",
        json=runtime_decision_payload(agent_id),
        headers={"X-AGCP-API-Key": SERVICE_API_KEY},
    )

    assert response.status_code == 201
    assert len(fetch_trace_events(session_factory)) == 1
    assert len(fetch_policy_decisions(session_factory)) == 1


def test_runtime_registry_scope_rule_denies_non_matching_agent_without_records(
    api_client: tuple[TestClient, SessionFactory],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    configure_service_actor_registry_api_key(
        monkeypatch,
        session_factory,
        require_auth=True,
        scope_rule={
            "agent_ids": [str(uuid4())],
            "environments": ["development"],
            "runtime_modes": ["simulation"],
            "tool_names": ["send_email"],
        },
    )

    response = client.post(
        "/runtime/tool-calls/decision",
        json=runtime_decision_payload(agent_id),
        headers={"X-AGCP-API-Key": SERVICE_API_KEY},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == (
        "Service actor is not permitted for this agent."
    )
    assert SERVICE_API_KEY not in response.text
    assert fetch_agent_runs(session_factory) == []
    assert fetch_trace_events(session_factory) == []
    assert fetch_policy_decisions(session_factory) == []


def test_runtime_registry_scope_rule_denies_non_matching_environment_without_records(
    api_client: tuple[TestClient, SessionFactory],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory, environment=Environment.DEVELOPMENT)
    configure_service_actor_registry_api_key(
        monkeypatch,
        session_factory,
        require_auth=True,
        scope_rule={
            "agent_ids": [str(agent_id)],
            "environments": ["staging"],
            "runtime_modes": ["simulation"],
            "tool_names": ["send_email"],
        },
    )

    response = client.post(
        "/runtime/tool-calls/decision",
        json=runtime_decision_payload(agent_id),
        headers={"X-AGCP-API-Key": SERVICE_API_KEY},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == (
        "Service actor is not permitted for this environment."
    )
    assert fetch_agent_runs(session_factory) == []
    assert fetch_trace_events(session_factory) == []
    assert fetch_policy_decisions(session_factory) == []


def test_runtime_registry_scope_rule_denies_non_matching_mode_without_records(
    api_client: tuple[TestClient, SessionFactory],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    configure_service_actor_registry_api_key(
        monkeypatch,
        session_factory,
        require_auth=True,
        scope_rule={
            "agent_ids": [str(agent_id)],
            "environments": ["development"],
            "runtime_modes": ["enforcement"],
            "tool_names": ["send_email"],
        },
    )

    response = client.post(
        "/runtime/tool-calls/decision",
        json=runtime_decision_payload(agent_id, mode="simulation"),
        headers={"X-AGCP-API-Key": SERVICE_API_KEY},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == (
        "Service actor is not permitted for this runtime mode."
    )
    assert fetch_agent_runs(session_factory) == []
    assert fetch_trace_events(session_factory) == []
    assert fetch_policy_decisions(session_factory) == []


def test_runtime_registry_scope_rule_denies_non_matching_tool_without_records(
    api_client: tuple[TestClient, SessionFactory],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    configure_service_actor_registry_api_key(
        monkeypatch,
        session_factory,
        require_auth=True,
        scope_rule={
            "agent_ids": [str(agent_id)],
            "environments": ["development"],
            "runtime_modes": ["simulation"],
            "tool_names": ["send_payment"],
        },
    )

    response = client.post(
        "/runtime/tool-calls/decision",
        json=runtime_decision_payload(agent_id, tool_name="send_email"),
        headers={"X-AGCP-API-Key": SERVICE_API_KEY},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == (
        "Service actor is not permitted for this tool name."
    )
    assert fetch_agent_runs(session_factory) == []
    assert fetch_trace_events(session_factory) == []
    assert fetch_policy_decisions(session_factory) == []


def test_runtime_service_api_key_without_decision_scope_is_rejected_without_records(
    api_client: tuple[TestClient, SessionFactory],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configure_service_actor_api_key(
        monkeypatch,
        scopes=("telemetry:write",),
        require_auth=True,
    )
    client, session_factory = api_client
    agent_id = create_agent(session_factory)

    response = client.post(
        "/runtime/tool-calls/decision",
        json=runtime_decision_payload(agent_id),
        headers={"X-AGCP-API-Key": SERVICE_API_KEY},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == (
        "Service actor requires scope: runtime:decision."
    )
    assert SERVICE_API_KEY not in response.text
    assert fetch_agent_runs(session_factory) == []
    assert fetch_trace_events(session_factory) == []
    assert fetch_policy_decisions(session_factory) == []
    assert fetch_human_approvals(session_factory) == []
    assert fetch_human_approval_audit_logs(session_factory) == []


def test_runtime_service_scope_rule_allows_matching_agent_environment_mode_and_tool(
    api_client: tuple[TestClient, SessionFactory],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    configure_service_actor_api_key(
        monkeypatch,
        require_auth=True,
        scope_rule={
            "agent_ids": [str(agent_id)],
            "environments": ["development"],
            "runtime_modes": ["simulation"],
            "tool_names": ["send_email"],
        },
    )

    response = client.post(
        "/runtime/tool-calls/decision",
        json=runtime_decision_payload(agent_id),
        headers={"X-AGCP-API-Key": SERVICE_API_KEY},
    )

    assert response.status_code == 201
    assert len(fetch_trace_events(session_factory)) == 1
    assert len(fetch_policy_decisions(session_factory)) == 1


def test_runtime_service_scope_rule_denies_non_matching_agent_without_records(
    api_client: tuple[TestClient, SessionFactory],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    configure_service_actor_api_key(
        monkeypatch,
        require_auth=True,
        scope_rule={
            "agent_ids": [str(uuid4())],
            "environments": ["development"],
            "runtime_modes": ["simulation"],
            "tool_names": ["send_email"],
        },
    )

    response = client.post(
        "/runtime/tool-calls/decision",
        json=runtime_decision_payload(agent_id),
        headers={"X-AGCP-API-Key": SERVICE_API_KEY},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == (
        "Service actor is not permitted for this agent."
    )
    assert SERVICE_API_KEY not in response.text
    assert fetch_agent_runs(session_factory) == []
    assert fetch_trace_events(session_factory) == []
    assert fetch_policy_decisions(session_factory) == []


def test_runtime_service_scope_rule_denies_non_matching_environment_without_records(
    api_client: tuple[TestClient, SessionFactory],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory, environment=Environment.DEVELOPMENT)
    configure_service_actor_api_key(
        monkeypatch,
        require_auth=True,
        scope_rule={
            "agent_ids": [str(agent_id)],
            "environments": ["staging"],
            "runtime_modes": ["simulation"],
            "tool_names": ["send_email"],
        },
    )

    response = client.post(
        "/runtime/tool-calls/decision",
        json=runtime_decision_payload(agent_id),
        headers={"X-AGCP-API-Key": SERVICE_API_KEY},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == (
        "Service actor is not permitted for this environment."
    )
    assert fetch_agent_runs(session_factory) == []
    assert fetch_trace_events(session_factory) == []
    assert fetch_policy_decisions(session_factory) == []


def test_runtime_service_scope_rule_denies_non_matching_mode_without_records(
    api_client: tuple[TestClient, SessionFactory],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    configure_service_actor_api_key(
        monkeypatch,
        require_auth=True,
        scope_rule={
            "agent_ids": [str(agent_id)],
            "environments": ["development"],
            "runtime_modes": ["enforcement"],
            "tool_names": ["send_email"],
        },
    )

    response = client.post(
        "/runtime/tool-calls/decision",
        json=runtime_decision_payload(agent_id, mode="simulation"),
        headers={"X-AGCP-API-Key": SERVICE_API_KEY},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == (
        "Service actor is not permitted for this runtime mode."
    )
    assert fetch_agent_runs(session_factory) == []
    assert fetch_trace_events(session_factory) == []
    assert fetch_policy_decisions(session_factory) == []


def test_runtime_service_scope_rule_denies_non_matching_tool_without_records(
    api_client: tuple[TestClient, SessionFactory],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    configure_service_actor_api_key(
        monkeypatch,
        require_auth=True,
        scope_rule={
            "agent_ids": [str(agent_id)],
            "environments": ["development"],
            "runtime_modes": ["simulation"],
            "tool_names": ["send_payment"],
        },
    )

    response = client.post(
        "/runtime/tool-calls/decision",
        json=runtime_decision_payload(agent_id, tool_name="send_email"),
        headers={"X-AGCP-API-Key": SERVICE_API_KEY},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == (
        "Service actor is not permitted for this tool name."
    )
    assert fetch_agent_runs(session_factory) == []
    assert fetch_trace_events(session_factory) == []
    assert fetch_policy_decisions(session_factory) == []


def test_runtime_service_scope_rule_wildcard_allows_broad_access_explicitly(
    api_client: tuple[TestClient, SessionFactory],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configure_service_actor_api_key(monkeypatch, require_auth=True)
    client, session_factory = api_client
    agent_id = create_agent(session_factory, environment=Environment.STAGING)

    response = client.post(
        "/runtime/tool-calls/decision",
        json=runtime_decision_payload(agent_id),
        headers={"X-AGCP-API-Key": SERVICE_API_KEY},
    )

    assert response.status_code == 201
    assert len(fetch_trace_events(session_factory)) == 1


def test_runtime_missing_fine_grained_rule_in_strict_mode_denies_without_records(
    api_client: tuple[TestClient, SessionFactory],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configure_service_actor_api_key(
        monkeypatch,
        require_auth=True,
        include_scope_rule=False,
    )
    client, session_factory = api_client
    agent_id = create_agent(session_factory)

    response = client.post(
        "/runtime/tool-calls/decision",
        json=runtime_decision_payload(agent_id),
        headers={"X-AGCP-API-Key": SERVICE_API_KEY},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == (
        "Service actor requires a fine-grained scope rule."
    )
    assert SERVICE_API_KEY not in response.text
    assert fetch_agent_runs(session_factory) == []
    assert fetch_trace_events(session_factory) == []
    assert fetch_policy_decisions(session_factory) == []


def test_runtime_invalid_service_api_key_is_rejected_without_records(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)

    response = client.post(
        "/runtime/tool-calls/decision",
        json=runtime_decision_payload(agent_id),
        headers={"X-AGCP-API-Key": "invalid-local-test-key"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid AGCP service actor API key."
    assert fetch_agent_runs(session_factory) == []
    assert fetch_trace_events(session_factory) == []
    assert fetch_policy_decisions(session_factory) == []
    assert fetch_human_approvals(session_factory) == []
    assert fetch_human_approval_audit_logs(session_factory) == []


def test_runtime_simulation_without_matching_policy_returns_not_applicable(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    create_policy_rule(
        session_factory,
        decision=PolicyDecisionValue.DENY,
        reason="Payment tool use is denied.",
        tool_name="send_payment",
    )

    response = client.post(
        "/runtime/tool-calls/decision",
        json=runtime_decision_payload(agent_id),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["decision"] == "not_applicable"
    assert body["proceed"] is False
    assert body["human_approval_id"] is None
    [policy_decision] = fetch_policy_decisions(session_factory)
    assert policy_decision.decision is PolicyDecisionValue.NOT_APPLICABLE
    assert policy_decision.policy_id is None
    assert policy_decision.rule_id is None
    assert fetch_human_approvals(session_factory) == []


def test_runtime_policy_evaluation_failure_defaults_to_fail_closed_deny(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    create_unsupported_policy_rule(session_factory)

    response = client.post(
        "/runtime/tool-calls/decision",
        json=runtime_decision_payload(agent_id),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["decision"] == "deny"
    assert body["proceed"] is False
    assert body["reason"] == (
        "Policy evaluation failed; runtime failure policy fail_closed_deny "
        "selected deny."
    )
    assert body["trace_event_id"] is not None
    assert body["policy_decision_id"] is not None
    assert body["human_approval_id"] is None

    [trace_event] = fetch_trace_events(session_factory)
    assert trace_event.metadata_ == {
        "ticket_category": "support",
        "tool_name": "send_email",
        "runtime_failure_category": "policy_evaluation",
        "runtime_failure_default": "fail_closed_deny",
    }
    [policy_decision] = fetch_policy_decisions(session_factory)
    assert policy_decision.decision is PolicyDecisionValue.DENY
    assert policy_decision.trace_event_id == trace_event.id
    assert policy_decision.policy_id is None
    assert policy_decision.rule_id is None
    assert fetch_human_approvals(session_factory) == []
    assert fetch_human_approval_audit_logs(session_factory) == []


def test_runtime_policy_evaluation_failure_can_fail_closed_to_human_review(
    api_client: tuple[TestClient, SessionFactory],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AGCP_RUNTIME_FAILURE_DEFAULT", "fail_closed_human_review")
    get_settings.cache_clear()
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    create_unsupported_policy_rule(session_factory)

    response = client.post(
        "/runtime/tool-calls/decision",
        json=runtime_decision_payload(agent_id),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["decision"] == "require_human_review"
    assert body["proceed"] is False
    assert body["reason"] == (
        "Policy evaluation failed; runtime failure policy "
        "fail_closed_human_review requested human review."
    )
    assert body["trace_event_id"] is not None
    assert body["policy_decision_id"] is not None
    assert body["human_approval_id"] is not None

    [trace_event] = fetch_trace_events(session_factory)
    assert trace_event.metadata_ == {
        "ticket_category": "support",
        "tool_name": "send_email",
        "runtime_failure_category": "policy_evaluation",
        "runtime_failure_default": "fail_closed_human_review",
    }
    [policy_decision] = fetch_policy_decisions(session_factory)
    [human_approval] = fetch_human_approvals(session_factory)
    [audit_log] = fetch_human_approval_audit_logs(session_factory)
    assert policy_decision.decision is PolicyDecisionValue.REQUIRE_HUMAN_REVIEW
    assert policy_decision.trace_event_id == trace_event.id
    assert human_approval.policy_decision_id == policy_decision.id
    assert human_approval.requested_by_actor_type is ActorType.DEVELOPMENT
    assert human_approval.requested_by_actor_id == "dev-placeholder"
    assert audit_log.event_type == "human_approval_requested"
    assert audit_log.actor_type is ActorType.DEVELOPMENT
    assert audit_log.actor_id == "dev-placeholder"
    assert audit_log.entity_id == str(human_approval.id)


def test_runtime_policy_evaluation_failure_can_record_only_in_simulation(
    api_client: tuple[TestClient, SessionFactory],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AGCP_RUNTIME_FAILURE_DEFAULT", "record_only")
    get_settings.cache_clear()
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    create_unsupported_policy_rule(session_factory)

    response = client.post(
        "/runtime/tool-calls/decision",
        json=runtime_decision_payload(agent_id),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["decision"] == "not_applicable"
    assert body["proceed"] is False
    assert body["reason"] == (
        "Policy evaluation failed; runtime failure policy record_only recorded "
        "the failure in simulation mode."
    )
    assert body["trace_event_id"] is not None
    assert body["policy_decision_id"] is None
    assert body["human_approval_id"] is None

    [trace_event] = fetch_trace_events(session_factory)
    assert trace_event.metadata_ == {
        "ticket_category": "support",
        "tool_name": "send_email",
        "runtime_failure_category": "policy_evaluation",
        "runtime_failure_default": "record_only",
    }
    assert fetch_policy_decisions(session_factory) == []
    assert fetch_human_approvals(session_factory) == []
    assert fetch_human_approval_audit_logs(session_factory) == []


def test_runtime_record_only_policy_failure_fails_closed_in_enforcement(
    api_client: tuple[TestClient, SessionFactory],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AGCP_RUNTIME_FAILURE_DEFAULT", "record_only")
    enable_runtime_enforcement(monkeypatch)
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    create_unsupported_policy_rule(session_factory)

    response = client.post(
        "/runtime/tool-calls/decision",
        json=runtime_decision_payload(agent_id, mode="enforcement"),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["decision"] == "deny"
    assert body["proceed"] is False
    assert body["reason"] == (
        "Policy evaluation failed; runtime failure policy fail_closed_deny "
        "selected deny."
    )
    assert body["policy_decision_id"] is not None
    assert body["human_approval_id"] is None

    [trace_event] = fetch_trace_events(session_factory)
    assert trace_event.metadata_["runtime_failure_default"] == "fail_closed_deny"
    [policy_decision] = fetch_policy_decisions(session_factory)
    assert policy_decision.decision is PolicyDecisionValue.DENY
    assert fetch_human_approvals(session_factory) == []


def test_duplicate_record_only_policy_failure_returns_existing_response(
    api_client: tuple[TestClient, SessionFactory],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AGCP_RUNTIME_FAILURE_DEFAULT", "record_only")
    get_settings.cache_clear()
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    run_id = uuid4()
    create_unsupported_policy_rule(session_factory)

    first_response = client.post(
        "/runtime/tool-calls/decision",
        json=runtime_decision_payload(agent_id, run_id=run_id),
    )
    duplicate_response = client.post(
        "/runtime/tool-calls/decision",
        json=runtime_decision_payload(
            agent_id,
            run_id=run_id,
            action_summary="Retried request with changed summary.",
        ),
    )

    assert first_response.status_code == 201
    assert duplicate_response.status_code == 200
    assert duplicate_response.json() == first_response.json()
    assert len(fetch_agent_runs(session_factory)) == 1
    assert len(fetch_trace_events(session_factory)) == 1
    assert fetch_policy_decisions(session_factory) == []
    assert fetch_human_approvals(session_factory) == []
    assert fetch_human_approval_audit_logs(session_factory) == []


def test_runtime_failure_policy_persistence_failure_rolls_back_trace_event(
    api_client: tuple[TestClient, SessionFactory],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    create_unsupported_policy_rule(session_factory)

    def fail_policy_decision_persistence(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("failure policy decision persistence failed")

    monkeypatch.setattr(
        runtime_gateway_api,
        "persist_policy_decision",
        fail_policy_decision_persistence,
    )

    with pytest.raises(
        RuntimeError,
        match="failure policy decision persistence failed",
    ):
        client.post(
            "/runtime/tool-calls/decision",
            json=runtime_decision_payload(agent_id),
        )

    assert fetch_agent_runs(session_factory) == []
    assert fetch_trace_events(session_factory) == []
    assert fetch_policy_decisions(session_factory) == []
    assert fetch_human_approvals(session_factory) == []
    assert fetch_human_approval_audit_logs(session_factory) == []


def test_runtime_failure_policy_audit_failure_rolls_back_human_review_records(
    api_client: tuple[TestClient, SessionFactory],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AGCP_RUNTIME_FAILURE_DEFAULT", "fail_closed_human_review")
    get_settings.cache_clear()
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    create_unsupported_policy_rule(session_factory)

    def fail_audit_log(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("failure policy audit log failed")

    monkeypatch.setattr(runtime_gateway_api, "append_audit_log", fail_audit_log)

    with pytest.raises(RuntimeError, match="failure policy audit log failed"):
        client.post(
            "/runtime/tool-calls/decision",
            json=runtime_decision_payload(agent_id),
        )

    assert fetch_agent_runs(session_factory) == []
    assert fetch_trace_events(session_factory) == []
    assert fetch_policy_decisions(session_factory) == []
    assert fetch_human_approvals(session_factory) == []
    assert fetch_human_approval_audit_logs(session_factory) == []


def test_runtime_enforcement_with_allow_policy_returns_allow(
    api_client: tuple[TestClient, SessionFactory],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    enable_runtime_enforcement(monkeypatch)
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    policy_id, rule_id = create_policy_rule(
        session_factory,
        decision=PolicyDecisionValue.ALLOW,
        reason="The requested tool is allowed.",
    )

    response = client.post(
        "/runtime/tool-calls/decision",
        json=runtime_decision_payload(agent_id, mode="enforcement"),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["decision"] == "allow"
    assert body["proceed"] is True
    assert body["human_approval_id"] is None
    [agent_run] = fetch_agent_runs(session_factory)
    assert agent_run.status == "enforced"
    [policy_decision] = fetch_policy_decisions(session_factory)
    assert policy_decision.decision is PolicyDecisionValue.ALLOW
    assert policy_decision.policy_id == policy_id
    assert policy_decision.rule_id == rule_id
    assert fetch_human_approvals(session_factory) == []


def test_runtime_enforcement_with_deny_policy_returns_deny(
    api_client: tuple[TestClient, SessionFactory],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    enable_runtime_enforcement(monkeypatch)
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    create_policy_rule(
        session_factory,
        decision=PolicyDecisionValue.DENY,
        reason="The requested tool is denied.",
    )

    response = client.post(
        "/runtime/tool-calls/decision",
        json=runtime_decision_payload(agent_id, mode="enforcement"),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["decision"] == "deny"
    assert body["proceed"] is False
    assert body["human_approval_id"] is None
    [policy_decision] = fetch_policy_decisions(session_factory)
    assert policy_decision.decision is PolicyDecisionValue.DENY
    assert fetch_human_approvals(session_factory) == []


def test_runtime_enforcement_with_review_policy_creates_human_approval(
    api_client: tuple[TestClient, SessionFactory],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    enable_runtime_enforcement(monkeypatch)
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    create_policy_rule(
        session_factory,
        decision=PolicyDecisionValue.REQUIRE_HUMAN_REVIEW,
        reason="The requested tool requires human review.",
    )

    response = client.post(
        "/runtime/tool-calls/decision",
        json=runtime_decision_payload(agent_id, mode="enforcement"),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["decision"] == "require_human_review"
    assert body["proceed"] is False
    assert body["human_approval_id"] is not None

    [policy_decision] = fetch_policy_decisions(session_factory)
    [approval] = fetch_human_approvals(session_factory)
    assert approval.id == UUID(body["human_approval_id"])
    assert approval.policy_decision_id == policy_decision.id
    assert approval.status is HumanApprovalStatus.PENDING
    [audit_log] = fetch_human_approval_audit_logs(session_factory)
    assert audit_log.event_type == "human_approval_requested"
    assert audit_log.entity_id == str(approval.id)


def test_runtime_enforcement_without_matching_policy_returns_not_applicable(
    api_client: tuple[TestClient, SessionFactory],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    enable_runtime_enforcement(monkeypatch)
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    create_policy_rule(
        session_factory,
        decision=PolicyDecisionValue.DENY,
        reason="Payment tool use is denied.",
        tool_name="send_payment",
    )

    response = client.post(
        "/runtime/tool-calls/decision",
        json=runtime_decision_payload(agent_id, mode="enforcement"),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["decision"] == "not_applicable"
    assert body["proceed"] is False
    assert body["human_approval_id"] is None
    [policy_decision] = fetch_policy_decisions(session_factory)
    assert policy_decision.decision is PolicyDecisionValue.NOT_APPLICABLE
    assert fetch_human_approvals(session_factory) == []


def test_runtime_simulation_unknown_agent_returns_404(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client

    response = client.post(
        "/runtime/tool-calls/decision",
        json=runtime_decision_payload(uuid4()),
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Agent not found."
    assert fetch_agent_runs(session_factory) == []
    assert fetch_trace_events(session_factory) == []
    assert fetch_policy_decisions(session_factory) == []
    assert fetch_human_approvals(session_factory) == []
    assert fetch_human_approval_audit_logs(session_factory) == []


def test_runtime_unknown_agent_still_fails_closed_with_record_only_config(
    api_client: tuple[TestClient, SessionFactory],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AGCP_RUNTIME_FAILURE_DEFAULT", "record_only")
    get_settings.cache_clear()
    client, session_factory = api_client

    response = client.post(
        "/runtime/tool-calls/decision",
        json=runtime_decision_payload(uuid4()),
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Agent not found."
    assert fetch_agent_runs(session_factory) == []
    assert fetch_trace_events(session_factory) == []
    assert fetch_policy_decisions(session_factory) == []
    assert fetch_human_approvals(session_factory) == []
    assert fetch_human_approval_audit_logs(session_factory) == []


def test_runtime_gateway_rejects_telemetry_mode(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    payload = runtime_decision_payload(agent_id)
    payload["mode"] = "telemetry"

    response = client.post("/runtime/tool-calls/decision", json=payload)

    assert response.status_code == 501
    assert response.json()["detail"] == (
        "Runtime Gateway telemetry mode is not implemented for this endpoint yet. "
        "Use POST /telemetry/events for telemetry ingestion."
    )
    assert fetch_agent_runs(session_factory) == []
    assert fetch_trace_events(session_factory) == []
    assert fetch_policy_decisions(session_factory) == []
    assert fetch_human_approvals(session_factory) == []
    assert fetch_human_approval_audit_logs(session_factory) == []


def test_runtime_gateway_rejects_enforcement_when_disabled(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    payload = runtime_decision_payload(agent_id, mode="enforcement")

    response = client.post("/runtime/tool-calls/decision", json=payload)

    assert response.status_code == 501
    assert response.json()["detail"] == (
        "Runtime Gateway enforcement mode is disabled. Set "
        "AGCP_RUNTIME_ENFORCEMENT_ENABLED=true to enable it."
    )
    assert fetch_agent_runs(session_factory) == []
    assert fetch_trace_events(session_factory) == []
    assert fetch_policy_decisions(session_factory) == []
    assert fetch_human_approvals(session_factory) == []
    assert fetch_human_approval_audit_logs(session_factory) == []


def test_runtime_request_missing_tool_name_is_rejected_by_schema(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    payload = runtime_decision_payload(agent_id)
    payload.pop("tool_name")

    response = client.post("/runtime/tool-calls/decision", json=payload)

    assert response.status_code == 422
    assert fetch_agent_runs(session_factory) == []
    assert fetch_trace_events(session_factory) == []
    assert fetch_policy_decisions(session_factory) == []
    assert fetch_human_approvals(session_factory) == []
    assert fetch_human_approval_audit_logs(session_factory) == []


def test_runtime_request_unsafe_metadata_is_rejected(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    payload = runtime_decision_payload(agent_id)
    payload["metadata"] = {"api_key": "redacted"}

    response = client.post("/runtime/tool-calls/decision", json=payload)

    assert response.status_code == 422
    assert fetch_agent_runs(session_factory) == []
    assert fetch_trace_events(session_factory) == []
    assert fetch_policy_decisions(session_factory) == []
    assert fetch_human_approvals(session_factory) == []
    assert fetch_human_approval_audit_logs(session_factory) == []


@pytest.mark.parametrize("metadata_key", ["raw_content", "chunks", "prompt"])
def test_runtime_request_rejects_raw_context_payload_metadata_without_records(
    api_client: tuple[TestClient, SessionFactory],
    metadata_key: str,
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    payload = runtime_decision_payload(agent_id)
    payload["metadata"] = {metadata_key: "do-not-store"}

    response = client.post("/runtime/tool-calls/decision", json=payload)

    assert response.status_code == 422
    assert fetch_agent_runs(session_factory) == []
    assert fetch_trace_events(session_factory) == []
    assert fetch_policy_decisions(session_factory) == []
    assert fetch_human_approvals(session_factory) == []
    assert fetch_human_approval_audit_logs(session_factory) == []


def test_runtime_unsafe_metadata_still_fails_closed_with_record_only_config(
    api_client: tuple[TestClient, SessionFactory],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AGCP_RUNTIME_FAILURE_DEFAULT", "record_only")
    get_settings.cache_clear()
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    payload = runtime_decision_payload(agent_id)
    payload["metadata"] = {"api_key": "redacted"}

    response = client.post("/runtime/tool-calls/decision", json=payload)

    assert response.status_code == 422
    assert fetch_agent_runs(session_factory) == []
    assert fetch_trace_events(session_factory) == []
    assert fetch_policy_decisions(session_factory) == []
    assert fetch_human_approvals(session_factory) == []
    assert fetch_human_approval_audit_logs(session_factory) == []


def test_duplicate_runtime_request_returns_existing_response(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    run_id = uuid4()
    create_policy_rule(
        session_factory,
        decision=PolicyDecisionValue.REQUIRE_HUMAN_REVIEW,
        reason="The requested tool requires human review.",
    )

    first_response = client.post(
        "/runtime/tool-calls/decision",
        json=runtime_decision_payload(agent_id, run_id=run_id),
    )
    duplicate_response = client.post(
        "/runtime/tool-calls/decision",
        json=runtime_decision_payload(
            agent_id,
            run_id=run_id,
            action_summary="Retried request with changed summary.",
        ),
    )

    assert first_response.status_code == 201
    assert duplicate_response.status_code == 200
    assert duplicate_response.json() == first_response.json()
    assert len(fetch_agent_runs(session_factory)) == 1
    assert len(fetch_trace_events(session_factory)) == 1
    assert len(fetch_policy_decisions(session_factory)) == 1
    assert len(fetch_human_approvals(session_factory)) == 1
    assert len(fetch_human_approval_audit_logs(session_factory)) == 1


def test_duplicate_runtime_enforcement_request_returns_existing_response(
    api_client: tuple[TestClient, SessionFactory],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    enable_runtime_enforcement(monkeypatch)
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    run_id = uuid4()
    create_policy_rule(
        session_factory,
        decision=PolicyDecisionValue.REQUIRE_HUMAN_REVIEW,
        reason="The requested tool requires human review.",
    )

    first_response = client.post(
        "/runtime/tool-calls/decision",
        json=runtime_decision_payload(agent_id, run_id=run_id, mode="enforcement"),
    )
    duplicate_response = client.post(
        "/runtime/tool-calls/decision",
        json=runtime_decision_payload(
            agent_id,
            run_id=run_id,
            action_summary="Retried request with changed summary.",
            mode="enforcement",
        ),
    )

    assert first_response.status_code == 201
    assert duplicate_response.status_code == 200
    assert duplicate_response.json() == first_response.json()
    assert len(fetch_agent_runs(session_factory)) == 1
    assert len(fetch_trace_events(session_factory)) == 1
    assert len(fetch_policy_decisions(session_factory)) == 1
    assert len(fetch_human_approvals(session_factory)) == 1
    assert len(fetch_human_approval_audit_logs(session_factory)) == 1


def test_runtime_decision_records_are_atomic_when_policy_persistence_fails(
    api_client: tuple[TestClient, SessionFactory],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    create_policy_rule(
        session_factory,
        decision=PolicyDecisionValue.DENY,
        reason="The requested tool is denied.",
    )

    def fail_policy_decision_persistence(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("policy decision persistence failed")

    monkeypatch.setattr(
        runtime_gateway_api,
        "persist_policy_decision",
        fail_policy_decision_persistence,
    )

    with pytest.raises(RuntimeError, match="policy decision persistence failed"):
        client.post(
            "/runtime/tool-calls/decision",
            json=runtime_decision_payload(agent_id),
        )

    assert fetch_agent_runs(session_factory) == []
    assert fetch_trace_events(session_factory) == []
    assert fetch_policy_decisions(session_factory) == []
    assert fetch_human_approvals(session_factory) == []
    assert fetch_human_approval_audit_logs(session_factory) == []


def test_runtime_enforcement_records_are_atomic_when_policy_persistence_fails(
    api_client: tuple[TestClient, SessionFactory],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    enable_runtime_enforcement(monkeypatch)
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    create_policy_rule(
        session_factory,
        decision=PolicyDecisionValue.DENY,
        reason="The requested tool is denied.",
    )

    def fail_policy_decision_persistence(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("policy decision persistence failed")

    monkeypatch.setattr(
        runtime_gateway_api,
        "persist_policy_decision",
        fail_policy_decision_persistence,
    )

    with pytest.raises(RuntimeError, match="policy decision persistence failed"):
        client.post(
            "/runtime/tool-calls/decision",
            json=runtime_decision_payload(agent_id, mode="enforcement"),
        )

    assert fetch_agent_runs(session_factory) == []
    assert fetch_trace_events(session_factory) == []
    assert fetch_policy_decisions(session_factory) == []
    assert fetch_human_approvals(session_factory) == []
    assert fetch_human_approval_audit_logs(session_factory) == []


def test_runtime_decision_records_are_atomic_when_human_approval_creation_fails(
    api_client: tuple[TestClient, SessionFactory],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    create_policy_rule(
        session_factory,
        decision=PolicyDecisionValue.REQUIRE_HUMAN_REVIEW,
        reason="The requested tool requires human review.",
    )

    def fail_human_approval_creation(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("human approval creation failed")

    monkeypatch.setattr(
        runtime_gateway_api,
        "_create_human_approval_for_policy_decision",
        fail_human_approval_creation,
    )

    with pytest.raises(RuntimeError, match="human approval creation failed"):
        client.post(
            "/runtime/tool-calls/decision",
            json=runtime_decision_payload(agent_id),
        )

    assert fetch_agent_runs(session_factory) == []
    assert fetch_trace_events(session_factory) == []
    assert fetch_policy_decisions(session_factory) == []
    assert fetch_human_approvals(session_factory) == []
    assert fetch_human_approval_audit_logs(session_factory) == []


def test_runtime_decision_records_are_atomic_when_audit_log_fails(
    api_client: tuple[TestClient, SessionFactory],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    create_policy_rule(
        session_factory,
        decision=PolicyDecisionValue.REQUIRE_HUMAN_REVIEW,
        reason="The requested tool requires human review.",
    )

    def fail_audit_log(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("audit log persistence failed")

    monkeypatch.setattr(runtime_gateway_api, "append_audit_log", fail_audit_log)

    with pytest.raises(RuntimeError, match="audit log persistence failed"):
        client.post(
            "/runtime/tool-calls/decision",
            json=runtime_decision_payload(agent_id),
        )

    assert fetch_agent_runs(session_factory) == []
    assert fetch_trace_events(session_factory) == []
    assert fetch_policy_decisions(session_factory) == []
    assert fetch_human_approvals(session_factory) == []
    assert fetch_human_approval_audit_logs(session_factory) == []


def test_evidence_bundle_includes_runtime_trace_event_and_policy_decision(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    create_policy_rule(
        session_factory,
        decision=PolicyDecisionValue.DENY,
        reason="The requested tool is denied.",
    )

    runtime_response = client.post(
        "/runtime/tool-calls/decision",
        json=runtime_decision_payload(agent_id),
    )
    set_evidence_export_actor()
    bundle_response = client.get(f"/agents/{agent_id}/evidence-bundle")

    assert runtime_response.status_code == 201
    assert bundle_response.status_code == 200
    runtime_body = runtime_response.json()
    bundle_body = bundle_response.json()

    [trace_event] = bundle_body["trace_events"]
    [policy_decision] = bundle_body["policy_decisions"]
    assert trace_event["id"] == runtime_body["trace_event_id"]
    assert trace_event["agent_id"] == str(agent_id)
    assert trace_event["run_id"] == runtime_body["run_id"]
    assert trace_event["external_event_id"] == "runtime-request-001"
    assert trace_event["event_type"] == "tool_call_requested"
    assert trace_event["metadata"] == {
        "ticket_category": "support",
        "tool_name": "send_email",
    }

    assert policy_decision["id"] == runtime_body["policy_decision_id"]
    assert policy_decision["agent_id"] == str(agent_id)
    assert policy_decision["trace_event_id"] == trace_event["id"]
    assert policy_decision["decision"] == "deny"
    assert policy_decision["policy"]
    assert policy_decision["rule"]


def test_evidence_bundle_includes_safe_runtime_context_metadata(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    create_policy_rule(
        session_factory,
        decision=PolicyDecisionValue.DENY,
        reason="The contextual action is denied.",
        tool_name="vectorize_source",
    )
    capability_id = uuid4()
    source_id = uuid4()
    model_id = uuid4()
    payload = runtime_decision_payload(
        agent_id,
        action_summary="Vectorize a governed source for semantic search.",
        tool_name="vectorize_source",
    )
    payload.update(
        {
            "action_type": "vectorize",
            "capability_id": str(capability_id),
            "source_ids": [str(source_id)],
            "model_id": str(model_id),
            "purpose": "semantic_search_indexing",
            "data_classification": "restricted",
            "contains_personal_data": True,
            "contains_sensitive_data": True,
        }
    )

    runtime_response = client.post("/runtime/tool-calls/decision", json=payload)
    set_evidence_export_actor()
    bundle_response = client.get(f"/agents/{agent_id}/evidence-bundle")

    assert runtime_response.status_code == 201
    assert bundle_response.status_code == 200
    [trace_event] = bundle_response.json()["trace_events"]
    assert trace_event["metadata"] == {
        "ticket_category": "support",
        "tool_name": "vectorize_source",
        "action_type": "vectorize",
        "capability_id": str(capability_id),
        "resolved_capability_status": "missing",
        "resolved_missing_capability_id": str(capability_id),
        "source_ids": str(source_id),
        "resolved_source_statuses": "missing",
        "resolved_missing_source_ids": str(source_id),
        "resolved_data_usage_review_statuses": "missing",
        "model_id": str(model_id),
        "resolved_model_status": "missing",
        "resolved_missing_model_id": str(model_id),
        "resolved_access_grant_statuses": "missing",
        "resolved_missing_access_grant_targets": (
            f"capability:{capability_id},source:{source_id},model_asset:{model_id}"
        ),
        "purpose": "semantic_search_indexing",
        "data_classification": "restricted",
        "contains_personal_data": True,
        "contains_sensitive_data": True,
    }


def test_evidence_bundle_includes_runtime_review_evidence_chain(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    run_id = uuid4()
    policy_id, rule_id = create_policy_rule(
        session_factory,
        decision=PolicyDecisionValue.REQUIRE_HUMAN_REVIEW,
        reason="The requested tool requires human review.",
    )

    runtime_response = client.post(
        "/runtime/tool-calls/decision",
        json=runtime_decision_payload(agent_id, run_id=run_id),
    )

    assert runtime_response.status_code == 201
    runtime_body = runtime_response.json()
    assert runtime_body["decision"] == "require_human_review"
    assert runtime_body["proceed"] is False
    assert runtime_body["human_approval_id"] is not None

    [agent_run] = fetch_agent_runs(session_factory)
    [trace_event] = fetch_trace_events(session_factory)
    [policy_decision] = fetch_policy_decisions(session_factory)
    [human_approval] = fetch_human_approvals(session_factory)
    [audit_log] = fetch_human_approval_audit_logs(session_factory)

    assert agent_run.agent_id == agent_id
    assert agent_run.run_id == run_id
    assert agent_run.status == "simulated"

    assert trace_event.id == UUID(runtime_body["trace_event_id"])
    assert trace_event.agent_id == agent_id
    assert trace_event.run_id == run_id
    assert trace_event.external_event_id == "runtime-request-001"
    assert trace_event.event_type is TraceEventType.TOOL_CALL_REQUESTED

    assert policy_decision.id == UUID(runtime_body["policy_decision_id"])
    assert policy_decision.agent_id == agent_id
    assert policy_decision.policy_id == policy_id
    assert policy_decision.rule_id == rule_id
    assert policy_decision.trace_event_id == trace_event.id
    assert policy_decision.decision is PolicyDecisionValue.REQUIRE_HUMAN_REVIEW

    assert human_approval.id == UUID(runtime_body["human_approval_id"])
    assert human_approval.agent_id == agent_id
    assert human_approval.policy_decision_id == policy_decision.id
    assert human_approval.status is HumanApprovalStatus.PENDING

    assert audit_log.event_type == "human_approval_requested"
    assert audit_log.entity_type == "human_approval"
    assert audit_log.entity_id == str(human_approval.id)
    assert audit_log.metadata_ == {
        "agent_id": str(agent_id),
        "status": "pending",
        "policy_decision_id": str(policy_decision.id),
    }

    set_evidence_export_actor()
    bundle_response = client.get(f"/agents/{agent_id}/evidence-bundle")

    assert bundle_response.status_code == 200
    bundle_body = bundle_response.json()
    [bundle_agent_run] = bundle_body["agent_runs"]
    [bundle_trace_event] = bundle_body["trace_events"]
    [bundle_policy_decision] = bundle_body["policy_decisions"]
    [bundle_human_approval] = bundle_body["human_approvals"]
    human_approval_audit_logs = [
        bundle_audit_log
        for bundle_audit_log in bundle_body["audit_logs"]
        if bundle_audit_log["event_type"] == "human_approval_requested"
    ]
    [bundle_audit_log] = human_approval_audit_logs

    assert bundle_agent_run["run_id"] == str(run_id)
    assert bundle_agent_run["status"] == "simulated"

    assert bundle_trace_event["id"] == str(trace_event.id)
    assert bundle_trace_event["agent_id"] == str(agent_id)
    assert bundle_trace_event["run_id"] == str(run_id)
    assert bundle_trace_event["external_event_id"] == "runtime-request-001"
    assert bundle_trace_event["event_type"] == "tool_call_requested"
    assert bundle_trace_event["metadata"] == {
        "ticket_category": "support",
        "tool_name": "send_email",
    }

    assert bundle_policy_decision["id"] == str(policy_decision.id)
    assert bundle_policy_decision["agent_id"] == str(agent_id)
    assert bundle_policy_decision["policy_id"] == str(policy_id)
    assert bundle_policy_decision["rule_id"] == str(rule_id)
    assert bundle_policy_decision["trace_event_id"] == bundle_trace_event["id"]
    assert bundle_policy_decision["decision"] == "require_human_review"
    assert bundle_policy_decision["policy"] == {
        "id": str(policy_id),
        "name": "Tool access policy",
        "status": "active",
    }
    assert bundle_policy_decision["rule"] == {
        "id": str(rule_id),
        "policy_id": str(policy_id),
        "name": "Tool access rule",
    }

    assert bundle_human_approval["id"] == str(human_approval.id)
    assert bundle_human_approval["agent_id"] == str(agent_id)
    assert bundle_human_approval["policy_decision_id"] == bundle_policy_decision["id"]
    assert bundle_human_approval["status"] == "pending"
    assert bundle_human_approval["requested_by_actor_type"] == "development"
    assert bundle_human_approval["requested_by_actor_id"] == "dev-placeholder"

    assert bundle_audit_log["entity_type"] == "human_approval"
    assert bundle_audit_log["entity_id"] == bundle_human_approval["id"]
    assert bundle_audit_log["metadata"] == {
        "agent_id": str(agent_id),
        "status": "pending",
        "policy_decision_id": bundle_policy_decision["id"],
    }


def create_agent(
    session_factory: SessionFactory,
    *,
    name: str = "Support assistant",
    environment: Environment = Environment.DEVELOPMENT,
) -> UUID:
    with session_factory() as session:
        agent = Agent(
            name=name,
            description=None,
            owner_type=OwnerType.TEAM,
            owner_id="team:ai-platform",
            owner_name="AI Platform",
            owner_contact_email="owner@example.com",
            environment=environment,
            status=AgentStatus.DRAFT,
            risk_level=RiskLevel.LOW,
            framework="LangGraph",
        )
        session.add(agent)
        session.commit()
        return agent.id


def seed_runtime_inventory_context(
    session_factory: SessionFactory,
    *,
    agent_id: UUID,
) -> dict[str, UUID]:
    with session_factory() as session:
        capability = Capability(
            name="Vectorize source",
            description="Governed source vectorization capability.",
            capability_type=CapabilityType.TOOL,
            external_ref="tool:vectorize_source",
            status=CapabilityStatus.ACTIVE,
            risk_level=RiskLevel.HIGH,
            metadata_={"domain": "rag"},
        )
        source = DataSource(
            name="Restricted knowledge source",
            description="Governed source for runtime context tests.",
            source_type=DataSourceType.KNOWLEDGE_BASE,
            external_ref="source:restricted-kb",
            owner_type=OwnerType.TEAM,
            owner_id="team:data-governance",
            owner_name="Data Governance",
            status=DataSourceStatus.ACTIVE,
            risk_level=RiskLevel.HIGH,
            metadata_={"domain": "support"},
        )
        model_asset = ModelAsset(
            name="External embedding model",
            description="Governed embedding model for runtime context tests.",
            model_type=ModelAssetType.EMBEDDING,
            provider=ModelProvider.OPENAI,
            model_ref="embedding:test",
            owner_type=OwnerType.TEAM,
            owner_id="team:model-governance",
            owner_name="Model Governance",
            status=ModelAssetStatus.ACTIVE,
            risk_level=RiskLevel.HIGH,
            metadata_={"domain": "rag"},
        )
        session.add_all([capability, source, model_asset])
        session.flush()

        profile = DataUsageProfile(
            source_id=source.id,
            data_classification=DataUsageClassification.RESTRICTED,
            contains_personal_data=True,
            contains_sensitive_data=True,
            data_categories=["customer_data"],
            allowed_purposes=["semantic_search_indexing"],
            prohibited_purposes=["model_training"],
            allowed_processing=["rag"],
            prohibited_processing=["training"],
            review_status=DataUsageReviewStatus.APPROVED,
            dpia_required=True,
            dpia_reference="dpia:DPIA-123",
            metadata_={"catalog_ref": "catalog:restricted-kb"},
        )
        session.add(profile)
        session.add_all(
            [
                runtime_access_grant(
                    agent_id=agent_id,
                    target_type=AccessGrantTargetType.CAPABILITY,
                    target_id=capability.id,
                ),
                runtime_access_grant(
                    agent_id=agent_id,
                    target_type=AccessGrantTargetType.SOURCE,
                    target_id=source.id,
                ),
                runtime_access_grant(
                    agent_id=agent_id,
                    target_type=AccessGrantTargetType.MODEL_ASSET,
                    target_id=model_asset.id,
                ),
            ]
        )
        session.commit()
        return {
            "capability_id": capability.id,
            "source_id": source.id,
            "model_id": model_asset.id,
        }


def runtime_access_grant(
    *,
    agent_id: UUID,
    target_type: AccessGrantTargetType,
    target_id: UUID,
    status: AccessGrantStatus = AccessGrantStatus.ACTIVE,
) -> AccessGrant:
    return AccessGrant(
        name=f"{target_type.value} runtime access",
        grant_type=access_grant_type_for_target(target_type),
        subject_type=AccessGrantSubjectType.AGENT,
        subject_id=agent_id,
        target_type=target_type,
        target_id=target_id,
        status=status,
        granted_by_actor_type=ActorType.USER,
        granted_by_actor_id="user:governance",
        reason="Runtime context test grant.",
        risk_level=RiskLevel.HIGH,
        metadata_={"ticket": "GOV-RUNTIME"},
    )


def access_grant_type_for_target(
    target_type: AccessGrantTargetType,
) -> AccessGrantType:
    if target_type is AccessGrantTargetType.CAPABILITY:
        return AccessGrantType.CAPABILITY
    if target_type is AccessGrantTargetType.SOURCE:
        return AccessGrantType.SOURCE
    if target_type is AccessGrantTargetType.MODEL_ASSET:
        return AccessGrantType.MODEL
    return AccessGrantType.OTHER


def disable_runtime_source_and_revoke_grant(
    session_factory: SessionFactory,
    *,
    source_id: UUID,
) -> None:
    with session_factory() as session:
        source = session.get(DataSource, source_id)
        assert source is not None
        source.status = DataSourceStatus.DISABLED
        grant = session.scalar(
            select(AccessGrant).where(
                AccessGrant.target_type == AccessGrantTargetType.SOURCE,
                AccessGrant.target_id == source_id,
            )
        )
        assert grant is not None
        grant.status = AccessGrantStatus.REVOKED
        session.commit()


def set_evidence_export_actor() -> None:
    app.dependency_overrides[get_current_actor] = lambda: ActorContext(
        actor_type=ActorType.USER,
        actor_id="user:runtime-auditor",
        roles=("auditor",),
    )


def create_policy_rule(
    session_factory: SessionFactory,
    *,
    decision: PolicyDecisionValue,
    reason: str,
    tool_name: str = "send_email",
    status: PolicyStatus = PolicyStatus.ACTIVE,
    condition: dict[str, object] | None = None,
) -> tuple[UUID, UUID]:
    with session_factory() as session:
        policy = Policy(
            name="Tool access policy",
            description=None,
            status=status,
        )
        session.add(policy)
        session.flush()

        rule = PolicyRule(
            policy_id=policy.id,
            name="Tool access rule",
            description=None,
            condition=json.dumps(
                condition
                or {
                    "decision": decision.value,
                    "reason": reason,
                    "tool_name": tool_name,
                }
            ),
        )
        session.add(rule)
        session.commit()
        return policy.id, rule.id


def create_policy_rule_for_policy(
    session_factory: SessionFactory,
    *,
    policy_id: UUID,
    condition: dict[str, object],
    name: str = "Additional tool access rule",
) -> UUID:
    with session_factory() as session:
        rule = PolicyRule(
            policy_id=policy_id,
            name=name,
            description=None,
            condition=json.dumps(condition),
        )
        session.add(rule)
        session.commit()
        return rule.id


def create_policy_version(
    session_factory: SessionFactory,
    *,
    policy_id: UUID,
    status: PolicyVersionStatus,
    rule_snapshots: list[dict[str, object]],
    check_step_snapshots: list[dict[str, object]] | None = None,
) -> UUID:
    now = datetime.now(UTC)
    submitted_statuses = {
        PolicyVersionStatus.UNDER_REVIEW,
        PolicyVersionStatus.APPROVED,
        PolicyVersionStatus.REJECTED,
        PolicyVersionStatus.ACTIVE,
        PolicyVersionStatus.SUPERSEDED,
        PolicyVersionStatus.ARCHIVED,
    }
    approved_statuses = {
        PolicyVersionStatus.APPROVED,
        PolicyVersionStatus.ACTIVE,
        PolicyVersionStatus.SUPERSEDED,
        PolicyVersionStatus.ARCHIVED,
    }
    activated_statuses = {
        PolicyVersionStatus.ACTIVE,
        PolicyVersionStatus.SUPERSEDED,
        PolicyVersionStatus.ARCHIVED,
    }
    with session_factory() as session:
        policy = session.get(Policy, policy_id)
        assert policy is not None
        version = PolicyVersion(
            policy_id=policy.id,
            version_number=1,
            status=status,
            change_summary="Reviewed runtime policy snapshot.",
            policy_snapshot={
                "id": str(policy.id),
                "name": policy.name,
                "description": policy.description,
                "status": policy.status.value,
            },
            rule_snapshots=rule_snapshots,
            check_step_snapshots=check_step_snapshots or [],
            created_by_actor_type=ActorType.DEVELOPMENT,
            created_by_actor_id="dev-placeholder",
            submitted_at=now if status in submitted_statuses else None,
            approved_at=now if status in approved_statuses else None,
            rejected_at=now if status is PolicyVersionStatus.REJECTED else None,
            activated_at=now if status in activated_statuses else None,
            superseded_at=now if status is PolicyVersionStatus.SUPERSEDED else None,
            archived_at=now if status is PolicyVersionStatus.ARCHIVED else None,
            created_at=now,
            updated_at=now,
        )
        session.add(version)
        session.commit()
        return version.id


def policy_rule_snapshot(
    *,
    policy_id: UUID,
    rule_id: UUID,
    condition: dict[str, object],
) -> dict[str, object]:
    return {
        "id": str(rule_id),
        "policy_id": str(policy_id),
        "name": "Snapshot tool access rule",
        "description": None,
        "condition": json.dumps(condition),
    }


def policy_check_step_snapshot(
    *,
    check_step_id: UUID,
    policy_rule_id: UUID,
    check_type: PolicyCheckStepCheckType,
    target_selector: PolicyCheckStepTargetSelector,
) -> dict[str, object]:
    return {
        "id": str(check_step_id),
        "policy_rule_id": str(policy_rule_id),
        "check_tool_id": None,
        "check_type": check_type.value,
        "target_selector": target_selector.value,
        "required": True,
        "failure_behavior": PolicyCheckStepFailureBehavior.RECORD_ONLY.value,
        "min_confidence": None,
        "status": PolicyCheckStepStatus.ACTIVE.value,
        "evidence_retention": PolicyCheckStepEvidenceRetention.EVIDENCE_BUNDLE.value,
        "metadata": {"purpose": "runtime_metadata_pre_check"},
    }


def fetch_policy_version(
    session_factory: SessionFactory,
    version_id: UUID,
) -> dict[str, object]:
    with session_factory() as session:
        version = session.get(PolicyVersion, version_id)
        assert version is not None
        return {
            "policy_snapshot": deepcopy(version.policy_snapshot),
            "rule_snapshots": deepcopy(version.rule_snapshots),
            "check_step_snapshots": deepcopy(version.check_step_snapshots),
            "status": version.status.value,
        }


def create_policy_check_step(
    session_factory: SessionFactory,
    *,
    policy_rule_id: UUID,
    check_type: PolicyCheckStepCheckType,
    target_selector: PolicyCheckStepTargetSelector,
    status: PolicyCheckStepStatus = PolicyCheckStepStatus.ACTIVE,
    failure_behavior: PolicyCheckStepFailureBehavior = (
        PolicyCheckStepFailureBehavior.RECORD_ONLY
    ),
) -> UUID:
    with session_factory() as session:
        step = PolicyCheckStep(
            policy_rule_id=policy_rule_id,
            check_type=check_type,
            target_selector=target_selector,
            failure_behavior=failure_behavior,
            status=status,
            evidence_retention=PolicyCheckStepEvidenceRetention.EVIDENCE_BUNDLE,
            metadata_={"purpose": "runtime_metadata_pre_check"},
        )
        session.add(step)
        session.commit()
        return step.id


def disable_policy_check_step(
    session_factory: SessionFactory,
    check_step_id: UUID,
) -> None:
    with session_factory() as session:
        check_step = session.get(PolicyCheckStep, check_step_id)
        assert check_step is not None
        check_step.status = PolicyCheckStepStatus.DISABLED
        session.commit()


def create_unsupported_policy_rule(
    session_factory: SessionFactory,
) -> tuple[UUID, UUID]:
    with session_factory() as session:
        policy = Policy(
            name="Unsupported condition policy",
            description=None,
            status=PolicyStatus.ACTIVE,
        )
        session.add(policy)
        session.flush()

        rule = PolicyRule(
            policy_id=policy.id,
            name="Unsupported condition rule",
            description=None,
            condition=json.dumps(
                {
                    "decision": "deny",
                    "reason": "Unsupported condition should trigger failure policy.",
                    "unsupported_field": "not-supported",
                }
            ),
        )
        session.add(rule)
        session.commit()
        return policy.id, rule.id


def runtime_decision_payload(
    agent_id: UUID,
    *,
    run_id: UUID | None = None,
    request_id: str = "runtime-request-001",
    action_summary: str = "Send a support follow-up email.",
    mode: str = "simulation",
    tool_name: str = "send_email",
) -> dict[str, object]:
    return {
        "request_id": request_id,
        "agent_id": str(agent_id),
        "run_id": str(run_id or uuid4()),
        "correlation_id": "support-run-001",
        "tool_name": tool_name,
        "action_summary": action_summary,
        "metadata": {"ticket_category": "support"},
        "mode": mode,
    }


def enable_runtime_enforcement(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGCP_RUNTIME_ENFORCEMENT_ENABLED", "true")
    get_settings.cache_clear()


def enable_runtime_metadata_pre_checks(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGCP_RUNTIME_METADATA_PRE_CHECKS_ENABLED", "true")
    get_settings.cache_clear()


def configure_service_actor_api_key(
    monkeypatch: pytest.MonkeyPatch,
    *,
    scopes: tuple[str, ...] = ("runtime:decision",),
    require_auth: bool = False,
    scope_rule: dict[str, object] | None = None,
    include_scope_rule: bool = True,
) -> None:
    monkeypatch.setenv(
        "AGCP_SERVICE_ACTOR_API_KEYS",
        f"{SERVICE_ACTOR_ID}={hash_service_actor_api_key(SERVICE_API_KEY)}",
    )
    monkeypatch.setenv(
        "AGCP_SERVICE_ACTOR_SCOPES",
        f"{SERVICE_ACTOR_ID}={','.join(scopes)}",
    )
    if include_scope_rule:
        monkeypatch.setenv(
            "AGCP_SERVICE_ACTOR_SCOPE_RULES",
            json.dumps(
                {
                    SERVICE_ACTOR_ID: scope_rule
                    or {
                        "agent_ids": ["*"],
                        "environments": ["*"],
                        "runtime_modes": ["*"],
                        "tool_names": ["*"],
                    }
                }
            ),
        )
    if require_auth:
        monkeypatch.setenv("AGCP_REQUIRE_SERVICE_AUTH", "true")
    get_settings.cache_clear()


def configure_service_actor_registry_api_key(
    monkeypatch: pytest.MonkeyPatch,
    session_factory: SessionFactory,
    *,
    scopes: tuple[str, ...] = ("runtime:decision",),
    require_auth: bool = False,
    scope_rule: dict[str, object] | None = None,
    include_scope_rule: bool = True,
    actor_status: ServiceActorStatus = ServiceActorStatus.ACTIVE,
    key_status: ServiceActorApiKeyStatus = ServiceActorApiKeyStatus.ACTIVE,
) -> None:
    with session_factory() as session:
        actor = ServiceActor(
            actor_id=SERVICE_ACTOR_ID,
            display_name="Runtime registry test service",
            status=actor_status,
        )
        api_key = ServiceActorApiKey(
            service_actor=actor,
            key_id="sak_runtime_registry_test",
            key_hash=hash_service_actor_api_key(SERVICE_API_KEY),
            status=key_status,
        )
        session.add(actor)
        session.add(api_key)
        for scope in scopes:
            session.add(
                ServiceActorScope(
                    service_actor=actor,
                    scope=scope,
                )
            )
        if include_scope_rule:
            rule = scope_rule or {
                "agent_ids": ["*"],
                "environments": ["*"],
                "runtime_modes": ["*"],
                "tool_names": ["*"],
            }
            session.add(
                ServiceActorScopeRule(
                    service_actor=actor,
                    agent_ids=rule.get("agent_ids", []),
                    environments=rule.get("environments", []),
                    runtime_modes=rule.get("runtime_modes", []),
                    tool_names=rule.get("tool_names", []),
                )
            )
        session.commit()

    monkeypatch.setenv("AGCP_SERVICE_ACTOR_REGISTRY_ENABLED", "true")
    if require_auth:
        monkeypatch.setenv("AGCP_REQUIRE_SERVICE_AUTH", "true")
    get_settings.cache_clear()


def fetch_agent_runs(session_factory: SessionFactory) -> list[AgentRunRecord]:
    with session_factory() as session:
        return list(session.scalars(select(AgentRunRecord)).all())


def fetch_trace_events(session_factory: SessionFactory) -> list[TraceEventRecord]:
    with session_factory() as session:
        return list(session.scalars(select(TraceEventRecord)).all())


def fetch_policy_decisions(session_factory: SessionFactory) -> list[PolicyDecision]:
    with session_factory() as session:
        return list(session.scalars(select(PolicyDecision)).all())


def fetch_human_approvals(session_factory: SessionFactory) -> list[HumanApproval]:
    with session_factory() as session:
        return list(session.scalars(select(HumanApproval)).all())


def fetch_check_results(session_factory: SessionFactory) -> list[CheckResult]:
    with session_factory() as session:
        return list(session.scalars(select(CheckResult)).all())


def fetch_human_approval_audit_logs(
    session_factory: SessionFactory,
) -> list[AuditLog]:
    with session_factory() as session:
        statement = (
            select(AuditLog)
            .where(AuditLog.entity_type == "human_approval")
            .order_by(AuditLog.created_at, AuditLog.id)
        )
        return list(session.scalars(statement).all())
