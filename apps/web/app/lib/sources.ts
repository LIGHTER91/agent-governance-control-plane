import { fetchApiArray, fetchApiJson, postApiJson } from "./api";

export type SourceMetadataValue = string | number | boolean | null;
export type SourceMetadata = Record<string, SourceMetadataValue>;

export type SourceRecord = {
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
  metadata: SourceMetadata;
  created_at: string;
  updated_at: string;
};

export type DataUsageProfile = {
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
  metadata: SourceMetadata;
  created_at: string;
  updated_at: string;
};

export type AccessGrantRecord = {
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
  metadata: SourceMetadata;
  created_at: string;
  updated_at: string;
};

export type AccessGrantTransitionAction =
  | "suspend"
  | "revoke"
  | "reactivate"
  | "expire";

export function fetchSources(signal?: AbortSignal): Promise<SourceRecord[]> {
  return fetchApiArray<SourceRecord>("/sources", {
    errorLabel: "GET /sources",
    signal
  });
}

export function fetchSourceUsageProfile(
  sourceId: string,
  signal?: AbortSignal
): Promise<DataUsageProfile> {
  return fetchApiJson<DataUsageProfile>(
    `/sources/${encodeURIComponent(sourceId)}/usage-profile`,
    {
      errorLabel: "GET /sources/{source_id}/usage-profile",
      signal
    }
  );
}

export function fetchAccessGrants(
  signal?: AbortSignal
): Promise<AccessGrantRecord[]> {
  return fetchApiArray<AccessGrantRecord>("/access-grants", {
    errorLabel: "GET /access-grants",
    signal
  });
}

export function transitionAccessGrant(
  accessGrantId: string,
  action: AccessGrantTransitionAction,
  transitionNote?: string,
  signal?: AbortSignal
): Promise<AccessGrantRecord> {
  const trimmedNote = transitionNote?.trim();

  return postApiJson<AccessGrantRecord>(
    `/access-grants/${encodeURIComponent(accessGrantId)}/${action}`,
    {
      body: trimmedNote ? { transition_note: trimmedNote } : {},
      errorLabel: `POST /access-grants/{access_grant_id}/${action}`,
      signal
    }
  );
}
