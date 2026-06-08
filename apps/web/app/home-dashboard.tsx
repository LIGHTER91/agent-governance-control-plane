"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { AgentRecord, fetchAgents } from "./lib/agents";
import {
  HumanApprovalRecord,
  fetchHumanApprovals
} from "./lib/human-approvals";
import { getApiBaseUrl } from "./lib/api";

type LoadState<T> =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; data: T };

const primaryRoutes = [
  {
    href: "/agents",
    label: "Agents",
    description:
      "Review registered Agents and open connected Agent Governance Profiles.",
    backend: "GET /agents"
  },
  {
    href: "/human-approvals",
    label: "Human Approvals",
    description:
      "Review pending or completed HumanApproval records returned by the backend.",
    backend: "GET /human-approvals"
  },
  {
    href: "/evidence",
    label: "Evidence",
    description:
      "Load bounded Evidence Bundle JSON for one Agent on explicit user action.",
    backend: "GET /agents/{agent_id}/evidence-bundle"
  },
  {
    href: "/audit",
    label: "Audit",
    description:
      "Reserved for append-only governance event review; no synthetic audit data.",
    backend: "Available in detail pages"
  },
  {
    href: "/policies",
    label: "Policies",
    description:
      "Manage Policy and PolicyRule records through existing backend APIs.",
    backend: "GET /policies"
  },
  {
    href: "/settings",
    label: "Settings",
    description:
      "Placeholder for local configuration notes; no auth or deployment setup.",
    backend: "Not connected yet"
  }
];

function errorMessage(error: unknown, fallback: string) {
  return error instanceof Error ? error.message : fallback;
}

function metricValue<T>(
  state: LoadState<T>,
  formatter: (data: T) => string
) {
  if (state.status === "loading") {
    return "Loading";
  }

  if (state.status === "error") {
    return "Unavailable";
  }

  return formatter(state.data);
}

export function HomeDashboard() {
  const [agentsState, setAgentsState] = useState<LoadState<AgentRecord[]>>({
    status: "loading"
  });
  const [approvalsState, setApprovalsState] = useState<
    LoadState<HumanApprovalRecord[]>
  >({ status: "loading" });

  useEffect(() => {
    const controller = new AbortController();

    fetchAgents(controller.signal)
      .then((agents) => {
        setAgentsState({ status: "ready", data: agents });
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) {
          return;
        }

        setAgentsState({
          status: "error",
          message: errorMessage(error, "Unable to load Agents from the backend.")
        });
      });

    fetchHumanApprovals("all", controller.signal)
      .then((approvals) => {
        setApprovalsState({ status: "ready", data: approvals });
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) {
          return;
        }

        setApprovalsState({
          status: "error",
          message: errorMessage(
            error,
            "Unable to load HumanApprovals from the backend."
          )
        });
      });

    return () => {
      controller.abort();
    };
  }, []);

  const pendingApprovalCount = useMemo(() => {
    if (approvalsState.status !== "ready") {
      return 0;
    }

    return approvalsState.data.filter((approval) => approval.status === "pending")
      .length;
  }, [approvalsState]);

  const hasBackendError =
    agentsState.status === "error" || approvalsState.status === "error";

  return (
    <>
      <section className="page-header">
        <p className="eyebrow">Product Dashboard</p>
        <h2>Agent Governance Control Plane</h2>
        <p>
          Use this connected workspace to inspect registered Agents, policy
          decisions, HumanApprovals, audit context, and bounded Evidence Bundle
          exports from the real backend API.
        </p>
      </section>

      <section className="status-band dashboard-intro">
        <div>
          <strong>Backend API</strong>
          <p>{getApiBaseUrl()}</p>
        </div>
        <p>
          Dashboard summaries below use existing endpoints only. If the backend
          is unavailable, the UI reports that state instead of substituting demo
          records or invented production metrics.
        </p>
      </section>

      {hasBackendError ? (
        <section className="data-panel dashboard-alert" role="alert">
          <div className="state-message error">
            <strong>Backend data unavailable</strong>
            {agentsState.status === "error" ? <p>{agentsState.message}</p> : null}
            {approvalsState.status === "error" ? (
              <p>{approvalsState.message}</p>
            ) : null}
            <p>
              Confirm that the API is running and that
              NEXT_PUBLIC_AGCP_API_BASE_URL points to the backend base URL.
            </p>
          </div>
        </section>
      ) : null}

      <section className="status-grid dashboard-metrics" aria-label="Dashboard summary">
        <article className="status-card">
          <span className="status-label foundation">Real API</span>
          <strong>Registered Agents</strong>
          <p className="metric-value">
            {metricValue(agentsState, (agents) => String(agents.length))}
          </p>
          <p>Loaded from GET /agents.</p>
        </article>

        <article className="status-card">
          <span className="status-label foundation">Real API</span>
          <strong>Pending Human Approvals</strong>
          <p className="metric-value">
            {metricValue(approvalsState, () => String(pendingApprovalCount))}
          </p>
          <p>Derived from GET /human-approvals where status is pending.</p>
        </article>

        <article className="status-card">
          <span className="status-label limited">Manual</span>
          <strong>Evidence Bundle</strong>
          <p className="metric-value">On demand</p>
          <p>Evidence JSON is loaded only after a reviewer enters an Agent ID.</p>
        </article>
      </section>

      {agentsState.status === "ready" && agentsState.data.length === 0 ? (
        <section className="data-panel">
          <div className="state-message">
            <strong>No agents registered</strong>
            <p>
              Create Agents through the backend or run the local full-stack demo
              seed, then refresh this dashboard.
            </p>
          </div>
        </section>
      ) : null}

      <h3 className="section-title">Connected Routes</h3>
      <section className="work-grid route-card-grid" aria-label="Connected routes">
        {primaryRoutes.map((route) => (
          <Link className="work-item route-card" href={route.href} key={route.href}>
            <strong>{route.label}</strong>
            <p>{route.description}</p>
            <span>{route.backend}</span>
          </Link>
        ))}
      </section>
    </>
  );
}
