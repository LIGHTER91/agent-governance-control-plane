from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy.orm import Session

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
    TraceEventRecord,
    TraceEventType,
)

DEMO_AGENT_ID = UUID("00000000-0000-4000-8000-000000000101")
DEMO_POLICY_ID = UUID("00000000-0000-4000-8000-000000000201")
DEMO_POLICY_RULE_ID = UUID("00000000-0000-4000-8000-000000000301")
DEMO_AGENT_RUN_RECORD_ID = UUID("00000000-0000-4000-8000-000000000401")
DEMO_RUN_ID = UUID("00000000-0000-4000-8000-000000000402")
DEMO_TRACE_EVENT_ID = UUID("00000000-0000-4000-8000-000000000501")
DEMO_POLICY_DECISION_ID = UUID("00000000-0000-4000-8000-000000000601")
DEMO_HUMAN_APPROVAL_ID = UUID("00000000-0000-4000-8000-000000000701")
DEMO_AGENT_AUDIT_LOG_ID = UUID("00000000-0000-4000-8000-000000000801")
DEMO_HUMAN_APPROVAL_AUDIT_LOG_ID = UUID("00000000-0000-4000-8000-000000000802")
DEMO_BASE_TIME = datetime(2026, 1, 15, 10, 0, tzinfo=UTC)
DEMO_TOOL_NAME = "local_demo_review_tool"
DEMO_CORRELATION_ID = "local-full-stack-demo"
DEMO_ACTOR_ID = "development:local-demo-seed"

METADATA_PRE_CHECK_DEMO_AGENT_ID = UUID("00000000-0000-4000-8000-000000001101")
METADATA_PRE_CHECK_DEMO_CAPABILITY_ID = UUID("00000000-0000-4000-8000-000000001201")
METADATA_PRE_CHECK_DEMO_SOURCE_ID = UUID("00000000-0000-4000-8000-000000001301")
METADATA_PRE_CHECK_DEMO_DATA_USAGE_PROFILE_ID = UUID(
    "00000000-0000-4000-8000-000000001302"
)
METADATA_PRE_CHECK_DEMO_MODEL_ID = UUID("00000000-0000-4000-8000-000000001401")
METADATA_PRE_CHECK_DEMO_CAPABILITY_GRANT_ID = UUID(
    "00000000-0000-4000-8000-000000001501"
)
METADATA_PRE_CHECK_DEMO_SOURCE_GRANT_ID = UUID("00000000-0000-4000-8000-000000001502")
METADATA_PRE_CHECK_DEMO_MODEL_GRANT_ID = UUID("00000000-0000-4000-8000-000000001503")
METADATA_PRE_CHECK_DEMO_POLICY_ID = UUID("00000000-0000-4000-8000-000000001601")
METADATA_PRE_CHECK_DEMO_RULE_ID = UUID("00000000-0000-4000-8000-000000001701")
METADATA_PRE_CHECK_DEMO_SOURCE_STATUS_STEP_ID = UUID(
    "00000000-0000-4000-8000-000000001801"
)
METADATA_PRE_CHECK_DEMO_SOURCE_CLASSIFICATION_STEP_ID = UUID(
    "00000000-0000-4000-8000-000000001802"
)
METADATA_PRE_CHECK_DEMO_DATA_USAGE_STEP_ID = UUID(
    "00000000-0000-4000-8000-000000001803"
)
METADATA_PRE_CHECK_DEMO_CAPABILITY_STEP_ID = UUID(
    "00000000-0000-4000-8000-000000001804"
)
METADATA_PRE_CHECK_DEMO_MODEL_STATUS_STEP_ID = UUID(
    "00000000-0000-4000-8000-000000001805"
)
METADATA_PRE_CHECK_DEMO_MODEL_PROVIDER_STEP_ID = UUID(
    "00000000-0000-4000-8000-000000001806"
)
METADATA_PRE_CHECK_DEMO_ACCESS_GRANT_STEP_ID = UUID(
    "00000000-0000-4000-8000-000000001807"
)
METADATA_PRE_CHECK_DEMO_POLICY_VERSION_ID = UUID("00000000-0000-4000-8000-000000001901")
METADATA_PRE_CHECK_DEMO_RUN_ID = UUID("00000000-0000-4000-8000-000000001a01")
METADATA_PRE_CHECK_DEMO_REQUEST_ID = "metadata-precheck-demo-001"
METADATA_PRE_CHECK_DEMO_TOOL_NAME = "vectorize_source"
METADATA_PRE_CHECK_DEMO_CORRELATION_ID = "metadata-precheck-demo"


@dataclass(frozen=True, slots=True)
class FullStackDemoSeedResult:
    dry_run: bool
    created: tuple[str, ...]
    reused: tuple[str, ...]
    agent_id: UUID
    policy_id: UUID
    policy_rule_id: UUID
    run_id: UUID
    trace_event_id: UUID
    policy_decision_id: UUID
    human_approval_id: UUID
    metadata_pre_check_agent_id: UUID
    metadata_pre_check_policy_id: UUID
    metadata_pre_check_policy_rule_id: UUID
    metadata_pre_check_policy_version_id: UUID
    metadata_pre_check_capability_id: UUID
    metadata_pre_check_source_id: UUID
    metadata_pre_check_model_id: UUID
    metadata_pre_check_run_id: UUID
    metadata_pre_check_request_id: str


def seed_full_stack_demo(
    session: Session,
    *,
    dry_run: bool = True,
) -> FullStackDemoSeedResult:
    created: list[str] = []
    reused: list[str] = []

    def ensure(name: str, model: type[object], object_id: UUID) -> bool:
        if session.get(model, object_id) is not None:
            reused.append(name)
            return False
        created.append(name)
        return True

    if ensure("agent", Agent, DEMO_AGENT_ID) and not dry_run:
        session.add(_demo_agent())
        session.flush()

    if ensure("policy", Policy, DEMO_POLICY_ID) and not dry_run:
        session.add(_demo_policy())
        session.flush()

    if ensure("policy_rule", PolicyRule, DEMO_POLICY_RULE_ID) and not dry_run:
        session.add(_demo_policy_rule())
        session.flush()

    if ensure("agent_run", AgentRunRecord, DEMO_AGENT_RUN_RECORD_ID) and not dry_run:
        session.add(_demo_agent_run())
        session.flush()

    if ensure("trace_event", TraceEventRecord, DEMO_TRACE_EVENT_ID) and not dry_run:
        session.add(_demo_trace_event())
        session.flush()

    if (
        ensure("policy_decision", PolicyDecision, DEMO_POLICY_DECISION_ID)
        and not dry_run
    ):
        session.add(_demo_policy_decision())
        session.flush()

    if ensure("human_approval", HumanApproval, DEMO_HUMAN_APPROVAL_ID) and not dry_run:
        session.add(_demo_human_approval())
        session.flush()

    if ensure("agent_audit_log", AuditLog, DEMO_AGENT_AUDIT_LOG_ID) and not dry_run:
        session.add(_demo_agent_audit_log())
        session.flush()

    if (
        ensure("human_approval_audit_log", AuditLog, DEMO_HUMAN_APPROVAL_AUDIT_LOG_ID)
        and not dry_run
    ):
        session.add(_demo_human_approval_audit_log())
        session.flush()

    if (
        ensure("metadata_pre_check_agent", Agent, METADATA_PRE_CHECK_DEMO_AGENT_ID)
        and not dry_run
    ):
        session.add(_metadata_pre_check_agent())
        session.flush()

    if (
        ensure(
            "metadata_pre_check_capability",
            Capability,
            METADATA_PRE_CHECK_DEMO_CAPABILITY_ID,
        )
        and not dry_run
    ):
        session.add(_metadata_pre_check_capability())
        session.flush()

    if (
        ensure(
            "metadata_pre_check_source",
            DataSource,
            METADATA_PRE_CHECK_DEMO_SOURCE_ID,
        )
        and not dry_run
    ):
        session.add(_metadata_pre_check_source())
        session.flush()

    if (
        ensure(
            "metadata_pre_check_data_usage_profile",
            DataUsageProfile,
            METADATA_PRE_CHECK_DEMO_DATA_USAGE_PROFILE_ID,
        )
        and not dry_run
    ):
        session.add(_metadata_pre_check_data_usage_profile())
        session.flush()

    if (
        ensure(
            "metadata_pre_check_model_asset",
            ModelAsset,
            METADATA_PRE_CHECK_DEMO_MODEL_ID,
        )
        and not dry_run
    ):
        session.add(_metadata_pre_check_model_asset())
        session.flush()

    for name, grant in _metadata_pre_check_access_grants().items():
        if ensure(name, AccessGrant, grant.id) and not dry_run:
            session.add(grant)
            session.flush()

    if (
        ensure(
            "metadata_pre_check_policy",
            Policy,
            METADATA_PRE_CHECK_DEMO_POLICY_ID,
        )
        and not dry_run
    ):
        session.add(_metadata_pre_check_policy())
        session.flush()

    if (
        ensure(
            "metadata_pre_check_policy_rule",
            PolicyRule,
            METADATA_PRE_CHECK_DEMO_RULE_ID,
        )
        and not dry_run
    ):
        session.add(_metadata_pre_check_policy_rule())
        session.flush()

    for name, step in _metadata_pre_check_steps().items():
        if ensure(name, PolicyCheckStep, step.id) and not dry_run:
            session.add(step)
            session.flush()

    if (
        ensure(
            "metadata_pre_check_policy_version",
            PolicyVersion,
            METADATA_PRE_CHECK_DEMO_POLICY_VERSION_ID,
        )
        and not dry_run
    ):
        session.add(_metadata_pre_check_policy_version())
        session.flush()

    if not dry_run:
        session.commit()

    return FullStackDemoSeedResult(
        dry_run=dry_run,
        created=tuple(created),
        reused=tuple(reused),
        agent_id=DEMO_AGENT_ID,
        policy_id=DEMO_POLICY_ID,
        policy_rule_id=DEMO_POLICY_RULE_ID,
        run_id=DEMO_RUN_ID,
        trace_event_id=DEMO_TRACE_EVENT_ID,
        policy_decision_id=DEMO_POLICY_DECISION_ID,
        human_approval_id=DEMO_HUMAN_APPROVAL_ID,
        metadata_pre_check_agent_id=METADATA_PRE_CHECK_DEMO_AGENT_ID,
        metadata_pre_check_policy_id=METADATA_PRE_CHECK_DEMO_POLICY_ID,
        metadata_pre_check_policy_rule_id=METADATA_PRE_CHECK_DEMO_RULE_ID,
        metadata_pre_check_policy_version_id=METADATA_PRE_CHECK_DEMO_POLICY_VERSION_ID,
        metadata_pre_check_capability_id=METADATA_PRE_CHECK_DEMO_CAPABILITY_ID,
        metadata_pre_check_source_id=METADATA_PRE_CHECK_DEMO_SOURCE_ID,
        metadata_pre_check_model_id=METADATA_PRE_CHECK_DEMO_MODEL_ID,
        metadata_pre_check_run_id=METADATA_PRE_CHECK_DEMO_RUN_ID,
        metadata_pre_check_request_id=METADATA_PRE_CHECK_DEMO_REQUEST_ID,
    )


def format_full_stack_demo_seed_result(result: FullStackDemoSeedResult) -> str:
    mode = "DRY RUN" if result.dry_run else "APPLIED"
    lines = [
        f"Local full-stack demo seed: {mode}",
        f"created={_format_items(result.created)}",
        f"reused={_format_items(result.reused)}",
        f"agent_id={result.agent_id}",
        f"policy_id={result.policy_id}",
        f"policy_rule_id={result.policy_rule_id}",
        f"run_id={result.run_id}",
        f"trace_event_id={result.trace_event_id}",
        f"policy_decision_id={result.policy_decision_id}",
        f"human_approval_id={result.human_approval_id}",
        "",
        "Metadata-only runtime pre-check demo:",
        f"metadata_agent_id={result.metadata_pre_check_agent_id}",
        f"metadata_policy_id={result.metadata_pre_check_policy_id}",
        f"metadata_policy_rule_id={result.metadata_pre_check_policy_rule_id}",
        f"metadata_policy_version_id={result.metadata_pre_check_policy_version_id}",
        f"metadata_capability_id={result.metadata_pre_check_capability_id}",
        f"metadata_source_id={result.metadata_pre_check_source_id}",
        f"metadata_model_id={result.metadata_pre_check_model_id}",
        f"metadata_run_id={result.metadata_pre_check_run_id}",
        f"metadata_request_id={result.metadata_pre_check_request_id}",
    ]
    if result.dry_run:
        lines.append("Run again with --apply to write local demo records.")
    else:
        lines.append("Open the frontend at /agents to review the demo chain.")
        lines.append(
            "Set AGCP_RUNTIME_METADATA_PRE_CHECKS_ENABLED=true and call "
            "POST /runtime/tool-calls/decision with the metadata_* IDs to "
            "create real metadata-only CheckResults."
        )
    return "\n".join(lines)


def _demo_agent() -> Agent:
    return Agent(
        id=DEMO_AGENT_ID,
        name="Local Demo Review Agent",
        description=(
            "Safe local demo agent for exercising the full-stack governance UI."
        ),
        owner_type=OwnerType.TEAM,
        owner_id="team:local-governance",
        owner_name="Local Governance Team",
        owner_contact_email=None,
        environment=Environment.DEVELOPMENT,
        status=AgentStatus.ACTIVE,
        risk_level=RiskLevel.MEDIUM,
        framework="LangGraph-style demo",
        created_at=DEMO_BASE_TIME,
        updated_at=DEMO_BASE_TIME,
    )


def _demo_policy() -> Policy:
    return Policy(
        id=DEMO_POLICY_ID,
        name="Local demo runtime review policy",
        description=("Requires human review for the safe local demo tool action."),
        status=PolicyStatus.ACTIVE,
        created_at=DEMO_BASE_TIME + timedelta(minutes=1),
        updated_at=DEMO_BASE_TIME + timedelta(minutes=1),
    )


def _demo_policy_rule() -> PolicyRule:
    return PolicyRule(
        id=DEMO_POLICY_RULE_ID,
        policy_id=DEMO_POLICY_ID,
        name="Require review for local demo tool",
        description="Matches only the local demo tool name.",
        condition=json.dumps(
            {
                "tool_name": DEMO_TOOL_NAME,
                "decision": PolicyDecisionValue.REQUIRE_HUMAN_REVIEW.value,
                "reason": "Local demo tool use requires human review.",
            },
            sort_keys=True,
        ),
        created_at=DEMO_BASE_TIME + timedelta(minutes=2),
        updated_at=DEMO_BASE_TIME + timedelta(minutes=2),
    )


def _demo_agent_run() -> AgentRunRecord:
    return AgentRunRecord(
        id=DEMO_AGENT_RUN_RECORD_ID,
        agent_id=DEMO_AGENT_ID,
        run_id=DEMO_RUN_ID,
        correlation_id=DEMO_CORRELATION_ID,
        environment=Environment.DEVELOPMENT,
        status="observed",
        started_at=DEMO_BASE_TIME + timedelta(minutes=3),
        ended_at=None,
        summary="Local demo runtime event observed.",
        metadata_={"demo": "full_stack", "runtime_mode": "simulation"},
        created_at=DEMO_BASE_TIME + timedelta(minutes=3),
    )


def _demo_trace_event() -> TraceEventRecord:
    return TraceEventRecord(
        id=DEMO_TRACE_EVENT_ID,
        agent_id=DEMO_AGENT_ID,
        run_id=DEMO_RUN_ID,
        external_event_id="local-demo-tool-call-requested",
        correlation_id=DEMO_CORRELATION_ID,
        event_type=TraceEventType.TOOL_CALL_REQUESTED,
        timestamp=DEMO_BASE_TIME + timedelta(minutes=4),
        summary="Local demo agent requested a governed tool action.",
        metadata_={
            "tool_name": DEMO_TOOL_NAME,
            "action_type": "demo_review_action",
            "purpose": "local_full_stack_demo",
        },
        created_at=DEMO_BASE_TIME + timedelta(minutes=4),
    )


def _demo_policy_decision() -> PolicyDecision:
    return PolicyDecision(
        id=DEMO_POLICY_DECISION_ID,
        agent_id=DEMO_AGENT_ID,
        policy_id=DEMO_POLICY_ID,
        rule_id=DEMO_POLICY_RULE_ID,
        trace_event_id=DEMO_TRACE_EVENT_ID,
        decision=PolicyDecisionValue.REQUIRE_HUMAN_REVIEW,
        reason="Local demo tool use requires human review.",
        context_hash=None,
        created_at=DEMO_BASE_TIME + timedelta(minutes=5),
    )


def _demo_human_approval() -> HumanApproval:
    return HumanApproval(
        id=DEMO_HUMAN_APPROVAL_ID,
        agent_id=DEMO_AGENT_ID,
        policy_decision_id=DEMO_POLICY_DECISION_ID,
        status=HumanApprovalStatus.PENDING,
        requested_by_actor_type=ActorType.DEVELOPMENT,
        requested_by_actor_id=DEMO_ACTOR_ID,
        reason="Review the local demo governed tool request.",
        decision_note=None,
        reviewed_by_actor_type=None,
        reviewed_by_actor_id=None,
        reviewed_at=None,
        expires_at=None,
        created_at=DEMO_BASE_TIME + timedelta(minutes=6),
    )


def _demo_agent_audit_log() -> AuditLog:
    return AuditLog(
        id=DEMO_AGENT_AUDIT_LOG_ID,
        event_type="agent_seeded_for_local_demo",
        actor_type=ActorType.DEVELOPMENT,
        actor_id=DEMO_ACTOR_ID,
        entity_type="agent",
        entity_id=str(DEMO_AGENT_ID),
        summary="Local demo agent seeded for full-stack review.",
        metadata_={"agent_id": str(DEMO_AGENT_ID), "demo": "full_stack"},
        created_at=DEMO_BASE_TIME + timedelta(minutes=7),
    )


def _demo_human_approval_audit_log() -> AuditLog:
    return AuditLog(
        id=DEMO_HUMAN_APPROVAL_AUDIT_LOG_ID,
        event_type="human_approval_requested",
        actor_type=ActorType.DEVELOPMENT,
        actor_id=DEMO_ACTOR_ID,
        entity_type="human_approval",
        entity_id=str(DEMO_HUMAN_APPROVAL_ID),
        summary="Human approval requested for the local demo tool action.",
        metadata_={
            "agent_id": str(DEMO_AGENT_ID),
            "policy_decision_id": str(DEMO_POLICY_DECISION_ID),
            "status": HumanApprovalStatus.PENDING.value,
        },
        created_at=DEMO_BASE_TIME + timedelta(minutes=8),
    )


def _metadata_pre_check_agent() -> Agent:
    return Agent(
        id=METADATA_PRE_CHECK_DEMO_AGENT_ID,
        name="Metadata Pre-Check Demo Agent",
        description=("Local demo agent for metadata-only Runtime Gateway pre-checks."),
        owner_type=OwnerType.TEAM,
        owner_id="team:local-governance",
        owner_name="Local Governance Team",
        owner_contact_email=None,
        environment=Environment.PRODUCTION,
        status=AgentStatus.ACTIVE,
        risk_level=RiskLevel.HIGH,
        framework="LangGraph-style demo",
        created_at=DEMO_BASE_TIME + timedelta(minutes=20),
        updated_at=DEMO_BASE_TIME + timedelta(minutes=20),
    )


def _metadata_pre_check_capability() -> Capability:
    return Capability(
        id=METADATA_PRE_CHECK_DEMO_CAPABILITY_ID,
        name="Vectorize source for local metadata demo",
        description="Safe local metadata-only pre-check demo capability.",
        capability_type=CapabilityType.TOOL,
        external_ref="tool:vectorize_source",
        status=CapabilityStatus.ACTIVE,
        risk_level=RiskLevel.HIGH,
        metadata_={"demo": "metadata_pre_check", "domain": "rag"},
        created_at=DEMO_BASE_TIME + timedelta(minutes=21),
        updated_at=DEMO_BASE_TIME + timedelta(minutes=21),
    )


def _metadata_pre_check_source() -> DataSource:
    return DataSource(
        id=METADATA_PRE_CHECK_DEMO_SOURCE_ID,
        name="Confidential metadata-only demo source",
        description=(
            "Local demo Source record. It stores metadata only, not source content."
        ),
        source_type=DataSourceType.KNOWLEDGE_BASE,
        external_ref="source:metadata-precheck-confidential",
        owner_type=OwnerType.TEAM,
        owner_id="team:data-governance",
        owner_name="Data Governance",
        owner_contact_email=None,
        status=DataSourceStatus.ACTIVE,
        risk_level=RiskLevel.HIGH,
        metadata_={"demo": "metadata_pre_check", "catalog_ref": "catalog:demo-source"},
        created_at=DEMO_BASE_TIME + timedelta(minutes=22),
        updated_at=DEMO_BASE_TIME + timedelta(minutes=22),
    )


def _metadata_pre_check_data_usage_profile() -> DataUsageProfile:
    return DataUsageProfile(
        id=METADATA_PRE_CHECK_DEMO_DATA_USAGE_PROFILE_ID,
        source_id=METADATA_PRE_CHECK_DEMO_SOURCE_ID,
        data_classification=DataUsageClassification.CONFIDENTIAL,
        contains_personal_data=False,
        contains_sensitive_data=True,
        data_categories=["governance_metadata"],
        legal_basis=None,
        allowed_purposes=["semantic_search_indexing"],
        prohibited_purposes=["model_training"],
        allowed_processing=["rag", "vectorization"],
        prohibited_processing=["training"],
        residency="local-demo",
        retention_policy="local-demo-only",
        data_owner="Local Data Governance",
        review_status=DataUsageReviewStatus.APPROVED,
        reviewed_by_actor_type=ActorType.DEVELOPMENT,
        reviewed_by_actor_id=DEMO_ACTOR_ID,
        reviewed_at=DEMO_BASE_TIME + timedelta(minutes=23),
        review_expires_at=None,
        dpia_required=True,
        dpia_reference="dpia:local-metadata-demo",
        metadata_={"demo": "metadata_pre_check"},
        created_at=DEMO_BASE_TIME + timedelta(minutes=23),
        updated_at=DEMO_BASE_TIME + timedelta(minutes=23),
    )


def _metadata_pre_check_model_asset() -> ModelAsset:
    return ModelAsset(
        id=METADATA_PRE_CHECK_DEMO_MODEL_ID,
        name="External embedding model for local metadata demo",
        description="Safe local ModelAsset metadata for Runtime Gateway checks.",
        model_type=ModelAssetType.EMBEDDING,
        provider=ModelProvider.OPENAI,
        model_ref="embedding:metadata-demo",
        version="local-demo",
        owner_type=OwnerType.TEAM,
        owner_id="team:model-governance",
        owner_name="Model Governance",
        owner_contact_email=None,
        status=ModelAssetStatus.ACTIVE,
        risk_level=RiskLevel.HIGH,
        metadata_={"demo": "metadata_pre_check", "provider_boundary": "external"},
        created_at=DEMO_BASE_TIME + timedelta(minutes=24),
        updated_at=DEMO_BASE_TIME + timedelta(minutes=24),
    )


def _metadata_pre_check_access_grants() -> dict[str, AccessGrant]:
    return {
        "metadata_pre_check_capability_grant": _metadata_pre_check_access_grant(
            grant_id=METADATA_PRE_CHECK_DEMO_CAPABILITY_GRANT_ID,
            name="Metadata demo capability grant",
            grant_type=AccessGrantType.CAPABILITY,
            target_type=AccessGrantTargetType.CAPABILITY,
            target_id=METADATA_PRE_CHECK_DEMO_CAPABILITY_ID,
            created_offset=25,
        ),
        "metadata_pre_check_source_grant": _metadata_pre_check_access_grant(
            grant_id=METADATA_PRE_CHECK_DEMO_SOURCE_GRANT_ID,
            name="Metadata demo source grant",
            grant_type=AccessGrantType.SOURCE,
            target_type=AccessGrantTargetType.SOURCE,
            target_id=METADATA_PRE_CHECK_DEMO_SOURCE_ID,
            created_offset=26,
        ),
        "metadata_pre_check_model_grant": _metadata_pre_check_access_grant(
            grant_id=METADATA_PRE_CHECK_DEMO_MODEL_GRANT_ID,
            name="Metadata demo model grant",
            grant_type=AccessGrantType.MODEL,
            target_type=AccessGrantTargetType.MODEL_ASSET,
            target_id=METADATA_PRE_CHECK_DEMO_MODEL_ID,
            created_offset=27,
        ),
    }


def _metadata_pre_check_access_grant(
    *,
    grant_id: UUID,
    name: str,
    grant_type: AccessGrantType,
    target_type: AccessGrantTargetType,
    target_id: UUID,
    created_offset: int,
) -> AccessGrant:
    created_at = DEMO_BASE_TIME + timedelta(minutes=created_offset)
    return AccessGrant(
        id=grant_id,
        name=name,
        description="Local demo AccessGrant for metadata-only Runtime Gateway checks.",
        grant_type=grant_type,
        subject_type=AccessGrantSubjectType.AGENT,
        subject_id=METADATA_PRE_CHECK_DEMO_AGENT_ID,
        target_type=target_type,
        target_id=target_id,
        external_ref=None,
        status=AccessGrantStatus.ACTIVE,
        granted_by_actor_type=ActorType.DEVELOPMENT,
        granted_by_actor_id=DEMO_ACTOR_ID,
        reason="Local metadata pre-check demo grant.",
        expires_at=None,
        risk_level=RiskLevel.HIGH,
        metadata_={"demo": "metadata_pre_check"},
        created_at=created_at,
        updated_at=created_at,
    )


def _metadata_pre_check_policy() -> Policy:
    return Policy(
        id=METADATA_PRE_CHECK_DEMO_POLICY_ID,
        name="Metadata pre-check external vectorization review policy",
        description=(
            "Requires review for confidential Source vectorization with an "
            "external model when metadata-only checks confirm provider metadata."
        ),
        status=PolicyStatus.ACTIVE,
        created_at=DEMO_BASE_TIME + timedelta(minutes=28),
        updated_at=DEMO_BASE_TIME + timedelta(minutes=28),
    )


def _metadata_pre_check_policy_rule() -> PolicyRule:
    return PolicyRule(
        id=METADATA_PRE_CHECK_DEMO_RULE_ID,
        policy_id=METADATA_PRE_CHECK_DEMO_POLICY_ID,
        name="Require review for confidential external vectorization",
        description=("Matches a real metadata-only ModelAsset provider CheckResult."),
        condition=json.dumps(_metadata_pre_check_rule_condition(), sort_keys=True),
        created_at=DEMO_BASE_TIME + timedelta(minutes=29),
        updated_at=DEMO_BASE_TIME + timedelta(minutes=29),
    )


def _metadata_pre_check_rule_condition() -> dict[str, object]:
    return {
        "tool_name": METADATA_PRE_CHECK_DEMO_TOOL_NAME,
        "action_type": "vectorize",
        "environment": Environment.PRODUCTION.value,
        "risk_level": RiskLevel.HIGH.value,
        "purpose": "semantic_search_indexing",
        "source_data_classification": DataUsageClassification.CONFIDENTIAL.value,
        "data_usage_review_status": DataUsageReviewStatus.APPROVED.value,
        "model_provider_type": "external",
        "access_grant_status": AccessGrantStatus.ACTIVE.value,
        "check_type": PolicyCheckStepCheckType.MODEL_PROVIDER_TYPE.value,
        "check_outcome": "pass",
        "check_target_type": "model_asset",
        "decision": PolicyDecisionValue.REQUIRE_HUMAN_REVIEW.value,
        "reason": (
            "Confidential source vectorization with an external model requires "
            "human review after metadata-only pre-check evidence."
        ),
    }


def _metadata_pre_check_steps() -> dict[str, PolicyCheckStep]:
    return {
        "metadata_pre_check_source_status_step": _metadata_pre_check_step(
            step_id=METADATA_PRE_CHECK_DEMO_SOURCE_STATUS_STEP_ID,
            check_type=PolicyCheckStepCheckType.SOURCE_STATUS,
            target_selector=PolicyCheckStepTargetSelector.SOURCE_IDS,
            created_offset=30,
        ),
        "metadata_pre_check_source_classification_step": _metadata_pre_check_step(
            step_id=METADATA_PRE_CHECK_DEMO_SOURCE_CLASSIFICATION_STEP_ID,
            check_type=PolicyCheckStepCheckType.SOURCE_CLASSIFICATION,
            target_selector=PolicyCheckStepTargetSelector.SOURCE_IDS,
            created_offset=31,
        ),
        "metadata_pre_check_data_usage_step": _metadata_pre_check_step(
            step_id=METADATA_PRE_CHECK_DEMO_DATA_USAGE_STEP_ID,
            check_type=PolicyCheckStepCheckType.DATA_USAGE_PROFILE_STATUS,
            target_selector=PolicyCheckStepTargetSelector.SOURCE_IDS,
            created_offset=32,
        ),
        "metadata_pre_check_capability_step": _metadata_pre_check_step(
            step_id=METADATA_PRE_CHECK_DEMO_CAPABILITY_STEP_ID,
            check_type=PolicyCheckStepCheckType.CAPABILITY_STATUS,
            target_selector=PolicyCheckStepTargetSelector.CAPABILITY_ID,
            created_offset=33,
        ),
        "metadata_pre_check_model_status_step": _metadata_pre_check_step(
            step_id=METADATA_PRE_CHECK_DEMO_MODEL_STATUS_STEP_ID,
            check_type=PolicyCheckStepCheckType.MODEL_ASSET_STATUS,
            target_selector=PolicyCheckStepTargetSelector.MODEL_ID,
            created_offset=34,
        ),
        "metadata_pre_check_model_provider_step": _metadata_pre_check_step(
            step_id=METADATA_PRE_CHECK_DEMO_MODEL_PROVIDER_STEP_ID,
            check_type=PolicyCheckStepCheckType.MODEL_PROVIDER_TYPE,
            target_selector=PolicyCheckStepTargetSelector.MODEL_ID,
            created_offset=35,
        ),
        "metadata_pre_check_access_grant_step": _metadata_pre_check_step(
            step_id=METADATA_PRE_CHECK_DEMO_ACCESS_GRANT_STEP_ID,
            check_type=PolicyCheckStepCheckType.ACCESS_GRANT_STATUS,
            target_selector=PolicyCheckStepTargetSelector.ACCESS_GRANTS,
            created_offset=36,
        ),
    }


def _metadata_pre_check_step(
    *,
    step_id: UUID,
    check_type: PolicyCheckStepCheckType,
    target_selector: PolicyCheckStepTargetSelector,
    created_offset: int,
) -> PolicyCheckStep:
    created_at = DEMO_BASE_TIME + timedelta(minutes=created_offset)
    return PolicyCheckStep(
        id=step_id,
        policy_rule_id=METADATA_PRE_CHECK_DEMO_RULE_ID,
        check_tool_id=None,
        check_type=check_type,
        target_selector=target_selector,
        required=True,
        failure_behavior=PolicyCheckStepFailureBehavior.RECORD_ONLY,
        min_confidence=None,
        status=PolicyCheckStepStatus.ACTIVE,
        evidence_retention=PolicyCheckStepEvidenceRetention.EVIDENCE_BUNDLE,
        metadata_={
            "purpose": "runtime_metadata_pre_check",
            "demo": "metadata_pre_check",
        },
        created_at=created_at,
        updated_at=created_at,
    )


def _metadata_pre_check_policy_version() -> PolicyVersion:
    now = DEMO_BASE_TIME + timedelta(minutes=37)
    return PolicyVersion(
        id=METADATA_PRE_CHECK_DEMO_POLICY_VERSION_ID,
        policy_id=METADATA_PRE_CHECK_DEMO_POLICY_ID,
        source_version_id=None,
        version_number=1,
        status=PolicyVersionStatus.ACTIVE,
        change_summary=("Local metadata-only Runtime Gateway pre-check demo snapshot."),
        policy_snapshot={
            "id": str(METADATA_PRE_CHECK_DEMO_POLICY_ID),
            "name": "Metadata pre-check external vectorization review policy",
            "description": (
                "Requires review for confidential Source vectorization with an "
                "external model when metadata-only checks confirm provider metadata."
            ),
            "status": PolicyStatus.ACTIVE.value,
        },
        rule_snapshots=[_metadata_pre_check_rule_snapshot()],
        check_step_snapshots=_metadata_pre_check_step_snapshots(),
        created_by_actor_type=ActorType.DEVELOPMENT,
        created_by_actor_id=DEMO_ACTOR_ID,
        review_requested_by_actor_type=ActorType.DEVELOPMENT,
        review_requested_by_actor_id=DEMO_ACTOR_ID,
        reviewed_by_actor_type=ActorType.DEVELOPMENT,
        reviewed_by_actor_id=DEMO_ACTOR_ID,
        review_note="Local demo version activated for metadata-only pre-check testing.",
        created_at=now,
        updated_at=now,
        submitted_at=now,
        approved_at=now,
        rejected_at=None,
        activated_at=now,
        superseded_at=None,
        archived_at=None,
    )


def _metadata_pre_check_rule_snapshot() -> dict[str, object]:
    return {
        "id": str(METADATA_PRE_CHECK_DEMO_RULE_ID),
        "policy_id": str(METADATA_PRE_CHECK_DEMO_POLICY_ID),
        "name": "Require review for confidential external vectorization",
        "description": (
            "Matches a real metadata-only ModelAsset provider CheckResult."
        ),
        "condition": json.dumps(_metadata_pre_check_rule_condition(), sort_keys=True),
    }


def _metadata_pre_check_step_snapshots() -> list[dict[str, object]]:
    return [
        _metadata_pre_check_step_snapshot(step)
        for step in _metadata_pre_check_steps().values()
    ]


def _metadata_pre_check_step_snapshot(step: PolicyCheckStep) -> dict[str, object]:
    return {
        "id": str(step.id),
        "policy_rule_id": str(step.policy_rule_id),
        "check_tool_id": None,
        "check_type": step.check_type.value,
        "target_selector": step.target_selector.value,
        "required": step.required,
        "failure_behavior": step.failure_behavior.value,
        "min_confidence": step.min_confidence,
        "status": step.status.value,
        "evidence_retention": step.evidence_retention.value,
        "metadata": step.metadata_,
    }


def metadata_pre_check_demo_runtime_payload() -> dict[str, object]:
    """Return the safe Runtime Gateway payload for the local metadata demo."""

    return {
        "request_id": METADATA_PRE_CHECK_DEMO_REQUEST_ID,
        "agent_id": str(METADATA_PRE_CHECK_DEMO_AGENT_ID),
        "run_id": str(METADATA_PRE_CHECK_DEMO_RUN_ID),
        "correlation_id": METADATA_PRE_CHECK_DEMO_CORRELATION_ID,
        "tool_name": METADATA_PRE_CHECK_DEMO_TOOL_NAME,
        "action_summary": (
            "Vectorize a confidential demo source with an external embedding model."
        ),
        "metadata": {"demo": "metadata_pre_check"},
        "mode": "simulation",
        "action_type": "vectorize",
        "capability_id": str(METADATA_PRE_CHECK_DEMO_CAPABILITY_ID),
        "source_ids": [str(METADATA_PRE_CHECK_DEMO_SOURCE_ID)],
        "model_id": str(METADATA_PRE_CHECK_DEMO_MODEL_ID),
        "purpose": "semantic_search_indexing",
        "data_classification": DataUsageClassification.CONFIDENTIAL.value,
        "contains_personal_data": False,
        "contains_sensitive_data": True,
    }


def _format_items(items: tuple[str, ...]) -> str:
    if not items:
        return "none"
    return ",".join(items)
