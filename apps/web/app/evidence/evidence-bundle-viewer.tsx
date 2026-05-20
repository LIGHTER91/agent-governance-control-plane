"use client";

import { FormEvent, useState } from "react";
import { ApiRequestError, getApiBaseUrl } from "../lib/api";
import {
  EvidenceAgent,
  EvidenceAgentRun,
  EvidenceAuditLog,
  EvidenceBundle,
  EvidenceHumanApproval,
  EvidenceMetadata,
  EvidencePolicyDecision,
  EvidenceTraceEvent,
  fetchEvidenceBundle
} from "../lib/evidence";

type EvidenceState =
  | { status: "idle" }
  | { status: "loading"; agentId: string }
  | { status: "error"; agentId: string; message: string }
  | { status: "ready"; agentId: string; bundle: EvidenceBundle };

function formatValue(value: string | null | undefined) {
  if (!value) {
    return "Not set";
  }

  return value
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function formatTimestamp(value: string | null | undefined) {
  if (!value) {
    return "Not set";
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleString();
}

function metadataText(metadata: EvidenceMetadata) {
  const entries = Object.entries(metadata);

  if (entries.length === 0) {
    return "No safe metadata";
  }

  return JSON.stringify(metadata, null, 2);
}

function errorMessage(error: unknown) {
  if (error instanceof ApiRequestError) {
    if (error.status === 403) {
      return "Evidence Bundle export requires an auditor or platform_admin role.";
    }

    if (error.status === 404) {
      return "Agent not found.";
    }
  }

  return error instanceof Error
    ? error.message
    : "Unable to load the Evidence Bundle from the backend.";
}

export function EvidenceBundleViewer() {
  const [agentId, setAgentId] = useState("");
  const [state, setState] = useState<EvidenceState>({ status: "idle" });

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const normalizedAgentId = agentId.trim();
    if (!normalizedAgentId) {
      setState({
        status: "error",
        agentId: "",
        message: "Enter an agent_id before requesting an Evidence Bundle."
      });
      return;
    }

    const controller = new AbortController();
    setState({ status: "loading", agentId: normalizedAgentId });

    try {
      const bundle = await fetchEvidenceBundle(
        normalizedAgentId,
        controller.signal
      );
      setState({ status: "ready", agentId: normalizedAgentId, bundle });
    } catch (error: unknown) {
      if (controller.signal.aborted) {
        return;
      }

      setState({
        status: "error",
        agentId: normalizedAgentId,
        message: errorMessage(error)
      });
    }
  }

  return (
    <>
      <section className="lookup-panel" aria-label="Evidence Bundle lookup">
        <form className="lookup-form" onSubmit={handleSubmit}>
          <label htmlFor="evidence-agent-id">
            <span>agent_id</span>
            <input
              id="evidence-agent-id"
              type="text"
              value={agentId}
              onChange={(event) => setAgentId(event.target.value)}
              placeholder="00000000-0000-0000-0000-000000000000"
              spellCheck={false}
            />
          </label>
          <button type="submit">Load Evidence Bundle</button>
        </form>
        <p>
          Requests `GET /agents/{"{agent_id}"}/evidence-bundle` from{" "}
          {getApiBaseUrl()}.
        </p>
      </section>

      {state.status === "idle" ? (
        <section className="state-message evidence-state">
          <strong>No Evidence Bundle loaded</strong>
          <p>
            Enter an Agent ID to inspect filtered evidence records already
            exported by the backend.
          </p>
        </section>
      ) : null}

      {state.status === "loading" ? (
        <section className="state-message evidence-state" aria-live="polite">
          <strong>Loading Evidence Bundle</strong>
          <p>Requesting evidence for agent_id {state.agentId}.</p>
        </section>
      ) : null}

      {state.status === "error" ? (
        <section className="state-message error evidence-state" role="alert">
          <strong>Unable to load Evidence Bundle</strong>
          <p>{state.message}</p>
        </section>
      ) : null}

      {state.status === "ready" ? (
        <EvidenceBundleSections bundle={state.bundle} />
      ) : null}
    </>
  );
}

function EvidenceBundleSections({ bundle }: { bundle: EvidenceBundle }) {
  return (
    <div className="evidence-layout">
      <AgentSection agent={bundle.agent} />
      <AuditLogsSection auditLogs={bundle.audit_logs} />
      <AgentRunsSection agentRuns={bundle.agent_runs} />
      <TraceEventsSection traceEvents={bundle.trace_events} />
      <PolicyDecisionsSection policyDecisions={bundle.policy_decisions} />
      <HumanApprovalsSection humanApprovals={bundle.human_approvals} />
    </div>
  );
}

function AgentSection({ agent }: { agent: EvidenceAgent }) {
  const fields = [
    ["id", agent.id],
    ["name", agent.name],
    ["description", agent.description],
    ["owner_type", agent.owner_type],
    ["owner_id", agent.owner_id],
    ["owner_name", agent.owner_name],
    ["owner_contact_email", agent.owner_contact_email],
    ["environment", agent.environment],
    ["status", agent.status],
    ["risk_level", agent.risk_level],
    ["framework", agent.framework],
    ["created_at", formatTimestamp(agent.created_at)],
    ["updated_at", formatTimestamp(agent.updated_at)]
  ];

  return (
    <section className="evidence-section">
      <SectionHeader title="agent" count={1} />
      <dl className="evidence-fields">
        {fields.map(([label, value]) => (
          <div key={label}>
            <dt>{label}</dt>
            <dd>{formatValue(value)}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}

function AuditLogsSection({ auditLogs }: { auditLogs: EvidenceAuditLog[] }) {
  return (
    <section className="evidence-section">
      <SectionHeader title="audit_logs" count={auditLogs.length} />
      {auditLogs.length === 0 ? (
        <EmptySection />
      ) : (
        <div className="table-scroll">
          <table className="data-table evidence-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Event Type</th>
                <th>Actor</th>
                <th>Entity</th>
                <th>Summary</th>
                <th>Metadata</th>
                <th>Created</th>
              </tr>
            </thead>
            <tbody>
              {auditLogs.map((log) => (
                <tr key={log.id}>
                  <td className="id-cell">{log.id}</td>
                  <td>{formatValue(log.event_type)}</td>
                  <td className="id-cell">
                    {log.actor_type}:{log.actor_id}
                  </td>
                  <td className="id-cell">
                    {log.entity_type}:{log.entity_id}
                  </td>
                  <td>{log.summary}</td>
                  <td>
                    <pre className="metadata-block">
                      {metadataText(log.metadata)}
                    </pre>
                  </td>
                  <td>{formatTimestamp(log.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

function AgentRunsSection({ agentRuns }: { agentRuns: EvidenceAgentRun[] }) {
  return (
    <section className="evidence-section">
      <SectionHeader title="agent_runs" count={agentRuns.length} />
      {agentRuns.length === 0 ? (
        <EmptySection />
      ) : (
        <div className="table-scroll">
          <table className="data-table evidence-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Run ID</th>
                <th>Correlation ID</th>
                <th>Environment</th>
                <th>Status</th>
                <th>Summary</th>
                <th>Metadata</th>
                <th>Started</th>
                <th>Ended</th>
              </tr>
            </thead>
            <tbody>
              {agentRuns.map((run) => (
                <tr key={run.id}>
                  <td className="id-cell">{run.id}</td>
                  <td className="id-cell">{run.run_id}</td>
                  <td className="id-cell">{run.correlation_id}</td>
                  <td>{formatValue(run.environment)}</td>
                  <td>{formatValue(run.status)}</td>
                  <td>{formatValue(run.summary)}</td>
                  <td>
                    <pre className="metadata-block">
                      {metadataText(run.metadata)}
                    </pre>
                  </td>
                  <td>{formatTimestamp(run.started_at)}</td>
                  <td>{formatTimestamp(run.ended_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

function TraceEventsSection({
  traceEvents
}: {
  traceEvents: EvidenceTraceEvent[];
}) {
  return (
    <section className="evidence-section">
      <SectionHeader title="trace_events" count={traceEvents.length} />
      {traceEvents.length === 0 ? (
        <EmptySection />
      ) : (
        <div className="table-scroll">
          <table className="data-table evidence-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Run ID</th>
                <th>External Event ID</th>
                <th>Correlation ID</th>
                <th>Event Type</th>
                <th>Summary</th>
                <th>Metadata</th>
                <th>Timestamp</th>
              </tr>
            </thead>
            <tbody>
              {traceEvents.map((event) => (
                <tr key={event.id}>
                  <td className="id-cell">{event.id}</td>
                  <td className="id-cell">{event.run_id}</td>
                  <td className="id-cell">{event.external_event_id}</td>
                  <td className="id-cell">{event.correlation_id}</td>
                  <td>{formatValue(event.event_type)}</td>
                  <td>{event.summary}</td>
                  <td>
                    <pre className="metadata-block">
                      {metadataText(event.metadata)}
                    </pre>
                  </td>
                  <td>{formatTimestamp(event.timestamp)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

function PolicyDecisionsSection({
  policyDecisions
}: {
  policyDecisions: EvidencePolicyDecision[];
}) {
  return (
    <section className="evidence-section">
      <SectionHeader title="policy_decisions" count={policyDecisions.length} />
      {policyDecisions.length === 0 ? (
        <EmptySection />
      ) : (
        <div className="table-scroll">
          <table className="data-table evidence-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Decision</th>
                <th>Reason</th>
                <th>Trace Event ID</th>
                <th>Policy</th>
                <th>Rule</th>
                <th>Created</th>
              </tr>
            </thead>
            <tbody>
              {policyDecisions.map((decision) => (
                <tr key={decision.id}>
                  <td className="id-cell">{decision.id}</td>
                  <td>
                    <span className={`table-pill decision-${decision.decision}`}>
                      {formatValue(decision.decision)}
                    </span>
                  </td>
                  <td>{decision.reason}</td>
                  <td className="id-cell">
                    {formatValue(decision.trace_event_id)}
                  </td>
                  <td>{policyLabel(decision)}</td>
                  <td>{ruleLabel(decision)}</td>
                  <td>{formatTimestamp(decision.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

function HumanApprovalsSection({
  humanApprovals
}: {
  humanApprovals: EvidenceHumanApproval[];
}) {
  return (
    <section className="evidence-section">
      <SectionHeader title="human_approvals" count={humanApprovals.length} />
      {humanApprovals.length === 0 ? (
        <EmptySection />
      ) : (
        <div className="table-scroll">
          <table className="data-table evidence-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Policy Decision ID</th>
                <th>Status</th>
                <th>Requester</th>
                <th>Reviewer</th>
                <th>Reason</th>
                <th>Decision Note</th>
                <th>Created</th>
                <th>Reviewed</th>
                <th>Expires</th>
              </tr>
            </thead>
            <tbody>
              {humanApprovals.map((approval) => (
                <tr key={approval.id}>
                  <td className="id-cell">{approval.id}</td>
                  <td className="id-cell">
                    {formatValue(approval.policy_decision_id)}
                  </td>
                  <td>
                    <span className={`table-pill approval-${approval.status}`}>
                      {formatValue(approval.status)}
                    </span>
                  </td>
                  <td className="id-cell">
                    {approval.requested_by_actor_type}:
                    {approval.requested_by_actor_id}
                  </td>
                  <td className="id-cell">
                    {approval.reviewed_by_actor_type
                      ? `${approval.reviewed_by_actor_type}:${approval.reviewed_by_actor_id}`
                      : "Not set"}
                  </td>
                  <td>{formatValue(approval.reason)}</td>
                  <td>{formatValue(approval.decision_note)}</td>
                  <td>{formatTimestamp(approval.created_at)}</td>
                  <td>{formatTimestamp(approval.reviewed_at)}</td>
                  <td>{formatTimestamp(approval.expires_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

function SectionHeader({ title, count }: { title: string; count: number }) {
  return (
    <header className="evidence-section-header">
      <h3>{title}</h3>
      <span>{count}</span>
    </header>
  );
}

function EmptySection() {
  return (
    <div className="state-message compact">
      <strong>No records in this section</strong>
      <p>The backend returned an empty list for this evidence category.</p>
    </div>
  );
}

function policyLabel(decision: EvidencePolicyDecision) {
  if (decision.policy) {
    return `${decision.policy.name} (${decision.policy.status})`;
  }

  return formatValue(decision.policy_id);
}

function ruleLabel(decision: EvidencePolicyDecision) {
  if (decision.rule) {
    return decision.rule.name;
  }

  return formatValue(decision.rule_id);
}
