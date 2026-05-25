from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from agent_governance_api.audit import append_audit_log
from agent_governance_api.auth import ActorContext, get_current_actor
from agent_governance_api.database import get_db_session
from agent_governance_api.models import DataSource, DataUsageProfile
from agent_governance_api.openapi_examples import (
    SOURCE_CREATE_OPENAPI,
    SOURCE_GET_OPENAPI,
    SOURCE_LIST_OPENAPI,
    SOURCE_UPDATE_OPENAPI,
)
from agent_governance_api.schemas import (
    DataSourceCreate,
    DataSourceRead,
    DataSourceUpdate,
    DataUsageProfileCreate,
    DataUsageProfileRead,
    DataUsageProfileUpdate,
)

router = APIRouter(prefix="/sources", tags=["sources"])


@router.post(
    "",
    response_model=DataSourceRead,
    status_code=status.HTTP_201_CREATED,
    openapi_extra=SOURCE_CREATE_OPENAPI,
)
def create_source(
    payload: DataSourceCreate,
    session: Session = Depends(get_db_session),
    actor: ActorContext = Depends(get_current_actor),
) -> DataSource:
    now = datetime.now(UTC)
    source = DataSource(
        id=uuid4(),
        name=payload.name,
        description=payload.description,
        source_type=payload.source_type,
        external_ref=payload.external_ref,
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

    session.add(source)
    append_audit_log(
        session,
        event_type="source_created",
        actor_type=actor.actor_type,
        actor_id=actor.actor_id,
        entity_type="source",
        entity_id=str(source.id),
        summary="Source created.",
        metadata={
            "operation": "create",
            "source_type": source.source_type.value,
            "owner_type": source.owner_type.value,
            "status": source.status.value,
            "risk_level": source.risk_level.value,
        },
    )
    session.commit()
    session.refresh(source)

    return source


@router.get(
    "",
    response_model=list[DataSourceRead],
    openapi_extra=SOURCE_LIST_OPENAPI,
)
def list_sources(session: Session = Depends(get_db_session)) -> list[DataSource]:
    statement = select(DataSource).order_by(DataSource.created_at, DataSource.id)
    return list(session.scalars(statement).all())


@router.post(
    "/{source_id}/usage-profile",
    response_model=DataUsageProfileRead,
    status_code=status.HTTP_201_CREATED,
)
def create_source_usage_profile(
    source_id: UUID,
    payload: DataUsageProfileCreate,
    session: Session = Depends(get_db_session),
    actor: ActorContext = Depends(get_current_actor),
) -> DataUsageProfile:
    _get_source_or_404(session, source_id)

    existing_profile = _get_usage_profile_for_source(session, source_id)
    if existing_profile is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Data usage profile already exists for source.",
        )

    now = datetime.now(UTC)
    profile = DataUsageProfile(
        id=uuid4(),
        source_id=source_id,
        data_classification=payload.data_classification,
        contains_personal_data=payload.contains_personal_data,
        contains_sensitive_data=payload.contains_sensitive_data,
        data_categories=payload.data_categories,
        legal_basis=payload.legal_basis,
        allowed_purposes=payload.allowed_purposes,
        prohibited_purposes=payload.prohibited_purposes,
        allowed_processing=payload.allowed_processing,
        prohibited_processing=payload.prohibited_processing,
        residency=payload.residency,
        retention_policy=payload.retention_policy,
        data_owner=payload.data_owner,
        review_status=payload.review_status,
        reviewed_by_actor_type=payload.reviewed_by_actor_type,
        reviewed_by_actor_id=payload.reviewed_by_actor_id,
        reviewed_at=payload.reviewed_at,
        review_expires_at=payload.review_expires_at,
        dpia_required=payload.dpia_required,
        dpia_reference=payload.dpia_reference,
        metadata_=payload.metadata,
        created_at=now,
        updated_at=now,
    )

    session.add(profile)
    append_audit_log(
        session,
        event_type="data_usage_profile_created",
        actor_type=actor.actor_type,
        actor_id=actor.actor_id,
        entity_type="data_usage_profile",
        entity_id=str(profile.id),
        summary="Data usage profile created.",
        metadata={
            "operation": "create",
            "source_id": str(source_id),
            "data_classification": profile.data_classification.value,
            "review_status": profile.review_status.value,
            "contains_personal_data": profile.contains_personal_data,
            "contains_sensitive_data": profile.contains_sensitive_data,
            "dpia_required": profile.dpia_required,
        },
    )
    session.commit()
    session.refresh(profile)

    return profile


@router.get(
    "/{source_id}/usage-profile",
    response_model=DataUsageProfileRead,
)
def get_source_usage_profile(
    source_id: UUID,
    session: Session = Depends(get_db_session),
) -> DataUsageProfile:
    _get_source_or_404(session, source_id)
    return _get_usage_profile_for_source_or_404(session, source_id)


@router.patch(
    "/{source_id}/usage-profile",
    response_model=DataUsageProfileRead,
)
def update_source_usage_profile(
    source_id: UUID,
    payload: DataUsageProfileUpdate,
    session: Session = Depends(get_db_session),
    actor: ActorContext = Depends(get_current_actor),
) -> DataUsageProfile:
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No update fields provided.",
        )

    _get_source_or_404(session, source_id)
    profile = _get_usage_profile_for_source_or_404(session, source_id)
    previous_review_status = profile.review_status

    for field, value in updates.items():
        if field == "metadata":
            profile.metadata_ = value
        else:
            setattr(profile, field, value)
    profile.updated_at = datetime.now(UTC)

    review_status_changed = (
        "review_status" in updates and profile.review_status != previous_review_status
    )
    event_type = (
        "data_usage_profile_review_status_changed"
        if review_status_changed
        else "data_usage_profile_updated"
    )
    metadata = {
        "source_id": str(source_id),
        "updated_fields": ",".join(sorted(updates)),
    }
    if review_status_changed:
        metadata["review_status_from"] = _value(previous_review_status)
        metadata["review_status_to"] = _value(profile.review_status)

    append_audit_log(
        session,
        event_type=event_type,
        actor_type=actor.actor_type,
        actor_id=actor.actor_id,
        entity_type="data_usage_profile",
        entity_id=str(profile.id),
        summary=(
            "Data usage profile review status changed."
            if review_status_changed
            else "Data usage profile updated."
        ),
        metadata=metadata,
    )
    session.commit()
    session.refresh(profile)

    return profile


@router.get(
    "/{source_id}",
    response_model=DataSourceRead,
    openapi_extra=SOURCE_GET_OPENAPI,
)
def get_source(
    source_id: UUID,
    session: Session = Depends(get_db_session),
) -> DataSource:
    return _get_source_or_404(session, source_id)


@router.patch(
    "/{source_id}",
    response_model=DataSourceRead,
    openapi_extra=SOURCE_UPDATE_OPENAPI,
)
def update_source(
    source_id: UUID,
    payload: DataSourceUpdate,
    session: Session = Depends(get_db_session),
    actor: ActorContext = Depends(get_current_actor),
) -> DataSource:
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No update fields provided.",
        )

    source = _get_source_or_404(session, source_id)
    previous_status = source.status

    for field, value in updates.items():
        if field == "metadata":
            source.metadata_ = value
        else:
            setattr(source, field, value)
    source.updated_at = datetime.now(UTC)

    status_changed = "status" in updates and source.status != previous_status
    event_type = "source_status_changed" if status_changed else "source_updated"
    metadata = {"updated_fields": ",".join(sorted(updates))}
    if status_changed:
        metadata["status_from"] = _value(previous_status)
        metadata["status_to"] = _value(source.status)

    append_audit_log(
        session,
        event_type=event_type,
        actor_type=actor.actor_type,
        actor_id=actor.actor_id,
        entity_type="source",
        entity_id=str(source.id),
        summary="Source status changed." if status_changed else "Source updated.",
        metadata=metadata,
    )
    session.commit()
    session.refresh(source)

    return source


def _get_source_or_404(
    session: Session,
    source_id: UUID,
) -> DataSource:
    source = session.get(DataSource, source_id)
    if source is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source not found.",
        )
    return source


def _get_usage_profile_for_source(
    session: Session,
    source_id: UUID,
) -> DataUsageProfile | None:
    statement = select(DataUsageProfile).where(DataUsageProfile.source_id == source_id)
    return session.scalar(statement)


def _get_usage_profile_for_source_or_404(
    session: Session,
    source_id: UUID,
) -> DataUsageProfile:
    profile = _get_usage_profile_for_source(session, source_id)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data usage profile not found.",
        )
    return profile


def _value(value: object) -> str:
    enum_value = getattr(value, "value", None)
    if isinstance(enum_value, str):
        return enum_value
    return str(value)
