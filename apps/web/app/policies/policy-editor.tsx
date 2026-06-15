"use client";

import type {
  PolicyBlock,
  PolicyValidationMessage,
  PolicyValidationMessageTone
} from "./policy-dsl";
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
  validationMessages: PolicyValidationMessage[];
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
  validationMessages: PolicyValidationMessage[];
}) {
  const groupedMessages = consoleMessageGroups(validationMessages);

  return (
    <div className="ps2-sim">
      <div className="ps2-sim-head">
        <div className="ps2-sim-title-group">
          <span className="ps2-sim-title">// LOCAL VALIDATION CONSOLE - Local validation only</span>
          <span className="ps2-sim-help">
            Validate does not save, submit for review, or simulate production runtime.
            Save draft persists a PolicyVersion draft.
          </span>
        </div>
        <button className="ps2-sim-run" onClick={onValidate} type="button">
          Validate
        </button>
      </div>
      <div className="ps2-sim-body">
        {groupedMessages.map((group) => (
          <div className="ps2-sim-group" key={group.tone}>
            <div className={`ps2-sim-group-title ${messageClass(group.tone)}`}>
              {group.label}
            </div>
            {group.messages.map((message, index) => (
              <div
                className={`ps2-sim-line ${messageClass(message.tone)}`}
                key={`${message.text}-${index}`}
              >
                <span className="ps2-sym">{messageSymbolForTone(message.tone)}</span>
                <span>{message.text}</span>
              </div>
            ))}
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

function messageSymbolForTone(tone: PolicyValidationMessageTone) {
  if (tone === "success") {
    return messageSymbol("ok");
  }
  if (tone === "attention") {
    return messageSymbol("warn");
  }
  if (tone === "blocking") {
    return "x";
  }
  return messageSymbol("info");
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
