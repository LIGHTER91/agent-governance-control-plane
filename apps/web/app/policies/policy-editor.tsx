"use client";

import type { PolicyBlock } from "./policy-dsl";
import { PolicyBlocksEditor } from "./policy-blocks-editor";
import { PolicyCodeEditor } from "./policy-code-editor";

type EditorMode = "blocks" | "code";

export function PolicyEditor({
  blocks,
  compiled,
  dsl,
  editorMode,
  onChangeDsl,
  onSelectBlock,
  onSetEditorMode,
  onValidate,
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
  onChangeDsl: (dsl: string) => void;
  onSelectBlock: (blockId: string) => void;
  onSetEditorMode: (mode: EditorMode) => void;
  onValidate: () => void;
  selectedBlockId: string | null;
  validationMessages: Array<{ tone: "ok" | "warn" | "error" | "info"; text: string }>;
}) {
  const counts = {
    check: blocks.filter((block) => block.group === "check").length,
    prove: blocks.filter((block) => block.group === "prove").length,
    then: blocks.filter((block) => block.group === "then").length,
    when: blocks.filter((block) => block.group === "when").length
  };

  return (
    <main className="ps2-editor-pane" aria-label="Policy IDE editor">
      <div className="ps2-struct-bar">
        <span className="ps2-struct-lbl">policy structure</span>
        {[
          { id: "when", label: "WHEN", className: "s-when", count: counts.when },
          {
            id: "check",
            label: "CHECK",
            className: "s-check",
            count: counts.check
          },
          { id: "then", label: "THEN", className: "s-then", count: counts.then },
          {
            id: "prove",
            label: "PROVE",
            className: "s-prove",
            count: counts.prove
          }
        ].map((step, index) => (
          <span key={step.id} className="ps2-step-wrap">
            {index > 0 ? <span className="ps2-step-sep">→</span> : null}
            <span className={`ps2-step ${step.className} active`}>
              <span className="ps2-step-count">{step.count}</span>
              {step.label}
            </span>
          </span>
        ))}
        <div className="ps2-editor-toggle">
          <button
            className={`ps2-etbtn ${editorMode === "blocks" ? "on-blocks" : ""}`}
            onClick={() => onSetEditorMode("blocks")}
            type="button"
          >
            Blocks
          </button>
          <button
            className={`ps2-etbtn ${editorMode === "code" ? "on-code" : ""}`}
            onClick={() => onSetEditorMode("code")}
            type="button"
          >
            Code DSL
          </button>
        </div>
      </div>

      <div className="ps2-editor-scroll">
        {editorMode === "blocks" ? (
          <PolicyBlocksEditor
            blocks={blocks}
            onEditInCode={() => onSetEditorMode("code")}
            onSelectBlock={onSelectBlock}
            selectedBlockId={selectedBlockId}
          />
        ) : (
          <PolicyCodeEditor dsl={dsl} onChange={onChangeDsl} />
        )}
      </div>

      <CompileBar compiled={compiled} />
      <ValidationConsole
        onValidate={onValidate}
        validationMessages={validationMessages}
      />
    </main>
  );
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
      <span aria-hidden="true">✓</span>
      <span>Compiles to</span>
      <div className="ps2-compile-pills">
        {shape.map((item) => (
          <span className={`ps2-co-pill chip ${item.className}`} key={item.text}>
            {item.text}
          </span>
        ))}
      </div>
    </div>
  );
}

function ValidationConsole({
  onValidate,
  validationMessages
}: {
  onValidate: () => void;
  validationMessages: Array<{ tone: "ok" | "warn" | "error" | "info"; text: string }>;
}) {
  return (
    <div className="ps2-sim">
      <div className="ps2-sim-head">
        <span className="ps2-sim-title">// LOCAL VALIDATION CONSOLE - Local validation only</span>
        <button className="ps2-sim-run" onClick={onValidate} type="button">
          Validate
        </button>
      </div>
      <div className="ps2-sim-body">
        {validationMessages.map((message, index) => (
          <div
            className={`ps2-sim-line ${messageClass(message.tone)}`}
            key={`${message.text}-${index}`}
          >
            <span className="ps2-sym">{messageSymbol(message.tone)}</span>
            <span>{message.text}</span>
          </div>
        ))}
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
      text: `Runtime decision: ${compiled.decision}`
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
      text: "Not published"
    }
  ];
}

function messageClass(tone: "ok" | "warn" | "error" | "info") {
  if (tone === "ok") {
    return "ps2-sim-ok";
  }
  if (tone === "warn" || tone === "error") {
    return "ps2-sim-warn";
  }
  return "ps2-sim-info";
}

function messageSymbol(tone: "ok" | "warn" | "error" | "info") {
  if (tone === "ok") {
    return "✓";
  }
  if (tone === "warn" || tone === "error") {
    return "!";
  }
  return "i";
}
