from agent_governance_api.auth import DEVELOPMENT_ACTOR_ID, get_current_actor
from agent_governance_api.models import ActorType


def test_default_actor_context_is_development_placeholder() -> None:
    actor = get_current_actor()

    assert actor.actor_type is ActorType.DEVELOPMENT
    assert actor.actor_id == DEVELOPMENT_ACTOR_ID
    assert actor.roles == ()
