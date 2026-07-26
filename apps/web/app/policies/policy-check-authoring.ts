import type { AgentRecord } from "../lib/agents";
import type {
  PolicyCheckEvidenceRetention,
  PolicyCheckExpectedOutcome,
  PolicyCheckFailureBehavior,
  PolicyCheckMetadataValue,
  PolicyCheckStatus,
  PolicyCheckStepRecord,
  PolicyCheckTargetSelector,
  PolicyCheckType
} from "../lib/policy-check-steps";
import type {
  AccessGrantRecord,
  CapabilityRecord,
  DataUsageProfile,
  ModelAssetRecord,
  SourceRecord
} from "../lib/sources";
import type {
  PolicyCondition,
  PolicyValidationMessage
} from "./policy-dsl";

export const POLICY_CHECK_TYPES = [
  "access_grant_status",
  "data_usage_profile_status",
  "source_status",
  "source_classification",
  "capability_status",
  "model_asset_status",
  "model_provider_type"
] as const satisfies readonly PolicyCheckType[];

export const POLICY_CHECK_FAILURE_BEHAVIORS = [
  "record_only",
  "require_human_review",
  "fail_closed",
  "ignore_if_unavailable"
] as const satisfies readonly PolicyCheckFailureBehavior[];

export const POLICY_CHECK_EVIDENCE_RETENTION = [
  "decision_only",
  "evidence_bundle",
  "none"
] as const satisfies readonly PolicyCheckEvidenceRetention[];

export const POLICY_CHECK_STATUSES = [
  "active",
  "disabled",
  "retired"
] as const satisfies readonly PolicyCheckStatus[];

export const POLICY_CHECK_EXPECTED_OUTCOMES = [
  "pass",
  "fail",
  "unknown",
  "error",
  "not_applicable"
] as const satisfies readonly PolicyCheckExpectedOutcome[];

export const POLICY_CHECK_TARGET_SELECTOR_BY_TYPE: Record<
  PolicyCheckType,
  PolicyCheckTargetSelector
> = {
  access_grant_status: "access_grants",
  capability_status: "capability_id",
  data_usage_profile_status: "source_ids",
  model_asset_status: "model_id",
  model_provider_type: "model_id",
  source_classification: "source_ids",
  source_status: "source_ids"
};

const CHECK_RESULT_TARGET_TYPE_BY_TYPE: Record<PolicyCheckType, string> = {
  access_grant_status: "access_grant",
  capability_status: "capability",
  data_usage_profile_status: "data_usage_profile",
  model_asset_status: "model_asset",
  model_provider_type: "model_asset",
  source_classification: "source",
  source_status: "source"
};

const UNSAFE_METADATA_KEY_PARTS = [
  "access_token",
  "api_key",
  "authorization",
  "chunk",
  "credential",
  "document_content",
  "password",
  "payload",
  "prompt",
  "private_customer_data",
  "raw_content",
  "refresh_token",
  "secret",
  "source_content",
  "token"
] as const;

export type PolicyCheckDraft = PolicyCheckStepRecord;

export type PolicyCheckTargetOption = {
  id: string;
  label: string;
  detail: string;
  runtimeTargetId: string;
};

export type PolicyCheckInventory = {
  accessGrants: AccessGrantRecord[];
  agents: AgentRecord[];
  capabilities: CapabilityRecord[];
  dataUsageProfiles: Array<{
    profile: DataUsageProfile;
    source: SourceRecord;
  }>;
  models: ModelAssetRecord[];
  sources: SourceRecord[];
};

export type PolicyCheckInventoryState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | {
      status: "ready";
      inventory: PolicyCheckInventory;
      profileWarning: string | null;
    };

export type PolicyCheckValidation = {
  checkId: string;
  messages: PolicyValidationMessage[];
  valid: boolean;
};

export function createPolicyCheckDraft(
  policyRuleId: string,
  checkType: PolicyCheckType = "source_status"
): PolicyCheckDraft {
  return {
    check_tool_id: null,
    check_type: checkType,
    evidence_retention: "decision_only",
    failure_behavior: "record_only",
    id: crypto.randomUUID(),
    metadata: {
      expected_outcome: "pass"
    },
    min_confidence: null,
    policy_rule_id: policyRuleId,
    required: true,
    status: "active",
    target_selector: POLICY_CHECK_TARGET_SELECTOR_BY_TYPE[checkType]
  };
}

export function policyCheckDraftsFromSnapshots(
  snapshots: Array<Record<string, unknown>>,
  policyRuleId: string
): PolicyCheckDraft[] {
  return snapshots.flatMap((snapshot) => {
    const parsed = parsePolicyCheckSnapshot(snapshot, policyRuleId);
    return parsed ? [parsed] : [];
  });
}

export function policyCheckDraftsFromRecords(
  records: PolicyCheckStepRecord[],
  policyRuleId: string
): PolicyCheckDraft[] {
  return records.map((record) => ({
    ...record,
    metadata: {
      expected_outcome: "pass",
      ...record.metadata
    },
    policy_rule_id: policyRuleId
  }));
}

export function policyCheckSnapshots(
  checks: PolicyCheckDraft[],
  policyRuleId: string
): Array<Record<string, unknown>> {
  return checks.map((check) => ({
    check_tool_id: check.check_tool_id,
    check_type: check.check_type,
    evidence_retention: check.evidence_retention,
    failure_behavior: check.failure_behavior,
    id: check.id,
    metadata: { ...check.metadata },
    min_confidence: check.min_confidence,
    policy_rule_id: policyRuleId,
    required: check.required,
    status: check.status,
    target_selector: check.target_selector
  }));
}

export function policyCheckDefinition(checkType: PolicyCheckType) {
  const definitions: Record<
    PolicyCheckType,
    { description: string; label: string; targetLabel: string }
  > = {
    access_grant_status: {
      description: "Observe the status of a real Access Grant selected for this rule.",
      label: "Access Grant status",
      targetLabel: "Access Grant"
    },
    capability_status: {
      description: "Observe Capability inventory status from runtime request context.",
      label: "Capability status",
      targetLabel: "Capability"
    },
    data_usage_profile_status: {
      description: "Observe the review status of a Source Data Usage Profile.",
      label: "Data Usage Profile review status",
      targetLabel: "Data Usage Profile"
    },
    model_asset_status: {
      description: "Observe ModelAsset inventory status from runtime request context.",
      label: "Model status",
      targetLabel: "ModelAsset"
    },
    model_provider_type: {
      description: "Observe whether a ModelAsset provider is external, local, or unknown.",
      label: "Model provider type",
      targetLabel: "ModelAsset"
    },
    source_classification: {
      description: "Observe the governed classification metadata for a Source.",
      label: "Source classification",
      targetLabel: "Source"
    },
    source_status: {
      description: "Observe Source inventory status from runtime request context.",
      label: "Source status",
      targetLabel: "Source"
    }
  };
  return definitions[checkType];
}

export function policyCheckExpectedOutcome(
  check: PolicyCheckDraft
): PolicyCheckExpectedOutcome {
  const value = check.metadata.expected_outcome;
  return POLICY_CHECK_EXPECTED_OUTCOMES.includes(
    value as PolicyCheckExpectedOutcome
  )
    ? (value as PolicyCheckExpectedOutcome)
    : "pass";
}

export function policyCheckTargetId(check: PolicyCheckDraft) {
  return typeof check.metadata.governed_target_id === "string"
    ? check.metadata.governed_target_id
    : "";
}

export function policyCheckTargetName(check: PolicyCheckDraft) {
  return typeof check.metadata.governed_target_name === "string"
    ? check.metadata.governed_target_name
    : "";
}

export function policyCheckRuntimeTargetId(check: PolicyCheckDraft) {
  return typeof check.metadata.runtime_target_id === "string"
    ? check.metadata.runtime_target_id
    : policyCheckTargetId(check);
}

export function policyCheckTargetOptions(
  checkType: PolicyCheckType,
  inventory: PolicyCheckInventory
): PolicyCheckTargetOption[] {
  if (checkType === "access_grant_status") {
    const agentNames = new Map(
      inventory.agents.map((agent) => [agent.id, agent.name])
    );
    return inventory.accessGrants.map((grant) => ({
      detail: `${agentNames.get(grant.subject_id) || grant.subject_id} / ${grant.target_type} / ${grant.status}`,
      id: grant.id,
      label: grant.name,
      runtimeTargetId: grant.id
    }));
  }
  if (checkType === "capability_status") {
    return inventory.capabilities.map((capability) => ({
      detail: `${capability.capability_type} / ${capability.status}`,
      id: capability.id,
      label: capability.name,
      runtimeTargetId: capability.id
    }));
  }
  if (checkType === "data_usage_profile_status") {
    return inventory.dataUsageProfiles.map(({ profile, source }) => ({
      detail: `${source.name} / ${profile.review_status}`,
      id: source.id,
      label: `${source.name} usage profile`,
      runtimeTargetId: profile.id
    }));
  }
  if (
    checkType === "model_asset_status" ||
    checkType === "model_provider_type"
  ) {
    return inventory.models.map((model) => ({
      detail: `${model.provider} / ${model.status}`,
      id: model.id,
      label: model.name,
      runtimeTargetId: model.id
    }));
  }
  return inventory.sources.map((source) => ({
    detail: `${source.source_type} / ${source.status}`,
    id: source.id,
    label: source.name,
    runtimeTargetId: source.id
  }));
}

export function updatePolicyCheckType(
  check: PolicyCheckDraft,
  checkType: PolicyCheckType
): PolicyCheckDraft {
  const metadata = { ...check.metadata };
  delete metadata.governed_target_id;
  delete metadata.governed_target_name;
  delete metadata.runtime_target_id;
  return {
    ...check,
    check_type: checkType,
    metadata,
    target_selector: POLICY_CHECK_TARGET_SELECTOR_BY_TYPE[checkType]
  };
}

export function updatePolicyCheckTarget(
  check: PolicyCheckDraft,
  target: PolicyCheckTargetOption | null
): PolicyCheckDraft {
  const metadata = { ...check.metadata };
  if (!target) {
    delete metadata.governed_target_id;
    delete metadata.governed_target_name;
    delete metadata.runtime_target_id;
  } else {
    metadata.governed_target_id = target.id;
    metadata.governed_target_name = target.label;
    metadata.runtime_target_id = target.runtimeTargetId;
  }
  return { ...check, metadata };
}

export function updatePolicyCheckExpectedOutcome(
  check: PolicyCheckDraft,
  outcome: PolicyCheckExpectedOutcome
): PolicyCheckDraft {
  return {
    ...check,
    metadata: {
      ...check.metadata,
      expected_outcome: outcome
    }
  };
}

export function applyPolicyCheckCondition(
  condition: PolicyCondition,
  check: PolicyCheckDraft
): PolicyCondition {
  const targetId = policyCheckRuntimeTargetId(check);
  return {
    ...condition,
    check_outcome: policyCheckExpectedOutcome(check),
    check_target_id: targetId,
    check_target_type: CHECK_RESULT_TARGET_TYPE_BY_TYPE[check.check_type],
    check_type: check.check_type
  };
}

export function isPolicyCheckConditionLinked(
  condition: PolicyCondition,
  check: PolicyCheckDraft
) {
  return (
    condition.check_type === check.check_type &&
    condition.check_outcome === policyCheckExpectedOutcome(check) &&
    condition.check_target_type ===
      CHECK_RESULT_TARGET_TYPE_BY_TYPE[check.check_type] &&
    condition.check_target_id === policyCheckRuntimeTargetId(check)
  );
}

export function validatePolicyChecks(
  checks: PolicyCheckDraft[],
  condition: PolicyCondition,
  inventoryState: PolicyCheckInventoryState
): {
  byCheckId: Map<string, PolicyCheckValidation>;
  messages: PolicyValidationMessage[];
} {
  const byCheckId = new Map<string, PolicyCheckValidation>();
  const messages: PolicyValidationMessage[] = [];
  const identities = new Map<string, number>();
  const availableTargets =
    inventoryState.status === "ready"
      ? new Map(
          POLICY_CHECK_TYPES.map((checkType) => [
            checkType,
            new Set(
              policyCheckTargetOptions(checkType, inventoryState.inventory).map(
                (target) => target.id
              )
            )
          ])
        )
      : null;

  for (const check of checks) {
    const checkMessages: PolicyValidationMessage[] = [];
    if (!POLICY_CHECK_TYPES.includes(check.check_type)) {
      checkMessages.push(blocking("Unsupported check type."));
    }
    if (
      check.target_selector !==
      POLICY_CHECK_TARGET_SELECTOR_BY_TYPE[check.check_type]
    ) {
      checkMessages.push(
        blocking("Check type and target selector are incompatible.")
      );
    }
    const targetId = policyCheckTargetId(check);
    if (!targetId) {
      checkMessages.push(blocking("Select a real governed target."));
    } else if (
      availableTargets &&
      !availableTargets.get(check.check_type)?.has(targetId)
    ) {
      checkMessages.push(
        blocking("The selected governed target is not present in backend inventory.")
      );
    }
    if (
      typeof check.metadata.expected_outcome !== "string" ||
      !POLICY_CHECK_EXPECTED_OUTCOMES.includes(
        check.metadata.expected_outcome as PolicyCheckExpectedOutcome
      )
    ) {
      checkMessages.push(blocking("Expected outcome is unsupported."));
    }
    if (
      check.min_confidence !== null &&
      (!Number.isFinite(check.min_confidence) ||
        check.min_confidence < 0 ||
        check.min_confidence > 1)
    ) {
      checkMessages.push(
        blocking("Minimum confidence must be between 0 and 1.")
      );
    }
    if (!POLICY_CHECK_FAILURE_BEHAVIORS.includes(check.failure_behavior)) {
      checkMessages.push(blocking("Failure behavior is unsupported."));
    }
    if (!POLICY_CHECK_EVIDENCE_RETENTION.includes(check.evidence_retention)) {
      checkMessages.push(blocking("Evidence retention is unsupported."));
    }
    if (!POLICY_CHECK_STATUSES.includes(check.status)) {
      checkMessages.push(blocking("PolicyCheckStep status is unsupported."));
    }
    const unsafeKeys = Object.keys(check.metadata).filter(isUnsafeMetadataKey);
    if (unsafeKeys.length > 0) {
      checkMessages.push(
        blocking(`Unsafe metadata key(s): ${unsafeKeys.join(", ")}.`)
      );
    }
    const identity = `${check.check_type}:${check.target_selector}:${targetId}`;
    identities.set(identity, (identities.get(identity) || 0) + 1);
    byCheckId.set(check.id, {
      checkId: check.id,
      messages: checkMessages,
      valid: checkMessages.every((message) => message.tone !== "blocking")
    });
    messages.push(...checkMessages);
  }

  for (const check of checks) {
    const identity = `${check.check_type}:${check.target_selector}:${policyCheckTargetId(
      check
    )}`;
    if ((identities.get(identity) || 0) <= 1) {
      continue;
    }
    const duplicateMessage = blocking(
      `${policyCheckDefinition(check.check_type).label} duplicates another check for the same governed target.`
    );
    const validation = byCheckId.get(check.id);
    if (validation) {
      validation.messages.push(duplicateMessage);
      validation.valid = false;
    }
    messages.push(duplicateMessage);
  }

  const hasConditionReference =
    typeof condition.check_type === "string" ||
    typeof condition.check_outcome === "string";
  if (
    checks.length > 0 &&
    hasConditionReference &&
    !checks.some((check) => isPolicyCheckConditionLinked(condition, check))
  ) {
    messages.push(
      blocking(
        "The PolicyRule check outcome condition does not reference an authored check."
      )
    );
  } else if (
    checks.length > 0 &&
    !checks.some((check) => isPolicyCheckConditionLinked(condition, check))
  ) {
    messages.push({
      tone: "attention",
      text: "Authored checks currently collect evidence only. Link one expected result to the PolicyRule condition to affect the final THEN decision."
    });
  }

  if (inventoryState.status === "error" && checks.length > 0) {
    messages.push(blocking(inventoryState.message));
  }
  if (inventoryState.status === "loading" && checks.length > 0) {
    messages.push(
      blocking(
        "Wait for governed target inventory to load before saving PolicyCheckSteps."
      )
    );
  }

  return { byCheckId, messages };
}

export function policyCheckFailureBehaviorHelp(
  behavior: PolicyCheckFailureBehavior
) {
  const labels: Record<PolicyCheckFailureBehavior, string> = {
    fail_closed:
      "Evidence intent only today. It does not automatically deny the request.",
    ignore_if_unavailable:
      "Evidence intent only today. The final PolicyRule condition remains authoritative.",
    record_only:
      "Records bounded CheckResult evidence without changing the decision by itself.",
    require_human_review:
      "Evidence intent only today. Human review occurs only when the PolicyRule THEN decision requires it."
  };
  return labels[behavior];
}

export function policyCheckEvidenceRetentionHelp(
  retention: PolicyCheckEvidenceRetention
) {
  const labels: Record<PolicyCheckEvidenceRetention, string> = {
    decision_only:
      "Declares bounded decision-context retention intent; related audit references may remain.",
    evidence_bundle:
      "Declares that safe CheckResult summaries should be available to Evidence Bundles.",
    none:
      "Declares no additional check evidence retention; it is not a total-deletion guarantee."
  };
  return labels[retention];
}

export function policyCheckCodePreview(checks: PolicyCheckDraft[]) {
  if (checks.length === 0) {
    return "# No persisted PolicyCheckStep snapshots in this draft.";
  }
  return checks
    .map((check) =>
      [
        `CHECK_STEP ${check.check_type}`,
        `  TARGET_SELECTOR ${check.target_selector}`,
        `  EXPECTED_TARGET_ID "${policyCheckRuntimeTargetId(check)}"`,
        `  EXPECT ${policyCheckExpectedOutcome(check)}`,
        `  ON_FAILURE ${check.failure_behavior}`,
        `  RETAIN ${check.evidence_retention}`,
        `  STATUS ${check.status}`
      ].join("\n")
    )
    .join("\n\n");
}

function parsePolicyCheckSnapshot(
  snapshot: Record<string, unknown>,
  policyRuleId: string
): PolicyCheckDraft | null {
  if (
    typeof snapshot.id !== "string" ||
    !POLICY_CHECK_TYPES.includes(snapshot.check_type as PolicyCheckType) ||
    !POLICY_CHECK_FAILURE_BEHAVIORS.includes(
      snapshot.failure_behavior as PolicyCheckFailureBehavior
    ) ||
    !POLICY_CHECK_EVIDENCE_RETENTION.includes(
      snapshot.evidence_retention as PolicyCheckEvidenceRetention
    ) ||
    !POLICY_CHECK_STATUSES.includes(snapshot.status as PolicyCheckStatus)
  ) {
    return null;
  }
  const checkType = snapshot.check_type as PolicyCheckType;
  const metadata =
    snapshot.metadata &&
    typeof snapshot.metadata === "object" &&
    !Array.isArray(snapshot.metadata)
      ? (snapshot.metadata as Record<string, PolicyCheckMetadataValue>)
      : {};
  return {
    check_tool_id:
      typeof snapshot.check_tool_id === "string" ? snapshot.check_tool_id : null,
    check_type: checkType,
    evidence_retention:
      snapshot.evidence_retention as PolicyCheckEvidenceRetention,
    failure_behavior: snapshot.failure_behavior as PolicyCheckFailureBehavior,
    id: snapshot.id,
    metadata: {
      expected_outcome: "pass",
      ...metadata
    },
    min_confidence:
      typeof snapshot.min_confidence === "number"
        ? snapshot.min_confidence
        : null,
    policy_rule_id: policyRuleId,
    required: snapshot.required !== false,
    status: snapshot.status as PolicyCheckStatus,
    target_selector:
      typeof snapshot.target_selector === "string"
        ? (snapshot.target_selector as PolicyCheckTargetSelector)
        : POLICY_CHECK_TARGET_SELECTOR_BY_TYPE[checkType]
  };
}

function isUnsafeMetadataKey(key: string) {
  const normalized = key.toLowerCase();
  return UNSAFE_METADATA_KEY_PARTS.some((part) => normalized.includes(part));
}

function blocking(text: string): PolicyValidationMessage {
  return { text, tone: "blocking" };
}
