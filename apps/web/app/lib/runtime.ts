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
  related_ids?: Record<string, string>;
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
