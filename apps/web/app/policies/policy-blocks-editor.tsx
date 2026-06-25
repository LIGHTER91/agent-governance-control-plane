"use client";

import type { CSSProperties } from "react";
import { PolicyBlock } from "./policy-dsl";
import { PolicyIcon, PolicyIconName } from "./policy-icons";

const BLOCK_GROUPS = [
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

const BLOCK_LIBRARY = [
  {
    title: "Events",
    count: 3,
    items: ["AgentActionEvent", "ToolInvocationEvent", "DataTransferIntentEvent"]
  },
  {
    title: "Checks",
    count: 6,
    items: [
      "DataClassificationCheck",
      "DestinationAllowlistCheck",
      "DLPContentCheck",
      "VolumeThresholdCheck",
      "UserContextCheck",
      "TimeWindowCheck"
    ]
  },
  {
    title: "Controls",
    count: 4,
    items: ["DenyAction", "MaskContent", "RequireApproval", "QuarantineData"]
  },
  {
    title: "Proof",
    count: 3,
    items: ["LogDecision", "LogEvidence", "Retention"]
  }
];

export function PolicyBlocksEditor({
  blocks,
  onEditInCode,
  onSelectBlock,
  selectedBlockId
}: {
  blocks: PolicyBlock[];
  onEditInCode: () => void;
  onSelectBlock: (blockId: string) => void;
  selectedBlockId: string | null;
}) {
  return (
    <div className="ps2-block-workbench">
      <aside className="ps2-block-library" aria-label="Block library">
        <div className="ps2-block-library-head">
          <span>Block library</span>
          <button type="button" aria-label="Add custom block">
            <PolicyIcon name="plus" size={13} />
          </button>
        </div>
        <label className="ps2-library-search">
          <PolicyIcon name="search" size={14} />
          <input placeholder="Search blocks" type="search" />
        </label>
        <div className="ps2-library-groups">
          {BLOCK_LIBRARY.map((group) => (
            <section className="ps2-library-group" key={group.title}>
              <div className="ps2-library-group-title">
                <span>{group.title}</span>
                <small>{group.count}</small>
              </div>
              {group.items.map((item) => (
                <button className="ps2-library-item" key={item} type="button">
                  <PolicyIcon name={libraryIcon(group.title)} size={13} />
                  <span>{item}</span>
                  <PolicyIcon name="more" size={13} />
                </button>
              ))}
            </section>
          ))}
        </div>
      </aside>

      <div className="ps2-flow-canvas">
        <div className="ps2-flow-columns">
          {BLOCK_GROUPS.map((group) => {
            const groupBlocks = blocks.filter(
              (block) => block.group === group.key
            );

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
                    <div className="ps2-empty-flow-state">{emptyStateForGroup(group.key)}</div>
                  ) : null}
                  {groupBlocks.map((block) => (
                    <button
                      className={`ps2-flow-block bk-${block.kind} ${
                        selectedBlockId === block.id ? "sel" : ""
                      }`}
                      key={block.id}
                      onClick={() => onSelectBlock(block.id)}
                      type="button"
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
                      <span className="ps2-flow-menu" aria-hidden="true">
                        <PolicyIcon name="more" size={13} />
                      </span>
                    </button>
                  ))}
                </div>
                <button
                  className="ps2-add-flow-block"
                  onClick={onEditInCode}
                  title="Use Code DSL for precise editing in V1"
                  type="button"
                >
                  <PolicyIcon name="plus" size={13} />
                  {group.addLabel} in Code DSL
                </button>
              </section>
            );
          })}
        </div>
      </div>
    </div>
  );
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

function libraryIcon(groupTitle: string): PolicyIconName {
  if (groupTitle === "Events") {
    return "when";
  }
  if (groupTitle === "Checks") {
    return "check";
  }
  if (groupTitle === "Controls") {
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
