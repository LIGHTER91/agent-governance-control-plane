import pytest
from fastapi import HTTPException

from agent_governance_api.auth import (
    DEVELOPMENT_ACTOR_ID,
    get_current_actor,
    has_scope,
    hash_service_actor_api_key,
    require_scope,
    service_actor_from_api_key,
)
from agent_governance_api.config import (
    ServiceActorApiKey,
    ServiceActorScopes,
    Settings,
)
from agent_governance_api.models import ActorType


def test_default_actor_context_is_development_placeholder() -> None:
    actor = get_current_actor()

    assert actor.actor_type is ActorType.DEVELOPMENT
    assert actor.actor_id == DEVELOPMENT_ACTOR_ID
    assert actor.roles == ()


def test_service_actor_context_resolves_valid_api_key() -> None:
    settings = Settings(
        service_actor_api_keys=(
            ServiceActorApiKey(
                actor_id="service:runtime-test",
                key_hash=hash_service_actor_api_key("local-test-service-key"),
            ),
        ),
        service_actor_scopes=(
            ServiceActorScopes(
                actor_id="service:runtime-test",
                scopes=("runtime:decision",),
            ),
        ),
    )

    actor = service_actor_from_api_key("local-test-service-key", settings=settings)

    assert actor is not None
    assert actor.actor_type is ActorType.SERVICE
    assert actor.actor_id == "service:runtime-test"
    assert actor.roles == ("runtime:decision",)
    assert has_scope(actor, "runtime:decision") is True
    assert has_scope(actor, "runtime:resume") is False


def test_service_actor_context_rejects_invalid_api_key() -> None:
    settings = Settings(
        service_actor_api_keys=(
            ServiceActorApiKey(
                actor_id="service:runtime-test",
                key_hash=hash_service_actor_api_key("local-test-service-key"),
            ),
        )
    )

    assert service_actor_from_api_key("wrong-key", settings=settings) is None


def test_service_actor_context_without_configured_scopes_has_no_scopes() -> None:
    settings = Settings(
        service_actor_api_keys=(
            ServiceActorApiKey(
                actor_id="service:runtime-test",
                key_hash=hash_service_actor_api_key("local-test-service-key"),
            ),
        ),
    )

    actor = service_actor_from_api_key("local-test-service-key", settings=settings)

    assert actor is not None
    assert actor.roles == ()
    assert has_scope(actor, "runtime:decision") is False


def test_require_scope_rejects_service_actor_without_scope() -> None:
    settings = Settings(
        service_actor_api_keys=(
            ServiceActorApiKey(
                actor_id="service:runtime-test",
                key_hash=hash_service_actor_api_key("local-test-service-key"),
            ),
        ),
    )
    actor = service_actor_from_api_key("local-test-service-key", settings=settings)
    assert actor is not None

    with pytest.raises(HTTPException) as exc_info:
        require_scope(actor, "runtime:decision")

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Service actor requires scope: runtime:decision."


def test_require_scope_preserves_development_actor_fallback() -> None:
    actor = get_current_actor()

    require_scope(actor, "runtime:decision")
