"use client";

import { FormEvent, useState } from "react";
import {
  AGCPBadge,
  AGCPEmptyState,
  AGCPErrorState,
  AGCPPanel,
  AGCPSectionHeader
} from "../agcp-studio/primitives";
import { ApiRequestError, getApiBaseUrl } from "../lib/api";
import {
  EvidenceAccessGrant,
  EvidenceAgent,
  EvidenceAgentRun,
  EvidenceAuditLog,
  EvidenceBundle,
  EvidenceCapabilityReference,
  EvidenceCheckResult,
  EvidenceDataUsageProfile,
  EvidenceHumanApproval,
  EvidenceMetadata,
  EvidenceModelAssetReference,
  EvidencePolicyDecision,
  EvidencePolicyVersionReference,
  EvidenceSourceReference,
  EvidenceTraceEvent,
  fetchEvidenceBundle
} from "../lib/evidence";

type EvidenceState =
  | { status: "idle" }
  | { status: "loading"; agentId: string }
  | { status: "error"; agentId: string; message: string }
  | {
      status: "ready";
      agentId: string;
      bundle: EvidenceBundle;
      exportedAt: string;
    };

type EvidenceCounts = {
  access_grants: number;
  agent_runs: number;
  audit_logs: number;
  capability_references: number;
  check_results: number;
  data_usage_profiles: number;
  human_approvals: number;
  model_asset_references: number;
  policy_decisions: number;
  policy_versions: number;
  source_references: number;
  trace_events: number;
};

const EXPORT_WARNINGS = [
  "Evidence Bundle is an audit/review package; it does not certify legal compliance.",
  "The Evidence Bundle excludes raw prompts, source contents, secrets, tokens, credentials, and unsafe payloads.",
  "JSON remains the canonical bounded export for now; PDF export, cryptographic signing, and external GRC/SIEM integrations are out of scope."
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

function plainValue(value: string | number | boolean | null | undefined) {
  return value === null || value === undefined || value === ""
    ? "Not set"
    : String(value);
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

function joinList(values: string[]) {
  return values.length > 0 ? values.join(", ") : "None";
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
      setState({
        status: "ready",
        agentId: normalizedAgentId,
        bundle,
        exportedAt: new Date().toISOString()
      });
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
    <div className="agcp-evidence-workspace">
      <AGCPPanel aria-label="Evidence Bundle lookup">
        <AGCPSectionHeader
          eyebrow="manual export"
          title="Evidence Bundle lookup"
          description={`Requests GET /agents/{agent_id}/evidence-bundle from ${getApiBaseUrl()} only after this manual action.`}
          meta={<AGCPBadge tone="ok">canonical JSON</AGCPBadge>}
        />
        <form className="agcp-evidence-lookup" onSubmit={handleSubmit}>
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
          <button type="submit">
            {state.status === "loading"
              ? "Loading Evidence Bundle"
              : "Load Evidence Bundle"}
          </button>
        </form>
      </AGCPPanel>

      {state.status === "idle" ? (
        <AGCPPanel>
          <AGCPEmptyState title="No Evidence Bundle loaded">
            Enter an Agent ID to review the bounded JSON evidence package and
            download the canonical artifact returned by the backend.
          </AGCPEmptyState>
        </AGCPPanel>
      ) : null}

      {state.status === "loading" ? (
        <AGCPPanel aria-live="polite">
          <AGCPEmptyState title="Loading Evidence Bundle">
            Requesting evidence for agent_id {state.agentId}.
          </AGCPEmptyState>
        </AGCPPanel>
      ) : null}

      {state.status === "error" ? (
        <AGCPPanel>
          <AGCPErrorState title="Unable to load Evidence Bundle">
            {state.message}
          </AGCPErrorState>
        </AGCPPanel>
      ) : null}

      {state.status === "ready" ? (
        <EvidenceBundleSections
          agentId={state.agentId}
          bundle={state.bundle}
          exportedAt={state.exportedAt}
        />
      ) : null}
    </div>
  );
}

function EvidenceBundleSections({
  agentId,
  bundle,
  exportedAt
}: {
  agentId: string;
  bundle: EvidenceBundle;
  exportedAt: string;
}) {
  const policyVersions = policyVersionReferences(bundle);
  const counts = evidenceCounts(bundle, policyVersions.length);

  return (
    <div className="evidence-layout agcp-evidence-workspace">
      <ExportWarnings />
      <ExportMetadataSection
        agentId={agentId}
        bundle={bundle}
        counts={counts}
        exportedAt={exportedAt}
      />
      <EvidenceChainSummary bundle={bundle} counts={counts} />
      <CanonicalJsonSection
        agentId={agentId}
        bundle={bundle}
        exportedAt={exportedAt}
      />
      <AgentSection agent={bundle.agent} />
      <AccessGrantsSection accessGrants={bundle.access_grants} />
      <InventoryReferencesSection
        capabilities={bundle.capability_references}
        modelAssets={bundle.model_asset_references}
        sources={bundle.source_references}
      />
      <DataUsageProfilesSection profiles={bundle.data_usage_profiles} />
      <AgentRunsSection agentRuns={bundle.agent_runs} />
      <TraceEventsSection traceEvents={bundle.trace_events} />
      <PolicyDecisionsSection policyDecisions={bundle.policy_decisions} />
      <PolicyVersionsSection policyVersions={policyVersions} />
      <CheckResultsSection checkResults={bundle.check_results} />
      <HumanApprovalsSection humanApprovals={bundle.human_approvals} />
      <AuditLogsSection auditLogs={bundle.audit_logs} />
    </div>
  );
}

function ExportWarnings() {
  return (
    <section className="evidence-section evidence-warning-panel">
      <SectionHeader title="export_warnings" count={EXPORT_WARNINGS.length} />
      <ul className="evidence-warning-list">
        {EXPORT_WARNINGS.map((warning) => (
          <li key={warning}>{warning}</li>
        ))}
      </ul>
    </section>
  );
}

function ExportMetadataSection({
  agentId,
  bundle,
  counts,
  exportedAt
}: {
  agentId: string;
  bundle: EvidenceBundle;
  counts: EvidenceCounts;
  exportedAt: string;
}) {
  const metadataRows = [
    ["exported_at", formatTimestamp(exportedAt)],
    ["exported_by", "Not exposed by current backend response"],
    ["agent_id", bundle.agent.id || agentId],
    ["agent_name", bundle.agent.name],
    ["warning_count", String(EXPORT_WARNINGS.length)]
  ];

  return (
    <section className="evidence-section">
      <SectionHeader title="safe_export_metadata" count={metadataRows.length} />
      <dl className="evidence-fields">
        {metadataRows.map(([label, value]) => (
          <div key={label}>
            <dt>{label}</dt>
            <dd className={label.endsWith("_id") ? "id-cell" : undefined}>
              {value}
            </dd>
          </div>
        ))}
      </dl>
      <div className="evidence-count-grid" aria-label="Evidence Bundle counts">
        {Object.entries(counts).map(([label, count]) => (
          <div key={label}>
            <span>{label}</span>
            <strong>{count}</strong>
          </div>
        ))}
      </div>
    </section>
  );
}

function EvidenceChainSummary({
  bundle,
  counts
}: {
  bundle: EvidenceBundle;
  counts: EvidenceCounts;
}) {
  const chainItems = [
    {
      title: "Agent",
      summary: `${bundle.agent.name} in ${formatValue(
        bundle.agent.environment
      )} with ${formatValue(bundle.agent.risk_level)} risk.`
    },
    {
      title: "Access Grants",
      summary: `${counts.access_grants} declared grants, ${counts.capability_references} Capability references, ${counts.source_references} Source references, and ${counts.model_asset_references} ModelAsset references.`
    },
    {
      title: "Data Usage Profile summaries",
      summary: `${counts.data_usage_profiles} safe Source usage profiles for granted Sources.`
    },
    {
      title: "TraceEvents",
      summary: `${counts.trace_events} runtime or telemetry events linked to this Agent.`
    },
    {
      title: "PolicyDecisions",
      summary: `${counts.policy_decisions} persisted decisions explain allow, deny, review, or not-applicable outcomes.`
    },
    {
      title: "PolicyVersion references",
      summary: `${counts.policy_versions} compact active PolicyVersion references are included where decisions or checks recorded them.`
    },
    {
      title: "CheckResults",
      summary: `${counts.check_results} bounded check summaries are evidence inputs, not standalone enforcement decisions.`
    },
    {
      title: "HumanApprovals",
      summary: `${counts.human_approvals} human oversight records show requested and reviewed decisions.`
    },
    {
      title: "AuditLogs",
      summary: `${counts.audit_logs} append-only audit entries provide mutation and export context.`
    }
  ];

  return (
    <section className="evidence-section">
      <SectionHeader title="human_readable_evidence_chain" count={chainItems.length} />
      <ol className="evidence-chain">
        {chainItems.map((item) => (
          <li key={item.title}>
            <strong>{item.title}</strong>
            <p>{item.summary}</p>
          </li>
        ))}
      </ol>
    </section>
  );
}

function CanonicalJsonSection({
  agentId,
  bundle,
  exportedAt
}: {
  agentId: string;
  bundle: EvidenceBundle;
  exportedAt: string;
}) {
  const jsonText = JSON.stringify(bundle, null, 2);

  return (
    <section className="evidence-section">
      <AGCPSectionHeader
        eyebrow="artifact"
        title="canonical_json_export"
        description="Raw JSON remains the canonical Evidence Bundle artifact returned by the backend."
        actions={
          <button
            className="secondary-action"
            type="button"
            onClick={() => downloadEvidenceBundle(agentId, bundle, exportedAt)}
          >
            Download Evidence Bundle JSON
          </button>
        }
      />
      <pre className="evidence-json-block">{jsonText}</pre>
    </section>
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
            <dd>{plainValue(value)}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}

function AccessGrantsSection({
  accessGrants
}: {
  accessGrants: EvidenceAccessGrant[];
}) {
  return (
    <section className="evidence-section">
      <SectionHeader title="access_grants" count={accessGrants.length} />
      {accessGrants.length === 0 ? (
        <EmptySection />
      ) : (
        <div className="table-scroll">
          <table className="data-table evidence-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Name</th>
                <th>Target</th>
                <th>Status</th>
                <th>Risk</th>
                <th>Reason</th>
                <th>Granted By</th>
                <th>Expires</th>
                <th>Metadata</th>
              </tr>
            </thead>
            <tbody>
              {accessGrants.map((grant) => (
                <tr key={grant.id}>
                  <td className="id-cell">{grant.id}</td>
                  <td>{grant.name}</td>
                  <td>
                    <span className="table-pill">
                      {formatValue(grant.target_type)}
                    </span>
                    <div className="id-cell">
                      {grant.target_id || grant.external_ref || "Not set"}
                    </div>
                  </td>
                  <td>{formatValue(grant.status)}</td>
                  <td>{formatValue(grant.risk_level)}</td>
                  <td>{plainValue(grant.reason)}</td>
                  <td className="id-cell">
                    {grant.granted_by_actor_type}:{grant.granted_by_actor_id}
                  </td>
                  <td>{formatTimestamp(grant.expires_at)}</td>
                  <td>
                    <pre className="metadata-block">
                      {metadataText(grant.metadata)}
                    </pre>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

function InventoryReferencesSection({
  capabilities,
  modelAssets,
  sources
}: {
  capabilities: EvidenceCapabilityReference[];
  modelAssets: EvidenceModelAssetReference[];
  sources: EvidenceSourceReference[];
}) {
  return (
    <section className="evidence-section">
      <SectionHeader
        title="inventory_references"
        count={capabilities.length + sources.length + modelAssets.length}
      />
      <div className="evidence-reference-grid">
        <CapabilityReferences capabilities={capabilities} />
        <SourceReferences sources={sources} />
        <ModelAssetReferences modelAssets={modelAssets} />
      </div>
    </section>
  );
}

function CapabilityReferences({
  capabilities
}: {
  capabilities: EvidenceCapabilityReference[];
}) {
  return (
    <section className="evidence-reference-group">
      <h4>Capability references</h4>
      {capabilities.length === 0 ? (
        <p>No Capability references in this Evidence Bundle.</p>
      ) : (
        <ul>
          {capabilities.map((capability) => (
            <li key={capability.id}>
              <strong>{capability.name}</strong>
              <span>{formatValue(capability.capability_type)}</span>
              <span>{formatValue(capability.status)}</span>
              <span className="id-cell">{capability.id}</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function SourceReferences({ sources }: { sources: EvidenceSourceReference[] }) {
  return (
    <section className="evidence-reference-group">
      <h4>Source references</h4>
      {sources.length === 0 ? (
        <p>No Source references in this Evidence Bundle.</p>
      ) : (
        <ul>
          {sources.map((source) => (
            <li key={source.id}>
              <strong>{source.name}</strong>
              <span>{formatValue(source.source_type)}</span>
              <span>{formatValue(source.status)}</span>
              <span className="id-cell">{source.id}</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function ModelAssetReferences({
  modelAssets
}: {
  modelAssets: EvidenceModelAssetReference[];
}) {
  return (
    <section className="evidence-reference-group">
      <h4>ModelAsset references</h4>
      {modelAssets.length === 0 ? (
        <p>No ModelAsset references in this Evidence Bundle.</p>
      ) : (
        <ul>
          {modelAssets.map((modelAsset) => (
            <li key={modelAsset.id}>
              <strong>{modelAsset.name}</strong>
              <span>{formatValue(modelAsset.model_type)}</span>
              <span>{formatValue(modelAsset.provider)}</span>
              <span className="id-cell">{modelAsset.id}</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function DataUsageProfilesSection({
  profiles
}: {
  profiles: EvidenceDataUsageProfile[];
}) {
  return (
    <section className="evidence-section">
      <SectionHeader
        title="data_usage_profile_summaries"
        count={profiles.length}
      />
      {profiles.length === 0 ? (
        <EmptySection />
      ) : (
        <div className="table-scroll">
          <table className="data-table evidence-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Source ID</th>
                <th>Classification</th>
                <th>Personal</th>
                <th>Sensitive</th>
                <th>Review</th>
                <th>Allowed Purposes</th>
                <th>Prohibited Purposes</th>
                <th>DPIA</th>
                <th>Review Expires</th>
                <th>Metadata</th>
              </tr>
            </thead>
            <tbody>
              {profiles.map((profile) => (
                <tr key={profile.id}>
                  <td className="id-cell">{profile.id}</td>
                  <td className="id-cell">{profile.source_id}</td>
                  <td>{formatValue(profile.data_classification)}</td>
                  <td>{plainValue(profile.contains_personal_data)}</td>
                  <td>{plainValue(profile.contains_sensitive_data)}</td>
                  <td>{formatValue(profile.review_status)}</td>
                  <td>{joinList(profile.allowed_purposes)}</td>
                  <td>{joinList(profile.prohibited_purposes)}</td>
                  <td>
                    {profile.dpia_required
                      ? plainValue(profile.dpia_reference)
                      : "Not required"}
                  </td>
                  <td>{formatTimestamp(profile.review_expires_at)}</td>
                  <td>
                    <pre className="metadata-block">
                      {metadataText(profile.metadata)}
                    </pre>
                  </td>
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
                  <td>{plainValue(run.summary)}</td>
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
                <th>PolicyVersion</th>
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
                    {plainValue(decision.trace_event_id)}
                  </td>
                  <td>{policyLabel(decision)}</td>
                  <td>{ruleLabel(decision)}</td>
                  <td>{policyVersionLabel(decision.policy_version)}</td>
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

function CheckResultsSection({
  checkResults
}: {
  checkResults: EvidenceCheckResult[];
}) {
  return (
    <section className="evidence-section">
      <SectionHeader title="check_results" count={checkResults.length} />
      {checkResults.length === 0 ? (
        <EmptySection />
      ) : (
        <div className="table-scroll">
          <table className="data-table evidence-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Outcome</th>
                <th>Confidence</th>
                <th>Check Tool</th>
                <th>Target</th>
                <th>Policy Decision ID</th>
                <th>PolicyVersion</th>
                <th>Summary</th>
                <th>Reason</th>
                <th>Metadata</th>
                <th>Created</th>
              </tr>
            </thead>
            <tbody>
              {checkResults.map((result) => (
                <tr key={result.check_result_id}>
                  <td className="id-cell">{result.check_result_id}</td>
                  <td>{formatValue(result.outcome)}</td>
                  <td>{formatValue(result.confidence)}</td>
                  <td>
                    {plainValue(result.check_tool_name)}
                    <div>{formatValue(result.check_tool_type)}</div>
                  </td>
                  <td>
                    <span className="table-pill">
                      {formatValue(result.target_type)}
                    </span>
                    <div className="id-cell">
                      {plainValue(result.target_id)}
                    </div>
                  </td>
                  <td className="id-cell">
                    {plainValue(result.policy_decision_id)}
                  </td>
                  <td>{policyVersionLabel(result.policy_version)}</td>
                  <td>{result.summary}</td>
                  <td>{plainValue(result.reason)}</td>
                  <td>
                    <pre className="metadata-block">
                      {metadataText(result.metadata)}
                    </pre>
                  </td>
                  <td>{formatTimestamp(result.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

function PolicyVersionsSection({
  policyVersions
}: {
  policyVersions: EvidencePolicyVersionReference[];
}) {
  return (
    <section className="evidence-section">
      <SectionHeader title="policy_version_references" count={policyVersions.length} />
      {policyVersions.length === 0 ? (
        <EmptySection />
      ) : (
        <div className="table-scroll">
          <table className="data-table evidence-table">
            <thead>
              <tr>
                <th>PolicyVersion ID</th>
                <th>Policy ID</th>
                <th>Version</th>
                <th>Status</th>
                <th>Activated</th>
                <th>Change Summary</th>
              </tr>
            </thead>
            <tbody>
              {policyVersions.map((version) => (
                <tr key={version.policy_version_id}>
                  <td className="id-cell">{version.policy_version_id}</td>
                  <td className="id-cell">{version.policy_id}</td>
                  <td>{version.version_number}</td>
                  <td>{formatValue(version.status)}</td>
                  <td>{formatTimestamp(version.activated_at)}</td>
                  <td>{plainValue(version.change_summary)}</td>
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
                    {plainValue(approval.policy_decision_id)}
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
                  <td>{plainValue(approval.reason)}</td>
                  <td>{plainValue(approval.decision_note)}</td>
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

function SectionHeader({ title, count }: { title: string; count: number }) {
  return (
    <AGCPSectionHeader
      eyebrow="evidence"
      title={title}
      meta={<AGCPBadge tone={count > 0 ? "purple" : "muted"}>{count}</AGCPBadge>}
    />
  );
}

function EmptySection() {
  return (
    <AGCPEmptyState title="No records in this section">
      The backend returned an empty list for this evidence category.
    </AGCPEmptyState>
  );
}

function policyLabel(decision: EvidencePolicyDecision) {
  if (decision.policy) {
    return `${decision.policy.name} (${decision.policy.status})`;
  }

  return plainValue(decision.policy_id);
}

function ruleLabel(decision: EvidencePolicyDecision) {
  if (decision.rule) {
    return decision.rule.name;
  }

  return plainValue(decision.rule_id);
}

function policyVersionLabel(
  policyVersion: EvidencePolicyVersionReference | null | undefined
) {
  if (!policyVersion) {
    return "Not recorded";
  }

  return `v${policyVersion.version_number} (${policyVersion.status})`;
}

function evidenceCounts(
  bundle: EvidenceBundle,
  policyVersionReferenceCount: number
): EvidenceCounts {
  return {
    access_grants: bundle.access_grants.length,
    agent_runs: bundle.agent_runs.length,
    audit_logs: bundle.audit_logs.length,
    capability_references: bundle.capability_references.length,
    check_results: bundle.check_results.length,
    data_usage_profiles: bundle.data_usage_profiles.length,
    human_approvals: bundle.human_approvals.length,
    model_asset_references: bundle.model_asset_references.length,
    policy_decisions: bundle.policy_decisions.length,
    policy_versions: policyVersionReferenceCount,
    source_references: bundle.source_references.length,
    trace_events: bundle.trace_events.length
  };
}

function policyVersionReferences(bundle: EvidenceBundle) {
  const policyVersions = new Map<string, EvidencePolicyVersionReference>();

  for (const decision of bundle.policy_decisions) {
    if (decision.policy_version) {
      policyVersions.set(
        decision.policy_version.policy_version_id,
        decision.policy_version
      );
    }
  }

  for (const result of bundle.check_results) {
    if (result.policy_version) {
      policyVersions.set(
        result.policy_version.policy_version_id,
        result.policy_version
      );
    }
  }

  return Array.from(policyVersions.values());
}

function downloadEvidenceBundle(
  agentId: string,
  bundle: EvidenceBundle,
  exportedAt: string
) {
  const blob = new Blob([JSON.stringify(bundle, null, 2)], {
    type: "application/json"
  });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");

  link.href = url;
  link.download = `evidence-bundle-${agentId}-${fileTimestamp(exportedAt)}.json`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function fileTimestamp(value: string) {
  return value.replace(/[:.]/g, "-");
}
