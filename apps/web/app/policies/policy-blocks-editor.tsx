"use client";

import { PolicyBlock } from "./policy-dsl";

const BLOCK_GROUPS = [
  { key: "when", label: "WHEN", color: "#8b78f6", desc: "runtime match" },
  { key: "check", label: "CHECK", color: "#38b4f5", desc: "required facts" },
  { key: "then", label: "THEN", color: "#f0873a", desc: "decision" },
  { key: "prove", label: "PROVE", color: "#22d37a", desc: "evidence" }
] as const;

export function PolicyBlocksEditor({
  blocks,
  onSelectBlock,
  selectedBlockId
}: {
  blocks: PolicyBlock[];
  onSelectBlock: (blockId: string) => void;
  selectedBlockId: string | null;
}) {
  return (
    <div className="ps2-block-list">
      {BLOCK_GROUPS.map((group, groupIndex) => {
        const groupBlocks = blocks.filter((block) => block.group === group.key);

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
              Edit {group.label} fields in Code DSL
            </div>
          </div>
        );
      })}
    </div>
  );
}
