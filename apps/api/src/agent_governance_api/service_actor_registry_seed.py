from dataclasses import dataclass
from enum import StrEnum
from itertools import count

from sqlalchemy import select
from sqlalchemy.orm import Session

from agent_governance_api.config import Settings
from agent_governance_api.models import (
    ServiceActor,
    ServiceActorApiKey,
    ServiceActorApiKeyStatus,
    ServiceActorStatus,
)


class SeedAction(StrEnum):
    CREATE = "create"
    EXISTS = "exists"
    DRY_RUN_CREATE = "dry_run_create"


@dataclass(frozen=True)
class SeedResult:
    actor_id: str
    key_id: str
    actor_action: SeedAction
    key_action: SeedAction


def seed_service_actor_registry_from_settings(
    session: Session,
    settings: Settings,
    *,
    dry_run: bool = True,
) -> list[SeedResult]:
    """Seed service actors and hashed API key records from safe config values.

    This imports only `AGCP_SERVICE_ACTOR_API_KEYS` entries that already contain
    `sha256:<digest>` values. Use the scope seed helper to import endpoint
    scopes and fine-grained rules separately.
    """

    results: list[SeedResult] = []
    reserved_key_ids: set[str] = set()

    for index, configured_key in enumerate(settings.service_actor_api_keys, start=1):
        actor = _service_actor_by_actor_id(session, configured_key.actor_id)
        actor_action = SeedAction.EXISTS
        if actor is None:
            actor_action = SeedAction.DRY_RUN_CREATE if dry_run else SeedAction.CREATE
            actor = ServiceActor(
                actor_id=configured_key.actor_id,
                display_name=_display_name_for_actor(configured_key.actor_id),
                status=ServiceActorStatus.ACTIVE,
            )
            if not dry_run:
                session.add(actor)
                session.flush()

        api_key = _api_key_by_hash(session, configured_key.key_hash)
        key_action = SeedAction.EXISTS
        if api_key is None:
            key_action = SeedAction.DRY_RUN_CREATE if dry_run else SeedAction.CREATE
            key_id = _next_imported_key_id(
                session,
                configured_key.actor_id,
                index=index,
                reserved_key_ids=reserved_key_ids,
            )
            reserved_key_ids.add(key_id)
            if not dry_run:
                session.add(
                    ServiceActorApiKey(
                        service_actor=actor,
                        key_id=key_id,
                        key_hash=configured_key.key_hash,
                        hash_algorithm="sha256",
                        status=ServiceActorApiKeyStatus.ACTIVE,
                    )
                )
        else:
            if api_key.service_actor.actor_id != configured_key.actor_id:
                raise ValueError(
                    "Configured service actor API key hash already belongs to "
                    "a different service actor."
                )
            key_id = api_key.key_id

        results.append(
            SeedResult(
                actor_id=configured_key.actor_id,
                key_id=key_id,
                actor_action=actor_action,
                key_action=key_action,
            )
        )

    if not dry_run:
        session.commit()

    return results


def format_seed_results(results: list[SeedResult], *, dry_run: bool) -> str:
    if not results:
        return "No AGCP_SERVICE_ACTOR_API_KEYS entries found. Nothing to seed."

    mode = "DRY RUN" if dry_run else "APPLIED"
    lines = [
        f"{mode}: service actor registry seed results",
        "Use seed_service_actor_registry_scopes.py to seed scopes and rules.",
    ]
    for result in results:
        lines.append(
            " - "
            f"actor_id={result.actor_id} "
            f"actor_action={result.actor_action.value} "
            f"key_id={result.key_id} "
            f"key_action={result.key_action.value}"
        )
    return "\n".join(lines)


def _service_actor_by_actor_id(session: Session, actor_id: str) -> ServiceActor | None:
    return session.scalar(select(ServiceActor).where(ServiceActor.actor_id == actor_id))


def _api_key_by_hash(session: Session, key_hash: str) -> ServiceActorApiKey | None:
    return session.scalar(
        select(ServiceActorApiKey).where(ServiceActorApiKey.key_hash == key_hash)
    )


def _next_imported_key_id(
    session: Session,
    actor_id: str,
    *,
    index: int,
    reserved_key_ids: set[str],
) -> str:
    slug = _actor_id_slug(actor_id)
    base_key_id = f"sak_imported_{slug}_{index:03d}"
    if not _key_id_exists(session, base_key_id) and base_key_id not in reserved_key_ids:
        return base_key_id

    for suffix in count(1):
        key_id = f"{base_key_id}_{suffix:02d}"
        if not _key_id_exists(session, key_id) and key_id not in reserved_key_ids:
            return key_id

    raise RuntimeError("Unable to allocate a service actor API key ID.")


def _key_id_exists(session: Session, key_id: str) -> bool:
    return (
        session.scalar(
            select(ServiceActorApiKey.id).where(ServiceActorApiKey.key_id == key_id)
        )
        is not None
    )


def _actor_id_slug(actor_id: str) -> str:
    stable_id = actor_id.removeprefix("service:").lower()
    slug = "".join(char if char.isalnum() else "_" for char in stable_id).strip("_")
    return (slug or "service_actor")[:64]


def _display_name_for_actor(actor_id: str) -> str:
    stable_id = actor_id.removeprefix("service:")
    return f"Imported service actor {stable_id}"
