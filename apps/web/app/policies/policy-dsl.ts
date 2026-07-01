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

export type PolicyValidationMessageTone =
  | "success"
  | "info"
  | "attention"
  | "blocking";

export type PolicyValidationMessage = {
  tone: PolicyValidationMessageTone;
  text: string;
};

export type PolicyBlock = {
  id: string;
  field?: string;
  group: "when" | "check" | "then" | "prove";
  kind: "when" | "check" | "then" | "prove";
  expr: string;
  detail: string;
  status: string;
  statusClass: string;
};

export type ConditionFieldGroup = "when" | "check" | "then" | "prove";

export type ConditionFieldDefinition = {
  field: string;
  group: ConditionFieldGroup;
  label: string;
  valueType: "number" | "select" | "text";
  defaultValue: ConditionValue;
  options?: readonly string[];
  help: string;
};

const WHEN_FIELDS = [
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

const CHECK_FIELDS = [
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

const SUPPORTED_CONDITION_FIELDS = new Set<string>([
  "decision",
  "reason",
  ...WHEN_FIELDS,
  ...CHECK_FIELDS
]);

const UUID_PLACEHOLDERS = {
  capability_id: "00000000-0000-4000-8000-000000000002",
  model_id: "00000000-0000-4000-8000-000000000001",
  source_id: "00000000-0000-4000-8000-000000000000"
} as const;

export const CONDITION_FIELD_DEFINITIONS: ConditionFieldDefinition[] = [
  {
    field: "action_type",
    group: "when",
    label: "action_type",
    valueType: "text",
    defaultValue: "external_api_call",
    help: "Runtime action type declared by the caller."
  },
  {
    field: "tool_name",
    group: "when",
    label: "tool_name",
    valueType: "text",
    defaultValue: "example_tool",
    help: "Tool name from the runtime request."
  },
  {
    field: "environment",
    group: "when",
    label: "environment",
    valueType: "select",
    defaultValue: "production",
    options: ["development", "staging", "production"],
    help: "Agent environment for the governed request."
  },
  {
    field: "risk_level",
    group: "when",
    label: "risk_level",
    valueType: "select",
    defaultValue: "high",
    options: ["low", "medium", "high", "critical"],
    help: "Risk level attached to the Agent or request context."
  },
  {
    field: "source_id",
    group: "when",
    label: "source_id",
    valueType: "text",
    defaultValue: UUID_PLACEHOLDERS.source_id,
    help: "Source UUID reference. Replace the placeholder before relying on it."
  },
  {
    field: "model_id",
    group: "when",
    label: "model_id",
    valueType: "text",
    defaultValue: UUID_PLACEHOLDERS.model_id,
    help: "Model UUID reference. Replace the placeholder before relying on it."
  },
  {
    field: "capability_id",
    group: "when",
    label: "capability_id",
    valueType: "text",
    defaultValue: UUID_PLACEHOLDERS.capability_id,
    help: "Capability UUID reference. Replace the placeholder before relying on it."
  },
  {
    field: "purpose",
    group: "when",
    label: "purpose",
    valueType: "text",
    defaultValue: "governed_action",
    help: "Safe purpose label declared by the caller."
  },
  {
    field: "data_classification",
    group: "when",
    label: "data_classification",
    valueType: "select",
    defaultValue: "confidential",
    options: ["public", "internal", "confidential", "restricted"],
    help: "Declared data classification for the request."
  },
  {
    field: "check_type",
    group: "check",
    label: "check_type",
    valueType: "select",
    defaultValue: "access_grant_status",
    options: [
      "access_grant_status",
      "data_usage_profile_status",
      "source_status",
      "source_classification",
      "capability_status",
      "model_asset_status",
      "model_provider_type"
    ],
    help: "Safe CheckResult or metadata check type."
  },
  {
    field: "check_outcome",
    group: "check",
    label: "check_outcome",
    valueType: "select",
    defaultValue: "pass",
    options: ["pass", "fail", "unknown", "error", "not_applicable"],
    help: "CheckResult outcome matched by this PolicyRule."
  },
  {
    field: "access_grant_status",
    group: "check",
    label: "access_grant_status",
    valueType: "select",
    defaultValue: "active",
    options: ["pending_review", "active", "suspended", "revoked", "expired", "missing"],
    help: "Resolved AccessGrant status fact."
  },
  {
    field: "data_usage_review_status",
    group: "check",
    label: "data_usage_review_status",
    valueType: "select",
    defaultValue: "approved",
    options: ["draft", "approved", "rejected", "expired", "needs_review", "missing"],
    help: "Resolved Data Usage Profile review status."
  },
  {
    field: "source_status",
    group: "check",
    label: "source_status",
    valueType: "select",
    defaultValue: "active",
    options: ["active", "disabled", "retired", "missing"],
    help: "Resolved Source inventory status."
  },
  {
    field: "source_data_classification",
    group: "check",
    label: "source_classification",
    valueType: "select",
    defaultValue: "confidential",
    options: ["public", "internal", "confidential", "restricted"],
    help: "Resolved Source Data Usage Profile classification."
  },
  {
    field: "model_status",
    group: "check",
    label: "model_asset_status",
    valueType: "select",
    defaultValue: "active",
    options: ["active", "disabled", "retired", "missing"],
    help: "Resolved Model inventory status."
  },
  {
    field: "model_provider_type",
    group: "check",
    label: "model_provider_type",
    valueType: "select",
    defaultValue: "external",
    options: ["external", "local", "unknown"],
    help: "Resolved model provider type classification."
  },
  {
    field: "capability_status",
    group: "check",
    label: "capability_status",
    valueType: "select",
    defaultValue: "active",
    options: ["active", "disabled", "retired", "missing"],
    help: "Resolved Capability inventory status."
  },
  {
    field: "decision",
    group: "then",
    label: "decision",
    valueType: "select",
    defaultValue: "require_human_review",
    options: ["allow", "deny", "require_human_review", "not_applicable"],
    help: "PolicyDecision value returned when the rule matches."
  },
  {
    field: "reason",
    group: "then",
    label: "reason",
    valueType: "text",
    defaultValue: "Policy conditions require human review.",
    help: "Human-readable reason stored on PolicyDecision."
  },
  {
    field: "prove_intent",
    group: "prove",
    label: "evidence intent",
    valueType: "text",
    defaultValue:
      "Evidence comes from PolicyDecision, CheckResults, reviews, AuditLog, and Evidence Bundle.",
    help: "Frontend evidence intent only; not a backend proof engine."
  }
];

const FIELD_ALIASES: Record<string, string> = {
  "access_grant.status": "access_grant_status",
  "action.capability_id": "capability_id",
  "action.risk": "risk_level",
  "action.type": "action_type",
  "AgentActionEvent.action": "action_type",
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
  "DataClassificationCheck": "data_classification",
  "data_usage.allowed_purpose": "data_usage_allowed_purpose",
  "data_usage.prohibited_purpose": "data_usage_prohibited_purpose",
  "data_usage.review_status": "data_usage_review_status",
  "DestinationAllowlistCheck": "data_usage_review_status",
  "DLPContentCheck": "check_type",
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
  "tool.name": "tool_name",
  "VolumeThresholdCheck": "check_outcome"
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
    id: "data_exfiltration_prevention",
    name: "Data Exfiltration Prevention",
    className: "ps2-tc-access",
    description:
      "Prevent unauthorized outbound transfer of sensitive data through agent actions and tool use.",
    tags: ["data-protection", "exfiltration", "dlp"],
    condition: {
      decision: "deny",
      reason: "Unauthorized outbound transfer of sensitive data is blocked.",
      action_type: "transfer_data",
      data_classification: "sensitive",
      contains_sensitive_data: true,
      access_grant_status: "active",
      source_status: "active",
      data_usage_review_status: "approved",
      check_type: "data_loss_prevention",
      check_outcome: "pass"
    }
  },
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

export function conditionFieldDefinitionsForGroup(group: ConditionFieldGroup) {
  return CONDITION_FIELD_DEFINITIONS.filter(
    (definition) => definition.group === group
  );
}

export function conditionFieldDefinition(field: string) {
  return CONDITION_FIELD_DEFINITIONS.find(
    (definition) => definition.field === normalizeConditionField(field)
  );
}

export function conditionToCanvasNodes(condition: PolicyCondition) {
  return policyBlocksFromCondition(condition);
}

export function dslToCondition(dsl: string) {
  return parsePolicyDslToPolicyRule(dsl);
}

export function addConditionField(
  condition: PolicyCondition,
  field: string,
  value?: ConditionValue
) {
  const definition = conditionFieldDefinition(field);
  if (!definition) {
    return stableCondition(condition);
  }
  if (definition.field === "prove_intent") {
    return stableCondition(condition);
  }

  return updateConditionField(
    condition,
    definition.field,
    value ?? definition.defaultValue
  );
}

export function updateConditionField(
  condition: PolicyCondition,
  field: string,
  value: ConditionValue
) {
  const normalizedField = normalizeConditionField(field);
  if (normalizedField === "prove_intent") {
    return stableCondition(condition);
  }

  const nextCondition = {
    ...condition,
    [normalizedField]: normalizeConditionValue(normalizedField, value)
  };
  if (normalizedField === "decision" && !nextCondition.reason) {
    nextCondition.reason = defaultReasonForDecision(String(value) as PolicyRuleDecision);
  }

  return stableCondition(nextCondition);
}

export function removeConditionField(condition: PolicyCondition, field: string) {
  const normalizedField = normalizeConditionField(field);
  if (
    normalizedField === "decision" ||
    normalizedField === "reason" ||
    normalizedField === "prove_intent"
  ) {
    return stableCondition(condition);
  }

  const nextCondition = { ...condition };
  delete nextCondition[normalizedField];
  return stableCondition(nextCondition);
}

export function validateCondition(condition: PolicyCondition) {
  const errors: string[] = [];
  if (!condition.decision || typeof condition.decision !== "string") {
    errors.push("PolicyRule condition decision is required.");
  }
  if (!condition.reason || String(condition.reason).trim().length === 0) {
    errors.push("PolicyRule condition reason is required.");
  }
  for (const field of ["source_id", "model_id", "capability_id"]) {
    const value = condition[field];
    if (typeof value === "string" && !isUuidLike(value)) {
      errors.push(`${field} must be a UUID string.`);
    }
  }
  return errors;
}

export function templateToDsl(template: PolicyTemplate) {
  return conditionToDsl(slugifyPolicyName(template.name), template.condition);
}

export function conditionToDsl(policyName: string, condition: PolicyCondition) {
  const slug = slugifyPolicyName(policyName);
  if (
    slug === "data_exfiltration_prevention" &&
    isDataExfiltrationCondition(condition)
  ) {
    return dataExfiltrationPreventionDsl();
  }

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

function isDataExfiltrationCondition(condition: PolicyCondition) {
  return condition.action_type === "transfer_data" && condition.decision === "deny";
}

function dataExfiltrationPreventionDsl() {
  return [
    'policy "Data Exfiltration Prevention"',
    "",
    'when AgentActionEvent.action == "transfer_data"',
    "",
    'check DataClassificationCheck == "sensitive" required',
    'check DestinationAllowlistCheck == "approved" required',
    'check DLPContentCheck == "data_loss_prevention" required',
    'check VolumeThresholdCheck == "below_threshold" required',
    "",
    'then DenyAction reason "unauthorized outbound transfer"',
    'then RequireApproval reviewer_group "security-governance"',
    "",
    "prove LogDecision",
    "prove LogEvidence include check_results",
    "prove Retention days 365"
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
  const policyNameMatch =
    policyLine?.match(/^policy\s+"([^"]+)"/) ||
    policyLine?.match(/^policy\s+([a-zA-Z0-9_ -]+)/);
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
      if (line.startsWith("then RequireApproval")) {
        structural.push(rawLine);
        continue;
      }

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

  for (const validationError of validateCondition(condition)) {
    if (!errors.includes(validationError)) {
      errors.push(validationError);
    }
  }

  if (unsupported.length > 0) {
    warnings.push("Unsupported DSL lines were ignored by the local compiler.");
  }

  const hasWhen = entriesForFields(condition, WHEN_FIELDS).length > 0;
  const hasCheck = entriesForFields(condition, CHECK_FIELDS).length > 0;
  if (!hasWhen && !hasCheck) {
    warnings.push("This policy has neither WHEN request fields nor CHECK facts.");
  } else if (!hasWhen) {
    warnings.push(
      "This policy currently relies on CHECK facts rather than WHEN request fields."
    );
  } else if (!hasCheck) {
    warnings.push("This policy currently uses WHEN request fields without CHECK facts.");
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
  if (isDataExfiltrationCondition(condition)) {
    return dataExfiltrationBlocks();
  }

  const whenBlocks = entriesForFields(condition, WHEN_FIELDS).map(
    (entry, index) => ({
      field: entry.key,
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
    field: entry.key,
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
      field: "decision",
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
      detail:
        "Evidence comes from PolicyDecision, CheckResults, reviews, AuditLog, and Evidence Bundle",
      status: "metadata",
      statusClass: "ps2-st-col"
    }
  ];
}

function dataExfiltrationBlocks(): PolicyBlock[] {
  return [
    {
      id: "when-agent-action-event",
      group: "when",
      kind: "when",
      expr: "AgentActionEvent",
      detail: "Agent attempts to transfer data",
      status: "event",
      statusClass: "ps2-st-col"
    },
    {
      id: "check-data-classification",
      group: "check",
      kind: "check",
      expr: "DataClassificationCheck",
      detail: "Classify data sensitivity",
      status: "required",
      statusClass: "ps2-st-req"
    },
    {
      id: "check-destination-allowlist",
      group: "check",
      kind: "check",
      expr: "DestinationAllowlistCheck",
      detail: "Destination is in approved allowlist",
      status: "required",
      statusClass: "ps2-st-req"
    },
    {
      id: "check-dlp-content",
      group: "check",
      kind: "check",
      expr: "DLPContentCheck",
      detail: "Content does not contain sensitive data",
      status: "required",
      statusClass: "ps2-st-req"
    },
    {
      id: "check-volume-threshold",
      group: "check",
      kind: "check",
      expr: "VolumeThresholdCheck",
      detail: "Data volume is below threshold",
      status: "required",
      statusClass: "ps2-st-req"
    },
    {
      id: "then-deny-action",
      group: "then",
      kind: "then",
      expr: "DenyAction",
      detail: "Block the data transfer",
      status: "block",
      statusClass: "ps2-st-req"
    },
    {
      id: "then-require-approval",
      group: "then",
      kind: "then",
      expr: "RequireApproval",
      detail: "Require security review for exception",
      status: "review",
      statusClass: "ps2-st-pnd"
    },
    {
      id: "prove-log-decision",
      group: "prove",
      kind: "prove",
      expr: "LogDecision",
      detail: "Record decision and context",
      status: "record",
      statusClass: "ps2-st-col"
    },
    {
      id: "prove-log-evidence",
      group: "prove",
      kind: "prove",
      expr: "LogEvidence",
      detail: "Capture check results",
      status: "capture",
      statusClass: "ps2-st-col"
    },
    {
      id: "prove-retention",
      group: "prove",
      kind: "prove",
      expr: "Retention",
      detail: "Retain evidence for 365 days",
      status: "365d",
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
  const messages: PolicyValidationMessage[] = [];

  if (parsed.errors.length === 0) {
    messages.push({ tone: "success", text: `policy ${parsed.policyName} parsed` });
    messages.push({
      tone: "success",
      text: "condition JSON generated from supported AGCP fields"
    });
    messages.push({
      tone: "success",
      text: "Compiled editor state maps to deterministic PolicyRule condition JSON"
    });
    messages.push({
      tone: "success",
      text: "Required fields present: decision and reason"
    });
    messages.push({
      tone: parsed.unsupported.length > 0 ? "blocking" : "success",
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
    messages.push({ tone: "blocking", text: error });
  }

  const hasWhen = parsed.condition
    ? entriesForFields(parsed.condition, WHEN_FIELDS).length > 0
    : false;
  const hasCheck = parsed.condition
    ? entriesForFields(parsed.condition, CHECK_FIELDS).length > 0
    : false;

  for (const warning of parsed.warnings) {
    messages.push({
      tone: !hasWhen && !hasCheck ? "attention" : "info",
      text: warning
    });
  }

  if (parsed.unsupported.length > 0) {
    messages.push({
      tone: "blocking",
      text: `${parsed.unsupported.length} unsupported DSL line(s) ignored locally`
    });
  }

  messages.push({
    tone: "info",
    text: "Local validation only; no runtime decision request is executed"
  });
  messages.push({
    tone: "info",
    text: "Save draft creates a draft PolicyVersion and does not affect runtime until activation"
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

function normalizeConditionField(field: string) {
  if (field === "source_classification") {
    return "source_data_classification";
  }
  if (field === "model_asset_status") {
    return "model_status";
  }
  return field;
}

function normalizeConditionValue(field: string, value: ConditionValue) {
  const definition = conditionFieldDefinition(field);
  if (definition?.valueType === "number") {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : definition.defaultValue;
  }
  if (Array.isArray(value)) {
    return value.filter((item) => item.trim().length > 0);
  }
  if (typeof value === "string") {
    return value.trim();
  }
  return value;
}

function isUuidLike(value: string) {
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(
    value
  );
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
    line.startsWith("owner ") ||
    line.startsWith("description ") ||
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
  const denyActionMatch = expression.match(/^DenyAction\s+reason\s+(.+)$/);
  if (denyActionMatch) {
    return {
      decision: "deny",
      reason: String(parseValue(denyActionMatch[1]))
    };
  }

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
