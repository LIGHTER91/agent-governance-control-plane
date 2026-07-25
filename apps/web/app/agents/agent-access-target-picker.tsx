import Link from "next/link";
import type {
  InventoryTarget,
  ProposedAccessGrant,
  ProposedGrantErrors,
  ProposedGrantField,
  ResourceState,
  RiskLevel
} from "./agent-governance-model";
import {
  formatGovernanceValue,
  RISK_LEVELS
} from "./agent-governance-model";
import {
  AgentField,
  AgentStatusBadge
} from "./agent-form-controls";

export function AgentAccessTargetPicker({
  existingTargetKeys,
  label,
  proposals,
  proposalErrors,
  state,
  onRetry,
  onToggle,
  onUpdate
}: {
  existingTargetKeys: Set<string>;
  label: string;
  proposals: ProposedAccessGrant[];
  proposalErrors: ProposedGrantErrors;
  state: ResourceState<InventoryTarget[]>;
  onRetry: () => void;
  onToggle: (target: InventoryTarget) => void;
  onUpdate: (
    targetKey: string,
    field: ProposedGrantField,
    value: string
  ) => void;
}) {
  if (state.status === "loading") {
    return (
      <section className="agent-target-group" aria-live="polite">
        <header>
          <h3>{label}</h3>
        </header>
        <div className="agent-inline-state">
          <strong>Loading {label.toLowerCase()}</strong>
          <p>Requesting real governed inventory from the backend.</p>
        </div>
      </section>
    );
  }

  if (state.status === "error") {
    return (
      <section className="agent-target-group">
        <header>
          <h3>{label}</h3>
        </header>
        <div className="agent-inline-state error" role="alert">
          <strong>Unable to load {label.toLowerCase()}</strong>
          <p>{state.message}</p>
          <button type="button" onClick={onRetry}>
            Retry inventory
          </button>
        </div>
      </section>
    );
  }

  if (state.data.length === 0) {
    return (
      <section className="agent-target-group">
        <header>
          <h3>{label}</h3>
          <span>0 available</span>
        </header>
        <div className="agent-inline-state">
          <strong>No {label.toLowerCase()} exist</strong>
          <p>
            Inventory records must exist before access can be declared in this
            workflow.
          </p>
          <Link href="/access-data">Open Access &amp; Data</Link>
        </div>
      </section>
    );
  }

  const proposalByKey = new Map(
    proposals.map((proposal) => [proposal.target.key, proposal])
  );

  return (
    <section className="agent-target-group">
      <header>
        <h3>{label}</h3>
        <span>{state.data.length} available</span>
      </header>

      <div className="agent-target-list">
        {state.data.map((target) => {
          const proposal = proposalByKey.get(target.key);
          const alreadyDeclared = existingTargetKeys.has(target.key);
          const errors = proposalErrors[target.key] || {};

          return (
            <article
              className={`agent-target-record ${proposal ? "selected" : ""}`}
              key={target.key}
            >
              <label className="agent-target-choice">
                <input
                  checked={Boolean(proposal)}
                  disabled={alreadyDeclared}
                  type="checkbox"
                  onChange={() => onToggle(target)}
                />
                <span className="agent-target-copy">
                  <strong>{target.name}</strong>
                  <small>
                    {formatGovernanceValue(target.type_label)}
                    {target.context ? ` · ${target.context}` : ""}
                  </small>
                  {target.description ? <p>{target.description}</p> : null}
                  <code>{target.id}</code>
                </span>
                <span className="agent-target-badges">
                  <AgentStatusBadge value={target.status} />
                  <AgentStatusBadge value={target.risk_level} />
                </span>
              </label>

              {alreadyDeclared ? (
                <p className="agent-existing-target-note">
                  An Access Grant already references this target. Review its
                  lifecycle in Access &amp; Data instead of creating a duplicate.
                </p>
              ) : null}

              {proposal ? (
                <div className="agent-grant-editor">
                  <div>
                    <strong>Pending review declaration</strong>
                    <p>
                      This creates an Access Grant with status Pending Review. It
                      does not provision credentials or activate external access.
                    </p>
                  </div>

                  <div className="agent-form-grid two-column">
                    <AgentField
                      error={errors.name}
                      htmlFor={`grant-name-${target.id}`}
                      label="Grant name"
                    >
                      <input
                        aria-describedby={
                          errors.name
                            ? `grant-name-${target.id}-error`
                            : undefined
                        }
                        aria-invalid={Boolean(errors.name)}
                        id={`grant-name-${target.id}`}
                        maxLength={255}
                        placeholder={`Name the ${target.name} declaration`}
                        value={proposal.name}
                        onChange={(event) =>
                          onUpdate(target.key, "name", event.target.value)
                        }
                      />
                    </AgentField>

                    <AgentField
                      error={errors.risk_level}
                      htmlFor={`grant-risk-${target.id}`}
                      label="Grant risk"
                    >
                      <select
                        aria-describedby={
                          errors.risk_level
                            ? `grant-risk-${target.id}-error`
                            : undefined
                        }
                        aria-invalid={Boolean(errors.risk_level)}
                        id={`grant-risk-${target.id}`}
                        value={proposal.risk_level}
                        onChange={(event) =>
                          onUpdate(
                            target.key,
                            "risk_level",
                            event.target.value as RiskLevel
                          )
                        }
                      >
                        {RISK_LEVELS.map((riskLevel) => (
                          <option key={riskLevel} value={riskLevel}>
                            {formatGovernanceValue(riskLevel)}
                          </option>
                        ))}
                      </select>
                    </AgentField>

                    <AgentField
                      error={errors.reason}
                      help="Use governance rationale only; do not include secrets or private payloads."
                      htmlFor={`grant-reason-${target.id}`}
                      label="Reason"
                      optional
                    >
                      <textarea
                        aria-describedby={
                          errors.reason
                            ? `grant-reason-${target.id}-error`
                            : undefined
                        }
                        aria-invalid={Boolean(errors.reason)}
                        id={`grant-reason-${target.id}`}
                        maxLength={4000}
                        placeholder="Explain why this declared access is needed"
                        rows={3}
                        value={proposal.reason}
                        onChange={(event) =>
                          onUpdate(target.key, "reason", event.target.value)
                        }
                      />
                    </AgentField>

                    <AgentField
                      error={errors.expires_at}
                      help="Leave blank when the declaration has no known expiration."
                      htmlFor={`grant-expiry-${target.id}`}
                      label="Expiration"
                      optional
                    >
                      <input
                        aria-describedby={
                          errors.expires_at
                            ? `grant-expiry-${target.id}-error`
                            : undefined
                        }
                        aria-invalid={Boolean(errors.expires_at)}
                        id={`grant-expiry-${target.id}`}
                        type="datetime-local"
                        value={proposal.expires_at}
                        onChange={(event) =>
                          onUpdate(target.key, "expires_at", event.target.value)
                        }
                      />
                    </AgentField>
                  </div>
                </div>
              ) : null}
            </article>
          );
        })}
      </div>
    </section>
  );
}
