from uuid import uuid4

import pytest
from pydantic import ValidationError

from agent_governance_api.models import HumanApprovalStatus, PolicyDecisionValue
from agent_governance_api.runtime_gateway import (
    RuntimeDecisionMode,
    RuntimeToolCallDecisionRequest,
    RuntimeToolCallDecisionResponse,
    RuntimeToolCallResumeRequest,
    RuntimeToolCallResumeResponse,
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
    assert request.source_ids == []


def test_runtime_request_accepts_optional_contextual_fields() -> None:
    payload = runtime_request_payload()
    capability_id = uuid4()
    source_id = uuid4()
    model_id = uuid4()
    payload.update(
        {
            "action_type": "vectorize",
            "capability_id": str(capability_id),
            "source_ids": [str(source_id)],
            "model_id": str(model_id),
            "purpose": "semantic_search_indexing",
            "data_classification": "confidential",
            "contains_personal_data": True,
            "contains_sensitive_data": False,
        }
    )

    request = RuntimeToolCallDecisionRequest(**payload)

    assert request.action_type == "vectorize"
    assert request.capability_id == capability_id
    assert request.source_ids == [source_id]
    assert request.model_id == model_id
    assert request.purpose == "semantic_search_indexing"
    assert request.data_classification == "confidential"
    assert request.contains_personal_data is True
    assert request.contains_sensitive_data is False


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("action_type", " "),
        ("action_type", "vectorize this entire prompt"),
        ("purpose", " "),
        ("purpose", "customer support answering"),
    ],
)
def test_runtime_request_rejects_invalid_contextual_labels(
    field: str,
    value: str,
) -> None:
    payload = runtime_request_payload()
    payload[field] = value

    with pytest.raises(ValidationError):
        RuntimeToolCallDecisionRequest(**payload)


def test_runtime_request_rejects_duplicate_contextual_source_ids() -> None:
    source_id = str(uuid4())
    payload = runtime_request_payload()
    payload["source_ids"] = [source_id, source_id]

    with pytest.raises(ValidationError):
        RuntimeToolCallDecisionRequest(**payload)


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
        {"raw_content": "do not store this"},
        {"chunks": "do not store this"},
        {"prompt": "do not store this"},
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


def test_valid_runtime_tool_call_resume_request() -> None:
    agent_id = uuid4()
    run_id = uuid4()
    human_approval_id = uuid4()
    policy_decision_id = uuid4()

    request = RuntimeToolCallResumeRequest(
        resume_id="runtime-request-001:resume:001",
        original_request_id="runtime-request-001",
        agent_id=agent_id,
        run_id=run_id,
        tool_name="send_email",
        human_approval_id=human_approval_id,
        policy_decision_id=policy_decision_id,
        action_ref="support-ticket-123:follow-up-email",
        correlation_id="support-run-001",
        metadata={"ticket_category": "support"},
    )

    assert request.resume_id == "runtime-request-001:resume:001"
    assert request.original_request_id == "runtime-request-001"
    assert request.agent_id == agent_id
    assert request.run_id == run_id
    assert request.tool_name == "send_email"
    assert request.human_approval_id == human_approval_id
    assert request.policy_decision_id == policy_decision_id
    assert request.action_ref == "support-ticket-123:follow-up-email"
    assert request.correlation_id == "support-run-001"
    assert request.metadata == {"ticket_category": "support"}


def test_valid_runtime_tool_call_resume_response() -> None:
    response = RuntimeToolCallResumeResponse(
        resume_id="runtime-request-001:resume:001",
        original_request_id="runtime-request-001",
        agent_id=uuid4(),
        run_id=uuid4(),
        tool_name="send_email",
        decision="allow",
        proceed=True,
        reason="Human approval is approved and the resume context matches.",
        human_approval_status="approved",
        trace_event_id=uuid4(),
        policy_decision_id=uuid4(),
        human_approval_id=uuid4(),
    )

    assert response.decision is PolicyDecisionValue.ALLOW
    assert response.proceed is True
    assert response.human_approval_status is HumanApprovalStatus.APPROVED


@pytest.mark.parametrize(
    "missing_field",
    [
        "resume_id",
        "original_request_id",
        "human_approval_id",
        "policy_decision_id",
    ],
)
def test_runtime_resume_request_rejects_missing_required_fields(
    missing_field: str,
) -> None:
    payload = runtime_resume_request_payload()
    payload.pop(missing_field)

    with pytest.raises(ValidationError):
        RuntimeToolCallResumeRequest(**payload)


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
def test_runtime_resume_request_rejects_unsafe_metadata_keys(
    metadata: dict[str, str],
) -> None:
    payload = runtime_resume_request_payload()
    payload["metadata"] = metadata

    with pytest.raises(ValidationError):
        RuntimeToolCallResumeRequest(**payload)


def test_runtime_resume_response_allows_proceed_only_for_approved_allow() -> None:
    payload = runtime_resume_response_payload(
        decision=PolicyDecisionValue.ALLOW,
        proceed=True,
        human_approval_status=HumanApprovalStatus.APPROVED,
    )

    response = RuntimeToolCallResumeResponse(**payload)

    assert response.decision is PolicyDecisionValue.ALLOW
    assert response.proceed is True
    assert response.human_approval_status is HumanApprovalStatus.APPROVED


@pytest.mark.parametrize(
    ("decision", "human_approval_status"),
    [
        (PolicyDecisionValue.DENY, HumanApprovalStatus.APPROVED),
        (PolicyDecisionValue.REQUIRE_HUMAN_REVIEW, HumanApprovalStatus.APPROVED),
        (PolicyDecisionValue.NOT_APPLICABLE, HumanApprovalStatus.APPROVED),
        (PolicyDecisionValue.ALLOW, HumanApprovalStatus.PENDING),
    ],
)
def test_runtime_resume_response_rejects_invalid_proceed_true_combinations(
    decision: PolicyDecisionValue,
    human_approval_status: HumanApprovalStatus,
) -> None:
    payload = runtime_resume_response_payload(
        decision=decision,
        proceed=True,
        human_approval_status=human_approval_status,
    )

    with pytest.raises(ValidationError):
        RuntimeToolCallResumeResponse(**payload)


@pytest.mark.parametrize(
    ("human_approval_status", "decision"),
    [
        (HumanApprovalStatus.PENDING, PolicyDecisionValue.REQUIRE_HUMAN_REVIEW),
        (HumanApprovalStatus.REJECTED, PolicyDecisionValue.DENY),
        (HumanApprovalStatus.CANCELLED, PolicyDecisionValue.DENY),
        (HumanApprovalStatus.EXPIRED, PolicyDecisionValue.DENY),
    ],
)
def test_runtime_resume_response_blocks_unapproved_statuses(
    human_approval_status: HumanApprovalStatus,
    decision: PolicyDecisionValue,
) -> None:
    payload = runtime_resume_response_payload(
        decision=decision,
        proceed=False,
        human_approval_status=human_approval_status,
    )

    response = RuntimeToolCallResumeResponse(**payload)

    assert response.human_approval_status is human_approval_status
    assert response.decision is decision
    assert response.proceed is False


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


def runtime_resume_request_payload() -> dict[str, object]:
    return {
        "resume_id": "runtime-request-001:resume:001",
        "original_request_id": "runtime-request-001",
        "agent_id": uuid4(),
        "run_id": uuid4(),
        "tool_name": "send_email",
        "human_approval_id": uuid4(),
        "policy_decision_id": uuid4(),
        "action_ref": "support-ticket-123:follow-up-email",
        "correlation_id": "support-run-001",
        "metadata": {"ticket_category": "support"},
    }


def runtime_resume_response_payload(
    *,
    decision: PolicyDecisionValue,
    proceed: bool,
    human_approval_status: HumanApprovalStatus,
) -> dict[str, object]:
    return {
        "resume_id": "runtime-request-001:resume:001",
        "original_request_id": "runtime-request-001",
        "agent_id": uuid4(),
        "run_id": uuid4(),
        "tool_name": "send_email",
        "decision": decision,
        "proceed": proceed,
        "reason": "Runtime resume decision.",
        "human_approval_status": human_approval_status,
        "trace_event_id": None,
        "policy_decision_id": uuid4(),
        "human_approval_id": uuid4(),
    }
