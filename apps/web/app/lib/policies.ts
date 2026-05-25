import { fetchApiArray, fetchApiJson, patchApiJson, postApiJson } from "./api";

export const POLICY_STATUSES = [
  "draft",
  "active",
  "disabled",
  "archived"
] as const;

export type PolicyStatus = (typeof POLICY_STATUSES)[number];

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
