import json
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from agent_governance_api.main import app


@pytest.fixture()
def api_client() -> Iterator[TestClient]:
    app.openapi_schema = None
    with TestClient(app) as client:
        yield client
    app.openapi_schema = None


@pytest.mark.parametrize(
    ("path", "method", "status_code", "has_request_body"),
    [
        ("/agents", "post", "201", True),
        ("/agents", "get", "200", False),
        ("/agents/{agent_id}", "get", "200", False),
        ("/agents/{agent_id}/access-grants", "get", "200", False),
        ("/agents/{agent_id}/activity", "get", "200", False),
        ("/agents/{agent_id}", "patch", "200", True),
        ("/capabilities", "post", "201", True),
        ("/capabilities", "get", "200", False),
        ("/capabilities/{capability_id}", "get", "200", False),
        ("/capabilities/{capability_id}", "patch", "200", True),
        ("/sources", "post", "201", True),
        ("/sources", "get", "200", False),
        ("/sources/{source_id}", "get", "200", False),
        ("/sources/{source_id}", "patch", "200", True),
        ("/models", "post", "201", True),
        ("/models", "get", "200", False),
        ("/models/{model_id}", "get", "200", False),
        ("/models/{model_id}", "patch", "200", True),
        ("/access-grants", "post", "201", True),
        ("/access-grants", "get", "200", False),
        ("/access-grants/{access_grant_id}", "get", "200", False),
        ("/access-grants/{access_grant_id}", "patch", "200", True),
        ("/policies", "post", "201", True),
        ("/policies", "get", "200", False),
        ("/policies/{policy_id}", "get", "200", False),
        ("/policies/{policy_id}/rules", "get", "200", False),
        ("/policies/{policy_id}", "patch", "200", True),
        ("/policy-rules", "post", "201", True),
        ("/policy-rules", "get", "200", False),
        ("/policy-rules/{rule_id}", "get", "200", False),
        ("/policy-rules/{rule_id}", "patch", "200", True),
        ("/telemetry/events", "post", "201", True),
        ("/agents/{agent_id}/evidence-bundle", "get", "200", False),
        ("/runtime/tool-calls/activity", "get", "200", False),
        ("/human-approvals", "post", "201", True),
        ("/human-approvals/{approval_id}/approve", "post", "200", True),
        ("/human-approvals/{approval_id}/reject", "post", "200", True),
        ("/human-approvals/{approval_id}/cancel", "post", "200", False),
    ],
)
def test_core_endpoints_have_v0_openapi_examples(
    api_client: TestClient,
    path: str,
    method: str,
    status_code: str,
    has_request_body: bool,
) -> None:
    operation = api_client.get("/openapi.json").json()["paths"][path][method]

    response_examples = _response_examples(operation, status_code)
    assert "v0GovernanceFlow" in response_examples

    if has_request_body:
        request_examples = _request_examples(operation)
        assert "v0GovernanceFlow" in request_examples


def test_openapi_examples_represent_v0_governance_chain(
    api_client: TestClient,
) -> None:
    schema = api_client.get("/openapi.json").json()
    telemetry_response = _response_example_value(
        schema["paths"]["/telemetry/events"]["post"],
        "201",
    )
    evidence_bundle = _response_example_value(
        schema["paths"]["/agents/{agent_id}/evidence-bundle"]["get"],
        "200",
    )

    [trace_event] = evidence_bundle["trace_events"]
    [policy_decision] = evidence_bundle["policy_decisions"]
    [human_approval] = evidence_bundle["human_approvals"]
    human_approval_audit_log = next(
        audit_log
        for audit_log in evidence_bundle["audit_logs"]
        if audit_log["event_type"] == "human_approval_requested"
    )

    assert telemetry_response["event_type"] == "tool_call_requested"
    assert telemetry_response["policy_decision"]["decision"] == "require_human_review"
    assert telemetry_response["human_approval_id"] == human_approval["id"]
    assert trace_event["id"] == telemetry_response["id"]
    assert policy_decision["trace_event_id"] == trace_event["id"]
    assert policy_decision["decision"] == "require_human_review"
    assert human_approval["policy_decision_id"] == policy_decision["id"]
    assert human_approval_audit_log["entity_id"] == human_approval["id"]
    assert (
        human_approval_audit_log["metadata"]["policy_decision_id"]
        == policy_decision["id"]
    )


def test_runtime_gateway_openapi_examples_cover_simulation_decisions(
    api_client: TestClient,
) -> None:
    operation = api_client.get("/openapi.json").json()["paths"][
        "/runtime/tool-calls/decision"
    ]["post"]

    request_examples = _request_examples(operation)
    created_examples = _response_examples(operation, "201")
    not_implemented_examples = _response_examples(operation, "501")

    assert set(request_examples) == {
        "allowDecision",
        "denyDecision",
        "requireHumanReviewDecision",
        "notApplicableDecision",
        "unsupportedTelemetryMode",
        "disabledEnforcementMode",
    }
    assert set(created_examples) == {
        "allowDecision",
        "denyDecision",
        "requireHumanReviewDecision",
        "notApplicableDecision",
    }
    assert set(not_implemented_examples) == {
        "unsupportedTelemetryMode",
        "disabledEnforcementMode",
    }

    assert request_examples["allowDecision"]["value"]["mode"] == "simulation"
    assert request_examples["allowDecision"]["value"]["metadata"] == {
        "ticket_category": "support",
        "destination_type": "customer",
    }
    assert request_examples["unsupportedTelemetryMode"]["value"]["mode"] == "telemetry"
    assert request_examples["disabledEnforcementMode"]["value"]["mode"] == "enforcement"

    assert created_examples["allowDecision"]["value"]["decision"] == "allow"
    assert created_examples["allowDecision"]["value"]["proceed"] is True
    assert created_examples["denyDecision"]["value"]["decision"] == "deny"
    assert created_examples["denyDecision"]["value"]["proceed"] is False
    review_response = created_examples["requireHumanReviewDecision"]["value"]
    assert review_response["decision"] == "require_human_review"
    assert review_response["proceed"] is False
    assert review_response["human_approval_id"] is not None
    assert (
        created_examples["notApplicableDecision"]["value"]["decision"]
        == "not_applicable"
    )
    assert created_examples["notApplicableDecision"]["value"]["proceed"] is False

    assert (
        "telemetry"
        in not_implemented_examples["unsupportedTelemetryMode"]["value"]["detail"]
    )
    assert (
        "enforcement"
        in not_implemented_examples["disabledEnforcementMode"]["value"]["detail"]
    )
    assert (
        "AGCP_RUNTIME_ENFORCEMENT_ENABLED"
        in not_implemented_examples["disabledEnforcementMode"]["value"]["detail"]
    )


def test_runtime_gateway_resume_openapi_examples_cover_approval_statuses(
    api_client: TestClient,
) -> None:
    operation = api_client.get("/openapi.json").json()["paths"][
        "/runtime/tool-calls/resume"
    ]["post"]

    request_examples = _request_examples(operation)
    created_examples = _response_examples(operation, "201")
    conflict_examples = _response_examples(operation, "409")

    assert set(request_examples) == {
        "approvedApproval",
        "pendingApproval",
        "rejectedApproval",
        "cancelledApproval",
        "expiredApproval",
        "contextMismatch",
    }
    assert set(created_examples) == {
        "approvedApproval",
        "pendingApproval",
        "rejectedApproval",
        "cancelledApproval",
        "expiredApproval",
    }
    assert set(conflict_examples) == {"contextMismatch"}

    approved = created_examples["approvedApproval"]["value"]
    assert approved["decision"] == "allow"
    assert approved["proceed"] is True
    assert approved["human_approval_status"] == "approved"

    pending = created_examples["pendingApproval"]["value"]
    assert pending["decision"] == "require_human_review"
    assert pending["proceed"] is False
    assert pending["human_approval_status"] == "pending"

    for example_name, approval_status in [
        ("rejectedApproval", "rejected"),
        ("cancelledApproval", "cancelled"),
        ("expiredApproval", "expired"),
    ]:
        example = created_examples[example_name]["value"]
        assert example["decision"] == "deny"
        assert example["proceed"] is False
        assert example["human_approval_status"] == approval_status

    request = request_examples["approvedApproval"]["value"]
    assert request["metadata"] == {
        "resume_channel": "polling",
        "ticket_category": "support",
    }
    assert request["action_ref"] == "support-ticket-123:follow-up-email"
    assert request_examples["contextMismatch"]["value"]["tool_name"] == "send_payment"
    assert (
        conflict_examples["contextMismatch"]["value"]["detail"]
        == "Tool name does not match the original trace event."
    )


def test_runtime_gateway_activity_openapi_example_is_newest_first(
    api_client: TestClient,
) -> None:
    operation = api_client.get("/openapi.json").json()["paths"][
        "/runtime/tool-calls/activity"
    ]["get"]

    activity = _response_example_value(operation, "200")

    assert [item["type"] for item in activity] == [
        "tool_call_resume",
        "tool_call_decision",
    ]
    assert [item["timestamp"] for item in activity] == sorted(
        [item["timestamp"] for item in activity],
        reverse=True,
    )
    resume_item = activity[0]
    assert resume_item["request_id"] == "runtime-request-001:resume:001"
    assert resume_item.get("mode") is None
    assert resume_item["related_ids"]["original_request_id"] == "runtime-request-001"


def test_agent_access_grants_openapi_example_is_newest_first(
    api_client: TestClient,
) -> None:
    operation = api_client.get("/openapi.json").json()["paths"][
        "/agents/{agent_id}/access-grants"
    ]["get"]

    access_grants = _response_example_value(operation, "200")

    assert [grant["target_type"] for grant in access_grants] == [
        "model_asset",
        "source",
        "capability",
    ]
    assert [grant["created_at"] for grant in access_grants] == sorted(
        [grant["created_at"] for grant in access_grants],
        reverse=True,
    )
    assert {grant["subject_type"] for grant in access_grants} == {"agent"}


def test_openapi_examples_do_not_include_sensitive_payloads(
    api_client: TestClient,
) -> None:
    schema = api_client.get("/openapi.json").json()
    examples_blob = json.dumps(_collect_example_values(schema), sort_keys=True).lower()

    for unsafe_text in [
        "api_key",
        "token",
        "password",
        "secret",
        "authorization",
        "raw_prompt",
        "raw_payload",
    ]:
        assert unsafe_text not in examples_blob


def _request_examples(operation: dict[str, object]) -> dict[str, object]:
    request_body = operation["requestBody"]
    assert isinstance(request_body, dict)
    return _json_content_examples(request_body)


def _response_examples(
    operation: dict[str, object],
    status_code: str,
) -> dict[str, object]:
    responses = operation["responses"]
    assert isinstance(responses, dict)
    response = responses[status_code]
    assert isinstance(response, dict)
    return _json_content_examples(response)


def _response_example_value(
    operation: dict[str, object],
    status_code: str,
) -> object:
    return _response_examples(operation, status_code)["v0GovernanceFlow"]["value"]


def _json_content_examples(documented_content: dict[str, object]) -> dict[str, object]:
    content = documented_content["content"]
    assert isinstance(content, dict)
    json_content = content["application/json"]
    assert isinstance(json_content, dict)
    examples = json_content["examples"]
    assert isinstance(examples, dict)
    return examples


def _optional_json_content_examples(
    documented_content: dict[str, object],
) -> dict[str, object]:
    content = documented_content.get("content")
    if not isinstance(content, dict):
        return {}
    json_content = content.get("application/json")
    if not isinstance(json_content, dict):
        return {}
    examples = json_content.get("examples")
    if not isinstance(examples, dict):
        return {}
    return examples


def _collect_example_values(schema: dict[str, object]) -> list[object]:
    values: list[object] = []
    paths = schema["paths"]
    assert isinstance(paths, dict)
    for path_item in paths.values():
        assert isinstance(path_item, dict)
        for operation in path_item.values():
            if not isinstance(operation, dict):
                continue
            request_body = operation.get("requestBody")
            if isinstance(request_body, dict):
                values.extend(
                    _example_values(_optional_json_content_examples(request_body))
                )
            responses = operation.get("responses")
            if not isinstance(responses, dict):
                continue
            for response in responses.values():
                if isinstance(response, dict) and "content" in response:
                    values.extend(
                        _example_values(_optional_json_content_examples(response))
                    )
    return values


def _example_values(examples: dict[str, object]) -> list[object]:
    values: list[object] = []
    for example in examples.values():
        assert isinstance(example, dict)
        values.append(example["value"])
    return values
