"use client";

import { useState } from "react";
import type { CurrentActorRecord } from "../lib/current-actor";
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
import type {
  PolicyCheckDraft,
  PolicyCheckInventoryState,
  PolicyCheckValidation
} from "./policy-check-authoring";
import { PolicyCheckInspector } from "./policy-check-inspector";
import { PolicyIcon } from "./policy-icons";
import type { PolicyLifecycleState, PolicyStudioEditorSource } from "./policy-studio";

export function PolicyInspector({
  compiled,
  condition,
  currentActorState,
  editorSource,
  localNote,
  policyChecks,
  policyCheckInventoryState,
  policyCheckValidationById,
  onChangeLocalNote,
  onArchivePolicy,
  onCreateNewDraftForChanges,
  onDeletePolicy,
  onLinkPolicyCheckCondition,
  onRemovePolicyCheck,
  onSaveDraft,
  onSubmitReview,
  onValidate,
  onUpdatePolicyCheck,
  parsed,
  policyLifecycleState,
  policyVersionsState,
  reviewDiffState,
  reviewState,
  saveDisabledReason,
  saveState,
  selectedDraftReviewState,
  selectedDraftVersion,
  selectedPolicyCheckId,
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
  editorSource: PolicyStudioEditorSource;
  localNote: string;
  policyChecks: PolicyCheckDraft[];
  policyCheckInventoryState: PolicyCheckInventoryState;
  policyCheckValidationById: Map<string, PolicyCheckValidation>;
  onChangeLocalNote: (note: string) => void;
  onArchivePolicy: () => void;
  onCreateNewDraftForChanges: () => void;
  onDeletePolicy: () => void;
  onLinkPolicyCheckCondition: (checkId: string) => void;
  onRemovePolicyCheck: (checkId: string) => void;
  onSaveDraft: () => void;
  onSubmitReview: () => void;
  onValidate: () => void;
  onUpdatePolicyCheck: (check: PolicyCheckDraft) => void;
  parsed: ParsedPolicyDsl;
  policyLifecycleState: PolicyLifecycleState;
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
  selectedPolicyCheckId: string | null;
  selectedPolicy: PolicyRecord | null;
  selectedRule: PolicyRuleRecord | null;
  selectedRuleUnsupportedFields: string[];
}) {
  const reviewStatus = selectedDraftVersion?.status || selectedPolicy?.status || "local_draft";
  const policyDisplayName =
    selectedPolicy?.name || titleizePolicyName(parsed.policyName);
  const policyVersionLabel = selectedDraftVersion
    ? `v${selectedDraftVersion.version_number}`
    : "Local draft";
  const humanApprovalRequired = hasApprovalRequirement(parsed, compiled.decision);
  const modifiedAt =
    selectedDraftVersion?.updated_at ||
    selectedRule?.updated_at ||
    selectedPolicy?.updated_at ||
    null;
  const retentionDays = evidenceRetentionDays(parsed);
  const versionCount =
    policyVersionsState.status === "ready"
      ? String(policyVersionsState.versions.length)
      : policyVersionsState.status;
  const reviewStatusLabelText = selectedDraftReviewState
    ? reviewStateLabel(selectedDraftReviewState.review_status)
    : reviewStateFallbackLabel(versionReviewState);
  const reviewStateMessage =
    selectedDraftReviewState?.review_status === "pending"
      ? "This draft is locked while review is pending. Create a new draft for additional changes."
      : selectedDraftReviewState?.message ||
        (versionReviewState.status === "error"
          ? versionReviewState.message
          : "Review state is not loaded for this draft.");
  const submitDisabledReason = submitReviewDisabledReason({
    currentActorState,
    editorSource,
    reviewState,
    saveDisabledReason,
    saveState,
    selectedDraftReviewState,
    selectedDraftVersion
  });
  const hasPendingReview =
    selectedDraftReviewState?.review_status === "pending";
  const createDraftDisabledReason = createDraftForChangesDisabledReason({
    parsed,
    saveState,
    selectedPolicy,
    selectedRuleUnsupportedFields
  });
  const archiveDisabledReason = archivePolicyDisabledReason({
    policyLifecycleState,
    policyVersionsState,
    selectedPolicy
  });
  const deleteDisabledReason = deletePolicyDisabledReason({
    policyLifecycleState,
    policyVersionsState,
    selectedPolicy
  });
  const [activeTab, setActiveTab] = useState<"inspector" | "references">(
    "inspector"
  );
  const selectedPolicyCheck =
    policyChecks.find((check) => check.id === selectedPolicyCheckId) || null;
  const checkEditingLocked =
    selectedDraftReviewState?.review_status === "pending";

  return (
    <aside className="ps2-inspector" aria-label="Policy inspector">
      <div className="ps2-insp-top">
        <button
          className={`ps2-insp-tab ${activeTab === "inspector" ? "active" : ""}`}
          onClick={() => setActiveTab("inspector")}
          type="button"
        >
          Inspector
        </button>
        <button
          className={`ps2-insp-tab ${activeTab === "references" ? "active" : ""}`}
          onClick={() => setActiveTab("references")}
          type="button"
        >
          References
        </button>
      </div>

      {activeTab === "references" ? (
        <ReferencesTab
          selectedDraftReviewState={selectedDraftReviewState}
          selectedDraftVersion={selectedDraftVersion}
          selectedPolicy={selectedPolicy}
          selectedRule={selectedRule}
        />
      ) : (
      <div className="ps2-insp-scroll">
        {selectedPolicyCheck ? (
          <PolicyCheckInspector
            check={selectedPolicyCheck}
            condition={condition}
            editingLocked={checkEditingLocked}
            inventoryState={policyCheckInventoryState}
            onChange={onUpdatePolicyCheck}
            onLinkCondition={() =>
              onLinkPolicyCheckCondition(selectedPolicyCheck.id)
            }
            onRemove={() => onRemovePolicyCheck(selectedPolicyCheck.id)}
            validation={
              policyCheckValidationById.get(selectedPolicyCheck.id) || null
            }
          />
        ) : null}
        <section className="ps2-insp-sec">
          <div className="ps2-insp-sec-title ist2-summary">Policy details</div>
          <div className="ps2-review-card">
            <ReviewRow
              label="Reference"
              title={selectedPolicy?.id}
              value={
                selectedPolicy
                  ? referenceLabel("Policy", selectedPolicy.id)
                  : "Not persisted"
              }
            />
            <ReviewRow label="Name" value={policyDisplayName} />
            <ReviewRow
              label="Folder"
              value={selectedPolicy?.folder_name || "Uncategorized"}
            />
            <ReviewRow label="Version" value={policyVersionLabel} />
            <ReviewRow
              label="Status"
              value={reviewStatus === "local_draft" ? "Local draft" : reviewStatus}
            />
            <ReviewRow label="Owner" value={currentActorLabel(currentActorState)} />
            <ReviewRow
              label="Last modified"
              value={modifiedAt ? formatDateTime(modifiedAt) : "Local only"}
            />
          </div>
          <div className="ps2-summary-box">{summarizePolicyRule(condition)}</div>
        </section>

        <section className="ps2-insp-sec">
          <div className="ps2-insp-sec-title ist2-review">Governance</div>
          <div className="ps2-review-card">
            <ReviewRow label="Lifecycle" value={lifecycleLabel(reviewStatus)} />
            <ReviewRow
              label="Next step"
              value={governanceNextStep({
                editorSource,
                selectedDraftReviewState,
                selectedDraftVersion,
                selectedPolicy
              })}
            />
            <ReviewRow
              label="Reviewers"
              title={selectedDraftReviewState?.reviewer_actor_id || undefined}
              value={
                selectedDraftReviewState?.reviewer_actor_id
                  ? actorReference(selectedDraftReviewState.reviewer_actor_id)
                  : "Not assigned"
              }
            />
            <ReviewRow
              label="Review channel"
              value={
                selectedDraftReviewState?.latest_review_request_id
                  ? "PolicyVersion review request"
                  : "Not submitted"
              }
            />
          </div>
        </section>

        <section className="ps2-insp-sec">
          <div className="ps2-insp-sec-title ist2-compiled">Policy settings</div>
          <div className="ps2-review-card">
            <ReviewRow
              label="Effect on violation"
              value={
                compiled.decision === "deny"
                  ? "Block"
                  : decisionLabel(compiled.decision)
              }
            />
            <ReviewRow label="Default action" value={decisionLabel(compiled.decision)} />
            <ReviewRow
              label="Exception handling"
              value={humanApprovalRequired ? "Require approval" : "Not configured"}
            />
            <ReviewRow
              label="Evidence retention"
              value={retentionDays ? `${retentionDays} days` : "Not configured"}
            />
            <ReviewRow
              label="Data sensitivity scope"
              value={dataSensitivityScope(condition)}
            />
            <ReviewRow label="Applies to" value={appliesToScope(condition)} />
          </div>
        </section>

        <section className="ps2-insp-sec">
          <div className="ps2-insp-sec-title ist2-flow">Decision Flow</div>
          <div className="ps2-dflow">
            <div className="ps2-dflow-row">
              <FlowNode color="#8b78f6" label="WHEN" sub="runtime fields" />
              <div className="ps2-darrow">-&gt;</div>
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
              <div className="ps2-darrow">-&gt;</div>
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
            <ReviewRow label="Policy status" value={reviewStatus.replace(/_/g, " ")} />
            <ReviewRow label="Editor source" value={editorSourceLabel(editorSource)} />
            <ReviewRow
              label="Policy reference"
              title={selectedPolicy?.id}
              value={
                selectedPolicy
                  ? referenceLabel("Policy", selectedPolicy.id)
                  : "Not persisted"
              }
            />
            <ReviewRow
              label="Selected rule"
              title={selectedRule?.id}
              value={
                selectedRule
                  ? referenceLabel("Rule", selectedRule.id)
                  : "No persisted source rule"
              }
            />
            <ReviewRow
              label="Draft version"
              title={selectedDraftVersion?.id}
              value={
                selectedDraftVersion
                  ? referenceLabel("Draft", selectedDraftVersion.id)
                  : "No draft PolicyVersion saved"
              }
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
            {hasPendingReview ? (
              <ReviewRow
                label="Draft lock"
                value="Locked while review is pending"
              />
            ) : null}
            <ReviewRow
              label="Review request"
              title={selectedDraftReviewState?.latest_review_request_id || undefined}
              value={
                selectedDraftReviewState?.latest_review_request_id
                  ? `${referenceLabel(
                      "Request",
                      selectedDraftReviewState.latest_review_request_id
                    )} / ${reviewStatusLabelText}`
                  : "Not submitted"
              }
            />
            <ReviewRow label="Review state message" value={reviewStateMessage} />
            <ReviewRow
              label="Requested at"
              value={
                selectedDraftReviewState?.requested_at
                  ? formatDateTime(selectedDraftReviewState.requested_at)
                  : "Not submitted"
              }
            />
            <ReviewRow
              label="Decided at"
              value={
                selectedDraftReviewState?.decided_at
                  ? formatDateTime(selectedDraftReviewState.decided_at)
                  : "Not decided"
              }
            />
            <ReviewRow
              label="Reviewer"
              title={selectedDraftReviewState?.reviewer_actor_id || undefined}
              value={
                selectedDraftReviewState?.reviewer_actor_id
                  ? actorReference(selectedDraftReviewState.reviewer_actor_id)
                  : "Not decided"
              }
            />
            <ReviewRow
              label="Runtime impact"
              value={runtimeImpactLabel(editorSource)}
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
              value={
                selectedRule?.updated_at
                  ? formatDateTime(selectedRule.updated_at)
                  : selectedPolicy?.updated_at
                    ? formatDateTime(selectedPolicy.updated_at)
                    : "Local only"
              }
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
              <p>{policyStudioRuntimeEffectSummary(reviewDiffState.diff)}</p>
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
          {hasPendingReview ? (
            <button
              className="ps2-inline-review-action"
              disabled={Boolean(createDraftDisabledReason)}
              onClick={onCreateNewDraftForChanges}
              title={
                createDraftDisabledReason ||
                "Create a new draft PolicyVersion from the current editor state. This does not affect runtime."
              }
              type="button"
            >
              Create new draft for changes
            </button>
          ) : null}
        </section>

        <section className="ps2-insp-sec">
          <div className="ps2-insp-sec-title ist2-review">Tags</div>
          <div className="ps2-tag-row">
            <span>No tags configured</span>
          </div>
        </section>

        <section className="ps2-insp-sec">
          <div className="ps2-insp-sec-title ist2-review">Policy Lifecycle</div>
          <div className="ps2-lifecycle-card">
            <div className="ps2-lifecycle-copy">
              <span>Archive keeps evidence and history.</span>
              <span>
                Delete is only available for draft-only policies with no governance
                history.
              </span>
              <span>
                Policies with versions, reviews, or runtime decisions cannot be
                deleted.
              </span>
            </div>
            <div className="ps2-lifecycle-actions">
              <button
                className="ps2-act-btn ps2-btn-archive"
                disabled={Boolean(archiveDisabledReason)}
                onClick={onArchivePolicy}
                title={
                  archiveDisabledReason ||
                  "Archive policy. Evidence, versions, reviews, decisions, and audit history are retained."
                }
                type="button"
              >
                Archive policy
              </button>
              <button
                className="ps2-act-btn ps2-btn-delete"
                disabled={Boolean(deleteDisabledReason)}
                onClick={onDeletePolicy}
                title={
                  deleteDisabledReason ||
                  "Delete draft policy after typing the policy name. Backend safety checks still apply."
                }
                type="button"
              >
                Delete draft policy
              </button>
            </div>
            {archiveDisabledReason ? (
              <small className="ps2-lifecycle-reason">
                Archive unavailable: {archiveDisabledReason}
              </small>
            ) : null}
            {deleteDisabledReason ? (
              <small className="ps2-lifecycle-reason">
                Delete unavailable: {deleteDisabledReason}
              </small>
            ) : null}
            {policyLifecycleState.status !== "idle" ? (
              <div
                className={`ps2-save-state ${policyLifecycleStateClass(
                  policyLifecycleState
                )}`}
              >
                {policyLifecycleState.message}
              </div>
            ) : null}
          </div>
        </section>
      </div>
      )}
    </aside>
  );
}

function titleizePolicyName(value: string) {
  return value
    .replace(/_/g, " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function ReferencesTab({
  selectedDraftReviewState,
  selectedDraftVersion,
  selectedPolicy,
  selectedRule
}: {
  selectedDraftReviewState: PolicyVersionReviewStateRecord | null;
  selectedDraftVersion: PolicyVersionRecord | null;
  selectedPolicy: PolicyRecord | null;
  selectedRule: PolicyRuleRecord | null;
}) {
  const checkStepCount = selectedDraftVersion?.check_step_snapshots.length || 0;
  const references = [
    selectedPolicy
      ? {
          label: "Policy",
          meta: selectedPolicy.status,
          title: selectedPolicy.id,
          value: referenceLabel("Policy", selectedPolicy.id)
        }
      : null,
    selectedDraftVersion
      ? {
          label: "PolicyVersion",
          meta: `v${selectedDraftVersion.version_number} / ${selectedDraftVersion.status}`,
          title: selectedDraftVersion.id,
          value: referenceLabel("Version", selectedDraftVersion.id)
        }
      : null,
    selectedRule
      ? {
          label: "PolicyRule",
          meta: selectedRule.name,
          title: selectedRule.id,
          value: referenceLabel("Rule", selectedRule.id)
        }
      : null,
    checkStepCount > 0
      ? {
          label: "PolicyCheckSteps",
          value: String(checkStepCount),
          meta: "snapshot records"
        }
      : null,
    selectedDraftReviewState?.latest_review_request_id
      ? {
          label: "Review request",
          meta: selectedDraftReviewState.review_status,
          title: selectedDraftReviewState.latest_review_request_id,
          value: referenceLabel(
            "Request",
            selectedDraftReviewState.latest_review_request_id
          )
        }
      : null
  ].filter(Boolean) as Array<{
    label: string;
    meta: string;
    title?: string;
    value: string;
  }>;

  return (
    <div className="ps2-insp-scroll">
      <section className="ps2-insp-sec">
        <div className="ps2-insp-sec-title ist2-review">References</div>
        {references.length > 0 ? (
          <div className="ps2-compiled-list">
            {references.map((reference) => (
              <CompiledItem
                color="var(--purple-lt)"
                key={`${reference.label}-${reference.value}`}
                name={`${reference.value} / ${reference.meta}`}
                title={reference.title}
                type={reference.label}
              />
            ))}
          </div>
        ) : (
          <div className="ps2-review-card">
            <ReviewRow
              label="Linked objects"
              value="No persisted references loaded"
            />
            <ReviewRow
              label="Evidence Bundle"
              value="Not available from current Policy Studio context"
            />
          </div>
        )}
      </section>
    </div>
  );
}

function hasApprovalRequirement(parsed: ParsedPolicyDsl, decision: string) {
  return (
    decision === "require_human_review" ||
    parsed.structural.some((line) => line.includes("RequireApproval"))
  );
}

function evidenceRetentionDays(parsed: ParsedPolicyDsl) {
  const retentionLine = parsed.structural.find((line) =>
    /Retention\s+days\s+\d+/i.test(line)
  );
  const match = retentionLine?.match(/Retention\s+days\s+(\d+)/i);
  return match?.[1] || null;
}

function lifecycleLabel(status: string) {
  if (status === "local_draft") {
    return "Local authoring";
  }
  return status.replace(/_/g, " ");
}

function governanceNextStep({
  editorSource,
  selectedDraftReviewState,
  selectedDraftVersion,
  selectedPolicy
}: {
  editorSource: PolicyStudioEditorSource;
  selectedDraftReviewState: PolicyVersionReviewStateRecord | null;
  selectedDraftVersion: PolicyVersionRecord | null;
  selectedPolicy: PolicyRecord | null;
}) {
  if (selectedDraftReviewState?.review_status === "pending") {
    return "Wait for review decision";
  }
  if (selectedDraftVersion?.status === "draft") {
    return "Submit for review";
  }
  if (editorSource.kind === "active_version") {
    return "Create draft for changes";
  }
  if (selectedPolicy) {
    return "Save draft PolicyVersion";
  }
  return "Save draft";
}

function decisionLabel(decision: string) {
  if (decision === "uncompiled") {
    return "Not configured";
  }
  return decision.replace(/_/g, " ");
}

function dataSensitivityScope(condition: PolicyCondition) {
  const fields = [
    condition.data_classification,
    condition.source_data_classification
  ].filter(Boolean);
  if (fields.length > 0) {
    return fields.map(String).join(", ");
  }
  if (condition.contains_sensitive_data === true) {
    return "contains sensitive data";
  }
  if (condition.contains_personal_data === true) {
    return "contains personal data";
  }
  return "Not configured";
}

function appliesToScope(condition: PolicyCondition) {
  if (condition.agent_id) {
    return `Agent ${shortReference(String(condition.agent_id))}`;
  }
  if (condition.environment) {
    return `Environment ${String(condition.environment)}`;
  }
  return "Matching runtime requests";
}

function formatDateTime(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString(undefined, {
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    month: "short",
    year: "numeric"
  });
}

function submitReviewDisabledReason({
  currentActorState,
  editorSource,
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
  editorSource: PolicyStudioEditorSource;
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
    return "Current actor is not configured.";
  }
  if (currentActorState.actor.actor_type === "service") {
    return "Backend authorization still applies.";
  }
  if (selectedDraftReviewState?.review_status === "pending") {
    return "Review request already pending.";
  }
  if (editorSource.kind === "active_version") {
    return "Create a draft before submitting changes for review.";
  }
  if (editorSource.kind !== "draft_version") {
    return "Save a draft before submitting for review.";
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
    return "Review request already pending.";
  }
  if (selectedDraftReviewState && !selectedDraftReviewState.can_submit_review) {
    return "This PolicyVersion is not a draft.";
  }
  return null;
}

function createDraftForChangesDisabledReason({
  parsed,
  saveState,
  selectedPolicy,
  selectedRuleUnsupportedFields
}: {
  parsed: ParsedPolicyDsl;
  saveState: {
    status: "unsaved" | "saving" | "saved" | "save_error";
    message: string;
  };
  selectedPolicy: PolicyRecord | null;
  selectedRuleUnsupportedFields: string[];
}) {
  if (!selectedPolicy) {
    return "Save a draft before creating another draft.";
  }
  if (parsed.errors.length > 0 || parsed.unsupported.length > 0) {
    return "Fix validation errors before creating a new draft.";
  }
  if (selectedRuleUnsupportedFields.length > 0) {
    return "Unsupported backend fields must be resolved before creating a new draft.";
  }
  if (saveState.status === "saving") {
    return "Draft creation is already in progress.";
  }
  return null;
}

function archivePolicyDisabledReason({
  policyLifecycleState,
  policyVersionsState,
  selectedPolicy
}: {
  policyLifecycleState: PolicyLifecycleState;
  policyVersionsState:
    | { status: "idle" }
    | { status: "loading" }
    | { status: "error"; message: string }
    | { status: "ready"; versions: PolicyVersionRecord[] };
  selectedPolicy: PolicyRecord | null;
}) {
  if (!selectedPolicy) {
    return "Select a persisted Policy before archiving.";
  }
  if (policyLifecycleState.status === "submitting") {
    return "Policy lifecycle action is already running.";
  }
  if (selectedPolicy.status === "archived") {
    return "Policy is already archived.";
  }
  if (policyVersionsState.status === "loading") {
    return "PolicyVersion state is still loading.";
  }
  if (
    policyVersionsState.status === "ready" &&
    policyVersionsState.versions.some((version) => version.status === "active")
  ) {
    return "Deactivate or supersede the active PolicyVersion before archiving this policy.";
  }
  return null;
}

function deletePolicyDisabledReason({
  policyLifecycleState,
  policyVersionsState,
  selectedPolicy
}: {
  policyLifecycleState: PolicyLifecycleState;
  policyVersionsState:
    | { status: "idle" }
    | { status: "loading" }
    | { status: "error"; message: string }
    | { status: "ready"; versions: PolicyVersionRecord[] };
  selectedPolicy: PolicyRecord | null;
}) {
  if (!selectedPolicy) {
    return "Select a persisted draft Policy before deleting.";
  }
  if (policyLifecycleState.status === "submitting") {
    return "Policy lifecycle action is already running.";
  }
  if (selectedPolicy.status !== "draft") {
    return "Delete is only available for draft-only policies with no governance history.";
  }
  if (policyVersionsState.status === "loading") {
    return "PolicyVersion state is still loading.";
  }
  if (
    policyVersionsState.status === "ready" &&
    policyVersionsState.versions.length > 0
  ) {
    return "Policies with versions, reviews, or runtime decisions cannot be deleted.";
  }
  return null;
}

function policyLifecycleStateClass(policyLifecycleState: PolicyLifecycleState) {
  if (policyLifecycleState.status === "success") {
    return "success";
  }
  if (policyLifecycleState.status === "submitting") {
    return "info";
  }
  return stateMessageClass(policyLifecycleState.message);
}

function stateMessageClass(message: string) {
  if (
    message.includes("review is pending") ||
    message.includes("already pending") ||
    message.includes("Current actor is not configured") ||
    message.includes("Save a draft before submitting") ||
    message.includes("Create a draft before submitting")
  ) {
    return "info";
  }
  if (
    message.includes("Fix validation errors") ||
    message.includes("unsupported") ||
    message.includes("not a draft")
  ) {
    return "attention";
  }
  return "error";
}

function saveStateClass(saveState: {
  status: "unsaved" | "saving" | "saved" | "save_error";
  message: string;
}) {
  if (saveState.status === "saved") {
    return "success";
  }
  return stateMessageClass(saveState.message);
}

function reviewStateClass(reviewState: {
  status: "idle" | "submitting" | "success" | "error";
  message: string;
}) {
  if (reviewState.status === "success") {
    return reviewState.message.includes("already pending") ? "info" : "success";
  }
  return stateMessageClass(reviewState.message);
}

function editorSourceLabel(editorSource: PolicyStudioEditorSource) {
  if (editorSource.kind === "draft_version") {
    return `Editing draft PolicyVersion v${editorSource.versionNumber}`;
  }
  if (editorSource.kind === "active_version") {
    return `Editing active PolicyVersion v${editorSource.versionNumber} baseline`;
  }
  if (editorSource.kind === "live_fallback") {
    return "Live PolicyRule fallback";
  }
  return "Local unsaved draft";
}

function runtimeImpactLabel(editorSource: PolicyStudioEditorSource) {
  if (editorSource.kind === "draft_version") {
    return "No runtime effect until reviewed and activated";
  }
  if (editorSource.kind === "active_version") {
    return "Currently active baseline; edits require a new draft";
  }
  return "None until explicit PolicyVersion activation";
}

function currentActorLabel(
  currentActorState:
    | { status: "idle" }
    | { status: "loading" }
    | { status: "error"; message: string }
    | { status: "ready"; actor: CurrentActorRecord }
) {
  if (currentActorState.status === "loading") {
    return "Loading current actor";
  }
  if (currentActorState.status === "error") {
    return "Not configured";
  }
  if (currentActorState.status === "idle") {
    return "Not configured";
  }

  const actor = currentActorState.actor;
  return actor.display_name
    ? `${actor.display_name} (${formatActorType(actor.actor_type)} / ${actorReference(actor.actor_id)})`
    : `${formatActorType(actor.actor_type)} / ${actorReference(actor.actor_id)}`;
}

function currentActorRolesLabel(
  currentActorState:
    | { status: "idle" }
    | { status: "loading" }
    | { status: "error"; message: string }
    | { status: "ready"; actor: CurrentActorRecord }
) {
  if (currentActorState.status !== "ready") {
    return "Not configured";
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
  title,
  type
}: {
  color: string;
  name: string;
  title?: string;
  type: string;
}) {
  return (
    <div className="ps2-compiled-item">
      <span
        className="ps2-ci-dot"
        style={{ background: color, boxShadow: `0 0 5px ${color}` }}
      />
      <span className="ps2-ci-type">{type}</span>
      <span className="ps2-ci-name" title={title}>{name}</span>
    </div>
  );
}

function ReviewRow({
  label,
  title,
  value
}: {
  label: string;
  title?: string;
  value: string;
}) {
  return (
    <div className="ps2-rc-row">
      <span className="ps2-rc-key">{label}</span>
      <span className="ps2-rc-val" title={title}>{value}</span>
    </div>
  );
}

function referenceLabel(kind: string, id: string) {
  return `${kind} ref ${shortReference(id)}`;
}

function actorReference(actorId: string) {
  return actorId.includes("@") ? actorId : `ref ${shortReference(actorId)}`;
}

function shortReference(value: string) {
  if (value.length <= 12) {
    return value;
  }
  return `${value.slice(0, 8)}...${value.slice(-4)}`;
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
  return "No active baseline yet";
}

function policyStudioRuntimeEffectSummary(diff: PolicyVersionReviewDiffRecord) {
  if (diff.baseline_type === "none") {
    return [
      "This appears to be the first reviewed version for this policy.",
      "No runtime effect until activation."
    ].join(" ");
  }
  const backendNoBaselineMessage = ["No active baseline", "found."].join(" ");
  return diff.runtime_effect_summary
    .join(" ")
    .replace(backendNoBaselineMessage, "No active baseline yet.");
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
