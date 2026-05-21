from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from agent_governance_api.auth import hash_service_actor_api_key
from agent_governance_api.config import ServiceActorApiKey, Settings
from agent_governance_api.database import Base
from agent_governance_api.models import (
    ServiceActor,
    ServiceActorApiKeyStatus,
    ServiceActorStatus,
)
from agent_governance_api.models import (
    ServiceActorApiKey as ServiceActorApiKeyRecord,
)
from agent_governance_api.service_actor_registry_seed import (
    SeedAction,
    format_seed_results,
    seed_service_actor_registry_from_settings,
)


def test_seed_service_actor_registry_dry_run_writes_no_records() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    try:
        with Session(engine) as session:
            results = seed_service_actor_registry_from_settings(
                session,
                _settings_for_key(raw_key="dry-run-secret"),
                dry_run=True,
            )

            assert results[0].actor_action is SeedAction.DRY_RUN_CREATE
            assert results[0].key_action is SeedAction.DRY_RUN_CREATE
            assert session.scalars(select(ServiceActor)).all() == []
            assert session.scalars(select(ServiceActorApiKeyRecord)).all() == []
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_seed_service_actor_registry_persists_hashed_config_only() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    raw_key = "manual-seed-secret"
    settings = _settings_for_key(raw_key=raw_key)

    try:
        with Session(engine) as session:
            results = seed_service_actor_registry_from_settings(
                session,
                settings,
                dry_run=False,
            )

            [actor] = session.scalars(select(ServiceActor)).all()
            [api_key] = session.scalars(select(ServiceActorApiKeyRecord)).all()
            assert results[0].actor_action is SeedAction.CREATE
            assert results[0].key_action is SeedAction.CREATE
            assert actor.actor_id == "service:seed-test"
            assert actor.status is ServiceActorStatus.ACTIVE
            assert api_key.service_actor_id == actor.id
            assert api_key.key_hash == hash_service_actor_api_key(raw_key)
            assert api_key.status is ServiceActorApiKeyStatus.ACTIVE
            assert raw_key not in str(api_key.__dict__)
            assert raw_key not in format_seed_results(results, dry_run=False)
            assert api_key.key_hash not in format_seed_results(results, dry_run=False)
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_seed_service_actor_registry_is_idempotent_for_existing_records() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    settings = _settings_for_key(raw_key="idempotent-secret")

    try:
        with Session(engine) as session:
            seed_service_actor_registry_from_settings(
                session,
                settings,
                dry_run=False,
            )
            results = seed_service_actor_registry_from_settings(
                session,
                settings,
                dry_run=False,
            )

            assert results[0].actor_action is SeedAction.EXISTS
            assert results[0].key_action is SeedAction.EXISTS
            assert len(session.scalars(select(ServiceActor)).all()) == 1
            assert len(session.scalars(select(ServiceActorApiKeyRecord)).all()) == 1
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


def _settings_for_key(*, raw_key: str) -> Settings:
    return Settings(
        service_actor_api_keys=(
            ServiceActorApiKey(
                actor_id="service:seed-test",
                key_hash=hash_service_actor_api_key(raw_key),
            ),
        )
    )
