import json
from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from agent_governance_api.auth import hash_service_actor_api_key
from agent_governance_api.config import (
    ServiceActorApiKey,
    ServiceActorScopes,
    Settings,
    get_settings,
)
from agent_governance_api.config import (
    ServiceActorScopeRule as ConfigServiceActorScopeRule,
)
from agent_governance_api.database import Base
from agent_governance_api.models import (
    ServiceActor,
    ServiceActorScope,
    ServiceActorStatus,
)
from agent_governance_api.models import (
    ServiceActorApiKey as ServiceActorApiKeyRecord,
)
from agent_governance_api.models import (
    ServiceActorScopeRule as ServiceActorScopeRuleRecord,
)
from agent_governance_api.service_actor_registry_scope_seed import (
    ScopeSeedAction,
    format_scope_seed_results,
    seed_service_actor_registry_scopes_from_settings,
)


@pytest.fixture()
def registry_session() -> Iterator[Session]:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    try:
        with Session(engine) as session:
            yield session
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_seed_service_actor_registry_scopes_dry_run_writes_no_records(
    registry_session: Session,
) -> None:
    add_service_actor(registry_session)
    settings = settings_for_scope_seed(
        scopes=("runtime:decision",),
        rule=ConfigServiceActorScopeRule(
            actor_id="service:scope-seed-test",
            agent_ids=("11111111-1111-4111-8111-111111111111",),
            environments=("development",),
            runtime_modes=("simulation",),
            tool_names=("send_email",),
        ),
    )

    results = seed_service_actor_registry_scopes_from_settings(
        registry_session,
        settings,
        dry_run=True,
    )

    assert results.scopes[0].action is ScopeSeedAction.DRY_RUN_CREATE
    assert results.rules[0].action is ScopeSeedAction.DRY_RUN_CREATE
    assert registry_session.scalars(select(ServiceActorScope)).all() == []
    assert registry_session.scalars(select(ServiceActorScopeRuleRecord)).all() == []


def test_seed_service_actor_registry_scopes_apply_creates_scope_records(
    registry_session: Session,
) -> None:
    actor = add_service_actor(registry_session)
    settings = settings_for_scope_seed(
        scopes=("runtime:decision", "runtime:resume"),
    )

    results = seed_service_actor_registry_scopes_from_settings(
        registry_session,
        settings,
        dry_run=False,
    )

    persisted_scopes = registry_session.scalars(
        select(ServiceActorScope).where(ServiceActorScope.service_actor_id == actor.id)
    ).all()
    assert [result.action for result in results.scopes] == [
        ScopeSeedAction.CREATE,
        ScopeSeedAction.CREATE,
    ]
    assert sorted(scope.scope for scope in persisted_scopes) == [
        "runtime:decision",
        "runtime:resume",
    ]


def test_seed_service_actor_registry_scopes_apply_creates_rule_records(
    registry_session: Session,
) -> None:
    actor = add_service_actor(registry_session)
    settings = settings_for_scope_seed(
        rule=ConfigServiceActorScopeRule(
            actor_id=actor.actor_id,
            agent_ids=("11111111-1111-4111-8111-111111111111",),
            environments=("development",),
            runtime_modes=("simulation",),
            tool_names=("send_email",),
        ),
    )

    results = seed_service_actor_registry_scopes_from_settings(
        registry_session,
        settings,
        dry_run=False,
    )

    [rule] = registry_session.scalars(select(ServiceActorScopeRuleRecord)).all()
    assert results.rules[0].action is ScopeSeedAction.CREATE
    assert rule.service_actor_id == actor.id
    assert rule.agent_ids == ["11111111-1111-4111-8111-111111111111"]
    assert rule.environments == ["development"]
    assert rule.runtime_modes == ["simulation"]
    assert rule.tool_names == ["send_email"]


def test_seed_service_actor_registry_scopes_avoids_duplicate_scopes(
    registry_session: Session,
) -> None:
    actor = add_service_actor(registry_session)
    registry_session.add(
        ServiceActorScope(service_actor=actor, scope="runtime:decision")
    )
    registry_session.commit()
    settings = settings_for_scope_seed(
        scopes=("runtime:decision", "telemetry:write"),
    )

    results = seed_service_actor_registry_scopes_from_settings(
        registry_session,
        settings,
        dry_run=False,
    )

    persisted_scopes = registry_session.scalars(select(ServiceActorScope)).all()
    assert [result.action for result in results.scopes] == [
        ScopeSeedAction.EXISTS,
        ScopeSeedAction.CREATE,
    ]
    assert sorted(scope.scope for scope in persisted_scopes) == [
        "runtime:decision",
        "telemetry:write",
    ]


def test_seed_service_actor_registry_scopes_reports_missing_service_actors(
    registry_session: Session,
) -> None:
    settings = settings_for_scope_seed(
        actor_id="service:missing-scope-seed-test",
        scopes=("runtime:decision",),
        rule=ConfigServiceActorScopeRule(
            actor_id="service:missing-scope-seed-test",
            agent_ids=("*",),
        ),
    )

    results = seed_service_actor_registry_scopes_from_settings(
        registry_session,
        settings,
        dry_run=True,
    )
    output = format_scope_seed_results(results, dry_run=True)

    assert results.scopes[0].action is ScopeSeedAction.MISSING_ACTOR
    assert results.rules[0].action is ScopeSeedAction.MISSING_ACTOR
    assert "service:missing-scope-seed-test" in output
    assert "missing_actor" in output
    assert registry_session.scalars(select(ServiceActorScope)).all() == []
    assert registry_session.scalars(select(ServiceActorScopeRuleRecord)).all() == []


def test_seed_service_actor_registry_scopes_rejects_unsupported_rule_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv(
        "AGCP_SERVICE_ACTOR_SCOPE_RULES",
        json.dumps({"service:scope-seed-test": {"unsupported": ["value"]}}),
    )

    try:
        with pytest.raises(ValueError, match="unsupported fields"):
            get_settings()
    finally:
        get_settings.cache_clear()


def test_seed_service_actor_registry_scopes_preserves_existing_records(
    registry_session: Session,
) -> None:
    actor = add_service_actor(registry_session)
    registry_session.add(
        ServiceActorScopeRuleRecord(
            service_actor=actor,
            agent_ids=["existing-agent"],
            environments=["development"],
            runtime_modes=["simulation"],
            tool_names=["send_email"],
        )
    )
    registry_session.commit()
    settings = settings_for_scope_seed(
        rule=ConfigServiceActorScopeRule(
            actor_id=actor.actor_id,
            agent_ids=("new-agent",),
            environments=("staging",),
            runtime_modes=("simulation",),
            tool_names=("send_email",),
        ),
    )

    results = seed_service_actor_registry_scopes_from_settings(
        registry_session,
        settings,
        dry_run=False,
    )

    persisted_rules = registry_session.scalars(
        select(ServiceActorScopeRuleRecord).where(
            ServiceActorScopeRuleRecord.service_actor_id == actor.id
        )
    ).all()
    assert results.rules[0].action is ScopeSeedAction.CREATE
    assert sorted(rule.agent_ids[0] for rule in persisted_rules) == [
        "existing-agent",
        "new-agent",
    ]


def test_seed_service_actor_registry_scopes_does_not_log_or_persist_raw_api_keys(
    registry_session: Session,
) -> None:
    add_service_actor(registry_session)
    raw_key = "scope-seed-raw-api-key"
    key_hash = hash_service_actor_api_key(raw_key)
    settings = Settings(
        service_actor_api_keys=(
            ServiceActorApiKey(
                actor_id="service:scope-seed-test",
                key_hash=key_hash,
            ),
        ),
        service_actor_scopes=(
            ServiceActorScopes(
                actor_id="service:scope-seed-test",
                scopes=("runtime:decision",),
            ),
        ),
    )

    results = seed_service_actor_registry_scopes_from_settings(
        registry_session,
        settings,
        dry_run=False,
    )
    output = format_scope_seed_results(results, dry_run=False)

    assert raw_key not in output
    assert key_hash not in output
    assert registry_session.scalars(select(ServiceActorApiKeyRecord)).all() == []
    [scope] = registry_session.scalars(select(ServiceActorScope)).all()
    assert raw_key not in str(scope.__dict__)
    assert key_hash not in str(scope.__dict__)


def add_service_actor(
    session: Session,
    *,
    actor_id: str = "service:scope-seed-test",
) -> ServiceActor:
    actor = ServiceActor(
        actor_id=actor_id,
        display_name="Scope seed test service actor",
        status=ServiceActorStatus.ACTIVE,
    )
    session.add(actor)
    session.commit()
    return actor


def settings_for_scope_seed(
    *,
    actor_id: str = "service:scope-seed-test",
    scopes: tuple[str, ...] = (),
    rule: ConfigServiceActorScopeRule | None = None,
) -> Settings:
    return Settings(
        service_actor_scopes=(
            (ServiceActorScopes(actor_id=actor_id, scopes=scopes),) if scopes else ()
        ),
        service_actor_scope_rules=(rule,) if rule else (),
    )
