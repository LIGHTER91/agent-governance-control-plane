"use client";

import { useState, type CSSProperties } from "react";
import {
  addConditionField,
  conditionFieldDefinition,
  conditionFieldDefinitionsForGroup,
  removeConditionField,
  updateConditionField,
  type ConditionFieldDefinition,
  type ConditionFieldGroup,
  type ConditionValue,
  type PolicyBlock,
  type PolicyCondition
} from "./policy-dsl";
import { PolicyIcon, PolicyIconName } from "./policy-icons";

const CANVAS_GROUPS = [
  {
    key: "when",
    label: "WHEN",
    color: "#8b78f6",
    title: "When",
    addLabel: "Add event"
  },
  {
    key: "check",
    label: "CHECK",
    color: "#65d88f",
    title: "Check",
    addLabel: "Add check"
  },
  {
    key: "then",
    label: "THEN",
    color: "#f0b43a",
    title: "Then",
    addLabel: "Add control"
  },
  {
    key: "prove",
    label: "PROVE",
    color: "#5ea8ff",
    title: "Prove",
    addLabel: "Add proof"
  }
] as const;

export function PolicyCanvas({
  blocks,
  condition,
  onChangeCondition,
  onSelectBlock,
  selectedBlockId
}: {
  blocks: PolicyBlock[];
  condition: PolicyCondition;
  onChangeCondition: (condition: PolicyCondition) => void;
  onSelectBlock: (blockId: string) => void;
  selectedBlockId: string | null;
}) {
  const [activeAddGroup, setActiveAddGroup] =
    useState<ConditionFieldGroup | null>(null);
  const [draftField, setDraftField] = useState("");
  const [draftValue, setDraftValue] = useState<ConditionValue>("");
  const [libraryQuery, setLibraryQuery] = useState("");
  const normalizedLibraryQuery = libraryQuery.trim().toLowerCase();

  function openAddMenu(group: ConditionFieldGroup) {
    const definition = conditionFieldDefinitionsForGroup(group)[0];
    if (!definition) {
      return;
    }
    setActiveAddGroup(group);
    setDraftField(definition.field);
    setDraftValue(definition.defaultValue);
  }

  function addDraftField() {
    const definition = conditionFieldDefinition(draftField);
    if (!definition) {
      return;
    }
    onChangeCondition(addConditionField(condition, definition.field, draftValue));
    onSelectBlock(blockIdForDefinition(definition));
    setActiveAddGroup(null);
  }

  return (
    <div className="ps2-block-workbench">
      <aside className="ps2-block-library" aria-label="Block library">
        <div className="ps2-block-library-head">
          <span>Block library</span>
          <span className="ps2-canvas-badge">Policy Canvas</span>
        </div>
        <label className="ps2-library-search">
          <PolicyIcon name="search" size={14} />
          <input
            onChange={(event) => setLibraryQuery(event.target.value)}
            placeholder="Search blocks"
            type="search"
            value={libraryQuery}
          />
        </label>
        <div className="ps2-library-groups">
          {CANVAS_GROUPS.map((group) => {
            const definitions = conditionFieldDefinitionsForGroup(group.key).filter(
              (definition) => libraryDefinitionMatches(
                definition,
                normalizedLibraryQuery
              )
            );
            return (
              <section className="ps2-library-group" key={group.key}>
                <div className="ps2-library-group-title">
                  <span>{group.title}</span>
                  <small>{definitions.length}</small>
                </div>
                {definitions.length === 0 ? (
                  <div className="ps2-library-empty">No matching blocks</div>
                ) : null}
                {definitions.map((definition) => (
                  <button
                    aria-label={`Add ${definition.label} block`}
                    className="ps2-library-item"
                    key={definition.field}
                    onClick={() => {
                      setActiveAddGroup(group.key);
                      setDraftField(definition.field);
                      setDraftValue(definition.defaultValue);
                    }}
                    title={definition.help}
                    type="button"
                  >
                    <PolicyIcon name={groupIcon(group.key)} size={13} />
                    <span>{definition.label}</span>
                    <PolicyIcon name="plus" size={13} />
                  </button>
                ))}
              </section>
            );
          })}
        </div>
      </aside>

      <div className="ps2-flow-canvas" aria-label="Policy Canvas">
        <div className="ps2-flow-columns">
          {CANVAS_GROUPS.map((group) => {
            const groupBlocks = blocks.filter(
              (block) => block.group === group.key
            );
            const definitions = conditionFieldDefinitionsForGroup(group.key);
            const activeDefinition = conditionFieldDefinition(draftField);

            return (
              <section
                className={`ps2-flow-column flow-${group.key}`}
                key={group.key}
                style={{ "--flow-color": group.color } as CSSProperties}
              >
                <div className="ps2-flow-column-title">
                  <PolicyIcon name={groupIcon(group.key)} size={14} />
                  <span>{group.label}</span>
                  <small>{group.title}</small>
                </div>
                <div className="ps2-flow-stack">
                  {groupBlocks.length === 0 ? (
                    <div className="ps2-empty-flow-state">
                      {emptyStateForGroup(group.key)}
                    </div>
                  ) : null}
                  {groupBlocks.map((block) => (
                    <CanvasNode
                      block={block}
                      condition={condition}
                      key={block.id}
                      onChangeCondition={onChangeCondition}
                      onSelectBlock={onSelectBlock}
                      selected={selectedBlockId === block.id}
                    />
                  ))}
                </div>
                {activeAddGroup === group.key ? (
                  <div className="ps2-add-popover">
                    <label>
                      <span>Field</span>
                      <select
                        onChange={(event) => {
                          const nextDefinition = conditionFieldDefinition(
                            event.target.value
                          );
                          if (!nextDefinition) {
                            return;
                          }
                          setDraftField(nextDefinition.field);
                          setDraftValue(nextDefinition.defaultValue);
                        }}
                        value={draftField}
                      >
                        {definitions.map((definition) => (
                          <option key={definition.field} value={definition.field}>
                            {definition.label}
                          </option>
                        ))}
                      </select>
                    </label>
                    {activeDefinition ? (
                      <PolicyValueControl
                        definition={activeDefinition}
                        onChange={setDraftValue}
                        value={draftValue}
                      />
                    ) : null}
                    <small>
                      {activeDefinition?.help ||
                        "Choose a supported Policy Studio primitive."}
                    </small>
                    <small>
                      Editable before save. Save draft persists the generated
                      PolicyVersion snapshot.
                    </small>
                    <div className="ps2-add-popover-actions">
                      <button onClick={addDraftField} type="button">
                        Add
                      </button>
                      <button
                        onClick={() => setActiveAddGroup(null)}
                        type="button"
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                ) : (
                  <button
                    className="ps2-add-flow-block"
                    onClick={() => openAddMenu(group.key)}
                    title={`${group.addLabel} to the ${group.label} lane`}
                    type="button"
                  >
                    <PolicyIcon name="plus" size={13} />
                    {group.addLabel}
                  </button>
                )}
              </section>
            );
          })}
        </div>
      </div>
    </div>
  );
}

function CanvasNode({
  block,
  condition,
  onChangeCondition,
  onSelectBlock,
  selected
}: {
  block: PolicyBlock;
  condition: PolicyCondition;
  onChangeCondition: (condition: PolicyCondition) => void;
  onSelectBlock: (blockId: string) => void;
  selected: boolean;
}) {
  const definition = block.field ? conditionFieldDefinition(block.field) : null;

  return (
    <div
      className={`ps2-flow-block bk-${block.kind} ${selected ? "sel" : ""}`}
      aria-label={`Select ${block.kind.toUpperCase()} block: ${block.expr}`}
      aria-pressed={selected}
      onKeyDown={(event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          onSelectBlock(block.id);
        }
      }}
      onClick={() => onSelectBlock(block.id)}
      role="button"
      tabIndex={0}
    >
      <span className="ps2-flow-icon" aria-hidden="true">
        <PolicyIcon name={groupIcon(block.group)} size={14} />
      </span>
      <span className="ps2-flow-copy">
        <strong>{block.expr}</strong>
        <small>{block.detail}</small>
      </span>
      <span className={`ps2-flow-status ${block.statusClass}`}>
        {block.status}
      </span>
      {selected && definition ? (
        <div className="ps2-node-editor" onClick={(event) => event.stopPropagation()}>
          <PolicyValueControl
            definition={definition}
            onChange={(value) =>
              onChangeCondition(updateConditionField(condition, definition.field, value))
            }
            value={condition[definition.field] ?? definition.defaultValue}
          />
          {definition.field === "decision" ? (
            <PolicyValueControl
              definition={conditionFieldDefinition("reason") as ConditionFieldDefinition}
              onChange={(value) =>
                onChangeCondition(updateConditionField(condition, "reason", value))
              }
              value={condition.reason || "Policy conditions require human review."}
            />
          ) : null}
          {definition.group !== "then" ? (
            <button
              className="ps2-node-remove"
              onClick={() =>
                onChangeCondition(removeConditionField(condition, definition.field))
              }
              type="button"
              title={`Remove ${definition.label} from this policy draft`}
            >
              Remove
            </button>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

function PolicyValueControl({
  definition,
  onChange,
  value
}: {
  definition: ConditionFieldDefinition;
  onChange: (value: ConditionValue) => void;
  value: ConditionValue;
}) {
  const stringValue = Array.isArray(value) ? value.join(", ") : String(value ?? "");

  return (
    <label className="ps2-value-control">
      <span>{definition.label}</span>
      {definition.valueType === "select" ? (
        <select
          aria-label={definition.label}
          onChange={(event) => onChange(event.target.value)}
          value={stringValue}
        >
          {(definition.options || []).map((option) => (
            <option key={option} value={option}>
              {formatOptionLabel(option)}
            </option>
          ))}
        </select>
      ) : (
        <input
          aria-label={definition.label}
          onChange={(event) => onChange(event.target.value)}
          type={definition.valueType === "number" ? "number" : "text"}
          value={stringValue}
        />
      )}
    </label>
  );
}

function blockIdForDefinition(definition: ConditionFieldDefinition) {
  if (definition.group === "then") {
    return "then-decision";
  }
  if (definition.group === "prove") {
    return "prove-evidence";
  }
  return `${definition.group}-${definition.field}`;
}

function groupIcon(group: PolicyBlock["group"]): PolicyIconName {
  if (group === "when") {
    return "when";
  }
  if (group === "check") {
    return "check";
  }
  if (group === "then") {
    return "then";
  }
  return "prove";
}

function emptyStateForGroup(group: PolicyBlock["group"]) {
  if (group === "when") {
    return "No WHEN fields";
  }
  if (group === "check") {
    return "No metadata checks";
  }
  if (group === "then") {
    return "No decision yet";
  }
  return "Evidence intent only";
}

function libraryDefinitionMatches(
  definition: ConditionFieldDefinition,
  normalizedQuery: string
) {
  if (!normalizedQuery) {
    return true;
  }
  return `${definition.label} ${definition.field} ${definition.help}`
    .toLowerCase()
    .includes(normalizedQuery);
}

function formatOptionLabel(value: string) {
  return value
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}
