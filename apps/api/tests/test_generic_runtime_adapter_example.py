import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from uuid import uuid4

import pytest


@pytest.fixture()
def adapter_example() -> ModuleType:
    repo_root = Path(__file__).resolve().parents[3]
    example_path = (
        repo_root / "docs" / "examples" / "generic_runtime_adapter_example.py"
    )
    spec = importlib.util.spec_from_file_location(
        "generic_runtime_adapter_example",
        example_path,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["generic_runtime_adapter_example"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def governed_action(adapter_example: ModuleType) -> object:
    return adapter_example.GovernedAction(
        agent_id=uuid4(),
        run_id=uuid4(),
        correlation_id="support-run-001",
        tool_name="create_ticket",
        action_ref="ticket-draft-001",
        action_summary="Create an internal support ticket.",
        metadata={"ticket_category": "support"},
        mode="enforcement",
    )


def test_adapter_builds_stable_request_id(
    adapter_example: ModuleType,
    governed_action: object,
) -> None:
    first_payload = adapter_example.build_runtime_decision_request(governed_action)
    second_payload = adapter_example.build_runtime_decision_request(governed_action)

    assert first_payload == second_payload
    assert first_payload["request_id"].startswith("runtime:create_ticket:")
    assert first_payload["tool_name"] == "create_ticket"
    assert first_payload["metadata"] == {"ticket_category": "support"}
    assert first_payload["mode"] == "enforcement"


def test_adapter_executes_tool_only_when_decision_allows(
    adapter_example: ModuleType,
    governed_action: object,
) -> None:
    calls = []
    observed_payloads = []

    def decision_client(payload: dict[str, object]) -> dict[str, object]:
        observed_payloads.append(payload)
        return {
            "decision": "allow",
            "proceed": True,
            "trace_event_id": "33333333-3333-4333-8333-333333333333",
            "policy_decision_id": "66666666-6666-4666-8666-666666666666",
            "human_approval_id": None,
        }

    def local_tool(ticket_ref: str) -> dict[str, str]:
        calls.append(ticket_ref)
        return {"ticket_ref": ticket_ref, "status": "queued"}

    adapter = adapter_example.GenericRuntimeAdapter(decision_client=decision_client)
    tool = adapter_example.RegisteredTool(
        name="create_ticket",
        function=local_tool,
        args=("ticket-draft-001",),
    )

    result = adapter.run(governed_action, tool)

    assert calls == ["ticket-draft-001"]
    assert len(observed_payloads) == 1
    assert result == {
        "status": "executed",
        "decision": "allow",
        "tool_name": "create_ticket",
        "tool_result": {"ticket_ref": "ticket-draft-001", "status": "queued"},
        "trace_event_id": "33333333-3333-4333-8333-333333333333",
        "policy_decision_id": "66666666-6666-4666-8666-666666666666",
        "human_approval_id": None,
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
def test_adapter_returns_blocked_statuses_without_executing_tool(
    adapter_example: ModuleType,
    governed_action: object,
    decision: str,
    expected_status: str,
    human_approval_id: str | None,
) -> None:
    calls = []

    def decision_client(_payload: dict[str, object]) -> dict[str, object]:
        return {
            "decision": decision,
            "proceed": False,
            "reason": "Tool execution did not proceed.",
            "trace_event_id": "33333333-3333-4333-8333-333333333333",
            "policy_decision_id": "66666666-6666-4666-8666-666666666666",
            "human_approval_id": human_approval_id,
        }

    def local_tool() -> dict[str, str]:
        calls.append("called")
        return {"status": "queued"}

    adapter = adapter_example.GenericRuntimeAdapter(decision_client=decision_client)
    tool = adapter_example.RegisteredTool(
        name="create_ticket",
        function=local_tool,
    )

    result = adapter.run(governed_action, tool)

    assert calls == []
    assert result["status"] == expected_status
    assert result["decision"] == decision
    assert result["reason"] == "Tool execution did not proceed."
    assert result["human_approval_id"] == human_approval_id


def test_adapter_retries_transient_gateway_failure_with_same_request(
    adapter_example: ModuleType,
    governed_action: object,
) -> None:
    observed_payloads = []

    def decision_client(payload: dict[str, object]) -> dict[str, object]:
        observed_payloads.append(dict(payload))
        if len(observed_payloads) == 1:
            raise TimeoutError("gateway timed out")
        return {
            "decision": "allow",
            "proceed": True,
            "trace_event_id": "33333333-3333-4333-8333-333333333333",
            "policy_decision_id": "66666666-6666-4666-8666-666666666666",
            "human_approval_id": None,
        }

    adapter = adapter_example.GenericRuntimeAdapter(
        decision_client=decision_client,
        max_attempts=2,
    )
    tool = adapter_example.RegisteredTool(
        name="create_ticket",
        function=lambda: {"status": "queued"},
    )

    result = adapter.run(governed_action, tool)

    assert result["status"] == "executed"
    assert len(observed_payloads) == 2
    assert observed_payloads[0]["request_id"] == observed_payloads[1]["request_id"]
    assert observed_payloads[0] == observed_payloads[1]


def test_adapter_blocks_after_gateway_failures_without_executing_tool(
    adapter_example: ModuleType,
    governed_action: object,
) -> None:
    calls = []
    attempts = []

    def decision_client(payload: dict[str, object]) -> dict[str, object]:
        attempts.append(payload)
        raise TimeoutError("gateway timed out")

    def local_tool() -> dict[str, str]:
        calls.append("called")
        return {"status": "queued"}

    adapter = adapter_example.GenericRuntimeAdapter(
        decision_client=decision_client,
        max_attempts=2,
    )
    tool = adapter_example.RegisteredTool(
        name="create_ticket",
        function=local_tool,
    )

    result = adapter.run(governed_action, tool)

    assert len(attempts) == 2
    assert calls == []
    assert result == {
        "status": "blocked_gateway_error",
        "decision": "gateway_error",
        "reason": (
            "Runtime Gateway did not return a decision after retry; "
            "tool was not executed."
        ),
        "human_approval_id": None,
    }


def test_adapter_blocks_on_unsafe_gateway_response_without_executing_tool(
    adapter_example: ModuleType,
    governed_action: object,
) -> None:
    calls = []

    def decision_client(_payload: dict[str, object]) -> dict[str, object]:
        return {"decision": "deny"}

    def local_tool() -> dict[str, str]:
        calls.append("called")
        return {"status": "queued"}

    adapter = adapter_example.GenericRuntimeAdapter(decision_client=decision_client)
    tool = adapter_example.RegisteredTool(
        name="create_ticket",
        function=local_tool,
    )

    result = adapter.run(governed_action, tool)

    assert calls == []
    assert result["status"] == "blocked_gateway_error"
    assert result["decision"] == "gateway_error"
    assert result["human_approval_id"] is None
    assert result["reason"] == (
        "Runtime Gateway response was not safe to act on; tool was not executed. "
        "Error: Runtime Gateway response must include proceed."
    )


def test_adapter_rejects_tool_name_mismatch(
    adapter_example: ModuleType,
    governed_action: object,
) -> None:
    adapter = adapter_example.GenericRuntimeAdapter(
        decision_client=lambda _payload: {"decision": "allow", "proceed": True},
    )
    tool = adapter_example.RegisteredTool(
        name="send_email",
        function=lambda: {"status": "queued"},
    )

    with pytest.raises(
        adapter_example.RuntimeAdapterError,
        match="Governed action tool_name must match tool.",
    ):
        adapter.run(governed_action, tool)
