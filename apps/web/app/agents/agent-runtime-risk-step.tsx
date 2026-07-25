import type {
  AgentFieldErrors,
  AgentFormValues,
  AgentStatus,
  Environment,
  RiskLevel
} from "./agent-governance-model";
import {
  AGENT_STATUSES,
  ENVIRONMENTS,
  formatGovernanceValue,
  RISK_LEVELS
} from "./agent-governance-model";
import {
  AgentBoundaryNote,
  AgentField,
  AgentStepHeader
} from "./agent-form-controls";

export function AgentRuntimeRiskStep({
  confirmationRequired,
  confirmed,
  errors,
  values,
  onChange,
  onConfirm
}: {
  confirmationRequired: boolean;
  confirmed: boolean;
  errors: AgentFieldErrors;
  values: AgentFormValues;
  onChange: <K extends keyof AgentFormValues>(
    field: K,
    value: AgentFormValues[K]
  ) => void;
  onConfirm: (confirmed: boolean) => void;
}) {
  return (
    <section className="agent-step-panel" aria-labelledby="agent-runtime-risk-title">
      <AgentStepHeader
        id="agent-runtime-risk-title"
        step="Step 3 of 5"
        title="Runtime & Risk"
        description="Classify where this external Agent operates and its direct lifecycle state."
      />

      <AgentBoundaryNote title="Direct, audited mutation">
        AGCP does not add an Agent review workflow here. The selected values are
        submitted directly, validated by the backend, and recorded in the audit
        trail.
      </AgentBoundaryNote>

      <div className="agent-form-grid three-column">
        <AgentField
          error={errors.environment}
          help="Used as governance context; AGCP does not deploy the Agent."
          htmlFor="agent-environment"
          label="Environment"
        >
          <select
            aria-describedby={
              errors.environment ? "agent-environment-error" : undefined
            }
            aria-invalid={Boolean(errors.environment)}
            id="agent-environment"
            value={values.environment}
            onChange={(event) =>
              onChange("environment", event.target.value as Environment | "")
            }
          >
            <option value="">Select environment</option>
            {ENVIRONMENTS.map((environment) => (
              <option key={environment} value={environment}>
                {formatGovernanceValue(environment)}
              </option>
            ))}
          </select>
        </AgentField>

        <AgentField
          error={errors.status}
          help="A direct Agent Registry lifecycle value, not a review result."
          htmlFor="agent-status"
          label="Agent status"
        >
          <select
            aria-describedby={
              errors.status ? "agent-status-error" : undefined
            }
            aria-invalid={Boolean(errors.status)}
            id="agent-status"
            value={values.status}
            onChange={(event) => {
              onChange("status", event.target.value as AgentStatus | "");
              onConfirm(false);
            }}
          >
            <option value="">Select lifecycle status</option>
            {AGENT_STATUSES.map((status) => (
              <option key={status} value={status}>
                {formatGovernanceValue(status)}
              </option>
            ))}
          </select>
        </AgentField>

        <AgentField
          error={errors.risk_level}
          help="Qualitative classification only; AGCP does not calculate a score."
          htmlFor="agent-risk"
          label="Risk level"
        >
          <select
            aria-describedby={
              errors.risk_level ? "agent-risk-error" : undefined
            }
            aria-invalid={Boolean(errors.risk_level)}
            id="agent-risk"
            value={values.risk_level}
            onChange={(event) =>
              onChange("risk_level", event.target.value as RiskLevel | "")
            }
          >
            <option value="">Select risk level</option>
            {RISK_LEVELS.map((riskLevel) => (
              <option key={riskLevel} value={riskLevel}>
                {formatGovernanceValue(riskLevel)}
              </option>
            ))}
          </select>
        </AgentField>
      </div>

      {confirmationRequired ? (
        <AgentBoundaryNote
          title={`${formatGovernanceValue(values.status)} changes operating expectations`}
          tone={values.status === "active" ? "warning" : "danger"}
        >
          <label className="agent-impact-confirmation">
            <input
              checked={confirmed}
              type="checkbox"
              onChange={(event) => onConfirm(event.target.checked)}
            />
            <span>{statusImpactCopy(values.status)}</span>
          </label>
        </AgentBoundaryNote>
      ) : null}
    </section>
  );
}

function statusImpactCopy(status: AgentFormValues["status"]) {
  if (status === "active") {
    return "I understand that Active records this Agent as currently operating; AGCP still does not deploy or execute it.";
  }
  if (status === "suspended") {
    return "I understand that Suspended changes governance metadata only and does not stop an external runtime by itself.";
  }
  return "I understand that Retired is a lifecycle declaration and does not delete the Agent or its evidence.";
}
