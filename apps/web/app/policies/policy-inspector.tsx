"use client";

import {
  PolicyRecord,
  PolicyRuleRecord,
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
  localNote,
  onChangeLocalNote,
  onSaveDraft,
  onValidate,
  parsed,
  policyVersionsState,
  saveDisabledReason,
  saveState,
  selectedDraftVersion,
  selectedPolicy,
  selectedRule,
  selectedRuleUnsupportedFields
}: {
  compiled: {
    checkFields: string[];
    decision: string;
    hasEvidenceIntent: boolean;
    policyRuleCount: number;
    usesCheckFields: boolean;
  };
  condition: PolicyCondition;
  localNote: string;
  onChangeLocalNote: (note: string) => void;
  onSaveDraft: () => void;
  onValidate: () => void;
  parsed: ParsedPolicyDsl;
  policyVersionsState:
    | { status: "idle" }
    | { status: "loading" }
    | { status: "error"; message: string }
    | { status: "ready"; versions: PolicyVersionRecord[] };
  saveDisabledReason: string | null;
  saveState: { status: "idle" | "saving" | "success" | "error"; message: string };
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
                  ? `${selectedDraftVersion.status} / not active / not submitted`
                  : "Local only"
              }
            />
            <ReviewRow label="Known versions" value={versionCount} />
            <ReviewRow
              label="Runtime impact"
              value="None until explicit PolicyVersion activation"
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
              value={saveState.status === "idle" ? "No save attempted" : saveState.message}
            />
          </div>
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
        ) : saveState.status === "error" || saveState.status === "success" ? (
          <div className={`ps2-save-state ${saveState.status}`}>
            {saveState.message}
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
          disabled
          title="Submit for review is not wired to a backend lifecycle endpoint in this frontend flow yet."
          type="button"
        >
          Submit for review
        </button>
      </div>
    </aside>
  );
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
