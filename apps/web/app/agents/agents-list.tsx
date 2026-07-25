"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  AGCPBadge,
  AGCPDataTable,
  AGCPEmptyState,
  AGCPErrorState,
  AGCPPanel,
  AGCPSectionHeader
} from "../agcp-studio/primitives";
import { AgentRecord, fetchAgents, getApiBaseUrl } from "../lib/agents";

type AgentsState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; agents: AgentRecord[] };

const columns = [
  "Name",
  "Owner",
  "Owner Type",
  "Environment",
  "Status",
  "Risk",
  "Framework"
];

function formatValue(value: string | null | undefined) {
  if (!value) {
    return "Not set";
  }

  return value
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function ownerDisplay(agent: AgentRecord) {
  return agent.owner_name || agent.owner_id;
}

function badgeTone(value: string | null | undefined) {
  if (value === "active" || value === "approved" || value === "low") {
    return "ok";
  }

  if (
    value === "pending" ||
    value === "medium" ||
    value === "staging" ||
    value === "development"
  ) {
    return "warn";
  }

  if (
    value === "disabled" ||
    value === "archived" ||
    value === "high" ||
    value === "critical" ||
    value === "production"
  ) {
    return "danger";
  }

  return "info";
}

function environmentCount(agents: AgentRecord[], environment: string) {
  return agents.filter((agent) => agent.environment === environment).length;
}

export function AgentsList() {
  const [state, setState] = useState<AgentsState>({ status: "loading" });

  useEffect(() => {
    const controller = new AbortController();

    fetchAgents(controller.signal)
      .then((agents) => {
        setState({ status: "ready", agents });
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) {
          return;
        }

        const message =
          error instanceof Error
            ? error.message
            : "Unable to load agents from the backend.";
        setState({ status: "error", message });
      });

    return () => {
      controller.abort();
    };
  }, []);

  if (state.status === "loading") {
    return (
      <AGCPPanel>
        <AGCPEmptyState title="Loading agents">
          Requesting registered agents from {getApiBaseUrl()}.
        </AGCPEmptyState>
      </AGCPPanel>
    );
  }

  if (state.status === "error") {
    return (
      <AGCPPanel>
        <AGCPErrorState title="Unable to load agents">
          {state.message} Check that the backend is running and that
          NEXT_PUBLIC_AGCP_API_BASE_URL points to the API base URL.
        </AGCPErrorState>
      </AGCPPanel>
    );
  }

  if (state.agents.length === 0) {
    return (
      <AGCPPanel>
        <AGCPEmptyState title="No agents registered">
          Register the first Agent using real ownership and governance metadata.{" "}
          <Link className="agcp-primary-link" href="/agents/new">
            Register agent
          </Link>
        </AGCPEmptyState>
      </AGCPPanel>
    );
  }

  return (
    <AGCPPanel className="agcp-agent-registry" aria-label="Registered agents">
      <AGCPSectionHeader
        eyebrow="connected registry"
        title="Registered agents"
        description="Live records from GET /agents. Open a Governance Profile or register another Agent without synthetic records."
        meta={<AGCPBadge tone="purple">{state.agents.length} agents</AGCPBadge>}
        actions={
          <Link className="agent-inline-action" href="/agents/new">
            Register agent
          </Link>
        }
      />

      <div className="agcp-registry-summary" aria-label="Agent registry summary">
        <div>
          <span>Total</span>
          <strong>{state.agents.length}</strong>
        </div>
        <div>
          <span>Production</span>
          <strong>{environmentCount(state.agents, "production")}</strong>
        </div>
        <div>
          <span>High or critical risk</span>
          <strong>
            {
              state.agents.filter(
                (agent) =>
                  agent.risk_level === "high" || agent.risk_level === "critical"
              ).length
            }
          </strong>
        </div>
      </div>

      <AGCPDataTable>
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={column} scope="col">
                {column}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {state.agents.map((agent) => (
            <tr key={agent.id}>
              <td>
                <Link
                  className="agcp-primary-link"
                  href={`/agents/${encodeURIComponent(agent.id)}`}
                >
                  {agent.name}
                </Link>
                <div className="agcp-id">{agent.id}</div>
              </td>
              <td>{ownerDisplay(agent)}</td>
              <td>
                <AGCPBadge tone="muted">{formatValue(agent.owner_type)}</AGCPBadge>
              </td>
              <td>
                <AGCPBadge tone={badgeTone(agent.environment)}>
                  {formatValue(agent.environment)}
                </AGCPBadge>
              </td>
              <td>
                <AGCPBadge tone={badgeTone(agent.status)}>
                  {formatValue(agent.status)}
                </AGCPBadge>
              </td>
              <td>
                <AGCPBadge tone={badgeTone(agent.risk_level)}>
                  {formatValue(agent.risk_level)}
                </AGCPBadge>
              </td>
              <td>{formatValue(agent.framework)}</td>
            </tr>
          ))}
        </tbody>
      </AGCPDataTable>
    </AGCPPanel>
  );
}
