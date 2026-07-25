export const AGENT_WORKFLOW_STEPS = [
  {
    id: "identity",
    label: "Identity",
    description: "Name and runtime framework"
  },
  {
    id: "ownership",
    label: "Ownership",
    description: "Accountable owner reference"
  },
  {
    id: "runtime-risk",
    label: "Runtime & Risk",
    description: "Environment and lifecycle"
  },
  {
    id: "governed-access",
    label: "Governed Access",
    description: "Declared inventory access"
  },
  {
    id: "review",
    label: "Review",
    description: "Confirm governance metadata"
  }
] as const;

export function AgentWorkflowSteps({
  currentStep,
  furthestStep,
  onSelectStep
}: {
  currentStep: number;
  furthestStep: number;
  onSelectStep: (step: number) => void;
}) {
  return (
    <nav className="agent-workflow-steps" aria-label="Agent onboarding steps">
      <ol>
        {AGENT_WORKFLOW_STEPS.map((step, index) => {
          const isCurrent = currentStep === index;
          const isComplete = index < currentStep || index < furthestStep;
          const canSelect = index <= furthestStep;

          return (
            <li
              className={`${isCurrent ? "current" : ""} ${
                isComplete ? "complete" : ""
              }`}
              key={step.id}
            >
              <button
                aria-current={isCurrent ? "step" : undefined}
                disabled={!canSelect}
                type="button"
                onClick={() => onSelectStep(index)}
              >
                <span>{isComplete ? "✓" : index + 1}</span>
                <strong>{step.label}</strong>
                <small>{step.description}</small>
              </button>
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
