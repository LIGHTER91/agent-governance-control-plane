import { fetchApiArray, fetchApiJson, getApiBaseUrl } from "./api";

export type AgentRecord = {
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

export type AgentActivityMetadataValue = string | number | boolean | null;

export type AgentActivityItem = {
  id: string;
  type: string;
  timestamp: string;
  title: string;
  summary: string | null;
  severity?: "info" | "warning" | "error";
  trace_event_id?: string | null;
  policy_decision_id?: string | null;
  human_approval_id?: string | null;
  audit_log_id?: string | null;
  run_id?: string | null;
  related_ids?: Record<string, string>;
  metadata?: Record<string, AgentActivityMetadataValue>;
};

export type AgentGovernanceProfileOwner = {
  owner_type: string;
  owner_id: string;
  owner_name: string;
  owner_contact_email: string | null;
};

export type AgentGovernanceProfileTargetReference = {
  target_type: string;
  id: string;
  name: string;
  status: string;
  risk_level: string;
  external_ref: string | null;
  inventory_type: string | null;
  provider: string | null;
  version: string | null;
};

export type AgentGovernanceProfileAccessGrant = {
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
  metadata: Record<string, AgentActivityMetadataValue>;
  target: AgentGovernanceProfileTargetReference | null;
  created_at: string;
  updated_at: string;
};

export type AgentGovernanceProfileHumanApproval = {
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

export type AgentGovernanceProfile = {
  agent: AgentRecord;
  owner: AgentGovernanceProfileOwner;
  environment: string;
  status: string;
  risk_level: string;
  recent_activity: {
    limit: number;
    items: AgentActivityItem[];
  };
  human_approvals: {
    total_count: number;
    by_status: Record<string, number>;
    recent: AgentGovernanceProfileHumanApproval[];
  };
  access_grants: AgentGovernanceProfileAccessGrant[];
  policy_summary: {
    policy_decision_count: number;
    referenced_policy_ids: string[];
    referenced_rule_ids: string[];
  };
  evidence_bundle: {
    available: boolean;
    export_path: string;
    export_format: "json";
    access: "allowed" | "restricted";
    contains_full_evidence: boolean;
  };
};

export { getApiBaseUrl };

export async function fetchAgents(signal?: AbortSignal): Promise<AgentRecord[]> {
  return fetchApiArray<AgentRecord>("/agents", {
    errorLabel: "GET /agents",
    signal
  });
}

export async function fetchAgent(
  agentId: string,
  signal?: AbortSignal
): Promise<AgentRecord> {
  return fetchApiJson<AgentRecord>(`/agents/${encodeURIComponent(agentId)}`, {
    errorLabel: "GET /agents/{agent_id}",
    signal
  });
}

export async function fetchAgentActivity(
  agentId: string,
  signal?: AbortSignal
): Promise<AgentActivityItem[]> {
  return fetchApiJson<AgentActivityItem[]>(
    `/agents/${encodeURIComponent(agentId)}/activity`,
    {
      errorLabel: "GET /agents/{agent_id}/activity",
      signal
    }
  );
}

export async function fetchAgentGovernanceProfile(
  agentId: string,
  signal?: AbortSignal
): Promise<AgentGovernanceProfile> {
  return fetchApiJson<AgentGovernanceProfile>(
    `/agents/${encodeURIComponent(agentId)}/governance-profile`,
    {
      errorLabel: "GET /agents/{agent_id}/governance-profile",
      signal
    }
  );
}
