"use client";

import { useEffect, useState } from "react";
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
      <section className="data-panel" aria-live="polite">
        <div className="state-message">
          <strong>Loading agents</strong>
          <p>Requesting registered agents from {getApiBaseUrl()}.</p>
        </div>
      </section>
    );
  }

  if (state.status === "error") {
    return (
      <section className="data-panel" role="alert">
        <div className="state-message error">
          <strong>Unable to load agents</strong>
          <p>{state.message}</p>
          <p>
            Check that the backend is running and that
            NEXT_PUBLIC_AGCP_API_BASE_URL points to the API base URL.
          </p>
        </div>
      </section>
    );
  }

  if (state.agents.length === 0) {
    return (
      <section className="data-panel">
        <div className="state-message">
          <strong>No agents registered</strong>
          <p>
            Once agents are created through the backend API, they will appear
            here with ownership, environment, status, risk level, and framework
            metadata.
          </p>
        </div>
      </section>
    );
  }

  return (
    <section className="data-panel" aria-label="Registered agents">
      <div className="table-scroll">
        <table className="data-table">
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
                  <strong>{agent.name}</strong>
                </td>
                <td>{ownerDisplay(agent)}</td>
                <td>{formatValue(agent.owner_type)}</td>
                <td>{formatValue(agent.environment)}</td>
                <td>
                  <span className="table-pill">{formatValue(agent.status)}</span>
                </td>
                <td>
                  <span className={`table-pill risk-${agent.risk_level}`}>
                    {formatValue(agent.risk_level)}
                  </span>
                </td>
                <td>{formatValue(agent.framework)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
