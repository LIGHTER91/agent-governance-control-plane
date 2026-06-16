import {
  deleteApi,
  fetchApiArray,
  fetchApiJson,
  patchApiJson,
  postApiJson
} from "./api";

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

export const POLICY_VERSION_REVIEW_REQUEST_STATUSES = [
  "pending",
  "approved",
  "rejected",
  "canceled"
] as const;

export type PolicyVersionReviewRequestStatus =
  (typeof POLICY_VERSION_REVIEW_REQUEST_STATUSES)[number];

export type PolicyVersionReviewStateStatus =
  | "not_submitted"
  | "pending"
  | "approved"
  | "rejected"
  | "canceled";

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

export type PolicyVersionReviewRequestRecord = {
  id: string;
  policy_version_id: string;
  policy_id: string;
  status: PolicyVersionReviewRequestStatus;
  requested_by_actor_type: string;
  requested_by_actor_id: string;
  reviewer_actor_type: string | null;
  reviewer_actor_id: string | null;
  assigned_reviewer_actor_type: string | null;
  assigned_reviewer_actor_id: string | null;
  assigned_reviewer_name: string | null;
  assigned_at: string | null;
  assigned_by_actor_type: string | null;
  assigned_by_actor_id: string | null;
  request_note: string | null;
  decision_note: string | null;
  created_at: string;
  decided_at: string | null;
  policy_name: string | null;
  policy_version_number: number | null;
};

export type PolicyVersionReviewStateRecord = {
  policy_version_id: string;
  latest_review_request_id: string | null;
  review_status: PolicyVersionReviewStateStatus;
  requested_at: string | null;
  decided_at: string | null;
  reviewer_actor_id: string | null;
  can_submit_review: boolean;
  message: string;
};

export type PolicyVersionReviewRequestPayload = {
  request_note?: string | null;
};

export type PolicyVersionReviewDecisionPayload = {
  decision_note?: string | null;
};

export type PolicyVersionReviewAssignmentPayload = {
  assigned_reviewer_actor_type: string;
  assigned_reviewer_actor_id: string;
  assigned_reviewer_name?: string | null;
  assignment_note?: string | null;
};

export type PolicyVersionReviewActivationPayload = {
  replace_active?: boolean;
};

export type PolicyVersionRollbackDraftPayload = {
  change_summary: string;
};

export type PolicyVersionDiffFieldValue = {
  field: string;
  value: unknown;
};

export type PolicyVersionDiffChangedField = {
  field: string;
  baseline: unknown;
  reviewed: unknown;
};

export type PolicyVersionDiffFieldChange = {
  changed: boolean;
  baseline: unknown;
  reviewed: unknown;
};

export type PolicyVersionReviewAuditReference = {
  id: string;
  event_type: string;
  entity_type: string;
  entity_id: string;
  summary: string;
  created_at: string;
  metadata: Record<string, unknown>;
};

export type PolicyVersionReviewDiffRecord = {
  review_request_id: string;
  policy_id: string;
  policy_version_id: string;
  baseline_policy_version_id: string | null;
  baseline_type: "active_version" | "live_fallback" | "none";
  baseline_summary: string;
  reviewed_version_status: PolicyVersionStatus;
  review_status: PolicyVersionReviewRequestStatus;
  can_activate: boolean;
  activation_requires_replace: boolean;
  policy_snapshot_changes: {
    name: PolicyVersionDiffFieldChange;
    description: PolicyVersionDiffFieldChange;
    status: PolicyVersionDiffFieldChange;
  };
  rule_condition_changes: {
    added_fields: PolicyVersionDiffFieldValue[];
    removed_fields: PolicyVersionDiffFieldValue[];
    changed_fields: PolicyVersionDiffChangedField[];
    unchanged_fields_count: number;
  };
  check_step_changes: {
    added_count: number;
    removed_count: number;
    changed_count: number;
    unchanged_count: number;
    changed_fields: string[];
  };
  plain_language_summary: string[];
  runtime_effect_summary: string[];
  evidence: {
    review_status: PolicyVersionReviewRequestStatus;
    review_requested_at: string;
    decided_at: string | null;
    requested_by_actor_type: string;
    requested_by_actor_id: string;
    reviewer_actor_type: string | null;
    reviewer_actor_id: string | null;
    activation_audit_event: PolicyVersionReviewAuditReference | null;
    superseded_audit_event: PolicyVersionReviewAuditReference | null;
    activated_policy_version_id: string | null;
    previous_active_policy_version_id: string | null;
  };
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

export async function archivePolicy(
  policyId: string,
  signal?: AbortSignal
): Promise<PolicyRecord> {
  return postApiJson<PolicyRecord>(
    `/policies/${encodeURIComponent(policyId)}/archive`,
    {
      errorLabel: "POST /policies/{policy_id}/archive",
      signal
    }
  );
}

export async function deletePolicy(
  policyId: string,
  signal?: AbortSignal
): Promise<void> {
  return deleteApi(`/policies/${encodeURIComponent(policyId)}`, {
    errorLabel: "DELETE /policies/{policy_id}",
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

export async function fetchPolicyVersionReviewRequests(
  status: PolicyVersionReviewRequestStatus = "pending",
  signal?: AbortSignal
): Promise<PolicyVersionReviewRequestRecord[]> {
  const searchParams = new URLSearchParams();
  searchParams.set("status", status);

  return fetchApiArray<PolicyVersionReviewRequestRecord>(
    "/policy-version-review-requests",
    {
      errorLabel: "GET /policy-version-review-requests",
      searchParams,
      signal
    }
  );
}

export async function fetchPolicyVersionReviewState(
  policyVersionId: string,
  signal?: AbortSignal
): Promise<PolicyVersionReviewStateRecord> {
  return fetchApiJson<PolicyVersionReviewStateRecord>(
    `/policy-versions/${encodeURIComponent(policyVersionId)}/review-state`,
    {
      errorLabel: "GET /policy-versions/{policy_version_id}/review-state",
      signal
    }
  );
}

export async function createPolicyVersionReviewRequest(
  policyVersionId: string,
  payload: PolicyVersionReviewRequestPayload = {},
  signal?: AbortSignal
): Promise<PolicyVersionReviewRequestRecord> {
  return postApiJson<PolicyVersionReviewRequestRecord>(
    `/policy-versions/${encodeURIComponent(policyVersionId)}/review-requests`,
    {
      body: payload,
      errorLabel: "POST /policy-versions/{policy_version_id}/review-requests",
      signal
    }
  );
}

export async function decidePolicyVersionReviewRequest(
  reviewRequestId: string,
  action: "approve" | "reject",
  payload: PolicyVersionReviewDecisionPayload = {},
  signal?: AbortSignal
): Promise<PolicyVersionReviewRequestRecord> {
  const errorLabel =
    action === "approve"
      ? "POST /policy-version-review-requests/{review_request_id}/approve"
      : "POST /policy-version-review-requests/{review_request_id}/reject";

  return postApiJson<PolicyVersionReviewRequestRecord>(
    `/policy-version-review-requests/${encodeURIComponent(reviewRequestId)}/${action}`,
    {
      body: payload,
      errorLabel,
      signal
    }
  );
}

export async function assignPolicyVersionReviewRequest(
  reviewRequestId: string,
  payload: PolicyVersionReviewAssignmentPayload,
  signal?: AbortSignal
): Promise<PolicyVersionReviewRequestRecord> {
  return postApiJson<PolicyVersionReviewRequestRecord>(
    `/policy-version-review-requests/${encodeURIComponent(reviewRequestId)}/assign`,
    {
      body: payload,
      errorLabel: "POST /policy-version-review-requests/{review_request_id}/assign",
      signal
    }
  );
}

export async function activatePolicyVersionReviewRequest(
  reviewRequestId: string,
  payload: PolicyVersionReviewActivationPayload = {},
  signal?: AbortSignal
): Promise<PolicyVersionRecord> {
  return postApiJson<PolicyVersionRecord>(
    `/policy-version-review-requests/${encodeURIComponent(reviewRequestId)}/activate`,
    {
      body: payload,
      errorLabel: "POST /policy-version-review-requests/{review_request_id}/activate",
      signal
    }
  );
}

export async function fetchPolicyVersionReviewRequestDiff(
  reviewRequestId: string,
  signal?: AbortSignal
): Promise<PolicyVersionReviewDiffRecord> {
  return fetchApiJson<PolicyVersionReviewDiffRecord>(
    `/policy-version-review-requests/${encodeURIComponent(reviewRequestId)}/diff`,
    {
      errorLabel: "GET /policy-version-review-requests/{review_request_id}/diff",
      signal
    }
  );
}

export async function createPolicyVersionRollbackDraft(
  policyVersionId: string,
  payload: PolicyVersionRollbackDraftPayload,
  signal?: AbortSignal
): Promise<PolicyVersionRecord> {
  return postApiJson<PolicyVersionRecord>(
    `/policy-versions/${encodeURIComponent(policyVersionId)}/rollback-draft`,
    {
      body: payload,
      errorLabel: "POST /policy-versions/{policy_version_id}/rollback-draft",
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
