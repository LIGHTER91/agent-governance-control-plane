from datetime import UTC, datetime
from hmac import compare_digest

from sqlalchemy import select
from sqlalchemy.orm import Session

from agent_governance_api.config import Settings, get_settings
from agent_governance_api.models import (
    ServiceActor,
    ServiceActorApiKey,
    ServiceActorApiKeyStatus,
    ServiceActorStatus,
)

AUTHENTICATABLE_SERVICE_ACTOR_API_KEY_STATUSES = frozenset(
    {
        ServiceActorApiKeyStatus.ACTIVE,
        ServiceActorApiKeyStatus.RETIRING,
    }
)


def is_service_actor_registry_enabled(settings: Settings | None = None) -> bool:
    settings = settings or get_settings()
    return settings.service_actor_registry_enabled


def get_service_actor_by_actor_id(
    session: Session,
    actor_id: str,
    *,
    settings: Settings | None = None,
) -> ServiceActor | None:
    if not is_service_actor_registry_enabled(settings):
        return None

    return session.scalar(
        select(ServiceActor).where(ServiceActor.actor_id == actor_id),
    )


def get_service_actor_api_key_by_key_id(
    session: Session,
    key_id: str,
    *,
    settings: Settings | None = None,
) -> ServiceActorApiKey | None:
    if not is_service_actor_registry_enabled(settings):
        return None

    return session.scalar(
        select(ServiceActorApiKey).where(ServiceActorApiKey.key_id == key_id),
    )


def get_service_actor_api_key_by_key_hash(
    session: Session,
    key_hash: str,
    *,
    settings: Settings | None = None,
) -> ServiceActorApiKey | None:
    if not is_service_actor_registry_enabled(settings):
        return None

    return session.scalar(
        select(ServiceActorApiKey).where(ServiceActorApiKey.key_hash == key_hash),
    )


def get_authenticatable_service_actor_api_key_by_hash(
    session: Session,
    key_hash: str,
    *,
    settings: Settings | None = None,
    now: datetime | None = None,
) -> ServiceActorApiKey | None:
    api_key = get_service_actor_api_key_by_key_hash(
        session,
        key_hash,
        settings=settings,
    )
    if api_key is None:
        return None
    if not compare_digest(api_key.key_hash, key_hash):
        return None
    if not is_service_actor_api_key_authenticatable(api_key, now=now):
        return None

    return api_key


def is_service_actor_api_key_authenticatable(
    api_key: ServiceActorApiKey,
    *,
    now: datetime | None = None,
) -> bool:
    service_actor = api_key.service_actor
    if service_actor is None or service_actor.status is not ServiceActorStatus.ACTIVE:
        return False
    if api_key.status not in AUTHENTICATABLE_SERVICE_ACTOR_API_KEY_STATUSES:
        return False

    now = now or datetime.now(UTC)
    if _is_expired(api_key.expires_at, now=now):
        return False
    if api_key.status is ServiceActorApiKeyStatus.RETIRING and _is_expired(
        api_key.grace_expires_at, now=now
    ):
        return False

    return True


def _is_expired(expires_at: datetime | None, *, now: datetime) -> bool:
    if expires_at is None:
        return False
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if now.tzinfo is None:
        now = now.replace(tzinfo=UTC)
    return expires_at <= now
