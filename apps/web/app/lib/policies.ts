import { fetchApiArray, fetchApiJson, patchApiJson, postApiJson } from "./api";

export const POLICY_STATUSES = [
  "draft",
  "active",
  "disabled",
  "archived"
] as const;

export type PolicyStatus = (typeof POLICY_STATUSES)[number];

export const POLICY_VERSION_STATUSES = [
  "draft",
  "under_review",
  "approved",
  "rejected",
  "active",
  "superseded",
  "archived"
] as const;

export type PolicyVersionStatus = (typeof POLICY_VERSION_STATUSES)[number];

export const POLICY_RULE_DECISIONS = [
  "allow",
  "deny",
  "require_human_review",
  "not_applicable"
] as const;

export const POLICY_RULE_ENVIRONMENTS = [
  "development",
  "staging",
  "production"
] as const;

export const POLICY_RULE_RISK_LEVELS = [
  "low",
  "medium",
  "high",
  "critical"
] as const;

export const POLICY_RULE_DATA_CLASSIFICATIONS = [
  "public",
  "internal",
  "confidential",
  "restricted"
] as const;

export const POLICY_RULE_CHECK_TYPES = [
  "access_grant_status",
  "data_usage_profile_status",
  "source_status",
  "capability_status",
  "model_asset_status"
] as const;

export const POLICY_RULE_CHECK_OUTCOMES = [
  "pass",
  "fail",
  "unknown",
  "error",
  "not_applicable"
] as const;

export const POLICY_RULE_CHECK_TARGET_TYPES = [
  "source",
  "capability",
  "model_asset",
  "access_grant",
  "data_usage_profile",
  "external"
] as const;

export const POLICY_RULE_CAPABILITY_TYPES = [
  "tool",
  "api",
  "integration",
  "workflow_action",
  "other"
] as const;

export const POLICY_RULE_CAPABILITY_STATUSES = [
  "active",
  "disabled",
  "retired",
  "missing"
] as const;

export const POLICY_RULE_SOURCE_STATUSES = [
  "active",
  "disabled",
  "retired",
  "missing"
] as const;

export const POLICY_RULE_MODEL_TYPES = [
  "llm",
  "embedding",
  "reranker",
  "classifier",
  "vision",
  "audio",
  "other"
] as const;

export const POLICY_RULE_MODEL_PROVIDERS = [
  "openai",
  "mistral",
  "anthropic",
  "local",
  "azure",
  "aws",
  "gcp",
  "other"
] as const;

export const POLICY_RULE_MODEL_PROVIDER_TYPES = [
  "external",
  "local",
  "unknown"
] as const;

export const POLICY_RULE_MODEL_STATUSES = [
  "active",
  "disabled",
  "retired",
  "missing"
] as const;

export const POLICY_RULE_ACCESS_GRANT_STATUSES = [
  "pending_review",
  "active",
  "suspended",
  "revoked",
  "expired",
  "missing"
] as const;

export const POLICY_RULE_DATA_USAGE_REVIEW_STATUSES = [
  "draft",
  "approved",
  "rejected",
  "expired",
  "needs_review",
  "missing"
] as const;

export type PolicyRuleDecision = (typeof POLICY_RULE_DECISIONS)[number];

export type PolicyRecord = {
  id: string;
  name: string;
  description: string | null;
  status: PolicyStatus;
  created_at: string;
  updated_at: string;
};

export type PolicyPayload = {
  name: string;
  description: string | null;
  status: PolicyStatus;
};

export type PolicyRuleRecord = {
  id: string;
  policy_id: string;
  name: string;
  description: string | null;
  condition: string;
  created_at: string;
  updated_at: string;
};

export type PolicyRulePayload = {
  policy_id: string;
  name: string;
  description: string | null;
  condition: string;
};

export type PolicyVersionRecord = {
  id: string;
  policy_id: string;
  source_version_id: string | null;
  version_number: number;
  status: PolicyVersionStatus;
  change_summary: string;
  policy_snapshot: Record<string, unknown>;
  rule_snapshots: Array<Record<string, unknown>>;
  check_step_snapshots: Array<Record<string, unknown>>;
  created_by_actor_type: string;
  created_by_actor_id: string;
  review_requested_by_actor_type: string | null;
  review_requested_by_actor_id: string | null;
  reviewed_by_actor_type: string | null;
  reviewed_by_actor_id: string | null;
  review_note: string | null;
  created_at: string;
  updated_at: string;
  submitted_at: string | null;
  approved_at: string | null;
  rejected_at: string | null;
  activated_at: string | null;
  superseded_at: string | null;
  archived_at: string | null;
};

export type PolicyVersionDraftPolicySnapshotPayload = {
  name: string;
  description: string | null;
  status: PolicyStatus;
};

export type PolicyVersionDraftRuleSnapshotPayload = {
  id?: string;
  name: string;
  description: string | null;
  condition: string;
};

export type PolicyVersionDraftPayload = {
  change_summary: string;
  policy_snapshot?: PolicyVersionDraftPolicySnapshotPayload;
  rule_snapshots: PolicyVersionDraftRuleSnapshotPayload[];
  check_step_snapshots?: Array<Record<string, unknown>>;
};

export async function fetchPolicies(
  signal?: AbortSignal
): Promise<PolicyRecord[]> {
  return fetchApiArray<PolicyRecord>("/policies", {
    errorLabel: "GET /policies",
    signal
  });
}

export async function fetchPolicy(
  policyId: string,
  signal?: AbortSignal
): Promise<PolicyRecord> {
  return fetchApiJson<PolicyRecord>(
    `/policies/${encodeURIComponent(policyId)}`,
    {
      errorLabel: "GET /policies/{policy_id}",
      signal
    }
  );
}

export async function createPolicy(
  payload: PolicyPayload,
  signal?: AbortSignal
): Promise<PolicyRecord> {
  return postApiJson<PolicyRecord>("/policies", {
    body: payload,
    errorLabel: "POST /policies",
    signal
  });
}

export async function updatePolicy(
  policyId: string,
  payload: Partial<PolicyPayload>,
  signal?: AbortSignal
): Promise<PolicyRecord> {
  return patchApiJson<PolicyRecord>(`/policies/${encodeURIComponent(policyId)}`, {
    body: payload,
    errorLabel: "PATCH /policies/{policy_id}",
    signal
  });
}

export async function fetchPolicyRulesForPolicy(
  policyId: string,
  signal?: AbortSignal
): Promise<PolicyRuleRecord[]> {
  return fetchApiArray<PolicyRuleRecord>(
    `/policies/${encodeURIComponent(policyId)}/rules`,
    {
      errorLabel: "GET /policies/{policy_id}/rules",
      signal
    }
  );
}

export async function fetchPolicyVersionsForPolicy(
  policyId: string,
  signal?: AbortSignal
): Promise<PolicyVersionRecord[]> {
  return fetchApiArray<PolicyVersionRecord>(
    `/policies/${encodeURIComponent(policyId)}/versions`,
    {
      errorLabel: "GET /policies/{policy_id}/versions",
      signal
    }
  );
}

export async function createPolicyVersionDraft(
  policyId: string,
  payload: PolicyVersionDraftPayload,
  signal?: AbortSignal
): Promise<PolicyVersionRecord> {
  return postApiJson<PolicyVersionRecord>(
    `/policies/${encodeURIComponent(policyId)}/versions/draft`,
    {
      body: payload,
      errorLabel: "POST /policies/{policy_id}/versions/draft",
      signal
    }
  );
}

export async function updatePolicyVersionDraft(
  policyVersionId: string,
  payload: PolicyVersionDraftPayload,
  signal?: AbortSignal
): Promise<PolicyVersionRecord> {
  return patchApiJson<PolicyVersionRecord>(
    `/policy-versions/${encodeURIComponent(policyVersionId)}/draft`,
    {
      body: payload,
      errorLabel: "PATCH /policy-versions/{policy_version_id}/draft",
      signal
    }
  );
}

export async function createPolicyRule(
  payload: PolicyRulePayload,
  signal?: AbortSignal
): Promise<PolicyRuleRecord> {
  return postApiJson<PolicyRuleRecord>("/policy-rules", {
    body: payload,
    errorLabel: "POST /policy-rules",
    signal
  });
}

export async function updatePolicyRule(
  ruleId: string,
  payload: Partial<PolicyRulePayload>,
  signal?: AbortSignal
): Promise<PolicyRuleRecord> {
  return patchApiJson<PolicyRuleRecord>(
    `/policy-rules/${encodeURIComponent(ruleId)}`,
    {
      body: payload,
      errorLabel: "PATCH /policy-rules/{rule_id}",
      signal
    }
  );
}
