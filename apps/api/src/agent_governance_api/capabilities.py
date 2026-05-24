from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from agent_governance_api.audit import append_audit_log
from agent_governance_api.auth import ActorContext, get_current_actor
from agent_governance_api.database import get_db_session
from agent_governance_api.models import Capability
from agent_governance_api.openapi_examples import (
    CAPABILITY_CREATE_OPENAPI,
    CAPABILITY_GET_OPENAPI,
    CAPABILITY_LIST_OPENAPI,
    CAPABILITY_UPDATE_OPENAPI,
)
from agent_governance_api.schemas import (
    CapabilityCreate,
    CapabilityRead,
    CapabilityUpdate,
)

router = APIRouter(prefix="/capabilities", tags=["capabilities"])


@router.post(
    "",
    response_model=CapabilityRead,
    status_code=status.HTTP_201_CREATED,
    openapi_extra=CAPABILITY_CREATE_OPENAPI,
)
def create_capability(
    payload: CapabilityCreate,
    session: Session = Depends(get_db_session),
    actor: ActorContext = Depends(get_current_actor),
) -> Capability:
    now = datetime.now(UTC)
    capability = Capability(
        id=uuid4(),
        name=payload.name,
        description=payload.description,
        capability_type=payload.capability_type,
        external_ref=payload.external_ref,
        status=payload.status,
        risk_level=payload.risk_level,
        metadata_=payload.metadata,
        created_at=now,
        updated_at=now,
    )

    session.add(capability)
    append_audit_log(
        session,
        event_type="capability_created",
        actor_type=actor.actor_type,
        actor_id=actor.actor_id,
        entity_type="capability",
        entity_id=str(capability.id),
        summary="Capability created.",
        metadata={
            "operation": "create",
            "capability_type": capability.capability_type.value,
            "status": capability.status.value,
            "risk_level": capability.risk_level.value,
        },
    )
    session.commit()
    session.refresh(capability)

    return capability


@router.get(
    "",
    response_model=list[CapabilityRead],
    openapi_extra=CAPABILITY_LIST_OPENAPI,
)
def list_capabilities(session: Session = Depends(get_db_session)) -> list[Capability]:
    statement = select(Capability).order_by(Capability.created_at, Capability.id)
    return list(session.scalars(statement).all())


@router.get(
    "/{capability_id}",
    response_model=CapabilityRead,
    openapi_extra=CAPABILITY_GET_OPENAPI,
)
def get_capability(
    capability_id: UUID,
    session: Session = Depends(get_db_session),
) -> Capability:
    return _get_capability_or_404(session, capability_id)


@router.patch(
    "/{capability_id}",
    response_model=CapabilityRead,
    openapi_extra=CAPABILITY_UPDATE_OPENAPI,
)
def update_capability(
    capability_id: UUID,
    payload: CapabilityUpdate,
    session: Session = Depends(get_db_session),
    actor: ActorContext = Depends(get_current_actor),
) -> Capability:
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No update fields provided.",
        )

    capability = _get_capability_or_404(session, capability_id)
    previous_status = capability.status

    for field, value in updates.items():
        if field == "metadata":
            capability.metadata_ = value
        else:
            setattr(capability, field, value)
    capability.updated_at = datetime.now(UTC)

    status_changed = "status" in updates and capability.status != previous_status
    event_type = "capability_status_changed" if status_changed else "capability_updated"
    metadata = {"updated_fields": ",".join(sorted(updates))}
    if status_changed:
        metadata["status_from"] = _value(previous_status)
        metadata["status_to"] = _value(capability.status)

    append_audit_log(
        session,
        event_type=event_type,
        actor_type=actor.actor_type,
        actor_id=actor.actor_id,
        entity_type="capability",
        entity_id=str(capability.id),
        summary=(
            "Capability status changed." if status_changed else "Capability updated."
        ),
        metadata=metadata,
    )
    session.commit()
    session.refresh(capability)

    return capability


def _get_capability_or_404(
    session: Session,
    capability_id: UUID,
) -> Capability:
    capability = session.get(Capability, capability_id)
    if capability is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Capability not found.",
        )
    return capability


def _value(value: object) -> str:
    enum_value = getattr(value, "value", None)
    if isinstance(enum_value, str):
        return enum_value
    return str(value)
