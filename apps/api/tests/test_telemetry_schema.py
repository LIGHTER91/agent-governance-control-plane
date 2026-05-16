from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from agent_governance_api.models import Environment
from agent_governance_api.telemetry import AgentRun, TraceEvent, TraceEventType


def test_valid_agent_run_schema() -> None:
    agent_id = uuid4()
    run_id = uuid4()
    started_at = datetime.now(UTC)

    run = AgentRun(
        id=run_id,
        agent_id=agent_id,
        correlation_id="corr-123",
        environment="production",
        started_at=started_at,
        status="started",
        summary="Agent run started.",
        metadata={"framework": "LangGraph"},
    )

    assert run.id == run_id
    assert run.agent_id == agent_id
    assert run.environment is Environment.PRODUCTION
    assert run.correlation_id == "corr-123"
    assert run.metadata == {"framework": "LangGraph"}


def test_valid_trace_event_schema() -> None:
    event_id = uuid4()
    agent_id = uuid4()
    run_id = uuid4()
    timestamp = datetime.now(UTC)

    event = TraceEvent(
        id=event_id,
        agent_id=agent_id,
        run_id=run_id,
        correlation_id="corr-123",
        event_type="tool_call_requested",
        timestamp=timestamp,
        summary="Agent requested a tool call.",
        metadata={"tool_name": "send_email"},
    )

    assert event.id == event_id
    assert event.agent_id == agent_id
    assert event.run_id == run_id
    assert event.event_type is TraceEventType.TOOL_CALL_REQUESTED
    assert event.metadata == {"tool_name": "send_email"}


def test_trace_event_rejects_invalid_event_type() -> None:
    with pytest.raises(ValidationError):
        TraceEvent(
            id=uuid4(),
            agent_id=uuid4(),
            run_id=uuid4(),
            correlation_id="corr-123",
            event_type="tool_call_finished",
            timestamp=datetime.now(UTC),
            summary="Unsupported event type.",
        )


@pytest.mark.parametrize("missing_field", ["correlation_id", "run_id"])
def test_trace_event_rejects_missing_correlation_id_or_run_id(
    missing_field: str,
) -> None:
    payload = {
        "id": uuid4(),
        "agent_id": uuid4(),
        "run_id": uuid4(),
        "correlation_id": "corr-123",
        "event_type": "tool_call_allowed",
        "timestamp": datetime.now(UTC),
        "summary": "Tool call allowed.",
    }
    payload.pop(missing_field)

    with pytest.raises(ValidationError):
        TraceEvent(**payload)


def test_agent_run_rejects_missing_correlation_id() -> None:
    with pytest.raises(ValidationError):
        AgentRun(
            id=uuid4(),
            agent_id=uuid4(),
            environment="development",
            started_at=datetime.now(UTC),
            status="started",
        )


@pytest.mark.parametrize(
    "metadata",
    [
        {"api_key": "redacted"},
        {"access_token": "redacted"},
        {"token": "redacted"},
        {"password": "redacted"},
        {"client_secret": "redacted"},
        {"authorization": "Bearer redacted"},
        {"raw_prompt": "do not store this"},
        {"raw_payload": "do not store this"},
    ],
)
def test_trace_event_rejects_unsafe_metadata_keys(
    metadata: dict[str, str],
) -> None:
    with pytest.raises(ValidationError):
        TraceEvent(
            id=uuid4(),
            agent_id=uuid4(),
            run_id=uuid4(),
            correlation_id="corr-123",
            event_type=TraceEventType.ERROR,
            timestamp=datetime.now(UTC),
            summary="Tool call failed.",
            metadata=metadata,
        )


def test_trace_event_rejects_nested_metadata() -> None:
    with pytest.raises(ValidationError):
        TraceEvent(
            id=uuid4(),
            agent_id=uuid4(),
            run_id=uuid4(),
            correlation_id="corr-123",
            event_type=TraceEventType.ERROR,
            timestamp=datetime.now(UTC),
            summary="Tool call failed.",
            metadata={"nested": {"secret": "do not store this"}},
        )
