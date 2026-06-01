from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from agent_governance_api.metadata_safety import (
    UNSAFE_METADATA_KEY_PARTS,
    filter_safe_metadata,
    redact_sensitive_text,
)
from agent_governance_api.models import (
    AccessGrant,
    AccessGrantSubjectType,
    AccessGrantTargetType,
    Agent,
    AgentRunRecord,
    AuditLog,
    Capability,
    CheckResult,
    CheckTool,
    DataSource,
    DataUsageProfile,
    HumanApproval,
    ModelAsset,
    Policy,
    PolicyDecision,
    PolicyRule,
    PolicyVersion,
    TraceEventRecord,
)
from agent_governance_api.schemas import (
    AgentRead,
    EvidenceAccessGrantRead,
    EvidenceAgentRunRead,
    EvidenceAuditLogRead,
    EvidenceBundleRead,
    EvidenceCapabilityReferenceRead,
    EvidenceCheckResultRead,
    EvidenceDataUsageProfileRead,
    EvidenceHumanApprovalRead,
    EvidenceModelAssetReferenceRead,
    EvidencePolicyDecisionRead,
    EvidencePolicyReferenceRead,
    EvidencePolicyRuleReferenceRead,
    EvidencePolicyVersionReferenceRead,
    EvidenceSourceReferenceRead,
    EvidenceTraceEventRead,
)


def build_agent_evidence_bundle(
    session: Session,
    *,
    agent: Agent,
) -> EvidenceBundleRead:
    agent_runs = _load_agent_runs(session, agent.id)
    trace_events = _load_trace_events(session, agent.id)
    policy_decisions = _load_policy_decisions(session, agent.id)
    human_approvals = _load_human_approvals(session, agent.id)
    access_grants = _load_access_grants(session, agent.id)
    audit_logs = _load_agent_audit_logs(
        session,
        agent.id,
        human_approvals=human_approvals,
    )
    policy_references = _load_policy_references(session, policy_decisions)
    rule_references = _load_rule_references(session, policy_decisions)
    policy_version_references = _load_policy_version_references(
        session,
        policy_decisions,
    )
    capability_references = _load_capability_references(session, access_grants)
    source_references = _load_source_references(session, access_grants)
    data_usage_profiles = _load_data_usage_profiles(session, access_grants)
    model_asset_references = _load_model_asset_references(session, access_grants)
    check_results = _load_check_results(
        session,
        agent_id=agent.id,
        policy_decisions=policy_decisions,
    )
    policy_versions_by_policy_decision_id = _policy_versions_by_policy_decision_id(
        policy_decisions,
        policy_version_references,
    )

    return EvidenceBundleRead(
        agent=AgentRead.model_validate(agent),
        audit_logs=[_audit_log_response(audit_log) for audit_log in audit_logs],
        agent_runs=[_agent_run_response(agent_run) for agent_run in agent_runs],
        trace_events=[
            _trace_event_response(trace_event) for trace_event in trace_events
        ],
        policy_decisions=[
            _policy_decision_response(
                policy_decision,
                policy_references=policy_references,
                rule_references=rule_references,
                policy_version_references=policy_version_references,
            )
            for policy_decision in policy_decisions
        ],
        human_approvals=[
            _human_approval_response(human_approval)
            for human_approval in human_approvals
        ],
        access_grants=[
            _access_grant_response(access_grant) for access_grant in access_grants
        ],
        capability_references=[
            _capability_reference_response(capability)
            for capability in capability_references
        ],
        source_references=[
            _source_reference_response(source) for source in source_references
        ],
        data_usage_profiles=[
            _data_usage_profile_response(profile) for profile in data_usage_profiles
        ],
        model_asset_references=[
            _model_asset_reference_response(model_asset)
            for model_asset in model_asset_references
        ],
        check_results=[
            _check_result_response(
                check_result,
                check_tool=check_tool,
                policy_versions_by_policy_decision_id=(
                    policy_versions_by_policy_decision_id
                ),
            )
            for check_result, check_tool in check_results
        ],
    )


def _load_agent_audit_logs(
    session: Session,
    agent_id: UUID,
    *,
    human_approvals: list[HumanApproval],
) -> list[AuditLog]:
    related_conditions = [
        and_(
            AuditLog.entity_type == "agent",
            AuditLog.entity_id == str(agent_id),
        )
    ]
    human_approval_entity_ids = [
        str(human_approval.id) for human_approval in human_approvals
    ]
    if human_approval_entity_ids:
        related_conditions.append(
            and_(
                AuditLog.entity_type == "human_approval",
                AuditLog.entity_id.in_(human_approval_entity_ids),
            )
        )

    statement = (
        select(AuditLog)
        .where(or_(*related_conditions))
        .order_by(AuditLog.created_at, AuditLog.id)
    )
    return list(session.scalars(statement).all())


def _load_agent_runs(session: Session, agent_id: UUID) -> list[AgentRunRecord]:
    statement = (
        select(AgentRunRecord)
        .where(AgentRunRecord.agent_id == agent_id)
        .order_by(AgentRunRecord.started_at, AgentRunRecord.id)
    )
    return list(session.scalars(statement).all())


def _load_trace_events(session: Session, agent_id: UUID) -> list[TraceEventRecord]:
    statement = (
        select(TraceEventRecord)
        .where(TraceEventRecord.agent_id == agent_id)
        .order_by(TraceEventRecord.timestamp, TraceEventRecord.id)
    )
    return list(session.scalars(statement).all())


def _load_policy_decisions(session: Session, agent_id: UUID) -> list[PolicyDecision]:
    statement = (
        select(PolicyDecision)
        .where(PolicyDecision.agent_id == agent_id)
        .order_by(PolicyDecision.created_at, PolicyDecision.id)
    )
    return list(session.scalars(statement).all())


def _load_human_approvals(session: Session, agent_id: UUID) -> list[HumanApproval]:
    statement = (
        select(HumanApproval)
        .where(HumanApproval.agent_id == agent_id)
        .order_by(HumanApproval.created_at, HumanApproval.id)
    )
    return list(session.scalars(statement).all())


def _load_access_grants(session: Session, agent_id: UUID) -> list[AccessGrant]:
    statement = (
        select(AccessGrant)
        .where(
            AccessGrant.subject_type == AccessGrantSubjectType.AGENT,
            AccessGrant.subject_id == agent_id,
        )
        .order_by(AccessGrant.created_at, AccessGrant.id)
    )
    return list(session.scalars(statement).all())


def _load_capability_references(
    session: Session,
    access_grants: list[AccessGrant],
) -> list[Capability]:
    capability_ids = _target_ids(access_grants, AccessGrantTargetType.CAPABILITY)
    if not capability_ids:
        return []

    statement = (
        select(Capability)
        .where(Capability.id.in_(capability_ids))
        .order_by(Capability.created_at, Capability.id)
    )
    return list(session.scalars(statement).all())


def _load_source_references(
    session: Session,
    access_grants: list[AccessGrant],
) -> list[DataSource]:
    source_ids = _target_ids(access_grants, AccessGrantTargetType.SOURCE)
    if not source_ids:
        return []

    statement = (
        select(DataSource)
        .where(DataSource.id.in_(source_ids))
        .order_by(DataSource.created_at, DataSource.id)
    )
    return list(session.scalars(statement).all())


def _load_model_asset_references(
    session: Session,
    access_grants: list[AccessGrant],
) -> list[ModelAsset]:
    model_asset_ids = _target_ids(access_grants, AccessGrantTargetType.MODEL_ASSET)
    if not model_asset_ids:
        return []

    statement = (
        select(ModelAsset)
        .where(ModelAsset.id.in_(model_asset_ids))
        .order_by(ModelAsset.created_at, ModelAsset.id)
    )
    return list(session.scalars(statement).all())


def _load_data_usage_profiles(
    session: Session,
    access_grants: list[AccessGrant],
) -> list[DataUsageProfile]:
    source_ids = _target_ids(access_grants, AccessGrantTargetType.SOURCE)
    if not source_ids:
        return []

    statement = (
        select(DataUsageProfile)
        .where(DataUsageProfile.source_id.in_(source_ids))
        .order_by(DataUsageProfile.created_at, DataUsageProfile.id)
    )
    return list(session.scalars(statement).all())


def _load_check_results(
    session: Session,
    *,
    agent_id: UUID,
    policy_decisions: list[PolicyDecision],
) -> list[tuple[CheckResult, CheckTool | None]]:
    policy_decision_ids = {policy_decision.id for policy_decision in policy_decisions}
    related_conditions = [
        and_(
            CheckResult.policy_decision_id.is_(None),
            CheckResult.agent_id == agent_id,
        )
    ]
    if policy_decision_ids:
        related_conditions.append(
            CheckResult.policy_decision_id.in_(policy_decision_ids)
        )

    statement = (
        select(CheckResult, CheckTool)
        .outerjoin(CheckTool, CheckResult.check_tool_id == CheckTool.id)
        .where(or_(*related_conditions))
        .order_by(CheckResult.created_at, CheckResult.id)
    )
    return [
        (check_result, check_tool)
        for check_result, check_tool in session.execute(statement).all()
    ]


def _target_ids(
    access_grants: list[AccessGrant],
    target_type: AccessGrantTargetType,
) -> set[UUID]:
    return {
        access_grant.target_id
        for access_grant in access_grants
        if access_grant.target_type is target_type
        and access_grant.target_id is not None
    }


def _load_policy_references(
    session: Session,
    policy_decisions: list[PolicyDecision],
) -> dict[UUID, EvidencePolicyReferenceRead]:
    policy_ids = {
        policy_decision.policy_id
        for policy_decision in policy_decisions
        if policy_decision.policy_id is not None
    }
    if not policy_ids:
        return {}

    statement = select(Policy).where(Policy.id.in_(policy_ids))
    return {
        policy.id: EvidencePolicyReferenceRead(
            id=policy.id,
            name=policy.name,
            status=policy.status,
        )
        for policy in session.scalars(statement).all()
    }


def _load_rule_references(
    session: Session,
    policy_decisions: list[PolicyDecision],
) -> dict[UUID, EvidencePolicyRuleReferenceRead]:
    rule_ids = {
        policy_decision.rule_id
        for policy_decision in policy_decisions
        if policy_decision.rule_id is not None
    }
    if not rule_ids:
        return {}

    statement = select(PolicyRule).where(PolicyRule.id.in_(rule_ids))
    return {
        rule.id: EvidencePolicyRuleReferenceRead(
            id=rule.id,
            policy_id=rule.policy_id,
            name=rule.name,
        )
        for rule in session.scalars(statement).all()
    }


def _load_policy_version_references(
    session: Session,
    policy_decisions: list[PolicyDecision],
) -> dict[UUID, EvidencePolicyVersionReferenceRead]:
    policy_version_ids = {
        policy_decision.policy_version_id
        for policy_decision in policy_decisions
        if policy_decision.policy_version_id is not None
    }
    if not policy_version_ids:
        return {}

    statement = select(PolicyVersion).where(PolicyVersion.id.in_(policy_version_ids))
    return {
        policy_version.id: _policy_version_reference_response(policy_version)
        for policy_version in session.scalars(statement).all()
    }


def _policy_versions_by_policy_decision_id(
    policy_decisions: list[PolicyDecision],
    policy_version_references: dict[UUID, EvidencePolicyVersionReferenceRead],
) -> dict[UUID, EvidencePolicyVersionReferenceRead]:
    references: dict[UUID, EvidencePolicyVersionReferenceRead] = {}
    for policy_decision in policy_decisions:
        if policy_decision.policy_version_id is None:
            continue
        policy_version = policy_version_references.get(
            policy_decision.policy_version_id
        )
        if policy_version is not None:
            references[policy_decision.id] = policy_version
    return references


def _policy_version_reference_response(
    policy_version: PolicyVersion,
) -> EvidencePolicyVersionReferenceRead:
    return EvidencePolicyVersionReferenceRead(
        policy_version_id=policy_version.id,
        policy_id=policy_version.policy_id,
        version_number=policy_version.version_number,
        status=policy_version.status,
        activated_at=policy_version.activated_at,
        change_summary=_safe_change_summary(policy_version.change_summary),
    )


def _safe_change_summary(change_summary: str) -> str | None:
    lowered_summary = change_summary.lower()
    if any(part in lowered_summary for part in UNSAFE_METADATA_KEY_PARTS):
        return None
    return redact_sensitive_text(change_summary)


def _audit_log_response(audit_log: AuditLog) -> EvidenceAuditLogRead:
    return EvidenceAuditLogRead(
        id=audit_log.id,
        event_type=audit_log.event_type,
        actor_type=audit_log.actor_type,
        actor_id=audit_log.actor_id,
        entity_type=audit_log.entity_type,
        entity_id=audit_log.entity_id,
        summary=audit_log.summary,
        metadata=filter_safe_metadata(audit_log.metadata_),
        created_at=audit_log.created_at,
    )


def _agent_run_response(agent_run: AgentRunRecord) -> EvidenceAgentRunRead:
    return EvidenceAgentRunRead(
        id=agent_run.id,
        agent_id=agent_run.agent_id,
        run_id=agent_run.run_id,
        correlation_id=agent_run.correlation_id,
        environment=agent_run.environment,
        status=agent_run.status,
        started_at=agent_run.started_at,
        ended_at=agent_run.ended_at,
        summary=agent_run.summary,
        metadata=filter_safe_metadata(agent_run.metadata_),
        created_at=agent_run.created_at,
    )


def _trace_event_response(trace_event: TraceEventRecord) -> EvidenceTraceEventRead:
    return EvidenceTraceEventRead(
        id=trace_event.id,
        agent_id=trace_event.agent_id,
        run_id=trace_event.run_id,
        external_event_id=trace_event.external_event_id,
        correlation_id=trace_event.correlation_id,
        event_type=trace_event.event_type,
        timestamp=trace_event.timestamp,
        summary=trace_event.summary,
        metadata=filter_safe_metadata(trace_event.metadata_),
        created_at=trace_event.created_at,
    )


def _policy_decision_response(
    policy_decision: PolicyDecision,
    *,
    policy_references: dict[UUID, EvidencePolicyReferenceRead],
    rule_references: dict[UUID, EvidencePolicyRuleReferenceRead],
    policy_version_references: dict[UUID, EvidencePolicyVersionReferenceRead],
) -> EvidencePolicyDecisionRead:
    policy = (
        policy_references.get(policy_decision.policy_id)
        if policy_decision.policy_id is not None
        else None
    )
    rule = (
        rule_references.get(policy_decision.rule_id)
        if policy_decision.rule_id is not None
        else None
    )
    policy_version = (
        policy_version_references.get(policy_decision.policy_version_id)
        if policy_decision.policy_version_id is not None
        else None
    )

    return EvidencePolicyDecisionRead(
        id=policy_decision.id,
        agent_id=policy_decision.agent_id,
        policy_id=policy_decision.policy_id,
        policy_version_id=policy_decision.policy_version_id,
        rule_id=policy_decision.rule_id,
        trace_event_id=policy_decision.trace_event_id,
        decision=policy_decision.decision,
        reason=policy_decision.reason,
        context_hash=policy_decision.context_hash,
        policy=policy,
        rule=rule,
        policy_version=policy_version,
        created_at=policy_decision.created_at,
    )


def _human_approval_response(
    human_approval: HumanApproval,
) -> EvidenceHumanApprovalRead:
    return EvidenceHumanApprovalRead(
        id=human_approval.id,
        agent_id=human_approval.agent_id,
        policy_decision_id=human_approval.policy_decision_id,
        status=human_approval.status,
        requested_by_actor_type=human_approval.requested_by_actor_type,
        requested_by_actor_id=human_approval.requested_by_actor_id,
        reviewed_by_actor_type=human_approval.reviewed_by_actor_type,
        reviewed_by_actor_id=human_approval.reviewed_by_actor_id,
        reason=human_approval.reason,
        decision_note=human_approval.decision_note,
        created_at=human_approval.created_at,
        reviewed_at=human_approval.reviewed_at,
        expires_at=human_approval.expires_at,
    )


def _access_grant_response(access_grant: AccessGrant) -> EvidenceAccessGrantRead:
    return EvidenceAccessGrantRead(
        id=access_grant.id,
        name=access_grant.name,
        description=access_grant.description,
        grant_type=access_grant.grant_type,
        subject_type=access_grant.subject_type,
        subject_id=access_grant.subject_id,
        target_type=access_grant.target_type,
        target_id=access_grant.target_id,
        external_ref=access_grant.external_ref,
        status=access_grant.status,
        granted_by_actor_type=access_grant.granted_by_actor_type,
        granted_by_actor_id=access_grant.granted_by_actor_id,
        reason=access_grant.reason,
        expires_at=access_grant.expires_at,
        risk_level=access_grant.risk_level,
        metadata=filter_safe_metadata(access_grant.metadata_),
        created_at=access_grant.created_at,
        updated_at=access_grant.updated_at,
    )


def _capability_reference_response(
    capability: Capability,
) -> EvidenceCapabilityReferenceRead:
    return EvidenceCapabilityReferenceRead(
        id=capability.id,
        name=capability.name,
        description=capability.description,
        capability_type=capability.capability_type,
        external_ref=capability.external_ref,
        status=capability.status,
        risk_level=capability.risk_level,
        metadata=filter_safe_metadata(capability.metadata_),
        created_at=capability.created_at,
        updated_at=capability.updated_at,
    )


def _source_reference_response(source: DataSource) -> EvidenceSourceReferenceRead:
    return EvidenceSourceReferenceRead(
        id=source.id,
        name=source.name,
        description=source.description,
        source_type=source.source_type,
        external_ref=source.external_ref,
        owner_type=source.owner_type,
        owner_id=source.owner_id,
        owner_name=source.owner_name,
        owner_contact_email=source.owner_contact_email,
        status=source.status,
        risk_level=source.risk_level,
        metadata=filter_safe_metadata(source.metadata_),
        created_at=source.created_at,
        updated_at=source.updated_at,
    )


def _data_usage_profile_response(
    profile: DataUsageProfile,
) -> EvidenceDataUsageProfileRead:
    return EvidenceDataUsageProfileRead(
        id=profile.id,
        source_id=profile.source_id,
        data_classification=profile.data_classification,
        contains_personal_data=profile.contains_personal_data,
        contains_sensitive_data=profile.contains_sensitive_data,
        data_categories=profile.data_categories,
        legal_basis=profile.legal_basis,
        allowed_purposes=profile.allowed_purposes,
        prohibited_purposes=profile.prohibited_purposes,
        allowed_processing=profile.allowed_processing,
        prohibited_processing=profile.prohibited_processing,
        residency=profile.residency,
        retention_policy=profile.retention_policy,
        data_owner=profile.data_owner,
        review_status=profile.review_status,
        reviewed_by_actor_type=profile.reviewed_by_actor_type,
        reviewed_by_actor_id=profile.reviewed_by_actor_id,
        reviewed_at=profile.reviewed_at,
        review_expires_at=profile.review_expires_at,
        dpia_required=profile.dpia_required,
        dpia_reference=profile.dpia_reference,
        metadata=filter_safe_metadata(profile.metadata_),
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )


def _model_asset_reference_response(
    model_asset: ModelAsset,
) -> EvidenceModelAssetReferenceRead:
    return EvidenceModelAssetReferenceRead(
        id=model_asset.id,
        name=model_asset.name,
        description=model_asset.description,
        model_type=model_asset.model_type,
        provider=model_asset.provider,
        model_ref=model_asset.model_ref,
        version=model_asset.version,
        owner_type=model_asset.owner_type,
        owner_id=model_asset.owner_id,
        owner_name=model_asset.owner_name,
        owner_contact_email=model_asset.owner_contact_email,
        status=model_asset.status,
        risk_level=model_asset.risk_level,
        metadata=filter_safe_metadata(model_asset.metadata_),
        created_at=model_asset.created_at,
        updated_at=model_asset.updated_at,
    )


def _check_result_response(
    check_result: CheckResult,
    *,
    check_tool: CheckTool | None,
    policy_versions_by_policy_decision_id: dict[
        UUID,
        EvidencePolicyVersionReferenceRead,
    ],
) -> EvidenceCheckResultRead:
    policy_version = (
        policy_versions_by_policy_decision_id.get(check_result.policy_decision_id)
        if check_result.policy_decision_id is not None
        else None
    )
    return EvidenceCheckResultRead(
        check_result_id=check_result.id,
        check_tool_id=check_result.check_tool_id,
        check_tool_name=(
            redact_sensitive_text(check_tool.name) if check_tool is not None else None
        ),
        check_tool_type=check_tool.tool_type if check_tool is not None else None,
        outcome=check_result.outcome,
        confidence=check_result.confidence,
        summary=redact_sensitive_text(check_result.summary),
        reason=(
            redact_sensitive_text(check_result.reason)
            if check_result.reason is not None
            else None
        ),
        target_type=check_result.target_type,
        target_id=check_result.target_id,
        policy_decision_id=check_result.policy_decision_id,
        policy_version_id=(
            policy_version.policy_version_id if policy_version is not None else None
        ),
        policy_version=policy_version,
        trace_event_id=check_result.trace_event_id,
        run_id=check_result.run_id,
        created_at=check_result.created_at,
        metadata=filter_safe_metadata(check_result.metadata_),
    )
