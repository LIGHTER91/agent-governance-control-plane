"""Minimal governed tool-call wrapper example.

This file is intentionally dependency-free. It is not an SDK and does not import
LangGraph or any other agent framework. The example shows the shape an
application wrapper could take when calling the Agent Governance Control Plane
Runtime Gateway.

Modes:
- telemetry: observation-only; current integrations can use /telemetry/events.
- simulation: current Runtime Gateway mode; records what the decision would be.
- enforcement: future mode; integrations must honor proceed before acting.

The wrapper below honors `proceed` even in simulation so the control flow is easy
to reuse later, but simulation mode itself does not claim to block actions in
the platform.
"""

import json
from collections.abc import Callable, Mapping
from typing import Any
from urllib import request as urllib_request
from uuid import UUID

SafeMetadataValue = str | int | float | bool | None
SafeMetadata = dict[str, SafeMetadataValue]
RuntimeDecisionRequest = dict[str, object]
RuntimeDecisionResponse = dict[str, object]
ToolResult = dict[str, object]
DecisionClient = Callable[[RuntimeDecisionRequest], RuntimeDecisionResponse]
ToolCallable = Callable[[], object]


class RuntimeGatewayError(RuntimeError):
    """Raised when the Runtime Gateway response is not safe to act on."""


def build_runtime_tool_call_decision_request(
    *,
    request_id: str,
    agent_id: UUID,
    run_id: UUID,
    correlation_id: str,
    tool_name: str,
    action_summary: str,
    metadata: Mapping[str, SafeMetadataValue] | None = None,
    mode: str = "simulation",
) -> RuntimeDecisionRequest:
    return {
        "request_id": request_id,
        "agent_id": str(agent_id),
        "run_id": str(run_id),
        "correlation_id": correlation_id,
        "tool_name": tool_name,
        "action_summary": action_summary,
        "metadata": dict(metadata or {}),
        "mode": mode,
    }


def post_runtime_gateway_decision(
    *,
    base_url: str,
    payload: RuntimeDecisionRequest,
    timeout_seconds: float = 5.0,
) -> RuntimeDecisionResponse:
    """Call AGCP with only the Python standard library.

    Applications can replace this function with their own HTTP client. Do not
    include raw prompts, raw tool payloads, credentials, or private data in
    `payload`.
    """

    url = f"{base_url.rstrip('/')}/runtime/tool-calls/decision"
    body = json.dumps(payload).encode("utf-8")
    http_request = urllib_request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urllib_request.urlopen(http_request, timeout=timeout_seconds) as response:
        response_body = response.read().decode("utf-8")
    parsed_response = json.loads(response_body)
    if not isinstance(parsed_response, dict):
        raise RuntimeGatewayError("Runtime Gateway returned a non-object response.")
    return parsed_response


def run_governed_tool_call(
    *,
    decision_client: DecisionClient,
    tool: ToolCallable,
    request_payload: RuntimeDecisionRequest,
) -> ToolResult:
    """Call the Runtime Gateway and execute `tool` only when proceed is true."""

    decision_response = decision_client(request_payload)
    decision = _required_text(decision_response, "decision")
    proceed = decision_response.get("proceed")
    if not isinstance(proceed, bool):
        raise RuntimeGatewayError("Runtime Gateway response must include proceed.")

    if proceed:
        if decision != "allow":
            raise RuntimeGatewayError("Only an allow decision may proceed.")
        return {
            "status": "executed",
            "decision": decision,
            "tool_result": tool(),
            "trace_event_id": decision_response.get("trace_event_id"),
            "policy_decision_id": decision_response.get("policy_decision_id"),
        }

    return _blocked_tool_result(decision_response, decision)


def _blocked_tool_result(
    decision_response: RuntimeDecisionResponse,
    decision: str,
) -> ToolResult:
    reason = _required_text(decision_response, "reason")

    if decision == "deny":
        status = "denied"
    elif decision == "require_human_review":
        status = "pending_human_review"
    elif decision == "not_applicable":
        status = "not_applicable"
    else:
        raise RuntimeGatewayError(f"Unsupported runtime decision: {decision}")

    return {
        "status": status,
        "decision": decision,
        "reason": reason,
        "trace_event_id": decision_response.get("trace_event_id"),
        "policy_decision_id": decision_response.get("policy_decision_id"),
        "human_approval_id": decision_response.get("human_approval_id"),
    }


def _required_text(payload: Mapping[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise RuntimeGatewayError(f"Runtime Gateway response missing {key}.")
    return value


def example_tool_action() -> dict[str, str]:
    """A placeholder local tool action.

    Real integrations should keep raw tool inputs and outputs out of AGCP
    metadata. Send short summaries and stable references instead.
    """

    return {"ticket_status": "queued"}
