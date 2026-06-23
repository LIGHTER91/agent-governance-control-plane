import { fetchApiArray } from "./api";

export type RuntimeDecisionValue =
  | "allow"
  | "deny"
  | "require_human_review"
  | "not_applicable";

export type RuntimeDecisionMode = "telemetry" | "simulation" | "enforcement";

export type RuntimeToolCallActivityItem = {
  id: string;
  type: "tool_call_decision" | "tool_call_resume";
  agent_id: string;
  run_id: string;
  request_id: string | null;
  timestamp: string;
  tool_name: string | null;
  mode: RuntimeDecisionMode | null;
  decision: RuntimeDecisionValue | null;
  proceed: boolean | null;
  reason: string | null;
  trace_event_id: string;
  policy_decision_id: string | null;
  human_approval_id: string | null;
  human_approval_status?: string | null;
  human_approval_requested_at?: string | null;
  policy_id?: string | null;
  policy_rule_id?: string | null;
  policy_version_id?: string | null;
  policy_version_number?: number | null;
  environment?: string | null;
  action_type?: string | null;
  capability_id?: string | null;
  source_id?: string | null;
  source_ids?: string[] | null;
  model_id?: string | null;
  purpose?: string | null;
  data_classification?: string | null;
  source_data_classification?: string | null;
  check_results?: RuntimeCheckResultSummary[];
  related_ids?: Record<string, string>;
};

export type RuntimeCheckResultSummary = {
  id?: string | null;
  check_type: string;
  outcome: string;
  target_type?: string | null;
  target_id?: string | null;
  confidence?: number | null;
  created_at?: string | null;
  metadata?: Record<string, unknown> | null;
};

export async function fetchRuntimeToolCallActivity(
  signal?: AbortSignal
): Promise<RuntimeToolCallActivityItem[]> {
  return fetchApiArray<RuntimeToolCallActivityItem>(
    "/runtime/tool-calls/activity",
    {
      errorLabel: "GET /runtime/tool-calls/activity",
      signal
    }
  );
}
