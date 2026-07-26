import { fetchApiArray } from "./api";

export type PolicyCheckType =
  | "access_grant_status"
  | "data_usage_profile_status"
  | "source_status"
  | "source_classification"
  | "capability_status"
  | "model_asset_status"
  | "model_provider_type";

export type PolicyCheckTargetSelector =
  | "access_grants"
  | "source_ids"
  | "capability_id"
  | "model_id";

export type PolicyCheckFailureBehavior =
  | "record_only"
  | "require_human_review"
  | "fail_closed"
  | "ignore_if_unavailable";

export type PolicyCheckEvidenceRetention =
  | "decision_only"
  | "evidence_bundle"
  | "none";

export type PolicyCheckStatus = "active" | "disabled" | "retired";
export type PolicyCheckExpectedOutcome =
  | "pass"
  | "fail"
  | "unknown"
  | "error"
  | "not_applicable";

export type PolicyCheckMetadataValue = string | number | boolean | null;

export type PolicyCheckStepRecord = {
  id: string;
  policy_rule_id: string;
  check_tool_id: string | null;
  check_type: PolicyCheckType;
  target_selector: PolicyCheckTargetSelector;
  required: boolean;
  failure_behavior: PolicyCheckFailureBehavior;
  min_confidence: number | null;
  status: PolicyCheckStatus;
  evidence_retention: PolicyCheckEvidenceRetention;
  metadata: Record<string, PolicyCheckMetadataValue>;
  created_at?: string;
  updated_at?: string;
};

export function fetchPolicyCheckStepsForRule(
  policyRuleId: string,
  signal?: AbortSignal
): Promise<PolicyCheckStepRecord[]> {
  return fetchApiArray<PolicyCheckStepRecord>(
    `/policy-rules/${encodeURIComponent(policyRuleId)}/check-steps`,
    {
      errorLabel: "GET /policy-rules/{rule_id}/check-steps",
      signal
    }
  );
}
