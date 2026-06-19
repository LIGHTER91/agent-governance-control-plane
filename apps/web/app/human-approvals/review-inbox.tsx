"use client";

import {
  useCallback,
  useEffect,
  useMemo,
  useState,
  type Dispatch,
  type ReactNode,
  type SetStateAction
} from "react";
import {
  AGCPBadge,
  AGCPEmptyState,
  AGCPErrorState
} from "../agcp-studio/primitives";
import { getApiBaseUrl } from "../lib/api";
import {
  CurrentActorRecord,
  fetchCurrentActor
} from "../lib/current-actor";
import type { EvidenceCheckResult, EvidenceMetadata } from "../lib/evidence";
import {
  HumanApprovalAction,
  HumanApprovalRecord,
  transitionHumanApproval,
  fetchHumanApprovals
} from "../lib/human-approvals";
import {
  PolicyVersionReviewDiffRecord,
  PolicyVersionReviewRequestRecord,
  PolicyVersionReviewRequestStatus,
  activatePolicyVersionReviewRequest,
  assignPolicyVersionReviewRequest,
  decidePolicyVersionReviewRequest,
  fetchPolicyVersionReviewRequestDiff,
  fetchPolicyVersionReviewRequests
} from "../lib/policies";

type InboxState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | {
      status: "ready";
      humanApprovals: HumanApprovalRecord[];
      policyReviews: PolicyVersionReviewRequestRecord[];
      warnings: string[];
    };

type CurrentActorState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; actor: CurrentActorRecord };

type DiffState =
  | { status: "loading" }
  | { status: "ready"; diff: PolicyVersionReviewDiffRecord }
  | { status: "error"; message: string };

type ReviewTab = "mine" | "waiting" | "escalated" | "completed";

type PolicyReviewItem = {
  kind: "policy";
  key: string;
  request: PolicyVersionReviewRequestRecord;
  tab: ReviewTab;
  title: string;
  subtitle: string;
  status: string;
  metadata: string[];
};

type RuntimeReviewItem = {
  kind: "runtime";
  key: string;
  approval: HumanApprovalRecord;
  tab: ReviewTab;
  title: string;
  subtitle: string;
  status: string;
  metadata: string[];
};

type ReviewItem = PolicyReviewItem | RuntimeReviewItem;

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

const REVIEW_TABS: Array<{ id: ReviewTab; label: string }> = [
  { id: "mine", label: "Mine" },
  { id: "waiting", label: "Waiting" },
  { id: "escalated", label: "Escalated" },
  { id: "completed", label: "Completed" }
];

const POLICY_REVIEW_INBOX_STATUSES: PolicyVersionReviewRequestStatus[] = [
  "pending",
  "approved",
  "rejected",
  "canceled"
];

const REVIEWER_ACTOR_TYPES = ["user", "development"] as const;
const REVIEWER_ROLES = ["reviewer", "platform_admin"] as const;

export function ReviewInbox() {
  const [activeTab, setActiveTab] = useState<ReviewTab>("mine");
  const [selectedItemKey, setSelectedItemKey] = useState<string | null>(null);
  const [inboxState, setInboxState] = useState<InboxState>({
    status: "loading"
  });
  const [actorState, setActorState] = useState<CurrentActorState>({
    status: "loading"
  });
  const [diffsById, setDiffsById] = useState<Record<string, DiffState>>({});
  const [notesByKey, setNotesByKey] = useState<Record<string, string>>({});
  const [assignmentDraftsById, setAssignmentDraftsById] = useState<
    Record<string, AssignmentDraft>
  >({});
  const [replaceActiveById, setReplaceActiveById] = useState<
    Record<string, boolean>
  >({});
  const [actionState, setActionState] = useState<ActionState>({
    id: null,
    status: "idle",
    message: "No review action submitted"
  });

  const loadActor = useCallback(async (signal?: AbortSignal) => {
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
            : "Unable to load current actor from GET /me."
      });
    }
  }, []);

  const loadInbox = useCallback(async (signal?: AbortSignal) => {
    setInboxState({ status: "loading" });

    const [humanResult, policyResult] = await Promise.all([
      fetchHumanApprovals("all", signal)
        .then((approvals) => ({ approvals, error: null }))
        .catch((error: unknown) => ({
          approvals: [] as HumanApprovalRecord[],
          error:
            error instanceof Error
              ? error.message
              : "Unable to load HumanApproval records."
        })),
      fetchPolicyReviewBatch(signal)
    ]);

    if (signal?.aborted) {
      return;
    }

    const warnings = [
      ...(humanResult.error ? [humanResult.error] : []),
      ...policyResult.errors
    ];
    const hasAnyData =
      humanResult.approvals.length > 0 || policyResult.requests.length > 0;

    if (!hasAnyData && warnings.length > 0) {
      setInboxState({
        status: "error",
        message: warnings.join(" ")
      });
      return;
    }

    const sortedPolicyReviews = dedupePolicyReviews(policyResult.requests).sort(
      (left, right) => right.created_at.localeCompare(left.created_at)
    );

    setInboxState({
      status: "ready",
      humanApprovals: humanResult.approvals.sort((left, right) =>
        right.created_at.localeCompare(left.created_at)
      ),
      policyReviews: sortedPolicyReviews,
      warnings
    });

    setDiffsById(
      Object.fromEntries(
        sortedPolicyReviews.map((request) => [
          request.id,
          { status: "loading" } satisfies DiffState
        ])
      )
    );

    const diffEntries = await Promise.all(
      sortedPolicyReviews.map(async (request) => {
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
                  : "Unable to load Policy Review Diff."
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
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    void loadActor(controller.signal);
    void loadInbox(controller.signal);
    return () => controller.abort();
  }, [loadActor, loadInbox]);

  const items = useMemo(
    () =>
      inboxState.status === "ready"
        ? buildReviewItems(inboxState, actorState)
        : [],
    [actorState, inboxState]
  );

  const visibleItems = useMemo(
    () => items.filter((item) => item.tab === activeTab),
    [activeTab, items]
  );

  const selectedItem =
    visibleItems.find((item) => item.key === selectedItemKey) ||
    visibleItems[0] ||
    null;

  async function refreshAfterAction() {
    await loadInbox();
  }

  async function handleRuntimeAction(
    item: RuntimeReviewItem,
    action: Exclude<HumanApprovalAction, "cancel">
  ) {
    setActionState({
      id: item.key,
      status: "submitting",
      message: `${formatValue(action)} runtime approval`
    });

    try {
      await transitionHumanApproval(
        item.approval.id,
        action,
        notesByKey[item.key]
      );
      setActionState({
        id: item.key,
        status: "success",
        message:
          action === "approve"
            ? "HumanApproval approved. Caller-owned execution remains outside AGCP."
            : "HumanApproval rejected. AGCP records the review decision."
      });
      setNotesByKey((current) => ({ ...current, [item.key]: "" }));
      await refreshAfterAction();
    } catch (error: unknown) {
      setActionState({
        id: item.key,
        status: "error",
        message:
          error instanceof Error
            ? error.message
            : `Unable to ${action} HumanApproval.`
      });
    }
  }

  async function handlePolicyDecision(
    item: PolicyReviewItem,
    action: "approve" | "reject"
  ) {
    setActionState({
      id: item.key,
      status: "submitting",
      message: `${formatValue(action)} PolicyVersion review request`
    });

    try {
      await decidePolicyVersionReviewRequest(item.request.id, action, {
        decision_note: notesByKey[item.key]?.trim() || null
      });
      setActionState({
        id: item.key,
        status: "success",
        message:
          action === "approve"
            ? "Policy review approved. Approval does not activate this version."
            : "Policy review rejected. No runtime policy change was made."
      });
      setNotesByKey((current) => ({ ...current, [item.key]: "" }));
      await refreshAfterAction();
    } catch (error: unknown) {
      setActionState({
        id: item.key,
        status: "error",
        message:
          error instanceof Error
            ? error.message
            : `Unable to ${action} PolicyVersion review request.`
      });
    }
  }

  async function handleAssign(item: PolicyReviewItem) {
    const draft = assignmentDraftsById[item.request.id] || emptyAssignmentDraft();
    const actorId = draft.actorId.trim();

    if (!actorId) {
      setActionState({
        id: item.key,
        status: "error",
        message: "Reviewer actor id is required before Reassign."
      });
      return;
    }

    setActionState({
      id: item.key,
      status: "submitting",
      message: "Reassigning PolicyVersion review request"
    });

    try {
      await assignPolicyVersionReviewRequest(item.request.id, {
        assigned_reviewer_actor_type: draft.actorType,
        assigned_reviewer_actor_id: actorId,
        assigned_reviewer_name: draft.name.trim() || null,
        assignment_note: draft.note.trim() || null
      });
      setActionState({
        id: item.key,
        status: "success",
        message:
          "Reviewer assigned. Assignment does not approve, reject, or activate the review."
      });
      setAssignmentDraftsById((current) => ({
        ...current,
        [item.request.id]: emptyAssignmentDraft()
      }));
      await refreshAfterAction();
    } catch (error: unknown) {
      setActionState({
        id: item.key,
        status: "error",
        message:
          error instanceof Error
            ? error.message
            : "Unable to reassign PolicyVersion review request."
      });
    }
  }

  async function handleActivate(item: PolicyReviewItem) {
    setActionState({
      id: item.key,
      status: "submitting",
      message: "Activating approved PolicyVersion review request"
    });

    try {
      await activatePolicyVersionReviewRequest(item.request.id, {
        replace_active: Boolean(replaceActiveById[item.request.id])
      });
      setActionState({
        id: item.key,
        status: "success",
        message:
          "Approved PolicyVersion activated. Future Runtime Gateway and telemetry decisions can use it."
      });
      setReplaceActiveById((current) => ({
        ...current,
        [item.request.id]: false
      }));
      await refreshAfterAction();
    } catch (error: unknown) {
      setActionState({
        id: item.key,
        status: "error",
        message:
          error instanceof Error
            ? error.message
            : "Unable to activate approved PolicyVersion review request."
      });
    }
  }

  return (
    <section className="review-inbox-route" aria-label="Review Inbox">
      <aside className="review-inbox-pane" aria-label="Review work items">
        <div className="review-inbox-header">
          <div>
            <span className="review-kicker">Human Oversight</span>
            <h2>Review Inbox</h2>
            <p>Runtime approvals and PolicyVersion reviews in one queue.</p>
          </div>
          {inboxState.status === "ready" ? (
            <AGCPBadge tone="purple">{items.length} items</AGCPBadge>
          ) : null}
        </div>

        <CurrentActorCompact actorState={actorState} />

        <div className="review-inbox-tabs" role="tablist">
          {REVIEW_TABS.map((tab) => (
            <button
              aria-selected={activeTab === tab.id}
              className={`review-inbox-tab ${activeTab === tab.id ? "active" : ""}`}
              key={tab.id}
              onClick={() => {
                setActiveTab(tab.id);
                setSelectedItemKey(null);
              }}
              role="tab"
              type="button"
            >
              {tab.label}
              <span>{items.filter((item) => item.tab === tab.id).length}</span>
            </button>
          ))}
        </div>

        {inboxState.status === "loading" ? (
          <AGCPEmptyState title="Loading Review Inbox">
            Requesting HumanApproval records and PolicyVersion review requests
            from {getApiBaseUrl()}.
          </AGCPEmptyState>
        ) : null}

        {inboxState.status === "error" ? (
          <AGCPErrorState title="Unable to load Review Inbox">
            {inboxState.message} Check that the backend is running and that the
            current actor can read HumanApproval and PolicyVersion review data.
          </AGCPErrorState>
        ) : null}

        {inboxState.status === "ready" && inboxState.warnings.length > 0 ? (
          <div className="review-inbox-warning" role="status">
            {inboxState.warnings.map((warning) => (
              <p key={warning}>{warning}</p>
            ))}
          </div>
        ) : null}

        {inboxState.status === "ready" ? (
          <div className="review-inbox-list">
            {visibleItems.length === 0 ? (
              <AGCPEmptyState title={emptyTitleForTab(activeTab)}>
                {emptyCopyForTab(activeTab)}
              </AGCPEmptyState>
            ) : (
              visibleItems.map((item) => (
                <button
                  className={`review-inbox-item ${
                    selectedItem?.key === item.key ? "selected" : ""
                  }`}
                  key={item.key}
                  onClick={() => setSelectedItemKey(item.key)}
                  type="button"
                >
                  <div className="review-inbox-item-top">
                    <span>{item.kind === "policy" ? "Policy review" : "Runtime approval"}</span>
                    <AGCPBadge tone={statusTone(item.status)}>
                      {formatValue(item.status)}
                    </AGCPBadge>
                  </div>
                  <strong>{item.title}</strong>
                  <p>{item.subtitle}</p>
                  <div className="review-inbox-item-meta">
                    {item.metadata.map((value) => (
                      <span key={value}>{value}</span>
                    ))}
                  </div>
                </button>
              ))
            )}
          </div>
        ) : null}
      </aside>

      <main className="review-detail-pane" aria-label="Selected review detail">
        {selectedItem ? (
          <ReviewDetail
            actionState={actionState}
            actorState={actorState}
            assignmentDraftsById={assignmentDraftsById}
            diffState={
              selectedItem.kind === "policy"
                ? diffsById[selectedItem.request.id]
                : undefined
            }
            item={selectedItem}
            notesByKey={notesByKey}
            onActivate={handleActivate}
            onAssign={handleAssign}
            onPolicyDecision={handlePolicyDecision}
            onRuntimeAction={handleRuntimeAction}
            replaceActiveById={replaceActiveById}
            setAssignmentDraftsById={setAssignmentDraftsById}
            setNotesByKey={setNotesByKey}
            setReplaceActiveById={setReplaceActiveById}
          />
        ) : (
          <div className="review-detail-empty">
            <AGCPEmptyState title="No review selected">
              Select a review from the inbox. Escalation routing is not wired
              yet, so the Escalated tab stays empty until backend support
              exists.
            </AGCPEmptyState>
          </div>
        )}
      </main>
    </section>
  );
}

function ReviewDetail({
  actionState,
  actorState,
  assignmentDraftsById,
  diffState,
  item,
  notesByKey,
  onActivate,
  onAssign,
  onPolicyDecision,
  onRuntimeAction,
  replaceActiveById,
  setAssignmentDraftsById,
  setNotesByKey,
  setReplaceActiveById
}: {
  actionState: ActionState;
  actorState: CurrentActorState;
  assignmentDraftsById: Record<string, AssignmentDraft>;
  diffState?: DiffState;
  item: ReviewItem;
  notesByKey: Record<string, string>;
  onActivate: (item: PolicyReviewItem) => Promise<void>;
  onAssign: (item: PolicyReviewItem) => Promise<void>;
  onPolicyDecision: (
    item: PolicyReviewItem,
    action: "approve" | "reject"
  ) => Promise<void>;
  onRuntimeAction: (
    item: RuntimeReviewItem,
    action: Exclude<HumanApprovalAction, "cancel">
  ) => Promise<void>;
  replaceActiveById: Record<string, boolean>;
  setAssignmentDraftsById: Dispatch<
    SetStateAction<Record<string, AssignmentDraft>>
  >;
  setNotesByKey: Dispatch<SetStateAction<Record<string, string>>>;
  setReplaceActiveById: Dispatch<SetStateAction<Record<string, boolean>>>;
}) {
  const isSubmitting = actionState.status === "submitting";
  const actionMessageVisible =
    actionState.id === item.key && actionState.status !== "idle";

  return (
    <>
      <div className="review-detail-header">
        <div>
          <span className="review-kicker">
            {item.kind === "policy" ? "PolicyVersion ReviewRequest" : "Runtime HumanApproval"}
          </span>
          <h1>{item.title}</h1>
          <p>{item.subtitle}</p>
        </div>
        <div className="review-detail-status">
          <AGCPBadge tone={statusTone(item.status)}>
            {formatValue(item.status)}
          </AGCPBadge>
          <span>{item.kind === "policy" ? "review workflow" : "runtime gate"}</span>
        </div>
      </div>

      {item.kind === "policy" ? (
        <PolicyReviewDetailBody
          actionMessageVisible={actionMessageVisible}
          actionState={actionState}
          actorState={actorState}
          assignmentDraftsById={assignmentDraftsById}
          diffState={diffState}
          isSubmitting={isSubmitting}
          item={item}
          notesByKey={notesByKey}
          onActivate={onActivate}
          onAssign={onAssign}
          onPolicyDecision={onPolicyDecision}
          replaceActiveById={replaceActiveById}
          setAssignmentDraftsById={setAssignmentDraftsById}
          setNotesByKey={setNotesByKey}
          setReplaceActiveById={setReplaceActiveById}
        />
      ) : (
        <RuntimeApprovalDetailBody
          actionMessageVisible={actionMessageVisible}
          actionState={actionState}
          actorState={actorState}
          isSubmitting={isSubmitting}
          item={item}
          notesByKey={notesByKey}
          onRuntimeAction={onRuntimeAction}
          setNotesByKey={setNotesByKey}
        />
      )}
    </>
  );
}

function PolicyReviewDetailBody({
  actionMessageVisible,
  actionState,
  actorState,
  assignmentDraftsById,
  diffState,
  isSubmitting,
  item,
  notesByKey,
  onActivate,
  onAssign,
  onPolicyDecision,
  replaceActiveById,
  setAssignmentDraftsById,
  setNotesByKey,
  setReplaceActiveById
}: {
  actionMessageVisible: boolean;
  actionState: ActionState;
  actorState: CurrentActorState;
  assignmentDraftsById: Record<string, AssignmentDraft>;
  diffState?: DiffState;
  isSubmitting: boolean;
  item: PolicyReviewItem;
  notesByKey: Record<string, string>;
  onActivate: (item: PolicyReviewItem) => Promise<void>;
  onAssign: (item: PolicyReviewItem) => Promise<void>;
  onPolicyDecision: (
    item: PolicyReviewItem,
    action: "approve" | "reject"
  ) => Promise<void>;
  replaceActiveById: Record<string, boolean>;
  setAssignmentDraftsById: Dispatch<
    SetStateAction<Record<string, AssignmentDraft>>
  >;
  setNotesByKey: Dispatch<SetStateAction<Record<string, string>>>;
  setReplaceActiveById: Dispatch<SetStateAction<Record<string, boolean>>>;
}) {
  const request = item.request;
  const decisionAccess = policyReviewDecisionAccess(request, actorState);
  const roleAccess = policyReviewRoleAccess(actorState);
  const decisionDisabled =
    request.status !== "pending" || isSubmitting || !decisionAccess.allowed;
  const assignmentDisabled =
    request.status !== "pending" || isSubmitting || !roleAccess.allowed;
  const activateDisabled =
    request.status !== "approved" || isSubmitting || !roleAccess.allowed;
  const draft = assignmentDraftsById[request.id] || emptyAssignmentDraft();

  return (
    <>
      <div className="review-detail-grid">
        <ReviewSection accent="orange" title="Why Review Is Required">
          <p>
            This PolicyVersion can change future Runtime Gateway and telemetry
            policy evaluation after activation.
          </p>
          <p>
            Review approval records reviewer intent only. Activation remains a
            separate explicit step; there is no direct runtime promotion
            shortcut.
          </p>
          <MiniMetaGrid
            items={[
              ["Requested by", actorRef(request.requested_by_actor_type, request.requested_by_actor_id)],
              ["Assigned reviewer", assignedReviewerLabel(request)],
              ["Version", `v${request.policy_version_number || "?"} / ${shortId(request.policy_version_id)}`]
            ]}
          />
        </ReviewSection>

        <ReviewSection accent="purple" title="Policy Decision">
          <PolicyDiffSummary diffState={diffState} />
        </ReviewSection>

        <ReviewSection accent="sky" title="Policy Checks">
          <PolicyChecksSummary diffState={diffState} />
        </ReviewSection>

        <ReviewSection accent="green" title="Evidence Preview">
          <PolicyEvidencePreview diffState={diffState} request={request} />
        </ReviewSection>
      </div>

      <div className="review-decision-note">
        <label>
          <span>Decision note</span>
          <textarea
            disabled={decisionDisabled}
            onChange={(event) =>
              setNotesByKey((current) => ({
                ...current,
                [item.key]: event.target.value
              }))
            }
            placeholder="Optional reviewer note"
            value={notesByKey[item.key] || ""}
          />
        </label>
      </div>

      {request.status === "pending" ? (
        <div className="review-reassign-box">
          <div>
            <strong>Reassign reviewer</strong>
            <p>No fake user directory. Enter a stable actor id.</p>
          </div>
          <label>
            <span>Actor type</span>
            <select
              disabled={assignmentDisabled}
              onChange={(event) =>
                setAssignmentDraftsById((current) => ({
                  ...current,
                  [request.id]: { ...draft, actorType: event.target.value }
                }))
              }
              value={draft.actorType}
            >
              {REVIEWER_ACTOR_TYPES.map((actorType) => (
                <option key={actorType} value={actorType}>
                  {formatValue(actorType)}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span>Reviewer actor id</span>
            <input
              disabled={assignmentDisabled}
              onChange={(event) =>
                setAssignmentDraftsById((current) => ({
                  ...current,
                  [request.id]: { ...draft, actorId: event.target.value }
                }))
              }
              placeholder="local-admin"
              value={draft.actorId}
            />
          </label>
          <label>
            <span>Display name optional</span>
            <input
              disabled={assignmentDisabled}
              onChange={(event) =>
                setAssignmentDraftsById((current) => ({
                  ...current,
                  [request.id]: { ...draft, name: event.target.value }
                }))
              }
              placeholder="Local Admin"
              value={draft.name}
            />
          </label>
          <label>
            <span>Assignment note optional</span>
            <input
              disabled={assignmentDisabled}
              onChange={(event) =>
                setAssignmentDraftsById((current) => ({
                  ...current,
                  [request.id]: { ...draft, note: event.target.value }
                }))
              }
              placeholder="Reason for reassignment"
              value={draft.note}
            />
          </label>
        </div>
      ) : null}

      {request.status === "approved" ? (
        <label className="review-activation-check">
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
          <span>This will replace the current active version if one exists.</span>
        </label>
      ) : null}

      <div className="review-action-row">
        {request.status === "approved" ? (
          <>
            <button
              className="review-action-btn approve"
              disabled={activateDisabled}
              onClick={() => void onActivate(item)}
              type="button"
            >
              Activate approved version
            </button>
            <button
              className="review-action-btn secondary"
              disabled
              title="This review is already approved."
              type="button"
            >
              Approve
            </button>
            <button
              className="review-action-btn secondary"
              disabled
              title="This review is already approved."
              type="button"
            >
              Reject
            </button>
          </>
        ) : (
          <>
            <button
              className="review-action-btn approve"
              disabled={decisionDisabled}
              onClick={() => void onPolicyDecision(item, "approve")}
              type="button"
            >
              Approve
            </button>
            <button
              className="review-action-btn reject"
              disabled={decisionDisabled}
              onClick={() => void onPolicyDecision(item, "reject")}
              type="button"
            >
              Reject
            </button>
          </>
        )}
        <button
          className="review-action-btn secondary"
          disabled
          title="Request info workflow is not wired yet."
          type="button"
        >
          Request info
        </button>
        <button
          className="review-action-btn secondary"
          disabled={assignmentDisabled}
          onClick={() => void onAssign(item)}
          type="button"
        >
          Reassign
        </button>
      </div>

      <p className="review-disabled-reason">
        {policyReviewActionReason(request, decisionAccess, roleAccess)}
      </p>

      {actionMessageVisible ? (
        <p className={`review-action-message ${actionState.status}`}>
          {actionState.message}
        </p>
      ) : null}
    </>
  );
}

function RuntimeApprovalDetailBody({
  actionMessageVisible,
  actionState,
  actorState,
  isSubmitting,
  item,
  notesByKey,
  onRuntimeAction,
  setNotesByKey
}: {
  actionMessageVisible: boolean;
  actionState: ActionState;
  actorState: CurrentActorState;
  isSubmitting: boolean;
  item: RuntimeReviewItem;
  notesByKey: Record<string, string>;
  onRuntimeAction: (
    item: RuntimeReviewItem,
    action: Exclude<HumanApprovalAction, "cancel">
  ) => Promise<void>;
  setNotesByKey: Dispatch<SetStateAction<Record<string, string>>>;
}) {
  const approval = item.approval;
  const roleAccess = policyReviewRoleAccess(actorState);
  const pending = approval.status === "pending";
  const decisionDisabled = !pending || isSubmitting || !roleAccess.allowed;
  const checkResults = approval.check_results || [];

  return (
    <>
      <div className="review-detail-grid">
        <ReviewSection accent="orange" title="Why Review Is Required">
          <p>
            {approval.reason ||
              "The Runtime Gateway requested human oversight for this action."}
          </p>
          <p>
            AGCP records the decision and evidence. The runtime or orchestrator
            still owns whether and how tool execution resumes.
          </p>
          <MiniMetaGrid
            items={[
              ["Requested by", actorRef(approval.requested_by_actor_type, approval.requested_by_actor_id)],
              ["Agent", shortId(approval.agent_id)],
              ["Expires", formatTimestamp(approval.expires_at)]
            ]}
          />
        </ReviewSection>

        <ReviewSection accent="purple" title="Policy Decision">
          <MiniMetaGrid
            items={[
              ["Policy decision", shortId(approval.policy_decision_id)],
              ["Status", formatValue(approval.status)],
              ["Decision note", approval.decision_note || "Not set"]
            ]}
          />
        </ReviewSection>

        <ReviewSection accent="sky" title="Policy Checks">
          {checkResults.length > 0 ? (
            <p>
              {checkResults.length} metadata pre-check result
              {checkResults.length === 1 ? "" : "s"} attached to the
              linked PolicyDecision.
            </p>
          ) : (
            <p>No metadata pre-check results attached yet.</p>
          )}
        </ReviewSection>

        <ReviewSection accent="green" title="Evidence Preview">
          <MiniMetaGrid
            items={[
              ["HumanApproval", shortId(approval.id)],
              ["Created", formatTimestamp(approval.created_at)],
              ["Reviewed by", actorRef(approval.reviewed_by_actor_type, approval.reviewed_by_actor_id)],
              ["Reviewed at", formatTimestamp(approval.reviewed_at)]
            ]}
          />
          <RuntimeCheckResultsPreview checkResults={checkResults} />
        </ReviewSection>
      </div>

      <div className="review-decision-note">
        <label>
          <span>Decision note</span>
          <textarea
            disabled={decisionDisabled}
            onChange={(event) =>
              setNotesByKey((current) => ({
                ...current,
                [item.key]: event.target.value
              }))
            }
            placeholder="Optional runtime review note"
            value={notesByKey[item.key] || ""}
          />
        </label>
      </div>

      <div className="review-action-row">
        <button
          className="review-action-btn approve"
          disabled={decisionDisabled}
          onClick={() => void onRuntimeAction(item, "approve")}
          type="button"
        >
          Approve
        </button>
        <button
          className="review-action-btn reject"
          disabled={decisionDisabled}
          onClick={() => void onRuntimeAction(item, "reject")}
          type="button"
        >
          Reject
        </button>
        <button
          className="review-action-btn secondary"
          disabled
          title="Request info workflow is not wired yet."
          type="button"
        >
          Request info
        </button>
        <button
          className="review-action-btn secondary"
          disabled
          title="Runtime HumanApproval reassignment is not wired yet."
          type="button"
        >
          Reassign
        </button>
      </div>

      <p className="review-disabled-reason">
        {pending
          ? roleAccess.allowed
            ? "Backend authorization still enforced."
            : roleAccess.reason
          : "This runtime review is already completed."}
      </p>

      {actionMessageVisible ? (
        <p className={`review-action-message ${actionState.status}`}>
          {actionState.message}
        </p>
      ) : null}
    </>
  );
}

function ReviewSection({
  accent,
  children,
  title
}: {
  accent: "orange" | "purple" | "sky" | "green";
  children: ReactNode;
  title: string;
}) {
  return (
    <section className={`review-section-card ${accent}`}>
      <div className="review-section-head">
        <span />
        <h3>{title}</h3>
      </div>
      <div className="review-section-body">{children}</div>
    </section>
  );
}

function MiniMetaGrid({ items }: { items: Array<[string, string]> }) {
  return (
    <dl className="review-mini-meta">
      {items.map(([label, value]) => (
        <div key={label}>
          <dt>{label}</dt>
          <dd>{value}</dd>
        </div>
      ))}
    </dl>
  );
}

function CurrentActorCompact({
  actorState
}: {
  actorState: CurrentActorState;
}) {
  if (actorState.status === "loading") {
    return (
      <div className="review-current-actor">
        <strong>Current actor</strong>
        <span>Loading GET /me</span>
        <AGCPBadge tone="muted">Backend authorization still enforced</AGCPBadge>
      </div>
    );
  }

  if (actorState.status === "error") {
    return (
      <div className="review-current-actor warning">
        <strong>Current actor</strong>
        <span>{actorState.message}</span>
        <AGCPBadge tone="warn">Backend authorization still enforced</AGCPBadge>
      </div>
    );
  }

  const actor = actorState.actor;
  return (
    <div className="review-current-actor">
      <strong>Current actor</strong>
      <span>{actor.display_name || actor.actor_id}</span>
      <AGCPBadge tone={canReviewPolicies(actor) ? "ok" : "warn"}>
        {actor.roles.length > 0 ? actor.roles.join(", ") : "No roles"}
      </AGCPBadge>
      <small>
        {actor.dev_mode_caveat ||
          "Frontend role hints are advisory; backend authorization still enforced."}
      </small>
    </div>
  );
}

function PolicyDiffSummary({ diffState }: { diffState?: DiffState }) {
  if (!diffState || diffState.status === "loading") {
    return <p>Loading deterministic Policy Review Diff from the backend.</p>;
  }

  if (diffState.status === "error") {
    return <p>{diffState.message}</p>;
  }

  const diff = diffState.diff;
  const changedFields = changedConditionFieldNames(diff);
  return (
    <>
      <p>{diff.baseline_summary}</p>
      <MiniMetaGrid
        items={[
          ["Baseline", policyReviewBaselineLabel(diff)],
          ["Changed fields", String(diffConditionChangeCount(diff))],
          ["Can activate", diff.can_activate ? "Yes" : "No"],
          ["Replace active", diff.activation_requires_replace ? "Required" : "Not required"]
        ]}
      />
      <p className="review-code-line">
        {diff.runtime_effect_summary.join(" ") || "No runtime effect until activation"}
      </p>
      {changedFields.length > 0 ? (
        <ul className="review-field-list">
          {changedFields.slice(0, 6).map((field) => (
            <li key={field}>{field}</li>
          ))}
        </ul>
      ) : (
        <p>No condition field changes detected.</p>
      )}
    </>
  );
}

function PolicyChecksSummary({ diffState }: { diffState?: DiffState }) {
  if (!diffState || diffState.status === "loading") {
    return <p>Loading check-step comparison.</p>;
  }

  if (diffState.status === "error") {
    return <p>No PolicyCheckStep evidence attached yet.</p>;
  }

  const changes = diffState.diff.check_step_changes;
  const hasChanges =
    changes.added_count > 0 ||
    changes.removed_count > 0 ||
    changes.changed_count > 0 ||
    changes.changed_fields.length > 0;

  if (!hasChanges) {
    return <p>No PolicyCheckStep evidence attached yet.</p>;
  }

  return (
    <>
      <MiniMetaGrid
        items={[
          ["Added", String(changes.added_count)],
          ["Removed", String(changes.removed_count)],
          ["Changed", String(changes.changed_count)],
          ["Unchanged", String(changes.unchanged_count)]
        ]}
      />
      {changes.changed_fields.length > 0 ? (
        <ul className="review-field-list">
          {changes.changed_fields.map((field) => (
            <li key={field}>{field}</li>
          ))}
        </ul>
      ) : null}
    </>
  );
}

function PolicyEvidencePreview({
  diffState,
  request
}: {
  diffState?: DiffState;
  request: PolicyVersionReviewRequestRecord;
}) {
  if (!diffState || diffState.status === "loading") {
    return (
      <MiniMetaGrid
        items={[
          ["Review request", shortId(request.id)],
          ["PolicyVersion", shortId(request.policy_version_id)],
          ["Evidence", "Loading"]
        ]}
      />
    );
  }

  if (diffState.status === "error") {
    return (
      <MiniMetaGrid
        items={[
          ["Review request", shortId(request.id)],
          ["PolicyVersion", shortId(request.policy_version_id)],
          ["Evidence", "Diff unavailable"]
        ]}
      />
    );
  }

  const evidence = diffState.diff.evidence;
  return (
    <MiniMetaGrid
      items={[
        ["Review request", shortId(request.id)],
        ["PolicyVersion", shortId(request.policy_version_id)],
        ["Requested", formatTimestamp(evidence.review_requested_at)],
        [
          "Reviewer",
          actorRef(evidence.reviewer_actor_type, evidence.reviewer_actor_id)
        ],
        [
          "Activation audit",
          evidence.activation_audit_event?.event_type || "No activation audit event yet"
        ],
        [
          "Superseded audit",
          evidence.superseded_audit_event?.event_type || "No supersession audit event yet"
        ]
      ]}
    />
  );
}

function RuntimeCheckResultsPreview({
  checkResults
}: {
  checkResults: EvidenceCheckResult[];
}) {
  if (checkResults.length === 0) {
    return <p>No metadata pre-check results attached yet.</p>;
  }

  return (
    <div className="review-check-results" aria-label="Metadata pre-check results">
      {checkResults.map((result) => {
        const metadataEntries = safeEvidenceMetadataEntries(result.metadata);
        return (
          <article className="review-check-result-card" key={result.check_result_id}>
            <div className="review-check-result-top">
              <strong>{result.check_type || "metadata_check"}</strong>
              <AGCPBadge tone={statusTone(result.outcome)}>
                {formatValue(result.outcome)}
              </AGCPBadge>
            </div>
            <MiniMetaGrid
              items={[
                ["Target", `${formatValue(result.target_type)} / ${shortId(result.target_id)}`],
                ["Confidence", result.confidence ? formatValue(result.confidence) : "Not set"],
                ["Created", formatTimestamp(result.created_at)]
              ]}
            />
            {metadataEntries.length > 0 ? (
              <ul className="review-field-list" aria-label="Safe check metadata">
                {metadataEntries.map(([key, value]) => (
                  <li key={key}>
                    {key}: {formatEvidenceMetadataValue(value)}
                  </li>
                ))}
              </ul>
            ) : (
              <p>No safe metadata attached.</p>
            )}
          </article>
        );
      })}
    </div>
  );
}

const UNSAFE_EVIDENCE_METADATA_KEY_PARTS = [
  "api_key",
  "authorization",
  "chunk",
  "credential",
  "password",
  "prompt",
  "raw",
  "secret",
  "token"
];

function safeEvidenceMetadataEntries(metadata: EvidenceMetadata) {
  return Object.entries(metadata).filter(([key]) => {
    const normalizedKey = key.toLowerCase();
    return !UNSAFE_EVIDENCE_METADATA_KEY_PARTS.some((unsafePart) =>
      normalizedKey.includes(unsafePart)
    );
  });
}

function formatEvidenceMetadataValue(value: EvidenceMetadata[string]) {
  if (value === null) {
    return "null";
  }
  if (typeof value === "boolean") {
    return value ? "true" : "false";
  }
  return String(value);
}

async function fetchPolicyReviewBatch(signal?: AbortSignal) {
  const results = await Promise.all(
    POLICY_REVIEW_INBOX_STATUSES.map(async (status) => {
      try {
        const requests = await fetchPolicyVersionReviewRequests(status, signal);
        return { requests, error: null };
      } catch (error: unknown) {
        return {
          requests: [] as PolicyVersionReviewRequestRecord[],
          error:
            error instanceof Error
              ? error.message
              : `Unable to load ${status} PolicyVersion review requests.`
        };
      }
    })
  );

  return {
    requests: results.flatMap((result) => result.requests),
    errors: results
      .map((result) => result.error)
      .filter((error): error is string => Boolean(error))
  };
}

function buildReviewItems(
  inboxState: Extract<InboxState, { status: "ready" }>,
  actorState: CurrentActorState
): ReviewItem[] {
  const policyItems: PolicyReviewItem[] = inboxState.policyReviews.map(
    (request) => ({
      kind: "policy",
      key: `policy:${request.id}`,
      request,
      tab: policyReviewTab(request, actorState),
      title: request.policy_name || "Policy version review",
      subtitle: `v${request.policy_version_number || "?"} · ${assignedReviewerLabel(request)}`,
      status: request.status,
      metadata: [
        `policy ${shortId(request.policy_id)}`,
        `version ${shortId(request.policy_version_id)}`,
        `created ${formatTimestamp(request.created_at)}`
      ]
    })
  );

  const runtimeItems: RuntimeReviewItem[] = inboxState.humanApprovals.map(
    (approval) => ({
      kind: "runtime",
      key: `runtime:${approval.id}`,
      approval,
      tab: approval.status === "pending" ? "mine" : "completed",
      title: approval.reason || `Runtime approval ${shortId(approval.id)}`,
      subtitle: `agent ${shortId(approval.agent_id)} · ${actorRef(
        approval.requested_by_actor_type,
        approval.requested_by_actor_id
      )}`,
      status: approval.status,
      metadata: [
        `approval ${shortId(approval.id)}`,
        `created ${formatTimestamp(approval.created_at)}`,
        `expires ${formatTimestamp(approval.expires_at)}`
      ]
    })
  );

  return [...policyItems, ...runtimeItems].sort((left, right) => {
    const leftCreated =
      left.kind === "policy" ? left.request.created_at : left.approval.created_at;
    const rightCreated =
      right.kind === "policy"
        ? right.request.created_at
        : right.approval.created_at;
    return rightCreated.localeCompare(leftCreated);
  });
}

function policyReviewTab(
  request: PolicyVersionReviewRequestRecord,
  actorState: CurrentActorState
): ReviewTab {
  if (request.status !== "pending") {
    return "completed";
  }

  return policyReviewDecisionAccess(request, actorState).allowed
    ? "mine"
    : "waiting";
}

function dedupePolicyReviews(requests: PolicyVersionReviewRequestRecord[]) {
  return Array.from(new Map(requests.map((request) => [request.id, request])).values());
}

function emptyAssignmentDraft(): AssignmentDraft {
  return {
    actorType: "user",
    actorId: "",
    name: "",
    note: ""
  };
}

function emptyTitleForTab(tab: ReviewTab) {
  if (tab === "escalated") {
    return "No escalated reviews";
  }
  if (tab === "completed") {
    return "No completed reviews";
  }
  if (tab === "waiting") {
    return "No waiting reviews";
  }
  return "No reviews assigned to you";
}

function emptyCopyForTab(tab: ReviewTab) {
  if (tab === "escalated") {
    return "Escalation routing is not wired yet. This tab stays empty until backend escalation support exists.";
  }
  if (tab === "completed") {
    return "Approved, rejected, canceled, cancelled, or expired review work items will appear here after backend review actions complete.";
  }
  if (tab === "waiting") {
    return "Reviews assigned to another reviewer or blocked by current actor state will appear here.";
  }
  return "Pending Runtime approvals and PolicyVersion reviews that the current actor can act on will appear here.";
}

function formatValue(value: string | null | undefined) {
  if (!value) {
    return "Not set";
  }

  return value
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function formatTimestamp(value: string | null | undefined) {
  if (!value) {
    return "Not set";
  }

  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

function statusTone(status: string) {
  if (status === "approved" || status === "active") {
    return "ok";
  }
  if (status === "pending" || status === "under_review") {
    return "warn";
  }
  if (
    status === "rejected" ||
    status === "canceled" ||
    status === "cancelled" ||
    status === "expired"
  ) {
    return "danger";
  }
  return "info";
}

function shortId(value: string | null | undefined) {
  if (!value) {
    return "not set";
  }
  return value.length > 10 ? value.slice(0, 8) : value;
}

function actorRef(
  actorType: string | null | undefined,
  actorId: string | null | undefined
) {
  if (!actorType && !actorId) {
    return "Not set";
  }
  return `${formatValue(actorType)} / ${actorId || "not set"}`;
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

function policyReviewRoleAccess(actorState: CurrentActorState) {
  if (actorState.status === "loading") {
    return { allowed: false, reason: "Current actor state is unavailable." };
  }
  if (actorState.status === "error") {
    return {
      allowed: false,
      reason: "Backend authorization still enforced."
    };
  }
  if (canReviewPolicies(actorState.actor)) {
    return { allowed: true, reason: "Backend authorization still enforced." };
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
    return { allowed: true, reason: "Backend authorization still enforced." };
  }
  if (
    actor.actor_type === request.assigned_reviewer_actor_type &&
    actor.actor_id === request.assigned_reviewer_actor_id
  ) {
    return { allowed: true, reason: "Backend authorization still enforced." };
  }
  return { allowed: false, reason: "Assigned to another reviewer." };
}

function policyReviewActionReason(
  request: PolicyVersionReviewRequestRecord,
  decisionAccess: { allowed: boolean; reason: string },
  roleAccess: { allowed: boolean; reason: string }
) {
  if (request.status === "pending") {
    return decisionAccess.reason;
  }
  if (request.status === "approved") {
    return roleAccess.allowed
      ? "Activation changes runtime policy evaluation and is explicit."
      : roleAccess.reason;
  }
  return "This review request is completed.";
}

function canReviewPolicies(actor: CurrentActorRecord) {
  return REVIEWER_ROLES.some((role) => hasRole(actor, role));
}

function hasRole(actor: CurrentActorRecord, role: string) {
  return actor.roles.includes(role);
}

function policyReviewBaselineLabel(diff: PolicyVersionReviewDiffRecord) {
  if (diff.baseline_type === "active_version") {
    return "Baseline active version";
  }
  if (diff.baseline_type === "live_fallback") {
    return "Baseline live fallback";
  }
  return "No active baseline yet";
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
