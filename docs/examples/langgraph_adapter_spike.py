"""LangGraph adapter spike for AGCP Runtime Gateway.

This is documentation-quality example code, not a production SDK. It does not
import LangGraph and does not replace LangGraph graph execution, state,
checkpoints, routing, or tools.

The intended LangGraph-side integration point is a wrapper around selected tools
before execution. A future integration could plug these helpers into a
LangGraph `@tool`, a ToolNode wrapper, or an application-specific tool registry.
The wrapped tool still runs inside the LangGraph application. AGCP only returns
governance decisions and records evidence.

Do not send raw prompts, raw tool inputs, raw tool outputs, credentials,
authorization headers, or private customer data to AGCP. Use safe summaries,
safe metadata, and stable application-owned references such as `action_ref`.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from hashlib import sha256
from typing import Any
from urllib import request as urllib_request
from uuid import UUID

SafeMetadataValue = str | int | float | bool | None
SafeMetadata = dict[str, SafeMetadataValue]
RuntimeRequest = dict[str, object]
RuntimeResponse = dict[str, object]
ToolCallable = Callable[..., object]
GatewayClient = Callable[[RuntimeRequest], RuntimeResponse]
AdapterResult = dict[str, object]

DEFAULT_TIMEOUT_SECONDS = 5.0


class LangGraphAdapterSpikeError(RuntimeError):
    """Raised when the spike cannot safely interpret gateway output."""


@dataclass(frozen=True)
class LangGraphRunContext:
    """Safe AGCP identifiers mapped from one LangGraph invocation/thread/run."""

    agent_id: UUID
    run_id: UUID
    correlation_id: str
    node_name: str
    mode: str = "enforcement"
    metadata: SafeMetadata = field(default_factory=dict)


@dataclass(frozen=True)
class LangGraphToolCall:
    """Safe description of a LangGraph tool call before execution.

    `action_ref` should be an application-owned id such as a job id, ticket id,
    or checkpoint reference. It must not contain raw prompts or raw tool
    payloads.
    """

    tool_name: str
    action_ref: str
    action_summary: str
    metadata: SafeMetadata = field(default_factory=dict)


@dataclass(frozen=True)
class BlockedLangGraphToolCall:
    """Safe references preserved when AGCP requires HumanApproval."""

    context: LangGraphRunContext
    tool_call: LangGraphToolCall
    original_request_id: str
    human_approval_id: UUID
    policy_decision_id: UUID


def governed_langgraph_tool_call(
    *,
    context: LangGraphRunContext,
    tool_call: LangGraphToolCall,
    tool_function: ToolCallable,
    decision_client: GatewayClient,
    args: tuple[object, ...] = (),
    kwargs: Mapping[str, object] | None = None,
) -> AdapterResult:
    """Wrap a LangGraph tool before execution.

    In a real LangGraph app, this function would be called inside the tool
    wrapper before delegating to the original tool implementation.
    """

    request_payload = build_runtime_decision_request(context, tool_call)
    decision_response = decision_client(request_payload)
    return handle_runtime_decision_response(
        decision_response,
        context=context,
        tool_call=tool_call,
        tool_function=tool_function,
        args=args,
        kwargs=kwargs or {},
    )


def resume_langgraph_tool_call(
    *,
    blocked_call: BlockedLangGraphToolCall,
    tool_function: ToolCallable,
    resume_client: GatewayClient,
    args: tuple[object, ...] = (),
    kwargs: Mapping[str, object] | None = None,
) -> AdapterResult:
    """Ask AGCP whether a previously blocked LangGraph tool may resume."""

    resume_payload = build_runtime_resume_request(blocked_call)
    resume_response = resume_client(resume_payload)
    return handle_runtime_resume_response(
        resume_response,
        blocked_call=blocked_call,
        tool_function=tool_function,
        args=args,
        kwargs=kwargs or {},
    )


def build_runtime_decision_request(
    context: LangGraphRunContext,
    tool_call: LangGraphToolCall,
) -> RuntimeRequest:
    """Build RuntimeToolCallDecisionRequest from safe LangGraph references."""

    return {
        "request_id": stable_request_id(context, tool_call),
        "agent_id": str(context.agent_id),
        "run_id": str(context.run_id),
        "correlation_id": context.correlation_id,
        "tool_name": tool_call.tool_name,
        "action_summary": tool_call.action_summary,
        "metadata": {
            **context.metadata,
            **tool_call.metadata,
            "langgraph_node": context.node_name,
            "action_ref": tool_call.action_ref,
        },
        "mode": context.mode,
    }


def build_runtime_resume_request(
    blocked_call: BlockedLangGraphToolCall,
) -> RuntimeRequest:
    """Build RuntimeToolCallResumeRequest from preserved safe references."""

    context = blocked_call.context
    tool_call = blocked_call.tool_call
    return {
        "resume_id": stable_resume_id(blocked_call),
        "original_request_id": blocked_call.original_request_id,
        "agent_id": str(context.agent_id),
        "run_id": str(context.run_id),
        "tool_name": tool_call.tool_name,
        "human_approval_id": str(blocked_call.human_approval_id),
        "policy_decision_id": str(blocked_call.policy_decision_id),
        "action_ref": tool_call.action_ref,
        "correlation_id": context.correlation_id,
        "metadata": {
            **context.metadata,
            **tool_call.metadata,
            "langgraph_node": context.node_name,
        },
    }


def stable_request_id(
    context: LangGraphRunContext,
    tool_call: LangGraphToolCall,
) -> str:
    """Stable idempotency key for one LangGraph tool attempt."""

    identity = "|".join(
        (
            str(context.agent_id),
            str(context.run_id),
            context.node_name,
            context.mode,
            tool_call.tool_name,
            tool_call.action_ref,
        )
    )
    digest = sha256(identity.encode("utf-8")).hexdigest()[:24]
    return f"langgraph:{tool_call.tool_name}:{digest}"


def stable_resume_id(blocked_call: BlockedLangGraphToolCall) -> str:
    """Stable idempotency key for one resume check."""

    context = blocked_call.context
    tool_call = blocked_call.tool_call
    identity = "|".join(
        (
            str(context.agent_id),
            str(context.run_id),
            blocked_call.original_request_id,
            tool_call.tool_name,
            tool_call.action_ref,
            str(blocked_call.human_approval_id),
            str(blocked_call.policy_decision_id),
        )
    )
    digest = sha256(identity.encode("utf-8")).hexdigest()[:16]
    return f"{blocked_call.original_request_id}:resume:{digest}"


def post_runtime_gateway_decision(
    *,
    base_url: str,
    payload: RuntimeRequest,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
) -> RuntimeResponse:
    """Call `POST /runtime/tool-calls/decision` with standard-library HTTP."""

    return _post_json(
        url=f"{base_url.rstrip('/')}/runtime/tool-calls/decision",
        payload=payload,
        timeout_seconds=timeout_seconds,
    )


def post_runtime_gateway_resume(
    *,
    base_url: str,
    payload: RuntimeRequest,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
) -> RuntimeResponse:
    """Call `POST /runtime/tool-calls/resume` with standard-library HTTP."""

    return _post_json(
        url=f"{base_url.rstrip('/')}/runtime/tool-calls/resume",
        payload=payload,
        timeout_seconds=timeout_seconds,
    )


def handle_runtime_decision_response(
    response: RuntimeResponse,
    *,
    context: LangGraphRunContext,
    tool_call: LangGraphToolCall,
    tool_function: ToolCallable,
    args: tuple[object, ...],
    kwargs: Mapping[str, object],
) -> AdapterResult:
    decision = _required_text(response, "decision")
    proceed = _required_bool(response, "proceed")

    if proceed:
        if decision != "allow":
            raise LangGraphAdapterSpikeError("Only allow may proceed.")
        return _executed_result(response, tool_call, tool_function, args, kwargs)

    if decision == "require_human_review":
        return {
            **_blocked_result(response, "blocked_pending_human_review"),
            "original_request_id": _required_text(response, "request_id"),
            "action_ref": tool_call.action_ref,
            "langgraph_node": context.node_name,
        }
    if decision == "deny":
        return _blocked_result(response, "blocked_denied")
    if decision == "not_applicable":
        return _blocked_result(response, "blocked_not_applicable")

    raise LangGraphAdapterSpikeError(f"Unsupported runtime decision: {decision}")


def handle_runtime_resume_response(
    response: RuntimeResponse,
    *,
    blocked_call: BlockedLangGraphToolCall,
    tool_function: ToolCallable,
    args: tuple[object, ...],
    kwargs: Mapping[str, object],
) -> AdapterResult:
    if "detail" in response and "decision" not in response:
        return {
            "status": "blocked_context_mismatch",
            "decision": "context_mismatch",
            "reason": _required_text(response, "detail"),
            "human_approval_id": str(blocked_call.human_approval_id),
        }

    decision = _required_text(response, "decision")
    proceed = _required_bool(response, "proceed")
    approval_status = _required_text(response, "human_approval_status")

    if proceed:
        if decision != "allow":
            raise LangGraphAdapterSpikeError("Only allow resume may proceed.")
        if approval_status != "approved":
            raise LangGraphAdapterSpikeError(
                "Resume allow requires approved human approval."
            )
        return _executed_result(
            response,
            blocked_call.tool_call,
            tool_function,
            args,
            kwargs,
            human_approval_status=approval_status,
        )

    if decision == "require_human_review" and approval_status == "pending":
        return _blocked_resume_result(response, "blocked_pending_human_review")
    if decision == "deny" and approval_status == "rejected":
        return _blocked_resume_result(response, "blocked_rejected")
    if decision == "deny" and approval_status == "cancelled":
        return _blocked_resume_result(response, "blocked_cancelled")
    if decision == "deny" and approval_status == "expired":
        return _blocked_resume_result(response, "blocked_expired")
    if decision == "not_applicable":
        return _blocked_resume_result(response, "blocked_not_applicable")

    raise LangGraphAdapterSpikeError(
        f"Unsupported resume decision/status: {decision}/{approval_status}"
    )


def _post_json(
    *,
    url: str,
    payload: RuntimeRequest,
    timeout_seconds: float,
) -> RuntimeResponse:
    body = json.dumps(payload).encode("utf-8")
    http_request = urllib_request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib_request.urlopen(http_request, timeout=timeout_seconds) as response:
        parsed_response = json.loads(response.read().decode("utf-8"))
    if not isinstance(parsed_response, dict):
        raise LangGraphAdapterSpikeError("Runtime Gateway returned a non-object.")
    return parsed_response


def _executed_result(
    response: RuntimeResponse,
    tool_call: LangGraphToolCall,
    tool_function: ToolCallable,
    args: tuple[object, ...],
    kwargs: Mapping[str, object],
    *,
    human_approval_status: str | None = None,
) -> AdapterResult:
    result: AdapterResult = {
        "status": "executed",
        "decision": "allow",
        "tool_name": tool_call.tool_name,
        "action_ref": tool_call.action_ref,
        "tool_result": tool_function(*args, **dict(kwargs)),
        "trace_event_id": response.get("trace_event_id"),
        "policy_decision_id": response.get("policy_decision_id"),
        "human_approval_id": response.get("human_approval_id"),
    }
    if human_approval_status is not None:
        result["human_approval_status"] = human_approval_status
    return result


def _blocked_result(response: RuntimeResponse, status: str) -> AdapterResult:
    return {
        "status": status,
        "decision": _required_text(response, "decision"),
        "reason": _required_text(response, "reason"),
        "trace_event_id": response.get("trace_event_id"),
        "policy_decision_id": response.get("policy_decision_id"),
        "human_approval_id": response.get("human_approval_id"),
    }


def _blocked_resume_result(response: RuntimeResponse, status: str) -> AdapterResult:
    return {
        **_blocked_result(response, status),
        "human_approval_status": _required_text(response, "human_approval_status"),
    }


def _required_text(payload: Mapping[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise LangGraphAdapterSpikeError(f"Gateway response missing {key}.")
    return value


def _required_bool(payload: Mapping[str, Any], key: str) -> bool:
    value = payload.get(key)
    if not isinstance(value, bool):
        raise LangGraphAdapterSpikeError(f"Gateway response missing {key}.")
    return value


def example_langgraph_tool(ticket_ref: str) -> dict[str, str]:
    """Placeholder for the original LangGraph tool implementation."""

    return {"ticket_ref": ticket_ref, "status": "queued"}
