from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, event, select
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.schema import CreateTable

from agent_governance_api.database import Base
from agent_governance_api.models import (
    Agent,
    AgentRunRecord,
    AgentStatus,
    Environment,
    OwnerType,
    RiskLevel,
    TraceEventRecord,
    TraceEventType,
)


def test_telemetry_tables_compile_for_postgresql() -> None:
    agent_runs_ddl = str(
        CreateTable(AgentRunRecord.__table__).compile(dialect=postgresql.dialect())
    )
    trace_events_ddl = str(
        CreateTable(TraceEventRecord.__table__).compile(dialect=postgresql.dialect())
    )

    assert "CREATE TABLE agent_runs" in agent_runs_ddl
    assert "agent_run_environment" in agent_runs_ddl
    assert "UNIQUE (agent_id, run_id)" in agent_runs_ddl
    assert "FOREIGN KEY(agent_id) REFERENCES agents" in agent_runs_ddl
    assert "metadata JSON DEFAULT '{}'" in agent_runs_ddl
    assert "CREATE TABLE trace_events" in trace_events_ddl
    assert "trace_event_type" in trace_events_ddl
    assert "FOREIGN KEY(agent_id) REFERENCES agents" in trace_events_ddl
    assert "FOREIGN KEY(agent_id, run_id) REFERENCES agent_runs" in trace_events_ddl


def test_trace_event_with_matching_agent_id_and_run_id_persists() -> None:
    engine = create_foreign_key_test_engine()
    Base.metadata.create_all(engine)

    try:
        with Session(engine) as session:
            agent = build_agent()
            session.add(agent)
            session.flush()

            run_id = uuid4()
            run = AgentRunRecord(
                agent_id=agent.id,
                run_id=run_id,
                correlation_id="corr-123",
                environment=Environment.DEVELOPMENT,
                status="started",
                started_at=datetime.now(UTC),
                summary="Agent run started.",
                metadata_={"framework": "LangGraph"},
            )
            event = TraceEventRecord(
                agent_id=agent.id,
                run_id=run_id,
                correlation_id="corr-123",
                event_type=TraceEventType.TOOL_CALL_REQUESTED,
                timestamp=datetime.now(UTC),
                summary="Tool call requested.",
                metadata_={"tool_name": "send_email"},
            )
            session.add_all([run, event])
            session.commit()

            saved_run = session.scalars(select(AgentRunRecord)).one()
            saved_event = session.scalars(select(TraceEventRecord)).one()

            assert saved_run.agent_id == agent.id
            assert saved_run.run_id == run_id
            assert saved_run.metadata_ == {"framework": "LangGraph"}
            assert saved_event.agent_id == agent.id
            assert saved_event.run_id == run_id
            assert saved_event.event_type is TraceEventType.TOOL_CALL_REQUESTED
            assert saved_event.metadata_ == {"tool_name": "send_email"}
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_trace_event_with_mismatched_agent_id_and_run_id_is_rejected() -> None:
    engine = create_foreign_key_test_engine()
    Base.metadata.create_all(engine)

    try:
        with Session(engine) as session:
            run_agent = build_agent()
            event_agent = build_agent(name="Risk review assistant")
            session.add_all([run_agent, event_agent])
            session.flush()

            run_id = uuid4()
            run = AgentRunRecord(
                agent_id=run_agent.id,
                run_id=run_id,
                correlation_id="corr-123",
                environment=Environment.DEVELOPMENT,
                status="started",
                started_at=datetime.now(UTC),
                summary="Agent run started.",
                metadata_={},
            )
            mismatched_event = TraceEventRecord(
                agent_id=event_agent.id,
                run_id=run_id,
                correlation_id="corr-123",
                event_type=TraceEventType.TOOL_CALL_REQUESTED,
                timestamp=datetime.now(UTC),
                summary="Tool call requested.",
                metadata_={},
            )
            session.add_all([run, mismatched_event])

            with pytest.raises(IntegrityError):
                session.commit()
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.mark.parametrize(
    ("record_class", "metadata"),
    [
        (AgentRunRecord, {"api_key": "redacted"}),
        (TraceEventRecord, {"authorization": "Bearer redacted"}),
        (TraceEventRecord, {"access_token": "redacted"}),
    ],
)
def test_telemetry_records_reject_unsafe_metadata_keys(
    record_class: type[AgentRunRecord] | type[TraceEventRecord],
    metadata: dict[str, str],
) -> None:
    common_fields = {
        "agent_id": uuid4(),
        "run_id": uuid4(),
        "correlation_id": "corr-123",
        "metadata_": metadata,
    }
    event_fields = {
        "event_type": TraceEventType.ERROR,
        "timestamp": datetime.now(UTC),
        "summary": "Telemetry event rejected.",
    }
    run_fields = {
        "environment": Environment.DEVELOPMENT,
        "status": "started",
        "started_at": datetime.now(UTC),
        "summary": "Agent run rejected.",
    }

    with pytest.raises(ValueError, match="Metadata contains unsafe key names."):
        if record_class is AgentRunRecord:
            record_class(**common_fields, **run_fields)
        else:
            record_class(**common_fields, **event_fields)


def create_foreign_key_test_engine():
    engine = create_engine("sqlite+pysqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


def build_agent(name: str = "Support assistant") -> Agent:
    return Agent(
        name=name,
        description=None,
        owner_type=OwnerType.TEAM,
        owner_id="team:ai-platform",
        owner_name="AI Platform",
        owner_contact_email="owner@example.com",
        environment=Environment.DEVELOPMENT,
        status=AgentStatus.DRAFT,
        risk_level=RiskLevel.LOW,
        framework="LangGraph",
    )
