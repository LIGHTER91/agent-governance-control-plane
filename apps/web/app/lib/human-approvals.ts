import { fetchApiArray, postApiJson } from "./api";
import { EvidenceCheckResult } from "./evidence";

export const HUMAN_APPROVAL_STATUSES = [
  "pending",
  "approved",
  "rejected",
  "cancelled",
  "expired"
] as const;

export type HumanApprovalStatus = (typeof HUMAN_APPROVAL_STATUSES)[number];
export type HumanApprovalStatusFilter = HumanApprovalStatus | "all";

export type HumanApprovalRecord = {
  id: string;
  agent_id: string;
  policy_decision_id: string | null;
  status: HumanApprovalStatus;
  requested_by_actor_type: string;
  requested_by_actor_id: string;
  reviewed_by_actor_type: string | null;
  reviewed_by_actor_id: string | null;
  reason: string | null;
  decision_note: string | null;
  created_at: string;
  reviewed_at: string | null;
  expires_at: string | null;
  check_results: EvidenceCheckResult[];
};

export type HumanApprovalAction = "approve" | "reject" | "cancel";

export async function fetchHumanApprovals(
  status: HumanApprovalStatusFilter,
  signal?: AbortSignal
): Promise<HumanApprovalRecord[]> {
  const searchParams = new URLSearchParams();

  if (status !== "all") {
    searchParams.set("status", status);
  }

  return fetchApiArray<HumanApprovalRecord>("/human-approvals", {
    errorLabel: "GET /human-approvals",
    searchParams,
    signal
  });
}

export async function fetchAgentHumanApprovals(
  agentId: string,
  signal?: AbortSignal
): Promise<HumanApprovalRecord[]> {
  return fetchApiArray<HumanApprovalRecord>(
    `/agents/${encodeURIComponent(agentId)}/human-approvals`,
    {
      errorLabel: "GET /agents/{agent_id}/human-approvals",
      signal
    }
  );
}

export async function transitionHumanApproval(
  approvalId: string,
  action: HumanApprovalAction,
  decisionNote?: string,
  signal?: AbortSignal
): Promise<HumanApprovalRecord> {
  const trimmedNote = decisionNote?.trim();
  const body =
    action === "cancel"
      ? undefined
      : trimmedNote
        ? { decision_note: trimmedNote }
        : {};

  return postApiJson<HumanApprovalRecord>(
    `/human-approvals/${encodeURIComponent(approvalId)}/${action}`,
    {
      body,
      errorLabel: `POST /human-approvals/{approval_id}/${action}`,
      signal
    }
  );
}
