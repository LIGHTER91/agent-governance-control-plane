from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.schema import CreateTable

from agent_governance_api.auth import hash_service_actor_api_key
from agent_governance_api.config import Settings
from agent_governance_api.database import Base
from agent_governance_api.models import (
    ServiceActor,
    ServiceActorApiKey,
    ServiceActorApiKeyStatus,
    ServiceActorScope,
    ServiceActorScopeRule,
    ServiceActorStatus,
)
from agent_governance_api.schemas import (
    ServiceActorApiKeyRead,
    ServiceActorRead,
    ServiceActorScopeRead,
    ServiceActorScopeRuleRead,
)
from agent_governance_api.service_actor_registry import (
    get_service_actor_api_key_by_key_id,
    get_service_actor_by_actor_id,
)


def test_service_actor_status_enum_has_expected_values() -> None:
    assert [item.value for item in ServiceActorStatus] == [
        "active",
        "disabled",
    ]


def test_service_actor_api_key_status_enum_has_expected_values() -> None:
    assert [item.value for item in ServiceActorApiKeyStatus] == [
        "active",
        "retiring",
        "revoked",
        "expired",
    ]


def test_service_actor_registry_tables_compile_for_postgresql() -> None:
    service_actor_ddl = str(
        CreateTable(ServiceActor.__table__).compile(dialect=postgresql.dialect())
    )
    api_key_ddl = str(
        CreateTable(ServiceActorApiKey.__table__).compile(dialect=postgresql.dialect())
    )
    scope_ddl = str(
        CreateTable(ServiceActorScope.__table__).compile(dialect=postgresql.dialect())
    )
    scope_rule_ddl = str(
        CreateTable(ServiceActorScopeRule.__table__).compile(
            dialect=postgresql.dialect()
        )
    )

    assert "CREATE TABLE service_actors" in service_actor_ddl
    assert "service_actor_status" in service_actor_ddl
    assert "UNIQUE (actor_id)" in service_actor_ddl
    assert "CREATE TABLE service_actor_api_keys" in api_key_ddl
    assert "service_actor_api_key_status" in api_key_ddl
    assert "key_hash VARCHAR(255) NOT NULL" in api_key_ddl
    assert "FOREIGN KEY(service_actor_id) REFERENCES service_actors" in api_key_ddl
    assert "raw_key" not in api_key_ddl
    assert "CREATE TABLE service_actor_scopes" in scope_ddl
    assert "scope VARCHAR(255) NOT NULL" in scope_ddl
    assert "FOREIGN KEY(service_actor_id) REFERENCES service_actors" in scope_ddl
    assert "CREATE TABLE service_actor_scope_rules" in scope_rule_ddl
    assert "agent_ids JSON DEFAULT '[]' NOT NULL" in scope_rule_ddl
    assert "environments JSON DEFAULT '[]' NOT NULL" in scope_rule_ddl
    assert "runtime_modes JSON DEFAULT '[]' NOT NULL" in scope_rule_ddl
    assert "tool_names JSON DEFAULT '[]' NOT NULL" in scope_rule_ddl


def test_service_actor_registry_models_persist_without_raw_keys() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    raw_key = "local-raw-secret"
    key_hash = hash_service_actor_api_key(raw_key)

    try:
        with Session(engine) as session:
            actor = ServiceActor(
                actor_id="service:registry-test",
                display_name="Registry test service",
                status=ServiceActorStatus.ACTIVE,
            )
            api_key = ServiceActorApiKey(
                service_actor=actor,
                key_id="sak_test_001",
                key_hash=key_hash,
                hash_algorithm="sha256",
                status=ServiceActorApiKeyStatus.ACTIVE,
                activated_at=datetime.now(UTC),
            )
            session.add(actor)
            session.add(api_key)
            session.commit()

            saved_actor = session.scalars(select(ServiceActor)).one()
            saved_api_key = session.scalars(select(ServiceActorApiKey)).one()

            assert saved_actor.actor_id == "service:registry-test"
            assert saved_actor.api_keys == [saved_api_key]
            assert saved_api_key.service_actor_id == saved_actor.id
            assert saved_api_key.key_hash == key_hash
            assert raw_key not in str(saved_api_key.__dict__)
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_service_actor_api_key_supports_rotation_status_fields() -> None:
    now = datetime.now(UTC)
    retiring_key = ServiceActorApiKey(
        service_actor_id=uuid4(),
        key_id="sak_retiring_001",
        key_hash=hash_service_actor_api_key("retiring-secret"),
        status=ServiceActorApiKeyStatus.RETIRING,
        retiring_at=now,
        grace_expires_at=now + timedelta(hours=24),
        expires_at=now + timedelta(days=90),
        last_used_endpoint="runtime:decision",
    )

    assert retiring_key.status is ServiceActorApiKeyStatus.RETIRING
    assert retiring_key.grace_expires_at == now + timedelta(hours=24)
    assert retiring_key.last_used_endpoint == "runtime:decision"


def test_service_actor_scope_model_persists_relationship() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    try:
        with Session(engine) as session:
            actor = ServiceActor(
                actor_id="service:scope-test",
                display_name="Scope test service",
            )
            scope = ServiceActorScope(
                service_actor=actor,
                scope="runtime:decision",
            )
            session.add(actor)
            session.add(scope)
            session.commit()

            saved_actor = session.scalars(select(ServiceActor)).one()
            saved_scope = session.scalars(select(ServiceActorScope)).one()

            assert saved_actor.scopes == [saved_scope]
            assert saved_scope.service_actor_id == saved_actor.id
            assert saved_scope.scope == "runtime:decision"
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_service_actor_scope_rejects_unsupported_scope() -> None:
    with pytest.raises(ValueError, match="Service actor scope"):
        ServiceActorScope(
            service_actor_id=uuid4(),
            scope="unsupported:scope",
        )


def test_service_actor_scope_is_unique_per_actor() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    try:
        with Session(engine) as session:
            actor = ServiceActor(
                actor_id="service:duplicate-scope-test",
                display_name="Duplicate scope test service",
            )
            session.add(actor)
            session.flush()
            session.add_all(
                [
                    ServiceActorScope(
                        service_actor_id=actor.id,
                        scope="telemetry:write",
                    ),
                    ServiceActorScope(
                        service_actor_id=actor.id,
                        scope="telemetry:write",
                    ),
                ]
            )

            with pytest.raises(IntegrityError):
                session.commit()
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_service_actor_scope_rule_model_persists_supported_fields() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    try:
        with Session(engine) as session:
            actor = ServiceActor(
                actor_id="service:scope-rule-test",
                display_name="Scope rule test service",
            )
            rule = ServiceActorScopeRule(
                service_actor=actor,
                agent_ids=(
                    "11111111-1111-4111-8111-111111111111",
                    "*",
                ),
                environments=("DEVELOPMENT", "*"),
                runtime_modes=("SIMULATION",),
                tool_names=("send_email", "send_email"),
            )
            session.add(actor)
            session.add(rule)
            session.commit()

            saved_actor = session.scalars(select(ServiceActor)).one()
            saved_rule = session.scalars(select(ServiceActorScopeRule)).one()

            assert saved_actor.scope_rules == [saved_rule]
            assert saved_rule.service_actor_id == saved_actor.id
            assert saved_rule.agent_ids == [
                "11111111-1111-4111-8111-111111111111",
                "*",
            ]
            assert saved_rule.environments == ["development", "*"]
            assert saved_rule.runtime_modes == ["simulation"]
            assert saved_rule.tool_names == ["send_email"]
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_service_actor_scope_rule_rejects_unsupported_values() -> None:
    with pytest.raises(ValueError, match="runtime_modes unsupported value"):
        ServiceActorScopeRule(
            service_actor_id=uuid4(),
            runtime_modes=("training",),
        )


def test_service_actor_api_key_rejects_raw_key_material_as_hash() -> None:
    with pytest.raises(ValueError, match="sha256"):
        ServiceActorApiKey(
            service_actor_id=None,
            key_id="sak_invalid_001",
            key_hash="raw-secret-value",
        )


def test_service_actor_read_schemas_do_not_expose_key_hash() -> None:
    now = datetime.now(UTC)
    actor = ServiceActor(
        id=uuid4(),
        actor_id="service:schema-test",
        display_name="Schema test service",
        status=ServiceActorStatus.ACTIVE,
        created_at=now,
        updated_at=now,
    )
    api_key = ServiceActorApiKey(
        id=uuid4(),
        service_actor_id=actor.id,
        key_id="sak_schema_001",
        key_hash=hash_service_actor_api_key("schema-secret"),
        hash_algorithm="sha256",
        status=ServiceActorApiKeyStatus.ACTIVE,
        created_at=now,
    )

    actor_schema = ServiceActorRead.model_validate(actor)
    api_key_schema = ServiceActorApiKeyRead.model_validate(api_key)

    assert actor_schema.actor_id == "service:schema-test"
    assert api_key_schema.key_id == "sak_schema_001"
    assert not hasattr(api_key_schema, "key_hash")
    assert "schema-secret" not in api_key_schema.model_dump_json()
    assert "sha256:" not in api_key_schema.model_dump_json()


def test_service_actor_scope_read_schemas() -> None:
    now = datetime.now(UTC)
    service_actor_id = uuid4()
    scope = ServiceActorScope(
        id=uuid4(),
        service_actor_id=service_actor_id,
        scope="telemetry:write",
        created_at=now,
    )
    rule = ServiceActorScopeRule(
        id=uuid4(),
        service_actor_id=service_actor_id,
        agent_ids=["*"],
        environments=["development"],
        runtime_modes=["simulation"],
        tool_names=["send_email"],
        created_at=now,
        updated_at=now,
    )

    scope_schema = ServiceActorScopeRead.model_validate(scope)
    rule_schema = ServiceActorScopeRuleRead.model_validate(rule)

    assert scope_schema.service_actor_id == service_actor_id
    assert scope_schema.scope == "telemetry:write"
    assert rule_schema.agent_ids == ["*"]
    assert rule_schema.environments == ["development"]
    assert rule_schema.runtime_modes == ["simulation"]
    assert rule_schema.tool_names == ["send_email"]


def test_registry_lookup_is_disabled_until_feature_flag_is_enabled() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    try:
        with Session(engine) as session:
            actor = ServiceActor(
                actor_id="service:flag-test",
                display_name="Flag test service",
            )
            api_key = ServiceActorApiKey(
                service_actor=actor,
                key_id="sak_flag_001",
                key_hash=hash_service_actor_api_key("flag-secret"),
            )
            session.add(actor)
            session.add(api_key)
            session.commit()

            disabled_settings = Settings(service_actor_registry_enabled=False)
            enabled_settings = Settings(service_actor_registry_enabled=True)

            assert (
                get_service_actor_by_actor_id(
                    session,
                    "service:flag-test",
                    settings=disabled_settings,
                )
                is None
            )
            assert (
                get_service_actor_api_key_by_key_id(
                    session,
                    "sak_flag_001",
                    settings=disabled_settings,
                )
                is None
            )
            assert (
                get_service_actor_by_actor_id(
                    session,
                    "service:flag-test",
                    settings=enabled_settings,
                )
                is not None
            )
            assert (
                get_service_actor_api_key_by_key_id(
                    session,
                    "sak_flag_001",
                    settings=enabled_settings,
                )
                is not None
            )
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_service_actor_actor_id_must_use_service_prefix() -> None:
    with pytest.raises(ValueError, match="service:<stable-id>"):
        ServiceActor(actor_id="runtime-test", display_name="Runtime test")


def test_service_actor_key_id_is_unique() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    try:
        with Session(engine) as session:
            actor = ServiceActor(
                actor_id="service:unique-key-test",
                display_name="Unique key test service",
            )
            session.add(actor)
            session.flush()
            session.add_all(
                [
                    ServiceActorApiKey(
                        service_actor_id=actor.id,
                        key_id="sak_duplicate",
                        key_hash=hash_service_actor_api_key("first-secret"),
                    ),
                    ServiceActorApiKey(
                        service_actor_id=actor.id,
                        key_id="sak_duplicate",
                        key_hash=hash_service_actor_api_key("second-secret"),
                    ),
                ]
            )

            with pytest.raises(IntegrityError):
                session.commit()
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_service_actor_registry_migration_declares_expected_tables() -> None:
    migration_path = (
        Path(__file__).resolve().parents[1]
        / "migrations"
        / "versions"
        / "202605210001_create_service_actor_registry.py"
    )
    migration_text = migration_path.read_text(encoding="utf-8")

    assert 'revision: str = "202605210001"' in migration_text
    assert 'down_revision: str | None = "202605180001"' in migration_text
    assert '"service_actors"' in migration_text
    assert '"service_actor_api_keys"' in migration_text
    assert '"key_hash"' in migration_text
    assert "raw_key" not in migration_text


def test_service_actor_scope_migration_declares_expected_tables() -> None:
    migration_path = (
        Path(__file__).resolve().parents[1]
        / "migrations"
        / "versions"
        / "202605220001_create_service_actor_scope_tables.py"
    )
    migration_text = migration_path.read_text(encoding="utf-8")

    assert 'revision: str = "202605220001"' in migration_text
    assert 'down_revision: str | None = "202605210001"' in migration_text
    assert '"service_actor_scopes"' in migration_text
    assert '"service_actor_scope_rules"' in migration_text
    assert '"service_actor_id"' in migration_text
    assert '"scope"' in migration_text
    assert '"agent_ids"' in migration_text
    assert '"environments"' in migration_text
    assert '"runtime_modes"' in migration_text
    assert '"tool_names"' in migration_text
