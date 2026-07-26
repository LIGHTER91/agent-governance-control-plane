"use client";

import type { PolicyBlock, PolicyCondition } from "./policy-dsl";
import type {
  PolicyCheckDraft,
  PolicyCheckValidation
} from "./policy-check-authoring";
import { PolicyCanvas } from "./policy-canvas";

export function PolicyBlocksEditor({
  blocks,
  checks,
  checkValidationById,
  condition,
  onAddCheck,
  onChangeCondition,
  onSelectCheck,
  onSelectBlock,
  selectedCheckId,
  selectedBlockId
}: {
  blocks: PolicyBlock[];
  checks: PolicyCheckDraft[];
  checkValidationById: Map<string, PolicyCheckValidation>;
  condition: PolicyCondition;
  onAddCheck: () => void;
  onChangeCondition: (condition: PolicyCondition) => void;
  onSelectCheck: (checkId: string) => void;
  onSelectBlock: (blockId: string) => void;
  selectedCheckId: string | null;
  selectedBlockId: string | null;
}) {
  return (
    <PolicyCanvas
      blocks={blocks}
      checks={checks}
      checkValidationById={checkValidationById}
      condition={condition}
      onAddCheck={onAddCheck}
      onChangeCondition={onChangeCondition}
      onSelectCheck={onSelectCheck}
      onSelectBlock={onSelectBlock}
      selectedCheckId={selectedCheckId}
      selectedBlockId={selectedBlockId}
    />
  );
}
