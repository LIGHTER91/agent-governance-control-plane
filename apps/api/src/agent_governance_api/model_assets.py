from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from agent_governance_api.audit import append_audit_log
from agent_governance_api.auth import ActorContext, get_current_actor
from agent_governance_api.database import get_db_session
from agent_governance_api.models import ModelAsset
from agent_governance_api.openapi_examples import (
    MODEL_ASSET_CREATE_OPENAPI,
    MODEL_ASSET_GET_OPENAPI,
    MODEL_ASSET_LIST_OPENAPI,
    MODEL_ASSET_UPDATE_OPENAPI,
)
from agent_governance_api.schemas import (
    ModelAssetCreate,
    ModelAssetRead,
    ModelAssetUpdate,
)

router = APIRouter(prefix="/models", tags=["models"])


@router.post(
    "",
    response_model=ModelAssetRead,
    status_code=status.HTTP_201_CREATED,
    openapi_extra=MODEL_ASSET_CREATE_OPENAPI,
)
def create_model_asset(
    payload: ModelAssetCreate,
    session: Session = Depends(get_db_session),
    actor: ActorContext = Depends(get_current_actor),
) -> ModelAsset:
    now = datetime.now(UTC)
    model_asset = ModelAsset(
        id=uuid4(),
        name=payload.name,
        description=payload.description,
        model_type=payload.model_type,
        provider=payload.provider,
        model_ref=payload.model_ref,
        version=payload.version,
        owner_type=payload.owner_type,
        owner_id=payload.owner_id,
        owner_name=payload.owner_name,
        owner_contact_email=payload.owner_contact_email,
        status=payload.status,
        risk_level=payload.risk_level,
        metadata_=payload.metadata,
        created_at=now,
        updated_at=now,
    )

    session.add(model_asset)
    append_audit_log(
        session,
        event_type="model_asset_created",
        actor_type=actor.actor_type,
        actor_id=actor.actor_id,
        entity_type="model_asset",
        entity_id=str(model_asset.id),
        summary="Model asset created.",
        metadata={
            "operation": "create",
            "model_type": model_asset.model_type.value,
            "provider": model_asset.provider.value,
            "owner_type": model_asset.owner_type.value,
            "status": model_asset.status.value,
            "risk_level": model_asset.risk_level.value,
        },
    )
    session.commit()
    session.refresh(model_asset)

    return model_asset


@router.get(
    "",
    response_model=list[ModelAssetRead],
    openapi_extra=MODEL_ASSET_LIST_OPENAPI,
)
def list_model_assets(
    session: Session = Depends(get_db_session),
) -> list[ModelAsset]:
    statement = select(ModelAsset).order_by(ModelAsset.created_at, ModelAsset.id)
    return list(session.scalars(statement).all())


@router.get(
    "/{model_id}",
    response_model=ModelAssetRead,
    openapi_extra=MODEL_ASSET_GET_OPENAPI,
)
def get_model_asset(
    model_id: UUID,
    session: Session = Depends(get_db_session),
) -> ModelAsset:
    return _get_model_asset_or_404(session, model_id)


@router.patch(
    "/{model_id}",
    response_model=ModelAssetRead,
    openapi_extra=MODEL_ASSET_UPDATE_OPENAPI,
)
def update_model_asset(
    model_id: UUID,
    payload: ModelAssetUpdate,
    session: Session = Depends(get_db_session),
    actor: ActorContext = Depends(get_current_actor),
) -> ModelAsset:
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No update fields provided.",
        )

    model_asset = _get_model_asset_or_404(session, model_id)
    previous_status = model_asset.status

    for field, value in updates.items():
        if field == "metadata":
            model_asset.metadata_ = value
        else:
            setattr(model_asset, field, value)
    model_asset.updated_at = datetime.now(UTC)

    status_changed = "status" in updates and model_asset.status != previous_status
    event_type = (
        "model_asset_status_changed" if status_changed else "model_asset_updated"
    )
    metadata = {"updated_fields": ",".join(sorted(updates))}
    if status_changed:
        metadata["status_from"] = _value(previous_status)
        metadata["status_to"] = _value(model_asset.status)

    append_audit_log(
        session,
        event_type=event_type,
        actor_type=actor.actor_type,
        actor_id=actor.actor_id,
        entity_type="model_asset",
        entity_id=str(model_asset.id),
        summary=(
            "Model asset status changed." if status_changed else "Model asset updated."
        ),
        metadata=metadata,
    )
    session.commit()
    session.refresh(model_asset)

    return model_asset


def _get_model_asset_or_404(
    session: Session,
    model_id: UUID,
) -> ModelAsset:
    model_asset = session.get(ModelAsset, model_id)
    if model_asset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model asset not found.",
        )
    return model_asset


def _value(value: object) -> str:
    enum_value = getattr(value, "value", None)
    if isinstance(enum_value, str):
        return enum_value
    return str(value)
