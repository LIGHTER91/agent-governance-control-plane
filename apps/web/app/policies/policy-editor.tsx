"use client";

import type {
  PolicyBlock,
  PolicyValidationMessage,
  PolicyValidationMessageTone
} from "./policy-dsl";
import { PolicyBlocksEditor } from "./policy-blocks-editor";
import { PolicyCodeEditor } from "./policy-code-editor";
import { PolicyIcon } from "./policy-icons";

type EditorMode = "blocks" | "code";

export function PolicyEditor({
  blocks,
  compiled,
  dsl,
  editorMode,
  policyDescription,
  policyStatus,
  policyTitle,
  policyVersion,
  validationRunCount,
  onChangeDsl,
  onSaveDraft,
  onSelectBlock,
  onSetEditorMode,
  onSubmitReview,
  onValidate,
  saveDisabledReason,
  selectedBlockId,
  validationMessages
}: {
  blocks: PolicyBlock[];
  compiled: {
    checkFields: string[];
    decision: string;
    hasEvidenceIntent: boolean;
    policyRuleCount: number;
    usesCheckFields: boolean;
  };
  dsl: string;
  editorMode: EditorMode;
  policyDescription: string;
  policyStatus: string;
  policyTitle: string;
  policyVersion: string;
  validationRunCount: number;
  onChangeDsl: (dsl: string) => void;
  onSaveDraft: () => void;
  onSelectBlock: (blockId: string) => void;
  onSetEditorMode: (mode: EditorMode) => void;
  onSubmitReview: () => void;
  onValidate: () => void;
  saveDisabledReason: string | null;
  selectedBlockId: string | null;
  validationMessages: PolicyValidationMessage[];
}) {
  const counts = {
    check: blocks.filter((block) => block.group === "check").length,
    prove: blocks.filter((block) => block.group === "prove").length,
    then: blocks.filter((block) => block.group === "then").length,
    when: blocks.filter((block) => block.group === "when").length
  };
  const firstWhenDetail =
    blocks.find((block) => block.group === "when")?.detail || "No WHEN fields";
  const structureSteps = [
    {
      id: "when",
      icon: "when" as const,
      label: "WHEN",
      className: "s-when",
      body: firstWhenDetail
    },
    {
      id: "check",
      icon: "check" as const,
      label: "CHECK",
      className: "s-check",
      body:
        counts.check > 0
          ? `${counts.check} metadata/check fact${counts.check === 1 ? "" : "s"}`
          : "No metadata checks"
    },
    {
      id: "then",
      icon: "then" as const,
      label: "THEN",
      className: "s-then",
      body:
        compiled.decision === "uncompiled"
          ? "No decision yet"
          : `Decision: ${compiled.decision.replace(/_/g, " ")}`
    },
    {
      id: "prove",
      icon: "prove" as const,
      label: "PROVE",
      className: "s-prove",
      body: "Evidence intent only"
    }
  ];

  return (
    <main className="ps2-editor-pane" aria-label="Policy IDE editor">
      <div className="ps2-product-topbar">
        <div className="ps2-product-title">
          <span className="ps2-policy-glyph" aria-hidden="true">
            <PolicyIcon name="code" size={14} />
          </span>
          <span>
            <strong>Policy Studio Refinement</strong>
            <small>Agent Governance Control Plane</small>
          </span>
        </div>
      </div>

      <header className="ps2-policy-header">
        <div className="ps2-policy-title-row">
          <div className="ps2-policy-title-copy">
            <div className="ps2-policy-name-line">
              <h1>{policyTitle}</h1>
              <span className={`chip ${policyStatusChipClass(policyStatus)}`}>
                {formatPolicyStatus(policyStatus)}
              </span>
              <span className="ps2-version-pill">{policyVersion}</span>
            </div>
            <p>{policyDescription}</p>
          </div>
          <div className="ps2-policy-actions" aria-label="Policy actions">
            <button
              className="ps2-header-btn"
              disabled={Boolean(saveDisabledReason)}
              onClick={onSaveDraft}
              title={saveDisabledReason || "Save draft"}
              type="button"
            >
              <PolicyIcon name="save" size={14} />
              Save draft
            </button>
            <button
              className="ps2-header-btn primary"
              onClick={onSubmitReview}
              type="button"
            >
              <PolicyIcon name="send" size={14} />
              Submit for review
            </button>
            <button className="ps2-header-icon" type="button" aria-label="More actions">
              <PolicyIcon name="more" size={14} />
            </button>
          </div>
        </div>
      </header>

      <section className="ps2-structure-panel" aria-label="Policy structure">
        <div className="ps2-structure-head">
          <span className="ps2-struct-lbl">Policy structure</span>
          <button className="ps2-structure-view" type="button">View structure</button>
        </div>
        <div className="ps2-structure-flow">
          {structureSteps.map((step, index) => (
            <span key={step.id} className="ps2-structure-wrap">
              {index > 0 ? (
                <span className="ps2-step-sep" aria-hidden="true">
                  <PolicyIcon name="arrowRight" size={18} />
                </span>
              ) : null}
              <span className={`ps2-structure-card ${step.className}`}>
                <span className="ps2-step-count">
                  <PolicyIcon name={step.icon} size={15} />
                </span>
                <span className="ps2-structure-copy">
                  <strong>{step.label}</strong>
                  <span>{step.body}</span>
                </span>
              </span>
            </span>
          ))}
        </div>
      </section>

      <div className="ps2-editor-toolbar">
        <div className="ps2-editor-toggle">
          <button
            className={`ps2-etbtn ${editorMode === "blocks" ? "on-blocks" : ""}`}
            onClick={() => onSetEditorMode("blocks")}
            type="button"
          >
            <PolicyIcon name="blocks" size={13} />
            Blocks
          </button>
          <button
            className={`ps2-etbtn ${editorMode === "code" ? "on-code" : ""}`}
            onClick={() => onSetEditorMode("code")}
            type="button"
          >
            <PolicyIcon name="code" size={13} />
            Code DSL
          </button>
        </div>
        <div className="ps2-canvas-tools" aria-hidden="true">
          <span><PolicyIcon name="arrowRight" size={13} /></span>
          <span><PolicyIcon name="zoom" size={13} /></span>
          <span>100%</span>
          <span><PolicyIcon name="expand" size={13} /></span>
        </div>
      </div>

      <div
        className={`ps2-editor-scroll ${
          editorMode === "blocks" ? "blocks-mode" : "code-mode"
        }`}
      >
        {editorMode === "blocks" ? (
          <PolicyBlocksEditor
            blocks={blocks}
            onEditInCode={() => onSetEditorMode("code")}
            onSelectBlock={onSelectBlock}
            selectedBlockId={selectedBlockId}
          />
        ) : (
          <PolicyCodeEditor
            dsl={dsl}
            onChange={onChangeDsl}
            policyTitle={policyTitle}
            policyVersion={policyVersion}
          />
        )}
      </div>

      <CompileBar compiled={compiled} />
      <ValidationConsole
        onValidate={onValidate}
        validationRunCount={validationRunCount}
        validationMessages={validationMessages}
      />
    </main>
  );
}

function policyStatusChipClass(status: string) {
  const normalized = status.toLowerCase();
  if (normalized === "active") {
    return "chip-active";
  }
  if (normalized === "draft" || normalized === "local_draft") {
    return "chip-draft";
  }
  if (normalized === "disabled" || normalized.includes("review")) {
    return "chip-review";
  }
  return "chip-unsaved";
}

function formatPolicyStatus(status: string) {
  return status
    .split(/[_\s-]+/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function CompileBar({
  compiled
}: {
  compiled: {
    checkFields: string[];
    decision: string;
    hasEvidenceIntent: boolean;
    policyRuleCount: number;
    usesCheckFields: boolean;
  };
}) {
  const shape = compileBarShape(compiled);

  return (
    <div className="ps2-compile-bar">
      <span aria-hidden="true">OK</span>
      <span>Compilation</span>
      <div className="ps2-compile-pills">
        {shape.map((item) => (
          <span className={`ps2-co-pill chip ${item.className}`} key={item.text}>
            {item.text}
          </span>
        ))}
      </div>
      <button className="ps2-compile-action" type="button">Compile</button>
    </div>
  );
}

function ValidationConsole({
  onValidate,
  validationRunCount,
  validationMessages
}: {
  onValidate: () => void;
  validationRunCount: number;
  validationMessages: PolicyValidationMessage[];
}) {
  const hasRun = validationRunCount > 0;
  const visibleMessages = hasRun ? validationMessages : [];
  const counts = visibleMessages.reduce(
    (accumulator, message) => {
      accumulator.all += 1;
      if (message.tone === "blocking") {
        accumulator.errors += 1;
      } else if (message.tone === "attention") {
        accumulator.warnings += 1;
      } else {
        accumulator.info += 1;
      }
      return accumulator;
    },
    { all: 0, errors: 0, info: 0, warnings: 0 }
  );

  return (
    <div className="ps2-sim">
      <div className="ps2-sim-head">
        <div className="ps2-sim-title-group">
          <span className="ps2-sim-title">LOCAL VALIDATION CONSOLE</span>
          <span className="ps2-sim-help">
            Local validation only. Validate does not save, submit for review, or
            execute runtime decisions. Save draft persists a PolicyVersion draft.
          </span>
        </div>
        <div className="ps2-console-tabs">
          <button type="button">All <b>{counts.all}</b></button>
          <button type="button">Errors <b>{counts.errors}</b></button>
          <button type="button">Warnings <b>{counts.warnings}</b></button>
          <button type="button">Info <b>{counts.info}</b></button>
        </div>
        <button className="ps2-sim-run" onClick={onValidate} type="button">Validate</button>
      </div>
      <div className="ps2-validation-grid" role="table" aria-label="Local validation messages">
        <div className="ps2-validation-row head" role="row">
          <span>Type</span>
          <span>Code</span>
          <span>Message</span>
          <span>Location</span>
        </div>
        {visibleMessages.length === 0 ? (
          <div className="ps2-validation-row ps2-validation-empty" role="row">
            <span className="ps2-sim-info">
              <PolicyIcon name="info" size={13} />
              Info
            </span>
            <span>-</span>
            <span>
              {hasRun
                ? "No local validation messages for the current editor state."
                : "Validation has not run yet."}
            </span>
            <span>-</span>
          </div>
        ) : null}
        {visibleMessages.map((message, index) => {
          const code = validationCode(message.tone, index);
          return (
            <div className="ps2-validation-row" key={`${code}-${index}`} role="row">
              <span className={messageClass(message.tone)}>
                <PolicyIcon name={validationIcon(message.tone)} size={13} />
                {validationTypeLabel(message.tone)}
              </span>
              <span>{code}</span>
              <span>{message.text}</span>
              <span>-</span>
            </div>
          );
        })}
      </div>
      <div className="ps2-validation-footer">
        <span>
          {validationRunCount > 0
            ? "OK Local validation completed"
            : "Local validation not run"}
        </span>
        <span>Current editor state</span>
        <span>Local only</span>
      </div>
    </div>
  );
}

function compileBarShape(compiled: {
  checkFields: string[];
  decision: string;
  hasEvidenceIntent: boolean;
  policyRuleCount: number;
  usesCheckFields: boolean;
}) {
  return [
    {
      className: compiled.policyRuleCount > 0 ? "chip-vio" : "chip-unsaved",
      text: `${compiled.policyRuleCount} PolicyRule`
    },
    {
      className: compiled.usesCheckFields ? "chip-review" : "chip-unsaved",
      text: compiled.usesCheckFields
        ? "Uses check outcome fields"
        : "No check fields"
    },
    {
      className:
        compiled.decision === "allow"
          ? "chip-active"
          : compiled.decision === "deny"
            ? "chip-unsaved"
            : "chip-draft",
      text: `Policy decision: ${compiled.decision}`
    },
    {
      className: compiled.hasEvidenceIntent ? "chip-active" : "chip-review",
      text: compiled.hasEvidenceIntent
        ? "Evidence metadata available"
        : "Evidence intent local only"
    },
    {
      className: "chip-review",
      text: "Compiled locally from editor state"
    },
    {
      className: "chip-draft",
      text: "Not active"
    }
  ];
}

function consoleMessageGroups(messages: PolicyValidationMessage[]) {
  const groupOrder: Array<{
    label: string;
    tone: PolicyValidationMessageTone;
  }> = [
    { label: "Success", tone: "success" },
    { label: "Info", tone: "info" },
    { label: "Attention", tone: "attention" },
    { label: "Blocking", tone: "blocking" }
  ];

  return groupOrder
    .map((group) => ({
      ...group,
      messages: messages.filter((message) => message.tone === group.tone)
    }))
    .filter((group) => group.messages.length > 0);
}

function messageClass(tone: PolicyValidationMessageTone) {
  if (tone === "success") {
    return "ps2-sim-ok";
  }
  if (tone === "attention") {
    return "ps2-sim-warn";
  }
  if (tone === "blocking") {
    return "ps2-sim-blocking";
  }
  return "ps2-sim-info";
}

function validationTypeLabel(tone: PolicyValidationMessageTone) {
  if (tone === "blocking") {
    return "Error";
  }
  if (tone === "attention") {
    return "Warning";
  }
  if (tone === "success") {
    return "Info";
  }
  return "Info";
}

function validationCode(tone: PolicyValidationMessageTone, index: number) {
  const prefix =
    tone === "blocking"
      ? "100"
      : tone === "attention"
        ? "200"
        : tone === "success"
          ? "300"
          : "400";
  return `LOCAL-VAL-${prefix}${String(index + 1).padStart(2, "0")}`;
}

function validationIcon(tone: PolicyValidationMessageTone) {
  if (tone === "blocking") {
    return "error" as const;
  }
  if (tone === "attention") {
    return "warning" as const;
  }
  if (tone === "success") {
    return "check" as const;
  }
  return "info" as const;
}

function messageSymbolForTone(tone: PolicyValidationMessageTone) {
  if (tone === "success") {
    return "OK";
  }
  if (tone === "attention") {
    return "!";
  }
  if (tone === "blocking") {
    return "x";
  }
  return "i";
}
