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

export type EvidencePolicyDecision = {
  id: string;
  agent_id: string | null;
  policy_id: string | null;
  rule_id: string | null;
  trace_event_id: string | null;
  decision: string;
  reason: string;
  context_hash: string | null;
  policy: EvidencePolicyReference | null;
  rule: EvidencePolicyRuleReference | null;
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

export type EvidenceBundle = {
  agent: EvidenceAgent;
  audit_logs: EvidenceAuditLog[];
  agent_runs: EvidenceAgentRun[];
  trace_events: EvidenceTraceEvent[];
  policy_decisions: EvidencePolicyDecision[];
  human_approvals: EvidenceHumanApproval[];
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
