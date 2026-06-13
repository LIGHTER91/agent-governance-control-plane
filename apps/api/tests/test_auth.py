from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from agent_governance_api.auth import (
    DEVELOPMENT_ACTOR_ID,
    ActorContext,
    get_current_actor,
    get_current_integration_actor,
    has_role,
    has_scope,
    hash_service_actor_api_key,
    require_role,
    require_scope,
    require_service_actor_fine_grained_scope,
    service_actor_from_api_key,
)
from agent_governance_api.config import (
    ServiceActorApiKey,
    ServiceActorScopeRule,
    ServiceActorScopes,
    Settings,
    get_settings,
)
from agent_governance_api.database import Base
from agent_governance_api.models import (
    ActorType,
    Environment,
    ServiceActor,
    ServiceActorApiKeyStatus,
    ServiceActorScope,
    ServiceActorStatus,
)
from agent_governance_api.models import (
    ServiceActorApiKey as ServiceActorApiKeyRecord,
)
from agent_governance_api.models import (
    ServiceActorScopeRule as ServiceActorScopeRuleRecord,
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


def test_default_actor_context_is_development_placeholder(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    get_settings.cache_clear()
    monkeypatch.delenv("AGCP_DEV_ACTOR_ID", raising=False)
    monkeypatch.delenv("AGCP_DEV_ACTOR_ROLES", raising=False)
    monkeypatch.delenv("AGCP_DEV_ACTOR_DISPLAY_NAME", raising=False)

    try:
        actor = get_current_actor()
    finally:
        get_settings.cache_clear()

    assert actor.actor_type is ActorType.DEVELOPMENT
    assert actor.actor_id == DEVELOPMENT_ACTOR_ID
    assert actor.roles == ()
    assert actor.display_name is None


def test_configured_dev_actor_context_uses_safe_local_roles(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("AGCP_DEV_ACTOR_ID", "local-admin")
    monkeypatch.setenv("AGCP_DEV_ACTOR_ROLES", "platform_admin,reviewer,auditor")
    monkeypatch.setenv("AGCP_DEV_ACTOR_DISPLAY_NAME", "Local Admin")

    try:
        actor = get_current_actor()
    finally:
        get_settings.cache_clear()

    assert actor.actor_type is ActorType.DEVELOPMENT
    assert actor.actor_id == "local-admin"
    assert actor.roles == ("platform_admin", "reviewer", "auditor")
    assert actor.display_name == "Local Admin"


def test_integration_actor_preserves_missing_key_development_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    get_settings.cache_clear()
    monkeypatch.delenv("AGCP_REQUIRE_SERVICE_AUTH", raising=False)

    try:
        actor = get_current_integration_actor()

        assert actor.actor_type is ActorType.DEVELOPMENT
        assert actor.actor_id == DEVELOPMENT_ACTOR_ID
    finally:
        get_settings.cache_clear()


def test_integration_actor_requires_api_key_when_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("AGCP_REQUIRE_SERVICE_AUTH", "true")

    try:
        with pytest.raises(HTTPException) as exc_info:
            get_current_integration_actor()

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "AGCP service actor API key is required."
    finally:
        get_settings.cache_clear()


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


def test_has_role_reads_actor_context_roles() -> None:
    actor = ActorContext(
        actor_type=ActorType.USER,
        actor_id="user:reviewer-1",
        roles=("reviewer",),
    )

    assert has_role(actor, "reviewer") is True
    assert has_role(actor, "platform_admin") is False


def test_require_role_rejects_actor_without_allowed_role() -> None:
    actor = ActorContext(
        actor_type=ActorType.USER,
        actor_id="user:viewer-1",
        roles=("viewer",),
    )

    with pytest.raises(HTTPException) as exc_info:
        require_role(actor, ("reviewer", "platform_admin"))

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == (
        "Actor requires one of these roles: reviewer, platform_admin."
    )


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


def test_config_service_actor_auth_is_unchanged_when_registry_disabled(
    registry_session: Session,
) -> None:
    add_registry_service_actor_key(registry_session, raw_key="registry-only-key")
    settings = Settings(
        service_actor_registry_enabled=False,
        service_actor_api_keys=(
            ServiceActorApiKey(
                actor_id="service:config-test",
                key_hash=hash_service_actor_api_key("config-key"),
            ),
        ),
        service_actor_scopes=(
            ServiceActorScopes(
                actor_id="service:config-test",
                scopes=("runtime:decision",),
            ),
        ),
    )

    actor = service_actor_from_api_key(
        "config-key",
        settings=settings,
        session=registry_session,
    )

    assert actor is not None
    assert actor.actor_type is ActorType.SERVICE
    assert actor.actor_id == "service:config-test"
    assert actor.roles == ("runtime:decision",)
    assert (
        service_actor_from_api_key(
            "registry-only-key",
            settings=settings,
            session=registry_session,
        )
        is None
    )


def test_registry_active_key_authenticates_when_enabled(
    registry_session: Session,
) -> None:
    add_registry_service_actor_key(
        registry_session,
        raw_key="registry-active-key",
        scopes=("runtime:decision",),
    )
    settings = Settings(service_actor_registry_enabled=True)

    actor = service_actor_from_api_key(
        "registry-active-key",
        settings=settings,
        session=registry_session,
    )

    assert actor is not None
    assert actor.actor_type is ActorType.SERVICE
    assert actor.actor_id == "service:registry-test"
    assert actor.roles == ("runtime:decision",)


def test_registry_retiring_non_expired_key_authenticates(
    registry_session: Session,
) -> None:
    now = datetime.now(UTC)
    add_registry_service_actor_key(
        registry_session,
        raw_key="registry-retiring-key",
        key_status=ServiceActorApiKeyStatus.RETIRING,
        grace_expires_at=now + timedelta(hours=1),
        scopes=("runtime:decision",),
    )
    settings = Settings(service_actor_registry_enabled=True)

    actor = service_actor_from_api_key(
        "registry-retiring-key",
        settings=settings,
        session=registry_session,
    )

    assert actor is not None
    assert actor.actor_id == "service:registry-test"


@pytest.mark.parametrize(
    ("key_status", "expires_at", "grace_expires_at"),
    [
        (ServiceActorApiKeyStatus.REVOKED, None, None),
        (ServiceActorApiKeyStatus.EXPIRED, None, None),
        (ServiceActorApiKeyStatus.ACTIVE, datetime.now(UTC) - timedelta(hours=1), None),
        (
            ServiceActorApiKeyStatus.RETIRING,
            None,
            datetime.now(UTC) - timedelta(hours=1),
        ),
    ],
)
def test_registry_invalid_key_lifecycle_is_rejected(
    registry_session: Session,
    key_status: ServiceActorApiKeyStatus,
    expires_at: datetime | None,
    grace_expires_at: datetime | None,
) -> None:
    add_registry_service_actor_key(
        registry_session,
        raw_key="registry-invalid-key",
        key_status=key_status,
        expires_at=expires_at,
        grace_expires_at=grace_expires_at,
    )
    settings = Settings(service_actor_registry_enabled=True)

    assert (
        service_actor_from_api_key(
            "registry-invalid-key",
            settings=settings,
            session=registry_session,
        )
        is None
    )


def test_registry_disabled_service_actor_is_rejected(
    registry_session: Session,
) -> None:
    add_registry_service_actor_key(
        registry_session,
        raw_key="registry-disabled-actor-key",
        actor_status=ServiceActorStatus.DISABLED,
    )
    settings = Settings(service_actor_registry_enabled=True)

    assert (
        service_actor_from_api_key(
            "registry-disabled-actor-key",
            settings=settings,
            session=registry_session,
        )
        is None
    )


def test_registry_actor_without_configured_scope_is_rejected_by_scope_check(
    registry_session: Session,
) -> None:
    add_registry_service_actor_key(
        registry_session,
        raw_key="registry-no-scope-key",
        scopes=(),
    )
    settings = Settings(service_actor_registry_enabled=True)

    actor = service_actor_from_api_key(
        "registry-no-scope-key",
        settings=settings,
        session=registry_session,
    )

    assert actor is not None
    assert actor.roles == ()
    with pytest.raises(HTTPException) as exc_info:
        require_scope(actor, "runtime:decision")

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Service actor requires scope: runtime:decision."


def test_registry_actor_ignores_config_scopes_when_registry_enabled(
    registry_session: Session,
) -> None:
    add_registry_service_actor_key(
        registry_session,
        raw_key="registry-scope-source-key",
        scopes=("telemetry:write",),
    )
    settings = Settings(
        service_actor_registry_enabled=True,
        service_actor_scopes=(
            ServiceActorScopes(
                actor_id="service:registry-test",
                scopes=("runtime:decision",),
            ),
        ),
    )

    actor = service_actor_from_api_key(
        "registry-scope-source-key",
        settings=settings,
        session=registry_session,
    )

    assert actor is not None
    assert actor.roles == ("telemetry:write",)
    assert has_scope(actor, "telemetry:write") is True
    assert has_scope(actor, "runtime:decision") is False


def test_registry_fine_grained_scope_allows_matching_rule(
    registry_session: Session,
) -> None:
    add_registry_service_actor_key(
        registry_session,
        raw_key="registry-rule-key",
        scopes=("runtime:decision",),
        scope_rules=(
            {
                "agent_ids": ["11111111-1111-4111-8111-111111111111"],
                "environments": ["development"],
                "runtime_modes": ["simulation"],
                "tool_names": ["send_email"],
            },
        ),
    )
    settings = Settings(service_actor_registry_enabled=True, require_service_auth=True)
    actor = service_actor_from_api_key(
        "registry-rule-key",
        settings=settings,
        session=registry_session,
    )
    assert actor is not None

    require_service_actor_fine_grained_scope(
        actor,
        agent_id="11111111-1111-4111-8111-111111111111",
        environment=Environment.DEVELOPMENT,
        runtime_mode="simulation",
        tool_name="send_email",
        settings=settings,
        session=registry_session,
    )


def test_registry_fine_grained_scope_rejects_missing_rule(
    registry_session: Session,
) -> None:
    add_registry_service_actor_key(
        registry_session,
        raw_key="registry-missing-rule-key",
        scopes=("runtime:decision",),
        scope_rules=(),
    )
    settings = Settings(service_actor_registry_enabled=True, require_service_auth=True)
    actor = service_actor_from_api_key(
        "registry-missing-rule-key",
        settings=settings,
        session=registry_session,
    )
    assert actor is not None

    with pytest.raises(HTTPException) as exc_info:
        require_service_actor_fine_grained_scope(
            actor,
            agent_id="11111111-1111-4111-8111-111111111111",
            environment=Environment.DEVELOPMENT,
            runtime_mode="simulation",
            tool_name="send_email",
            settings=settings,
            session=registry_session,
        )

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Service actor requires a fine-grained scope rule."


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


def test_fine_grained_scope_allows_matching_service_actor_context() -> None:
    actor = service_actor_for_test()
    settings = Settings(
        service_actor_scope_rules=(
            ServiceActorScopeRule(
                actor_id="service:runtime-test",
                agent_ids=("11111111-1111-4111-8111-111111111111",),
                environments=("development",),
                runtime_modes=("simulation",),
                tool_names=("send_email",),
            ),
        )
    )

    require_service_actor_fine_grained_scope(
        actor,
        agent_id="11111111-1111-4111-8111-111111111111",
        environment=Environment.DEVELOPMENT,
        runtime_mode="simulation",
        tool_name="send_email",
        settings=settings,
    )


def test_fine_grained_scope_denies_missing_rule_in_strict_mode() -> None:
    actor = service_actor_for_test()
    settings = Settings(require_service_auth=True)

    with pytest.raises(HTTPException) as exc_info:
        require_service_actor_fine_grained_scope(
            actor,
            agent_id="11111111-1111-4111-8111-111111111111",
            environment=Environment.DEVELOPMENT,
            runtime_mode="simulation",
            tool_name="send_email",
            settings=settings,
        )

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Service actor requires a fine-grained scope rule."


def test_fine_grained_scope_preserves_development_actor_fallback() -> None:
    actor = get_current_actor()

    require_service_actor_fine_grained_scope(
        actor,
        agent_id="11111111-1111-4111-8111-111111111111",
        environment=Environment.PRODUCTION,
        runtime_mode="enforcement",
        tool_name="send_email",
        settings=Settings(require_service_auth=True),
    )


def service_actor_for_test():
    actor = service_actor_from_api_key(
        "local-test-service-key",
        settings=Settings(
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
        ),
    )
    assert actor is not None
    return actor


def add_registry_service_actor_key(
    session: Session,
    *,
    raw_key: str,
    actor_id: str = "service:registry-test",
    actor_status: ServiceActorStatus = ServiceActorStatus.ACTIVE,
    key_status: ServiceActorApiKeyStatus = ServiceActorApiKeyStatus.ACTIVE,
    expires_at: datetime | None = None,
    grace_expires_at: datetime | None = None,
    scopes: tuple[str, ...] = (),
    scope_rules: tuple[dict[str, object], ...] = (),
) -> None:
    actor = ServiceActor(
        actor_id=actor_id,
        display_name="Registry test service",
        status=actor_status,
    )
    api_key = ServiceActorApiKeyRecord(
        service_actor=actor,
        key_id=f"sak_{actor_id.removeprefix('service:').replace('-', '_')}",
        key_hash=hash_service_actor_api_key(raw_key),
        status=key_status,
        expires_at=expires_at,
        grace_expires_at=grace_expires_at,
    )
    session.add(actor)
    session.add(api_key)
    for scope in scopes:
        session.add(
            ServiceActorScope(
                service_actor=actor,
                scope=scope,
            )
        )
    for rule in scope_rules:
        session.add(
            ServiceActorScopeRuleRecord(
                service_actor=actor,
                agent_ids=rule.get("agent_ids", []),
                environments=rule.get("environments", []),
                runtime_modes=rule.get("runtime_modes", []),
                tool_names=rule.get("tool_names", []),
            )
        )
    session.commit()
