from collections.abc import Callable, Iterator
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from agent_governance_api.auth import (
    hash_service_actor_api_key,
    service_actor_from_api_key,
)
from agent_governance_api.config import (
    ServiceActorApiKey as ConfigServiceActorApiKey,
)
from agent_governance_api.config import Settings, get_settings
from agent_governance_api.database import Base, get_db_session
from agent_governance_api.main import app
from agent_governance_api.models import (
    ActorType,
    ServiceActor,
    ServiceActorApiKey,
    ServiceActorApiKeyStatus,
    ServiceActorScope,
    ServiceActorScopeRule,
    ServiceActorStatus,
)

SessionFactory = Callable[[], Session]


def test_list_service_actors_requires_registry_feature_flag(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, _ = api_client
    app.dependency_overrides[get_settings] = lambda: Settings(
        service_actor_registry_enabled=False
    )

    response = client.get("/service-actors")

    assert response.status_code == 503
    assert response.json()["detail"] == (
        "Service actor registry admin is disabled. Config-based service actor "
        "auth remains the default."
    )


def test_list_and_get_service_actors_when_registry_enabled(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    with session_factory() as session:
        service_actor = seed_service_actor_registry(session)

    list_response = client.get("/service-actors")
    get_response = client.get(f"/service-actors/{service_actor.id}")

    assert list_response.status_code == 200
    assert get_response.status_code == 200
    assert [actor["id"] for actor in list_response.json()] == [str(service_actor.id)]
    body = get_response.json()
    assert body["id"] == str(service_actor.id)
    assert body["actor_id"] == "service:admin-api-test"
    assert body["display_name"] == "Admin API test service"
    assert body["description"] == "Used by registry admin API tests."
    assert body["status"] == "active"
    assert body["created_at"]
    assert body["updated_at"]
    assert body["disabled_at"] is None


def test_list_service_actor_key_metadata_does_not_expose_secret_material(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    raw_key = "admin-read-secret"
    with session_factory() as session:
        service_actor = seed_service_actor_registry(session, raw_key=raw_key)

    response = client.get(f"/service-actors/{service_actor.id}/api-keys")

    assert response.status_code == 200
    [api_key] = response.json()
    assert set(api_key) == {
        "key_id",
        "status",
        "created_at",
        "expires_at",
        "revoked_at",
        "last_used_at",
    }
    assert api_key["key_id"] == "sak_admin_api_test"
    assert api_key["status"] == "active"
    assert api_key["expires_at"] is not None
    assert api_key["last_used_at"] is not None
    response_text = response.text
    assert raw_key not in response_text
    assert "sha256:" not in response_text
    assert "key_hash" not in response_text
    assert "hash_algorithm" not in response_text
    assert "last_used_endpoint" not in response_text


def test_list_service_actor_scopes_and_scope_rules(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    with session_factory() as session:
        service_actor = seed_service_actor_registry(session)

    scopes_response = client.get(f"/service-actors/{service_actor.id}/scopes")
    rules_response = client.get(f"/service-actors/{service_actor.id}/scope-rules")

    assert scopes_response.status_code == 200
    assert [scope["scope"] for scope in scopes_response.json()] == [
        "runtime:decision",
        "telemetry:write",
    ]
    assert rules_response.status_code == 200
    [rule] = rules_response.json()
    assert rule["service_actor_id"] == str(service_actor.id)
    assert rule["agent_ids"] == ["11111111-1111-4111-8111-111111111111"]
    assert rule["environments"] == ["production"]
    assert rule["runtime_modes"] == ["enforcement"]
    assert rule["tool_names"] == ["send_email"]


def test_service_actor_nested_reads_return_404_for_unknown_actor(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, _ = api_client
    missing_id = "00000000-0000-0000-0000-000000000001"

    actor_response = client.get(f"/service-actors/{missing_id}")
    keys_response = client.get(f"/service-actors/{missing_id}/api-keys")
    scopes_response = client.get(f"/service-actors/{missing_id}/scopes")
    rules_response = client.get(f"/service-actors/{missing_id}/scope-rules")

    assert actor_response.status_code == 404
    assert keys_response.status_code == 404
    assert scopes_response.status_code == 404
    assert rules_response.status_code == 404
    assert actor_response.json()["detail"] == "Service actor not found."


def test_registry_admin_disabled_preserves_config_auth_fallback(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    raw_registry_key = "registry-only-key"
    raw_config_key = "config-only-key"
    app.dependency_overrides[get_settings] = lambda: Settings(
        service_actor_registry_enabled=False
    )

    with session_factory() as session:
        seed_service_actor_registry(session, raw_key=raw_registry_key)
        settings = Settings(
            service_actor_registry_enabled=False,
            service_actor_api_keys=(
                ConfigServiceActorApiKey(
                    actor_id="service:config-admin-test",
                    key_hash=hash_service_actor_api_key(raw_config_key),
                ),
            ),
        )

        admin_response = client.get("/service-actors")
        config_actor = service_actor_from_api_key(
            raw_config_key,
            settings=settings,
            session=session,
        )
        registry_actor = service_actor_from_api_key(
            raw_registry_key,
            settings=settings,
            session=session,
        )

    assert admin_response.status_code == 503
    assert config_actor is not None
    assert config_actor.actor_type is ActorType.SERVICE
    assert config_actor.actor_id == "service:config-admin-test"
    assert registry_actor is None


def seed_service_actor_registry(
    session: Session,
    *,
    raw_key: str = "admin-api-secret",
) -> ServiceActor:
    now = datetime.now(UTC).replace(microsecond=0)
    service_actor = ServiceActor(
        id=uuid4(),
        actor_id="service:admin-api-test",
        display_name="Admin API test service",
        description="Used by registry admin API tests.",
        status=ServiceActorStatus.ACTIVE,
        created_at=now,
        updated_at=now,
    )
    session.add(service_actor)
    session.flush()
    session.add_all(
        [
            ServiceActorApiKey(
                service_actor_id=service_actor.id,
                key_id="sak_admin_api_test",
                key_hash=hash_service_actor_api_key(raw_key),
                hash_algorithm="sha256",
                status=ServiceActorApiKeyStatus.ACTIVE,
                created_at=now,
                activated_at=now,
                expires_at=now + timedelta(days=30),
                last_used_at=now + timedelta(minutes=5),
                last_used_endpoint="/runtime/tool-call/decision",
            ),
            ServiceActorScope(
                service_actor_id=service_actor.id,
                scope="telemetry:write",
            ),
            ServiceActorScope(
                service_actor_id=service_actor.id,
                scope="runtime:decision",
            ),
            ServiceActorScopeRule(
                service_actor_id=service_actor.id,
                agent_ids=["11111111-1111-4111-8111-111111111111"],
                environments=["production"],
                runtime_modes=["enforcement"],
                tool_names=["send_email"],
            ),
        ]
    )
    session.commit()
    return service_actor


@pytest.fixture()
def api_client() -> Iterator[tuple[TestClient, SessionFactory]]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    testing_session_factory = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )

    def override_get_db_session() -> Iterator[Session]:
        with testing_session_factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_get_db_session
    app.dependency_overrides[get_settings] = lambda: Settings(
        service_actor_registry_enabled=True
    )
    try:
        with TestClient(app) as client:
            yield client, testing_session_factory
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(engine)
        engine.dispose()
