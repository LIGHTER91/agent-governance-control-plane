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
