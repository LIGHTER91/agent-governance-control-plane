import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from uuid import uuid4

import pytest


@pytest.fixture()
def langgraph_spike() -> ModuleType:
    repo_root = Path(__file__).resolve().parents[3]
    example_path = repo_root / "docs" / "examples" / "langgraph_adapter_spike.py"
    spec = importlib.util.spec_from_file_location(
        "langgraph_adapter_spike",
        example_path,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["langgraph_adapter_spike"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def langgraph_context(langgraph_spike: ModuleType) -> object:
    return langgraph_spike.LangGraphRunContext(
        agent_id=uuid4(),
        run_id=uuid4(),
        correlation_id="langgraph-thread-001",
        node_name="support_followup",
        mode="enforcement",
        metadata={"graph_name": "support_agent"},
    )


@pytest.fixture()
def langgraph_tool_call(langgraph_spike: ModuleType) -> object:
    return langgraph_spike.LangGraphToolCall(
        tool_name="create_ticket",
        action_ref="ticket-draft-001",
        action_summary="Create an internal support ticket.",
        metadata={"ticket_category": "support"},
    )


@pytest.fixture()
def blocked_langgraph_tool_call(
    langgraph_spike: ModuleType,
    langgraph_context: object,
    langgraph_tool_call: object,
) -> object:
    return langgraph_spike.BlockedLangGraphToolCall(
        context=langgraph_context,
        tool_call=langgraph_tool_call,
        original_request_id=langgraph_spike.stable_request_id(
            langgraph_context,
            langgraph_tool_call,
        ),
        human_approval_id=uuid4(),
        policy_decision_id=uuid4(),
    )


def test_langgraph_spike_builds_stable_decision_request(
    langgraph_spike: ModuleType,
    langgraph_context: object,
    langgraph_tool_call: object,
) -> None:
    first_payload = langgraph_spike.build_runtime_decision_request(
        langgraph_context,
        langgraph_tool_call,
    )
    second_payload = langgraph_spike.build_runtime_decision_request(
        langgraph_context,
        langgraph_tool_call,
    )

    assert first_payload == second_payload
    assert first_payload["request_id"].startswith("langgraph:create_ticket:")
    assert first_payload["tool_name"] == "create_ticket"
    assert first_payload["mode"] == "enforcement"
    assert first_payload["action_summary"] == "Create an internal support ticket."
    assert first_payload["metadata"] == {
        "graph_name": "support_agent",
        "ticket_category": "support",
        "langgraph_node": "support_followup",
        "action_ref": "ticket-draft-001",
    }


def test_langgraph_spike_executes_wrapped_tool_only_when_allowed(
    langgraph_spike: ModuleType,
    langgraph_context: object,
    langgraph_tool_call: object,
) -> None:
    calls = []
    observed_payloads = []

    def decision_client(payload: dict[str, object]) -> dict[str, object]:
        observed_payloads.append(payload)
        return decision_response(
            request_id=str(payload["request_id"]),
            decision="allow",
            proceed=True,
            reason="Tool call is allowed.",
        )

    def original_tool(ticket_ref: str) -> dict[str, str]:
        calls.append(ticket_ref)
        return {"ticket_ref": ticket_ref, "status": "queued"}

    result = langgraph_spike.governed_langgraph_tool_call(
        context=langgraph_context,
        tool_call=langgraph_tool_call,
        tool_function=original_tool,
        decision_client=decision_client,
        args=("ticket-draft-001",),
    )

    assert calls == ["ticket-draft-001"]
    assert len(observed_payloads) == 1
    assert result["status"] == "executed"
    assert result["decision"] == "allow"
    assert result["tool_result"] == {
        "ticket_ref": "ticket-draft-001",
        "status": "queued",
    }


@pytest.mark.parametrize(
    ("decision", "expected_status", "human_approval_id"),
    [
        ("deny", "blocked_denied", None),
        (
            "require_human_review",
            "blocked_pending_human_review",
            "77777777-7777-4777-8777-777777777777",
        ),
        ("not_applicable", "blocked_not_applicable", None),
    ],
)
def test_langgraph_spike_blocks_non_allow_decisions_without_tool_execution(
    langgraph_spike: ModuleType,
    langgraph_context: object,
    langgraph_tool_call: object,
    decision: str,
    expected_status: str,
    human_approval_id: str | None,
) -> None:
    calls = []

    def decision_client(payload: dict[str, object]) -> dict[str, object]:
        return decision_response(
            request_id=str(payload["request_id"]),
            decision=decision,
            proceed=False,
            reason="Tool call did not proceed.",
            human_approval_id=human_approval_id,
        )

    result = langgraph_spike.governed_langgraph_tool_call(
        context=langgraph_context,
        tool_call=langgraph_tool_call,
        tool_function=lambda: calls.append("called"),
        decision_client=decision_client,
    )

    assert calls == []
    assert result["status"] == expected_status
    assert result["decision"] == decision
    assert result["reason"] == "Tool call did not proceed."
    assert result["human_approval_id"] == human_approval_id
    if decision == "require_human_review":
        assert result["original_request_id"].startswith("langgraph:create_ticket:")
        assert result["action_ref"] == "ticket-draft-001"
        assert result["langgraph_node"] == "support_followup"


def test_langgraph_spike_builds_stable_resume_request(
    langgraph_spike: ModuleType,
    blocked_langgraph_tool_call: object,
) -> None:
    first_payload = langgraph_spike.build_runtime_resume_request(
        blocked_langgraph_tool_call,
    )
    second_payload = langgraph_spike.build_runtime_resume_request(
        blocked_langgraph_tool_call,
    )

    assert first_payload == second_payload
    assert first_payload["resume_id"].startswith(
        f"{blocked_langgraph_tool_call.original_request_id}:resume:"
    )
    assert first_payload["original_request_id"] == (
        blocked_langgraph_tool_call.original_request_id
    )
    assert first_payload["tool_name"] == "create_ticket"
    assert first_payload["action_ref"] == "ticket-draft-001"
    assert first_payload["human_approval_id"] == str(
        blocked_langgraph_tool_call.human_approval_id
    )
    assert first_payload["policy_decision_id"] == str(
        blocked_langgraph_tool_call.policy_decision_id
    )
    assert first_payload["metadata"] == {
        "graph_name": "support_agent",
        "ticket_category": "support",
        "langgraph_node": "support_followup",
    }


def test_langgraph_spike_resumes_tool_only_after_approved_allow(
    langgraph_spike: ModuleType,
    blocked_langgraph_tool_call: object,
) -> None:
    calls = []
    observed_payloads = []

    def resume_client(payload: dict[str, object]) -> dict[str, object]:
        observed_payloads.append(payload)
        return resume_response(
            blocked_langgraph_tool_call,
            decision="allow",
            proceed=True,
            human_approval_status="approved",
            reason="Human approval is approved and context matches.",
        )

    def original_tool(ticket_ref: str) -> dict[str, str]:
        calls.append(ticket_ref)
        return {"ticket_ref": ticket_ref, "status": "queued"}

    result = langgraph_spike.resume_langgraph_tool_call(
        blocked_call=blocked_langgraph_tool_call,
        tool_function=original_tool,
        resume_client=resume_client,
        args=("ticket-draft-001",),
    )

    assert calls == ["ticket-draft-001"]
    assert len(observed_payloads) == 1
    assert observed_payloads[0]["resume_id"].startswith(
        f"{blocked_langgraph_tool_call.original_request_id}:resume:"
    )
    assert result["status"] == "executed"
    assert result["decision"] == "allow"
    assert result["human_approval_status"] == "approved"


@pytest.mark.parametrize(
    ("decision", "human_approval_status", "expected_status"),
    [
        ("require_human_review", "pending", "blocked_pending_human_review"),
        ("deny", "rejected", "blocked_rejected"),
        ("deny", "cancelled", "blocked_cancelled"),
        ("deny", "expired", "blocked_expired"),
    ],
)
def test_langgraph_spike_resume_blocks_unresolved_or_denied_approval(
    langgraph_spike: ModuleType,
    blocked_langgraph_tool_call: object,
    decision: str,
    human_approval_status: str,
    expected_status: str,
) -> None:
    calls = []

    def resume_client(_payload: dict[str, object]) -> dict[str, object]:
        return resume_response(
            blocked_langgraph_tool_call,
            decision=decision,
            proceed=False,
            human_approval_status=human_approval_status,
            reason="Resume did not proceed.",
        )

    result = langgraph_spike.resume_langgraph_tool_call(
        blocked_call=blocked_langgraph_tool_call,
        tool_function=lambda: calls.append("called"),
        resume_client=resume_client,
    )

    assert calls == []
    assert result["status"] == expected_status
    assert result["decision"] == decision
    assert result["human_approval_status"] == human_approval_status
    assert result["human_approval_id"] == str(
        blocked_langgraph_tool_call.human_approval_id
    )


def test_langgraph_spike_resume_blocks_context_mismatch(
    langgraph_spike: ModuleType,
    blocked_langgraph_tool_call: object,
) -> None:
    calls = []

    result = langgraph_spike.resume_langgraph_tool_call(
        blocked_call=blocked_langgraph_tool_call,
        tool_function=lambda: calls.append("called"),
        resume_client=lambda _payload: {
            "detail": "Tool name does not match the original trace event."
        },
    )

    assert calls == []
    assert result == {
        "status": "blocked_context_mismatch",
        "decision": "context_mismatch",
        "reason": "Tool name does not match the original trace event.",
        "human_approval_id": str(blocked_langgraph_tool_call.human_approval_id),
    }


def decision_response(
    *,
    request_id: str,
    decision: str,
    proceed: bool,
    reason: str,
    human_approval_id: str | None = None,
) -> dict[str, object]:
    return {
        "request_id": request_id,
        "agent_id": "11111111-1111-4111-8111-111111111111",
        "run_id": "22222222-2222-4222-8222-222222222222",
        "tool_name": "create_ticket",
        "decision": decision,
        "proceed": proceed,
        "reason": reason,
        "trace_event_id": "33333333-3333-4333-8333-333333333333",
        "policy_decision_id": "66666666-6666-4666-8666-666666666666",
        "human_approval_id": human_approval_id,
    }


def resume_response(
    blocked_langgraph_tool_call: object,
    *,
    decision: str,
    proceed: bool,
    human_approval_status: str,
    reason: str,
) -> dict[str, object]:
    return {
        "resume_id": "resume-id",
        "original_request_id": blocked_langgraph_tool_call.original_request_id,
        "agent_id": str(blocked_langgraph_tool_call.context.agent_id),
        "run_id": str(blocked_langgraph_tool_call.context.run_id),
        "tool_name": blocked_langgraph_tool_call.tool_call.tool_name,
        "decision": decision,
        "proceed": proceed,
        "reason": reason,
        "human_approval_status": human_approval_status,
        "trace_event_id": "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
        "policy_decision_id": str(blocked_langgraph_tool_call.policy_decision_id),
        "human_approval_id": str(blocked_langgraph_tool_call.human_approval_id),
    }
