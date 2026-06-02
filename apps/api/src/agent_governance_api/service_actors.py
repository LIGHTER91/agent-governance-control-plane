from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from agent_governance_api.config import Settings, get_settings
from agent_governance_api.database import get_db_session
from agent_governance_api.models import (
    ServiceActor,
    ServiceActorApiKey,
    ServiceActorScope,
    ServiceActorScopeRule,
)
from agent_governance_api.schemas import (
    ServiceActorApiKeyRead,
    ServiceActorRead,
    ServiceActorScopeRead,
    ServiceActorScopeRuleRead,
)

router = APIRouter(prefix="/service-actors", tags=["service actors"])


@router.get("", response_model=list[ServiceActorRead])
def list_service_actors(
    session: Session = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> list[ServiceActor]:
    _require_registry_enabled(settings)
    statement = select(ServiceActor).order_by(ServiceActor.created_at, ServiceActor.id)
    return list(session.scalars(statement).all())


@router.get("/{service_actor_id}", response_model=ServiceActorRead)
def get_service_actor(
    service_actor_id: UUID,
    session: Session = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> ServiceActor:
    _require_registry_enabled(settings)
    return _get_service_actor_or_404(session, service_actor_id)


@router.get(
    "/{service_actor_id}/api-keys",
    response_model=list[ServiceActorApiKeyRead],
)
def list_service_actor_api_keys(
    service_actor_id: UUID,
    session: Session = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> list[ServiceActorApiKey]:
    _require_registry_enabled(settings)
    _get_service_actor_or_404(session, service_actor_id)
    statement = (
        select(ServiceActorApiKey)
        .where(ServiceActorApiKey.service_actor_id == service_actor_id)
        .order_by(ServiceActorApiKey.created_at, ServiceActorApiKey.key_id)
    )
    return list(session.scalars(statement).all())


@router.get(
    "/{service_actor_id}/scopes",
    response_model=list[ServiceActorScopeRead],
)
def list_service_actor_scopes(
    service_actor_id: UUID,
    session: Session = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> list[ServiceActorScope]:
    _require_registry_enabled(settings)
    _get_service_actor_or_404(session, service_actor_id)
    statement = (
        select(ServiceActorScope)
        .where(ServiceActorScope.service_actor_id == service_actor_id)
        .order_by(ServiceActorScope.scope)
    )
    return list(session.scalars(statement).all())


@router.get(
    "/{service_actor_id}/scope-rules",
    response_model=list[ServiceActorScopeRuleRead],
)
def list_service_actor_scope_rules(
    service_actor_id: UUID,
    session: Session = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> list[ServiceActorScopeRule]:
    _require_registry_enabled(settings)
    _get_service_actor_or_404(session, service_actor_id)
    statement = (
        select(ServiceActorScopeRule)
        .where(ServiceActorScopeRule.service_actor_id == service_actor_id)
        .order_by(ServiceActorScopeRule.created_at, ServiceActorScopeRule.id)
    )
    return list(session.scalars(statement).all())


def _require_registry_enabled(settings: Settings) -> None:
    if settings.service_actor_registry_enabled:
        return

    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=(
            "Service actor registry admin is disabled. Config-based service "
            "actor auth remains the default."
        ),
    )


def _get_service_actor_or_404(
    session: Session,
    service_actor_id: UUID,
) -> ServiceActor:
    service_actor = session.get(ServiceActor, service_actor_id)
    if service_actor is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service actor not found.",
        )
    return service_actor
