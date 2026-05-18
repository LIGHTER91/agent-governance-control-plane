AGENT_ID = "11111111-1111-4111-8111-111111111111"
RUN_ID = "22222222-2222-4222-8222-222222222222"
TRACE_EVENT_ID = "33333333-3333-4333-8333-333333333333"
POLICY_ID = "44444444-4444-4444-8444-444444444444"
RULE_ID = "55555555-5555-4555-8555-555555555555"
POLICY_DECISION_ID = "66666666-6666-4666-8666-666666666666"
HUMAN_APPROVAL_ID = "77777777-7777-4777-8777-777777777777"
AGENT_RUN_RECORD_ID = "88888888-8888-4888-8888-888888888888"
AGENT_AUDIT_LOG_ID = "99999999-9999-4999-8999-999999999999"
HUMAN_APPROVAL_AUDIT_LOG_ID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
RUNTIME_RESUME_TRACE_EVENT_ID = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"

CREATED_AT = "2026-01-15T12:00:00Z"
UPDATED_AT = "2026-01-15T12:00:00Z"
TRACE_EVENT_TIMESTAMP = "2026-01-15T12:05:00Z"
POLICY_DECISION_CREATED_AT = "2026-01-15T12:05:01Z"
HUMAN_APPROVAL_CREATED_AT = "2026-01-15T12:05:02Z"
RUNTIME_REQUEST_ID = "runtime-request-001"
RUNTIME_RESUME_ID = "runtime-request-001:resume:001"

AGENT_CREATE_REQUEST = {
    "name": "V0 Support Assistant",
    "description": "Routes support requests and requests governed tool access.",
    "owner_type": "team",
    "owner_id": "team:ai-platform",
    "owner_name": "AI Platform",
    "owner_contact_email": "ai-platform@example.invalid",
    "environment": "development",
    "status": "active",
    "risk_level": "medium",
    "framework": "LangGraph",
}

AGENT_RESPONSE = {
    **AGENT_CREATE_REQUEST,
    "id": AGENT_ID,
    "created_at": CREATED_AT,
    "updated_at": UPDATED_AT,
}

AGENT_UPDATE_REQUEST = {
    "status": "under_review",
    "risk_level": "high",
}

AGENT_UPDATED_RESPONSE = {
    **AGENT_RESPONSE,
    "status": "under_review",
    "risk_level": "high",
    "updated_at": "2026-01-15T12:10:00Z",
}

TELEMETRY_EVENT_REQUEST = {
    "id": TRACE_EVENT_ID,
    "agent_id": AGENT_ID,
    "run_id": RUN_ID,
    "external_event_id": "v0-demo-event-001",
    "correlation_id": "v0-demo-correlation",
    "event_type": "tool_call_requested",
    "timestamp": TRACE_EVENT_TIMESTAMP,
    "summary": "Agent requested send_email tool.",
    "metadata": {"tool_name": "send_email"},
}

POLICY_REFERENCE = {
    "id": POLICY_ID,
    "name": "V0 email tool review policy",
    "status": "active",
}

RULE_REFERENCE = {
    "id": RULE_ID,
    "policy_id": POLICY_ID,
    "name": "Require review for send_email",
}

POLICY_DECISION_RESPONSE = {
    "id": POLICY_DECISION_ID,
    "agent_id": AGENT_ID,
    "policy_id": POLICY_ID,
    "rule_id": RULE_ID,
    "trace_event_id": TRACE_EVENT_ID,
    "decision": "require_human_review",
    "reason": "Email tool use requires human review.",
    "context_hash": "sha256:v0-demo-context",
    "policy": POLICY_REFERENCE,
    "rule": RULE_REFERENCE,
    "created_at": POLICY_DECISION_CREATED_AT,
}

TELEMETRY_POLICY_DECISION_RESPONSE = {
    "id": POLICY_DECISION_ID,
    "trace_event_id": TRACE_EVENT_ID,
    "decision": "require_human_review",
    "reason": "Email tool use requires human review.",
    "policy_id": POLICY_ID,
    "rule_id": RULE_ID,
    "created_at": POLICY_DECISION_CREATED_AT,
}

TELEMETRY_EVENT_RESPONSE = {
    "id": TRACE_EVENT_ID,
    "agent_id": AGENT_ID,
    "run_id": RUN_ID,
    "event_type": "tool_call_requested",
    "created_at": TRACE_EVENT_TIMESTAMP,
    "policy_decision": TELEMETRY_POLICY_DECISION_RESPONSE,
    "human_approval_id": HUMAN_APPROVAL_ID,
}

HUMAN_APPROVAL_CREATE_REQUEST = {
    "agent_id": AGENT_ID,
    "policy_decision_id": POLICY_DECISION_ID,
    "reason": "Email tool use requires human review.",
}

HUMAN_APPROVAL_PENDING_RESPONSE = {
    "id": HUMAN_APPROVAL_ID,
    "agent_id": AGENT_ID,
    "policy_decision_id": POLICY_DECISION_ID,
    "status": "pending",
    "requested_by_actor_type": "development",
    "requested_by_actor_id": "dev-placeholder",
    "reviewed_by_actor_type": None,
    "reviewed_by_actor_id": None,
    "reason": "Email tool use requires human review.",
    "decision_note": None,
    "reviewed_at": None,
    "expires_at": None,
    "created_at": HUMAN_APPROVAL_CREATED_AT,
}

HUMAN_APPROVAL_APPROVE_REQUEST = {
    "decision_note": "Approved after reviewing the requested tool use.",
}

HUMAN_APPROVAL_APPROVED_RESPONSE = {
    **HUMAN_APPROVAL_PENDING_RESPONSE,
    "status": "approved",
    "reviewed_by_actor_type": "development",
    "reviewed_by_actor_id": "dev-placeholder",
    "decision_note": "Approved after reviewing the requested tool use.",
    "reviewed_at": "2026-01-15T12:20:00Z",
}

HUMAN_APPROVAL_REJECT_REQUEST = {
    "decision_note": "Rejected because the requested tool use needs more context.",
}

HUMAN_APPROVAL_REJECTED_RESPONSE = {
    **HUMAN_APPROVAL_PENDING_RESPONSE,
    "status": "rejected",
    "reviewed_by_actor_type": "development",
    "reviewed_by_actor_id": "dev-placeholder",
    "decision_note": "Rejected because the requested tool use needs more context.",
    "reviewed_at": "2026-01-15T12:20:00Z",
}

HUMAN_APPROVAL_CANCELLED_RESPONSE = {
    **HUMAN_APPROVAL_PENDING_RESPONSE,
    "status": "cancelled",
}

RUNTIME_TOOL_CALL_DECISION_REQUEST = {
    "request_id": RUNTIME_REQUEST_ID,
    "agent_id": AGENT_ID,
    "run_id": RUN_ID,
    "correlation_id": "runtime-demo-correlation",
    "tool_name": "send_email",
    "action_summary": "Send a support follow-up email.",
    "metadata": {
        "ticket_category": "support",
        "destination_type": "customer",
    },
    "mode": "simulation",
}

RUNTIME_TOOL_CALL_DECISION_ALLOW_RESPONSE = {
    "request_id": RUNTIME_REQUEST_ID,
    "agent_id": AGENT_ID,
    "run_id": RUN_ID,
    "tool_name": "send_email",
    "decision": "allow",
    "proceed": True,
    "reason": "Email tool use is allowed in simulation.",
    "trace_event_id": TRACE_EVENT_ID,
    "policy_decision_id": POLICY_DECISION_ID,
    "human_approval_id": None,
}

RUNTIME_TOOL_CALL_DECISION_DENY_RESPONSE = {
    **RUNTIME_TOOL_CALL_DECISION_ALLOW_RESPONSE,
    "decision": "deny",
    "proceed": False,
    "reason": "Email tool use is denied in simulation.",
}

RUNTIME_TOOL_CALL_DECISION_REVIEW_RESPONSE = {
    **RUNTIME_TOOL_CALL_DECISION_ALLOW_RESPONSE,
    "decision": "require_human_review",
    "proceed": False,
    "reason": "Email tool use requires human review.",
    "human_approval_id": HUMAN_APPROVAL_ID,
}

RUNTIME_TOOL_CALL_DECISION_NOT_APPLICABLE_RESPONSE = {
    **RUNTIME_TOOL_CALL_DECISION_ALLOW_RESPONSE,
    "decision": "not_applicable",
    "proceed": False,
    "reason": "No policy rule matched the request.",
}

RUNTIME_TELEMETRY_MODE_REQUEST = {
    **RUNTIME_TOOL_CALL_DECISION_REQUEST,
    "request_id": "runtime-request-telemetry",
    "mode": "telemetry",
}

RUNTIME_ENFORCEMENT_MODE_REQUEST = {
    **RUNTIME_TOOL_CALL_DECISION_REQUEST,
    "request_id": "runtime-request-enforcement",
    "mode": "enforcement",
}

RUNTIME_TELEMETRY_MODE_RESPONSE = {
    "detail": (
        "Runtime Gateway telemetry mode is not implemented for this endpoint yet. "
        "Use POST /telemetry/events for telemetry ingestion."
    ),
}

RUNTIME_ENFORCEMENT_MODE_RESPONSE = {
    "detail": (
        "Runtime Gateway enforcement mode is disabled. Set "
        "AGCP_RUNTIME_ENFORCEMENT_ENABLED=true to enable it."
    ),
}

RUNTIME_TOOL_CALL_RESUME_REQUEST = {
    "resume_id": RUNTIME_RESUME_ID,
    "original_request_id": RUNTIME_REQUEST_ID,
    "agent_id": AGENT_ID,
    "run_id": RUN_ID,
    "tool_name": "send_email",
    "human_approval_id": HUMAN_APPROVAL_ID,
    "policy_decision_id": POLICY_DECISION_ID,
    "action_ref": "support-ticket-123:follow-up-email",
    "correlation_id": "runtime-demo-correlation",
    "metadata": {
        "resume_channel": "polling",
        "ticket_category": "support",
    },
}

RUNTIME_TOOL_CALL_RESUME_CONTEXT_MISMATCH_REQUEST = {
    **RUNTIME_TOOL_CALL_RESUME_REQUEST,
    "tool_name": "send_payment",
}

RUNTIME_TOOL_CALL_RESUME_APPROVED_RESPONSE = {
    "resume_id": RUNTIME_RESUME_ID,
    "original_request_id": RUNTIME_REQUEST_ID,
    "agent_id": AGENT_ID,
    "run_id": RUN_ID,
    "tool_name": "send_email",
    "decision": "allow",
    "proceed": True,
    "reason": "Human approval is approved and the resume context matches.",
    "human_approval_status": "approved",
    "trace_event_id": RUNTIME_RESUME_TRACE_EVENT_ID,
    "policy_decision_id": POLICY_DECISION_ID,
    "human_approval_id": HUMAN_APPROVAL_ID,
}

RUNTIME_TOOL_CALL_RESUME_PENDING_RESPONSE = {
    **RUNTIME_TOOL_CALL_RESUME_APPROVED_RESPONSE,
    "decision": "require_human_review",
    "proceed": False,
    "reason": "Human approval is still pending.",
    "human_approval_status": "pending",
}

RUNTIME_TOOL_CALL_RESUME_REJECTED_RESPONSE = {
    **RUNTIME_TOOL_CALL_RESUME_APPROVED_RESPONSE,
    "decision": "deny",
    "proceed": False,
    "reason": "Human approval was rejected.",
    "human_approval_status": "rejected",
}

RUNTIME_TOOL_CALL_RESUME_CANCELLED_RESPONSE = {
    **RUNTIME_TOOL_CALL_RESUME_REJECTED_RESPONSE,
    "reason": "Human approval was cancelled.",
    "human_approval_status": "cancelled",
}

RUNTIME_TOOL_CALL_RESUME_EXPIRED_RESPONSE = {
    **RUNTIME_TOOL_CALL_RESUME_REJECTED_RESPONSE,
    "reason": "Human approval is expired.",
    "human_approval_status": "expired",
}

RUNTIME_TOOL_CALL_RESUME_CONTEXT_MISMATCH_RESPONSE = {
    "detail": "Tool name does not match the original trace event.",
}

EVIDENCE_BUNDLE_RESPONSE = {
    "agent": AGENT_RESPONSE,
    "audit_logs": [
        {
            "id": AGENT_AUDIT_LOG_ID,
            "event_type": "agent_created",
            "actor_type": "development",
            "actor_id": "dev-placeholder",
            "entity_type": "agent",
            "entity_id": AGENT_ID,
            "summary": "Agent created.",
            "metadata": {"operation": "create"},
            "created_at": CREATED_AT,
        },
        {
            "id": HUMAN_APPROVAL_AUDIT_LOG_ID,
            "event_type": "human_approval_requested",
            "actor_type": "development",
            "actor_id": "dev-placeholder",
            "entity_type": "human_approval",
            "entity_id": HUMAN_APPROVAL_ID,
            "summary": "Human approval requested.",
            "metadata": {
                "agent_id": AGENT_ID,
                "status": "pending",
                "policy_decision_id": POLICY_DECISION_ID,
            },
            "created_at": HUMAN_APPROVAL_CREATED_AT,
        },
    ],
    "agent_runs": [
        {
            "id": AGENT_RUN_RECORD_ID,
            "agent_id": AGENT_ID,
            "run_id": RUN_ID,
            "correlation_id": "v0-demo-correlation",
            "environment": "development",
            "status": "observed",
            "started_at": TRACE_EVENT_TIMESTAMP,
            "ended_at": None,
            "summary": "Auto-created from telemetry event.",
            "metadata": {},
            "created_at": TRACE_EVENT_TIMESTAMP,
        }
    ],
    "trace_events": [
        {
            **TELEMETRY_EVENT_REQUEST,
            "created_at": TRACE_EVENT_TIMESTAMP,
        }
    ],
    "policy_decisions": [POLICY_DECISION_RESPONSE],
    "human_approvals": [HUMAN_APPROVAL_PENDING_RESPONSE],
}


def _example(summary: str, value: object) -> dict[str, object]:
    return {
        "v0GovernanceFlow": {
            "summary": summary,
            "value": value,
        }
    }


def _named_example(summary: str, value: object) -> dict[str, object]:
    return {
        "summary": summary,
        "value": value,
    }


def _request_example(summary: str, value: object) -> dict[str, object]:
    return {
        "requestBody": {
            "content": {
                "application/json": {
                    "examples": _example(summary, value),
                }
            }
        }
    }


def _response_example(
    status_code: int,
    summary: str,
    value: object,
) -> dict[str, object]:
    return {
        "responses": {
            str(status_code): {
                "content": {
                    "application/json": {
                        "examples": _example(summary, value),
                    }
                }
            }
        }
    }


def _request_response_example(
    *,
    request_summary: str,
    request_value: object,
    response_status_code: int,
    response_summary: str,
    response_value: object,
) -> dict[str, object]:
    return {
        **_request_example(request_summary, request_value),
        **_response_example(response_status_code, response_summary, response_value),
    }


AGENT_CREATE_OPENAPI = _request_response_example(
    request_summary="Create the V0 demo agent.",
    request_value=AGENT_CREATE_REQUEST,
    response_status_code=201,
    response_summary="Created agent.",
    response_value=AGENT_RESPONSE,
)

AGENT_LIST_OPENAPI = _response_example(
    200,
    "List agents including the V0 demo agent.",
    [AGENT_RESPONSE],
)

AGENT_GET_OPENAPI = _response_example(
    200,
    "Read the V0 demo agent.",
    AGENT_RESPONSE,
)

AGENT_UPDATE_OPENAPI = _request_response_example(
    request_summary="Move the V0 demo agent into review.",
    request_value=AGENT_UPDATE_REQUEST,
    response_status_code=200,
    response_summary="Updated agent.",
    response_value=AGENT_UPDATED_RESPONSE,
)

TELEMETRY_EVENT_OPENAPI = _request_response_example(
    request_summary="Ingest a governed tool call request.",
    request_value=TELEMETRY_EVENT_REQUEST,
    response_status_code=201,
    response_summary="Trace event with a human-review policy decision.",
    response_value=TELEMETRY_EVENT_RESPONSE,
)

RUNTIME_TOOL_CALL_DECISION_OPENAPI = {
    "requestBody": {
        "content": {
            "application/json": {
                "examples": {
                    "allowDecision": _named_example(
                        "Simulate a tool call that is allowed.",
                        RUNTIME_TOOL_CALL_DECISION_REQUEST,
                    ),
                    "denyDecision": _named_example(
                        "Simulate a tool call that is denied.",
                        RUNTIME_TOOL_CALL_DECISION_REQUEST,
                    ),
                    "requireHumanReviewDecision": _named_example(
                        "Simulate a tool call requiring human review.",
                        RUNTIME_TOOL_CALL_DECISION_REQUEST,
                    ),
                    "notApplicableDecision": _named_example(
                        "Simulate a tool call with no matching policy.",
                        RUNTIME_TOOL_CALL_DECISION_REQUEST,
                    ),
                    "unsupportedTelemetryMode": _named_example(
                        "Telemetry mode is not implemented on this endpoint.",
                        RUNTIME_TELEMETRY_MODE_REQUEST,
                    ),
                    "disabledEnforcementMode": _named_example(
                        "Enforcement mode is disabled by default.",
                        RUNTIME_ENFORCEMENT_MODE_REQUEST,
                    ),
                }
            }
        }
    },
    "responses": {
        "201": {
            "content": {
                "application/json": {
                    "examples": {
                        "allowDecision": _named_example(
                            "Allowed runtime simulation decision.",
                            RUNTIME_TOOL_CALL_DECISION_ALLOW_RESPONSE,
                        ),
                        "denyDecision": _named_example(
                            "Denied runtime simulation decision.",
                            RUNTIME_TOOL_CALL_DECISION_DENY_RESPONSE,
                        ),
                        "requireHumanReviewDecision": _named_example(
                            "Human-review runtime simulation decision.",
                            RUNTIME_TOOL_CALL_DECISION_REVIEW_RESPONSE,
                        ),
                        "notApplicableDecision": _named_example(
                            "No matching runtime policy decision.",
                            RUNTIME_TOOL_CALL_DECISION_NOT_APPLICABLE_RESPONSE,
                        ),
                    }
                }
            }
        },
        "501": {
            "content": {
                "application/json": {
                    "examples": {
                        "unsupportedTelemetryMode": _named_example(
                            "Telemetry mode is not implemented on this endpoint.",
                            RUNTIME_TELEMETRY_MODE_RESPONSE,
                        ),
                        "disabledEnforcementMode": _named_example(
                            "Enforcement mode is disabled by default.",
                            RUNTIME_ENFORCEMENT_MODE_RESPONSE,
                        ),
                    }
                }
            }
        },
    },
}

RUNTIME_TOOL_CALL_RESUME_OPENAPI = {
    "requestBody": {
        "content": {
            "application/json": {
                "examples": {
                    "approvedApproval": _named_example(
                        "Check an approved human approval before resuming.",
                        RUNTIME_TOOL_CALL_RESUME_REQUEST,
                    ),
                    "pendingApproval": _named_example(
                        "Check a still-pending human approval.",
                        RUNTIME_TOOL_CALL_RESUME_REQUEST,
                    ),
                    "rejectedApproval": _named_example(
                        "Check a rejected human approval.",
                        RUNTIME_TOOL_CALL_RESUME_REQUEST,
                    ),
                    "cancelledApproval": _named_example(
                        "Check a cancelled human approval.",
                        RUNTIME_TOOL_CALL_RESUME_REQUEST,
                    ),
                    "expiredApproval": _named_example(
                        "Check an expired human approval.",
                        RUNTIME_TOOL_CALL_RESUME_REQUEST,
                    ),
                    "contextMismatch": _named_example(
                        "Reject resume when the submitted context changed.",
                        RUNTIME_TOOL_CALL_RESUME_CONTEXT_MISMATCH_REQUEST,
                    ),
                }
            }
        }
    },
    "responses": {
        "201": {
            "content": {
                "application/json": {
                    "examples": {
                        "approvedApproval": _named_example(
                            "Approved human approval may proceed.",
                            RUNTIME_TOOL_CALL_RESUME_APPROVED_RESPONSE,
                        ),
                        "pendingApproval": _named_example(
                            "Pending human approval remains blocked.",
                            RUNTIME_TOOL_CALL_RESUME_PENDING_RESPONSE,
                        ),
                        "rejectedApproval": _named_example(
                            "Rejected human approval remains blocked.",
                            RUNTIME_TOOL_CALL_RESUME_REJECTED_RESPONSE,
                        ),
                        "cancelledApproval": _named_example(
                            "Cancelled human approval remains blocked.",
                            RUNTIME_TOOL_CALL_RESUME_CANCELLED_RESPONSE,
                        ),
                        "expiredApproval": _named_example(
                            "Expired human approval remains blocked.",
                            RUNTIME_TOOL_CALL_RESUME_EXPIRED_RESPONSE,
                        ),
                    }
                }
            }
        },
        "409": {
            "content": {
                "application/json": {
                    "examples": {
                        "contextMismatch": _named_example(
                            "Resume context does not match the original request.",
                            RUNTIME_TOOL_CALL_RESUME_CONTEXT_MISMATCH_RESPONSE,
                        ),
                    }
                }
            }
        },
    },
}

EVIDENCE_BUNDLE_OPENAPI = _response_example(
    200,
    "Export the V0 governance evidence chain.",
    EVIDENCE_BUNDLE_RESPONSE,
)

HUMAN_APPROVAL_CREATE_OPENAPI = _request_response_example(
    request_summary="Request human approval for a policy decision.",
    request_value=HUMAN_APPROVAL_CREATE_REQUEST,
    response_status_code=201,
    response_summary="Pending human approval.",
    response_value=HUMAN_APPROVAL_PENDING_RESPONSE,
)

HUMAN_APPROVAL_APPROVE_OPENAPI = _request_response_example(
    request_summary="Approve a pending human approval.",
    request_value=HUMAN_APPROVAL_APPROVE_REQUEST,
    response_status_code=200,
    response_summary="Approved human approval.",
    response_value=HUMAN_APPROVAL_APPROVED_RESPONSE,
)

HUMAN_APPROVAL_REJECT_OPENAPI = _request_response_example(
    request_summary="Reject a pending human approval.",
    request_value=HUMAN_APPROVAL_REJECT_REQUEST,
    response_status_code=200,
    response_summary="Rejected human approval.",
    response_value=HUMAN_APPROVAL_REJECTED_RESPONSE,
)

HUMAN_APPROVAL_CANCEL_OPENAPI = _response_example(
    200,
    "Cancelled human approval.",
    HUMAN_APPROVAL_CANCELLED_RESPONSE,
)
