"use client";

import { useCallback, useEffect, useState } from "react";
import {
  AGCPBadge,
  AGCPEmptyState,
  AGCPErrorState,
  AGCPPanel,
  AGCPSectionHeader
} from "../agcp-studio/primitives";
import { getApiBaseUrl } from "../lib/api";
import {
  HUMAN_APPROVAL_STATUSES,
  fetchHumanApprovals
} from "../lib/human-approvals";
import type {
  HumanApprovalRecord,
  HumanApprovalStatusFilter
} from "../lib/human-approvals";

type HumanApprovalsState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; approvals: HumanApprovalRecord[] };

const columns = [
  "ID",
  "Agent ID",
  "Policy Decision ID",
  "Status",
  "Requester Type",
  "Requester ID",
  "Reviewer Type",
  "Reviewer ID",
  "Created",
  "Reviewed",
  "Expires"
];

function formatValue(value: string | null | undefined) {
  if (!value) {
    return "Not set";
  }

  return value
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function formatTimestamp(value: string | null) {
  if (!value) {
    return "Not set";
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleString();
}

function emptyMessage(statusFilter: HumanApprovalStatusFilter) {
  if (statusFilter === "all") {
    return "No human approvals found";
  }

  return `No ${formatValue(statusFilter).toLowerCase()} human approvals found`;
}

function statusTone(status: string) {
  if (status === "approved") {
    return "ok";
  }

  if (status === "pending") {
    return "warn";
  }

  if (status === "rejected" || status === "cancelled" || status === "expired") {
    return "danger";
  }

  return "info";
}

export function HumanApprovalsList() {
  const [statusFilter, setStatusFilter] =
    useState<HumanApprovalStatusFilter>("all");
  const [state, setState] = useState<HumanApprovalsState>({
    status: "loading"
  });

  const loadHumanApprovals = useCallback(
    async (signal?: AbortSignal) => {
      setState({ status: "loading" });

      try {
        const approvals = await fetchHumanApprovals(statusFilter, signal);
        setState({ status: "ready", approvals });
      } catch (error: unknown) {
        if (signal?.aborted) {
          return;
        }

        const message =
          error instanceof Error
            ? error.message
            : "Unable to load human approvals from the backend.";
        setState({ status: "error", message });
      }
    },
    [statusFilter]
  );

  useEffect(() => {
    const controller = new AbortController();

    void loadHumanApprovals(controller.signal);

    return () => {
      controller.abort();
    };
  }, [loadHumanApprovals]);

  return (
    <AGCPPanel aria-label="Human approvals">
      <AGCPSectionHeader
        eyebrow="review queue"
        title="HumanApproval records"
        description="Live records from GET /human-approvals. This view is styled as a governance review queue and does not inject fake approvals."
        meta={
          state.status === "ready" ? (
            <AGCPBadge tone="purple">{state.approvals.length} visible</AGCPBadge>
          ) : null
        }
      />

      <div className="filter-bar agcp-review-filter">
        <label htmlFor="human-approval-status-filter">
          <span>Status</span>
          <select
            id="human-approval-status-filter"
            value={statusFilter}
            onChange={(event) =>
              setStatusFilter(event.target.value as HumanApprovalStatusFilter)
            }
          >
            <option value="all">All statuses</option>
            {HUMAN_APPROVAL_STATUSES.map((status) => (
              <option key={status} value={status}>
                {formatValue(status)}
              </option>
            ))}
          </select>
        </label>
      </div>

      {state.status === "loading" ? (
        <AGCPEmptyState title="Loading human approvals">
          Requesting HumanApproval records from {getApiBaseUrl()}.
        </AGCPEmptyState>
      ) : null}

      {state.status === "error" ? (
        <AGCPErrorState title="Unable to load human approvals">
          {state.message} Check that the backend is running, the current actor
          can read Human Approvals, and NEXT_PUBLIC_AGCP_API_BASE_URL points to
          the API base URL.
        </AGCPErrorState>
      ) : null}

      {state.status === "ready" && state.approvals.length === 0 ? (
        <AGCPEmptyState title={emptyMessage(statusFilter)}>
          Matching HumanApproval records will appear here after backend
          governance flows request or resolve human review.
        </AGCPEmptyState>
      ) : null}

      {state.status === "ready" && state.approvals.length > 0 ? (
        <div className="agcp-review-list">
          {state.approvals.map((approval) => (
            <article className="agcp-review-card" key={approval.id}>
              <div className="agcp-review-head">
                <div>
                  <div className="agcp-review-title">
                    Approval {approval.id.slice(0, 8)}
                  </div>
                  <div className="agcp-review-meta">
                    <span>agent {approval.agent_id}</span>
                    <span>created {formatTimestamp(approval.created_at)}</span>
                  </div>
                </div>
                <AGCPBadge tone={statusTone(approval.status)}>
                  {formatValue(approval.status)}
                </AGCPBadge>
              </div>

              <p className="agcp-muted">
                {approval.reason ||
                  "No reason was persisted with this HumanApproval record."}
              </p>

              <dl className="agcp-approval-details">
                {columns.map((column) => {
                  const valueByColumn: Record<string, string> = {
                    ID: approval.id,
                    "Agent ID": approval.agent_id,
                    "Policy Decision ID": formatValue(
                      approval.policy_decision_id
                    ),
                    Status: formatValue(approval.status),
                    "Requester Type": formatValue(
                      approval.requested_by_actor_type
                    ),
                    "Requester ID": approval.requested_by_actor_id,
                    "Reviewer Type": formatValue(
                      approval.reviewed_by_actor_type
                    ),
                    "Reviewer ID": formatValue(approval.reviewed_by_actor_id),
                    Created: formatTimestamp(approval.created_at),
                    Reviewed: formatTimestamp(approval.reviewed_at),
                    Expires: formatTimestamp(approval.expires_at)
                  };

                  return (
                    <div key={column}>
                      <dt>{column}</dt>
                      <dd>{valueByColumn[column]}</dd>
                    </div>
                  );
                })}
              </dl>
            </article>
          ))}
        </div>
      ) : null}
    </AGCPPanel>
  );
}
