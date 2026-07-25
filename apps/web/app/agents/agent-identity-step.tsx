import type {
  AgentFieldErrors,
  AgentFormValues
} from "./agent-governance-model";
import {
  AgentBoundaryNote,
  AgentField,
  AgentStepHeader
} from "./agent-form-controls";

export function AgentIdentityStep({
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
    <section className="agent-step-panel" aria-labelledby="agent-identity-title">
      <AgentStepHeader
        id="agent-identity-title"
        step="Step 1 of 5"
        title="Identity"
        description="Register the governance identity that represents an Agent running in an external runtime."
      />

      <AgentBoundaryNote title="External runtime boundary">
        AGCP registers and governs this Agent. It does not host or execute the
        Agent.
      </AgentBoundaryNote>

      <div className="agent-form-grid">
        <AgentField
          error={errors.name}
          help="Use the durable product or system name operators already recognize."
          htmlFor="agent-name"
          label="Agent name"
        >
          <input
            aria-describedby={errors.name ? "agent-name-error" : undefined}
            aria-invalid={Boolean(errors.name)}
            autoComplete="off"
            id="agent-name"
            maxLength={255}
            placeholder="Enter the registered Agent name"
            value={values.name}
            onChange={(event) => onChange("name", event.target.value)}
          />
        </AgentField>

        <AgentField
          error={errors.framework}
          help="Record the real external framework or runtime when known."
          htmlFor="agent-framework"
          label="Framework"
          optional
        >
          <input
            aria-describedby={
              errors.framework ? "agent-framework-error" : undefined
            }
            aria-invalid={Boolean(errors.framework)}
            autoComplete="off"
            id="agent-framework"
            maxLength={255}
            placeholder="For example, the actual external runtime"
            value={values.framework}
            onChange={(event) => onChange("framework", event.target.value)}
          />
        </AgentField>

        <AgentField
          error={errors.description}
          help="Describe the governed purpose without including prompts, credentials, or private payloads."
          htmlFor="agent-description"
          label="Description"
          optional
        >
          <textarea
            aria-describedby={
              errors.description ? "agent-description-error" : undefined
            }
            aria-invalid={Boolean(errors.description)}
            id="agent-description"
            maxLength={4000}
            placeholder="Explain what this Agent is responsible for"
            rows={6}
            value={values.description}
            onChange={(event) => onChange("description", event.target.value)}
          />
        </AgentField>
      </div>
    </section>
  );
}
