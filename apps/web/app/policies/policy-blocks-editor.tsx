"use client";

import type { PolicyBlock, PolicyCondition } from "./policy-dsl";
import { PolicyCanvas } from "./policy-canvas";

export function PolicyBlocksEditor({
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
  return (
    <PolicyCanvas
      blocks={blocks}
      condition={condition}
      onChangeCondition={onChangeCondition}
      onSelectBlock={onSelectBlock}
      selectedBlockId={selectedBlockId}
    />
  );
}
