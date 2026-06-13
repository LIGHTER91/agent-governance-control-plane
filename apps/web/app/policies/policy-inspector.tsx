"use client";

import { CurrentActorRecord } from "../lib/current-actor";
import {
  PolicyRecord,
  PolicyRuleRecord,
  PolicyVersionReviewDiffRecord,
  PolicyVersionReviewStateRecord,
  PolicyVersionRecord
} from "../lib/policies";
import {
  ParsedPolicyDsl,
  PolicyCondition,
  jsonConditionPreview,
  summarizePolicyRule
} from "./policy-dsl";

export function PolicyInspector({
  compiled,
  condition,
  currentActorState,
  localNote,
  onChangeLocalNote,
  onSaveDraft,
  onSubmitReview,
  onValidate,
  parsed,
  policyVersionsState,
  reviewDiffState,
  reviewState,
  saveDisabledReason,
  saveState,
  selectedDraftReviewState,
  selectedDraftVersion,
  selectedPolicy,
  selectedRule,
  selectedRuleUnsupportedFields,
  versionReviewState
}: {
  compiled: {
    checkFields: string[];
    decision: string;
    hasEvidenceIntent: boolean;
    policyRuleCount: number;
    usesCheckFields: boolean;
  };
  condition: PolicyCondition;
  currentActorState:
    | { status: "idle" }
    | { status: "loading" }
    | { status: "error"; message: string }
    | { status: "ready"; actor: CurrentActorRecord };
  localNote: string;
  onChangeLocalNote: (note: string) => void;
  onSaveDraft: () => void;
  onSubmitReview: () => void;
  onValidate: () => void;
  parsed: ParsedPolicyDsl;
  policyVersionsState:
    | { status: "idle" }
    | { status: "loading" }
    | { status: "error"; message: string }
    | { status: "ready"; versions: PolicyVersionRecord[] };
  reviewDiffState:
    | { status: "idle" }
    | { status: "loading" }
    | { status: "error"; message: string }
    | { status: "ready"; diff: PolicyVersionReviewDiffRecord };
  versionReviewState:
    | { status: "idle" }
    | { status: "loading" }
    | { status: "error"; message: string }
    | { status: "ready"; state: PolicyVersionReviewStateRecord };
  reviewState: {
    status: "idle" | "submitting" | "success" | "error";
    message: string;
  };
  saveDisabledReason: string | null;
  saveState: {
    status: "unsaved" | "saving" | "saved" | "save_error";
    message: string;
  };
  selectedDraftReviewState: PolicyVersionReviewStateRecord | null;
  selectedDraftVersion: PolicyVersionRecord | null;
  selectedPolicy: PolicyRecord | null;
  selectedRule: PolicyRuleRecord | null;
  selectedRuleUnsupportedFields: string[];
}) {
  const reviewStatus = selectedDraftVersion?.status || selectedPolicy?.status || "local_draft";
  const humanApprovalRequired = compiled.decision === "require_human_review";
  const versionCount =
    policyVersionsState.status === "ready"
      ? String(policyVersionsState.versions.length)
      : policyVersionsState.status;
  const reviewStatusLabelText = selectedDraftReviewState
    ? reviewStateLabel(selectedDraftReviewState.review_status)
    : reviewStateFallbackLabel(versionReviewState);
  const reviewStateMessage =
    selectedDraftReviewState?.message ||
    (versionReviewState.status === "error"
      ? versionReviewState.message
      : "Review state is not loaded for this draft.");
  const submitDisabledReason = submitReviewDisabledReason({
    currentActorState,
    reviewState,
    saveDisabledReason,
    saveState,
    selectedDraftReviewState,
    selectedDraftVersion
  });

  return (
    <aside className="ps2-inspector" aria-label="Policy inspector">
      <div className="ps2-insp-top">
        <div className="ps2-insp-title">Inspector</div>
        <span className={`chip ${reviewStatusChip(reviewStatus)}`}>
          {reviewStatus}
        </span>
      </div>

      <div className="ps2-insp-scroll">
        <section className="ps2-insp-sec">
          <div className="ps2-insp-sec-title ist2-summary">Summary</div>
          <div className="ps2-summary-box">{summarizePolicyRule(condition)}</div>
        </section>

        <section className="ps2-insp-sec">
          <div className="ps2-insp-sec-title ist2-flow">Decision Flow</div>
          <div className="ps2-dflow">
            <div className="ps2-dflow-row">
              <FlowNode color="#8b78f6" label="WHEN" sub="runtime fields" />
              <div className="ps2-darrow">→</div>
              <FlowNode
                color="#38b4f5"
                label="CHECK"
                sub={`${compiled.checkFields.length} constraints`}
              />
            </div>
            <div className="ps2-dconn">
              <span className="ps2-dconn-line" />
              <span className="ps2-dconn-pill">deterministic match</span>
              <span className="ps2-dconn-line" />
            </div>
            <div className="ps2-dflow-row">
              <FlowNode color="#f0873a" label="THEN" sub={compiled.decision} />
              <div className="ps2-darrow">→</div>
              <FlowNode color="#22d37a" label="PROVE" sub="evidence intent" />
            </div>
          </div>
        </section>

        <section className="ps2-insp-sec">
          <div className="ps2-insp-sec-title ist2-compiled">Compiled Output</div>
          <div className="ps2-compiled-list">
            <CompiledItem
              color="var(--purple-lt)"
              name={parsed.policyName}
              type="Policy"
            />
            <CompiledItem
              color="var(--purple-lt)"
              name={`${parsed.ruleName || "unsaved_rule"} -> deterministic JSON`}
              type="PolicyRule"
            />
            <CompiledItem
              color="#38b4f5"
              name={
                compiled.checkFields.length > 0
                  ? compiled.checkFields.join(", ")
                  : "No supported check fields"
              }
              type="Check fields"
            />
            <CompiledItem
              color={humanApprovalRequired ? "#f0873a" : "var(--text-muted)"}
              name={
                humanApprovalRequired
                  ? "HumanApproval requirement present"
                  : "No HumanApproval requirement"
              }
              type="Review"
            />
            <CompiledItem
              color="#22d37a"
              name="decision, checks, reviewer, evidence_bundle"
              type="Evidence"
            />
          </div>
          <details className="ps2-json-output">
            <summary>Compiled condition JSON</summary>
            <pre>{jsonConditionPreview(parsed.condition)}</pre>
          </details>
        </section>

        <section className="ps2-insp-sec">
          <div className="ps2-insp-sec-title ist2-review">Review Status</div>
          <div className="ps2-review-card">
            <ReviewRow label="Policy status" value={reviewStatus} />
            <ReviewRow
              label="Policy id"
              value={selectedPolicy?.id || "Not persisted"}
            />
            <ReviewRow
              label="Selected rule id"
              value={selectedRule?.id || "Not persisted"}
            />
            <ReviewRow
              label="Draft version id"
              value={selectedDraftVersion?.id || "No draft PolicyVersion saved"}
            />
            <ReviewRow
              label="Draft status"
              value={
                selectedDraftVersion
                  ? `${selectedDraftVersion.status} / not active`
                  : "Local only"
              }
            />
            <ReviewRow label="Known versions" value={versionCount} />
            <ReviewRow
              label="Current actor"
              value={currentActorLabel(currentActorState)}
            />
            <ReviewRow
              label="Actor roles"
              value={currentActorRolesLabel(currentActorState)}
            />
            <ReviewRow label="Review status" value={reviewStatusLabelText} />
            <ReviewRow
              label="Review request"
              value={
                selectedDraftReviewState?.latest_review_request_id
                  ? `${selectedDraftReviewState.latest_review_request_id} / ${reviewStatusLabelText}`
                  : "Not submitted"
              }
            />
            <ReviewRow label="Review state message" value={reviewStateMessage} />
            <ReviewRow
              label="Requested at"
              value={selectedDraftReviewState?.requested_at || "Not submitted"}
            />
            <ReviewRow
              label="Decided at"
              value={selectedDraftReviewState?.decided_at || "Not decided"}
            />
            <ReviewRow
              label="Reviewer"
              value={selectedDraftReviewState?.reviewer_actor_id || "Not decided"}
            />
            <ReviewRow
              label="Runtime impact"
              value="None until explicit PolicyVersion activation"
            />
            <ReviewRow
              label="Review diff"
              value={reviewDiffSummary(reviewDiffState)}
            />
            <ReviewRow
              label="Unsupported fields"
              value={
                selectedRuleUnsupportedFields.length > 0
                  ? selectedRuleUnsupportedFields.join(", ")
                  : "None detected"
              }
            />
            <ReviewRow
              label="Updated"
              value={selectedRule?.updated_at || selectedPolicy?.updated_at || "Local only"}
            />
            <ReviewRow
              label="Save state"
              value={
                saveState.status === "unsaved"
                  ? `Unsaved: ${saveState.message}`
                  : saveState.message
              }
            />
            <ReviewRow
              label="Review state"
              value={
                reviewState.status === "idle" ? "No review request" : reviewState.message
              }
            />
          </div>
          {reviewDiffState.status === "ready" ? (
            <div className="ps2-review-diff">
              <strong>Policy Review Diff</strong>
              <span>{policyStudioBaselineLabel(reviewDiffState.diff)}</span>
              <p>{reviewDiffState.diff.runtime_effect_summary.join(" ")}</p>
              <small>
                Changed fields: {policyStudioChangedFields(reviewDiffState.diff)}
              </small>
              {reviewDiffState.diff.evidence.activation_audit_event ? (
                <small>
                  Activation evidence:{" "}
                  {reviewDiffState.diff.evidence.activation_audit_event.event_type}
                </small>
              ) : null}
            </div>
          ) : null}
          <textarea
            className="ps2-review-note"
            onChange={(event) => onChangeLocalNote(event.target.value)}
            placeholder="Draft change summary. Saved on PolicyVersion drafts only."
            rows={3}
            value={localNote}
          />
        </section>
      </div>

      <div className="ps2-insp-actions">
        {saveDisabledReason ? (
          <div className="ps2-save-state error">{saveDisabledReason}</div>
        ) : saveState.status === "save_error" || saveState.status === "saved" ? (
          <div
            className={`ps2-save-state ${
              saveState.status === "save_error" ? "error" : "success"
            }`}
          >
            {saveState.message}
          </div>
        ) : null}
        {reviewState.status === "error" || reviewState.status === "success" ? (
          <div className={`ps2-save-state ${reviewState.status}`}>
            {reviewState.message}
          </div>
        ) : null}
        <div className="ps2-act-row">
          <button
            className="ps2-act-btn ps2-btn-save"
            disabled={saveState.status === "saving" || Boolean(saveDisabledReason)}
            onClick={onSaveDraft}
            type="button"
          >
            {saveState.status === "saving" ? "Saving" : "Save draft"}
          </button>
          <button
            className="ps2-act-btn ps2-btn-sim"
            onClick={onValidate}
            type="button"
          >
            Validate
          </button>
        </div>
        <button
          className="ps2-act-btn ps2-btn-submit"
          disabled={Boolean(submitDisabledReason)}
          onClick={onSubmitReview}
          title={
            submitDisabledReason ||
            "Submit creates a PolicyVersion review request. Approval does not activate this version."
          }
          type="button"
        >
          {reviewState.status === "submitting" ? "Submitting" : "Submit for review"}
        </button>
        {submitDisabledReason ? (
          <div className="ps2-save-state error">{submitDisabledReason}</div>
        ) : (
          <div className="ps2-save-state success">
            Review approval does not activate this version.
          </div>
        )}
      </div>
    </aside>
  );
}

function submitReviewDisabledReason({
  currentActorState,
  reviewState,
  saveDisabledReason,
  saveState,
  selectedDraftReviewState,
  selectedDraftVersion
}: {
  currentActorState:
    | { status: "idle" }
    | { status: "loading" }
    | { status: "error"; message: string }
    | { status: "ready"; actor: CurrentActorRecord };
  reviewState: { status: "idle" | "submitting" | "success" | "error"; message: string };
  saveDisabledReason: string | null;
  saveState: {
    status: "unsaved" | "saving" | "saved" | "save_error";
    message: string;
  };
  selectedDraftReviewState: PolicyVersionReviewStateRecord | null;
  selectedDraftVersion: PolicyVersionRecord | null;
}) {
  if (currentActorState.status !== "ready") {
    return "Current actor state is unavailable.";
  }
  if (currentActorState.actor.actor_type === "service") {
    return "Backend authorization still applies.";
  }
  if (selectedDraftReviewState?.review_status === "pending") {
    return "A review request is already pending for this draft.";
  }
  if (!selectedDraftVersion) {
    return "Save a draft before submitting for review.";
  }
  if (selectedDraftVersion.status !== "draft") {
    return "This PolicyVersion is not a draft.";
  }
  if (saveDisabledReason || saveState.status === "save_error") {
    return "Fix validation errors before submitting.";
  }
  if (saveState.status === "saving" || reviewState.status === "submitting") {
    return "Backend authorization still applies.";
  }
  if (saveState.status !== "saved" && reviewState.status !== "success") {
    return "Save a draft before submitting for review.";
  }
  if (
    reviewState.status === "success" &&
    (reviewState.message.includes("Review requested") ||
      reviewState.message.includes("already pending"))
  ) {
    return "A review request is already pending for this draft.";
  }
  if (selectedDraftReviewState && !selectedDraftReviewState.can_submit_review) {
    return "This PolicyVersion is not a draft.";
  }
  return null;
}

function currentActorLabel(
  currentActorState:
    | { status: "idle" }
    | { status: "loading" }
    | { status: "error"; message: string }
    | { status: "ready"; actor: CurrentActorRecord }
) {
  if (currentActorState.status === "loading") {
    return "Loading current actor from GET /me";
  }
  if (currentActorState.status === "error") {
    return "Current actor state is unavailable.";
  }
  if (currentActorState.status === "idle") {
    return "Current actor state is unavailable.";
  }

  const actor = currentActorState.actor;
  return actor.display_name
    ? `${actor.display_name} (${formatActorType(actor.actor_type)} / ${actor.actor_id})`
    : `${formatActorType(actor.actor_type)} / ${actor.actor_id}`;
}

function currentActorRolesLabel(
  currentActorState:
    | { status: "idle" }
    | { status: "loading" }
    | { status: "error"; message: string }
    | { status: "ready"; actor: CurrentActorRecord }
) {
  if (currentActorState.status !== "ready") {
    return "Current actor state is unavailable.";
  }
  return currentActorState.actor.roles.length > 0
    ? currentActorState.actor.roles.join(", ")
    : "No roles";
}

function formatActorType(value: string) {
  return value
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function reviewStateLabel(
  status: PolicyVersionReviewStateRecord["review_status"]
) {
  if (status === "not_submitted") {
    return "Not submitted";
  }
  if (status === "pending") {
    return "Pending review";
  }
  if (status === "approved") {
    return "Approved";
  }
  if (status === "rejected") {
    return "Rejected";
  }
  return "Canceled";
}

function reviewStateFallbackLabel(
  versionReviewState:
    | { status: "idle" }
    | { status: "loading" }
    | { status: "error"; message: string }
    | { status: "ready"; state: PolicyVersionReviewStateRecord }
) {
  if (versionReviewState.status === "loading") {
    return "Loading review state";
  }
  if (versionReviewState.status === "error") {
    return "Review state unavailable for current actor.";
  }
  return "Not submitted";
}

function FlowNode({
  color,
  label,
  sub
}: {
  color: string;
  label: string;
  sub: string;
}) {
  return (
    <div className="ps2-dnode">
      <div
        className="ps2-ddot"
        style={{ background: color, boxShadow: `0 0 7px ${color}` }}
      />
      <div className="ps2-dlabel">{label}</div>
      <div className="ps2-dsub">{sub}</div>
    </div>
  );
}

function CompiledItem({
  color,
  name,
  type
}: {
  color: string;
  name: string;
  type: string;
}) {
  return (
    <div className="ps2-compiled-item">
      <span
        className="ps2-ci-dot"
        style={{ background: color, boxShadow: `0 0 5px ${color}` }}
      />
      <span className="ps2-ci-type">{type}</span>
      <span className="ps2-ci-name">{name}</span>
    </div>
  );
}

function ReviewRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="ps2-rc-row">
      <span className="ps2-rc-key">{label}</span>
      <span className="ps2-rc-val">{value}</span>
    </div>
  );
}

function reviewDiffSummary(
  reviewDiffState:
    | { status: "idle" }
    | { status: "loading" }
    | { status: "error"; message: string }
    | { status: "ready"; diff: PolicyVersionReviewDiffRecord }
) {
  if (reviewDiffState.status === "idle") {
    return "No review diff loaded";
  }
  if (reviewDiffState.status === "loading") {
    return "Loading Policy Review Diff";
  }
  if (reviewDiffState.status === "error") {
    return reviewDiffState.message;
  }
  return `${policyStudioBaselineLabel(reviewDiffState.diff)} / ${
    reviewDiffState.diff.review_status
  }`;
}

function policyStudioBaselineLabel(diff: PolicyVersionReviewDiffRecord) {
  if (diff.baseline_type === "active_version") {
    return "Baseline active version";
  }
  if (diff.baseline_type === "live_fallback") {
    return "Baseline live fallback";
  }
  return "No active baseline found";
}

function policyStudioChangedFields(diff: PolicyVersionReviewDiffRecord) {
  const fields = [
    ...diff.rule_condition_changes.added_fields.map((field) => field.field),
    ...diff.rule_condition_changes.removed_fields.map((field) => field.field),
    ...diff.rule_condition_changes.changed_fields.map((field) => field.field)
  ];
  return fields.length > 0 ? fields.join(", ") : "None detected";
}

function reviewStatusChip(status: string) {
  if (status === "active") {
    return "chip-active";
  }
  if (status === "draft" || status === "local_draft") {
    return "chip-draft";
  }
  if (status === "disabled") {
    return "chip-review";
  }
  return "chip-unsaved";
}
