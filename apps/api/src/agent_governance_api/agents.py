from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from agent_governance_api.audit import append_audit_log
from agent_governance_api.database import get_db_session
from agent_governance_api.evidence import build_agent_evidence_bundle
from agent_governance_api.models import ActorType, Agent
from agent_governance_api.openapi_examples import (
    AGENT_CREATE_OPENAPI,
    AGENT_GET_OPENAPI,
    AGENT_LIST_OPENAPI,
    AGENT_UPDATE_OPENAPI,
    EVIDENCE_BUNDLE_OPENAPI,
)
from agent_governance_api.schemas import (
    AgentCreate,
    AgentRead,
    AgentUpdate,
    EvidenceBundleRead,
)

router = APIRouter(prefix="/agents", tags=["agents"])

DEVELOPMENT_ACTOR_TYPE = ActorType.DEVELOPMENT
DEVELOPMENT_ACTOR_ID = "dev-placeholder"


@router.post(
    "",
    response_model=AgentRead,
    status_code=status.HTTP_201_CREATED,
    openapi_extra=AGENT_CREATE_OPENAPI,
)
def create_agent(
    payload: AgentCreate,
    session: Session = Depends(get_db_session),
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
        actor_type=DEVELOPMENT_ACTOR_TYPE,
        actor_id=DEVELOPMENT_ACTOR_ID,
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
    "/{agent_id}/evidence-bundle",
    response_model=EvidenceBundleRead,
    openapi_extra=EVIDENCE_BUNDLE_OPENAPI,
)
def export_agent_evidence_bundle(
    agent_id: UUID,
    session: Session = Depends(get_db_session),
) -> EvidenceBundleRead:
    agent = _get_agent_or_404(session, agent_id)
    return build_agent_evidence_bundle(session, agent=agent)


@router.patch(
    "/{agent_id}",
    response_model=AgentRead,
    openapi_extra=AGENT_UPDATE_OPENAPI,
)
def update_agent(
    agent_id: UUID,
    payload: AgentUpdate,
    session: Session = Depends(get_db_session),
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
        actor_type=DEVELOPMENT_ACTOR_TYPE,
        actor_id=DEVELOPMENT_ACTOR_ID,
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


def _value(value: object) -> str:
    enum_value = getattr(value, "value", None)
    if isinstance(enum_value, str):
        return enum_value
    return str(value)
