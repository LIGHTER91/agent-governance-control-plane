"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { ApiRequestError, getApiBaseUrl } from "../lib/api";
import {
  ServiceActorRegistrySummaryItem,
  fetchServiceActorRegistrySummary
} from "../lib/service-actors";

type IntegrationStatus =
  | "not_configured"
  | "design_only"
  | "spike"
  | "connected"
  | "error";

type RuntimeMode =
  | "telemetry_only"
  | "simulation"
  | "enforcement"
  | "resume_after_human_approval";

type IntegrationCard = {
  name: string;
  status: IntegrationStatus;
  statusDetail: string;
  supportedModes: RuntimeMode[];
  authIdentity: string;
  scopeRequirements: string[];
  setupNotes: string[];
  docs: string[];
};

type ServiceActorSummaryState =
  | { status: "loading" }
  | { status: "disabled"; message: string }
  | { status: "error"; message: string }
  | { status: "ready"; items: ServiceActorRegistrySummaryItem[] };

const integrations: IntegrationCard[] = [
  {
    name: "Custom Runtime Gateway API",
    status: "connected",
    statusDetail:
      "Runtime Gateway endpoints exist in AGCP; external callers still need their own wrapper or middleware.",
    supportedModes: [
      "telemetry_only",
      "simulation",
      "enforcement",
      "resume_after_human_approval"
    ],
    authIdentity:
      "service actor resolved from X-AGCP-API-Key, with config auth by default or registry auth when enabled",
    scopeRequirements: [
      "telemetry:write",
      "runtime:decision",
      "runtime:resume",
      "agent_ids",
      "environments",
      "runtime_modes",
      "tool_names"
    ],
    setupNotes: [
      "Call POST /runtime/tool-calls/decision before the local tool executes.",
      "Read decision and proceed; the caller/orchestrator is responsible for respecting proceed=true/false.",
      "Use POST /runtime/tool-calls/resume only after a linked HumanApproval has been approved.",
      "Do not send raw prompts, source contents, credentials, tokens, or tool payloads."
    ],
    docs: [
      "docs/RUNTIME_GATEWAY_DESIGN.md",
      "docs/RUNTIME_GATEWAY_ENFORCEMENT_MODE.md",
      "docs/examples/runtime_tool_wrapper_example.py"
    ]
  },
  {
    name: "LangGraph adapter spike",
    status: "spike",
    statusDetail:
      "Dependency-free example code exists, but there is no packaged LangGraph adapter.",
    supportedModes: [
      "telemetry_only",
      "simulation",
      "enforcement",
      "resume_after_human_approval"
    ],
    authIdentity:
      "service actor API key used by the LangGraph wrapper around selected tools",
    scopeRequirements: [
      "runtime:decision",
      "runtime:resume",
      "agent_ids",
      "runtime_modes",
      "tool_names"
    ],
    setupNotes: [
      "Wrap selected LangGraph tools so AGCP is called before side-effecting actions.",
      "Keep graph state, routing, checkpoints, and tool execution inside the LangGraph app.",
      "Treat the spike as integration guidance until adapter packaging and stronger auth are designed."
    ],
    docs: [
      "docs/LANGGRAPH_INTEGRATION_DESIGN.md",
      "docs/examples/langgraph_adapter_spike.py"
    ]
  },
  {
    name: "n8n template/node design",
    status: "design_only",
    statusDetail:
      "Placeholder for a future workflow node or template; no node package is implemented.",
    supportedModes: ["telemetry_only", "simulation"],
    authIdentity:
      "service actor API key stored by the n8n deployment, never by AGCP frontend pages",
    scopeRequirements: ["telemetry:write", "runtime:decision", "agent_ids"],
    setupNotes: [
      "Use a workflow node before governed actions to request a decision.",
      "The n8n workflow remains responsible for branching on proceed.",
      "Resume after HumanApproval needs a dedicated workflow pattern before it is advertised as ready."
    ],
    docs: ["docs/RUNTIME_GATEWAY_DESIGN.md"]
  },
  {
    name: "Dataiku plugin/design",
    status: "design_only",
    statusDetail:
      "Placeholder for Dataiku DSS governance integration design; no plugin is implemented here.",
    supportedModes: ["telemetry_only", "simulation"],
    authIdentity:
      "service actor API key scoped to the Dataiku project, flow, or governed action path",
    scopeRequirements: ["telemetry:write", "runtime:decision", "environments"],
    setupNotes: [
      "Report safe runtime or review events from existing Dataiku jobs or scenarios.",
      "Keep execution, data access, and project orchestration inside Dataiku.",
      "Do not expose raw Source contents or credentials through AGCP."
    ],
    docs: ["docs/RUNTIME_GATEWAY_DESIGN.md"]
  },
  {
    name: "MCP gateway/control pattern",
    status: "design_only",
    statusDetail:
      "Control pattern for MCP servers or gateways; AGCP does not become an MCP server executor.",
    supportedModes: ["telemetry_only", "simulation", "enforcement"],
    authIdentity:
      "service actor API key assigned to the MCP gateway or host integration",
    scopeRequirements: ["runtime:decision", "agent_ids", "tool_names"],
    setupNotes: [
      "Put the decision call in the host or gateway before invoking governed MCP tools.",
      "The MCP host remains responsible for tool execution and blocking behavior.",
      "Use safe tool names, target IDs, and source IDs instead of raw payloads."
    ],
    docs: ["docs/RUNTIME_GATEWAY_DESIGN.md"]
  },
  {
    name: "generic webhook/API integration",
    status: "not_configured",
    statusDetail:
      "Generic pattern for runtimes that can call HTTP before or after governed actions.",
    supportedModes: ["telemetry_only", "simulation", "enforcement"],
    authIdentity:
      "service actor API key scoped to the runtime, deployment, Agent, and action mode",
    scopeRequirements: [
      "telemetry:write",
      "runtime:decision",
      "agent_ids",
      "runtime_modes"
    ],
    setupNotes: [
      "Start with telemetry-only or simulation where blocking would be risky.",
      "Move to enforcement only when the caller consistently honors proceed.",
      "Use Evidence Bundle and Runtime activity to review what happened."
    ],
    docs: ["docs/examples/generic_runtime_adapter_example.py"]
  }
];

const statusLabels: Record<IntegrationStatus, string> = {
  connected: "connected",
  design_only: "design_only",
  error: "error",
  not_configured: "not_configured",
  spike: "spike"
};

const statusDescriptions: Record<IntegrationStatus, string> = {
  connected:
    "AGCP has a local API surface for this integration path; it does not prove any external runtime is enforcing decisions.",
  design_only:
    "Design placeholder. Use for planning and discussion, not as an adapter package.",
  error: "A dynamic integration status check failed.",
  not_configured:
    "No external runtime connection is configured or verified from this UI.",
  spike:
    "Spike/example code exists to explore the pattern, but packaging and hardening remain future work."
};

const modeLabels: Record<RuntimeMode, string> = {
  enforcement: "enforcement",
  resume_after_human_approval: "resume_after_human_approval",
  simulation: "simulation",
  telemetry_only: "telemetry_only"
};

function formatValue(value: string) {
  return value
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function formatCount(count: number, singular: string, plural = `${singular}s`) {
  return `${count} ${count === 1 ? singular : plural}`;
}

function serviceActorErrorMessage(error: unknown) {
  if (error instanceof ApiRequestError && error.status === 503) {
    return (
      "Service actor registry admin is disabled. Config-based service actor auth remains the default."
    );
  }

  return error instanceof Error
    ? error.message
    : "Unable to load Service Actor registry summary.";
}

function statusCount<T extends { status: string }>(items: T[], status: string) {
  return items.filter((item) => item.status === status).length;
}

function scopeRuleValues(items: ServiceActorRegistrySummaryItem[]) {
  const values = new Set<string>();

  for (const item of items) {
    for (const rule of item.scopeRules) {
      for (const agentId of rule.agent_ids) {
        values.add(`agent:${agentId}`);
      }

      for (const environment of rule.environments) {
        values.add(`environment:${environment}`);
      }

      for (const runtimeMode of rule.runtime_modes) {
        values.add(`runtime_mode:${runtimeMode}`);
      }

      for (const toolName of rule.tool_names) {
        values.add(`tool:${toolName}`);
      }
    }
  }

  return Array.from(values).slice(0, 8);
}

export function IntegrationHub() {
  const [serviceActorState, setServiceActorState] =
    useState<ServiceActorSummaryState>({ status: "loading" });

  useEffect(() => {
    const controller = new AbortController();

    fetchServiceActorRegistrySummary(controller.signal)
      .then((items) => {
        setServiceActorState({ status: "ready", items });
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) {
          return;
        }

        const message = serviceActorErrorMessage(error);
        setServiceActorState({
          status:
            error instanceof ApiRequestError && error.status === 503
              ? "disabled"
              : "error",
          message
        });
      });

    return () => {
      controller.abort();
    };
  }, []);

  return (
    <div className="integration-hub">
      <section className="page-header">
        <p className="eyebrow">Integration Hub</p>
        <h2>Runtime connections for governed agent stacks.</h2>
        <p>
          {
            "AGCP governs decisions and evidence for external runtimes. AGCP does not execute tools, run workflows, or replace orchestrators; the caller/orchestrator is responsible for respecting proceed=true/false."
          }
        </p>
      </section>

      <section className="policy-boundary integration-boundary">
        <strong>Governance boundary</strong>
        <p>
          Integration Hub explains how runtimes call AGCP through telemetry,
          simulation, enforcement, and resume-after-HumanApproval patterns.
          Service Actors, scopes, key status, and runtime modes make those
          callers reviewable without exposing plaintext API keys.
        </p>
      </section>

      <section className="integration-layout">
        <section className="evidence-section">
          <header className="evidence-section-header">
            <div>
              <h3>Runtime connection statuses</h3>
              <p>
                Status is product guidance for setup review, not a claim that
                any adapter package is complete.
              </p>
            </div>
            <span>{integrations.length}</span>
          </header>
          <div className="integration-status-grid">
            {Object.entries(statusDescriptions).map(([status, detail]) => (
              <div key={status}>
                <span className={`integration-status ${status}`}>
                  {status}
                </span>
                <p>{detail}</p>
              </div>
            ))}
          </div>
        </section>

        <ServiceActorRegistrySummary state={serviceActorState} />
      </section>

      <section
        className="integration-card-grid"
        aria-label="Integration cards"
      >
        {integrations.map((integration) => (
          <IntegrationConnectionCard
            integration={integration}
            key={integration.name}
          />
        ))}
      </section>

      <section className="integration-setup-grid">
        <SetupSnippet
          title="Custom Runtime Gateway API setup"
          summary="Use this pattern in any runtime wrapper or middleware that can call HTTP before a governed action."
          code={`POST /runtime/tool-calls/decision
X-AGCP-API-Key: <service-actor-api-key>

{
  "agent_id": "<agent-id>",
  "run_id": "<runtime-run-id>",
  "request_id": "<stable-request-id>",
  "tool_name": "send_email",
  "mode": "simulation",
  "purpose": "customer_support_answering",
  "source_ids": ["<source-id>"]
}

Read the response decision and proceed fields.
Execute the local tool only when proceed=true and decision=allow.`}
        />

        <SetupSnippet
          title="LangGraph adapter spike setup"
          summary="Use the existing spike as a wrapper pattern, while keeping graph execution in the LangGraph application."
          code={`from docs.examples.langgraph_adapter_spike import AgcpRuntimeGateway

gateway = AgcpRuntimeGateway(
    base_url="http://127.0.0.1:8000",
    api_key="<service-actor-api-key>",
)

# Wrap selected LangGraph tools before side-effecting actions.
# The wrapper calls AGCP, reads proceed, and returns a controlled result
# when deny or require_human_review is returned.`}
        />
      </section>
    </div>
  );
}

function IntegrationConnectionCard({
  integration
}: {
  integration: IntegrationCard;
}) {
  return (
    <article className="integration-card">
      <header>
        <span className={`integration-status ${integration.status}`}>
          {statusLabels[integration.status]}
        </span>
        <h3>{integration.name}</h3>
        <p>{integration.statusDetail}</p>
      </header>

      <section>
        <h4>Supported modes</h4>
        <ul className="chip-list">
          {integration.supportedModes.map((mode) => (
            <li key={mode}>{modeLabels[mode]}</li>
          ))}
        </ul>
      </section>

      <section>
        <h4>Expected auth identity</h4>
        <p>{integration.authIdentity}</p>
      </section>

      <section>
        <h4>Scope requirements</h4>
        <ul className="chip-list">
          {integration.scopeRequirements.map((scope) => (
            <li key={scope}>{scope}</li>
          ))}
        </ul>
      </section>

      <section>
        <h4>Safe setup notes</h4>
        <ul className="integration-note-list">
          {integration.setupNotes.map((note) => (
            <li key={note}>{note}</li>
          ))}
        </ul>
      </section>

      <section>
        <h4>Docs and examples</h4>
        <ul className="integration-doc-list">
          {integration.docs.map((doc) => (
            <li key={doc}>{doc}</li>
          ))}
        </ul>
      </section>
    </article>
  );
}

function ServiceActorRegistrySummary({
  state
}: {
  state: ServiceActorSummaryState;
}) {
  const summary = useMemo(() => {
    if (state.status !== "ready" || state.items.length === 0) {
      return null;
    }

    const actors = state.items.map((item) => item.actor);
    const apiKeys = state.items.flatMap((item) => item.apiKeys);
    const scopes = state.items.flatMap((item) => item.scopes);
    const scopeRules = state.items.flatMap((item) => item.scopeRules);

    return {
      activeActors: statusCount(actors, "active"),
      activeKeys: statusCount(apiKeys, "active"),
      disabledActors: statusCount(actors, "disabled"),
      expiredKeys: statusCount(apiKeys, "expired"),
      keyCount: apiKeys.length,
      retiringKeys: statusCount(apiKeys, "retiring"),
      revokedKeys: statusCount(apiKeys, "revoked"),
      safeRuleValues: scopeRuleValues(state.items),
      scopeCount: scopes.length,
      scopeRuleCount: scopeRules.length,
      serviceActorCount: actors.length
    };
  }, [state]);

  return (
    <section className="evidence-section integration-registry-summary">
      <header className="evidence-section-header">
        <div>
          <h3>Service Actor registry summary</h3>
          <p>
            GET /service-actors from {getApiBaseUrl()}; key metadata only, no
            plaintext API keys or hashes.
          </p>
        </div>
        <span>read-only</span>
      </header>

      {state.status === "loading" ? (
        <div className="state-message compact" aria-live="polite">
          <strong>Loading Service Actor registry summary</strong>
          <p>
            Requesting service actor, API key status, scope, and scope rule
            metadata from the backend.
          </p>
        </div>
      ) : null}

      {state.status === "disabled" ? (
        <div className="state-message compact">
          <strong>Registry admin disabled</strong>
          <p>{state.message}</p>
          <p>
            AGCP_SERVICE_ACTOR_REGISTRY_ENABLED=false keeps config-based auth as
            the default integration path.
          </p>
        </div>
      ) : null}

      {state.status === "error" ? (
        <div className="state-message error compact" role="alert">
          <strong>Unable to load Service Actor registry summary</strong>
          <p>{state.message}</p>
        </div>
      ) : null}

      {state.status === "ready" && state.items.length === 0 ? (
        <div className="state-message compact">
          <strong>No Service Actors found</strong>
          <p>
            Registry admin APIs are reachable, but no registry-backed
            integration identities have been seeded yet.
          </p>
        </div>
      ) : null}

      {state.status === "ready" && summary ? (
        <>
          <div className="detail-count-grid integration-counts">
            <div>
              <span>service actors</span>
              <strong>{summary.serviceActorCount}</strong>
            </div>
            <div>
              <span>active</span>
              <strong>{summary.activeActors}</strong>
            </div>
            <div>
              <span>disabled</span>
              <strong>{summary.disabledActors}</strong>
            </div>
            <div>
              <span>api keys</span>
              <strong>{summary.keyCount}</strong>
            </div>
            <div>
              <span>scopes</span>
              <strong>{summary.scopeCount}</strong>
            </div>
          </div>

          <div className="integration-registry-details">
            <div>
              <h4>Key status summary</h4>
              <ul className="chip-list">
                <li>{formatCount(summary.activeKeys, "active key")}</li>
                <li>{formatCount(summary.retiringKeys, "retiring key")}</li>
                <li>{formatCount(summary.revokedKeys, "revoked key")}</li>
                <li>{formatCount(summary.expiredKeys, "expired key")}</li>
              </ul>
            </div>

            <div>
              <h4>Scope rule coverage</h4>
              {summary.safeRuleValues.length > 0 ? (
                <ul className="chip-list">
                  {summary.safeRuleValues.map((value) => (
                    <li key={value}>{value}</li>
                  ))}
                </ul>
              ) : (
                <p>No Agent, environment, runtime mode, or tool rule values.</p>
              )}
              <p>
                {formatCount(summary.scopeRuleCount, "scope rule")} loaded from
                GET /service-actors/{`{service_actor_id}`}/scope-rules.
              </p>
            </div>
          </div>

          <ServiceActorTable items={state.items} />
        </>
      ) : null}
    </section>
  );
}

function ServiceActorTable({
  items
}: {
  items: ServiceActorRegistrySummaryItem[];
}) {
  if (items.length === 0) {
    return null;
  }

  return (
    <div className="table-scroll">
      <table className="data-table integration-actor-table">
        <thead>
          <tr>
            <th>Service Actor</th>
            <th>Status</th>
            <th>API key status</th>
            <th>Scopes</th>
            <th>Scope rules</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={item.actor.id}>
              <td>
                <strong>{item.actor.display_name}</strong>
                <div className="id-cell">{item.actor.actor_id}</div>
                <div className="id-cell">{item.actor.id}</div>
              </td>
              <td>
                <span className={`table-pill service-${item.actor.status}`}>
                  {formatValue(item.actor.status)}
                </span>
              </td>
              <td>
                <ul className="integration-compact-list">
                  {item.apiKeys.length > 0 ? (
                    item.apiKeys.map((apiKey) => (
                      <li key={apiKey.key_id}>
                        <span className="id-cell">{apiKey.key_id}</span>
                        <span className={`table-pill key-${apiKey.status}`}>
                          {formatValue(apiKey.status)}
                        </span>
                      </li>
                    ))
                  ) : (
                    <li>No key metadata</li>
                  )}
                </ul>
              </td>
              <td>
                <ul className="chip-list">
                  {item.scopes.length > 0 ? (
                    item.scopes.map((scope) => (
                      <li key={scope.id}>{scope.scope}</li>
                    ))
                  ) : (
                    <li>No scopes</li>
                  )}
                </ul>
              </td>
              <td>{formatCount(item.scopeRules.length, "rule")}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function SetupSnippet({
  code,
  summary,
  title
}: {
  code: string;
  summary: string;
  title: string;
}) {
  return (
    <section className="evidence-section integration-snippet">
      <header className="evidence-section-header">
        <div>
          <h3>{title}</h3>
          <p>{summary}</p>
        </div>
        <span>setup notes</span>
      </header>
      <pre className="evidence-json-block">{code}</pre>
      <div className="integration-snippet-footer">
        <Link href="/runtime-gateway" className="row-link">
          Runtime activity and gateway overview
        </Link>
        <Link href="/evidence" className="row-link">
          Evidence Bundle review
        </Link>
      </div>
    </section>
  );
}
