import importlib.util
from pathlib import Path
from types import ModuleType
from uuid import uuid4

import pytest


@pytest.fixture()
def wrapper_example() -> ModuleType:
    repo_root = Path(__file__).resolve().parents[3]
    example_path = repo_root / "docs" / "examples" / "runtime_tool_wrapper_example.py"
    spec = importlib.util.spec_from_file_location(
        "runtime_tool_wrapper_example",
        example_path,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_example_builds_safe_runtime_request(wrapper_example: ModuleType) -> None:
    agent_id = uuid4()
    run_id = uuid4()

    request_payload = wrapper_example.build_runtime_tool_call_decision_request(
        request_id="example-request-001",
        agent_id=agent_id,
        run_id=run_id,
        correlation_id="example-run-001",
        tool_name="create_ticket",
        action_summary="Create an internal support ticket.",
        metadata={"ticket_category": "support"},
    )

    assert request_payload == {
        "request_id": "example-request-001",
        "agent_id": str(agent_id),
        "run_id": str(run_id),
        "correlation_id": "example-run-001",
        "tool_name": "create_ticket",
        "action_summary": "Create an internal support ticket.",
        "metadata": {"ticket_category": "support"},
        "mode": "simulation",
    }

    enforcement_payload = wrapper_example.as_enforcement_request(request_payload)

    assert enforcement_payload == {
        **request_payload,
        "mode": "enforcement",
    }
    assert request_payload["mode"] == "simulation"


def test_simulation_wrapper_sends_simulation_mode(
    wrapper_example: ModuleType,
) -> None:
    observed_payloads = []

    def fake_decision_client(payload: dict[str, object]) -> dict[str, object]:
        observed_payloads.append(payload)
        return {
            "decision": "allow",
            "proceed": True,
            "trace_event_id": "33333333-3333-4333-8333-333333333333",
            "policy_decision_id": "66666666-6666-4666-8666-666666666666",
        }

    result = wrapper_example.run_simulated_tool_call(
        decision_client=fake_decision_client,
        tool=lambda: {"ticket_status": "queued"},
        request_payload={"request_id": "example-request-001", "mode": "enforcement"},
    )

    assert observed_payloads == [
        {"request_id": "example-request-001", "mode": "simulation"}
    ]
    assert result["status"] == "executed"


def test_wrapper_executes_tool_only_when_decision_allows(
    wrapper_example: ModuleType,
) -> None:
    calls = []

    def fake_decision_client(_payload: dict[str, object]) -> dict[str, object]:
        return {
            "decision": "allow",
            "proceed": True,
            "trace_event_id": "33333333-3333-4333-8333-333333333333",
            "policy_decision_id": "66666666-6666-4666-8666-666666666666",
        }

    def tool() -> dict[str, str]:
        calls.append("called")
        return {"ticket_status": "queued"}

    result = wrapper_example.run_governed_tool_call(
        decision_client=fake_decision_client,
        tool=tool,
        request_payload={"request_id": "example-request-001"},
    )

    assert calls == ["called"]
    assert result == {
        "status": "executed",
        "decision": "allow",
        "tool_result": {"ticket_status": "queued"},
        "trace_event_id": "33333333-3333-4333-8333-333333333333",
        "policy_decision_id": "66666666-6666-4666-8666-666666666666",
    }


def test_enforcement_wrapper_executes_tool_only_when_decision_allows(
    wrapper_example: ModuleType,
) -> None:
    calls = []
    observed_payloads = []

    def fake_decision_client(payload: dict[str, object]) -> dict[str, object]:
        observed_payloads.append(payload)
        return {
            "decision": "allow",
            "proceed": True,
            "trace_event_id": "33333333-3333-4333-8333-333333333333",
            "policy_decision_id": "66666666-6666-4666-8666-666666666666",
            "human_approval_id": None,
        }

    def tool() -> dict[str, str]:
        calls.append("called")
        return {"ticket_status": "queued"}

    result = wrapper_example.run_enforced_tool_call(
        decision_client=fake_decision_client,
        tool=tool,
        request_payload={"request_id": "example-request-001", "mode": "simulation"},
    )

    assert observed_payloads == [
        {"request_id": "example-request-001", "mode": "enforcement"}
    ]
    assert calls == ["called"]
    assert result["status"] == "executed"


@pytest.mark.parametrize(
    ("decision", "expected_status"),
    [
        ("deny", "blocked_denied"),
        ("require_human_review", "blocked_pending_human_review"),
        ("not_applicable", "blocked_not_applicable"),
    ],
)
def test_enforcement_wrapper_does_not_execute_tool_when_proceed_is_false(
    wrapper_example: ModuleType,
    decision: str,
    expected_status: str,
) -> None:
    calls = []

    def fake_decision_client(_payload: dict[str, object]) -> dict[str, object]:
        return {
            "decision": decision,
            "proceed": False,
            "reason": "Tool execution did not proceed.",
            "trace_event_id": "33333333-3333-4333-8333-333333333333",
            "policy_decision_id": "66666666-6666-4666-8666-666666666666",
            "human_approval_id": "77777777-7777-4777-8777-777777777777",
        }

    def tool() -> dict[str, str]:
        calls.append("called")
        return {"ticket_status": "queued"}

    result = wrapper_example.run_enforced_tool_call(
        decision_client=fake_decision_client,
        tool=tool,
        request_payload={"request_id": "example-request-001"},
    )

    assert calls == []
    assert result["status"] == expected_status
    assert result["decision"] == decision
    assert result["reason"] == "Tool execution did not proceed."
    if decision == "require_human_review":
        assert result["human_approval_id"] == "77777777-7777-4777-8777-777777777777"


@pytest.mark.parametrize(
    "gateway_error",
    [
        TimeoutError("gateway timed out"),
        OSError("connection failed"),
        pytest.param(
            None,
            id="runtime-gateway-error",
        ),
    ],
)
def test_enforcement_wrapper_blocks_on_gateway_error_or_timeout(
    wrapper_example: ModuleType,
    gateway_error: BaseException | None,
) -> None:
    calls = []

    def fake_decision_client(_payload: dict[str, object]) -> dict[str, object]:
        if gateway_error is None:
            raise wrapper_example.RuntimeGatewayError("malformed response")
        raise gateway_error

    def tool() -> dict[str, str]:
        calls.append("called")
        return {"ticket_status": "queued"}

    result = wrapper_example.run_enforced_tool_call(
        decision_client=fake_decision_client,
        tool=tool,
        request_payload={"request_id": "example-request-001"},
    )

    assert calls == []
    assert result["status"] == "blocked_gateway_error"
    assert result["decision"] == "gateway_error"
    assert result["reason"] == (
        "Runtime Gateway did not return a safe enforcement decision; "
        "tool was not executed."
    )
