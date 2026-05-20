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
