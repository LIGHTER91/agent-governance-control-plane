"""Generic Runtime Gateway adapter example.

This file is documentation-quality example code, not a production SDK. It uses
only the Python standard library and does not import any agent framework.

The adapter demonstrates how an application could wrap arbitrary local tool
functions with the Agent Governance Control Plane Runtime Gateway:

1. Build a stable `request_id` for one attempted governed action.
2. Call `POST /runtime/tool-calls/decision`.
3. Retry transient gateway failures with the same idempotency payload.
4. Execute the local tool only when the gateway returns `decision = "allow"`
   and `proceed = true`.
5. Return blocked statuses for deny, human review, not applicable, and gateway
   errors.
6. Later, build a stable `resume_id` and call
   `POST /runtime/tool-calls/resume` before executing a previously blocked
   action after human review.

Do not send raw prompts, raw tool inputs, raw tool outputs, credentials, tokens,
authorization headers, or private customer data to AGCP. Use safe summaries,
safe metadata, and stable application-owned references instead.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from hashlib import sha256
from typing import Any
from urllib import error as urllib_error
from urllib import request as urllib_request
from uuid import UUID

SafeMetadataValue = str | int | float | bool | None
SafeMetadata = dict[str, SafeMetadataValue]
RuntimeDecisionRequest = dict[str, object]
RuntimeDecisionResponse = dict[str, object]
RuntimeResumeRequest = dict[str, object]
RuntimeResumeResponse = dict[str, object]
AdapterResult = dict[str, object]
ToolCallable = Callable[..., object]
DecisionClient = Callable[[RuntimeDecisionRequest], RuntimeDecisionResponse]
ResumeClient = Callable[[RuntimeResumeRequest], RuntimeResumeResponse]

DEFAULT_TIMEOUT_SECONDS = 5.0
DEFAULT_MAX_ATTEMPTS = 2


class RuntimeAdapterError(RuntimeError):
    """Raised when the adapter cannot safely interpret gateway output."""


@dataclass(frozen=True)
class GovernedAction:
    """A safe description of one attempted governed action.

    `action_ref` is an application-owned stable reference, such as an internal
    job id or task id. It must not contain raw prompts, credentials, private
    customer data, or raw tool payloads.
    """

    agent_id: UUID
    run_id: UUID
    correlation_id: str
    tool_name: str
    action_ref: str
    action_summary: str
    metadata: SafeMetadata = field(default_factory=dict)
    mode: str = "enforcement"


@dataclass(frozen=True)
class RegisteredTool:
    """A local callable plus safe execution arguments owned by the application."""

    name: str
    function: ToolCallable
    args: tuple[object, ...] = ()
    kwargs: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class BlockedToolCall:
    """Safe references needed to resume a previously blocked action.

    The wrapper should keep only references and governance IDs. It should not
    store or send raw prompts, raw tool inputs, raw tool outputs, credentials, or
    authorization headers in this structure.
    """

    agent_id: UUID
    run_id: UUID
    correlation_id: str
    tool_name: str
    action_ref: str
    original_request_id: str
    human_approval_id: UUID
    policy_decision_id: UUID
    metadata: SafeMetadata = field(default_factory=dict)


class GenericRuntimeAdapter:
    """Reusable adapter shape for local tool functions.

    The adapter does not execute remote systems by itself. It wraps local
    callables supplied by the application and asks AGCP whether a governed action
    may proceed before calling them.
    """

    def __init__(
        self,
        *,
        decision_client: DecisionClient,
        max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    ) -> None:
        if max_attempts < 1:
            raise ValueError("max_attempts must be at least 1.")
        self._decision_client = decision_client
        self._max_attempts = max_attempts

    def run(self, action: GovernedAction, tool: RegisteredTool) -> AdapterResult:
        if action.tool_name != tool.name:
            raise RuntimeAdapterError("Governed action tool_name must match tool.")

        request_payload = build_runtime_decision_request(action)
        try:
            decision_response = self._call_gateway_with_retries(request_payload)
        except RuntimeAdapterError as exc:
            return _blocked_gateway_error(
                reason=(
                    "Runtime Gateway response was not safe to act on; "
                    f"tool was not executed. Error: {exc}"
                )
            )
        if decision_response is None:
            return _blocked_gateway_error(
                reason=(
                    "Runtime Gateway did not return a decision after retry; "
                    "tool was not executed."
                )
            )

        try:
            return _handle_decision_response(decision_response, tool)
        except RuntimeAdapterError as exc:
            return _blocked_gateway_error(
                reason=(
                    "Runtime Gateway response was not safe to act on; "
                    f"tool was not executed. Error: {exc}"
                )
            )

    def _call_gateway_with_retries(
        self,
        request_payload: RuntimeDecisionRequest,
    ) -> RuntimeDecisionResponse | None:
        """Retry transient gateway failures with the same stable request_id."""

        for attempt_number in range(1, self._max_attempts + 1):
            try:
                return self._decision_client(request_payload)
            except TRANSIENT_GATEWAY_ERRORS:
                if attempt_number == self._max_attempts:
                    return None
        return None


def run_resumed_tool_call(
    *,
    blocked_call: BlockedToolCall,
    tool: RegisteredTool,
    resume_client: ResumeClient,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
) -> AdapterResult:
    """Resume a previously blocked local tool call after human review.

    The resume endpoint still does not execute tools. It only tells this wrapper
    whether the original blocked action may now proceed. The wrapper executes
    the local tool only for `decision = "allow"` and `proceed = true`.
    """

    if blocked_call.tool_name != tool.name:
        raise RuntimeAdapterError("Blocked tool_call tool_name must match tool.")
    if max_attempts < 1:
        raise ValueError("max_attempts must be at least 1.")

    resume_payload = build_runtime_resume_request(blocked_call)
    try:
        resume_response = _call_gateway_with_retries(
            resume_client,
            resume_payload,
            max_attempts=max_attempts,
        )
    except RuntimeAdapterError as exc:
        return _blocked_gateway_error(
            reason=(
                "Runtime Gateway resume response was not safe to act on; "
                f"tool was not executed. Error: {exc}"
            )
        )
    if resume_response is None:
        return _blocked_gateway_error(
            reason=(
                "Runtime Gateway did not return a resume decision after retry; "
                "tool was not executed."
            )
        )

    try:
        return _handle_resume_response(resume_response, tool)
    except RuntimeAdapterError as exc:
        return _blocked_gateway_error(
            reason=(
                "Runtime Gateway resume response was not safe to act on; "
                f"tool was not executed. Error: {exc}"
            )
        )


TRANSIENT_GATEWAY_ERRORS = (
    TimeoutError,
    OSError,
    urllib_error.URLError,
)


def build_runtime_decision_request(action: GovernedAction) -> RuntimeDecisionRequest:
    """Build the Runtime Gateway request for one governed action."""

    return {
        "request_id": stable_request_id(action),
        "agent_id": str(action.agent_id),
        "run_id": str(action.run_id),
        "correlation_id": action.correlation_id,
        "tool_name": action.tool_name,
        "action_summary": action.action_summary,
        "metadata": dict(action.metadata),
        "mode": action.mode,
    }


def build_runtime_resume_request(blocked_call: BlockedToolCall) -> RuntimeResumeRequest:
    """Build a safe resume request for a previously blocked action."""

    return {
        "resume_id": stable_resume_id(blocked_call),
        "original_request_id": blocked_call.original_request_id,
        "agent_id": str(blocked_call.agent_id),
        "run_id": str(blocked_call.run_id),
        "tool_name": blocked_call.tool_name,
        "human_approval_id": str(blocked_call.human_approval_id),
        "policy_decision_id": str(blocked_call.policy_decision_id),
        "action_ref": blocked_call.action_ref,
        "correlation_id": blocked_call.correlation_id,
        "metadata": dict(blocked_call.metadata),
    }


def stable_request_id(action: GovernedAction) -> str:
    """Create a stable idempotency key for one attempted action.

    The key intentionally uses `action_ref`, not raw tool inputs. The same
    attempted action should reuse the same `action_ref`; a materially different
    action should use a new one.
    """

    request_identity = "|".join(
        (
            str(action.agent_id),
            str(action.run_id),
            action.tool_name,
            action.action_ref,
            action.mode,
        )
    )
    digest = sha256(request_identity.encode("utf-8")).hexdigest()[:24]
    return f"runtime:{action.tool_name}:{digest}"


def stable_resume_id(blocked_call: BlockedToolCall) -> str:
    """Create a stable idempotency key for one resume attempt.

    The key preserves the original request ID and uses `action_ref`, not raw
    tool payloads. Retries of the same resume check should reuse this value.
    """

    resume_identity = "|".join(
        (
            str(blocked_call.agent_id),
            str(blocked_call.run_id),
            blocked_call.original_request_id,
            blocked_call.tool_name,
            blocked_call.action_ref,
            str(blocked_call.human_approval_id),
            str(blocked_call.policy_decision_id),
        )
    )
    digest = sha256(resume_identity.encode("utf-8")).hexdigest()[:16]
    return f"{blocked_call.original_request_id}:resume:{digest}"


def post_runtime_gateway_decision(
    *,
    base_url: str,
    payload: RuntimeDecisionRequest,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
) -> RuntimeDecisionResponse:
    """Call the Runtime Gateway with only the Python standard library.

    Tests for this example use fake decision clients and do not make network
    calls. Applications can replace this function with their own HTTP client.
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
        raise RuntimeAdapterError("Runtime Gateway returned a non-object response.")
    return parsed_response


def post_runtime_gateway_resume(
    *,
    base_url: str,
    payload: RuntimeResumeRequest,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
) -> RuntimeResumeResponse:
    """Call the Runtime Gateway resume endpoint with standard-library HTTP."""

    url = f"{base_url.rstrip('/')}/runtime/tool-calls/resume"
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
        raise RuntimeAdapterError("Runtime Gateway returned a non-object response.")
    return parsed_response


def _call_gateway_with_retries(
    client: Callable[[dict[str, object]], dict[str, object]],
    payload: dict[str, object],
    *,
    max_attempts: int,
) -> dict[str, object] | None:
    for attempt_number in range(1, max_attempts + 1):
        try:
            return client(payload)
        except TRANSIENT_GATEWAY_ERRORS:
            if attempt_number == max_attempts:
                return None
    return None


def _handle_decision_response(
    decision_response: RuntimeDecisionResponse,
    tool: RegisteredTool,
) -> AdapterResult:
    decision = _required_text(decision_response, "decision")
    proceed = decision_response.get("proceed")
    if not isinstance(proceed, bool):
        raise RuntimeAdapterError("Runtime Gateway response must include proceed.")

    if proceed:
        if decision != "allow":
            raise RuntimeAdapterError("Only an allow decision may proceed.")
        return {
            "status": "executed",
            "decision": decision,
            "tool_name": tool.name,
            "tool_result": tool.function(*tool.args, **dict(tool.kwargs)),
            "trace_event_id": decision_response.get("trace_event_id"),
            "policy_decision_id": decision_response.get("policy_decision_id"),
            "human_approval_id": decision_response.get("human_approval_id"),
        }

    return _blocked_result(decision_response, decision)


def _handle_resume_response(
    resume_response: RuntimeResumeResponse,
    tool: RegisteredTool,
) -> AdapterResult:
    if "detail" in resume_response and "decision" not in resume_response:
        detail = _required_text(resume_response, "detail")
        return {
            "status": "blocked_context_mismatch",
            "decision": "context_mismatch",
            "reason": detail,
            "human_approval_id": resume_response.get("human_approval_id"),
        }

    decision = _required_text(resume_response, "decision")
    proceed = resume_response.get("proceed")
    if not isinstance(proceed, bool):
        raise RuntimeAdapterError(
            "Runtime Gateway resume response must include proceed."
        )

    approval_status = _required_text(resume_response, "human_approval_status")
    if proceed:
        if decision != "allow":
            raise RuntimeAdapterError("Only an allow resume decision may proceed.")
        if approval_status != "approved":
            raise RuntimeAdapterError("Resume allow requires approved human approval.")
        return {
            "status": "executed",
            "decision": decision,
            "human_approval_status": approval_status,
            "tool_name": tool.name,
            "tool_result": tool.function(*tool.args, **dict(tool.kwargs)),
            "trace_event_id": resume_response.get("trace_event_id"),
            "policy_decision_id": resume_response.get("policy_decision_id"),
            "human_approval_id": resume_response.get("human_approval_id"),
        }

    return _blocked_resume_result(
        resume_response,
        decision=decision,
        approval_status=approval_status,
    )


def _blocked_result(
    decision_response: RuntimeDecisionResponse,
    decision: str,
) -> AdapterResult:
    reason = _required_text(decision_response, "reason")

    if decision == "deny":
        status = "blocked_denied"
    elif decision == "require_human_review":
        status = "blocked_pending_human_review"
    elif decision == "not_applicable":
        status = "blocked_not_applicable"
    else:
        raise RuntimeAdapterError(f"Unsupported runtime decision: {decision}")

    return {
        "status": status,
        "decision": decision,
        "reason": reason,
        "trace_event_id": decision_response.get("trace_event_id"),
        "policy_decision_id": decision_response.get("policy_decision_id"),
        "human_approval_id": decision_response.get("human_approval_id"),
    }


def _blocked_resume_result(
    resume_response: RuntimeResumeResponse,
    *,
    decision: str,
    approval_status: str,
) -> AdapterResult:
    reason = _required_text(resume_response, "reason")
    if decision == "require_human_review" and approval_status == "pending":
        status = "blocked_pending_human_review"
    elif decision == "deny" and approval_status == "rejected":
        status = "blocked_rejected"
    elif decision == "deny" and approval_status == "cancelled":
        status = "blocked_cancelled"
    elif decision == "deny" and approval_status == "expired":
        status = "blocked_expired"
    elif decision == "deny":
        status = "blocked_denied"
    elif decision == "not_applicable":
        status = "blocked_not_applicable"
    else:
        raise RuntimeAdapterError(
            f"Unsupported resume decision/status: {decision}/{approval_status}"
        )

    return {
        "status": status,
        "decision": decision,
        "human_approval_status": approval_status,
        "reason": reason,
        "trace_event_id": resume_response.get("trace_event_id"),
        "policy_decision_id": resume_response.get("policy_decision_id"),
        "human_approval_id": resume_response.get("human_approval_id"),
    }


def _blocked_gateway_error(*, reason: str) -> AdapterResult:
    return {
        "status": "blocked_gateway_error",
        "decision": "gateway_error",
        "reason": reason,
        "human_approval_id": None,
    }


def _required_text(payload: Mapping[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise RuntimeAdapterError(f"Runtime Gateway response missing {key}.")
    return value


def example_local_tool(ticket_ref: str) -> dict[str, str]:
    """Placeholder local tool.

    The local application owns real tool execution. AGCP receives safe summaries
    and references; it does not receive raw tool payloads.
    """

    return {"ticket_ref": ticket_ref, "status": "queued"}
