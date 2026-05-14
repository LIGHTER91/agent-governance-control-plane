from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

from agent_governance_api import audit
from agent_governance_api.audit import append_audit_log
from agent_governance_api.main import app
from agent_governance_api.models import ActorType, AuditLog


class FakeSession:
    def __init__(self) -> None:
        self.added: object | None = None
        self.flushed = False

    def add(self, instance: object) -> None:
        self.added = instance

    def flush(self) -> None:
        self.flushed = True


def test_actor_type_enum_has_expected_values() -> None:
    assert [item.value for item in ActorType] == [
        "system",
        "user",
        "service",
        "development",
    ]


def test_append_audit_log_creates_record_with_system_placeholder_actor() -> None:
    session = FakeSession()

    record = append_audit_log(
        session,  # type: ignore[arg-type]
        event_type="agent_created",
        actor_type=ActorType.SYSTEM,
        actor_id="system",
        entity_type="Agent",
        entity_id="agent:123",
        summary="Agent record created.",
        metadata={"source": "test"},
    )

    assert session.added is record
    assert session.flushed is True
    assert record.actor_type is ActorType.SYSTEM
    assert record.actor_id == "system"
    assert record.entity_type == "Agent"
    assert record.metadata_ == {"source": "test"}
    assert record.created_at.tzinfo is not None


def test_append_audit_log_supports_development_placeholder_actor() -> None:
    session = FakeSession()

    record = append_audit_log(
        session,  # type: ignore[arg-type]
        event_type="agent_updated",
        actor_type=ActorType.DEVELOPMENT,
        actor_id="dev-placeholder",
        entity_type="Agent",
        entity_id="agent:123",
        summary="Agent record updated during development.",
    )

    assert record.actor_type is ActorType.DEVELOPMENT
    assert record.actor_id == "dev-placeholder"
    assert record.metadata_ == {}


def test_append_audit_log_rejects_unsafe_metadata_keys() -> None:
    session = FakeSession()

    try:
        append_audit_log(
            session,  # type: ignore[arg-type]
            event_type="agent_created",
            actor_type=ActorType.SYSTEM,
            actor_id="system",
            entity_type="Agent",
            entity_id="agent:123",
            summary="Agent record created.",
            metadata={"raw_prompt": "do not store this"},
        )
    except ValueError as exc:
        assert str(exc) == "Audit metadata contains unsafe key names."
    else:
        raise AssertionError("Expected unsafe audit metadata to be rejected.")

    assert session.added is None
    assert session.flushed is False


def test_audit_log_table_compiles_for_postgresql() -> None:
    ddl = str(CreateTable(AuditLog.__table__).compile(dialect=postgresql.dialect()))

    assert "CREATE TABLE audit_logs" in ddl
    assert "actor_id" in ddl
    assert "metadata" in ddl
    assert "audit_actor_type" in ddl


def test_audit_module_exposes_only_append_operation() -> None:
    assert audit.__all__ == ["append_audit_log"]
    assert not hasattr(audit, "update_audit_log")
    assert not hasattr(audit, "delete_audit_log")


def test_app_exposes_no_public_audit_routes() -> None:
    audit_routes = [
        route.path for route in app.routes if "audit" in getattr(route, "path", "")
    ]

    assert audit_routes == []
