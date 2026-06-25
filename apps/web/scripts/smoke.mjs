import { readFile } from "node:fs/promises";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import vm from "node:vm";

const root = fileURLToPath(new URL("..", import.meta.url));

const files = [
  "app/layout.tsx",
  "app/page.tsx",
  "app/agcp-studio/AGCPStudio.tsx",
  "app/agcp-studio/primitives.tsx",
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
  "app/lib/current-actor.ts",
  "app/lib/service-actors.ts",
  "app/access-data/page.tsx",
  "app/access-data/access-inventory-matrix.tsx",
  "app/access-data/access-grants-workflow.tsx",
  "app/access-data/sources-workflow.tsx",
  "app/policies/page.tsx",
  "app/policies/policy-blocks-editor.tsx",
  "app/policies/policy-code-editor.tsx",
  "app/policies/policy-dsl.ts",
  "app/policies/policy-editor.tsx",
  "app/policies/policy-inspector.tsx",
  "app/policies/policy-repository.tsx",
  "app/policies/policy-studio.tsx",
  "app/policies/policy-templates.tsx",
  "app/policies/policies-manager.tsx",
  "app/integrations/page.tsx",
  "app/integrations/integration-hub.tsx",
  "app/runtime-gateway/page.tsx",
  "app/runtime-gateway/runtime-activity-list.tsx",
  "app/human-approvals/page.tsx",
  "app/human-approvals/review-inbox.tsx",
  "app/human-approvals/human-approvals-list.tsx",
  "app/human-approvals/policy-reviews-list.tsx",
  "app/lib/evidence.ts",
  "app/evidence/page.tsx",
  "app/evidence/evidence-bundle-viewer.tsx",
  "app/audit/page.tsx",
  "app/settings/page.tsx"
];

const fileEntries = await Promise.all(
  files.map(async (file) => ({
    file,
    source: await readFile(join(root, file), "utf8")
  }))
);
const sourceByFile = new Map(
  fileEntries.map((entry) => [entry.file, entry.source])
);
const source = fileEntries.map((entry) => entry.source).join("\n");

const requiredText = [
  "AGCPStudio",
  "AGCPPanel",
  "AGCPBadge",
  "AGCPDataTable",
  "AGCPTimelineItem",
  "CONTROL PLANE",
  "Command Center",
  "Decision Inbox",
  "fetchAgents",
  "fetchHumanApprovals",
  "fetchPolicies",
  "fetchSources",
  "fetchAccessGrants",
  "fetchRuntimeToolCallActivity",
  "buildStudioKpis",
  "buildStudioInbox",
  "Agents",
  "Policies",
  "Access & Inventory",
  "Access & Inventory Matrix",
  "not credentials or IAM permissions",
  "Access Grants are declarations",
  "Matrix cells describe declared access",
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
  "GET /policies",
  "POST /policies",
  "POST /policies/{policy_id}/archive",
  "DELETE /policies/{policy_id}",
  "GET /policies/{policy_id}/versions",
  "POST /policies/{policy_id}/versions/draft",
  "PATCH /policy-versions/{policy_version_id}/draft",
  "GET /policy-versions/{policy_version_id}/review-state",
  "GET /policy-version-review-requests",
  "POST /policy-versions/{policy_version_id}/review-requests",
  "POST /policy-version-review-requests/{review_request_id}/approve",
  "POST /policy-version-review-requests/{review_request_id}/reject",
  "POST /policy-version-review-requests/{review_request_id}/assign",
  "POST /policy-version-review-requests/{review_request_id}/activate",
  "GET /me",
  "GET /policy-version-review-requests/{review_request_id}/diff",
  "POST /policy-versions/{policy_version_id}/rollback-draft",
  "GET /policies/{policy_id}/rules",
  "Policy Studio",
  "Policy Studio Refinement",
  "PolicyStudioRail",
  "ps2-icon-rail",
  "ps2-code-highlight",
  "Repository",
  "Policy repository",
  "Local backend",
  "Policies are loaded from the AGCP API.",
  "Search policies",
  "Templates",
  "New policy",
  "Policy structure",
  "WHEN",
  "CHECK",
  "THEN",
  "PROVE",
  "Blocks",
  "Block library",
  "ps2-block-workbench",
  "ps2-flow-canvas",
  "Backend Policy records",
  "Backend unavailable",
  "No backend policies",
  "No fallback policies are shown",
  "Use Code DSL for precise editing in V1",
  "Loading versions",
  "Unable to load versions",
  "No PolicyVersion",
  "Code DSL",
  "Validate",
  "LOCAL VALIDATION CONSOLE",
  "Local validation only",
  "Local validation not run",
  "LOCAL-VAL",
  "Current editor state",
  "References",
  "Inspector",
  "Compiled Output",
  "Review Status",
  "No tags configured",
  "Save draft",
  "Submit for review",
  "Create new draft for changes",
  "Archive policy",
  "Archive keeps evidence and history",
  "Delete draft policy",
  "Delete is only available for draft-only policies",
  "Policies with versions, reviews, or runtime decisions cannot be deleted",
  "cannot be deleted",
  "Save a draft before submitting for review.",
  "Fix validation errors before submitting.",
  "Save a draft PolicyVersion before submitting for review",
  "This PolicyVersion is not a draft.",
  "Current actor is not configured.",
  "Create a draft before submitting changes for review.",
  "Not submitted",
  "Pending review",
  "Review request submitted",
  "Review request already pending.",
  "Approval does not activate this version",
  "Review approval does not activate",
  "Current actor",
  "Local Admin",
  "platform_admin",
  "reviewer",
  "Reviewer role required",
  "Assigned to another reviewer",
  "Backend authorization still enforced",
  "No fake user directory",
  "Assigned reviewer",
  "Unassigned",
  "Assign reviewer",
  "Assignment does not approve the review",
  "Assigned reviewer must still approve or reject",
  "Activate approved version",
  "Activation changes runtime policy evaluation",
  "Activation changes future runtime policy evaluation",
  "This will replace the current active version",
  "Policy review diff",
  "Changed fields",
  "Baseline active version",
  "No active baseline yet",
  "This appears to be the first reviewed version for this policy.",
  "No runtime effect until activation",
  "Create rollback draft",
  "Rollback draft does not affect runtime",
  "Submit for review required before activation",
  "No runtime change until approved and activated",
  "Policy Reviews",
  "Pending and approved PolicyVersion review requests",
  "PolicyRule condition reason is required",
  "Generated deterministic condition JSON",
  "Validate does not save",
  "Save draft persists a PolicyVersion draft",
  "Save draft is possible from this editor state",
  "Info",
  "Warning",
  "Error",
  "Draft version saved",
  "Editing draft PolicyVersion",
  "Editor source:",
  "Live PolicyRule fallback",
  "No runtime effect until reviewed and activated",
  "This draft is locked while review is pending",
  "Create a new draft for additional changes",
  "Create new draft for changes",
  "This draft is locked because a review is pending",
  "Review request already pending.",
  "Use Save draft to create a reviewed PolicyVersion",
  "This draft will save a generated rule snapshot",
  "This policy currently relies on CHECK facts",
  "Save draft snapshots this source rule",
  "Draft PolicyVersion",
  "deterministic PolicyRule condition JSON",
  "Compiled locally from editor state",
  "Local validation only; no runtime decision request is executed",
  "Save draft creates a draft PolicyVersion and does not affect runtime until activation",
  "Confidential Data Vectorization Guard",
  "External Model Usage Guard",
  "Loading Policy repository",
  "Backend unavailable",
  "No backend policies",
  "check_type",
  "check_outcome",
  "check_target_type",
  "check_target_id",
  "check_tool_id",
  "check_min_confidence",
  "Compiled condition JSON",
  "does not affect runtime until activation",
  "Unsupported DSL lines were ignored by the local compiler",
  "unsupportedConditionFields",
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
  "AGCPTimelineItem",
  "badgeTone(severity)",
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
  "agcp-agent-hero",
  "agcp-timeline",
  "Evidence Bundle export requires an auditor or platform_admin role",
  "GET /human-approvals",
  "Review Inbox",
  "Mine",
  "Waiting",
  "Escalated",
  "Completed",
  "Why Review Is Required",
  "Policy Decision",
  "Policy Checks",
  "Evidence Preview",
  "Metadata pre-check results",
  "No metadata pre-check results attached yet",
  "Approve",
  "Reject",
  "Request info",
  "Reassign",
  "Activate approved version",
  "Loading human approvals",
  "Unable to load human approvals",
  "No human approvals",
  "review queue",
  "agcp-review-list",
  "policy_decision_id",
  "requested_by_actor_type",
  "requested_by_actor_id",
  "reviewed_by_actor_type",
  "reviewed_by_actor_id",
  "expires_at",
  "pending",
  "approved",
  "rejected",
  "cancelled",
  "expired",
  "Human Approval",
  "Evidence Bundle",
  "Evidence & Audit",
  "Export and inspect the evidence trail",
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
  "Runtime Decisions",
  "Trace how AGCP evaluated agent actions",
  "AGCP records and governs decisions",
  "GET /runtime/tool-calls/activity",
  "Loading Runtime activity",
  "Unable to load Runtime activity",
  "No Runtime activity records",
  "Runtime activity requires reviewer, auditor, or platform_admin role",
  "Runtime request received",
  "Context resolved",
  "Policy evaluated",
  "Metadata checks",
  "Human review",
  "Evidence",
  "No metadata pre-check results attached",
  "Run a local metadata pre-check decision",
  ".\\scripts\\dev-demo.ps1",
  "not executing the tool",
  "no fake production simulation",
  "Open Evidence Bundle",
  "Open Review Inbox",
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

runRootDashboardSmoke();
runActivityTimelineFixtureSmoke();
runRuntimeActivityFixtureSmoke();
runAgentGovernanceProfileFixtureSmoke();
runEvidenceBundleWorkflowFixtureSmoke();
runDataUsageWorkflowFixtureSmoke();
runAccessGrantWorkflowFixtureSmoke();
await runPolicyDslRoundTripSmoke();

console.log("Dashboard shell smoke check passed.");

function runRootDashboardSmoke() {
  const rootRequiredText = [
    "AGCPStudio",
    "AGCPStudioShell",
    "AGCPStudioDashboard",
    "Overview",
    "Agent Governance Control Plane",
    "Know your agents",
    "Control risky actions",
    "Prove what happened",
    "Run the metadata pre-check demo",
    ".\\scripts\\dev-demo.ps1",
    "not an orchestrator",
    "not a legal compliance certification tool",
    "no fake production simulation",
    "Current actor",
    "Needs attention",
    "Recent governance activity",
    "fetchCurrentActor",
    "fetchPolicyVersionReviewRequests",
    "Command Center",
    "Decision Inbox",
    "Control Map",
    "fetchAgents",
    "fetchHumanApprovals",
    "fetchPolicies",
    "fetchSources",
    "fetchAccessGrants",
    "fetchRuntimeToolCallActivity",
    'href: "/agents"',
    'href: "/human-approvals"',
    'href: "/evidence"',
    'href: "/audit"',
    'href: "/policies"',
    'href: "/settings"'
  ];

  for (const text of rootRequiredText) {
    if (!source.includes(text)) {
      throw new Error(`Root dashboard smoke check missing: ${text}`);
    }
  }

  const rootSource = [
    sourceByFile.get("app/page.tsx") ?? "",
    sourceByFile.get("app/agcp-studio/AGCPStudio.tsx") ?? "",
    sourceByFile.get("app/layout.tsx") ?? ""
  ].join("\n");

  for (const text of [
    "compliance score",
    "AI Act compliant",
    "ISO 42001 certified",
    "fully compliant"
  ]) {
    if (rootSource.toLowerCase().includes(text.toLowerCase())) {
      throw new Error(`Root dashboard contains disconnected or unsafe text: ${text}`);
    }
  }
}

async function runPolicyDslRoundTripSmoke() {
  const policyDsl = await loadPolicyDslModule();
  const {
    POLICY_TEMPLATES,
    conditionToDsl,
    parsePolicyDslToPolicyRule,
    templateToDsl,
    unsupportedConditionFields
  } = policyDsl;

  const roundTripCases = [
    {
      name: "allow",
      condition: {
        action_type: "read",
        decision: "allow",
        reason: "Allow verified action."
      }
    },
    {
      name: "deny",
      condition: {
        decision: "deny",
        reason: "Deny unsafe external action.",
        tool_name: "external_payments"
      }
    },
    {
      name: "require_human_review",
      condition: {
        decision: "require_human_review",
        environment: "production",
        reason: "Production external action requires review.",
        risk_level: "high"
      }
    },
    {
      name: "not_applicable",
      condition: {
        decision: "not_applicable",
        reason: "Policy does not apply to this request.",
        purpose: "support_triage"
      }
    }
  ];

  for (const fixture of roundTripCases) {
    const parsed = parsePolicyDslToPolicyRule(
      conditionToDsl(`${fixture.name}_case`, fixture.condition)
    );
    assertSmoke(parsed.errors.length === 0, `${fixture.name} DSL had errors`);
    assertSmoke(
      parsed.unsupported.length === 0,
      `${fixture.name} DSL produced unsupported lines`
    );
    assertJsonIncludes(
      parsed.condition,
      fixture.condition,
      `${fixture.name} round-trip condition`
    );
  }

  const missingReason = parsePolicyDslToPolicyRule(
    [
      "policy missing_reason {",
      '  when tool.name == "external_payments"',
      "  then deny()",
      "  prove decision, checks, reviewer, evidence_bundle",
      "}"
    ].join("\n")
  );
  assertSmoke(
    missingReason.condition === null,
    "missing reason DSL should not compile"
  );
  assertSmoke(
    missingReason.errors.includes("PolicyRule condition reason is required."),
    "missing reason DSL did not report reason requirement"
  );

  const invalidConfidence = parsePolicyDslToPolicyRule(
    [
      "policy invalid_confidence {",
      '  check check.min_confidence == 1.2 required',
      '  then allow("Confidence threshold is valid.")',
      "  prove decision, checks, reviewer, evidence_bundle",
      "}"
    ].join("\n")
  );
  assertSmoke(
    invalidConfidence.condition === null,
    "invalid check_min_confidence should not compile"
  );
  assertSmoke(
    invalidConfidence.errors.includes(
      "check_min_confidence must be a number between 0 and 1."
    ),
    "invalid check_min_confidence did not report threshold error"
  );

  const unsupported = parsePolicyDslToPolicyRule(
    [
      "policy unsupported_line {",
      '  when tool.name == "send_email"',
      '  inspect production_impact == "18 systems"',
      '  then require_review("Review unsupported syntax.")',
      "  prove decision, checks, reviewer, evidence_bundle",
      "}"
    ].join("\n")
  );
  assertSmoke(
    unsupported.unsupported.includes('inspect production_impact == "18 systems"'),
    "unsupported DSL syntax was not surfaced"
  );
  assertSmoke(
    unsupported.warnings.includes(
      "Unsupported DSL lines were ignored by the local compiler."
    ),
    "unsupported DSL syntax did not create a warning"
  );

  const emptyPolicy = parsePolicyDslToPolicyRule("");
  assertSmoke(emptyPolicy.condition === null, "empty policy should not compile");
  assertSmoke(
    emptyPolicy.errors.includes("PolicyRule condition reason is required."),
    "empty policy did not report missing reason"
  );

  for (const template of POLICY_TEMPLATES) {
    const parsedTemplate = parsePolicyDslToPolicyRule(templateToDsl(template));
    assertSmoke(
      parsedTemplate.errors.length === 0,
      `${template.name} template had DSL errors`
    );
    assertSmoke(
      parsedTemplate.unsupported.length === 0,
      `${template.name} template emitted unsupported DSL`
    );
    assertSmoke(
      parsedTemplate.condition?.reason,
      `${template.name} template did not compile a reason`
    );
  }

  const confidentialTemplate = POLICY_TEMPLATES.find(
    (template) => template.id === "confidential_vectorization_guard"
  );
  assertSmoke(
    Boolean(confidentialTemplate),
    "Confidential Data Vectorization Guard template missing"
  );
  assertJsonIncludes(
    confidentialTemplate.condition,
    {
      access_grant_status: "active",
      action_type: "vectorization",
      data_usage_allowed_purpose: "vectorization",
      data_usage_review_status: "approved",
      decision: "require_human_review",
      model_provider_type: "external",
      model_type: "embedding",
      source_data_classification: "confidential"
    },
    "confidential vectorization template"
  );

  const unsupportedFields = unsupportedConditionFields({
    declared_data_classification: "confidential",
    decision: "allow",
    reason: "Supported fields only."
  });
  assertSmoke(
    unsupportedFields.includes("declared_data_classification"),
    "unsupported backend fields were not detected"
  );

  const policyStudioSource = fileEntries
    .filter((entry) => entry.file.startsWith("app/policies/"))
    .map((entry) => entry.source)
    .join("\n");
  assertSmoke(
    !policyStudioSource.includes("Publish"),
    "Policy Studio source contains a Publish action"
  );
  assertSmoke(
    !policyStudioSource.includes("A review request is already pending for this draft."),
    "Policy Studio source contains noisy duplicate review request copy"
  );
  assertSmoke(
    !policyStudioSource.includes("No supported WHEN request fields were found."),
    "Policy Studio source contains noisy WHEN warning copy"
  );
  assertSmoke(
    !policyStudioSource.includes("No active baseline found"),
    "Policy Studio source contains scary baseline copy"
  );
  const normalizedPolicyStudioSource = policyStudioSource.toLowerCase();
  for (const forbidden of [
    "compliance score",
    "affected agents",
    "production simulation",
    "Security Governance Team",
    "May 23, 2025",
    "pol_data_exfil_prevention",
    "v0.4.0",
    "GovernanceLab",
    "Repository status Synced",
    "Current workspace",
    "Local drafts",
    "Local draft / not persisted"
  ]) {
    assertSmoke(
      !normalizedPolicyStudioSource.includes(forbidden.toLowerCase()),
      `Policy Studio source contains forbidden product claim: ${forbidden}`
    );
  }
}

async function loadPolicyDslModule() {
  const ts = await import("typescript");
  const sourceText = sourceByFile.get("app/policies/policy-dsl.ts");
  const transpiled = ts.transpileModule(sourceText, {
    compilerOptions: {
      esModuleInterop: true,
      module: ts.ModuleKind.CommonJS,
      target: ts.ScriptTarget.ES2020
    }
  });
  const module = { exports: {} };
  const context = {
    exports: module.exports,
    module,
    require: (specifier) => {
      throw new Error(`Unexpected runtime import in policy-dsl smoke: ${specifier}`);
    }
  };
  vm.runInNewContext(transpiled.outputText, context, {
    filename: "policy-dsl.ts"
  });
  return module.exports;
}

function assertJsonIncludes(actual, expected, label) {
  assertSmoke(Boolean(actual), `${label} did not produce JSON`);
  for (const [key, value] of Object.entries(expected)) {
    assertSmoke(
      JSON.stringify(actual[key]) === JSON.stringify(value),
      `${label} missing ${key}=${JSON.stringify(value)}`
    );
  }
}

function assertSmoke(condition, message) {
  if (!condition) {
    throw new Error(message);
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
  const policyVersionId = "77777777-7777-4777-8777-777777777777";

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
      human_approval_status: "pending",
      policy_version_id: policyVersionId,
      environment: "production",
      action_type: "external_tool_call",
      source_ids: ["source-confidential"],
      model_id: "model-external",
      purpose: "customer_notification",
      source_data_classification: "confidential",
      check_results: [
        {
          id: "88888888-8888-4888-8888-888888888888",
          check_type: "source_classification",
          outcome: "passed",
          target_type: "source",
          target_id: "source-confidential",
          confidence: 1,
          created_at: "2026-01-15T12:04:59Z",
          metadata: {
            data_classification: "confidential",
            raw_source_content: "do-not-render"
          }
        }
      ],
      related_ids: {
        trace_event_id: traceEventId,
        policy_decision_id: policyDecisionId,
        human_approval_id: humanApprovalId,
        policy_version_id: policyVersionId,
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
    "Runtime request received",
    "Context resolved",
    "Policy evaluated",
    "Metadata checks",
    "Human review",
    "Evidence",
    "AGCP does not execute the tool",
    "PolicyVersion",
    policyVersionId,
    "production",
    "external_tool_call",
    "source-confidential",
    "model-external",
    "customer_notification",
    "confidential",
    "source_classification",
    "passed",
    "No metadata pre-check results attached",
    "Open Review Inbox",
    "Open Evidence Bundle",
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

  if (!emptyActivity.includes(".\\scripts\\dev-demo.ps1")) {
    throw new Error("Runtime activity fixture did not cover the local demo command.");
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
    return "No Runtime activity records\nNo runtime decisions recorded yet. Run .\\scripts\\dev-demo.ps1 to create a local metadata pre-check decision.";
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
    item.reason || "No reason was persisted for this activity record.",
    "Runtime request received",
    "AGCP does not execute the tool",
    "Context resolved",
    item.environment || "No resolved inventory context attached.",
    item.action_type || "",
    (item.source_ids || []).join(", "),
    item.model_id || "",
    item.purpose || "",
    item.source_data_classification || item.data_classification || "",
    "Policy evaluated",
    "PolicyVersion",
    item.policy_version_id || item.related_ids?.policy_version_id || "No active PolicyVersion reference attached",
    "Metadata checks",
    "Human review",
    item.human_approval_id ? "Open Review Inbox" : "No human review was required for this decision.",
    "Evidence",
    "Open Evidence Bundle"
  ];

  const checkResults = item.check_results || [];
  if (checkResults.length === 0) {
    parts.push("No metadata pre-check results attached");
  }

  for (const result of checkResults) {
    parts.push(
      result.check_type,
      result.outcome,
      result.target_type || "Not attached",
      result.target_id || "Not attached",
      String(result.confidence ?? "Not attached")
    );

    for (const [key, value] of Object.entries(result.metadata || {})) {
      if (isSafeRuntimeMetadataKey(key)) {
        parts.push(key, String(value));
      }
    }
  }

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

function isSafeRuntimeMetadataKey(key) {
  const normalizedKey = key.toLowerCase();
  return ![
    "api_key",
    "authorization",
    "chunk",
    "content",
    "credential",
    "password",
    "payload",
    "prompt",
    "raw",
    "secret",
    "token"
  ].some((unsafeTerm) => normalizedKey.includes(unsafeTerm));
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
        check_type: "source_classification",
        outcome: "pass",
        policy_decision_id: policyDecisionId,
        policy_version_id: policyVersionId,
        summary: "Data Usage Profile is approved.",
        metadata: {
          data_classification: "confidential",
          raw_prompt: "do-not-render",
          api_key: "do-not-render"
        }
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

  for (const expectedText of [
    "Evidence & Audit",
    "Export and inspect the evidence trail",
    "Evidence Bundle is an audit/review package",
    "does not certify legal compliance",
    "Download Evidence Bundle JSON",
    "Export bundle",
    "safe_export_metadata",
    "exported_at",
    "exported_by",
    "agent_id",
    "human_readable_evidence_chain",
    "Agent",
    "Access Grants",
    "Data Usage Profile summaries",
    "Policy Decision",
    "Metadata CheckResults",
    "Human Review",
    "Policy Review",
    "Audit Trail",
    "data_usage_profile_summaries",
    "TraceEvents",
    "PolicyDecisions",
    "PolicyVersion references",
    "Export bundle",
    "policy_version_references",
    "CheckResults",
    "check_type",
    "source_classification",
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
    "data_classification",
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
    "raw_payload",
    "api_key"
  ]) {
    if (renderedWorkflow.toLowerCase().includes(unsafeText)) {
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
    "Evidence & Audit",
    "Export and inspect the evidence trail behind agent governance decisions.",
    "Evidence Bundle is an audit/review package; it does not certify legal compliance.",
    "The Evidence Bundle excludes raw prompts, source contents, secrets, tokens, credentials, and unsafe payloads.",
    "Download Evidence Bundle JSON",
    "Export bundle",
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
    "Policy Decision",
    "Metadata CheckResults",
    "Human Review",
    "Policy Review",
    "Audit Trail",
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
    JSON.stringify(sanitizeEvidenceFixture(bundle))
  ].join("\n");
}

function sanitizeEvidenceFixture(value) {
  if (Array.isArray(value)) {
    return value.map((item) => sanitizeEvidenceFixture(item));
  }

  if (value && typeof value === "object") {
    return Object.fromEntries(
      Object.entries(value)
        .filter(([key]) => isSafeEvidenceMetadataKey(key))
        .map(([key, nestedValue]) => [key, sanitizeEvidenceFixture(nestedValue)])
    );
  }

  return value;
}

function isSafeEvidenceMetadataKey(key) {
  const normalizedKey = key.toLowerCase();
  return ![
    "api_key",
    "authorization",
    "credential",
    "password",
    "private_payload",
    "prompt",
    "raw",
    "secret",
    "source_content",
    "token"
  ].some((unsafeTerm) => normalizedKey.includes(unsafeTerm));
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
