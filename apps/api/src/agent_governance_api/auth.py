from dataclasses import dataclass, field
from hashlib import sha256
from hmac import compare_digest
from typing import Annotated

from fastapi import Header, HTTPException, status

from agent_governance_api.config import (
    SERVICE_ACTOR_API_KEY_HASH_PREFIX,
    Settings,
    get_settings,
)
from agent_governance_api.models import ActorType

DEVELOPMENT_ACTOR_ID = "dev-placeholder"
SERVICE_ACTOR_API_KEY_HEADER = "X-AGCP-API-Key"
SCOPE_TELEMETRY_WRITE = "telemetry:write"
SCOPE_RUNTIME_DECISION = "runtime:decision"
SCOPE_RUNTIME_RESUME = "runtime:resume"


@dataclass(frozen=True)
class ActorContext:
    """Request-scoped actor placeholder for local development.

    This is not authentication or RBAC. V0 returns the development placeholder
    so call sites can stop hardcoding actor fields before real auth exists.
    """

    actor_type: ActorType
    actor_id: str
    roles: tuple[str, ...] = field(default_factory=tuple)


def get_current_actor() -> ActorContext:
    """Return the local development actor until real auth is implemented."""

    return ActorContext(
        actor_type=ActorType.DEVELOPMENT,
        actor_id=DEVELOPMENT_ACTOR_ID,
    )


def get_current_integration_actor(
    api_key: Annotated[
        str | None,
        Header(alias=SERVICE_ACTOR_API_KEY_HEADER),
    ] = None,
) -> ActorContext:
    """Resolve optional service API key auth for runtime integrations.

    Missing API keys intentionally preserve the V0 local development actor.
    Invalid API keys are rejected before endpoint code creates governance records.
    """

    if api_key is None:
        return get_current_actor()

    actor = service_actor_from_api_key(api_key, settings=get_settings())
    if actor is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid AGCP service actor API key.",
        )

    return actor


def service_actor_from_api_key(
    api_key: str,
    *,
    settings: Settings,
) -> ActorContext | None:
    if not api_key.strip():
        return None

    candidate_hash = hash_service_actor_api_key(api_key)
    for configured_key in settings.service_actor_api_keys:
        if compare_digest(candidate_hash, configured_key.key_hash):
            return ActorContext(
                actor_type=ActorType.SERVICE,
                actor_id=configured_key.actor_id,
                roles=_service_actor_scopes(configured_key.actor_id, settings),
            )

    return None


def hash_service_actor_api_key(api_key: str) -> str:
    digest = sha256(api_key.encode()).hexdigest()
    return f"{SERVICE_ACTOR_API_KEY_HASH_PREFIX}{digest}"


def has_scope(actor: ActorContext, scope: str) -> bool:
    if actor.actor_type is not ActorType.SERVICE:
        return True
    return scope in actor.roles


def require_scope(actor: ActorContext, scope: str) -> None:
    """Require a scope for service actors while preserving local dev fallback."""

    if has_scope(actor, scope):
        return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=f"Service actor requires scope: {scope}.",
    )


def _service_actor_scopes(actor_id: str, settings: Settings) -> tuple[str, ...]:
    for configured_scopes in settings.service_actor_scopes:
        if configured_scopes.actor_id == actor_id:
            return configured_scopes.scopes
    return ()
