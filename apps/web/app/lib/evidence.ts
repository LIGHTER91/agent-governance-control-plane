import { fetchApiJson } from "./api";

export type EvidenceMetadataValue = string | number | boolean | null;
export type EvidenceMetadata = Record<string, EvidenceMetadataValue>;

export type EvidenceAgent = {
  id: string;
  name: string;
  description: string | null;
  owner_type: string;
  owner_id: string;
  owner_name: string;
  owner_contact_email: string | null;
  environment: string;
  status: string;
  risk_level: string;
  framework: string | null;
  created_at: string;
  updated_at: string;
};

export type EvidenceAuditLog = {
  id: string;
  event_type: string;
  actor_type: string;
  actor_id: string;
  entity_type: string;
  entity_id: string;
  summary: string;
  metadata: EvidenceMetadata;
  created_at: string;
};

export type EvidenceAgentRun = {
  id: string;
  agent_id: string;
  run_id: string;
  correlation_id: string;
  environment: string;
  status: string;
  started_at: string;
  ended_at: string | null;
  summary: string | null;
  metadata: EvidenceMetadata;
  created_at: string;
};

export type EvidenceTraceEvent = {
  id: string;
  agent_id: string;
  run_id: string;
  external_event_id: string;
  correlation_id: string;
  event_type: string;
  timestamp: string;
  summary: string;
  metadata: EvidenceMetadata;
  created_at: string;
};

export type EvidencePolicyReference = {
  id: string;
  name: string;
  status: string;
};

export type EvidencePolicyRuleReference = {
  id: string;
  policy_id: string;
  name: string;
};

export type EvidencePolicyVersionReference = {
  policy_version_id: string;
  policy_id: string;
  version_number: number;
  status: string;
  activated_at: string | null;
  change_summary: string | null;
};

export type EvidencePolicyDecision = {
  id: string;
  agent_id: string | null;
  policy_id: string | null;
  policy_version_id: string | null;
  rule_id: string | null;
  trace_event_id: string | null;
  decision: string;
  reason: string;
  context_hash: string | null;
  policy: EvidencePolicyReference | null;
  rule: EvidencePolicyRuleReference | null;
  policy_version: EvidencePolicyVersionReference | null;
  created_at: string;
};

export type EvidenceHumanApproval = {
  id: string;
  agent_id: string;
  policy_decision_id: string | null;
  status: string;
  requested_by_actor_type: string;
  requested_by_actor_id: string;
  reviewed_by_actor_type: string | null;
  reviewed_by_actor_id: string | null;
  reason: string | null;
  decision_note: string | null;
  created_at: string;
  reviewed_at: string | null;
  expires_at: string | null;
};

export type EvidenceAccessGrant = {
  id: string;
  name: string;
  description: string | null;
  grant_type: string;
  subject_type: string;
  subject_id: string;
  target_type: string;
  target_id: string | null;
  external_ref: string | null;
  status: string;
  granted_by_actor_type: string;
  granted_by_actor_id: string;
  reason: string | null;
  expires_at: string | null;
  risk_level: string;
  metadata: EvidenceMetadata;
  created_at: string;
  updated_at: string;
};

export type EvidenceCapabilityReference = {
  id: string;
  name: string;
  description: string | null;
  capability_type: string;
  external_ref: string | null;
  status: string;
  risk_level: string;
  metadata: EvidenceMetadata;
  created_at: string;
  updated_at: string;
};

export type EvidenceSourceReference = {
  id: string;
  name: string;
  description: string | null;
  source_type: string;
  external_ref: string | null;
  owner_type: string;
  owner_id: string;
  owner_name: string;
  owner_contact_email: string | null;
  status: string;
  risk_level: string;
  metadata: EvidenceMetadata;
  created_at: string;
  updated_at: string;
};

export type EvidenceDataUsageProfile = {
  id: string;
  source_id: string;
  data_classification: string;
  contains_personal_data: boolean;
  contains_sensitive_data: boolean;
  data_categories: string[];
  legal_basis: string | null;
  allowed_purposes: string[];
  prohibited_purposes: string[];
  allowed_processing: string[];
  prohibited_processing: string[];
  residency: string | null;
  retention_policy: string | null;
  data_owner: string | null;
  review_status: string;
  reviewed_by_actor_type: string | null;
  reviewed_by_actor_id: string | null;
  reviewed_at: string | null;
  review_expires_at: string | null;
  dpia_required: boolean;
  dpia_reference: string | null;
  metadata: EvidenceMetadata;
  created_at: string;
  updated_at: string;
};

export type EvidenceModelAssetReference = {
  id: string;
  name: string;
  description: string | null;
  model_type: string;
  provider: string;
  model_ref: string | null;
  version: string | null;
  owner_type: string;
  owner_id: string;
  owner_name: string;
  owner_contact_email: string | null;
  status: string;
  risk_level: string;
  metadata: EvidenceMetadata;
  created_at: string;
  updated_at: string;
};

export type EvidenceCheckResult = {
  check_result_id: string;
  check_type: string | null;
  check_tool_id: string;
  check_tool_name: string | null;
  check_tool_type: string | null;
  outcome: string;
  confidence: string | null;
  summary: string;
  reason: string | null;
  target_type: string;
  target_id: string | null;
  policy_decision_id: string | null;
  policy_version_id: string | null;
  policy_version: EvidencePolicyVersionReference | null;
  trace_event_id: string | null;
  run_id: string | null;
  created_at: string;
  metadata: EvidenceMetadata;
};

export type EvidenceBundle = {
  agent: EvidenceAgent;
  audit_logs: EvidenceAuditLog[];
  agent_runs: EvidenceAgentRun[];
  trace_events: EvidenceTraceEvent[];
  policy_decisions: EvidencePolicyDecision[];
  human_approvals: EvidenceHumanApproval[];
  access_grants: EvidenceAccessGrant[];
  capability_references: EvidenceCapabilityReference[];
  source_references: EvidenceSourceReference[];
  data_usage_profiles: EvidenceDataUsageProfile[];
  model_asset_references: EvidenceModelAssetReference[];
  check_results: EvidenceCheckResult[];
};

export function fetchEvidenceBundle(
  agentId: string,
  signal?: AbortSignal
): Promise<EvidenceBundle> {
  return fetchApiJson<EvidenceBundle>(
    `/agents/${encodeURIComponent(agentId)}/evidence-bundle`,
    {
      errorLabel: "GET /agents/{agent_id}/evidence-bundle",
      signal
    }
  );
}
