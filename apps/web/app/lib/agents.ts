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

const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000";

export function getApiBaseUrl() {
  const configuredUrl = process.env.NEXT_PUBLIC_AGCP_API_BASE_URL;
  return (configuredUrl || DEFAULT_API_BASE_URL).replace(/\/+$/, "");
}

export async function fetchAgents(signal?: AbortSignal): Promise<AgentRecord[]> {
  const response = await fetch(`${getApiBaseUrl()}/agents`, {
    headers: {
      Accept: "application/json"
    },
    signal
  });

  if (!response.ok) {
    throw new Error(`GET /agents failed with status ${response.status}`);
  }

  const data: unknown = await response.json();

  if (!Array.isArray(data)) {
    throw new Error("GET /agents returned an unexpected response shape");
  }

  return data as AgentRecord[];
}
