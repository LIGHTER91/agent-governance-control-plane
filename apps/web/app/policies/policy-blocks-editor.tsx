"use client";

import type { ConditionValue, PolicyBlock, PolicyCondition } from "./policy-dsl";
import { conditionToBlocksViewModel, updateConditionField } from "./policy-dsl";

const BLOCK_GROUPS = [
  { key: "when", label: "WHEN", color: "#8b78f6", desc: "runtime match" },
  { key: "check", label: "CHECK", color: "#38b4f5", desc: "required facts" },
  { key: "then", label: "THEN", color: "#f0873a", desc: "decision" },
  { key: "prove", label: "PROVE", color: "#22d37a", desc: "evidence" }
] as const;

export function PolicyBlocksEditor({
  blocks,
  condition,
  onChangeCondition,
  onSelectBlock,
  selectedBlockId,
  unsupportedDslLines,
  unsupportedFieldNames
}: {
  blocks: PolicyBlock[];
  condition: PolicyCondition;
  onChangeCondition: (condition: PolicyCondition) => void;
  onSelectBlock: (blockId: string) => void;
  selectedBlockId: string | null;
  unsupportedDslLines: string[];
  unsupportedFieldNames: string[];
}) {
  const viewModel = conditionToBlocksViewModel(condition);
  const editingBlocked =
    unsupportedDslLines.length > 0 || unsupportedFieldNames.length > 0;

  function handleFieldChange(field: string, value: ConditionValue | null) {
    onChangeCondition(updateConditionField(condition, field, value));
  }

  return (
    <div className="ps2-block-list">
      <div className="ps2-block-editor-note">
        <strong>Blocks edit the same compiled policy condition as Code DSL.</strong>
        <span>
          Editable WHEN, Editable CHECK, and Editable THEN fields update Code
          DSL preview. Save draft stores current editor state as a PolicyVersion snapshot. Draft versions do not affect runtime until reviewed and activated.
        </span>
      </div>
      {editingBlocked ? (
        <div className="ps2-block-warning">
          Blocks editing is guarded because this editor state contains unsupported
          DSL lines or backend fields not represented in Blocks. Switch to Code
          DSL and remove unsupported syntax before saving.
        </div>
      ) : null}
      {BLOCK_GROUPS.map((group, groupIndex) => {
        const groupBlocks = blocks.filter((block) => block.group === group.key);
        const editableFields =
          group.key === "when"
            ? viewModel.whenFields
            : group.key === "check"
              ? viewModel.checkFields
              : [];

        return (
          <div className="ps2-block-group" key={group.key}>
            {groupIndex > 0 ? (
              <div className="ps2-spacer" style={{ color: group.color }}>
                enforced
              </div>
            ) : null}
            <div className="ps2-block-group-label" style={{ color: group.color }}>
              {group.label}
              <span className="ps2-group-line" />
              <span className="ps2-group-sub">{group.desc}</span>
            </div>
            {editableFields.length > 0 ? (
              <div className="ps2-block-field-grid">
                {editableFields.map((field) => (
                  <BlockFieldControl
                    disabled={editingBlocked}
                    field={field}
                    key={field.key}
                    onChange={handleFieldChange}
                  />
                ))}
              </div>
            ) : null}
            {group.key === "then" ? (
              <ThenEditor
                condition={condition}
                disabled={editingBlocked}
                onChange={handleFieldChange}
              />
            ) : null}
            {group.key === "prove" ? (
              <div className="ps2-prove-copy">{viewModel.prove}</div>
            ) : null}
            {groupBlocks.map((block) => (
              <button
                className={`ps2-block bk-${block.kind} ${
                  selectedBlockId === block.id ? "sel" : ""
                }`}
                key={block.id}
                onClick={() => onSelectBlock(block.id)}
                type="button"
              >
                <span className="ps2-block-accent" />
                <span className="ps2-block-inner">
                  <span className="ps2-block-type">{block.kind.toUpperCase()}</span>
                  <span className="ps2-block-body">
                    <span className="ps2-block-expr">{block.expr}</span>
                    <span className="ps2-block-detail">{block.detail}</span>
                  </span>
                  <span className={`ps2-block-st ${block.statusClass}`}>
                    {block.status}
                  </span>
                </span>
              </button>
            ))}
            <div className="ps2-add-block">
              <span aria-hidden="true">+</span>
              Editable {group.label} fields compile into deterministic JSON
            </div>
          </div>
        );
      })}
    </div>
  );
}

function BlockFieldControl({
  disabled,
  field,
  onChange
}: {
  disabled: boolean;
  field: {
    detail: string;
    input: "text" | "select" | "boolean" | "string_list" | "number";
    key: string;
    label: string;
    options?: string[];
    value?: ConditionValue;
  };
  onChange: (field: string, value: ConditionValue | null) => void;
}) {
  return (
    <label className="ps2-block-field">
      <span className="ps2-block-field-label">{field.label}</span>
      <span className="ps2-block-field-detail">{field.detail}</span>
      {field.input === "select" ? (
        <select
          disabled={disabled}
          onChange={(event) => onChange(field.key, event.target.value || null)}
          value={typeof field.value === "string" ? field.value : ""}
        >
          <option value="">not set</option>
          {(field.options || []).map((option) => (
            <option key={option} value={option}>
              {option}
            </option>
          ))}
        </select>
      ) : null}
      {field.input === "boolean" ? (
        <select
          disabled={disabled}
          onChange={(event) =>
            onChange(
              field.key,
              event.target.value === ""
                ? null
                : event.target.value === "true"
            )
          }
          value={typeof field.value === "boolean" ? String(field.value) : ""}
        >
          <option value="">not set</option>
          <option value="true">true</option>
          <option value="false">false</option>
        </select>
      ) : null}
      {field.input === "string_list" ? (
        <input
          disabled={disabled}
          onChange={(event) => onChange(field.key, parseStringList(event.target.value))}
          placeholder="source_a, source_b"
          type="text"
          value={Array.isArray(field.value) ? field.value.join(", ") : ""}
        />
      ) : null}
      {field.input === "number" ? (
        <input
          disabled={disabled}
          max={1}
          min={0}
          onChange={(event) =>
            onChange(
              field.key,
              event.target.value === "" ? null : Number(event.target.value)
            )
          }
          step={0.01}
          type="number"
          value={typeof field.value === "number" ? String(field.value) : ""}
        />
      ) : null}
      {field.input === "text" ? (
        <input
          disabled={disabled}
          onChange={(event) => onChange(field.key, event.target.value || null)}
          type="text"
          value={typeof field.value === "string" ? field.value : ""}
        />
      ) : null}
    </label>
  );
}

function ThenEditor({
  condition,
  disabled,
  onChange
}: {
  condition: PolicyCondition;
  disabled: boolean;
  onChange: (field: string, value: ConditionValue | null) => void;
}) {
  return (
    <div className="ps2-then-grid">
      <label className="ps2-block-field">
        <span className="ps2-block-field-label">decision</span>
        <span className="ps2-block-field-detail">Runtime decision returned by AGCP</span>
        <select
          disabled={disabled}
          onChange={(event) => onChange("decision", event.target.value)}
          value={String(condition.decision || "require_human_review")}
        >
          <option value="allow">allow</option>
          <option value="deny">deny</option>
          <option value="require_human_review">require_human_review</option>
          <option value="not_applicable">not_applicable</option>
        </select>
      </label>
      <label className="ps2-block-field ps2-block-field-wide">
        <span className="ps2-block-field-label">reason</span>
        <span className="ps2-block-field-detail">
          Required reason persisted in the compiled condition
        </span>
        <textarea
          disabled={disabled}
          onChange={(event) => onChange("reason", event.target.value)}
          rows={2}
          value={String(condition.reason || "")}
        />
      </label>
    </div>
  );
}

function parseStringList(value: string) {
  const values = value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
  return values.length > 0 ? values : null;
}
