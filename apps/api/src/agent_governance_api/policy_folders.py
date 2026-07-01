from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from agent_governance_api.audit import append_audit_log
from agent_governance_api.auth import ActorContext, get_current_actor
from agent_governance_api.database import get_db_session
from agent_governance_api.models import Policy, PolicyFolder
from agent_governance_api.schemas import (
    PolicyFolderCreate,
    PolicyFolderRead,
    PolicyFolderUpdate,
)

router = APIRouter(prefix="/policy-folders", tags=["policy-folders"])

POLICY_FOLDER_NOT_EMPTY_DETAIL = (
    "PolicyFolder is not empty. Move policies before deleting it."
)


@router.get("", response_model=list[PolicyFolderRead])
def list_policy_folders(
    session: Session = Depends(get_db_session),
) -> list[PolicyFolder]:
    statement = select(PolicyFolder).order_by(
        PolicyFolder.sort_order,
        PolicyFolder.name,
        PolicyFolder.created_at,
        PolicyFolder.id,
    )
    return list(session.scalars(statement).all())


@router.post(
    "",
    response_model=PolicyFolderRead,
    status_code=status.HTTP_201_CREATED,
)
def create_policy_folder(
    payload: PolicyFolderCreate,
    session: Session = Depends(get_db_session),
    actor: ActorContext = Depends(get_current_actor),
) -> PolicyFolder:
    now = datetime.now(UTC)
    folder = PolicyFolder(
        id=uuid4(),
        name=payload.name,
        description=payload.description,
        color=payload.color,
        sort_order=payload.sort_order,
        created_at=now,
        updated_at=now,
    )

    session.add(folder)
    append_audit_log(
        session,
        event_type="policy_folder_created",
        actor_type=actor.actor_type,
        actor_id=actor.actor_id,
        entity_type="policy_folder",
        entity_id=str(folder.id),
        summary="PolicyFolder created.",
        metadata={"operation": "create", "sort_order": folder.sort_order},
    )
    session.commit()
    session.refresh(folder)
    return folder


@router.patch("/{folder_id}", response_model=PolicyFolderRead)
def update_policy_folder(
    folder_id: UUID,
    payload: PolicyFolderUpdate,
    session: Session = Depends(get_db_session),
    actor: ActorContext = Depends(get_current_actor),
) -> PolicyFolder:
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No update fields provided.",
        )

    folder = _get_policy_folder_or_404(session, folder_id)
    for field, value in updates.items():
        setattr(folder, field, value)
    folder.updated_at = datetime.now(UTC)

    append_audit_log(
        session,
        event_type="policy_folder_updated",
        actor_type=actor.actor_type,
        actor_id=actor.actor_id,
        entity_type="policy_folder",
        entity_id=str(folder.id),
        summary="PolicyFolder updated.",
        metadata={"updated_fields": ",".join(sorted(updates))},
    )
    session.commit()
    session.refresh(folder)
    return folder


@router.delete("/{folder_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_policy_folder(
    folder_id: UUID,
    session: Session = Depends(get_db_session),
    actor: ActorContext = Depends(get_current_actor),
) -> Response:
    folder = _get_policy_folder_or_404(session, folder_id)
    if _policy_folder_has_policies(session, folder.id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=POLICY_FOLDER_NOT_EMPTY_DETAIL,
        )

    append_audit_log(
        session,
        event_type="policy_folder_deleted",
        actor_type=actor.actor_type,
        actor_id=actor.actor_id,
        entity_type="policy_folder",
        entity_id=str(folder.id),
        summary="PolicyFolder deleted.",
        metadata={"operation": "delete"},
    )
    session.delete(folder)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _get_policy_folder_or_404(session: Session, folder_id: UUID) -> PolicyFolder:
    folder = session.get(PolicyFolder, folder_id)
    if folder is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PolicyFolder not found.",
        )
    return folder


def _policy_folder_has_policies(session: Session, folder_id: UUID) -> bool:
    return (
        session.scalar(select(Policy.id).where(Policy.folder_id == folder_id).limit(1))
        is not None
    )
