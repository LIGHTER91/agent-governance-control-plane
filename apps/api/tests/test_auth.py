from agent_governance_api.auth import (
    DEVELOPMENT_ACTOR_ID,
    get_current_actor,
    hash_service_actor_api_key,
    service_actor_from_api_key,
)
from agent_governance_api.config import ServiceActorApiKey, Settings
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
        )
    )

    actor = service_actor_from_api_key("local-test-service-key", settings=settings)

    assert actor is not None
    assert actor.actor_type is ActorType.SERVICE
    assert actor.actor_id == "service:runtime-test"
    assert actor.roles == ()


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
