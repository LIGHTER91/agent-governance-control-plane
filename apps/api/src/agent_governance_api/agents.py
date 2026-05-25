from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from agent_governance_api.activity import build_agent_activity
from agent_governance_api.audit import append_audit_log
from agent_governance_api.auth import (
    ROLE_AUDITOR,
    ROLE_PLATFORM_ADMIN,
    ROLE_REVIEWER,
    ActorContext,
    get_current_actor,
    has_role,
    require_role,
)
from agent_governance_api.database import get_db_session
from agent_governance_api.evidence import build_agent_evidence_bundle
from agent_governance_api.governance_profile import build_agent_governance_profile
from agent_governance_api.models import (
    AccessGrant,
    AccessGrantStatus,
    AccessGrantSubjectType,
    AccessGrantTargetType,
    ActorType,
    Agent,
    OwnerType,
)
from agent_governance_api.openapi_examples import (
    AGENT_ACCESS_GRANTS_OPENAPI,
    AGENT_ACTIVITY_OPENAPI,
    AGENT_CREATE_OPENAPI,
    AGENT_GET_OPENAPI,
    AGENT_GOVERNANCE_PROFILE_OPENAPI,
    AGENT_LIST_OPENAPI,
    AGENT_UPDATE_OPENAPI,
    EVIDENCE_BUNDLE_OPENAPI,
)
from agent_governance_api.schemas import (
    AccessGrantRead,
    AgentActivityItemRead,
    AgentCreate,
    AgentGovernanceProfileRead,
    AgentRead,
    AgentUpdate,
    EvidenceBundleRead,
)

router = APIRouter(prefix="/agents", tags=["agents"])


@router.post(
    "",
    response_model=AgentRead,
    status_code=status.HTTP_201_CREATED,
    openapi_extra=AGENT_CREATE_OPENAPI,
)
def create_agent(
    payload: AgentCreate,
    session: Session = Depends(get_db_session),
    actor: ActorContext = Depends(get_current_actor),
) -> Agent:
    now = datetime.now(UTC)
    agent = Agent(
        id=uuid4(),
        created_at=now,
        updated_at=now,
        **payload.model_dump(),
    )

    session.add(agent)
    append_audit_log(
        session,
        event_type="agent_created",
        actor_type=actor.actor_type,
        actor_id=actor.actor_id,
        entity_type="agent",
        entity_id=str(agent.id),
        summary="Agent created.",
        metadata={"operation": "create"},
    )
    session.commit()
    session.refresh(agent)

    return agent


@router.get("", response_model=list[AgentRead], openapi_extra=AGENT_LIST_OPENAPI)
def list_agents(session: Session = Depends(get_db_session)) -> list[Agent]:
    statement = select(Agent).order_by(Agent.created_at, Agent.id)
    return list(session.scalars(statement).all())


@router.get("/{agent_id}", response_model=AgentRead, openapi_extra=AGENT_GET_OPENAPI)
def get_agent(
    agent_id: UUID,
    session: Session = Depends(get_db_session),
) -> Agent:
    return _get_agent_or_404(session, agent_id)


@router.get(
    "/{agent_id}/governance-profile",
    response_model=AgentGovernanceProfileRead,
    openapi_extra=AGENT_GOVERNANCE_PROFILE_OPENAPI,
)
def get_agent_governance_profile(
    agent_id: UUID,
    session: Session = Depends(get_db_session),
    actor: ActorContext = Depends(get_current_actor),
) -> AgentGovernanceProfileRead:
    agent = _get_agent_or_404(session, agent_id)
    return build_agent_governance_profile(
        session,
        agent=agent,
        evidence_bundle_access=_evidence_bundle_access(actor, agent),
    )


@router.get(
    "/{agent_id}/access-grants",
    response_model=list[AccessGrantRead],
    openapi_extra=AGENT_ACCESS_GRANTS_OPENAPI,
)
def list_agent_access_grants(
    agent_id: UUID,
    status: AccessGrantStatus | None = None,
    target_type: AccessGrantTargetType | None = None,
    session: Session = Depends(get_db_session),
) -> list[AccessGrant]:
    _get_agent_or_404(session, agent_id)

    statement = select(AccessGrant).where(
        AccessGrant.subject_type == AccessGrantSubjectType.AGENT,
        AccessGrant.subject_id == agent_id,
    )
    if status is not None:
        statement = statement.where(AccessGrant.status == status)
    if target_type is not None:
        statement = statement.where(AccessGrant.target_type == target_type)

    statement = statement.order_by(AccessGrant.created_at.desc(), AccessGrant.id.desc())
    return list(session.scalars(statement).all())


@router.get(
    "/{agent_id}/activity",
    response_model=list[AgentActivityItemRead],
    openapi_extra=AGENT_ACTIVITY_OPENAPI,
)
def list_agent_activity(
    agent_id: UUID,
    session: Session = Depends(get_db_session),
    actor: ActorContext = Depends(get_current_actor),
) -> list[AgentActivityItemRead]:
    _require_agent_activity_reader(actor)
    agent = _get_agent_or_404(session, agent_id)
    return build_agent_activity(session, agent=agent)


@router.get(
    "/{agent_id}/evidence-bundle",
    response_model=EvidenceBundleRead,
    openapi_extra=EVIDENCE_BUNDLE_OPENAPI,
)
def export_agent_evidence_bundle(
    agent_id: UUID,
    session: Session = Depends(get_db_session),
    actor: ActorContext = Depends(get_current_actor),
) -> EvidenceBundleRead:
    agent = session.get(Agent, agent_id)
    try:
        _require_evidence_bundle_exporter(actor, agent)
    except HTTPException:
        if agent is not None:
            append_audit_log(
                session,
                event_type="evidence_bundle_export_denied",
                actor_type=actor.actor_type,
                actor_id=actor.actor_id,
                entity_type="agent",
                entity_id=str(agent.id),
                summary="Evidence Bundle export denied.",
                metadata={
                    "agent_id": str(agent.id),
                    "reason": "forbidden",
                    "export_format": "json",
                },
            )
            session.commit()
        raise

    if agent is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found.",
        )

    evidence_bundle = build_agent_evidence_bundle(session, agent=agent)

    append_audit_log(
        session,
        event_type="evidence_bundle_exported",
        actor_type=actor.actor_type,
        actor_id=actor.actor_id,
        entity_type="agent",
        entity_id=str(agent.id),
        summary="Evidence Bundle exported.",
        metadata={
            "agent_id": str(agent.id),
            "export_format": "json",
            "audit_log_count": len(evidence_bundle.audit_logs),
            "agent_run_count": len(evidence_bundle.agent_runs),
            "trace_event_count": len(evidence_bundle.trace_events),
            "policy_decision_count": len(evidence_bundle.policy_decisions),
            "human_approval_count": len(evidence_bundle.human_approvals),
            "access_grant_count": len(evidence_bundle.access_grants),
            "capability_reference_count": len(evidence_bundle.capability_references),
            "source_reference_count": len(evidence_bundle.source_references),
            "model_asset_reference_count": len(evidence_bundle.model_asset_references),
        },
    )
    session.commit()

    return evidence_bundle


@router.patch(
    "/{agent_id}",
    response_model=AgentRead,
    openapi_extra=AGENT_UPDATE_OPENAPI,
)
def update_agent(
    agent_id: UUID,
    payload: AgentUpdate,
    session: Session = Depends(get_db_session),
    actor: ActorContext = Depends(get_current_actor),
) -> Agent:
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No update fields provided.",
        )

    agent = _get_agent_or_404(session, agent_id)
    previous_status = agent.status

    for field, value in updates.items():
        setattr(agent, field, value)
    agent.updated_at = datetime.now(UTC)

    status_changed = "status" in updates and agent.status != previous_status
    event_type = "agent_status_changed" if status_changed else "agent_updated"
    metadata = {"updated_fields": ",".join(sorted(updates))}
    if status_changed:
        metadata["status_from"] = _value(previous_status)
        metadata["status_to"] = _value(agent.status)

    append_audit_log(
        session,
        event_type=event_type,
        actor_type=actor.actor_type,
        actor_id=actor.actor_id,
        entity_type="agent",
        entity_id=str(agent.id),
        summary="Agent status changed." if status_changed else "Agent updated.",
        metadata=metadata,
    )
    session.commit()
    session.refresh(agent)

    return agent


def _get_agent_or_404(session: Session, agent_id: UUID) -> Agent:
    agent = session.get(Agent, agent_id)
    if agent is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found.",
        )
    return agent


def _require_evidence_bundle_exporter(
    actor: ActorContext,
    agent: Agent | None,
) -> None:
    if actor.actor_type is ActorType.SERVICE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Evidence Bundle export is not permitted for this actor.",
        )

    if has_role(actor, ROLE_AUDITOR) or has_role(actor, ROLE_PLATFORM_ADMIN):
        return

    if agent is not None and _is_direct_user_owner(actor, agent):
        return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Evidence Bundle export is not permitted for this actor.",
    )


def _is_direct_user_owner(actor: ActorContext, agent: Agent) -> bool:
    return (
        actor.actor_type is ActorType.USER
        and agent.owner_type is OwnerType.USER
        and actor.actor_id == agent.owner_id
    )


def _evidence_bundle_access(actor: ActorContext, agent: Agent) -> str:
    try:
        _require_evidence_bundle_exporter(actor, agent)
    except HTTPException:
        return "restricted"
    return "allowed"


def _require_agent_activity_reader(actor: ActorContext) -> None:
    if actor.actor_type is ActorType.SERVICE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Service actors cannot view Agent activity.",
        )

    require_role(actor, (ROLE_REVIEWER, ROLE_AUDITOR, ROLE_PLATFORM_ADMIN))


def _value(value: object) -> str:
    enum_value = getattr(value, "value", None)
    if isinstance(enum_value, str):
        return enum_value
    return str(value)
