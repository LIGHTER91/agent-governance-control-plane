"use client";

import { useCallback, useEffect, useState } from "react";
import { getApiBaseUrl } from "../lib/api";
import {
  HumanApprovalActions,
  actionPastTense
} from "./human-approval-actions";
import {
  HUMAN_APPROVAL_STATUSES,
  fetchHumanApprovals
} from "../lib/human-approvals";
import type {
  HumanApprovalAction,
  HumanApprovalRecord,
  HumanApprovalStatusFilter
} from "../lib/human-approvals";

type HumanApprovalsState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; approvals: HumanApprovalRecord[] };

type ReviewActionMessage =
  | { status: "success"; message: string }
  | { status: "error"; message: string }
  | null;

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
  "Expires",
  "Actions"
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

export function HumanApprovalsList() {
  const [statusFilter, setStatusFilter] =
    useState<HumanApprovalStatusFilter>("all");
  const [state, setState] = useState<HumanApprovalsState>({
    status: "loading"
  });
  const [reviewActionMessage, setReviewActionMessage] =
    useState<ReviewActionMessage>(null);

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

  async function handleActionCompleted(
    approval: HumanApprovalRecord,
    action: HumanApprovalAction
  ) {
    setReviewActionMessage({
      status: "success",
      message: `HumanApproval ${approval.id} ${actionPastTense(
        action
      )}. Refreshing the review queue.`
    });
    await loadHumanApprovals();
  }

  return (
    <section className="data-panel" aria-label="Human approvals">
      <div className="filter-bar">
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

      {reviewActionMessage ? (
        <div
          className={`review-action-message ${reviewActionMessage.status}`}
          role={reviewActionMessage.status === "error" ? "alert" : undefined}
        >
          {reviewActionMessage.message}
        </div>
      ) : null}

      {state.status === "loading" ? (
        <div className="state-message" aria-live="polite">
          <strong>Loading human approvals</strong>
          <p>Requesting HumanApproval records from {getApiBaseUrl()}.</p>
        </div>
      ) : null}

      {state.status === "error" ? (
        <div className="state-message error" role="alert">
          <strong>Unable to load human approvals</strong>
          <p>{state.message}</p>
          <p>
            Check that the backend is running, the current actor can read Human
            Approvals, and NEXT_PUBLIC_AGCP_API_BASE_URL points to the API base
            URL.
          </p>
        </div>
      ) : null}

      {state.status === "ready" && state.approvals.length === 0 ? (
        <div className="state-message">
          <strong>{emptyMessage(statusFilter)}</strong>
          <p>
            Matching HumanApproval records will appear here after backend
            governance flows request or resolve human review.
          </p>
        </div>
      ) : null}

      {state.status === "ready" && state.approvals.length > 0 ? (
        <div className="table-scroll">
          <table className="data-table human-approvals-table">
            <thead>
              <tr>
                {columns.map((column) => (
                  <th key={column} scope="col">
                    {column}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {state.approvals.map((approval) => (
                <tr key={approval.id}>
                  <td className="id-cell">{approval.id}</td>
                  <td className="id-cell">{approval.agent_id}</td>
                  <td className="id-cell">
                    {formatValue(approval.policy_decision_id)}
                  </td>
                  <td>
                    <span className={`table-pill approval-${approval.status}`}>
                      {formatValue(approval.status)}
                    </span>
                  </td>
                  <td>{formatValue(approval.requested_by_actor_type)}</td>
                  <td className="id-cell">{approval.requested_by_actor_id}</td>
                  <td>{formatValue(approval.reviewed_by_actor_type)}</td>
                  <td className="id-cell">
                    {formatValue(approval.reviewed_by_actor_id)}
                  </td>
                  <td>{formatTimestamp(approval.created_at)}</td>
                  <td>{formatTimestamp(approval.reviewed_at)}</td>
                  <td>{formatTimestamp(approval.expires_at)}</td>
                  <td>
                    <HumanApprovalActions
                      approval={approval}
                      onCompleted={handleActionCompleted}
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </section>
  );
}
