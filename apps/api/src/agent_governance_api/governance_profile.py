from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from agent_governance_api.activity import build_recent_agent_activity
from agent_governance_api.metadata_safety import filter_safe_metadata
from agent_governance_api.models import (
    AccessGrant,
    AccessGrantSubjectType,
    AccessGrantTargetType,
    Agent,
    Capability,
    DataSource,
    HumanApproval,
    ModelAsset,
    PolicyDecision,
)
from agent_governance_api.schemas import (
    AgentGovernanceProfileAccessGrantRead,
    AgentGovernanceProfileEvidenceBundleHintRead,
    AgentGovernanceProfileHumanApprovalSummaryRead,
    AgentGovernanceProfileOwnerRead,
    AgentGovernanceProfilePolicySummaryRead,
    AgentGovernanceProfileRead,
    AgentGovernanceProfileRecentActivityRead,
    AgentGovernanceProfileTargetReferenceRead,
    AgentRead,
    EvidenceHumanApprovalRead,
)

RECENT_ACTIVITY_LIMIT = 5
RECENT_HUMAN_APPROVAL_LIMIT = 5


def build_agent_governance_profile(
    session: Session,
    *,
    agent: Agent,
    evidence_bundle_access: str,
) -> AgentGovernanceProfileRead:
    access_grants = _load_agent_access_grants(session, agent.id)
    target_references = _load_target_references(session, access_grants)

    return AgentGovernanceProfileRead(
        agent=AgentRead.model_validate(agent),
        owner=AgentGovernanceProfileOwnerRead(
            owner_type=agent.owner_type,
            owner_id=agent.owner_id,
            owner_name=agent.owner_name,
            owner_contact_email=agent.owner_contact_email,
        ),
        environment=agent.environment,
        status=agent.status,
        risk_level=agent.risk_level,
        recent_activity=AgentGovernanceProfileRecentActivityRead(
            limit=RECENT_ACTIVITY_LIMIT,
            items=build_recent_agent_activity(
                session,
                agent=agent,
                limit=RECENT_ACTIVITY_LIMIT,
            ),
        ),
        human_approvals=_build_human_approval_summary(session, agent.id),
        access_grants=[
            _access_grant_response(
                access_grant,
                target_references=target_references,
            )
            for access_grant in access_grants
        ],
        policy_summary=_build_policy_summary(session, agent.id),
        evidence_bundle=AgentGovernanceProfileEvidenceBundleHintRead(
            available=True,
            export_path=f"/agents/{agent.id}/evidence-bundle",
            access=evidence_bundle_access,
        ),
    )


def _load_agent_access_grants(session: Session, agent_id: UUID) -> list[AccessGrant]:
    statement = (
        select(AccessGrant)
        .where(
            AccessGrant.subject_type == AccessGrantSubjectType.AGENT,
            AccessGrant.subject_id == agent_id,
        )
        .order_by(AccessGrant.created_at.desc(), AccessGrant.id.desc())
    )
    return list(session.scalars(statement).all())


def _load_target_references(
    session: Session,
    access_grants: list[AccessGrant],
) -> dict[
    tuple[AccessGrantTargetType, UUID],
    AgentGovernanceProfileTargetReferenceRead,
]:
    references: dict[
        tuple[AccessGrantTargetType, UUID],
        AgentGovernanceProfileTargetReferenceRead,
    ] = {}
    capability_ids = _target_ids(access_grants, AccessGrantTargetType.CAPABILITY)
    source_ids = _target_ids(access_grants, AccessGrantTargetType.SOURCE)
    model_asset_ids = _target_ids(access_grants, AccessGrantTargetType.MODEL_ASSET)

    if capability_ids:
        statement = select(Capability).where(Capability.id.in_(capability_ids))
        for capability in session.scalars(statement).all():
            references[(AccessGrantTargetType.CAPABILITY, capability.id)] = (
                AgentGovernanceProfileTargetReferenceRead(
                    target_type=AccessGrantTargetType.CAPABILITY,
                    id=capability.id,
                    name=capability.name,
                    status=capability.status,
                    risk_level=capability.risk_level,
                    external_ref=capability.external_ref,
                    inventory_type=capability.capability_type,
                )
            )

    if source_ids:
        statement = select(DataSource).where(DataSource.id.in_(source_ids))
        for source in session.scalars(statement).all():
            references[(AccessGrantTargetType.SOURCE, source.id)] = (
                AgentGovernanceProfileTargetReferenceRead(
                    target_type=AccessGrantTargetType.SOURCE,
                    id=source.id,
                    name=source.name,
                    status=source.status,
                    risk_level=source.risk_level,
                    external_ref=source.external_ref,
                    inventory_type=source.source_type,
                )
            )

    if model_asset_ids:
        statement = select(ModelAsset).where(ModelAsset.id.in_(model_asset_ids))
        for model_asset in session.scalars(statement).all():
            references[(AccessGrantTargetType.MODEL_ASSET, model_asset.id)] = (
                AgentGovernanceProfileTargetReferenceRead(
                    target_type=AccessGrantTargetType.MODEL_ASSET,
                    id=model_asset.id,
                    name=model_asset.name,
                    status=model_asset.status,
                    risk_level=model_asset.risk_level,
                    external_ref=model_asset.model_ref,
                    inventory_type=model_asset.model_type,
                    provider=model_asset.provider,
                    version=model_asset.version,
                )
            )

    return references


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


def _access_grant_response(
    access_grant: AccessGrant,
    *,
    target_references: dict[
        tuple[AccessGrantTargetType, UUID],
        AgentGovernanceProfileTargetReferenceRead,
    ],
) -> AgentGovernanceProfileAccessGrantRead:
    target = (
        target_references.get((access_grant.target_type, access_grant.target_id))
        if access_grant.target_id is not None
        else None
    )
    return AgentGovernanceProfileAccessGrantRead(
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
        target=target,
        created_at=access_grant.created_at,
        updated_at=access_grant.updated_at,
    )


def _build_human_approval_summary(
    session: Session,
    agent_id: UUID,
) -> AgentGovernanceProfileHumanApprovalSummaryRead:
    recent_statement = (
        select(HumanApproval)
        .where(HumanApproval.agent_id == agent_id)
        .order_by(HumanApproval.created_at.desc(), HumanApproval.id.desc())
        .limit(RECENT_HUMAN_APPROVAL_LIMIT)
    )
    counts_statement = (
        select(HumanApproval.status, func.count(HumanApproval.id))
        .where(HumanApproval.agent_id == agent_id)
        .group_by(HumanApproval.status)
    )
    counts = {
        status.value: count for status, count in session.execute(counts_statement).all()
    }

    return AgentGovernanceProfileHumanApprovalSummaryRead(
        total_count=sum(counts.values()),
        by_status=counts,
        recent=[
            _human_approval_response(human_approval)
            for human_approval in session.scalars(recent_statement).all()
        ],
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


def _build_policy_summary(
    session: Session,
    agent_id: UUID,
) -> AgentGovernanceProfilePolicySummaryRead:
    decision_count = session.scalar(
        select(func.count(PolicyDecision.id)).where(PolicyDecision.agent_id == agent_id)
    )
    policy_ids = _distinct_policy_decision_ids(
        session,
        agent_id=agent_id,
        column=PolicyDecision.policy_id,
    )
    rule_ids = _distinct_policy_decision_ids(
        session,
        agent_id=agent_id,
        column=PolicyDecision.rule_id,
    )

    return AgentGovernanceProfilePolicySummaryRead(
        policy_decision_count=decision_count or 0,
        referenced_policy_ids=policy_ids,
        referenced_rule_ids=rule_ids,
    )


def _distinct_policy_decision_ids(
    session: Session,
    *,
    agent_id: UUID,
    column: Any,
) -> list[UUID]:
    statement = (
        select(column)
        .where(PolicyDecision.agent_id == agent_id, column.is_not(None))
        .distinct()
    )
    return sorted(session.scalars(statement).all(), key=str)
