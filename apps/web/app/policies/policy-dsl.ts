import type {
  PolicyRecord,
  PolicyRuleDecision,
  PolicyRuleRecord
} from "../lib/policies";

export type ConditionValue = string | boolean | number | string[];
export type PolicyCondition = Record<string, ConditionValue>;

export type PolicyTemplate = {
  id: string;
  name: string;
  className: string;
  description: string;
  tags: string[];
  condition: PolicyCondition;
};

export type ParsedPolicyDsl = {
  condition: PolicyCondition | null;
  errors: string[];
  policyName: string;
  prove: string;
  ruleName: string;
  structural: string[];
  unsupported: string[];
  warnings: string[];
};

export type PolicyBlock = {
  id: string;
  group: "when" | "check" | "then" | "prove";
  kind: "when" | "check" | "then" | "prove";
  expr: string;
  detail: string;
  status: string;
  statusClass: string;
};

export type PolicyConditionFieldConfig = {
  key: string;
  label: string;
  detail: string;
  input: "text" | "select" | "boolean" | "string_list" | "number";
  options?: string[];
};

export const WHEN_FIELDS = [
  "agent_id",
  "tool_name",
  "environment",
  "risk_level",
  "action_type",
  "capability_id",
  "source_id",
  "source_ids",
  "model_id",
  "purpose",
  "data_classification",
  "contains_personal_data",
  "contains_sensitive_data"
] as const;

export const CHECK_FIELDS = [
  "access_grant_status",
  "data_usage_review_status",
  "data_usage_allowed_purpose",
  "data_usage_prohibited_purpose",
  "source_status",
  "source_data_classification",
  "source_contains_personal_data",
  "source_contains_sensitive_data",
  "capability_type",
  "capability_status",
  "model_type",
  "model_provider",
  "model_provider_type",
  "model_status",
  "check_type",
  "check_outcome",
  "check_target_type",
  "check_target_id",
  "check_tool_id",
  "check_min_confidence"
] as const;

export const POLICY_WHEN_FIELD_CONFIGS: PolicyConditionFieldConfig[] = [
  {
    key: "agent_id",
    label: "agent.id",
    detail: "Match a specific Agent id",
    input: "text"
  },
  {
    key: "tool_name",
    label: "tool.name",
    detail: "Runtime tool or operation name",
    input: "text"
  },
  {
    key: "environment",
    label: "system.environment",
    detail: "Runtime environment",
    input: "select",
    options: ["development", "staging", "production"]
  },
  {
    key: "risk_level",
    label: "action.risk",
    detail: "Declared risk level",
    input: "select",
    options: ["low", "medium", "high", "critical"]
  },
  {
    key: "action_type",
    label: "action.type",
    detail: "Governed runtime action type",
    input: "text"
  },
  {
    key: "capability_id",
    label: "capability.id",
    detail: "Declared Capability id",
    input: "text"
  },
  {
    key: "source_id",
    label: "source.id",
    detail: "Single declared Source id",
    input: "text"
  },
  {
    key: "source_ids",
    label: "source.ids",
    detail: "Comma-separated Source ids; runtime uses overlap matching",
    input: "string_list"
  },
  {
    key: "model_id",
    label: "model.id",
    detail: "Declared ModelAsset id",
    input: "text"
  },
  {
    key: "purpose",
    label: "request.purpose",
    detail: "Declared request purpose",
    input: "text"
  },
  {
    key: "data_classification",
    label: "data.classification",
    detail: "Runtime data classification",
    input: "select",
    options: ["public", "internal", "confidential", "restricted"]
  },
  {
    key: "contains_personal_data",
    label: "data.contains_personal_data",
    detail: "Whether request context declares personal data",
    input: "boolean"
  },
  {
    key: "contains_sensitive_data",
    label: "data.contains_sensitive_data",
    detail: "Whether request context declares sensitive data",
    input: "boolean"
  }
];

export const POLICY_CHECK_FIELD_CONFIGS: PolicyConditionFieldConfig[] = [
  {
    key: "capability_type",
    label: "capability.type",
    detail: "Resolved Capability type",
    input: "select",
    options: ["tool", "api", "integration", "workflow_action", "other"]
  },
  {
    key: "capability_status",
    label: "capability.status",
    detail: "Resolved Capability status",
    input: "select",
    options: ["active", "disabled", "retired", "missing"]
  },
  {
    key: "source_status",
    label: "source.status",
    detail: "Resolved Source status",
    input: "select",
    options: ["active", "disabled", "retired", "missing"]
  },
  {
    key: "source_data_classification",
    label: "source.classification",
    detail: "Resolved Source data classification",
    input: "select",
    options: ["public", "internal", "confidential", "restricted"]
  },
  {
    key: "source_contains_personal_data",
    label: "source.contains_personal_data",
    detail: "Resolved Source personal data flag",
    input: "boolean"
  },
  {
    key: "source_contains_sensitive_data",
    label: "source.contains_sensitive_data",
    detail: "Resolved Source sensitive data flag",
    input: "boolean"
  },
  {
    key: "model_type",
    label: "model.type",
    detail: "Resolved ModelAsset type",
    input: "select",
    options: ["llm", "embedding", "reranker", "classifier", "vision", "audio", "other"]
  },
  {
    key: "model_provider",
    label: "model.provider",
    detail: "Resolved model provider",
    input: "select",
    options: ["openai", "mistral", "anthropic", "local", "azure", "aws", "gcp", "other"]
  },
  {
    key: "model_provider_type",
    label: "model.provider_type",
    detail: "Resolved provider boundary",
    input: "select",
    options: ["external", "local", "unknown"]
  },
  {
    key: "model_status",
    label: "model.status",
    detail: "Resolved ModelAsset status",
    input: "select",
    options: ["active", "disabled", "retired", "missing"]
  },
  {
    key: "access_grant_status",
    label: "access_grant.status",
    detail: "Resolved AccessGrant status",
    input: "select",
    options: ["pending_review", "active", "suspended", "revoked", "expired", "missing"]
  },
  {
    key: "data_usage_review_status",
    label: "data_usage.review_status",
    detail: "Resolved DataUsageProfile review status",
    input: "select",
    options: ["draft", "approved", "rejected", "expired", "needs_review", "missing"]
  },
  {
    key: "data_usage_allowed_purpose",
    label: "data_usage.allowed_purpose",
    detail: "Allowed data usage purpose",
    input: "text"
  },
  {
    key: "data_usage_prohibited_purpose",
    label: "data_usage.prohibited_purpose",
    detail: "Prohibited data usage purpose",
    input: "text"
  },
  {
    key: "check_type",
    label: "check.type",
    detail: "Safe CheckResult type summary",
    input: "select",
    options: [
      "access_grant_status",
      "data_usage_profile_status",
      "source_status",
      "capability_status",
      "model_asset_status"
    ]
  },
  {
    key: "check_outcome",
    label: "check.outcome",
    detail: "Safe CheckResult outcome summary",
    input: "select",
    options: ["pass", "fail", "unknown", "error", "not_applicable"]
  },
  {
    key: "check_target_type",
    label: "check.target_type",
    detail: "Safe CheckResult target type",
    input: "select",
    options: ["source", "capability", "model_asset", "access_grant", "data_usage_profile", "external"]
  },
  {
    key: "check_target_id",
    label: "check.target_id",
    detail: "Safe CheckResult target id",
    input: "text"
  },
  {
    key: "check_tool_id",
    label: "check.tool_id",
    detail: "Safe CheckTool id",
    input: "text"
  },
  {
    key: "check_min_confidence",
    label: "check.min_confidence",
    detail: "Minimum check confidence, 0 through 1",
    input: "number"
  }
];

const SUPPORTED_CONDITION_FIELDS = new Set<string>([
  "decision",
  "reason",
  ...WHEN_FIELDS,
  ...CHECK_FIELDS
]);

const FIELD_ALIASES: Record<string, string> = {
  "access_grant.status": "access_grant_status",
  "action.capability_id": "capability_id",
  "action.risk": "risk_level",
  "action.type": "action_type",
  "agent.id": "agent_id",
  "capability.id": "capability_id",
  "capability.status": "capability_status",
  "capability.type": "capability_type",
  "check.min_confidence": "check_min_confidence",
  "check.outcome": "check_outcome",
  "check.target_id": "check_target_id",
  "check.target_type": "check_target_type",
  "check.tool_id": "check_tool_id",
  "check.type": "check_type",
  "data.classification": "data_classification",
  "data.contains_personal_data": "contains_personal_data",
  "data.contains_sensitive_data": "contains_sensitive_data",
  "data_usage.allowed_purpose": "data_usage_allowed_purpose",
  "data_usage.prohibited_purpose": "data_usage_prohibited_purpose",
  "data_usage.review_status": "data_usage_review_status",
  "model.id": "model_id",
  "model.provider": "model_provider",
  "model.provider_type": "model_provider_type",
  "model.status": "model_status",
  "model.type": "model_type",
  "request.purpose": "purpose",
  "source.classification": "source_data_classification",
  "source.contains_personal_data": "source_contains_personal_data",
  "source.contains_sensitive_data": "source_contains_sensitive_data",
  "source.id": "source_id",
  "source.ids": "source_ids",
  "source.status": "source_status",
  "system.environment": "environment",
  "tool.name": "tool_name"
};

const FIELD_LABELS: Record<string, string> = {
  access_grant_status: "access_grant.status",
  action_type: "action.type",
  agent_id: "agent.id",
  capability_id: "capability.id",
  capability_status: "capability.status",
  capability_type: "capability.type",
  check_min_confidence: "check.min_confidence",
  check_outcome: "check.outcome",
  check_target_id: "check.target_id",
  check_target_type: "check.target_type",
  check_tool_id: "check.tool_id",
  check_type: "check.type",
  contains_personal_data: "data.contains_personal_data",
  contains_sensitive_data: "data.contains_sensitive_data",
  data_classification: "data.classification",
  data_usage_allowed_purpose: "data_usage.allowed_purpose",
  data_usage_prohibited_purpose: "data_usage.prohibited_purpose",
  data_usage_review_status: "data_usage.review_status",
  environment: "system.environment",
  model_id: "model.id",
  model_provider: "model.provider",
  model_provider_type: "model.provider_type",
  model_status: "model.status",
  model_type: "model.type",
  purpose: "request.purpose",
  risk_level: "action.risk",
  source_contains_personal_data: "source.contains_personal_data",
  source_contains_sensitive_data: "source.contains_sensitive_data",
  source_data_classification: "source.classification",
  source_id: "source.id",
  source_ids: "source.ids",
  source_status: "source.status",
  tool_name: "tool.name"
};

export const POLICY_TEMPLATES: PolicyTemplate[] = [
  {
    id: "require_active_grant",
    name: "Require Active Grant",
    className: "ps2-tc-access",
    description:
      "Require an active Access Grant before a scoped agent action can proceed.",
    tags: ["access", "blocking"],
    condition: {
      decision: "require_human_review",
      reason: "Active Access Grant is required before this governed action.",
      access_grant_status: "active",
      check_type: "access_grant_status",
      check_outcome: "pass"
    }
  },
  {
    id: "hard_deny_action",
    name: "Hard Deny Action",
    className: "ps2-tc-deny",
    description:
      "Deny a specific high-risk action type without adding an approval path.",
    tags: ["deny", "enforcement"],
    condition: {
      decision: "deny",
      reason: "The requested action is not allowed by governance policy.",
      action_type: "external_api_call",
      risk_level: "critical"
    }
  },
  {
    id: "evidence_collection",
    name: "Evidence Collection",
    className: "ps2-tc-evidence",
    description:
      "Require audit evidence collection for matching policy decisions.",
    tags: ["audit", "evidence"],
    condition: {
      decision: "allow",
      reason: "Action may proceed while AGCP records bounded evidence metadata.",
      check_type: "data_usage_profile_status",
      check_outcome: "pass"
    }
  },
  {
    id: "governance_review_gate",
    name: "Governance Review Gate",
    className: "ps2-tc-review",
    description:
      "Route high-risk production actions through HumanApproval review.",
    tags: ["review", "runtime"],
    condition: {
      decision: "require_human_review",
      reason: "High-risk production action requires governance review.",
      environment: "production",
      risk_level: "high",
      action_type: "external_api_call"
    }
  },
  {
    id: "risk_threshold_trigger",
    name: "Risk Threshold Trigger",
    className: "ps2-tc-risk",
    description:
      "Escalate high or critical runtime actions to human review.",
    tags: ["risk", "review"],
    condition: {
      decision: "require_human_review",
      reason: "Risk threshold requires reviewer confirmation.",
      risk_level: "critical",
      check_outcome: "unknown"
    }
  },
  {
    id: "scoped_boundary_control",
    name: "Scoped Boundary Control",
    className: "ps2-tc-scope",
    description:
      "Control external boundary actions through deterministic request fields.",
    tags: ["scope", "boundary"],
    condition: {
      decision: "require_human_review",
      reason: "External boundary action requires governance review.",
      environment: "production",
      action_type: "external_api_call",
      capability_status: "active"
    }
  },
  {
    id: "external_model_usage_guard",
    name: "External Model Usage Guard",
    className: "ps2-tc-review",
    description:
      "Require review or denial for external model providers and unapproved models.",
    tags: ["model", "external"],
    condition: {
      decision: "require_human_review",
      reason: "External model usage requires approved model governance metadata.",
      model_provider_type: "external",
      model_status: "active",
      check_type: "model_asset_status",
      check_outcome: "pass"
    }
  },
  {
    id: "confidential_vectorization_guard",
    name: "Confidential Data Vectorization Guard",
    className: "ps2-tc-access",
    description:
      "Require approved data usage and active source access before external vectorization. Use a second rule for restricted data until OR-style authoring is wired.",
    tags: ["data", "vectorization"],
    condition: {
      decision: "require_human_review",
      reason:
        "Vectorizing confidential data with an external model requires approved data usage and active source access.",
      action_type: "vectorization",
      data_classification: "confidential",
      source_data_classification: "confidential",
      model_provider_type: "external",
      model_type: "embedding",
      data_usage_review_status: "approved",
      data_usage_allowed_purpose: "vectorization",
      access_grant_status: "active",
      check_type: "data_usage_profile_status",
      check_outcome: "pass"
    }
  }
];

export function slugifyPolicyName(value: string) {
  return (
    value
      .trim()
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "_")
      .replace(/^_+|_+$/g, "") || "untitled_policy"
  );
}

export function policyFileName(policy: PolicyRecord) {
  return `${slugifyPolicyName(policy.name)}.agcp`;
}

export function parseRuleCondition(rule: PolicyRuleRecord | null | undefined) {
  if (!rule) {
    return defaultCondition();
  }

  try {
    const parsed = JSON.parse(rule.condition) as unknown;
    return parsed && typeof parsed === "object" && !Array.isArray(parsed)
      ? (parsed as PolicyCondition)
      : defaultCondition();
  } catch {
    return defaultCondition();
  }
}

export function defaultCondition(): PolicyCondition {
  return {
    decision: "require_human_review",
    reason: "Governance review is required before this action proceeds."
  };
}

export function updateConditionField(
  condition: PolicyCondition,
  field: string,
  value: ConditionValue | null | undefined
) {
  const next = { ...condition };
  const isEmptyArray = Array.isArray(value) && value.length === 0;
  if (value === null || value === undefined || value === "" || isEmptyArray) {
    delete next[field];
    return stableCondition(next);
  }

  next[field] = value;
  return stableCondition(next);
}

export function conditionToBlocksViewModel(condition: PolicyCondition) {
  return {
    checkFields: POLICY_CHECK_FIELD_CONFIGS.map((field) => ({
      ...field,
      value: condition[field.key]
    })),
    decision: String(condition.decision || "require_human_review"),
    prove:
      "PROVE is evidence intent. Evidence comes from PolicyDecision, CheckResult, review metadata, AuditLog, and Evidence Bundle.",
    reason: String(condition.reason || ""),
    whenFields: POLICY_WHEN_FIELD_CONFIGS.map((field) => ({
      ...field,
      value: condition[field.key]
    }))
  };
}

export function validateCondition(condition: PolicyCondition) {
  return parsePolicyDslToPolicyRule(
    conditionToDsl("policy_studio_validation", condition)
  );
}

export function templateToDsl(template: PolicyTemplate) {
  return conditionToDsl(slugifyPolicyName(template.name), template.condition);
}

export function conditionToDsl(policyName: string, condition: PolicyCondition) {
  const slug = slugifyPolicyName(policyName);
  const whenLines = entriesForFields(condition, WHEN_FIELDS).map((entry, index) =>
    `${index === 0 ? "  when" : "    and"} ${fieldLabel(entry.key)} ${operatorForValue(
      entry.value
    )} ${dslValue(entry.value)}`
  );
  const checkLines = entriesForFields(condition, CHECK_FIELDS).map(
    (entry) =>
      `  check ${fieldLabel(entry.key)} ${operatorForValue(entry.value)} ${dslValue(
        entry.value
      )} required`
  );
  const decision = String(condition.decision || "require_human_review");
  const reason = String(condition.reason || "");

  return [
    `policy ${slug} {`,
    "  scope selected_policy",
    "",
    ...whenLines,
    whenLines.length > 0
      ? ""
      : "  // no supported WHEN fields yet; add when tool.name == \"example_tool\"",
    ...checkLines,
    checkLines.length > 0
      ? ""
      : "  // no supported CHECK fields yet; add check access_grant.status == \"active\" required",
    `  then ${decisionToDsl(decision, reason)}`,
    "  prove decision, checks, reviewer, evidence_bundle",
    "}"
  ].join("\n");
}

export function parsePolicyDslToPolicyRule(dsl: string): ParsedPolicyDsl {
  const errors: string[] = [];
  const warnings: string[] = [];
  const unsupported: string[] = [];
  const structural: string[] = [];
  const condition: PolicyCondition = {};
  const lines = dsl
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean)
    .filter((line) => !line.startsWith("//"));

  const policyLine = lines.find((line) => line.startsWith("policy "));
  const policyNameMatch = policyLine?.match(/^policy\s+([a-zA-Z0-9_ -]+)/);
  const policyName = policyNameMatch
    ? slugifyPolicyName(policyNameMatch[1])
    : "untitled_policy";

  for (const rawLine of lines) {
    const line = rawLine.replace(/\s+required$/, "").trim();

    if (isStructuralDslLine(line)) {
      structural.push(rawLine);
      continue;
    }

    if (
      line.startsWith("when ") ||
      line.startsWith("and ") ||
      line.startsWith("check ")
    ) {
      const expression = line.replace(/^(when|and|check)\s+/, "");
      const parsedExpression = parseExpression(expression);
      if (!parsedExpression) {
        unsupported.push(rawLine);
        continue;
      }

      const field = resolveField(parsedExpression.field);
      if (!field) {
        unsupported.push(rawLine);
        continue;
      }

      condition[field] = parsedExpression.value;
      continue;
    }

    if (line.startsWith("then ")) {
      const decision = parseDecision(line.replace(/^then\s+/, ""));
      if (!decision) {
        unsupported.push(rawLine);
      } else {
        condition.decision = decision.decision;
        condition.reason = decision.reason;
      }
      continue;
    }

    unsupported.push(rawLine);
  }

  if (!condition.decision) {
    condition.decision = "require_human_review";
  }

  if (!condition.reason || String(condition.reason).trim().length === 0) {
    errors.push("PolicyRule condition reason is required.");
  }

  if (condition.check_min_confidence !== undefined) {
    const confidence = Number(condition.check_min_confidence);
    if (!Number.isFinite(confidence) || confidence < 0 || confidence > 1) {
      errors.push("check_min_confidence must be a number between 0 and 1.");
    } else {
      condition.check_min_confidence = confidence;
    }
  }

  if (unsupported.length > 0) {
    warnings.push("Unsupported DSL lines were ignored by the local compiler.");
  }

  const hasWhen = entriesForFields(condition, WHEN_FIELDS).length > 0;
  const hasCheck = entriesForFields(condition, CHECK_FIELDS).length > 0;
  if (!hasWhen) {
    warnings.push("No supported WHEN request fields were found.");
  }
  if (!hasCheck) {
    warnings.push("No supported CHECK or inventory fields were found.");
  }

  return {
    condition: errors.length > 0 ? null : stableCondition(condition),
    errors,
    policyName,
    prove: "decision, checks, reviewer, evidence_bundle",
    ruleName: policyName,
    structural,
    unsupported,
    warnings
  };
}

export function policyBlocksFromCondition(condition: PolicyCondition): PolicyBlock[] {
  const whenBlocks = entriesForFields(condition, WHEN_FIELDS).map(
    (entry, index) => ({
      id: `when-${entry.key}`,
      group: "when" as const,
      kind: "when" as const,
      expr: `${fieldLabel(entry.key)} ${operatorForValue(entry.value)} ${dslValue(
        entry.value
      )}`,
      detail: index === 0 ? "runtime request match" : "additional request match",
      status: "active",
      statusClass: "ps2-st-ok"
    })
  );

  const checkBlocks = entriesForFields(condition, CHECK_FIELDS).map((entry) => ({
    id: `check-${entry.key}`,
    group: "check" as const,
    kind: "check" as const,
    expr: `${fieldLabel(entry.key)} ${operatorForValue(entry.value)} ${dslValue(
      entry.value
    )}`,
    detail: "inventory, review, or CheckResult constraint",
    status: "required",
    statusClass: "ps2-st-req"
  }));

  return [
    ...whenBlocks,
    ...checkBlocks,
    {
      id: "then-decision",
      group: "then",
      kind: "then",
      expr: decisionToDsl(
        String(condition.decision || "require_human_review"),
        String(condition.reason || "")
      ),
      detail: "runtime decision emitted by PolicyRule condition",
      status:
        condition.decision === "allow"
          ? "allow"
          : condition.decision === "deny"
            ? "deny"
            : "review",
      statusClass:
        condition.decision === "allow"
          ? "ps2-st-ok"
          : condition.decision === "deny"
            ? "ps2-st-req"
            : "ps2-st-pnd"
    },
    {
      id: "prove-evidence",
      group: "prove",
      kind: "prove",
      expr: "decision, checks, reviewer, evidence_bundle",
      detail: "AGCP records policy decisions, check results, approvals, and evidence bundles when available",
      status: "metadata",
      statusClass: "ps2-st-col"
    }
  ];
}

export function compilePolicyRulePreview(parsed: ParsedPolicyDsl) {
  const condition = parsed.condition;
  const checkFields = condition
    ? entriesForFields(condition, CHECK_FIELDS).map((entry) => entry.key)
    : [];
  const decision = condition
    ? String(condition.decision || "require_human_review")
    : "uncompiled";

  return {
    checkFields,
    decision,
    hasEvidenceIntent: Boolean(parsed.prove),
    policyRuleCount: condition ? 1 : 0,
    usesCheckFields: checkFields.length > 0
  };
}

export function localValidationMessages(parsed: ParsedPolicyDsl) {
  const messages: Array<{ tone: "ok" | "warn" | "error" | "info"; text: string }> = [];

  if (parsed.errors.length === 0) {
    messages.push({ tone: "ok", text: `policy ${parsed.policyName} parsed` });
    messages.push({
      tone: "ok",
      text: "condition JSON generated from supported AGCP fields"
    });
    messages.push({
      tone: "ok",
      text: "Compiled editor state maps to deterministic PolicyRule condition JSON"
    });
    messages.push({
      tone: "ok",
      text: "Required fields present: decision and reason"
    });
    messages.push({
      tone: parsed.unsupported.length > 0 ? "warn" : "ok",
      text:
        parsed.unsupported.length > 0
          ? "Save draft is blocked until unsupported DSL lines are removed"
          : "Save draft is possible from this editor state"
    });
    messages.push({
      tone: "info",
      text: `Generated deterministic condition JSON: ${compactConditionPreview(
        parsed.condition
      )}`
    });
  }

  for (const error of parsed.errors) {
    messages.push({ tone: "error", text: error });
  }

  for (const warning of parsed.warnings) {
    messages.push({ tone: "warn", text: warning });
  }

  if (parsed.unsupported.length > 0) {
    messages.push({
      tone: "warn",
      text: `${parsed.unsupported.length} unsupported DSL line(s) ignored locally`
    });
  }

  messages.push({
    tone: "info",
    text: "Backend simulation unavailable; this is local validation only"
  });
  messages.push({
    tone: "info",
    text: "No backend simulation endpoint wired; Save draft creates a draft PolicyVersion and does not affect runtime until activation"
  });

  return messages;
}

export function summarizePolicyRule(condition: PolicyCondition) {
  const decision = String(condition.decision || "require_human_review");
  const when = entriesForFields(condition, WHEN_FIELDS)
    .map((entry) => `${fieldLabel(entry.key)} ${formatValue(entry.value)}`)
    .join(", ");
  const checks = entriesForFields(condition, CHECK_FIELDS)
    .map((entry) => `${fieldLabel(entry.key)} ${formatValue(entry.value)}`)
    .join(", ");

  return [
    when ? `When ${when}` : "When a supported runtime request matches",
    checks ? `and checks require ${checks}` : "with no supported check constraints",
    `AGCP returns ${decisionLabel(decision)}.`,
    "Evidence intent covers policy decisions, check outcomes, approvals, and evidence bundles when available."
  ].join(" ");
}

export function unsupportedConditionFields(condition: PolicyCondition) {
  return Object.keys(condition)
    .filter((field) => !SUPPORTED_CONDITION_FIELDS.has(field))
    .sort();
}

export function stableCondition(condition: PolicyCondition): PolicyCondition {
  const sorted: PolicyCondition = {};
  for (const key of Object.keys(condition).sort()) {
    sorted[key] = condition[key];
  }
  return sorted;
}

export function jsonConditionPreview(condition: PolicyCondition | null) {
  return JSON.stringify(condition || {}, null, 2);
}

function entriesForFields(
  condition: PolicyCondition,
  fields: readonly string[]
) {
  return fields
    .filter((field) => condition[field] !== undefined && condition[field] !== "")
    .map((key) => ({ key, value: condition[key] }));
}

function fieldLabel(key: string) {
  return FIELD_LABELS[key] || key;
}

function resolveField(field: string) {
  const normalized = field.trim();
  if (FIELD_ALIASES[normalized]) {
    return FIELD_ALIASES[normalized];
  }

  if (
    WHEN_FIELDS.includes(normalized as (typeof WHEN_FIELDS)[number]) ||
    CHECK_FIELDS.includes(normalized as (typeof CHECK_FIELDS)[number]) ||
    normalized === "decision" ||
    normalized === "reason"
  ) {
    return normalized;
  }

  return null;
}

function isStructuralDslLine(line: string) {
  return (
    line === "}" ||
    line.endsWith("{") ||
    line.startsWith("policy ") ||
    line.startsWith("scope ") ||
    line.startsWith("prove ")
  );
}

function parseExpression(expression: string) {
  const inMatch = expression.match(/^([a-zA-Z0-9_.]+)\s+in\s+(\[[^\]]*\])$/);
  if (inMatch) {
    return { field: inMatch[1], value: parseValue(inMatch[2]) };
  }

  const comparisonMatch = expression.match(
    /^([a-zA-Z0-9_.]+)\s*(==|>=|<=|>|<)\s*(.+)$/
  );
  if (!comparisonMatch) {
    return null;
  }

  return {
    field: comparisonMatch[1],
    value: parseValue(comparisonMatch[3])
  };
}

function parseValue(rawValue: string): ConditionValue {
  const value = rawValue.trim().replace(/,$/, "");
  if (value.startsWith("[") && value.endsWith("]")) {
    return value
      .slice(1, -1)
      .split(",")
      .map((item) => item.trim().replace(/^"|"$/g, ""))
      .filter(Boolean);
  }

  if (value === "true") {
    return true;
  }
  if (value === "false") {
    return false;
  }
  if (/^-?\d+(\.\d+)?$/.test(value)) {
    return Number(value);
  }

  return value.replace(/^"|"$/g, "");
}

function parseDecision(expression: string):
  | { decision: PolicyRuleDecision; reason: string }
  | null {
  const match = expression.match(/^([a-z_]+)(?:\((.*)\))?$/);
  if (!match) {
    return null;
  }

  const rawDecision = match[1];
  const decision =
    rawDecision === "require_review"
      ? "require_human_review"
      : (rawDecision as PolicyRuleDecision);
  if (
    decision !== "allow" &&
    decision !== "deny" &&
    decision !== "require_human_review" &&
    decision !== "not_applicable"
  ) {
    return null;
  }

  const reason = match[2] === undefined ? "" : match[2].trim().replace(/^"|"$/g, "");

  return { decision, reason };
}

function defaultReasonForDecision(decision: PolicyRuleDecision) {
  if (decision === "allow") {
    return "Policy conditions allow this governed action.";
  }
  if (decision === "deny") {
    return "Policy conditions deny this governed action.";
  }
  if (decision === "not_applicable") {
    return "Policy does not apply to this runtime request.";
  }
  return "Policy conditions require human review.";
}

function decisionToDsl(decision: string, reason: string) {
  const escapedReason = reason.replace(/"/g, '\\"');
  if (decision === "require_human_review") {
    return `require_review("${escapedReason}")`;
  }
  return `${decision}("${escapedReason}")`;
}

function operatorForValue(value: ConditionValue) {
  return Array.isArray(value) ? "in" : "==";
}

function dslValue(value: ConditionValue) {
  if (Array.isArray(value)) {
    return `[${value.map((item) => `"${item}"`).join(", ")}]`;
  }

  if (typeof value === "string") {
    return `"${value}"`;
  }

  return String(value);
}

function formatValue(value: ConditionValue) {
  if (Array.isArray(value)) {
    return `[${value.join(", ")}]`;
  }

  return String(value);
}

function decisionLabel(decision: string) {
  return decision.replace(/_/g, " ");
}

function compactConditionPreview(condition: PolicyCondition | null) {
  return JSON.stringify(condition || {});
}
