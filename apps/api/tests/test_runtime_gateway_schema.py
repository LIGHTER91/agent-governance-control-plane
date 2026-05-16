from uuid import uuid4

import pytest
from pydantic import ValidationError

from agent_governance_api.models import PolicyDecisionValue
from agent_governance_api.runtime_gateway import (
    RuntimeDecisionMode,
    RuntimeToolCallDecisionRequest,
    RuntimeToolCallDecisionResponse,
)


def test_valid_runtime_tool_call_decision_request() -> None:
    agent_id = uuid4()
    run_id = uuid4()

    request = RuntimeToolCallDecisionRequest(
        request_id="runtime-request-001",
        agent_id=agent_id,
        run_id=run_id,
        correlation_id="support-run-001",
        tool_name="send_email",
        action_summary="Send a support follow-up email.",
        metadata={"ticket_category": "support"},
        mode="simulation",
    )

    assert request.request_id == "runtime-request-001"
    assert request.agent_id == agent_id
    assert request.run_id == run_id
    assert request.tool_name == "send_email"
    assert request.metadata == {"ticket_category": "support"}
    assert request.mode is RuntimeDecisionMode.SIMULATION


def test_valid_runtime_tool_call_decision_response() -> None:
    response = RuntimeToolCallDecisionResponse(
        request_id="runtime-request-001",
        agent_id=uuid4(),
        run_id=uuid4(),
        tool_name="send_email",
        decision="allow",
        proceed=True,
        reason="The requested tool is allowed.",
        trace_event_id=uuid4(),
        policy_decision_id=uuid4(),
        human_approval_id=None,
    )

    assert response.decision is PolicyDecisionValue.ALLOW
    assert response.proceed is True


def test_runtime_request_rejects_invalid_mode() -> None:
    payload = runtime_request_payload()
    payload["mode"] = "blocking"

    with pytest.raises(ValidationError):
        RuntimeToolCallDecisionRequest(**payload)


@pytest.mark.parametrize("missing_field", ["request_id", "tool_name"])
def test_runtime_request_rejects_missing_required_fields(missing_field: str) -> None:
    payload = runtime_request_payload()
    payload.pop(missing_field)

    with pytest.raises(ValidationError):
        RuntimeToolCallDecisionRequest(**payload)


@pytest.mark.parametrize(
    "metadata",
    [
        {"api_key": "redacted"},
        {"token": "redacted"},
        {"password": "redacted"},
        {"client_secret": "redacted"},
        {"authorization": "Bearer redacted"},
        {"raw_prompt": "do not store this"},
        {"raw_payload": "do not store this"},
    ],
)
def test_runtime_request_rejects_unsafe_metadata_keys(
    metadata: dict[str, str],
) -> None:
    payload = runtime_request_payload()
    payload["metadata"] = metadata

    with pytest.raises(ValidationError):
        RuntimeToolCallDecisionRequest(**payload)


@pytest.mark.parametrize(
    ("decision", "proceed"),
    [
        (PolicyDecisionValue.ALLOW, True),
        (PolicyDecisionValue.DENY, False),
        (PolicyDecisionValue.REQUIRE_HUMAN_REVIEW, False),
        (PolicyDecisionValue.NOT_APPLICABLE, False),
    ],
)
def test_runtime_response_accepts_consistent_decision_and_proceed(
    decision: PolicyDecisionValue,
    proceed: bool,
) -> None:
    payload = runtime_response_payload(decision=decision, proceed=proceed)

    response = RuntimeToolCallDecisionResponse(**payload)

    assert response.decision is decision
    assert response.proceed is proceed


@pytest.mark.parametrize(
    ("decision", "proceed"),
    [
        (PolicyDecisionValue.ALLOW, False),
        (PolicyDecisionValue.DENY, True),
        (PolicyDecisionValue.REQUIRE_HUMAN_REVIEW, True),
        (PolicyDecisionValue.NOT_APPLICABLE, True),
    ],
)
def test_runtime_response_rejects_inconsistent_decision_and_proceed(
    decision: PolicyDecisionValue,
    proceed: bool,
) -> None:
    payload = runtime_response_payload(decision=decision, proceed=proceed)

    with pytest.raises(ValidationError):
        RuntimeToolCallDecisionResponse(**payload)


def runtime_request_payload() -> dict[str, object]:
    return {
        "request_id": "runtime-request-001",
        "agent_id": uuid4(),
        "run_id": uuid4(),
        "correlation_id": "support-run-001",
        "tool_name": "send_email",
        "action_summary": "Send a support follow-up email.",
        "metadata": {"ticket_category": "support"},
        "mode": "simulation",
    }


def runtime_response_payload(
    *,
    decision: PolicyDecisionValue,
    proceed: bool,
) -> dict[str, object]:
    return {
        "request_id": "runtime-request-001",
        "agent_id": uuid4(),
        "run_id": uuid4(),
        "tool_name": "send_email",
        "decision": decision,
        "proceed": proceed,
        "reason": "Runtime policy decision.",
        "trace_event_id": None,
        "policy_decision_id": None,
        "human_approval_id": None,
    }
