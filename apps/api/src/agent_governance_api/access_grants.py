from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from agent_governance_api.audit import append_audit_log
from agent_governance_api.auth import ActorContext, get_current_actor
from agent_governance_api.database import get_db_session
from agent_governance_api.models import AccessGrant
from agent_governance_api.openapi_examples import (
    ACCESS_GRANT_CREATE_OPENAPI,
    ACCESS_GRANT_GET_OPENAPI,
    ACCESS_GRANT_LIST_OPENAPI,
    ACCESS_GRANT_UPDATE_OPENAPI,
)
from agent_governance_api.schemas import (
    AccessGrantCreate,
    AccessGrantRead,
    AccessGrantUpdate,
)

router = APIRouter(prefix="/access-grants", tags=["access grants"])


@router.post(
    "",
    response_model=AccessGrantRead,
    status_code=status.HTTP_201_CREATED,
    openapi_extra=ACCESS_GRANT_CREATE_OPENAPI,
)
def create_access_grant(
    payload: AccessGrantCreate,
    session: Session = Depends(get_db_session),
    actor: ActorContext = Depends(get_current_actor),
) -> AccessGrant:
    now = datetime.now(UTC)
    access_grant = AccessGrant(
        id=uuid4(),
        name=payload.name,
        description=payload.description,
        grant_type=payload.grant_type,
        subject_type=payload.subject_type,
        subject_id=payload.subject_id,
        target_type=payload.target_type,
        target_id=payload.target_id,
        external_ref=payload.external_ref,
        status=payload.status,
        granted_by_actor_type=actor.actor_type,
        granted_by_actor_id=actor.actor_id,
        reason=payload.reason,
        expires_at=payload.expires_at,
        risk_level=payload.risk_level,
        metadata_=payload.metadata,
        created_at=now,
        updated_at=now,
    )

    session.add(access_grant)
    append_audit_log(
        session,
        event_type="access_grant_created",
        actor_type=actor.actor_type,
        actor_id=actor.actor_id,
        entity_type="access_grant",
        entity_id=str(access_grant.id),
        summary="Access grant created.",
        metadata=_audit_metadata(access_grant, operation="create"),
    )
    session.commit()
    session.refresh(access_grant)

    return access_grant


@router.get(
    "",
    response_model=list[AccessGrantRead],
    openapi_extra=ACCESS_GRANT_LIST_OPENAPI,
)
def list_access_grants(
    session: Session = Depends(get_db_session),
) -> list[AccessGrant]:
    statement = select(AccessGrant).order_by(AccessGrant.created_at, AccessGrant.id)
    return list(session.scalars(statement).all())


@router.get(
    "/{access_grant_id}",
    response_model=AccessGrantRead,
    openapi_extra=ACCESS_GRANT_GET_OPENAPI,
)
def get_access_grant(
    access_grant_id: UUID,
    session: Session = Depends(get_db_session),
) -> AccessGrant:
    return _get_access_grant_or_404(session, access_grant_id)


@router.patch(
    "/{access_grant_id}",
    response_model=AccessGrantRead,
    openapi_extra=ACCESS_GRANT_UPDATE_OPENAPI,
)
def update_access_grant(
    access_grant_id: UUID,
    payload: AccessGrantUpdate,
    session: Session = Depends(get_db_session),
    actor: ActorContext = Depends(get_current_actor),
) -> AccessGrant:
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No update fields provided.",
        )

    access_grant = _get_access_grant_or_404(session, access_grant_id)
    previous_status = access_grant.status

    for field, value in updates.items():
        if field == "metadata":
            access_grant.metadata_ = value
        else:
            setattr(access_grant, field, value)
    access_grant.updated_at = datetime.now(UTC)

    status_changed = "status" in updates and access_grant.status != previous_status
    event_type = (
        "access_grant_status_changed" if status_changed else "access_grant_updated"
    )
    metadata = {"updated_fields": ",".join(sorted(updates))}
    if status_changed:
        metadata["status_from"] = _value(previous_status)
        metadata["status_to"] = _value(access_grant.status)

    append_audit_log(
        session,
        event_type=event_type,
        actor_type=actor.actor_type,
        actor_id=actor.actor_id,
        entity_type="access_grant",
        entity_id=str(access_grant.id),
        summary=(
            "Access grant status changed."
            if status_changed
            else "Access grant updated."
        ),
        metadata=metadata,
    )
    session.commit()
    session.refresh(access_grant)

    return access_grant


def _get_access_grant_or_404(
    session: Session,
    access_grant_id: UUID,
) -> AccessGrant:
    access_grant = session.get(AccessGrant, access_grant_id)
    if access_grant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Access grant not found.",
        )
    return access_grant


def _audit_metadata(
    access_grant: AccessGrant,
    *,
    operation: str,
) -> dict[str, str | None]:
    return {
        "operation": operation,
        "grant_type": access_grant.grant_type.value,
        "subject_type": access_grant.subject_type.value,
        "subject_id": str(access_grant.subject_id),
        "target_type": access_grant.target_type.value,
        "target_id": str(access_grant.target_id) if access_grant.target_id else None,
        "status": access_grant.status.value,
        "risk_level": access_grant.risk_level.value,
    }


def _value(value: object) -> str:
    enum_value = getattr(value, "value", None)
    if isinstance(enum_value, str):
        return enum_value
    return str(value)
