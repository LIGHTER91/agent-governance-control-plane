AGENT_ID = "11111111-1111-4111-8111-111111111111"
CAPABILITY_ID = "12121212-1212-4121-8121-121212121212"
SOURCE_ID = "13131313-1313-4131-8131-131313131313"
MODEL_ASSET_ID = "14141414-1414-4141-8141-141414141414"
DATA_USAGE_PROFILE_ID = "18181818-1818-4181-8181-181818181818"
CHECK_TOOL_ID = "19191919-1919-4191-8191-191919191919"
CHECK_RESULT_ID = "1a1a1a1a-1a1a-41a1-81a1-1a1a1a1a1a1a"
ACCESS_GRANT_ID = "15151515-1515-4151-8151-151515151515"
SOURCE_ACCESS_GRANT_ID = "16161616-1616-4161-8161-161616161616"
MODEL_ASSET_ACCESS_GRANT_ID = "17171717-1717-4171-8171-171717171717"
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
RUNTIME_RESUME_TRACE_EVENT_TIMESTAMP = "2026-01-15T12:20:01Z"
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

CAPABILITY_CREATE_REQUEST = {
    "name": "Send support email",
    "description": "Send a governed support follow-up email.",
    "capability_type": "tool",
    "external_ref": "tool:send_email",
    "status": "active",
    "risk_level": "medium",
    "metadata": {
        "domain": "support",
        "operation": "send_email",
    },
}

CAPABILITY_RESPONSE = {
    **CAPABILITY_CREATE_REQUEST,
    "id": CAPABILITY_ID,
    "created_at": CREATED_AT,
    "updated_at": UPDATED_AT,
}

CAPABILITY_UPDATE_REQUEST = {
    "status": "disabled",
    "metadata": {
        "domain": "support",
        "operation": "send_email",
        "review_status": "paused",
    },
}

CAPABILITY_UPDATED_RESPONSE = {
    **CAPABILITY_RESPONSE,
    **CAPABILITY_UPDATE_REQUEST,
    "updated_at": "2026-01-15T12:10:00Z",
}

SOURCE_CREATE_REQUEST = {
    "name": "Support knowledge base",
    "description": "Governed source for support runbooks and troubleshooting notes.",
    "source_type": "knowledge_base",
    "external_ref": "kb:support-runbooks",
    "owner_type": "team",
    "owner_id": "team:support-ops",
    "owner_name": "Support Operations",
    "owner_contact_email": "support-ops@example.invalid",
    "status": "active",
    "risk_level": "medium",
    "metadata": {
        "domain": "support",
        "system": "runbook_index",
    },
}

SOURCE_RESPONSE = {
    **SOURCE_CREATE_REQUEST,
    "id": SOURCE_ID,
    "created_at": CREATED_AT,
    "updated_at": UPDATED_AT,
}

DATA_USAGE_PROFILE_RESPONSE = {
    "id": DATA_USAGE_PROFILE_ID,
    "source_id": SOURCE_ID,
    "data_classification": "confidential",
    "contains_personal_data": True,
    "contains_sensitive_data": False,
    "data_categories": ["customer_data", "support_case"],
    "legal_basis": "declared_contractual_basis",
    "allowed_purposes": ["customer_support_answering"],
    "prohibited_purposes": ["model_training"],
    "allowed_processing": ["search", "rag"],
    "prohibited_processing": ["training"],
    "residency": "eu",
    "retention_policy": "support-standard-retention",
    "data_owner": "team:support-ops",
    "review_status": "approved",
    "reviewed_by_actor_type": "user",
    "reviewed_by_actor_id": "user:dpo-1",
    "reviewed_at": "2026-01-10T09:00:00Z",
    "review_expires_at": "2027-01-10T09:00:00Z",
    "dpia_required": True,
    "dpia_reference": "dpia:DPIA-123",
    "metadata": {"catalog_ref": "catalog:source-123"},
    "created_at": CREATED_AT,
    "updated_at": UPDATED_AT,
}

SOURCE_UPDATE_REQUEST = {
    "status": "disabled",
    "metadata": {
        "domain": "support",
        "system": "runbook_index",
        "review_status": "paused",
    },
}

SOURCE_UPDATED_RESPONSE = {
    **SOURCE_RESPONSE,
    **SOURCE_UPDATE_REQUEST,
    "updated_at": "2026-01-15T12:10:00Z",
}

MODEL_ASSET_CREATE_REQUEST = {
    "name": "Support assistant chat model",
    "description": "Governed hosted language model used for support assistance.",
    "model_type": "llm",
    "provider": "openai",
    "model_ref": "support-chat-deployment",
    "version": "2026-01",
    "owner_type": "team",
    "owner_id": "team:ai-platform",
    "owner_name": "AI Platform",
    "owner_contact_email": "ai-platform@example.invalid",
    "status": "active",
    "risk_level": "medium",
    "metadata": {
        "domain": "support",
        "usage": "assistant_response",
    },
}

MODEL_ASSET_RESPONSE = {
    **MODEL_ASSET_CREATE_REQUEST,
    "id": MODEL_ASSET_ID,
    "created_at": CREATED_AT,
    "updated_at": UPDATED_AT,
}

MODEL_ASSET_UPDATE_REQUEST = {
    "status": "disabled",
    "metadata": {
        "domain": "support",
        "usage": "assistant_response",
        "review_status": "paused",
    },
}

MODEL_ASSET_UPDATED_RESPONSE = {
    **MODEL_ASSET_RESPONSE,
    **MODEL_ASSET_UPDATE_REQUEST,
    "updated_at": "2026-01-15T12:10:00Z",
}

ACCESS_GRANT_CREATE_REQUEST = {
    "name": "Support email capability access",
    "description": "Allow the V0 Support Assistant to use the support email tool.",
    "grant_type": "capability",
    "subject_type": "agent",
    "subject_id": AGENT_ID,
    "target_type": "capability",
    "target_id": CAPABILITY_ID,
    "external_ref": None,
    "status": "active",
    "reason": "Support follow-up workflow reviewed for the V0 demo.",
    "expires_at": "2026-12-31T23:59:59Z",
    "risk_level": "medium",
    "metadata": {
        "approval_ticket": "GOV-123",
        "review_status": "approved",
    },
}

ACCESS_GRANT_RESPONSE = {
    **ACCESS_GRANT_CREATE_REQUEST,
    "id": ACCESS_GRANT_ID,
    "granted_by_actor_type": "development",
    "granted_by_actor_id": "dev-placeholder",
    "created_at": CREATED_AT,
    "updated_at": UPDATED_AT,
}

ACCESS_GRANT_UPDATE_REQUEST = {
    "status": "suspended",
    "reason": "Access paused during governance review.",
    "metadata": {
        "approval_ticket": "GOV-123",
        "review_status": "paused",
    },
}

ACCESS_GRANT_UPDATED_RESPONSE = {
    **ACCESS_GRANT_RESPONSE,
    **ACCESS_GRANT_UPDATE_REQUEST,
    "updated_at": "2026-01-15T12:10:00Z",
}

AGENT_ACCESS_GRANT_RESPONSE = [
    {
        **ACCESS_GRANT_RESPONSE,
        "id": MODEL_ASSET_ACCESS_GRANT_ID,
        "name": "Support model access",
        "description": "Allow the V0 Support Assistant to use the support chat model.",
        "grant_type": "model",
        "target_type": "model_asset",
        "target_id": MODEL_ASSET_ID,
        "reason": "Support response workflow reviewed for the V0 demo.",
        "metadata": {
            "approval_ticket": "GOV-125",
            "review_status": "approved",
        },
        "created_at": "2026-01-15T12:10:00Z",
        "updated_at": "2026-01-15T12:10:00Z",
    },
    {
        **ACCESS_GRANT_RESPONSE,
        "id": SOURCE_ACCESS_GRANT_ID,
        "name": "Support knowledge source access",
        "description": (
            "Allow the V0 Support Assistant to reference support runbooks."
        ),
        "grant_type": "source",
        "target_type": "source",
        "target_id": SOURCE_ID,
        "reason": "Support knowledge workflow reviewed for the V0 demo.",
        "metadata": {
            "approval_ticket": "GOV-124",
            "review_status": "approved",
        },
        "created_at": "2026-01-15T12:05:00Z",
        "updated_at": "2026-01-15T12:05:00Z",
    },
    ACCESS_GRANT_RESPONSE,
]

AGENT_ACTIVITY_RESPONSE = [
    {
        "id": TRACE_EVENT_ID,
        "type": "trace_event",
        "timestamp": TRACE_EVENT_TIMESTAMP,
        "title": "Trace event: Tool Call Requested",
        "summary": "Agent requested send_email tool.",
        "severity": "info",
        "trace_event_id": TRACE_EVENT_ID,
        "policy_decision_id": None,
        "human_approval_id": None,
        "audit_log_id": None,
        "run_id": RUN_ID,
        "related_ids": {
            "trace_event_id": TRACE_EVENT_ID,
            "run_id": RUN_ID,
        },
        "metadata": {
            "tool_name": "send_email",
        },
    },
    {
        "id": POLICY_DECISION_ID,
        "type": "policy_decision",
        "timestamp": POLICY_DECISION_CREATED_AT,
        "title": "Policy decision: Require Human Review",
        "summary": "Email tool use requires human review.",
        "severity": "warning",
        "trace_event_id": TRACE_EVENT_ID,
        "policy_decision_id": POLICY_DECISION_ID,
        "human_approval_id": None,
        "audit_log_id": None,
        "run_id": None,
        "related_ids": {
            "trace_event_id": TRACE_EVENT_ID,
            "policy_decision_id": POLICY_DECISION_ID,
        },
        "metadata": {},
    },
    {
        "id": HUMAN_APPROVAL_ID,
        "type": "human_approval",
        "timestamp": HUMAN_APPROVAL_CREATED_AT,
        "title": "Human approval: Pending",
        "summary": "Email tool use requires human review.",
        "severity": "info",
        "trace_event_id": None,
        "policy_decision_id": POLICY_DECISION_ID,
        "human_approval_id": HUMAN_APPROVAL_ID,
        "audit_log_id": None,
        "run_id": None,
        "related_ids": {
            "policy_decision_id": POLICY_DECISION_ID,
            "human_approval_id": HUMAN_APPROVAL_ID,
        },
        "metadata": {},
    },
]

AGENT_GOVERNANCE_PROFILE_RESPONSE = {
    "agent": AGENT_RESPONSE,
    "owner": {
        "owner_type": AGENT_RESPONSE["owner_type"],
        "owner_id": AGENT_RESPONSE["owner_id"],
        "owner_name": AGENT_RESPONSE["owner_name"],
        "owner_contact_email": AGENT_RESPONSE["owner_contact_email"],
    },
    "environment": AGENT_RESPONSE["environment"],
    "status": AGENT_RESPONSE["status"],
    "risk_level": AGENT_RESPONSE["risk_level"],
    "recent_activity": {
        "limit": 5,
        "items": AGENT_ACTIVITY_RESPONSE,
    },
    "human_approvals": {
        "total_count": 1,
        "by_status": {"pending": 1},
        "recent": [
            {
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
        ],
    },
    "access_grants": [
        {
            **AGENT_ACCESS_GRANT_RESPONSE[0],
            "target": {
                "target_type": "model_asset",
                "id": MODEL_ASSET_ID,
                "name": MODEL_ASSET_RESPONSE["name"],
                "status": MODEL_ASSET_RESPONSE["status"],
                "risk_level": MODEL_ASSET_RESPONSE["risk_level"],
                "external_ref": MODEL_ASSET_RESPONSE["model_ref"],
                "inventory_type": MODEL_ASSET_RESPONSE["model_type"],
                "provider": MODEL_ASSET_RESPONSE["provider"],
                "version": MODEL_ASSET_RESPONSE["version"],
            },
        },
        {
            **AGENT_ACCESS_GRANT_RESPONSE[1],
            "target": {
                "target_type": "source",
                "id": SOURCE_ID,
                "name": SOURCE_RESPONSE["name"],
                "status": SOURCE_RESPONSE["status"],
                "risk_level": SOURCE_RESPONSE["risk_level"],
                "external_ref": SOURCE_RESPONSE["external_ref"],
                "inventory_type": SOURCE_RESPONSE["source_type"],
                "provider": None,
                "version": None,
            },
        },
        {
            **AGENT_ACCESS_GRANT_RESPONSE[2],
            "target": {
                "target_type": "capability",
                "id": CAPABILITY_ID,
                "name": CAPABILITY_RESPONSE["name"],
                "status": CAPABILITY_RESPONSE["status"],
                "risk_level": CAPABILITY_RESPONSE["risk_level"],
                "external_ref": CAPABILITY_RESPONSE["external_ref"],
                "inventory_type": CAPABILITY_RESPONSE["capability_type"],
                "provider": None,
                "version": None,
            },
        },
    ],
    "policy_summary": {
        "policy_decision_count": 1,
        "referenced_policy_ids": [POLICY_ID],
        "referenced_rule_ids": [RULE_ID],
    },
    "evidence_bundle": {
        "available": True,
        "export_path": f"/agents/{AGENT_ID}/evidence-bundle",
        "export_format": "json",
        "access": "allowed",
        "contains_full_evidence": False,
    },
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

POLICY_CREATE_REQUEST = {
    "name": "V0 email tool review policy",
    "description": "Require human review before governed email tool use.",
    "status": "draft",
}

POLICY_RESPONSE = {
    **POLICY_CREATE_REQUEST,
    "id": POLICY_ID,
    "created_at": CREATED_AT,
    "updated_at": UPDATED_AT,
}

POLICY_UPDATE_REQUEST = {
    "status": "active",
    "description": "Active policy for governed email tool use.",
}

POLICY_UPDATED_RESPONSE = {
    **POLICY_RESPONSE,
    **POLICY_UPDATE_REQUEST,
    "updated_at": "2026-01-15T12:10:00Z",
}

POLICY_RULE_CREATE_REQUEST = {
    "policy_id": POLICY_ID,
    "name": "Require review for send_email",
    "description": "Require human review for governed support email.",
    "condition": (
        '{"decision":"require_human_review",'
        '"reason":"Email tool use requires human review.",'
        '"tool_name":"send_email"}'
    ),
}

POLICY_RULE_RESPONSE = {
    **POLICY_RULE_CREATE_REQUEST,
    "id": RULE_ID,
    "created_at": CREATED_AT,
    "updated_at": UPDATED_AT,
}

POLICY_RULE_UPDATE_REQUEST = {
    "description": "Deny declared confidential source vectorization.",
    "condition": (
        '{"decision":"deny",'
        '"reason":"Declared confidential vectorization is denied.",'
        '"tool_name":"vectorize_source",'
        '"action_type":"vectorize",'
        f'"capability_id":"{CAPABILITY_ID}",'
        f'"source_ids":["{SOURCE_ID}"],'
        f'"model_id":"{MODEL_ASSET_ID}",'
        '"purpose":"semantic_search_indexing",'
        '"data_classification":"confidential",'
        '"contains_personal_data":true,'
        '"contains_sensitive_data":false}'
    ),
}

POLICY_RULE_UPDATED_RESPONSE = {
    **POLICY_RULE_RESPONSE,
    **POLICY_RULE_UPDATE_REQUEST,
    "updated_at": "2026-01-15T12:10:00Z",
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

RUNTIME_CONTEXTUAL_TOOL_CALL_DECISION_REQUEST = {
    **RUNTIME_TOOL_CALL_DECISION_REQUEST,
    "request_id": "runtime-request-contextual-001",
    "tool_name": "vectorize_source",
    "action_summary": "Vectorize a governed source for semantic search.",
    "action_type": "vectorize",
    "capability_id": CAPABILITY_ID,
    "source_ids": [SOURCE_ID],
    "model_id": MODEL_ASSET_ID,
    "purpose": "semantic_search_indexing",
    "data_classification": "confidential",
    "contains_personal_data": True,
    "contains_sensitive_data": False,
    "metadata": {
        "ticket_category": "support",
        "embedding_provider_type": "external",
    },
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

RUNTIME_TOOL_CALL_ACTIVITY_RESPONSE = [
    {
        "id": RUNTIME_RESUME_TRACE_EVENT_ID,
        "type": "tool_call_resume",
        "agent_id": AGENT_ID,
        "run_id": RUN_ID,
        "request_id": RUNTIME_RESUME_ID,
        "timestamp": RUNTIME_RESUME_TRACE_EVENT_TIMESTAMP,
        "tool_name": "send_email",
        "mode": None,
        "decision": "allow",
        "proceed": True,
        "reason": "Human approval is approved and the resume context matches.",
        "trace_event_id": RUNTIME_RESUME_TRACE_EVENT_ID,
        "policy_decision_id": POLICY_DECISION_ID,
        "human_approval_id": HUMAN_APPROVAL_ID,
        "action_type": None,
        "capability_id": None,
        "source_ids": [],
        "model_id": None,
        "purpose": None,
        "data_classification": None,
        "contains_personal_data": None,
        "contains_sensitive_data": None,
        "related_ids": {
            "trace_event_id": RUNTIME_RESUME_TRACE_EVENT_ID,
            "policy_decision_id": POLICY_DECISION_ID,
            "human_approval_id": HUMAN_APPROVAL_ID,
            "run_id": RUN_ID,
            "original_request_id": RUNTIME_REQUEST_ID,
        },
    },
    {
        "id": TRACE_EVENT_ID,
        "type": "tool_call_decision",
        "agent_id": AGENT_ID,
        "run_id": RUN_ID,
        "request_id": RUNTIME_REQUEST_ID,
        "timestamp": TRACE_EVENT_TIMESTAMP,
        "tool_name": "send_email",
        "mode": "simulation",
        "decision": "require_human_review",
        "proceed": False,
        "reason": "Email tool use requires human review.",
        "trace_event_id": TRACE_EVENT_ID,
        "policy_decision_id": POLICY_DECISION_ID,
        "human_approval_id": HUMAN_APPROVAL_ID,
        "action_type": "send_email",
        "capability_id": CAPABILITY_ID,
        "source_ids": [],
        "model_id": None,
        "purpose": "customer_support_follow_up",
        "data_classification": "internal",
        "contains_personal_data": True,
        "contains_sensitive_data": False,
        "related_ids": {
            "trace_event_id": TRACE_EVENT_ID,
            "policy_decision_id": POLICY_DECISION_ID,
            "human_approval_id": HUMAN_APPROVAL_ID,
            "run_id": RUN_ID,
        },
    },
]

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
    "access_grants": AGENT_ACCESS_GRANT_RESPONSE,
    "capability_references": [CAPABILITY_RESPONSE],
    "source_references": [SOURCE_RESPONSE],
    "data_usage_profiles": [DATA_USAGE_PROFILE_RESPONSE],
    "model_asset_references": [MODEL_ASSET_RESPONSE],
    "check_results": [
        {
            "check_result_id": CHECK_RESULT_ID,
            "check_tool_id": CHECK_TOOL_ID,
            "check_tool_name": "data_usage_profile_checker",
            "check_tool_type": "data_usage_profile_check",
            "outcome": "pass",
            "confidence": "high",
            "summary": "Data Usage Profile is approved and current.",
            "reason": "Profile review is approved.",
            "target_type": "data_usage_profile",
            "target_id": DATA_USAGE_PROFILE_ID,
            "policy_decision_id": POLICY_DECISION_ID,
            "trace_event_id": TRACE_EVENT_ID,
            "run_id": RUN_ID,
            "created_at": POLICY_DECISION_CREATED_AT,
            "metadata": {
                "check_type": "data_usage_profile_status",
                "review_status": "approved",
            },
        }
    ],
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

AGENT_ACCESS_GRANTS_OPENAPI = _response_example(
    200,
    "Read Access Grants for the V0 demo agent, newest first.",
    AGENT_ACCESS_GRANT_RESPONSE,
)

AGENT_ACTIVITY_OPENAPI = _response_example(
    200,
    "Read the V0 demo agent activity timeline, newest first.",
    AGENT_ACTIVITY_RESPONSE,
)

AGENT_GOVERNANCE_PROFILE_OPENAPI = _response_example(
    200,
    "Read a compact Agent Governance Profile for the V0 demo agent.",
    AGENT_GOVERNANCE_PROFILE_RESPONSE,
)

AGENT_UPDATE_OPENAPI = _request_response_example(
    request_summary="Move the V0 demo agent into review.",
    request_value=AGENT_UPDATE_REQUEST,
    response_status_code=200,
    response_summary="Updated agent.",
    response_value=AGENT_UPDATED_RESPONSE,
)

CAPABILITY_CREATE_OPENAPI = _request_response_example(
    request_summary="Create an inventory record for a governed capability.",
    request_value=CAPABILITY_CREATE_REQUEST,
    response_status_code=201,
    response_summary="Created capability.",
    response_value=CAPABILITY_RESPONSE,
)

CAPABILITY_LIST_OPENAPI = _response_example(
    200,
    "List capabilities including the support email tool.",
    [CAPABILITY_RESPONSE],
)

CAPABILITY_GET_OPENAPI = _response_example(
    200,
    "Read the support email capability.",
    CAPABILITY_RESPONSE,
)

CAPABILITY_UPDATE_OPENAPI = _request_response_example(
    request_summary="Disable a governed capability.",
    request_value=CAPABILITY_UPDATE_REQUEST,
    response_status_code=200,
    response_summary="Updated capability.",
    response_value=CAPABILITY_UPDATED_RESPONSE,
)

SOURCE_CREATE_OPENAPI = _request_response_example(
    request_summary="Create an inventory record for a governed source.",
    request_value=SOURCE_CREATE_REQUEST,
    response_status_code=201,
    response_summary="Created source.",
    response_value=SOURCE_RESPONSE,
)

SOURCE_LIST_OPENAPI = _response_example(
    200,
    "List sources including the support knowledge base.",
    [SOURCE_RESPONSE],
)

SOURCE_GET_OPENAPI = _response_example(
    200,
    "Read the support knowledge base source.",
    SOURCE_RESPONSE,
)

SOURCE_UPDATE_OPENAPI = _request_response_example(
    request_summary="Disable a governed source.",
    request_value=SOURCE_UPDATE_REQUEST,
    response_status_code=200,
    response_summary="Updated source.",
    response_value=SOURCE_UPDATED_RESPONSE,
)

MODEL_ASSET_CREATE_OPENAPI = _request_response_example(
    request_summary="Create an inventory record for a governed model asset.",
    request_value=MODEL_ASSET_CREATE_REQUEST,
    response_status_code=201,
    response_summary="Created model asset.",
    response_value=MODEL_ASSET_RESPONSE,
)

MODEL_ASSET_LIST_OPENAPI = _response_example(
    200,
    "List model assets including the support assistant chat model.",
    [MODEL_ASSET_RESPONSE],
)

MODEL_ASSET_GET_OPENAPI = _response_example(
    200,
    "Read the support assistant chat model asset.",
    MODEL_ASSET_RESPONSE,
)

MODEL_ASSET_UPDATE_OPENAPI = _request_response_example(
    request_summary="Disable a governed model asset.",
    request_value=MODEL_ASSET_UPDATE_REQUEST,
    response_status_code=200,
    response_summary="Updated model asset.",
    response_value=MODEL_ASSET_UPDATED_RESPONSE,
)

ACCESS_GRANT_CREATE_OPENAPI = _request_response_example(
    request_summary="Create an inventory record for a governed access grant.",
    request_value=ACCESS_GRANT_CREATE_REQUEST,
    response_status_code=201,
    response_summary="Created access grant.",
    response_value=ACCESS_GRANT_RESPONSE,
)

ACCESS_GRANT_LIST_OPENAPI = _response_example(
    200,
    "List access grants including the support email capability grant.",
    [ACCESS_GRANT_RESPONSE],
)

ACCESS_GRANT_GET_OPENAPI = _response_example(
    200,
    "Read the support email capability access grant.",
    ACCESS_GRANT_RESPONSE,
)

ACCESS_GRANT_UPDATE_OPENAPI = _request_response_example(
    request_summary="Suspend a governed access grant.",
    request_value=ACCESS_GRANT_UPDATE_REQUEST,
    response_status_code=200,
    response_summary="Updated access grant.",
    response_value=ACCESS_GRANT_UPDATED_RESPONSE,
)

POLICY_CREATE_OPENAPI = _request_response_example(
    request_summary="Create a policy lifecycle record.",
    request_value=POLICY_CREATE_REQUEST,
    response_status_code=201,
    response_summary="Created policy.",
    response_value=POLICY_RESPONSE,
)

POLICY_LIST_OPENAPI = _response_example(
    200,
    "List policies including the V0 email tool review policy.",
    [POLICY_RESPONSE],
)

POLICY_GET_OPENAPI = _response_example(
    200,
    "Read the V0 email tool review policy.",
    POLICY_RESPONSE,
)

POLICY_UPDATE_OPENAPI = _request_response_example(
    request_summary="Activate a policy lifecycle record.",
    request_value=POLICY_UPDATE_REQUEST,
    response_status_code=200,
    response_summary="Updated policy.",
    response_value=POLICY_UPDATED_RESPONSE,
)

POLICY_RULE_CREATE_OPENAPI = _request_response_example(
    request_summary="Create a deterministic PolicyRule.",
    request_value=POLICY_RULE_CREATE_REQUEST,
    response_status_code=201,
    response_summary="Created PolicyRule.",
    response_value=POLICY_RULE_RESPONSE,
)

POLICY_RULE_LIST_OPENAPI = _response_example(
    200,
    "List PolicyRules including the send_email review rule.",
    [POLICY_RULE_RESPONSE],
)

POLICY_RULE_GET_OPENAPI = _response_example(
    200,
    "Read the send_email review PolicyRule.",
    POLICY_RULE_RESPONSE,
)

POLICY_RULE_UPDATE_OPENAPI = _request_response_example(
    request_summary="Update a deterministic PolicyRule.",
    request_value=POLICY_RULE_UPDATE_REQUEST,
    response_status_code=200,
    response_summary="Updated PolicyRule.",
    response_value=POLICY_RULE_UPDATED_RESPONSE,
)

POLICY_RULES_FOR_POLICY_OPENAPI = _response_example(
    200,
    "List PolicyRules for the V0 email tool review policy.",
    [POLICY_RULE_RESPONSE],
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
                    "contextualDecision": _named_example(
                        "Simulate a contextual RAG/vectorization request.",
                        RUNTIME_CONTEXTUAL_TOOL_CALL_DECISION_REQUEST,
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

RUNTIME_TOOL_CALL_ACTIVITY_OPENAPI = _response_example(
    200,
    "List Runtime Gateway tool-call activity, newest first.",
    RUNTIME_TOOL_CALL_ACTIVITY_RESPONSE,
)

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
