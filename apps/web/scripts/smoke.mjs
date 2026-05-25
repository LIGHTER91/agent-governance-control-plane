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
  "app/lib/runtime.ts",
  "app/lib/human-approvals.ts",
  "app/policies/page.tsx",
  "app/runtime-gateway/page.tsx",
  "app/runtime-gateway/runtime-activity-list.tsx",
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
  "Agent Governance Profile",
  "GET /agents/{agent_id}/governance-profile",
  "fetchAgentGovernanceProfile",
  "AgentGovernanceProfile",
  "Governance summary",
  "Access Grants",
  "Recent Activity",
  "Pending Human Approvals",
  "Evidence Bundle availability hint",
  "Inventory access",
  "Capabilities",
  "Sources",
  "Model assets",
  "External grants",
  "Policy and rule references",
  "Policy/rule technical references",
  "Agent technical reference",
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
  "Decision requests",
  "Resume checks",
  "GET /runtime/tool-calls/activity",
  "Loading Runtime activity",
  "Unable to load Runtime activity",
  "No Runtime activity records",
  "Runtime activity requires reviewer, auditor, or platform_admin role",
  "Runtime decisions activity",
  "tool_call_decision",
  "tool_call_resume",
  "tool_name",
  "mode",
  "decision",
  "proceed",
  "request_id"
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
runRuntimeActivityFixtureSmoke();
runAgentGovernanceProfileFixtureSmoke();

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

function runRuntimeActivityFixtureSmoke() {
  const traceEventId = "11111111-1111-4111-8111-111111111111";
  const policyDecisionId = "22222222-2222-4222-8222-222222222222";
  const humanApprovalId = "33333333-3333-4333-8333-333333333333";
  const runId = "44444444-4444-4444-8444-444444444444";

  const fixture = [
    {
      id: traceEventId,
      type: "tool_call_decision",
      agent_id: "55555555-5555-4555-8555-555555555555",
      run_id: runId,
      request_id: "runtime-request-001",
      timestamp: "2026-01-15T12:05:00Z",
      tool_name: "send_email",
      mode: "simulation",
      decision: "require_human_review",
      proceed: false,
      reason: "Email tool use requires human review.",
      trace_event_id: traceEventId,
      policy_decision_id: policyDecisionId,
      human_approval_id: humanApprovalId,
      related_ids: {
        trace_event_id: traceEventId,
        policy_decision_id: policyDecisionId,
        human_approval_id: humanApprovalId,
        run_id: runId
      }
    },
    {
      id: "66666666-6666-4666-8666-666666666666",
      type: "tool_call_resume",
      agent_id: "55555555-5555-4555-8555-555555555555",
      run_id: runId,
      request_id: "runtime-request-001:resume:001",
      timestamp: "2026-01-15T12:10:00Z",
      tool_name: "send_email",
      mode: null,
      decision: "allow",
      proceed: true,
      reason: "Human approval is approved and the resume context matches.",
      trace_event_id: "66666666-6666-4666-8666-666666666666",
      policy_decision_id: policyDecisionId,
      human_approval_id: humanApprovalId,
      related_ids: {
        original_request_id: "runtime-request-001"
      }
    }
  ];

  const renderedActivity = renderRuntimeActivityFixture(fixture);
  const emptyActivity = renderRuntimeActivityFixture([]);

  for (const expectedText of [
    "Tool Call Decision",
    "Tool Call Resume",
    "send_email",
    "simulation",
    "Not persisted",
    "require_human_review",
    "allow",
    "proceed=false",
    "proceed=true",
    "Email tool use requires human review.",
    "Human approval is approved and the resume context matches.",
    "trace_event_id",
    "policy_decision_id",
    "human_approval_id",
    "original_request_id",
    traceEventId,
    policyDecisionId,
    humanApprovalId,
    runId
  ]) {
    if (!renderedActivity.includes(expectedText)) {
      throw new Error(`Runtime activity fixture missing: ${expectedText}`);
    }
  }

  if (!emptyActivity.includes("No Runtime activity records")) {
    throw new Error("Runtime activity fixture did not cover the empty state.");
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
    if (renderedActivity.toLowerCase().includes(unsafeText)) {
      throw new Error(`Unsafe runtime fixture text rendered: ${unsafeText}`);
    }
  }
}

function renderRuntimeActivityFixture(items) {
  if (items.length === 0) {
    return "No Runtime activity records";
  }

  return items.map(renderRuntimeActivityFixtureItem).join("\n");
}

function renderRuntimeActivityFixtureItem(item) {
  const parts = [
    formatActivityValue(item.type),
    item.tool_name || "Not persisted",
    item.mode || "Not persisted",
    item.decision || "Not persisted",
    `proceed=${item.proceed === null ? "Not persisted" : String(item.proceed)}`,
    item.reason || "No reason was persisted for this activity record."
  ];

  for (const field of ["agent_id", "run_id", "request_id"]) {
    parts.push(field, item[field] || "Not persisted");
  }

  const relatedIds = Object.entries(item.related_ids || {});
  if (relatedIds.length > 0) {
    parts.push("Related IDs");
    for (const [key, value] of relatedIds) {
      parts.push(key, value);
    }
  }

  return parts.join("\n");
}

function runAgentGovernanceProfileFixtureSmoke() {
  const fixture = {
    agent: {
      id: "agent-001",
      name: "Claims Assistant",
      environment: "production",
      status: "active",
      risk_level: "high"
    },
    owner: {
      owner_name: "Claims Ops",
      owner_type: "user",
      owner_id: "owner-001"
    },
    recent_activity: {
      limit: 5,
      items: [
        {
          type: "policy_decision",
          title: "Policy decision: Require Human Review"
        }
      ]
    },
    human_approvals: {
      total_count: 2,
      by_status: {
        pending: 1,
        approved: 1
      }
    },
    access_grants: [
      {
        target_type: "capability",
        target: {
          name: "Send email",
          inventory_type: "tool"
        },
        status: "active"
      },
      {
        target_type: "source",
        target: {
          name: "Claims knowledge base",
          inventory_type: "knowledge_base"
        },
        status: "active"
      },
      {
        target_type: "model_asset",
        target: {
          name: "Triage model",
          inventory_type: "llm"
        },
        status: "active"
      },
      {
        target_type: "external",
        external_ref: "ticketing:claims",
        status: "active"
      }
    ],
    policy_summary: {
      policy_decision_count: 1,
      referenced_policy_ids: ["policy-001"],
      referenced_rule_ids: ["rule-001"]
    },
    evidence_bundle: {
      available: true,
      export_format: "json",
      export_path: "/agents/agent-001/evidence-bundle",
      access: "allowed"
    }
  };

  const renderedProfile = renderAgentGovernanceProfileFixture(fixture);

  for (const expectedText of [
    "Claims Assistant",
    "Claims Ops",
    "Active",
    "Production",
    "High",
    "Access Grants",
    "Capabilities",
    "Sources",
    "Model assets",
    "External grants",
    "Send email",
    "Claims knowledge base",
    "Triage model",
    "ticketing:claims",
    "Recent Activity",
    "Pending Human Approvals",
    "Evidence Bundle",
    "available",
    "Policy/rule technical references",
    "policy-001",
    "rule-001"
  ]) {
    if (!renderedProfile.includes(expectedText)) {
      throw new Error(`Agent profile fixture missing: ${expectedText}`);
    }
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
    if (renderedProfile.toLowerCase().includes(unsafeText)) {
      throw new Error(`Unsafe Agent profile fixture text rendered: ${unsafeText}`);
    }
  }
}

function renderAgentGovernanceProfileFixture(profile) {
  const parts = [
    "Agent Governance Profile",
    profile.agent.name,
    profile.owner.owner_name,
    formatActivityValue(profile.agent.status),
    formatActivityValue(profile.agent.environment),
    formatActivityValue(profile.agent.risk_level),
    "Access Grants",
    String(profile.access_grants.length),
    "Recent Activity",
    String(profile.recent_activity.items.length),
    "Pending Human Approvals",
    String(profile.human_approvals.by_status.pending || 0),
    "Evidence Bundle",
    profile.evidence_bundle.available ? "available" : "not_available",
    "Policy/rule technical references",
    ...profile.policy_summary.referenced_policy_ids,
    ...profile.policy_summary.referenced_rule_ids
  ];

  for (const group of ["capability", "source", "model_asset", "external"]) {
    parts.push(agentProfileGroupLabel(group));
    for (const grant of profile.access_grants.filter(
      (item) => item.target_type === group
    )) {
      parts.push(grant.target?.name || grant.external_ref || "Unresolved target");
    }
  }

  return parts.join("\n");
}

function agentProfileGroupLabel(targetType) {
  if (targetType === "capability") {
    return "Capabilities";
  }

  if (targetType === "source") {
    return "Sources";
  }

  if (targetType === "model_asset") {
    return "Model assets";
  }

  return "External grants";
}
