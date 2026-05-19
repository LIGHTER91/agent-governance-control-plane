from dataclasses import dataclass, field
from hashlib import sha256
from hmac import compare_digest
from typing import Annotated

from fastapi import Header, HTTPException, status

from agent_governance_api.config import (
    SERVICE_ACTOR_API_KEY_HASH_PREFIX,
    SERVICE_ACTOR_FINE_GRAINED_WILDCARD,
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

    Missing API keys preserve the V0 local development actor unless
    AGCP_REQUIRE_SERVICE_AUTH=true. Invalid API keys are rejected before
    endpoint code creates governance records.
    """

    settings = get_settings()
    if api_key is None:
        if settings.require_service_auth:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="AGCP service actor API key is required.",
            )
        return get_current_actor()

    actor = service_actor_from_api_key(api_key, settings=settings)
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


def require_service_actor_fine_grained_scope(
    actor: ActorContext,
    *,
    agent_id: object,
    environment: object,
    runtime_mode: object | None = None,
    tool_name: str | None = None,
    settings: Settings | None = None,
) -> None:
    """Narrow service actor endpoint scopes by Agent and request context.

    Local development actors are intentionally ignored here so the V0
    development fallback remains unchanged.
    """

    if actor.actor_type is not ActorType.SERVICE:
        return

    settings = settings or get_settings()
    actor_rules = tuple(
        rule
        for rule in settings.service_actor_scope_rules
        if rule.actor_id == actor.actor_id
    )
    if not actor_rules:
        if settings.require_service_auth or settings.service_actor_scope_rules:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Service actor requires a fine-grained scope rule.",
            )
        return

    agent_id_value = str(agent_id)
    environment_value = _scope_value(environment)
    candidate_rules = [
        rule for rule in actor_rules if _values_allow(rule.agent_ids, agent_id_value)
    ]
    if not candidate_rules:
        raise _fine_grained_scope_denied("agent")

    candidate_rules = [
        rule
        for rule in candidate_rules
        if _values_allow(rule.environments, environment_value)
    ]
    if not candidate_rules:
        raise _fine_grained_scope_denied("environment")

    if runtime_mode is not None:
        runtime_mode_value = _scope_value(runtime_mode)
        candidate_rules = [
            rule
            for rule in candidate_rules
            if _values_allow(rule.runtime_modes, runtime_mode_value)
        ]
        if not candidate_rules:
            raise _fine_grained_scope_denied("runtime mode")

    if tool_name is not None:
        candidate_rules = [
            rule
            for rule in candidate_rules
            if _values_allow(rule.tool_names, tool_name)
        ]
        if not candidate_rules:
            raise _fine_grained_scope_denied("tool name")


def _service_actor_scopes(actor_id: str, settings: Settings) -> tuple[str, ...]:
    for configured_scopes in settings.service_actor_scopes:
        if configured_scopes.actor_id == actor_id:
            return configured_scopes.scopes
    return ()


def _values_allow(values: tuple[str, ...], requested_value: str) -> bool:
    return SERVICE_ACTOR_FINE_GRAINED_WILDCARD in values or requested_value in values


def _scope_value(value: object) -> str:
    enum_value = getattr(value, "value", None)
    if isinstance(enum_value, str):
        return enum_value
    return str(value)


def _fine_grained_scope_denied(scope_name: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=f"Service actor is not permitted for this {scope_name}.",
    )
