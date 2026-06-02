"""Dependency-free LangGraph-style helper for AGCP Runtime Gateway calls.

This module is intentionally small and framework-free. It demonstrates the
boundary where a LangGraph caller can ask AGCP for a Runtime Gateway decision
before the caller executes a local tool. AGCP never executes the tool here.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any
from urllib import error as urllib_error
from urllib import request as urllib_request

JsonObject = dict[str, Any]
SafeMetadataValue = str | int | float | bool | None
SafeMetadata = dict[str, SafeMetadataValue]
Transport = Callable[[str, JsonObject, Mapping[str, str], float], JsonObject]
ToolCallable = Callable[..., object]

DECISION_ENDPOINT = "/runtime/tool-calls/decision"
RESUME_ENDPOINT = "/runtime/tool-calls/resume"
SERVICE_ACTOR_API_KEY_HEADER = "X-AGCP-API-Key"

UNSAFE_CONTEXT_KEY_PARTS = (
    "access_token",
    "api_key",
    "authorization",
    "chunk",
    "chunks",
    "credential",
    "document_content",
    "password",
    "payload",
    "prompt",
    "private_customer_data",
    "raw_content",
    "raw_payload",
    "raw_prompt",
    "refresh_token",
    "source_content",
    "secret",
    "token",
)


class AGCPHelperError(Exception):
    """Base error for the LangGraph helper spike."""


class AGCPResponseError(AGCPHelperError):
    """Raised when AGCP returns an invalid or failed response."""


class UnsafeContextError(AGCPHelperError):
    """Raised when helper metadata appears to contain unsafe context."""


@dataclass(frozen=True)
class Decision:
    """Runtime Gateway decision returned before a local tool call."""

    request_id: str
    agent_id: str
    run_id: str
    tool_name: str
    decision: str
    proceed: bool
    reason: str
    trace_event_id: str | None = None
    policy_decision_id: str | None = None
    human_approval_id: str | None = None
    raw_response: JsonObject = field(default_factory=dict)

    @property
    def branch(self) -> str:
        """Return the explicit caller branch for this decision."""

        return decision_to_branch(self)


@dataclass(frozen=True)
class ResumeDecision:
    """Runtime Gateway decision returned for a human-approval resume check."""

    resume_id: str
    original_request_id: str
    agent_id: str
    run_id: str
    tool_name: str
    decision: str
    proceed: bool
    reason: str
    human_approval_status: str
    trace_event_id: str | None = None
    policy_decision_id: str | None = None
    human_approval_id: str | None = None
    raw_response: JsonObject = field(default_factory=dict)

    @property
    def branch(self) -> str:
        """Return the explicit caller branch for this resume decision."""

        if self.proceed and self.decision == "allow":
            return "allowed"
        if self.human_approval_status == "approved":
            return decision_to_branch(self)
        return f"approval_{self.human_approval_status}"


@dataclass(frozen=True)
class GovernedToolResult:
    """Result of a caller-owned tool wrapped by a Runtime Gateway decision."""

    decision: Decision
    branch: str
    tool_executed: bool
    tool_result: object | None = None


class AGCPClient:
    """Small standard-library Runtime Gateway client for helper examples."""

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str | None = None,
        timeout_seconds: float = 5.0,
        transport: Transport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds
        self._transport = transport or _stdlib_json_transport

    def decide_tool_call(
        self,
        *,
        agent_id: str,
        run_id: str,
        request_id: str,
        tool_name: str,
        action_summary: str | None = None,
        correlation_id: str | None = None,
        mode: str = "enforcement",
        action_type: str | None = None,
        capability_id: str | None = None,
        source_ids: Sequence[str] | None = None,
        model_id: str | None = None,
        purpose: str | None = None,
        environment: str | None = None,
        risk_level: str | None = None,
        metadata: Mapping[str, object] | None = None,
    ) -> Decision:
        """Ask AGCP whether the caller should execute a local tool."""

        payload = build_decision_payload(
            agent_id=agent_id,
            run_id=run_id,
            request_id=request_id,
            tool_name=tool_name,
            action_summary=action_summary,
            correlation_id=correlation_id,
            mode=mode,
            action_type=action_type,
            capability_id=capability_id,
            source_ids=source_ids,
            model_id=model_id,
            purpose=purpose,
            environment=environment,
            risk_level=risk_level,
            metadata=metadata,
        )
        response = self._post_json(DECISION_ENDPOINT, payload)
        return _decision_from_response(response)

    def resume_after_approval(
        self,
        *,
        resume_id: str,
        original_request_id: str,
        agent_id: str,
        run_id: str,
        tool_name: str,
        human_approval_id: str,
        policy_decision_id: str,
        action_ref: str,
        correlation_id: str,
        metadata: Mapping[str, object] | None = None,
    ) -> ResumeDecision:
        """Ask AGCP whether a human-reviewed tool call may resume."""

        payload = build_resume_payload(
            resume_id=resume_id,
            original_request_id=original_request_id,
            agent_id=agent_id,
            run_id=run_id,
            tool_name=tool_name,
            human_approval_id=human_approval_id,
            policy_decision_id=policy_decision_id,
            action_ref=action_ref,
            correlation_id=correlation_id,
            metadata=metadata,
        )
        response = self._post_json(RESUME_ENDPOINT, payload)
        return _resume_decision_from_response(response)

    def _post_json(self, path: str, payload: JsonObject) -> JsonObject:
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if self.api_key is not None:
            headers[SERVICE_ACTOR_API_KEY_HEADER] = self.api_key

        return self._transport(
            f"{self.base_url}{path}",
            payload,
            headers,
            self.timeout_seconds,
        )


def governed_tool_call(
    *,
    client: AGCPClient,
    tool: ToolCallable,
    agent_id: str,
    run_id: str,
    request_id: str,
    tool_name: str,
    action_summary: str | None = None,
    correlation_id: str | None = None,
    mode: str = "enforcement",
    action_type: str | None = None,
    capability_id: str | None = None,
    source_ids: Sequence[str] | None = None,
    model_id: str | None = None,
    purpose: str | None = None,
    environment: str | None = None,
    risk_level: str | None = None,
    metadata: Mapping[str, object] | None = None,
    tool_args: Sequence[object] | None = None,
    tool_kwargs: Mapping[str, object] | None = None,
) -> GovernedToolResult:
    """Call AGCP before the caller-owned tool and branch explicitly.

    The helper executes the local callable only when AGCP returns
    ``decision='allow'`` and ``proceed=True``. All other outcomes are returned
    to the caller so the LangGraph flow can stop, pause, or branch.
    """

    decision = client.decide_tool_call(
        agent_id=agent_id,
        run_id=run_id,
        request_id=request_id,
        tool_name=tool_name,
        action_summary=action_summary,
        correlation_id=correlation_id,
        mode=mode,
        action_type=action_type,
        capability_id=capability_id,
        source_ids=source_ids,
        model_id=model_id,
        purpose=purpose,
        environment=environment,
        risk_level=risk_level,
        metadata=metadata,
    )
    branch = decision_to_branch(decision)
    if branch != "allowed":
        return GovernedToolResult(
            decision=decision,
            branch=branch,
            tool_executed=False,
        )

    result = tool(*(tool_args or ()), **dict(tool_kwargs or {}))
    return GovernedToolResult(
        decision=decision,
        branch=branch,
        tool_executed=True,
        tool_result=result,
    )


def decision_to_branch(decision: Decision | ResumeDecision | str) -> str:
    """Map a Runtime Gateway decision to an explicit caller branch."""

    decision_value = decision if isinstance(decision, str) else decision.decision
    proceed = False if isinstance(decision, str) else decision.proceed

    if decision_value == "allow" and proceed:
        return "allowed"
    if decision_value == "deny":
        return "denied"
    if decision_value == "require_human_review":
        return "requires_review"
    if decision_value == "not_applicable":
        return "not_applicable"
    raise AGCPResponseError(
        "Runtime Gateway response did not map to a safe caller branch."
    )


def resume_after_approval(
    *,
    client: AGCPClient,
    resume_id: str,
    original_request_id: str,
    agent_id: str,
    run_id: str,
    tool_name: str,
    human_approval_id: str,
    policy_decision_id: str,
    action_ref: str,
    correlation_id: str,
    metadata: Mapping[str, object] | None = None,
) -> ResumeDecision:
    """Call the Runtime Gateway resume endpoint without executing a tool."""

    return client.resume_after_approval(
        resume_id=resume_id,
        original_request_id=original_request_id,
        agent_id=agent_id,
        run_id=run_id,
        tool_name=tool_name,
        human_approval_id=human_approval_id,
        policy_decision_id=policy_decision_id,
        action_ref=action_ref,
        correlation_id=correlation_id,
        metadata=metadata,
    )


def build_decision_payload(
    *,
    agent_id: str,
    run_id: str,
    request_id: str,
    tool_name: str,
    action_summary: str | None = None,
    correlation_id: str | None = None,
    mode: str = "enforcement",
    action_type: str | None = None,
    capability_id: str | None = None,
    source_ids: Sequence[str] | None = None,
    model_id: str | None = None,
    purpose: str | None = None,
    environment: str | None = None,
    risk_level: str | None = None,
    metadata: Mapping[str, object] | None = None,
) -> JsonObject:
    """Build a safe Runtime Gateway decision payload."""

    safe_metadata = _safe_metadata(metadata)
    if environment is not None:
        safe_metadata["environment"] = _safe_text("environment", environment)
    if risk_level is not None:
        safe_metadata["risk_level"] = _safe_text("risk_level", risk_level)

    payload: JsonObject = {
        "request_id": _safe_text("request_id", request_id),
        "agent_id": _safe_text("agent_id", agent_id),
        "run_id": _safe_text("run_id", run_id),
        "correlation_id": _safe_text("correlation_id", correlation_id or run_id),
        "tool_name": _safe_text("tool_name", tool_name),
        "action_summary": _safe_text(
            "action_summary",
            action_summary or f"Call {tool_name}.",
        ),
        "metadata": safe_metadata,
        "mode": _safe_text("mode", mode),
    }

    _add_optional_text(payload, "action_type", action_type)
    _add_optional_text(payload, "capability_id", capability_id)
    _add_optional_text(payload, "model_id", model_id)
    _add_optional_text(payload, "purpose", purpose)
    if source_ids:
        payload["source_ids"] = [_safe_text("source_id", item) for item in source_ids]

    return payload


def build_resume_payload(
    *,
    resume_id: str,
    original_request_id: str,
    agent_id: str,
    run_id: str,
    tool_name: str,
    human_approval_id: str,
    policy_decision_id: str,
    action_ref: str,
    correlation_id: str,
    metadata: Mapping[str, object] | None = None,
) -> JsonObject:
    """Build a safe Runtime Gateway resume payload."""

    return {
        "resume_id": _safe_text("resume_id", resume_id),
        "original_request_id": _safe_text(
            "original_request_id",
            original_request_id,
        ),
        "agent_id": _safe_text("agent_id", agent_id),
        "run_id": _safe_text("run_id", run_id),
        "tool_name": _safe_text("tool_name", tool_name),
        "human_approval_id": _safe_text("human_approval_id", human_approval_id),
        "policy_decision_id": _safe_text("policy_decision_id", policy_decision_id),
        "action_ref": _safe_text("action_ref", action_ref),
        "correlation_id": _safe_text("correlation_id", correlation_id),
        "metadata": _safe_metadata(metadata),
    }


def _stdlib_json_transport(
    url: str,
    payload: JsonObject,
    headers: Mapping[str, str],
    timeout_seconds: float,
) -> JsonObject:
    data = json.dumps(payload).encode("utf-8")
    request = urllib_request.Request(
        url,
        data=data,
        headers=dict(headers),
        method="POST",
    )
    try:
        with urllib_request.urlopen(request, timeout=timeout_seconds) as response:
            body = response.read().decode("utf-8")
    except urllib_error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise AGCPResponseError(f"AGCP request failed with HTTP {exc.code}.") from exc
    except urllib_error.URLError as exc:
        raise AGCPResponseError(
            "AGCP request failed before receiving a response."
        ) from exc

    if not body:
        return {}
    try:
        parsed = json.loads(body)
    except json.JSONDecodeError as exc:
        raise AGCPResponseError("AGCP returned malformed JSON.") from exc
    if not isinstance(parsed, dict):
        raise AGCPResponseError("AGCP returned a non-object JSON response.")
    return parsed


def _decision_from_response(response: Mapping[str, object]) -> Decision:
    return Decision(
        request_id=_response_text(response, "request_id"),
        agent_id=_response_text(response, "agent_id"),
        run_id=_response_text(response, "run_id"),
        tool_name=_response_text(response, "tool_name"),
        decision=_response_text(response, "decision"),
        proceed=_response_bool(response, "proceed"),
        reason=_response_text(response, "reason"),
        trace_event_id=_optional_response_text(response, "trace_event_id"),
        policy_decision_id=_optional_response_text(response, "policy_decision_id"),
        human_approval_id=_optional_response_text(response, "human_approval_id"),
        raw_response=dict(response),
    )


def _resume_decision_from_response(response: Mapping[str, object]) -> ResumeDecision:
    return ResumeDecision(
        resume_id=_response_text(response, "resume_id"),
        original_request_id=_response_text(response, "original_request_id"),
        agent_id=_response_text(response, "agent_id"),
        run_id=_response_text(response, "run_id"),
        tool_name=_response_text(response, "tool_name"),
        decision=_response_text(response, "decision"),
        proceed=_response_bool(response, "proceed"),
        reason=_response_text(response, "reason"),
        human_approval_status=_response_text(response, "human_approval_status"),
        trace_event_id=_optional_response_text(response, "trace_event_id"),
        policy_decision_id=_optional_response_text(response, "policy_decision_id"),
        human_approval_id=_optional_response_text(response, "human_approval_id"),
        raw_response=dict(response),
    )


def _safe_metadata(metadata: Mapping[str, object] | None) -> SafeMetadata:
    safe_metadata: SafeMetadata = {}
    for key, value in dict(metadata or {}).items():
        if not isinstance(key, str):
            raise UnsafeContextError("Metadata keys must be strings.")
        _reject_unsafe_key(key)
        if not _is_safe_metadata_value(value):
            raise UnsafeContextError(
                "Metadata values must be strings, numbers, booleans, or null."
            )
        safe_metadata[key] = value
    return safe_metadata


def _safe_text(field_name: str, value: object) -> str:
    if not isinstance(value, str):
        value = str(value)
    stripped = value.strip()
    if not stripped:
        raise UnsafeContextError(f"{field_name} must not be empty.")
    _reject_unsafe_key(field_name)
    return stripped


def _add_optional_text(payload: JsonObject, field_name: str, value: object) -> None:
    if value is not None:
        payload[field_name] = _safe_text(field_name, value)


def _reject_unsafe_key(key: str) -> None:
    normalized = key.lower()
    if any(part in normalized for part in UNSAFE_CONTEXT_KEY_PARTS):
        raise UnsafeContextError(
            f"Unsafe context key {key!r} must not be sent to AGCP."
        )


def _is_safe_metadata_value(value: object) -> bool:
    return isinstance(value, str | int | float | bool) or value is None


def _response_text(response: Mapping[str, object], field_name: str) -> str:
    value = response.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise AGCPResponseError(f"AGCP response missing {field_name!r}.")
    return value


def _optional_response_text(
    response: Mapping[str, object],
    field_name: str,
) -> str | None:
    value = response.get(field_name)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise AGCPResponseError(f"AGCP response has invalid {field_name!r}.")
    return value


def _response_bool(response: Mapping[str, object], field_name: str) -> bool:
    value = response.get(field_name)
    if not isinstance(value, bool):
        raise AGCPResponseError(f"AGCP response missing boolean {field_name!r}.")
    return value
