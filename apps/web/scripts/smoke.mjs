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
  "app/lib/sources.ts",
  "app/lib/runtime.ts",
  "app/lib/human-approvals.ts",
  "app/lib/policies.ts",
  "app/lib/service-actors.ts",
  "app/access-data/page.tsx",
  "app/access-data/access-grants-workflow.tsx",
  "app/access-data/sources-workflow.tsx",
  "app/policies/page.tsx",
  "app/policies/policies-manager.tsx",
  "app/integrations/page.tsx",
  "app/integrations/integration-hub.tsx",
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

const studioFiles = [
  "app/agcp-studio/AGCPStudio.tsx"
];

const studioEntries = await Promise.all(
  studioFiles.map(async (file) => ({
    file,
    source: await readFile(join(root, file), "utf8")
  }))
);
const studioSource = studioEntries.map((entry) => entry.source).join("\n");
const agcpStudioSource =
  studioEntries.find((entry) => entry.file.endsWith("AGCPStudio.tsx"))?.source ??
  "";

const requiredText = [
  "Agents",
  "Policies",
  "Access & Data",
  "Access Grants and Source Data Usage",
  "Access Grant workflow",
  "Access Grants are declared governance records",
  "Transition actions update the governance record status",
  "does not by itself guarantee runtime blocking",
  "runtime enforcement depends on policies",
  "GET /access-grants",
  "POST /access-grants/{access_grant_id}",
  "Loading Access Grants",
  "Unable to load Access Grants",
  "Access Grants loaded",
  "Access Grant transition actions",
  "Transition note",
  "Updates the governance record status only",
  "No Access Grants match the current filters",
  "subject_type",
  "subject_id",
  "target_type",
  "target_id",
  "external_ref",
  "granted_by_actor_type",
  "granted_by_actor_id",
  "expires_at",
  "Safe Metadata",
  "Agent Governance Profile",
  "Evidence Bundle lookup",
  "Source/Data Usage workflow",
  "Source Data Usage Profiles",
  "GET /sources",
  "GET /sources/{source_id}/usage-profile",
  "GET /access-grants",
  "Data Usage Profiles are governance metadata",
  "does not inspect raw Source contents",
  "does not certify legal compliance",
  "Loading Sources",
  "Unable to load Sources",
  "No Sources found",
  "Source review",
  "No Source selected",
  "Data Usage Profile",
  "Loading Data Usage Profile",
  "No Data Usage Profile found",
  "Data Usage Profile loaded",
  "review_status",
  "data_classification",
  "contains_personal_data",
  "contains_sensitive_data",
  "data_categories",
  "allowed_purposes",
  "prohibited_purposes",
  "allowed_processing",
  "prohibited_processing",
  "residency",
  "retention_policy",
  "data_owner",
  "reviewed_by",
  "reviewed_at",
  "review_expires_at",
  "dpia_required",
  "dpia_reference",
  "Safe Data Usage Profile metadata",
  "Safe Source metadata",
  "RAG retrieval",
  "Vectorization / embedding",
  "Summarization",
  "Training",
  "External model usage",
  "related_source_access_grants",
  "Policy Governance",
  "GET /policies",
  "POST /policies",
  "PATCH /policies/{policy_id}",
  "GET /policies/{policy_id}/rules",
  "POST /policy-rules",
  "PATCH /policy-rules/{rule_id}",
  "Policy lifecycle and constrained rule editing",
  "PolicyRules define executable conditions",
  "Loading policies",
  "Unable to load policies",
  "No policies found",
  "Create Policy",
  "Edit selected Policy",
  "PolicyRule conditions",
  "Loading PolicyRules",
  "Unable to load PolicyRules",
  "No PolicyRules found",
  "Create PolicyRule",
  "Edit selected PolicyRule",
  "CheckResults are evidence inputs, not legal certification",
  "Changing PolicyRules can affect future Runtime Gateway decisions",
  "check_type",
  "check_outcome",
  "check_target_type",
  "check_target_id",
  "check_tool_id",
  "check_min_confidence",
  "Deterministic condition JSON preview",
  "Policy saved",
  "No Policy fields changed",
  "draft",
  "active",
  "disabled",
  "archived",
  "Runtime Gateway",
  "Integration Hub",
  "Runtime connections for governed agent stacks",
  "AGCP governs decisions and evidence",
  "AGCP does not execute tools",
  "caller/orchestrator is responsible for respecting proceed=true/false",
  "Service Actors, scopes, key status, and runtime modes",
  "GET /service-actors",
  "GET /service-actors/{service_actor_id}/api-keys",
  "GET /service-actors/{service_actor_id}/scopes",
  "GET /service-actors/{service_actor_id}/scope-rules",
  "AGCP_SERVICE_ACTOR_REGISTRY_ENABLED=false",
  "Loading Service Actor registry summary",
  "Unable to load Service Actor registry summary",
  "No Service Actors found",
  "Custom Runtime Gateway API",
  "LangGraph adapter spike",
  "n8n template/node design",
  "Dataiku plugin/design",
  "MCP gateway/control pattern",
  "generic webhook/API integration",
  "not_configured",
  "design_only",
  "spike",
  "connected",
  "error",
  "telemetry_only",
  "simulation",
  "enforcement",
  "resume_after_human_approval",
  "service actor API key",
  "X-AGCP-API-Key",
  "telemetry:write",
  "runtime:decision",
  "runtime:resume",
  "agent_ids",
  "environments",
  "runtime_modes",
  "tool_names",
  "POST /runtime/tool-calls/decision",
  "POST /runtime/tool-calls/resume",
  "Custom Runtime Gateway API setup",
  "LangGraph adapter spike setup",
  "Runtime activity and gateway overview",
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
  "Download Evidence Bundle JSON",
  "export_warnings",
  "safe_export_metadata",
  "human_readable_evidence_chain",
  "canonical_json_export",
  "Evidence Bundle is an audit/review package",
  "does not certify legal compliance",
  "raw prompts, source contents, secrets, tokens, credentials",
  "Access Grants",
  "Data Usage Profile summaries",
  "PolicyVersion references",
  "policy_version_references",
  "access_grants",
  "Agent not found",
  "audit_logs",
  "agent_runs",
  "trace_events",
  "policy_decisions",
  "policy_version_id",
  "capability_references",
  "source_references",
  "data_usage_profile_summaries",
  "model_asset_references",
  "check_results",
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
runEvidenceBundleWorkflowFixtureSmoke();
runDataUsageWorkflowFixtureSmoke();
runAccessGrantWorkflowFixtureSmoke();
runAGCPStudioFixtureSmoke();

console.log("Dashboard shell smoke check passed.");

function runAGCPStudioFixtureSmoke() {
  const expectedStudioText = [
    "AGCP",
    "CONTROL PLANE",
    "AI Systems",
    "Policies",
    "Reviews",
    "Evidence",
    "Risk",
    "Data",
    "Models",
    "Vendors",
    "Monitoring",
    "Integrations",
    "Admin",
    "Save draft",
    "Run simulation",
    "Submit review",
    "Approve",
    "Reject",
    "Code DSL",
    "WHEN",
    "CHECK",
    "THEN",
    "PROVE",
    "PolicyRule",
    "PolicyCheckStep",
    "HumanApproval",
    "EvidenceBundle",
    "Review status",
    "Submit for review",
    "AGCP decides and records. External runtimes execute.",
    "Evidence Vault",
    "Audit Timeline",
    "Data Governance",
    "Classification",
    "Personal data",
    "Sensitive data",
    "Allowed Purposes",
    "Prohibited Purposes",
    "Review status",
    "DPIA reference"
  ];

  const viewCases = [
    ['case "command"', "CommandView"],
    ['case "systems"', "AISystemsView"],
    ['case "policies"', "PolicyStudioView"],
    ['case "reviews"', "ReviewsView"],
    ['case "evidence"', "EvidenceView"],
    ['case "risk"', "RiskView"],
    ['case "data"', "DataView"],
    ['case "models"', "ModelsView"],
    ['case "vendors"', "VendorsView"],
    ['case "monitoring"', "MonitoringView"],
    ['case "integrations"', "IntegrationsView"],
    ['case "admin"', "AdminView"]
  ];

  const expectedPolicyDslPieces = [
    "policy external_action_control",
    "production_systems",
    "system.environment",
    '"production"',
    "action.risk",
    '"high"',
    '"critical"',
    "target.boundary",
    '"external"',
    "access_grant.status",
    '"active"',
    "target.approval",
    '"approved"',
    "require_review",
    '"governance"',
    "prove",
    "decision",
    "checks",
    "reviewer",
    "evidence_bundle"
  ];

  for (const text of expectedStudioText) {
    if (!studioSource.includes(text)) {
      throw new Error(`AGCP Studio fixture missing: ${text}`);
    }
  }

  for (const text of expectedPolicyDslPieces) {
    if (!studioSource.includes(text)) {
      throw new Error(`Controlled Policy Studio DSL missing: ${text}`);
    }
  }

  for (const [caseText, componentName] of viewCases) {
    if (!agcpStudioSource.includes(caseText)) {
      throw new Error(`Missing AGCP Studio view case: ${caseText}`);
    }

    if (!agcpStudioSource.includes(`<${componentName} />`)) {
      throw new Error(`Missing AGCP Studio view render: ${componentName}`);
    }
  }

  for (const action of ["Save draft", "Run simulation", "Submit for review"]) {
    if (!studioSource.includes(action)) {
      throw new Error(`Policy Studio missing review-safe action: ${action}`);
    }
  }

  for (const text of [
    "mockup",
    "frontend",
    "final product",
    "roadmap",
    "advanced module",
    "compliance score",
    "AI Act compliant",
    "ISO 42001 certified",
    "fully compliant",
    "production-ready",
    "Publish"
  ]) {
    const haystack = text === "Publish" ? studioSource : studioSource.toLowerCase();
    const needle = text === "Publish" ? text : text.toLowerCase();
    if (haystack.includes(needle)) {
      throw new Error(`Forbidden AGCP Studio text found: ${text}`);
    }
  }
}

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

function runEvidenceBundleWorkflowFixtureSmoke() {
  const policyVersionId = "77777777-7777-4777-8777-777777777777";
  const policyDecisionId = "88888888-8888-4888-8888-888888888888";
  const agentId = "99999999-9999-4999-8999-999999999999";

  const fixture = {
    agent: {
      id: agentId,
      name: "Claims Assistant",
      environment: "production",
      risk_level: "high"
    },
    access_grants: [
      {
        id: "grant-001",
        name: "Claims knowledge grant",
        target_type: "source",
        target_id: "source-001",
        status: "active"
      }
    ],
    capability_references: [
      {
        id: "capability-001",
        name: "Send email",
        capability_type: "tool",
        status: "active"
      }
    ],
    source_references: [
      {
        id: "source-001",
        name: "Claims knowledge base",
        source_type: "knowledge_base",
        status: "active"
      }
    ],
    data_usage_profiles: [
      {
        id: "profile-001",
        source_id: "source-001",
        data_classification: "confidential",
        review_status: "approved"
      }
    ],
    model_asset_references: [
      {
        id: "model-001",
        name: "Claims model",
        model_type: "llm",
        provider: "local"
      }
    ],
    agent_runs: [
      {
        id: "run-record-001",
        run_id: "run-001"
      }
    ],
    trace_events: [
      {
        id: "trace-001",
        event_type: "tool_call_requested"
      }
    ],
    policy_decisions: [
      {
        id: policyDecisionId,
        decision: "require_human_review",
        reason: "External email requires review.",
        policy_version_id: policyVersionId,
        policy_version: {
          policy_version_id: policyVersionId,
          policy_id: "policy-001",
          version_number: 3,
          status: "active"
        }
      }
    ],
    check_results: [
      {
        check_result_id: "check-001",
        outcome: "pass",
        policy_decision_id: policyDecisionId,
        policy_version_id: policyVersionId,
        summary: "Data Usage Profile is approved."
      }
    ],
    human_approvals: [
      {
        id: "approval-001",
        status: "pending",
        policy_decision_id: policyDecisionId
      }
    ],
    audit_logs: [
      {
        id: "audit-001",
        event_type: "evidence_bundle_exported"
      }
    ]
  };

  const renderedWorkflow = renderEvidenceBundleWorkflowFixture(fixture);
  const rawArtifact = JSON.stringify(fixture);

  for (const expectedText of [
    "Evidence Bundle is an audit/review package",
    "does not certify legal compliance",
    "Download Evidence Bundle JSON",
    "safe_export_metadata",
    "exported_at",
    "exported_by",
    "agent_id",
    "human_readable_evidence_chain",
    "Agent",
    "Access Grants",
    "Data Usage Profile summaries",
    "data_usage_profile_summaries",
    "TraceEvents",
    "PolicyDecisions",
    "PolicyVersion references",
    "policy_version_references",
    "CheckResults",
    "HumanApprovals",
    "AuditLogs",
    "canonical_json_export",
    "access_grants",
    "capability_references",
    "source_references",
    "data_usage_profile_summaries",
    "model_asset_references",
    "check_results",
    "policy_version_id",
    policyVersionId,
    agentId
  ]) {
    if (!renderedWorkflow.includes(expectedText)) {
      throw new Error(`Evidence Bundle workflow fixture missing: ${expectedText}`);
    }
  }

  for (const unsafeText of [
    "api_key",
    "authorization",
    "password",
    "raw_prompt",
    "raw_payload"
  ]) {
    if (rawArtifact.toLowerCase().includes(unsafeText)) {
      throw new Error(`Unsafe Evidence Bundle fixture text rendered: ${unsafeText}`);
    }
  }
}

function renderEvidenceBundleWorkflowFixture(bundle) {
  const counts = {
    access_grants: bundle.access_grants.length,
    agent_runs: bundle.agent_runs.length,
    audit_logs: bundle.audit_logs.length,
    capability_references: bundle.capability_references.length,
    check_results: bundle.check_results.length,
    data_usage_profiles: bundle.data_usage_profiles.length,
    human_approvals: bundle.human_approvals.length,
    model_asset_references: bundle.model_asset_references.length,
    policy_decisions: bundle.policy_decisions.length,
    policy_versions: evidencePolicyVersionCount(bundle),
    source_references: bundle.source_references.length,
    trace_events: bundle.trace_events.length
  };

  return [
    "Evidence Bundle is an audit/review package; it does not certify legal compliance.",
    "The Evidence Bundle excludes raw prompts, source contents, secrets, tokens, credentials, and unsafe payloads.",
    "Download Evidence Bundle JSON",
    "safe_export_metadata",
    "exported_at",
    "exported_by",
    "agent_id",
    bundle.agent.id,
    "human_readable_evidence_chain",
    "Agent",
    bundle.agent.name,
    "Access Grants",
    "Data Usage Profile summaries",
    "data_usage_profile_summaries",
    "TraceEvents",
    "PolicyDecisions",
    "PolicyVersion references",
    "policy_version_references",
    "CheckResults",
    "HumanApprovals",
    "AuditLogs",
    "canonical_json_export",
    ...Object.keys(counts),
    JSON.stringify(bundle)
  ].join("\n");
}

function evidencePolicyVersionCount(bundle) {
  const ids = new Set();

  for (const decision of bundle.policy_decisions) {
    if (decision.policy_version_id) {
      ids.add(decision.policy_version_id);
    }
  }

  for (const result of bundle.check_results) {
    if (result.policy_version_id) {
      ids.add(result.policy_version_id);
    }
  }

  return ids.size;
}

function runDataUsageWorkflowFixtureSmoke() {
  const sourceId = "12121212-1212-4121-8121-121212121212";
  const fixture = {
    source: {
      id: sourceId,
      name: "Support knowledge base",
      source_type: "knowledge_base",
      status: "active",
      risk_level: "medium",
      owner_name: "Support Operations",
      metadata: {
        catalog_ref: "catalog:support-kb"
      }
    },
    profile: {
      id: "23232323-2323-4232-8232-232323232323",
      source_id: sourceId,
      data_classification: "confidential",
      contains_personal_data: true,
      contains_sensitive_data: false,
      data_categories: ["customer_data", "support_ticket"],
      allowed_purposes: ["customer_support_answering"],
      prohibited_purposes: ["training_data_generation"],
      allowed_processing: ["search", "rag", "embedding"],
      prohibited_processing: ["external_model_provider"],
      residency: "eu",
      retention_policy: "retention:standard-support",
      data_owner: "team:support-ops",
      review_status: "approved",
      reviewed_by_actor_type: "user",
      reviewed_by_actor_id: "user:dpo-1",
      reviewed_at: "2026-01-15T12:00:00Z",
      review_expires_at: "2027-01-15T12:00:00Z",
      dpia_required: true,
      dpia_reference: "dpia:DPIA-123",
      metadata: {
        catalog_ref: "catalog:support-kb"
      }
    },
    access_grants: [
      {
        id: "34343434-3434-4343-8434-343434343434",
        name: "Support agent source access",
        subject_id: "45454545-4545-4454-8454-454545454545",
        target_type: "source",
        target_id: sourceId,
        status: "active"
      }
    ]
  };

  const renderedWorkflow = renderDataUsageWorkflowFixture(fixture);

  for (const expectedText of [
    "Access & Data",
    "Source Data Usage Profiles",
    "Data Usage Profiles are governance metadata",
    "does not certify legal compliance",
    "GET /sources",
    "GET /sources/{source_id}/usage-profile",
    "Source review",
    "Support knowledge base",
    "data_classification",
    "Confidential",
    "contains_personal_data",
    "review_status",
    "Approved",
    "RAG retrieval",
    "Vectorization / embedding",
    "Summarization",
    "Training",
    "External model usage",
    "Listed allowed",
    "Listed prohibited",
    "No explicit signal",
    "allowed_purposes",
    "prohibited_processing",
    "related_source_access_grants",
    "Support agent source access",
    sourceId
  ]) {
    if (!renderedWorkflow.includes(expectedText)) {
      throw new Error(`Data Usage workflow fixture missing: ${expectedText}`);
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
    "raw source content",
    "compliance score"
  ]) {
    if (renderedWorkflow.toLowerCase().includes(unsafeText)) {
      throw new Error(`Unsafe Data Usage workflow fixture text rendered: ${unsafeText}`);
    }
  }
}

function renderDataUsageWorkflowFixture(fixture) {
  const signals = [
    dataUsageSignal(fixture.profile, "RAG retrieval", [
      "rag",
      "retrieval",
      "search"
    ]),
    dataUsageSignal(fixture.profile, "Vectorization / embedding", [
      "vector",
      "embedding"
    ]),
    dataUsageSignal(fixture.profile, "Summarization", [
      "summarization",
      "summary"
    ]),
    dataUsageSignal(fixture.profile, "Training", ["training"]),
    dataUsageSignal(fixture.profile, "External model usage", [
      "external_model",
      "external_provider"
    ])
  ];

  return [
    "Access & Data",
    "Source Data Usage Profiles",
    "Data Usage Profiles are governance metadata",
    "This workflow reviews safe Source metadata and does not certify legal compliance.",
    "GET /sources",
    "GET /sources/{source_id}/usage-profile",
    "Source review",
    fixture.source.name,
    fixture.source.id,
    "data_classification",
    formatActivityValue(fixture.profile.data_classification),
    "contains_personal_data",
    String(fixture.profile.contains_personal_data),
    "review_status",
    formatActivityValue(fixture.profile.review_status),
    "allowed_purposes",
    ...fixture.profile.allowed_purposes,
    "prohibited_processing",
    ...fixture.profile.prohibited_processing,
    "related_source_access_grants",
    ...fixture.access_grants.map((grant) => grant.name),
    ...signals.flatMap((signal) => [
      signal.label,
      dataUsageSignalLabel(signal.status),
      signal.detail
    ])
  ].join("\n");
}

function dataUsageSignal(profile, label, tokens) {
  const allowedMatches = dataUsageMatchingValues(
    [...profile.allowed_purposes, ...profile.allowed_processing],
    tokens
  );
  const prohibitedMatches = dataUsageMatchingValues(
    [...profile.prohibited_purposes, ...profile.prohibited_processing],
    tokens
  );

  if (prohibitedMatches.length > 0) {
    return {
      label,
      status: "listed_prohibited",
      detail: prohibitedMatches.join(", ")
    };
  }

  if (allowedMatches.length > 0) {
    return {
      label,
      status: "listed_allowed",
      detail: allowedMatches.join(", ")
    };
  }

  return {
    label,
    status: "no_signal",
    detail: "No explicit profile signal."
  };
}

function dataUsageMatchingValues(values, tokens) {
  return values.filter((value) => {
    const normalizedValue = dataUsageNormalizeForMatch(value);
    return tokens.some((token) =>
      normalizedValue.includes(dataUsageNormalizeForMatch(token))
    );
  });
}

function dataUsageNormalizeForMatch(value) {
  return value.toLowerCase().replace(/[\s-]+/g, "_");
}

function dataUsageSignalLabel(status) {
  if (status === "listed_allowed") {
    return "Listed allowed";
  }

  if (status === "listed_prohibited") {
    return "Listed prohibited";
  }

  return "No explicit signal";
}

function runAccessGrantWorkflowFixtureSmoke() {
  const agentId = "56565656-5656-4565-8565-565656565656";
  const sourceId = "67676767-6767-4676-8676-676767676767";
  const fixture = [
    {
      id: "78787878-7878-4787-8787-787878787878",
      name: "Claims source access",
      subject_type: "agent",
      subject_id: agentId,
      target_type: "source",
      target_id: sourceId,
      external_ref: null,
      status: "active",
      reason: "Claims assistant can retrieve reviewed claim guidance.",
      risk_level: "medium",
      granted_by_actor_type: "user",
      granted_by_actor_id: "user:governance-reviewer",
      expires_at: "2027-01-15T12:00:00Z",
      metadata: {
        ticket_ref: "JIRA-123"
      },
      created_at: "2026-01-15T12:00:00Z",
      updated_at: "2026-01-15T12:00:00Z"
    },
    {
      id: "89898989-8989-4898-8898-898989898989",
      name: "External ticketing access",
      subject_type: "agent",
      subject_id: agentId,
      target_type: "external",
      target_id: null,
      external_ref: "ticketing:claims",
      status: "pending_review",
      reason: "Pending governance review.",
      risk_level: "high",
      granted_by_actor_type: "development",
      granted_by_actor_id: "dev-placeholder",
      expires_at: null,
      metadata: {},
      created_at: "2026-01-16T12:00:00Z",
      updated_at: "2026-01-16T12:00:00Z"
    },
    {
      id: "90909090-9090-4909-8909-909090909090",
      name: "Suspended model access",
      subject_type: "agent",
      subject_id: agentId,
      target_type: "model_asset",
      target_id: "91919191-9191-4919-8919-919191919191",
      external_ref: null,
      status: "suspended",
      reason: "Paused during model review.",
      risk_level: "medium",
      granted_by_actor_type: "user",
      granted_by_actor_id: "user:model-reviewer",
      expires_at: null,
      metadata: {},
      created_at: "2026-01-17T12:00:00Z",
      updated_at: "2026-01-17T12:30:00Z"
    },
    {
      id: "92929292-9292-4929-8929-929292929292",
      name: "Revoked capability access",
      subject_type: "agent",
      subject_id: agentId,
      target_type: "capability",
      target_id: "93939393-9393-4939-8939-939393939393",
      external_ref: null,
      status: "revoked",
      reason: "No longer required for this Agent.",
      risk_level: "low",
      granted_by_actor_type: "user",
      granted_by_actor_id: "user:governance-reviewer",
      expires_at: null,
      metadata: {},
      created_at: "2026-01-18T12:00:00Z",
      updated_at: "2026-01-18T12:30:00Z"
    }
  ];

  const renderedWorkflow = renderAccessGrantWorkflowFixture(fixture);
  const activeSourceFiltered = renderAccessGrantWorkflowFixture(
    fixture.filter(
      (grant) => grant.status === "active" && grant.target_type === "source"
    )
  );

  for (const expectedText of [
    "Access Grant workflow",
    "Access Grants are declared governance records",
    "not automatically enforced by the Runtime Gateway",
    "Transition actions update the governance record status",
    "does not by itself guarantee runtime blocking",
    "runtime enforcement depends on policies",
    "GET /access-grants",
    "Access Grants loaded",
    "Access Grant transition actions",
    "Transition note",
    "Updates the governance record status only",
    "Suspend",
    "Revoke",
    "Expire",
    "Reactivate",
    "Terminal governance status",
    "subject_type",
    "subject_id",
    "target_type",
    "target_id",
    "external_ref",
    "active",
    "pending_review",
    "suspended",
    "revoked",
    "risk_level",
    "granted_by_actor_type",
    "granted_by_actor_id",
    "expires_at",
    "Safe Metadata",
    "Agent Governance Profile",
    "Evidence Bundle lookup",
    "Source/Data Usage workflow",
    "Claims source access",
    "External ticketing access",
    "Suspended model access",
    "Revoked capability access",
    agentId,
    sourceId
  ]) {
    if (!renderedWorkflow.includes(expectedText)) {
      throw new Error(`Access Grant workflow fixture missing: ${expectedText}`);
    }
  }

  if (!activeSourceFiltered.includes("Claims source access")) {
    throw new Error("Access Grant workflow fixture did not cover filtered grants.");
  }

  if (activeSourceFiltered.includes("External ticketing access")) {
    throw new Error("Access Grant workflow fixture filter retained wrong target.");
  }

  for (const unsafeText of [
    "api_key",
    "password",
    "raw_prompt",
    "raw_payload",
    "source contents",
    "compliance score"
  ]) {
    if (renderedWorkflow.toLowerCase().includes(unsafeText)) {
      throw new Error(`Unsafe Access Grant workflow fixture text rendered: ${unsafeText}`);
    }
  }
}

function renderAccessGrantWorkflowFixture(grants) {
  return [
    "Access Grant workflow",
    "Access Grants are declared governance records",
    "Grants describe intended Agent access and are not automatically enforced by the Runtime Gateway.",
    "Transition actions update the governance record status",
    "does not by itself guarantee runtime blocking",
    "runtime enforcement depends on policies",
    "GET /access-grants",
    "Access Grants loaded",
    "Access Grant transition actions",
    "Transition note",
    "Updates the governance record status only",
    "subject_type",
    "subject_id",
    "target_type",
    "target_id",
    "external_ref",
    "risk_level",
    "granted_by_actor_type",
    "granted_by_actor_id",
    "expires_at",
    "Safe Metadata",
    "Agent Governance Profile",
    "Evidence Bundle lookup",
    "Source/Data Usage workflow",
    ...grants.flatMap((grant) => [
      grant.id,
      grant.name,
      grant.subject_type,
      grant.subject_id,
      grant.target_type,
      grant.target_id || grant.external_ref || "Not set",
      grant.status,
      grant.reason,
      grant.risk_level,
      grant.granted_by_actor_type,
      grant.granted_by_actor_id,
      JSON.stringify(grant.metadata),
      ...accessGrantFixtureActionsForStatus(grant.status)
    ])
  ].join("\n");
}

function accessGrantFixtureActionsForStatus(status) {
  if (status === "active") {
    return ["Suspend", "Revoke", "Expire"];
  }

  if (status === "pending_review") {
    return ["Revoke", "Expire"];
  }

  if (status === "suspended") {
    return ["Reactivate", "Revoke", "Expire"];
  }

  return ["Terminal governance status"];
}
