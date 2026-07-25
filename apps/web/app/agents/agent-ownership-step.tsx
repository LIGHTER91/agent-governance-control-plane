import type {
  AgentFieldErrors,
  AgentFormValues,
  OwnerType
} from "./agent-governance-model";
import {
  formatGovernanceValue,
  OWNER_TYPES
} from "./agent-governance-model";
import {
  AgentBoundaryNote,
  AgentField,
  AgentStepHeader
} from "./agent-form-controls";

export function AgentOwnershipStep({
  errors,
  values,
  onChange
}: {
  errors: AgentFieldErrors;
  values: AgentFormValues;
  onChange: <K extends keyof AgentFormValues>(
    field: K,
    value: AgentFormValues[K]
  ) => void;
}) {
  return (
    <section className="agent-step-panel" aria-labelledby="agent-ownership-title">
      <AgentStepHeader
        id="agent-ownership-title"
        step="Step 2 of 5"
        title="Ownership"
        description="Record the accountable owner using real persisted information."
      />

      <AgentBoundaryNote title="Declarative owner identity">
        Local V1 does not include an enterprise user or team directory. Enter
        the stable identity reference used by your organization; AGCP will not
        invent or resolve directory members.
      </AgentBoundaryNote>

      <div className="agent-form-grid two-column">
        <AgentField
          error={errors.owner_type}
          help="Only backend-supported owner types are available."
          htmlFor="agent-owner-type"
          label="Owner type"
        >
          <select
            aria-describedby={
              errors.owner_type ? "agent-owner-type-error" : undefined
            }
            aria-invalid={Boolean(errors.owner_type)}
            id="agent-owner-type"
            value={values.owner_type}
            onChange={(event) =>
              onChange("owner_type", event.target.value as OwnerType | "")
            }
          >
            <option value="">Select owner type</option>
            {OWNER_TYPES.map((ownerType) => (
              <option key={ownerType} value={ownerType}>
                {formatGovernanceValue(ownerType)}
              </option>
            ))}
          </select>
        </AgentField>

        <AgentField
          error={errors.owner_id}
          help="Use a durable external identifier, not an email address."
          htmlFor="agent-owner-id"
          label="Stable owner identifier"
        >
          <input
            aria-describedby={
              errors.owner_id ? "agent-owner-id-error" : undefined
            }
            aria-invalid={Boolean(errors.owner_id)}
            autoComplete="off"
            id="agent-owner-id"
            maxLength={255}
            placeholder={ownerIdPlaceholder(values.owner_type)}
            spellCheck={false}
            value={values.owner_id}
            onChange={(event) => onChange("owner_id", event.target.value)}
          />
        </AgentField>

        <AgentField
          error={errors.owner_name}
          help="This is display metadata, not a directory lookup."
          htmlFor="agent-owner-name"
          label="Owner display name"
        >
          <input
            aria-describedby={
              errors.owner_name ? "agent-owner-name-error" : undefined
            }
            aria-invalid={Boolean(errors.owner_name)}
            autoComplete="organization"
            id="agent-owner-name"
            maxLength={255}
            placeholder="Enter the persisted owner name"
            value={values.owner_name}
            onChange={(event) => onChange("owner_name", event.target.value)}
          />
        </AgentField>

        <AgentField
          error={errors.owner_contact_email}
          help="Optional operational contact only; it is not the primary owner identifier."
          htmlFor="agent-owner-email"
          label="Contact email"
          optional
        >
          <input
            aria-describedby={
              errors.owner_contact_email
                ? "agent-owner-email-error"
                : undefined
            }
            aria-invalid={Boolean(errors.owner_contact_email)}
            autoComplete="email"
            id="agent-owner-email"
            maxLength={320}
            placeholder="owner@example.com"
            type="email"
            value={values.owner_contact_email}
            onChange={(event) =>
              onChange("owner_contact_email", event.target.value)
            }
          />
        </AgentField>
      </div>
    </section>
  );
}

function ownerIdPlaceholder(ownerType: AgentFormValues["owner_type"]) {
  if (ownerType === "user") {
    return "user:<external-id>";
  }
  if (ownerType === "team") {
    return "team:<slug>";
  }
  if (ownerType === "service") {
    return "service:<slug>";
  }
  if (ownerType === "organization_unit") {
    return "org_unit:<slug>";
  }
  return "Select an owner type first";
}
