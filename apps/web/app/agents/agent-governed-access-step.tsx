import type { AgentGovernanceProfileAccessGrant } from "../lib/agents";
import type {
  InventoryState,
  InventoryTarget,
  ProposedAccessGrant,
  ProposedGrantErrors,
  ProposedGrantField
} from "./agent-governance-model";
import {
  AgentBoundaryNote,
  AgentStepHeader
} from "./agent-form-controls";
import { AgentAccessTargetPicker } from "./agent-access-target-picker";
import { AgentExistingGrants } from "./agent-existing-grants";

export function AgentGovernedAccessStep({
  existingGrants,
  existingTargetKeys,
  inventory,
  showExistingGrants,
  proposalErrors,
  proposals,
  onRetryInventory,
  onToggleTarget,
  onUpdateProposal
}: {
  existingGrants: AgentGovernanceProfileAccessGrant[];
  existingTargetKeys: Set<string>;
  inventory: InventoryState;
  showExistingGrants: boolean;
  proposalErrors: ProposedGrantErrors;
  proposals: ProposedAccessGrant[];
  onRetryInventory: () => void;
  onToggleTarget: (target: InventoryTarget) => void;
  onUpdateProposal: (
    targetKey: string,
    field: ProposedGrantField,
    value: string
  ) => void;
}) {
  return (
    <section className="agent-step-panel" aria-labelledby="agent-access-title">
      <AgentStepHeader
        id="agent-governed-access-title"
        step="Step 4 of 5"
        title="Governed Access"
        description="Select real governed inventory and prepare declarative Access Grants."
      />

      <AgentBoundaryNote title="Governance declaration boundary" tone="warning">
        Access Grants record declared governance intent. They do not provision
        credentials or enforce cloud permissions.
      </AgentBoundaryNote>

      {showExistingGrants ? (
        <AgentExistingGrants grants={existingGrants} />
      ) : null}

      <div className="agent-target-groups">
        <AgentAccessTargetPicker
          existingTargetKeys={existingTargetKeys}
          label="Capabilities"
          proposalErrors={proposalErrors}
          proposals={proposals}
          state={inventory.capabilities}
          onRetry={onRetryInventory}
          onToggle={onToggleTarget}
          onUpdate={onUpdateProposal}
        />
        <AgentAccessTargetPicker
          existingTargetKeys={existingTargetKeys}
          label="Sources"
          proposalErrors={proposalErrors}
          proposals={proposals}
          state={inventory.sources}
          onRetry={onRetryInventory}
          onToggle={onToggleTarget}
          onUpdate={onUpdateProposal}
        />
        <AgentAccessTargetPicker
          existingTargetKeys={existingTargetKeys}
          label="Models"
          proposalErrors={proposalErrors}
          proposals={proposals}
          state={inventory.models}
          onRetry={onRetryInventory}
          onToggle={onToggleTarget}
          onUpdate={onUpdateProposal}
        />
      </div>
    </section>
  );
}
