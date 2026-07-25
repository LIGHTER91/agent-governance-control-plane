import type { ReactNode } from "react";
import type {
  AgentFormValues,
  ProposedAccessGrant
} from "./agent-governance-model";
import {
  formatGovernanceValue
} from "./agent-governance-model";
import {
  AgentBoundaryNote,
  AgentStatusBadge,
  AgentStepHeader
} from "./agent-form-controls";

export function AgentReviewStep({
  mode,
  proposals,
  values
}: {
  mode: "create" | "edit";
  proposals: ProposedAccessGrant[];
  values: AgentFormValues;
}) {
  return (
    <section className="agent-step-panel" aria-labelledby="agent-review-title">
      <AgentStepHeader
        id="agent-review-title"
        step="Step 5 of 5"
        title="Review governance configuration"
        description={
          mode === "create"
            ? "Confirm the Agent metadata and proposed declarations before registration."
            : "Confirm changed Agent metadata and newly proposed declarations before saving."
        }
      />

      <div className="agent-review-grid">
        <ReviewSection title="Agent">
          <ReviewRow label="Name" value={values.name} />
          <ReviewRow label="Description" value={values.description} />
          <ReviewRow label="Framework" value={values.framework} />
          <ReviewRow label="Environment" value={values.environment} badge />
          <ReviewRow label="Status" value={values.status} badge />
          <ReviewRow label="Risk" value={values.risk_level} badge />
        </ReviewSection>

        <ReviewSection title="Owner">
          <ReviewRow label="Type" value={values.owner_type} badge />
          <ReviewRow label="Display name" value={values.owner_name} />
          <ReviewRow label="Stable identifier" value={values.owner_id} technical />
          <ReviewRow
            label="Contact email"
            value={values.owner_contact_email}
          />
        </ReviewSection>
      </div>

      <ReviewSection
        title={`New governed access declarations (${proposals.length})`}
      >
        {proposals.length === 0 ? (
          <div className="agent-inline-state">
            <strong>No new Access Grants selected</strong>
            <p>
              The Agent can be registered or updated without adding a
              declaration. Inventory can be reviewed later in Access &amp; Data.
            </p>
          </div>
        ) : (
          <ul className="agent-review-grants">
            {proposals.map((proposal) => (
              <li key={proposal.target.key}>
                <div>
                  <strong>{proposal.target.name}</strong>
                  <span>
                    {formatGovernanceValue(proposal.target.target_type)}
                  </span>
                </div>
                <dl>
                  <ReviewRow label="Grant name" value={proposal.name} />
                  <ReviewRow
                    label="Status"
                    value="pending_review"
                    badge
                  />
                  <ReviewRow
                    label="Risk"
                    value={proposal.risk_level}
                    badge
                  />
                  <ReviewRow label="Reason" value={proposal.reason} />
                  <ReviewRow
                    label="Expiration"
                    value={
                      proposal.expires_at
                        ? formatDate(proposal.expires_at)
                        : "No expiration"
                    }
                  />
                </dl>
              </li>
            ))}
          </ul>
        )}
      </ReviewSection>

      <div className="agent-review-boundaries">
        <AgentBoundaryNote title="What AGCP will do">
          AGCP will register governance metadata, append mutation audit records,
          and create each selected Access Grant as Pending Review.
        </AgentBoundaryNote>
        <AgentBoundaryNote title="What AGCP will not do" tone="warning">
          AGCP will not deploy or execute this Agent. Access Grants do not create
          IAM permissions. Runtime enforcement still depends on callers using
          Runtime Gateway and respecting <code>proceed</code>.
        </AgentBoundaryNote>
      </div>
    </section>
  );
}

function ReviewSection({
  children,
  title
}: {
  children: ReactNode;
  title: string;
}) {
  return (
    <section className="agent-review-section">
      <header>
        <h3>{title}</h3>
      </header>
      <dl>{children}</dl>
    </section>
  );
}

function ReviewRow({
  badge = false,
  label,
  technical = false,
  value
}: {
  badge?: boolean;
  label: string;
  technical?: boolean;
  value: string | null | undefined;
}) {
  const displayValue = value?.trim() || "Not set";
  return (
    <div className={technical ? "technical" : undefined}>
      <dt>{label}</dt>
      <dd>
        {badge && value ? (
          <AgentStatusBadge value={value} />
        ) : (
          displayValue
        )}
      </dd>
    </div>
  );
}

function formatDate(value: string) {
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleString();
}
