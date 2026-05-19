from dataclasses import dataclass, field

from agent_governance_api.models import ActorType

DEVELOPMENT_ACTOR_ID = "dev-placeholder"


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
