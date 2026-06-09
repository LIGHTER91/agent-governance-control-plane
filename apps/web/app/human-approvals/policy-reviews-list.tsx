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
  PolicyVersionReviewRequestRecord,
  activatePolicyVersionReviewRequest,
  decidePolicyVersionReviewRequest,
  fetchPolicyVersionReviewRequests
} from "../lib/policies";

type PolicyReviewsState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; requests: PolicyVersionReviewRequestRecord[] };

type ActionState = {
  id: string | null;
  status: "idle" | "submitting" | "success" | "error";
  message: string;
};

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
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

function statusTone(status: string) {
  if (status === "approved") {
    return "ok";
  }
  if (status === "pending") {
    return "warn";
  }
  if (status === "rejected" || status === "canceled") {
    return "danger";
  }
  return "info";
}

export function PolicyReviewsList() {
  const [state, setState] = useState<PolicyReviewsState>({ status: "loading" });
  const [notesById, setNotesById] = useState<Record<string, string>>({});
  const [replaceActiveById, setReplaceActiveById] = useState<
    Record<string, boolean>
  >({});
  const [actionState, setActionState] = useState<ActionState>({
    id: null,
    status: "idle",
    message: "No policy review action submitted"
  });

  const loadPolicyReviews = useCallback(async (signal?: AbortSignal) => {
    setState({ status: "loading" });

    try {
      const [pendingRequests, approvedRequests] = await Promise.all([
        fetchPolicyVersionReviewRequests("pending", signal),
        fetchPolicyVersionReviewRequests("approved", signal)
      ]);
      const requests = [...pendingRequests, ...approvedRequests].sort((left, right) =>
        right.created_at.localeCompare(left.created_at)
      );
      setState({ status: "ready", requests });
    } catch (error: unknown) {
      if (signal?.aborted) {
        return;
      }

      setState({
        status: "error",
        message:
          error instanceof Error
            ? error.message
            : "Unable to load PolicyVersion review requests from the backend."
      });
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    void loadPolicyReviews(controller.signal);
    return () => controller.abort();
  }, [loadPolicyReviews]);

  async function handleDecision(
    request: PolicyVersionReviewRequestRecord,
    action: "approve" | "reject"
  ) {
    setActionState({
      id: request.id,
      status: "submitting",
      message: `${formatValue(action)} review request`
    });

    try {
      await decidePolicyVersionReviewRequest(request.id, action, {
        decision_note: notesById[request.id]?.trim() || null
      });
      setActionState({
        id: request.id,
        status: "success",
        message: `${formatValue(action)} saved. Review approval does not activate the PolicyVersion.`
      });
      setNotesById((current) => ({ ...current, [request.id]: "" }));
      void loadPolicyReviews();
    } catch (error: unknown) {
      setActionState({
        id: request.id,
        status: "error",
        message:
          error instanceof Error
            ? error.message
            : `Unable to ${action} PolicyVersion review request.`
      });
    }
  }

  async function handleActivate(request: PolicyVersionReviewRequestRecord) {
    setActionState({
      id: request.id,
      status: "submitting",
      message: "Activating approved PolicyVersion review request"
    });

    try {
      await activatePolicyVersionReviewRequest(request.id, {
        replace_active: Boolean(replaceActiveById[request.id])
      });
      setActionState({
        id: request.id,
        status: "success",
        message:
          "Activate approved version saved. Activation changes runtime policy evaluation."
      });
      setReplaceActiveById((current) => ({ ...current, [request.id]: false }));
      void loadPolicyReviews();
    } catch (error: unknown) {
      setActionState({
        id: request.id,
        status: "error",
        message:
          error instanceof Error
            ? error.message
            : "Unable to activate approved PolicyVersion review request."
      });
    }
  }

  return (
    <AGCPPanel aria-label="Policy reviews">
      <AGCPSectionHeader
        eyebrow="policy review queue"
        title="Policy Reviews"
        description="Pending and approved PolicyVersion review requests from GET /policy-version-review-requests. Approval does not activate automatically; Activate approved version is the explicit runtime-changing step."
        meta={
          state.status === "ready" ? (
            <AGCPBadge tone="purple">{state.requests.length} open</AGCPBadge>
          ) : null
        }
      />

      {state.status === "loading" ? (
        <AGCPEmptyState title="Loading Policy Reviews">
          Requesting pending PolicyVersion review requests from {getApiBaseUrl()}.
        </AGCPEmptyState>
      ) : null}

      {state.status === "error" ? (
        <AGCPErrorState title="Unable to load Policy Reviews">
          {state.message} Check that the backend is running and the current
          actor can read PolicyVersion review requests.
        </AGCPErrorState>
      ) : null}

      {state.status === "ready" && state.requests.length === 0 ? (
        <AGCPEmptyState title="No open Policy Reviews">
          Draft PolicyVersion review requests will appear here after Policy
          Studio users submit saved drafts for review. Approved requests waiting
          for explicit activation also remain visible here.
        </AGCPEmptyState>
      ) : null}

      {state.status === "ready" && state.requests.length > 0 ? (
        <div className="agcp-review-list">
          {state.requests.map((request) => (
            <article className="agcp-review-card" key={request.id}>
              <div className="agcp-review-head">
                <div>
                  <div className="agcp-review-title">
                    {request.policy_name || "Policy"} v
                    {request.policy_version_number || "?"}
                  </div>
                  <div className="agcp-review-meta">
                    <span>policy {request.policy_id}</span>
                    <span>version {request.policy_version_id}</span>
                    <span>created {formatTimestamp(request.created_at)}</span>
                  </div>
                </div>
                <AGCPBadge tone={statusTone(request.status)}>
                  {formatValue(request.status)}
                </AGCPBadge>
              </div>

              <p className="agcp-muted">
                {request.request_note ||
                  "No request note was persisted with this PolicyVersion review request."}
              </p>

              <dl className="agcp-approval-details">
                <div>
                  <dt>Requested by</dt>
                  <dd>
                    {formatValue(request.requested_by_actor_type)} /{" "}
                    {request.requested_by_actor_id}
                  </dd>
                </div>
                <div>
                  <dt>Review status</dt>
                  <dd>{formatValue(request.status)}</dd>
                </div>
                <div>
                  <dt>Runtime impact</dt>
                  <dd>
                    {request.status === "approved"
                      ? "Activation changes runtime policy evaluation"
                      : "None until explicit PolicyVersion activation"}
                  </dd>
                </div>
              </dl>

              {request.status === "pending" ? (
                <div className="approval-actions">
                  <label className="approval-note">
                    <span>Decision note</span>
                    <textarea
                      disabled={actionState.status === "submitting"}
                      onChange={(event) =>
                        setNotesById((current) => ({
                          ...current,
                          [request.id]: event.target.value
                        }))
                      }
                      placeholder="Optional review decision note"
                      value={notesById[request.id] || ""}
                    />
                  </label>
                  <div className="approval-action-buttons">
                    <button
                      className="table-action-button approve"
                      disabled={actionState.status === "submitting"}
                      onClick={() => void handleDecision(request, "approve")}
                      type="button"
                    >
                      Approve
                    </button>
                    <button
                      className="table-action-button reject"
                      disabled={actionState.status === "submitting"}
                      onClick={() => void handleDecision(request, "reject")}
                      type="button"
                    >
                      Reject
                    </button>
                  </div>
                  {actionState.id === request.id &&
                  actionState.status !== "idle" ? (
                    <p className="review-action-message">{actionState.message}</p>
                  ) : null}
                </div>
              ) : null}

              {request.status === "approved" ? (
                <div className="approval-actions">
                  <label className="approval-note checkbox">
                    <input
                      checked={Boolean(replaceActiveById[request.id])}
                      disabled={actionState.status === "submitting"}
                      onChange={(event) =>
                        setReplaceActiveById((current) => ({
                          ...current,
                          [request.id]: event.target.checked
                        }))
                      }
                      type="checkbox"
                    />
                    <span>
                      This will replace the current active version if one exists.
                    </span>
                  </label>
                  <div className="approval-action-buttons">
                    <button
                      className="table-action-button approve"
                      disabled={actionState.status === "submitting"}
                      onClick={() => void handleActivate(request)}
                      type="button"
                    >
                      Activate approved version
                    </button>
                  </div>
                  <p className="agcp-muted">
                    Approval does not activate automatically. Activation changes
                    runtime policy evaluation for future Runtime Gateway and
                    telemetry decisions.
                  </p>
                  {actionState.id === request.id &&
                  actionState.status !== "idle" ? (
                    <p className="review-action-message">{actionState.message}</p>
                  ) : null}
                </div>
              ) : null}
            </article>
          ))}
        </div>
      ) : null}
    </AGCPPanel>
  );
}
