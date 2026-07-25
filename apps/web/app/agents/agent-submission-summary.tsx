import Link from "next/link";

export type FailedGrantOperation = {
  targetKey: string;
  targetName: string;
  grantName: string;
  message: string;
};

export type SubmissionState =
  | { status: "idle" }
  | { status: "submitting"; message: string }
  | { status: "error"; title: string; message: string }
  | {
      status: "partial";
      agentId: string;
      successfulGrantCount: number;
      failedGrants: FailedGrantOperation[];
    };

export function AgentSubmissionSummary({
  state,
  onRetry
}: {
  state: SubmissionState;
  onRetry: () => void;
}) {
  if (state.status === "idle") {
    return null;
  }

  if (state.status === "submitting") {
    return (
      <section className="agent-submission-summary submitting" aria-live="polite">
        <strong>Saving governance configuration</strong>
        <p>{state.message}</p>
      </section>
    );
  }

  if (state.status === "error") {
    return (
      <section className="agent-submission-summary error" role="alert">
        <strong>{state.title}</strong>
        <p>{state.message}</p>
      </section>
    );
  }

  return (
    <section className="agent-submission-summary partial" role="alert">
      <strong>Agent saved with partial Access Grant completion</strong>
      <p>
        The Agent remains registered. {state.successfulGrantCount} Access Grant
        operation(s) succeeded and {state.failedGrants.length} failed. Nothing
        was presented as rolled back.
      </p>
      <ul>
        {state.failedGrants.map((failure) => (
          <li key={failure.targetKey}>
            <span>{failure.targetName}</span>
            <strong>{failure.grantName || "Unnamed declaration"}</strong>
            <p>{failure.message}</p>
          </li>
        ))}
      </ul>
      <div>
        <button type="button" onClick={onRetry}>
          Retry failed grants
        </button>
        <Link href={`/agents/${encodeURIComponent(state.agentId)}`}>
          Open Agent Governance Profile
        </Link>
      </div>
    </section>
  );
}
