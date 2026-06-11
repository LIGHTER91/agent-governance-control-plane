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
  CurrentActorRecord,
  fetchCurrentActor
} from "../lib/current-actor";
import {
  PolicyVersionReviewDiffRecord,
  PolicyVersionReviewRequestRecord,
  activatePolicyVersionReviewRequest,
  assignPolicyVersionReviewRequest,
  createPolicyVersionRollbackDraft,
  decidePolicyVersionReviewRequest,
  fetchPolicyVersionReviewRequestDiff,
  fetchPolicyVersionReviewRequests
} from "../lib/policies";

type PolicyReviewsState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; requests: PolicyVersionReviewRequestRecord[] };

type CurrentActorState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; actor: CurrentActorRecord };

type ActionState = {
  id: string | null;
  status: "idle" | "submitting" | "success" | "error";
  message: string;
};

type AssignmentDraft = {
  actorType: string;
  actorId: string;
  name: string;
  note: string;
};

type DiffState =
  | { status: "loading" }
  | { status: "ready"; diff: PolicyVersionReviewDiffRecord }
  | { status: "error"; message: string };

const REVIEWER_ACTOR_TYPES = ["user", "development"] as const;
const REVIEWER_ROLES = ["reviewer", "platform_admin"] as const;

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
  const [actorState, setActorState] = useState<CurrentActorState>({
    status: "loading"
  });
  const [notesById, setNotesById] = useState<Record<string, string>>({});
  const [assignmentDraftsById, setAssignmentDraftsById] = useState<
    Record<string, AssignmentDraft>
  >({});
  const [replaceActiveById, setReplaceActiveById] = useState<
    Record<string, boolean>
  >({});
  const [diffsById, setDiffsById] = useState<Record<string, DiffState>>({});
  const [actionState, setActionState] = useState<ActionState>({
    id: null,
    status: "idle",
    message: "No policy review action submitted"
  });
  const [rollbackState, setRollbackState] = useState<ActionState>({
    id: null,
    status: "idle",
    message: "No rollback draft action submitted"
  });
  const [assignmentState, setAssignmentState] = useState<ActionState>({
    id: null,
    status: "idle",
    message: "No reviewer assignment submitted"
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
      setDiffsById(
        Object.fromEntries(
          requests.map((request) => [request.id, { status: "loading" }])
        )
      );
      const diffEntries = await Promise.all(
        requests.map(async (request) => {
          try {
            const diff = await fetchPolicyVersionReviewRequestDiff(
              request.id,
              signal
            );
            return [request.id, { status: "ready", diff }] as const;
          } catch (error: unknown) {
            if (signal?.aborted) {
              return null;
            }

            return [
              request.id,
              {
                status: "error",
                message:
                  error instanceof Error
                    ? error.message
                    : "Unable to load Policy review diff."
              }
            ] as const;
          }
        })
      );
      if (!signal?.aborted) {
        setDiffsById(
          Object.fromEntries(diffEntries.filter((entry) => entry !== null))
        );
      }
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

  const loadCurrentActor = useCallback(async (signal?: AbortSignal) => {
    setActorState({ status: "loading" });

    try {
      const actor = await fetchCurrentActor(signal);
      setActorState({ status: "ready", actor });
    } catch (error: unknown) {
      if (signal?.aborted) {
        return;
      }

      setActorState({
        status: "error",
        message:
          error instanceof Error
            ? error.message
            : "Unable to load current actor from the backend."
      });
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    void loadPolicyReviews(controller.signal);
    void loadCurrentActor(controller.signal);
    return () => controller.abort();
  }, [loadCurrentActor, loadPolicyReviews]);

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

  async function handleAssign(request: PolicyVersionReviewRequestRecord) {
    const draft = assignmentDraftsById[request.id] || emptyAssignmentDraft();
    const actorId = draft.actorId.trim();
    if (!actorId) {
      setAssignmentState({
        id: request.id,
        status: "error",
        message: "Reviewer actor id is required."
      });
      return;
    }

    setAssignmentState({
      id: request.id,
      status: "submitting",
      message: "Assigning reviewer"
    });

    try {
      await assignPolicyVersionReviewRequest(request.id, {
        assigned_reviewer_actor_type: draft.actorType,
        assigned_reviewer_actor_id: actorId,
        assigned_reviewer_name: draft.name.trim() || null,
        assignment_note: draft.note.trim() || null
      });
      setAssignmentState({
        id: request.id,
        status: "success",
        message:
          "Reviewer assigned. Assignment does not approve the review."
      });
      setAssignmentDraftsById((current) => ({
        ...current,
        [request.id]: emptyAssignmentDraft()
      }));
      void loadPolicyReviews();
    } catch (error: unknown) {
      setAssignmentState({
        id: request.id,
        status: "error",
        message:
          error instanceof Error
            ? error.message
            : "Unable to assign PolicyVersion reviewer."
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
          "Activate approved version saved. Activation changes future runtime policy evaluation."
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

  async function handleCreateRollbackDraft(
    request: PolicyVersionReviewRequestRecord,
    sourcePolicyVersionId: string
  ) {
    setRollbackState({
      id: request.id,
      status: "submitting",
      message: "Creating rollback draft"
    });

    try {
      const draft = await createPolicyVersionRollbackDraft(sourcePolicyVersionId, {
        change_summary: `Rollback draft copied from PolicyVersion ${sourcePolicyVersionId}.`
      });
      setRollbackState({
        id: request.id,
        status: "success",
        message: `Rollback draft v${draft.version_number} created. Submit for review required before activation.`
      });
      void loadPolicyReviews();
    } catch (error: unknown) {
      setRollbackState({
        id: request.id,
        status: "error",
        message:
          error instanceof Error
            ? error.message
            : "Unable to create rollback draft."
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

      <CurrentActorSummary actorState={actorState} />

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
          {state.requests.map((request) => {
            const decisionAccess = policyReviewDecisionAccess(
              request,
              actorState
            );
            const assignmentAccess = policyReviewRoleAccess(actorState);
            const activateAccess = policyReviewRoleAccess(actorState);
            const decisionDisabled =
              actionState.status === "submitting" || !decisionAccess.allowed;
            const assignmentDisabled =
              assignmentState.status === "submitting" ||
              !assignmentAccess.allowed;
            const activateDisabled =
              actionState.status === "submitting" || !activateAccess.allowed;

            return (
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
                <div>
                  <dt>Assigned reviewer</dt>
                  <dd>{assignedReviewerLabel(request)}</dd>
                </div>
              </dl>

              <div className="policy-review-assignment-box">
                <div>
                  <strong>Assigned reviewer</strong>
                  <p>
                    {request.assigned_reviewer_actor_id
                      ? `Assigned to ${assignedReviewerLabel(request)}`
                      : "Unassigned"}
                  </p>
                  <p>Assignment does not approve the review.</p>
                  <p>Assigned reviewer must still approve or reject.</p>
                </div>
                {request.status === "pending" ? (
                  <div className="policy-review-assignment-form">
                    <label className="approval-note">
                      <span>Reviewer actor type</span>
                      <select
                        disabled={assignmentDisabled}
                        onChange={(event) =>
                          setAssignmentDraftsById((current) => ({
                            ...current,
                            [request.id]: {
                              ...(current[request.id] || emptyAssignmentDraft()),
                              actorType: event.target.value
                            }
                          }))
                        }
                        value={
                          assignmentDraftsById[request.id]?.actorType ||
                          emptyAssignmentDraft().actorType
                        }
                      >
                        {REVIEWER_ACTOR_TYPES.map((actorType) => (
                          <option key={actorType} value={actorType}>
                            {formatValue(actorType)}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label className="approval-note">
                      <span>Reviewer actor id</span>
                      <input
                        disabled={assignmentDisabled}
                        onChange={(event) =>
                          setAssignmentDraftsById((current) => ({
                            ...current,
                            [request.id]: {
                              ...(current[request.id] || emptyAssignmentDraft()),
                              actorId: event.target.value
                            }
                          }))
                        }
                        placeholder="user:reviewer-1"
                        value={assignmentDraftsById[request.id]?.actorId || ""}
                      />
                    </label>
                    <label className="approval-note">
                      <span>Display name optional</span>
                      <input
                        disabled={assignmentDisabled}
                        onChange={(event) =>
                          setAssignmentDraftsById((current) => ({
                            ...current,
                            [request.id]: {
                              ...(current[request.id] || emptyAssignmentDraft()),
                              name: event.target.value
                            }
                          }))
                        }
                        placeholder="Reviewer One"
                        value={assignmentDraftsById[request.id]?.name || ""}
                      />
                    </label>
                    <label className="approval-note">
                      <span>Assignment note optional</span>
                      <textarea
                        disabled={assignmentDisabled}
                        onChange={(event) =>
                          setAssignmentDraftsById((current) => ({
                            ...current,
                            [request.id]: {
                              ...(current[request.id] || emptyAssignmentDraft()),
                              note: event.target.value
                            }
                          }))
                        }
                        placeholder="Context for this reviewer assignment"
                        value={assignmentDraftsById[request.id]?.note || ""}
                      />
                    </label>
                    <button
                      className="table-action-button"
                      disabled={assignmentDisabled}
                      onClick={() => void handleAssign(request)}
                      type="button"
                    >
                      {assignmentState.id === request.id &&
                      assignmentState.status === "submitting"
                        ? "Assigning reviewer"
                        : "Assign reviewer"}
                    </button>
                    {!assignmentAccess.allowed ? (
                      <p className="policy-review-disabled-reason">
                        {assignmentAccess.reason}
                      </p>
                    ) : (
                      <p className="policy-review-disabled-reason">
                        Backend authorization still enforced. No fake user directory is provided; enter a stable actor id.
                      </p>
                    )}
                    {assignmentState.id === request.id &&
                    assignmentState.status !== "idle" ? (
                      <p
                        className={`review-action-message ${assignmentState.status}`}
                      >
                        {assignmentState.message}
                      </p>
                    ) : null}
                  </div>
                ) : null}
              </div>

              <PolicyReviewDiffSummary
                diffState={diffsById[request.id]}
                onCreateRollbackDraft={(sourcePolicyVersionId) =>
                  void handleCreateRollbackDraft(request, sourcePolicyVersionId)
                }
                rollbackState={
                  rollbackState.id === request.id ? rollbackState : undefined
                }
              />

              {request.status === "pending" ? (
                <div className="approval-actions">
                  <label className="approval-note">
                    <span>Decision note</span>
                    <textarea
                      disabled={decisionDisabled}
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
                      disabled={decisionDisabled}
                      onClick={() => void handleDecision(request, "approve")}
                      type="button"
                    >
                      Approve
                    </button>
                    <button
                      className="table-action-button reject"
                      disabled={decisionDisabled}
                      onClick={() => void handleDecision(request, "reject")}
                      type="button"
                    >
                      Reject
                    </button>
                  </div>
                  <p className="agcp-muted">
                    Backend assignment rules are enforced on approve/reject:
                    assigned reviews can be decided by the assigned reviewer or
                    platform_admin.
                  </p>
                  {!decisionAccess.allowed ? (
                    <p className="policy-review-disabled-reason">
                      {decisionAccess.reason}
                    </p>
                  ) : null}
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
                      disabled={activateDisabled}
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
                      disabled={activateDisabled}
                      onClick={() => void handleActivate(request)}
                      type="button"
                    >
                      Activate approved version
                    </button>
                  </div>
                  <p className="agcp-muted">
                    Approval does not activate automatically. Activation changes
                    future runtime policy evaluation for Runtime Gateway and
                    telemetry decisions.
                  </p>
                  {!activateAccess.allowed ? (
                    <p className="policy-review-disabled-reason">
                      {activateAccess.reason}
                    </p>
                  ) : null}
                  {actionState.id === request.id &&
                  actionState.status !== "idle" ? (
                    <p className="review-action-message">{actionState.message}</p>
                  ) : null}
                </div>
              ) : null}
            </article>
            );
          })}
        </div>
      ) : null}
    </AGCPPanel>
  );
}

function emptyAssignmentDraft(): AssignmentDraft {
  return {
    actorType: "user",
    actorId: "",
    name: "",
    note: ""
  };
}

function assignedReviewerLabel(request: PolicyVersionReviewRequestRecord) {
  if (!request.assigned_reviewer_actor_id) {
    return "Unassigned";
  }
  if (request.assigned_reviewer_name) {
    return `${request.assigned_reviewer_name} (${formatValue(
      request.assigned_reviewer_actor_type
    )} / ${request.assigned_reviewer_actor_id})`;
  }
  return `${formatValue(request.assigned_reviewer_actor_type)} / ${
    request.assigned_reviewer_actor_id
  }`;
}

function CurrentActorSummary({
  actorState
}: {
  actorState: CurrentActorState;
}) {
  if (actorState.status === "loading") {
    return (
      <div className="policy-review-actor-bar">
        <strong>Current actor</strong>
        <span>Loading current actor from GET /me</span>
        <AGCPBadge tone="muted">Backend authorization still enforced</AGCPBadge>
      </div>
    );
  }

  if (actorState.status === "error") {
    return (
      <div className="policy-review-actor-bar warning">
        <strong>Current actor</strong>
        <span>{actorState.message}</span>
        <AGCPBadge tone="warn">Backend authorization still enforced</AGCPBadge>
      </div>
    );
  }

  const actor = actorState.actor;
  const rolesLabel = actor.roles.length > 0 ? actor.roles.join(", ") : "No roles";

  return (
    <div className="policy-review-actor-bar">
      <strong>Current actor</strong>
      <span>
        {formatValue(actor.actor_type)} / {actor.actor_id}
      </span>
      <AGCPBadge tone={canReviewPolicies(actor) ? "ok" : "warn"}>
        {rolesLabel}
      </AGCPBadge>
      <span>
        {actor.dev_mode_caveat ||
          "Frontend role-aware behavior is advisory; backend authorization still enforced."}
      </span>
    </div>
  );
}

function policyReviewRoleAccess(actorState: CurrentActorState) {
  if (actorState.status === "loading") {
    return { allowed: false, reason: "Current actor loading." };
  }
  if (actorState.status === "error") {
    return {
      allowed: false,
      reason: "Backend authorization still enforced."
    };
  }
  if (canReviewPolicies(actorState.actor)) {
    return { allowed: true, reason: null };
  }
  return { allowed: false, reason: "Reviewer role required." };
}

function policyReviewDecisionAccess(
  request: PolicyVersionReviewRequestRecord,
  actorState: CurrentActorState
) {
  const roleAccess = policyReviewRoleAccess(actorState);
  if (!roleAccess.allowed || actorState.status !== "ready") {
    return roleAccess;
  }

  const actor = actorState.actor;
  if (!request.assigned_reviewer_actor_id || hasRole(actor, "platform_admin")) {
    return { allowed: true, reason: null };
  }
  if (
    actor.actor_type === request.assigned_reviewer_actor_type &&
    actor.actor_id === request.assigned_reviewer_actor_id
  ) {
    return { allowed: true, reason: null };
  }
  return { allowed: false, reason: "Assigned to another reviewer." };
}

function canReviewPolicies(actor: CurrentActorRecord) {
  return REVIEWER_ROLES.some((role) => hasRole(actor, role));
}

function hasRole(actor: CurrentActorRecord, role: string) {
  return actor.roles.includes(role);
}

function PolicyReviewDiffSummary({
  diffState,
  onCreateRollbackDraft,
  rollbackState
}: {
  diffState: DiffState | undefined;
  onCreateRollbackDraft: (sourcePolicyVersionId: string) => void;
  rollbackState: ActionState | undefined;
}) {
  if (!diffState || diffState.status === "loading") {
    return (
      <div className="policy-review-diff-card">
        <div className="policy-review-diff-head">
          <strong>Policy review diff</strong>
          <AGCPBadge tone="muted">Loading</AGCPBadge>
        </div>
        <p>Loading deterministic Policy Review Diff from the backend.</p>
      </div>
    );
  }

  if (diffState.status === "error") {
    return (
      <div className="policy-review-diff-card error">
        <div className="policy-review-diff-head">
          <strong>Policy review diff</strong>
          <AGCPBadge tone="danger">Unavailable</AGCPBadge>
        </div>
        <p>{diffState.message}</p>
      </div>
    );
  }

  const diff = diffState.diff;
  const conditionChangeCount = diffConditionChangeCount(diff);
  const baselineLabel = policyReviewBaselineLabel(diff);
  const changedFields = changedConditionFieldNames(diff);
  const runtimeEffect = diff.runtime_effect_summary.join(" ");
  const rollbackSourcePolicyVersionId = rollbackSourceVersionId(diff);

  return (
    <div className="policy-review-diff-card">
      <div className="policy-review-diff-head">
        <div>
          <strong>Policy review diff</strong>
          <p>{diff.baseline_summary}</p>
        </div>
        <AGCPBadge tone={diff.baseline_type === "none" ? "warn" : "info"}>
          {baselineLabel}
        </AGCPBadge>
      </div>

      <div className="policy-review-diff-grid">
        <div>
          <span>Changed fields</span>
          <strong>{conditionChangeCount}</strong>
        </div>
        <div>
          <span>Unchanged condition fields</span>
          <strong>{diff.rule_condition_changes.unchanged_fields_count}</strong>
        </div>
        <div>
          <span>Can activate</span>
          <strong>{diff.can_activate ? "Yes" : "No"}</strong>
        </div>
        <div>
          <span>Requires replace</span>
          <strong>{diff.activation_requires_replace ? "Yes" : "No"}</strong>
        </div>
      </div>

      <p className="policy-review-runtime-effect">
        {runtimeEffect || "No runtime effect until activation"}
      </p>

      <div className="policy-review-rollback-box">
        <div>
          <strong>Create rollback draft</strong>
          <p>Rollback draft does not affect runtime.</p>
          <p>Submit for review required before activation.</p>
          <p>No runtime change until approved and activated.</p>
        </div>
        <button
          className="table-action-button"
          disabled={
            !rollbackSourcePolicyVersionId ||
            rollbackState?.status === "submitting"
          }
          onClick={() => {
            if (rollbackSourcePolicyVersionId) {
              onCreateRollbackDraft(rollbackSourcePolicyVersionId);
            }
          }}
          title={
            rollbackSourcePolicyVersionId
              ? `Create a draft copy from PolicyVersion ${rollbackSourcePolicyVersionId}`
              : "No prior active, superseded, approved, or archived PolicyVersion is available as a rollback source."
          }
          type="button"
        >
          {rollbackState?.status === "submitting"
            ? "Creating rollback draft"
            : "Create rollback draft"}
        </button>
      </div>

      {rollbackState && rollbackState.status !== "idle" ? (
        <p className={`review-action-message ${rollbackState.status}`}>
          {rollbackState.message}
        </p>
      ) : null}

      <details className="policy-review-diff-details">
        <summary>Expand Policy Review Diff details</summary>
        <div className="policy-review-diff-section">
          <h4>Changed condition fields</h4>
          {changedFields.length > 0 ? (
            <ul>
              {changedFields.map((field) => (
                <li key={field}>{field}</li>
              ))}
            </ul>
          ) : (
            <p>No condition field changes detected.</p>
          )}
        </div>

        <div className="policy-review-diff-section">
          <h4>Policy snapshot changes</h4>
          <ul>
            {(["name", "description", "status"] as const).map((field) => {
              const change = diff.policy_snapshot_changes[field];
              return (
                <li key={field}>
                  <span>{field}</span>
                  <code>
                    {change.changed
                      ? `${formatDiffValue(change.baseline)} -> ${formatDiffValue(
                          change.reviewed
                        )}`
                      : "unchanged"}
                  </code>
                </li>
              );
            })}
          </ul>
        </div>

        <div className="policy-review-diff-section">
          <h4>Check step changes</h4>
          <p>
            Added {diff.check_step_changes.added_count}, removed{" "}
            {diff.check_step_changes.removed_count}, changed{" "}
            {diff.check_step_changes.changed_count}, unchanged{" "}
            {diff.check_step_changes.unchanged_count}.
          </p>
        </div>

        <div className="policy-review-diff-section">
          <h4>Activation evidence</h4>
          <dl className="policy-review-evidence-grid">
            <div>
              <dt>Requested by</dt>
              <dd>
                {formatValue(diff.evidence.requested_by_actor_type)} /{" "}
                {diff.evidence.requested_by_actor_id}
              </dd>
            </div>
            <div>
              <dt>Reviewer</dt>
              <dd>
                {diff.evidence.reviewer_actor_type
                  ? `${formatValue(diff.evidence.reviewer_actor_type)} / ${
                      diff.evidence.reviewer_actor_id
                    }`
                  : "Not decided"}
              </dd>
            </div>
            <div>
              <dt>Activation audit</dt>
              <dd>
                {diff.evidence.activation_audit_event
                  ? diff.evidence.activation_audit_event.event_type
                  : "No activation audit event yet"}
              </dd>
            </div>
            <div>
              <dt>Superseded audit</dt>
              <dd>
                {diff.evidence.superseded_audit_event
                  ? diff.evidence.superseded_audit_event.event_type
                  : "No supersession audit event yet"}
              </dd>
            </div>
            <div>
              <dt>Activated PolicyVersion</dt>
              <dd>{diff.evidence.activated_policy_version_id || "Not activated"}</dd>
            </div>
            <div>
              <dt>Previous active version</dt>
              <dd>
                {diff.evidence.previous_active_policy_version_id ||
                  "No previous active version recorded"}
              </dd>
            </div>
          </dl>
        </div>
      </details>
    </div>
  );
}

function policyReviewBaselineLabel(diff: PolicyVersionReviewDiffRecord) {
  if (diff.baseline_type === "active_version") {
    return "Baseline active version";
  }
  if (diff.baseline_type === "live_fallback") {
    return "Baseline live fallback";
  }
  return "No active baseline found";
}

function rollbackSourceVersionId(diff: PolicyVersionReviewDiffRecord) {
  return (
    diff.evidence.previous_active_policy_version_id ||
    diff.baseline_policy_version_id ||
    null
  );
}

function diffConditionChangeCount(diff: PolicyVersionReviewDiffRecord) {
  return (
    diff.rule_condition_changes.added_fields.length +
    diff.rule_condition_changes.removed_fields.length +
    diff.rule_condition_changes.changed_fields.length
  );
}

function changedConditionFieldNames(diff: PolicyVersionReviewDiffRecord) {
  return [
    ...diff.rule_condition_changes.added_fields.map(
      (field) => `added ${field.field}`
    ),
    ...diff.rule_condition_changes.removed_fields.map(
      (field) => `removed ${field.field}`
    ),
    ...diff.rule_condition_changes.changed_fields.map(
      (field) => `changed ${field.field}`
    )
  ];
}

function formatDiffValue(value: unknown) {
  if (value === null || value === undefined) {
    return "not set";
  }
  if (typeof value === "string" || typeof value === "number") {
    return String(value);
  }
  if (typeof value === "boolean") {
    return value ? "true" : "false";
  }
  return JSON.stringify(value);
}
