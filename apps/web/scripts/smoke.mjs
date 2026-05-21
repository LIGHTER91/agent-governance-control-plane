import { readFile } from "node:fs/promises";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

const root = fileURLToPath(new URL("..", import.meta.url));

const files = [
  "app/layout.tsx",
  "app/page.tsx",
  "app/agents/page.tsx",
  "app/agents/agents-list.tsx",
  "app/agents/[agentId]/page.tsx",
  "app/agents/[agentId]/agent-detail.tsx",
  "app/lib/api.ts",
  "app/lib/agents.ts",
  "app/lib/human-approvals.ts",
  "app/policies/page.tsx",
  "app/runtime-gateway/page.tsx",
  "app/human-approvals/page.tsx",
  "app/human-approvals/human-approval-actions.tsx",
  "app/human-approvals/human-approvals-list.tsx",
  "app/lib/evidence.ts",
  "app/evidence/page.tsx",
  "app/evidence/evidence-bundle-viewer.tsx",
  "app/audit/page.tsx",
  "app/settings/page.tsx"
];

const source = (
  await Promise.all(files.map((file) => readFile(join(root, file), "utf8")))
).join("\n");

const requiredText = [
  "Agents",
  "Policies",
  "Runtime Gateway",
  "Human Approvals",
  "Evidence",
  "Audit",
  "Settings",
  "Agent Registry",
  "GET /agents",
  "NEXT_PUBLIC_AGCP_API_BASE_URL",
  "Loading agents",
  "Unable to load agents",
  "No agents registered",
  "owner_name",
  "owner_id",
  "owner_type",
  "/agents/${encodeURIComponent(agent.id)}",
  "GET /agents/{agent_id}",
  "GET /agents/{agent_id}/human-approvals",
  "environment",
  "status",
  "risk_level",
  "framework",
  "Agent overview",
  "Governance summary",
  "Human approvals",
  "Activity / Timeline",
  "GET /agents/{agent_id}/activity",
  "Loading Agent activity",
  "Unable to load Agent activity",
  "No activity records for this Agent",
  "Agent activity requires reviewer, auditor, or platform_admin role",
  "severity",
  "related_ids",
  "activity-severity",
  "severity-${severity}",
  "activityRelatedIds",
  "activityMetadataEntries",
  "Related IDs",
  "Filtered metadata",
  "trace_event_id",
  "audit_log_id",
  "run_id",
  "Evidence access",
  "Runtime / policy decisions",
  "Loading Agent detail",
  "Unable to load Agent detail",
  "Evidence Bundle export requires an auditor or platform_admin role",
  "GET /human-approvals",
  "Loading human approvals",
  "Unable to load human approvals",
  "No human approvals",
  "policy_decision_id",
  "requested_by_actor_type",
  "requested_by_actor_id",
  "reviewed_by_actor_type",
  "reviewed_by_actor_id",
  "expires_at",
  "Actions",
  "approval.status !== \"pending\"",
  "Only pending HumanApprovals can be reviewed from this UI.",
  "HumanApproval review actions",
  "Decision note",
  "Optional for approve or reject",
  "Approve",
  "Reject",
  "Cancel",
  "Approving",
  "Rejecting",
  "Cancelling",
  "transitionHumanApproval",
  "decision_note",
  "This actor is not allowed to perform this HumanApproval action.",
  "Unable to update HumanApproval",
  "review-action-message",
  "Refreshing the review queue",
  "Refreshing Agent governance records",
  "pending",
  "approved",
  "rejected",
  "cancelled",
  "expired",
  "Human Approval",
  "Evidence Bundle",
  "GET /agents/{agent_id}/evidence-bundle",
  "Loading Evidence Bundle",
  "Unable to load Evidence Bundle",
  "Evidence Bundle export requires an auditor or platform_admin role",
  "Agent not found",
  "audit_logs",
  "agent_runs",
  "trace_events",
  "policy_decisions",
  "human_approvals",
  "simulation",
  "enforcement",
  "resume",
  "POST /runtime/tool-calls/decision",
  "POST /runtime/tool-calls/resume",
  "AGCP_RUNTIME_ENFORCEMENT_ENABLED",
  "AGCP_RUNTIME_FAILURE_DEFAULT",
  "AGCP_REQUIRE_SERVICE_AUTH",
  "AGCP_SERVICE_ACTOR_API_KEYS",
  "AGCP_SERVICE_ACTOR_SCOPES",
  "AGCP_SERVICE_ACTOR_SCOPE_RULES",
  "AGCP decides and records evidence",
  "Wrappers/adapters execute or block",
  "AGCP does not execute tools itself",
  "No production-grade auth yet",
  "No API key rotation",
  "No DB-backed service actor registry",
  "No LangGraph production adapter yet",
  "RBAC Foundations"
];

const forbiddenText = [
  "compliance score",
  "AI Act compliant",
  "ISO 42001 certified",
  "production-ready",
  "fully compliant"
];

for (const text of requiredText) {
  if (!source.includes(text)) {
    throw new Error(`Missing expected dashboard text: ${text}`);
  }
}

const normalizedSource = source.toLowerCase();

for (const text of forbiddenText) {
  if (normalizedSource.includes(text.toLowerCase())) {
    throw new Error(`Forbidden dashboard claim found: ${text}`);
  }
}

runActivityTimelineFixtureSmoke();

console.log("Dashboard shell smoke check passed.");

function runActivityTimelineFixtureSmoke() {
  const traceEventId = "11111111-1111-4111-8111-111111111111";
  const policyDecisionId = "22222222-2222-4222-8222-222222222222";
  const humanApprovalId = "33333333-3333-4333-8333-333333333333";
  const auditLogId = "44444444-4444-4444-8444-444444444444";
  const runId = "55555555-5555-4555-8555-555555555555";

  const fixture = [
    {
      id: traceEventId,
      type: "trace_event",
      timestamp: "2026-01-15T12:05:00Z",
      title: "Trace event: Tool Call Requested",
      summary: "Agent requested a governed tool.",
      severity: "info",
      related_ids: {
        trace_event_id: traceEventId,
        run_id: runId
      },
      metadata: {
        tool_name: "send_email",
        source: "runtime_gateway"
      }
    },
    {
      id: policyDecisionId,
      type: "policy_decision",
      timestamp: "2026-01-15T12:05:01Z",
      title: "Policy decision: Require Human Review",
      summary: "Policy required review.",
      severity: "warning",
      related_ids: {
        trace_event_id: traceEventId,
        policy_decision_id: policyDecisionId
      }
    },
    {
      id: humanApprovalId,
      type: "human_approval",
      timestamp: "2026-01-15T12:05:02Z",
      title: "Human approval: Pending",
      summary: "Human oversight was requested.",
      severity: "info",
      related_ids: {
        human_approval_id: humanApprovalId,
        policy_decision_id: policyDecisionId
      },
      metadata: {}
    },
    {
      id: auditLogId,
      type: "audit_log",
      timestamp: "2026-01-15T12:05:03Z",
      title: "Audit log: Runtime Gateway Failure",
      summary: "Runtime Gateway recorded a controlled error.",
      severity: "error",
      related_ids: {
        audit_log_id: auditLogId,
        trace_event_id: traceEventId,
        policy_decision_id: policyDecisionId,
        human_approval_id: humanApprovalId,
        run_id: runId
      },
      metadata: {
        failure_type: "policy_evaluation_error"
      }
    }
  ];

  const renderedTimeline = renderActivityTimelineFixture(fixture);
  const emptyTimeline = renderActivityTimelineFixture([]);

  for (const expectedText of [
    "Trace Event",
    "Policy Decision",
    "Human Approval",
    "Audit Log",
    "Info",
    "Warning",
    "Error",
    "Related IDs",
    "trace_event_id",
    "policy_decision_id",
    "human_approval_id",
    "audit_log_id",
    "run_id",
    traceEventId,
    policyDecisionId,
    humanApprovalId,
    auditLogId,
    runId,
    "Filtered metadata",
    "tool_name",
    "send_email",
    "source",
    "runtime_gateway",
    "failure_type",
    "policy_evaluation_error"
  ]) {
    if (!renderedTimeline.includes(expectedText)) {
      throw new Error(`Activity timeline fixture missing: ${expectedText}`);
    }
  }

  const policyDecisionSection = renderActivityTimelineFixture([fixture[1]]);
  if (policyDecisionSection.includes("Filtered metadata")) {
    throw new Error("Activity timeline rendered metadata for an item without metadata.");
  }

  if (!emptyTimeline.includes("No activity records for this Agent")) {
    throw new Error("Activity timeline fixture did not cover the empty state.");
  }

  for (const unsafeText of [
    "api_key",
    "token",
    "password",
    "secret",
    "authorization",
    "raw_prompt",
    "raw_payload",
    "compliance score"
  ]) {
    if (renderedTimeline.toLowerCase().includes(unsafeText)) {
      throw new Error(`Unsafe fixture text rendered: ${unsafeText}`);
    }
  }
}

function renderActivityTimelineFixture(items) {
  if (items.length === 0) {
    return "No activity records for this Agent";
  }

  return items.map(renderActivityFixtureItem).join("\n");
}

function renderActivityFixtureItem(item) {
  const parts = [
    formatActivityValue(item.type),
    formatActivityValue(item.severity),
    item.title,
    item.summary || "No summary provided."
  ];

  const relatedIds = Object.entries(item.related_ids || {});
  if (relatedIds.length > 0) {
    parts.push("Related IDs");
    for (const [key, value] of relatedIds) {
      parts.push(key, value);
    }
  }

  const metadataEntries = Object.entries(item.metadata || {});
  if (metadataEntries.length > 0) {
    parts.push("Filtered metadata");
    for (const [key, value] of metadataEntries) {
      parts.push(key, String(value));
    }
  }

  return parts.join("\n");
}

function formatActivityValue(value) {
  if (!value) {
    return "Not set";
  }

  return value
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}
