"use client";

import { useState } from "react";
import { ApiRequestError } from "../lib/api";
import type {
  HumanApprovalAction,
  HumanApprovalRecord
} from "../lib/human-approvals";
import { transitionHumanApproval } from "../lib/human-approvals";

type HumanApprovalActionsProps = {
  approval: HumanApprovalRecord;
  onCompleted: (
    approval: HumanApprovalRecord,
    action: HumanApprovalAction
  ) => Promise<void> | void;
};

type ActionState =
  | { status: "idle" }
  | { status: "loading"; action: HumanApprovalAction }
  | { status: "success"; message: string }
  | { status: "error"; message: string };

export function HumanApprovalActions({
  approval,
  onCompleted
}: HumanApprovalActionsProps) {
  const [decisionNote, setDecisionNote] = useState("");
  const [actionState, setActionState] = useState<ActionState>({
    status: "idle"
  });

  if (approval.status !== "pending") {
    return (
      <span className="approval-action-note">
        Completed HumanApprovals are read-only in this UI.
      </span>
    );
  }

  const loadingAction =
    actionState.status === "loading" ? actionState.action : null;
  const isLoading = loadingAction !== null;

  async function handleAction(action: HumanApprovalAction) {
    setActionState({ status: "loading", action });

    try {
      const updatedApproval = await transitionHumanApproval(
        approval.id,
        action,
        action === "cancel" ? undefined : decisionNote
      );
      await onCompleted(updatedApproval, action);
      setDecisionNote("");
      setActionState({
        status: "success",
        message: `HumanApproval ${actionPastTense(action)}.`
      });
    } catch (error: unknown) {
      setActionState({
        status: "error",
        message: humanApprovalActionError(error)
      });
    }
  }

  return (
    <div className="approval-actions">
      <label className="approval-note">
        <span>Decision note</span>
        <textarea
          value={decisionNote}
          onChange={(event) => setDecisionNote(event.target.value)}
          placeholder="Optional for approve or reject"
          disabled={isLoading}
          rows={2}
        />
      </label>
      <div
        className="approval-action-buttons"
        aria-label="HumanApproval review actions"
      >
        <button
          className="table-action-button approve"
          type="button"
          disabled={isLoading}
          onClick={() => void handleAction("approve")}
        >
          {loadingAction === "approve" ? "Approving" : "Approve"}
        </button>
        <button
          className="table-action-button reject"
          type="button"
          disabled={isLoading}
          onClick={() => void handleAction("reject")}
        >
          {loadingAction === "reject" ? "Rejecting" : "Reject"}
        </button>
        <button
          className="table-action-button cancel"
          type="button"
          disabled={isLoading}
          onClick={() => void handleAction("cancel")}
        >
          {loadingAction === "cancel" ? "Cancelling" : "Cancel"}
        </button>
      </div>
      {actionState.status === "success" ? (
        <p className="approval-action-status success" aria-live="polite">
          {actionState.message}
        </p>
      ) : null}
      {actionState.status === "error" ? (
        <p className="approval-action-status error" role="alert">
          {actionState.message}
        </p>
      ) : null}
    </div>
  );
}

export function actionPastTense(action: HumanApprovalAction) {
  if (action === "approve") {
    return "approved";
  }

  if (action === "reject") {
    return "rejected";
  }

  return "cancelled";
}

function humanApprovalActionError(error: unknown) {
  if (error instanceof ApiRequestError) {
    if (error.status === 403) {
      return "RBAC denied: the current actor is not allowed to perform this HumanApproval action.";
    }

    if (error.status === 404) {
      return "HumanApproval not found. Refresh the list and confirm the record still exists.";
    }

    if (error.status === 400 || error.status === 409 || error.status === 422) {
      return "Invalid transition: this HumanApproval may already be reviewed or is no longer pending.";
    }
  }

  if (error instanceof TypeError) {
    return "Backend unavailable: the HumanApproval action request could not reach the API.";
  }

  return error instanceof Error ? error.message : "Unable to update HumanApproval.";
}
