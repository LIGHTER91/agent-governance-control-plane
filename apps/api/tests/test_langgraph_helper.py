import json
from collections.abc import Mapping

import pytest

from examples.langgraph_helper import (
    AGCPClient,
    Decision,
    UnsafeContextError,
    decision_to_branch,
    governed_tool_call,
    resume_after_approval,
)
from examples.langgraph_helper.helper import JsonObject, build_decision_payload

AGENT_ID = "11111111-1111-4111-8111-111111111111"
RUN_ID = "22222222-2222-4222-8222-222222222222"
REQUEST_ID = "support-run-001:create-ticket"
TOOL_NAME = "create_ticket"
POLICY_DECISION_ID = "66666666-6666-4666-8666-666666666666"
HUMAN_APPROVAL_ID = "77777777-7777-4777-8777-777777777777"


class FakeTransport:
    def __init__(self, responses: list[JsonObject]) -> None:
        self.responses = responses
        self.calls: list[tuple[str, JsonObject, dict[str, str], float]] = []

    def __call__(
        self,
        url: str,
        payload: JsonObject,
        headers: Mapping[str, str],
        timeout_seconds: float,
    ) -> JsonObject:
        self.calls.append((url, payload, dict(headers), timeout_seconds))
        return self.responses.pop(0)


def test_allow_executes_fake_tool() -> None:
    transport = FakeTransport(
        [decision_response(decision="allow", proceed=True, reason="Allowed.")]
    )
    client = AGCPClient(
        base_url="http://agcp.local",
        api_key="test-service-actor-key",
        transport=transport,
    )
    calls: list[str] = []

    def fake_tool(ticket_ref: str) -> dict[str, str]:
        calls.append(ticket_ref)
        return {"ticket_ref": ticket_ref, "status": "queued"}

    result = governed_tool_call(
        client=client,
        tool=fake_tool,
        agent_id=AGENT_ID,
        run_id=RUN_ID,
        request_id=REQUEST_ID,
        correlation_id="support-run-001",
        tool_name=TOOL_NAME,
        action_summary="Create an internal support ticket.",
        tool_args=("ticket-draft-001",),
    )

    assert calls == ["ticket-draft-001"]
    assert result.tool_executed is True
    assert result.branch == "allowed"
    assert result.tool_result == {"ticket_ref": "ticket-draft-001", "status": "queued"}


def test_deny_does_not_execute_fake_tool() -> None:
    transport = FakeTransport(
        [decision_response(decision="deny", proceed=False, reason="Denied.")]
    )
    client = AGCPClient(base_url="http://agcp.local", transport=transport)
    calls: list[str] = []

    result = governed_tool_call(
        client=client,
        tool=lambda: calls.append("called"),
        agent_id=AGENT_ID,
        run_id=RUN_ID,
        request_id=REQUEST_ID,
        tool_name=TOOL_NAME,
    )

    assert calls == []
    assert result.tool_executed is False
    assert result.branch == "denied"
    assert result.decision.reason == "Denied."


def test_require_human_review_returns_pause_branch_without_tool_execution() -> None:
    transport = FakeTransport(
        [
            decision_response(
                decision="require_human_review",
                proceed=False,
                reason="Needs review.",
                human_approval_id=HUMAN_APPROVAL_ID,
            )
        ]
    )
    client = AGCPClient(base_url="http://agcp.local", transport=transport)
    calls: list[str] = []

    result = governed_tool_call(
        client=client,
        tool=lambda: calls.append("called"),
        agent_id=AGENT_ID,
        run_id=RUN_ID,
        request_id=REQUEST_ID,
        tool_name=TOOL_NAME,
    )

    assert calls == []
    assert result.tool_executed is False
    assert result.branch == "requires_review"
    assert result.decision.human_approval_id == HUMAN_APPROVAL_ID


def test_client_sends_expected_safe_runtime_gateway_payload() -> None:
    transport = FakeTransport(
        [decision_response(decision="allow", proceed=True, reason="Allowed.")]
    )
    client = AGCPClient(
        base_url="http://agcp.local/",
        api_key="test-service-actor-key",
        timeout_seconds=2.5,
        transport=transport,
    )

    decision = client.decide_tool_call(
        agent_id=AGENT_ID,
        run_id=RUN_ID,
        request_id=REQUEST_ID,
        correlation_id="support-run-001",
        tool_name=TOOL_NAME,
        action_summary="Create an internal support ticket.",
        mode="enforcement",
        action_type="ticket_create",
        capability_id="33333333-3333-4333-8333-333333333333",
        source_ids=["44444444-4444-4444-8444-444444444444"],
        model_id="55555555-5555-4555-8555-555555555555",
        purpose="support_followup",
        environment="development",
        risk_level="medium",
        metadata={"langgraph_node": "support_followup"},
    )

    assert decision.branch == "allowed"
    assert len(transport.calls) == 1
    url, payload, headers, timeout_seconds = transport.calls[0]
    assert url == "http://agcp.local/runtime/tool-calls/decision"
    assert headers["X-AGCP-API-Key"] == "test-service-actor-key"
    assert timeout_seconds == 2.5
    assert payload == {
        "request_id": REQUEST_ID,
        "agent_id": AGENT_ID,
        "run_id": RUN_ID,
        "correlation_id": "support-run-001",
        "tool_name": TOOL_NAME,
        "action_summary": "Create an internal support ticket.",
        "metadata": {
            "langgraph_node": "support_followup",
            "environment": "development",
            "risk_level": "medium",
        },
        "mode": "enforcement",
        "action_type": "ticket_create",
        "capability_id": "33333333-3333-4333-8333-333333333333",
        "model_id": "55555555-5555-4555-8555-555555555555",
        "purpose": "support_followup",
        "source_ids": ["44444444-4444-4444-8444-444444444444"],
    }
    assert_no_unsafe_payload_fields(payload)


def test_resume_helper_calls_expected_endpoint() -> None:
    transport = FakeTransport(
        [
            resume_response(
                decision="allow",
                proceed=True,
                human_approval_status="approved",
                reason="Approved.",
            )
        ]
    )
    client = AGCPClient(base_url="http://agcp.local", transport=transport)

    decision = resume_after_approval(
        client=client,
        resume_id=f"{REQUEST_ID}:resume:001",
        original_request_id=REQUEST_ID,
        agent_id=AGENT_ID,
        run_id=RUN_ID,
        tool_name=TOOL_NAME,
        human_approval_id=HUMAN_APPROVAL_ID,
        policy_decision_id=POLICY_DECISION_ID,
        action_ref="ticket-draft-001",
        correlation_id="support-run-001",
        metadata={"langgraph_node": "support_followup"},
    )

    assert decision.branch == "allowed"
    assert len(transport.calls) == 1
    url, payload, _headers, _timeout_seconds = transport.calls[0]
    assert url == "http://agcp.local/runtime/tool-calls/resume"
    assert payload == {
        "resume_id": f"{REQUEST_ID}:resume:001",
        "original_request_id": REQUEST_ID,
        "agent_id": AGENT_ID,
        "run_id": RUN_ID,
        "tool_name": TOOL_NAME,
        "human_approval_id": HUMAN_APPROVAL_ID,
        "policy_decision_id": POLICY_DECISION_ID,
        "action_ref": "ticket-draft-001",
        "correlation_id": "support-run-001",
        "metadata": {"langgraph_node": "support_followup"},
    }
    assert_no_unsafe_payload_fields(payload)


@pytest.mark.parametrize(
    "metadata",
    [
        {"raw_prompt": "full prompt text"},
        {"source_content": "retrieved source body"},
        {"chunks": "retrieved chunk text"},
        {"api_key": "secret"},
        {"authorization": "Bearer secret"},
    ],
)
def test_helper_rejects_unsafe_metadata_keys(
    metadata: dict[str, str],
) -> None:
    with pytest.raises(UnsafeContextError):
        build_decision_payload(
            agent_id=AGENT_ID,
            run_id=RUN_ID,
            request_id=REQUEST_ID,
            tool_name=TOOL_NAME,
            metadata=metadata,
        )


def test_safe_helper_example_payload_does_not_include_raw_content() -> None:
    payload = build_decision_payload(
        agent_id=AGENT_ID,
        run_id=RUN_ID,
        request_id=REQUEST_ID,
        tool_name=TOOL_NAME,
        action_summary="Create an internal support ticket.",
        environment="development",
        risk_level="medium",
        metadata={"langgraph_node": "support_followup"},
    )

    serialized_payload = json.dumps(payload)
    assert "raw prompt text" not in serialized_payload
    assert "retrieved source body" not in serialized_payload
    assert "retrieved chunk text" not in serialized_payload
    assert_no_unsafe_payload_fields(payload)


@pytest.mark.parametrize(
    ("decision", "proceed", "expected_branch"),
    [
        ("allow", True, "allowed"),
        ("deny", False, "denied"),
        ("require_human_review", False, "requires_review"),
        ("not_applicable", False, "not_applicable"),
    ],
)
def test_decision_to_branch_maps_runtime_decisions(
    decision: str,
    proceed: bool,
    expected_branch: str,
) -> None:
    assert (
        decision_to_branch(
            Decision(
                request_id=REQUEST_ID,
                agent_id=AGENT_ID,
                run_id=RUN_ID,
                tool_name=TOOL_NAME,
                decision=decision,
                proceed=proceed,
                reason="Reason.",
            )
        )
        == expected_branch
    )


def decision_response(
    *,
    decision: str,
    proceed: bool,
    reason: str,
    human_approval_id: str | None = None,
) -> JsonObject:
    return {
        "request_id": REQUEST_ID,
        "agent_id": AGENT_ID,
        "run_id": RUN_ID,
        "tool_name": TOOL_NAME,
        "decision": decision,
        "proceed": proceed,
        "reason": reason,
        "trace_event_id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
        "policy_decision_id": POLICY_DECISION_ID,
        "human_approval_id": human_approval_id,
    }


def resume_response(
    *,
    decision: str,
    proceed: bool,
    human_approval_status: str,
    reason: str,
) -> JsonObject:
    return {
        "resume_id": f"{REQUEST_ID}:resume:001",
        "original_request_id": REQUEST_ID,
        "agent_id": AGENT_ID,
        "run_id": RUN_ID,
        "tool_name": TOOL_NAME,
        "decision": decision,
        "proceed": proceed,
        "reason": reason,
        "human_approval_status": human_approval_status,
        "trace_event_id": "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
        "policy_decision_id": POLICY_DECISION_ID,
        "human_approval_id": HUMAN_APPROVAL_ID,
    }


def assert_no_unsafe_payload_fields(payload: JsonObject) -> None:
    serialized = json.dumps(payload).lower()
    unsafe_terms = (
        "api_key",
        "authorization",
        "chunk",
        "credential",
        "password",
        "prompt",
        "raw_content",
        "source_content",
        "secret",
        "token",
    )
    for term in unsafe_terms:
        assert term not in serialized
