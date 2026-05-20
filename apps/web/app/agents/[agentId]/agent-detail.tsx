"use client";

import { useEffect, useMemo, useState } from "react";
import { ApiRequestError, getApiBaseUrl } from "../../lib/api";
import { AgentRecord, fetchAgent } from "../../lib/agents";
import { EvidenceBundle, fetchEvidenceBundle } from "../../lib/evidence";
import {
  HumanApprovalRecord,
  fetchAgentHumanApprovals
} from "../../lib/human-approvals";

type AgentDetailState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | {
      status: "ready";
      agent: AgentRecord;
      humanApprovals: HumanApprovalRecord[];
    };

type EvidenceState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; bundle: EvidenceBundle };

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

function agentErrorMessage(error: unknown) {
  if (error instanceof ApiRequestError && error.status === 404) {
    return "Agent not found.";
  }

  return error instanceof Error
    ? error.message
    : "Unable to load the Agent detail from the backend.";
}

function evidenceErrorMessage(error: unknown) {
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

function ownerDisplay(agent: AgentRecord) {
  return agent.owner_name || agent.owner_id;
}

export function AgentDetail({ agentId }: { agentId: string }) {
  const [state, setState] = useState<AgentDetailState>({ status: "loading" });
  const [evidenceState, setEvidenceState] = useState<EvidenceState>({
    status: "idle"
  });

  useEffect(() => {
    const controller = new AbortController();

    setState({ status: "loading" });
    setEvidenceState({ status: "idle" });

    Promise.all([
      fetchAgent(agentId, controller.signal),
      fetchAgentHumanApprovals(agentId, controller.signal)
    ])
      .then(([agent, humanApprovals]) => {
        setState({ status: "ready", agent, humanApprovals });
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) {
          return;
        }

        setState({ status: "error", message: agentErrorMessage(error) });
      });

    return () => {
      controller.abort();
    };
  }, [agentId]);

  async function handleLoadEvidence() {
    const controller = new AbortController();

    setEvidenceState({ status: "loading" });

    try {
      const bundle = await fetchEvidenceBundle(agentId, controller.signal);
      setEvidenceState({ status: "ready", bundle });
    } catch (error: unknown) {
      if (controller.signal.aborted) {
        return;
      }

      setEvidenceState({
        status: "error",
        message: evidenceErrorMessage(error)
      });
    }
  }

  if (state.status === "loading") {
    return (
      <section className="data-panel" aria-live="polite">
        <div className="state-message">
          <strong>Loading Agent detail</strong>
          <p>
            Requesting `GET /agents/{"{agent_id}"}` and related HumanApproval
            records from {getApiBaseUrl()}.
          </p>
        </div>
      </section>
    );
  }

  if (state.status === "error") {
    return (
      <section className="data-panel" role="alert">
        <div className="state-message error">
          <strong>Unable to load Agent detail</strong>
          <p>{state.message}</p>
          <p>
            Check that the backend is running and that
            NEXT_PUBLIC_AGCP_API_BASE_URL points to the API base URL.
          </p>
        </div>
      </section>
    );
  }

  return (
    <>
      <AgentHeader agent={state.agent} />
      <AgentOverview agent={state.agent} />
      <GovernanceSummary
        agent={state.agent}
        humanApprovals={state.humanApprovals}
      />
      <HumanApprovalsSection humanApprovals={state.humanApprovals} />
      <EvidenceAccessSection
        evidenceState={evidenceState}
        onLoadEvidence={handleLoadEvidence}
      />
      <RuntimePolicyPlaceholder />
    </>
  );
}

function AgentHeader({ agent }: { agent: AgentRecord }) {
  return (
    <section className="page-header">
      <p className="eyebrow">Agent Registry</p>
      <h2>{agent.name}</h2>
      <p>
        Product-oriented governance overview for one registered Agent, including
        ownership, lifecycle state, risk classification, human oversight, and
        evidence access.
      </p>
    </section>
  );
}

function AgentOverview({ agent }: { agent: AgentRecord }) {
  const fields = [
    ["name", agent.name],
    ["description", agent.description],
    ["owner_type", agent.owner_type],
    ["owner", ownerDisplay(agent)],
    ["environment", agent.environment],
    ["status", agent.status],
    ["risk_level", agent.risk_level],
    ["framework", agent.framework],
    ["created_at", formatTimestamp(agent.created_at)],
    ["updated_at", formatTimestamp(agent.updated_at)]
  ];

  return (
    <section className="evidence-section">
      <header className="evidence-section-header">
        <h3>Agent overview</h3>
        <span>read-only</span>
      </header>
      <dl className="evidence-fields agent-detail-fields">
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

function GovernanceSummary({
  agent,
  humanApprovals
}: {
  agent: AgentRecord;
  humanApprovals: HumanApprovalRecord[];
}) {
  const pendingCount = humanApprovals.filter(
    (approval) => approval.status === "pending"
  ).length;

  const summaryItems = [
    {
      label: "Lifecycle",
      value: formatValue(agent.status),
      detail: "Current Agent Registry status."
    },
    {
      label: "Risk",
      value: formatValue(agent.risk_level),
      detail: "Risk classification stored on the Agent record."
    },
    {
      label: "Environment",
      value: formatValue(agent.environment),
      detail: "Deployment environment used for governance context."
    },
    {
      label: "Pending Human Approvals",
      value: String(pendingCount),
      detail: "Open review items linked to this Agent."
    }
  ];

  return (
    <>
      <h3 className="section-title">Governance summary</h3>
      <section className="detail-summary-grid" aria-label="Governance summary">
        {summaryItems.map((item) => (
          <article className="work-item" key={item.label}>
            <span className="status-label foundation">{item.label}</span>
            <strong>{item.value}</strong>
            <p>{item.detail}</p>
          </article>
        ))}
      </section>
    </>
  );
}

function HumanApprovalsSection({
  humanApprovals
}: {
  humanApprovals: HumanApprovalRecord[];
}) {
  return (
    <>
      <h3 className="section-title">Human approvals</h3>
      <section className="data-panel" aria-label="Agent Human Approvals">
        {humanApprovals.length === 0 ? (
          <div className="state-message">
            <strong>No HumanApproval records for this Agent</strong>
            <p>
              Pending, approved, rejected, cancelled, or expired review records
              will appear here after backend governance flows request human
              oversight.
            </p>
          </div>
        ) : (
          <div className="table-scroll">
            <table className="data-table agent-approvals-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Policy Decision ID</th>
                  <th>Status</th>
                  <th>Requester</th>
                  <th>Reviewer</th>
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
    </>
  );
}

function EvidenceAccessSection({
  evidenceState,
  onLoadEvidence
}: {
  evidenceState: EvidenceState;
  onLoadEvidence: () => void;
}) {
  const counts = useMemo(() => {
    if (evidenceState.status !== "ready") {
      return [];
    }

    const { bundle } = evidenceState;

    return [
      ["audit_logs", bundle.audit_logs.length],
      ["agent_runs", bundle.agent_runs.length],
      ["trace_events", bundle.trace_events.length],
      ["policy_decisions", bundle.policy_decisions.length],
      ["human_approvals", bundle.human_approvals.length]
    ];
  }, [evidenceState]);

  return (
    <>
      <h3 className="section-title">Evidence access</h3>
      <section className="detail-card">
        <div className="detail-card-header">
          <div>
            <strong>Evidence Bundle</strong>
            <p>
              Loads `GET /agents/{"{agent_id}"}/evidence-bundle` only when
              requested. Backend RBAC may require an auditor or platform_admin
              actor.
            </p>
          </div>
          <button
            className="secondary-action"
            type="button"
            onClick={onLoadEvidence}
            disabled={evidenceState.status === "loading"}
          >
            {evidenceState.status === "loading"
              ? "Loading Evidence Bundle"
              : "Load Evidence Bundle"}
          </button>
        </div>

        {evidenceState.status === "idle" ? (
          <div className="state-message compact">
            <strong>No Evidence Bundle loaded</strong>
            <p>
              Use the action above to inspect whether evidence export is
              available for the current backend actor.
            </p>
          </div>
        ) : null}

        {evidenceState.status === "error" ? (
          <div className="state-message error compact" role="alert">
            <strong>Unable to load Evidence Bundle</strong>
            <p>{evidenceState.message}</p>
          </div>
        ) : null}

        {evidenceState.status === "ready" ? (
          <div className="detail-count-grid" aria-label="Evidence Bundle counts">
            {counts.map(([label, count]) => (
              <div key={label}>
                <span>{label}</span>
                <strong>{count}</strong>
              </div>
            ))}
          </div>
        ) : null}
      </section>
    </>
  );
}

function RuntimePolicyPlaceholder() {
  return (
    <>
      <h3 className="section-title">Runtime / policy decisions</h3>
      <section className="placeholder-panel">
        <p>
          No dedicated Agent-specific runtime or policy decision endpoint is
          wired into the frontend yet. Authorized Evidence Bundle access can
          show linked trace events and PolicyDecision records for this Agent.
        </p>
      </section>
    </>
  );
}
