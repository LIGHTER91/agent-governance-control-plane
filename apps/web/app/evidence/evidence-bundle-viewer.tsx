"use client";

import { FormEvent, ReactNode, useState } from "react";
import {
  AGCPBadge,
  AGCPEmptyState,
  AGCPErrorState,
  AGCPMetaGrid,
  AGCPPanel,
  AGCPSectionHeader
} from "../agcp-studio/primitives";
import { ApiRequestError, getApiBaseUrl } from "../lib/api";
import {
  EvidenceAuditLog,
  EvidenceBundle,
  EvidenceCheckResult,
  EvidenceHumanApproval,
  EvidenceMetadata,
  EvidencePolicyDecision,
  EvidencePolicyVersionReference,
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

const UNSAFE_METADATA_TERMS = [
  "api_key",
  "authorization",
  "credential",
  "password",
  "private_payload",
  "prompt",
  "raw",
  "secret",
  "source_content",
  "token"
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

function shortId(value: string | null | undefined) {
  if (!value) {
    return "Not set";
  }

  return value.length > 14 ? `${value.slice(0, 10)}...` : value;
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

function unsafeMetadataKey(key: string) {
  const normalizedKey = key.toLowerCase();
  return UNSAFE_METADATA_TERMS.some((term) => normalizedKey.includes(term));
}

function safeMetadata(metadata: EvidenceMetadata | null | undefined) {
  return Object.fromEntries(
    Object.entries(metadata || {}).filter(([key]) => !unsafeMetadataKey(key))
  );
}

function metadataText(metadata: EvidenceMetadata | null | undefined) {
  const filtered = safeMetadata(metadata);

  if (Object.keys(filtered).length === 0) {
    return "No safe metadata";
  }

  return JSON.stringify(filtered, null, 2);
}

function sanitizeForEvidenceDisplay(value: unknown): unknown {
  if (Array.isArray(value)) {
    return value.map((item) => sanitizeForEvidenceDisplay(item));
  }

  if (value && typeof value === "object") {
    return Object.fromEntries(
      Object.entries(value as Record<string, unknown>)
        .filter(([key]) => !unsafeMetadataKey(key))
        .map(([key, nestedValue]) => [key, sanitizeForEvidenceDisplay(nestedValue)])
    );
  }

  return value;
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
    <div className="evidence-explorer-workspace">
      <AGCPPanel className="evidence-lookup-panel" aria-label="Evidence Bundle lookup">
        <AGCPSectionHeader
          eyebrow="evidence explorer"
          title="Evidence Bundle lookup"
          description={`Requests GET /agents/{agent_id}/evidence-bundle from ${getApiBaseUrl()} only after this manual action.`}
          meta={<AGCPBadge tone="ok">real API only</AGCPBadge>}
        />
        <p className="evidence-helper-copy">
          Select an agent or decision with an available Evidence Bundle. AGCP will
          display only records returned by the backend.
        </p>
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
          <AGCPEmptyState title="No evidence bundle available yet">
            No evidence bundle available yet. Run .\scripts\dev-demo.ps1 to
            create a local metadata pre-check decision, then load the Agent ID
            returned by the demo.
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
        <EvidenceExplorerSections
          agentId={state.agentId}
          bundle={state.bundle}
          exportedAt={state.exportedAt}
        />
      ) : null}
    </div>
  );
}

function EvidenceExplorerSections({
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
    <div className="evidence-review-workspace">
      <ExportWarnings />
      <EvidenceChainOverview bundle={bundle} counts={counts} />
      <SubjectSection
        agentId={agentId}
        bundle={bundle}
        exportedAt={exportedAt}
      />
      <PolicyDecisionSection policyDecisions={bundle.policy_decisions} />
      <CheckResultsSection checkResults={bundle.check_results} />
      <HumanReviewSection humanApprovals={bundle.human_approvals} />
      <PolicyReviewEvidenceSection policyVersions={policyVersions} />
      <AuditTrailSection auditLogs={bundle.audit_logs} />
      <ExportBundleSection
        agentId={agentId}
        bundle={bundle}
        counts={counts}
        exportedAt={exportedAt}
      />
    </div>
  );
}

function ExportWarnings() {
  return (
    <AGCPPanel className="evidence-warning-panel">
      <AGCPSectionHeader
        eyebrow="export_warnings"
        title="Evidence safety boundaries"
        meta={<AGCPBadge tone="warn">{EXPORT_WARNINGS.length}</AGCPBadge>}
      />
      <ul className="evidence-warning-list">
        {EXPORT_WARNINGS.map((warning) => (
          <li key={warning}>{warning}</li>
        ))}
      </ul>
    </AGCPPanel>
  );
}

function EvidenceChainOverview({
  bundle,
  counts
}: {
  bundle: EvidenceBundle;
  counts: EvidenceCounts;
}) {
  const items = [
    ["Agent", "agent", bundle.agent.name],
    ["Access Grants", "access_grants", `${counts.access_grants} records`],
    [
      "Data Usage Profile summaries",
      "data_usage_profile_summaries",
      `${counts.data_usage_profiles} records`
    ],
    ["TraceEvents", "trace_events", `${counts.trace_events} records`],
    ["PolicyDecisions", "policy_decisions", `${counts.policy_decisions} records`],
    [
      "PolicyVersion references",
      "policy_version_references",
      `${counts.policy_versions} references`
    ],
    ["CheckResults", "check_results", `${counts.check_results} records`],
    ["HumanApprovals", "human_approvals", `${counts.human_approvals} records`],
    ["AuditLogs", "audit_logs", `${counts.audit_logs} records`]
  ];

  return (
    <AGCPPanel className="evidence-chain-panel">
      <AGCPSectionHeader
        eyebrow="human_readable_evidence_chain"
        title="What happened?"
        description="A bounded evidence chain assembled from the backend Evidence Bundle response."
      />
      <div className="evidence-chain-cards">
        {items.map(([label, key, value]) => (
          <article className="evidence-chain-card" key={label}>
            <span>{label}</span>
            <em>{key}</em>
            <strong>{value}</strong>
          </article>
        ))}
      </div>
    </AGCPPanel>
  );
}

function SubjectSection({
  agentId,
  bundle,
  exportedAt
}: {
  agentId: string;
  bundle: EvidenceBundle;
  exportedAt: string;
}) {
  const trace = bundle.trace_events[0];
  const run = bundle.agent_runs[0];
  const decision = bundle.policy_decisions[0];

  return (
    <EvidenceSection
      eyebrow="safe_export_metadata"
      title="Subject"
      count={1}
      description="Agent and request identifiers attached to this Evidence Bundle."
    >
      <AGCPMetaGrid
        items={[
          { label: "agent", value: bundle.agent.name },
          { label: "agent_id", value: bundle.agent.id || agentId },
          { label: "environment", value: bundle.agent.environment || run?.environment || "Not set" },
          { label: "generated_at", value: formatTimestamp(exportedAt) },
          { label: "run_id", value: run?.run_id || trace?.run_id || "Not included" },
          { label: "trace_id", value: trace?.id || decision?.trace_event_id || "Not included" },
          { label: "policy_decision_id", value: decision?.id || "Not included" }
        ]}
      />
    </EvidenceSection>
  );
}

function PolicyDecisionSection({
  policyDecisions
}: {
  policyDecisions: EvidencePolicyDecision[];
}) {
  return (
    <EvidenceSection
      eyebrow="evidence"
      title="Policy Decision"
      count={policyDecisions.length}
      description="Decision records explain which policy or fallback rule allowed, denied, or escalated the action."
    >
      {policyDecisions.length === 0 ? (
        <EvidenceEmpty>No PolicyDecision evidence attached.</EvidenceEmpty>
      ) : (
        <div className="evidence-card-grid">
          {policyDecisions.map((decision) => (
            <article className="evidence-record-card" key={decision.id}>
              <RecordCardHeader
                badge={formatValue(decision.decision)}
                title={decision.policy?.name || "Policy decision"}
                tone={decision.decision === "deny" ? "danger" : "purple"}
              />
              <p>{decision.reason || "No reason recorded."}</p>
              <AGCPMetaGrid
                items={[
                  { label: "decision_id", value: decision.id },
                  { label: "proceed", value: "Not exposed by current evidence response" },
                  { label: "policy_id", value: plainValue(decision.policy_id) },
                  { label: "policy_version_id", value: plainValue(decision.policy_version_id) },
                  { label: "rule", value: decision.rule?.name || plainValue(decision.rule_id) },
                  { label: "created_at", value: formatTimestamp(decision.created_at) }
                ]}
              />
            </article>
          ))}
        </div>
      )}
    </EvidenceSection>
  );
}

function CheckResultsSection({
  checkResults
}: {
  checkResults: EvidenceCheckResult[];
}) {
  return (
    <EvidenceSection
      eyebrow="evidence"
      title="Metadata CheckResults"
      count={checkResults.length}
      description="Metadata-only pre-check results are evidence inputs. They are not fake scanner output."
    >
      {checkResults.length === 0 ? (
        <EvidenceEmpty>No metadata pre-check results attached.</EvidenceEmpty>
      ) : (
        <div className="evidence-card-grid">
          {checkResults.map((result) => (
            <article className="evidence-record-card" key={result.check_result_id}>
              <RecordCardHeader
                badge={formatValue(result.outcome)}
                title={result.check_type || result.check_tool_name || "Metadata check"}
                tone={result.outcome === "pass" || result.outcome === "passed" ? "ok" : "warn"}
              />
              <AGCPMetaGrid
                items={[
                  { label: "check_type", value: plainValue(result.check_type) },
                  { label: "outcome", value: formatValue(result.outcome) },
                  { label: "target_type", value: formatValue(result.target_type) },
                  { label: "target_id", value: shortId(result.target_id) },
                  { label: "confidence", value: plainValue(result.confidence) },
                  { label: "policy_decision_id", value: shortId(result.policy_decision_id) },
                  { label: "created_at", value: formatTimestamp(result.created_at) }
                ]}
              />
              <SafeMetadataBlock metadata={result.metadata} />
            </article>
          ))}
        </div>
      )}
    </EvidenceSection>
  );
}

function HumanReviewSection({
  humanApprovals
}: {
  humanApprovals: EvidenceHumanApproval[];
}) {
  return (
    <EvidenceSection
      eyebrow="evidence"
      title="Human Review"
      count={humanApprovals.length}
      description="HumanApproval records show whether oversight was required and how it was resolved."
    >
      {humanApprovals.length === 0 ? (
        <EvidenceEmpty>No human review evidence attached.</EvidenceEmpty>
      ) : (
        <div className="evidence-card-grid">
          {humanApprovals.map((approval) => (
            <article className="evidence-record-card" key={approval.id}>
              <RecordCardHeader
                badge={formatValue(approval.status)}
                title="HumanApproval"
                tone={approval.status === "approved" ? "ok" : "warn"}
              />
              <AGCPMetaGrid
                items={[
                  { label: "approval_id", value: approval.id },
                  { label: "policy_decision_id", value: shortId(approval.policy_decision_id) },
                  { label: "requester", value: `${approval.requested_by_actor_type}:${approval.requested_by_actor_id}` },
                  {
                    label: "reviewer",
                    value: approval.reviewed_by_actor_type
                      ? `${approval.reviewed_by_actor_type}:${approval.reviewed_by_actor_id}`
                      : "Not set"
                  },
                  { label: "created_at", value: formatTimestamp(approval.created_at) },
                  { label: "reviewed_at", value: formatTimestamp(approval.reviewed_at) }
                ]}
              />
            </article>
          ))}
        </div>
      )}
    </EvidenceSection>
  );
}

function PolicyReviewEvidenceSection({
  policyVersions
}: {
  policyVersions: EvidencePolicyVersionReference[];
}) {
  return (
    <EvidenceSection
      eyebrow="policy_version_references"
      title="Policy Review"
      count={policyVersions.length}
      description="Policy version evidence is shown only when the Evidence Bundle read model includes it."
    >
      {policyVersions.length === 0 ? (
        <EvidenceEmpty>No PolicyVersionReviewRequest evidence included in this bundle.</EvidenceEmpty>
      ) : (
        <div className="evidence-card-grid">
          {policyVersions.map((version) => (
            <article className="evidence-record-card" key={version.policy_version_id}>
              <RecordCardHeader
                badge={`v${version.version_number}`}
                title="PolicyVersion reference"
                tone={version.status === "active" ? "ok" : "purple"}
              />
              <AGCPMetaGrid
                items={[
                  { label: "policy_version_id", value: version.policy_version_id },
                  { label: "policy_id", value: version.policy_id },
                  { label: "status", value: formatValue(version.status) },
                  { label: "activated_at", value: formatTimestamp(version.activated_at) },
                  { label: "change_summary", value: plainValue(version.change_summary) }
                ]}
              />
            </article>
          ))}
        </div>
      )}
    </EvidenceSection>
  );
}

function AuditTrailSection({ auditLogs }: { auditLogs: EvidenceAuditLog[] }) {
  return (
    <EvidenceSection
      eyebrow="evidence"
      title="Audit Trail"
      count={auditLogs.length}
      description="Audit events provide append-only context for governance actions and exports."
    >
      {auditLogs.length === 0 ? (
        <EvidenceEmpty>No audit events included in this bundle.</EvidenceEmpty>
      ) : (
        <div className="evidence-card-grid">
          {auditLogs.map((log) => (
            <article className="evidence-record-card" key={log.id}>
              <RecordCardHeader
                badge={formatValue(log.event_type)}
                title={log.summary || "Audit event"}
                tone="info"
              />
              <AGCPMetaGrid
                items={[
                  { label: "event_type", value: log.event_type },
                  { label: "actor", value: `${log.actor_type}:${log.actor_id}` },
                  { label: "entity", value: `${log.entity_type}:${log.entity_id}` },
                  { label: "timestamp", value: formatTimestamp(log.created_at) }
                ]}
              />
              <SafeMetadataBlock metadata={log.metadata} />
            </article>
          ))}
        </div>
      )}
    </EvidenceSection>
  );
}

function ExportBundleSection({
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
  const displayBundle = sanitizeForEvidenceDisplay(bundle);

  return (
    <EvidenceSection
      eyebrow="artifact"
      title="Export bundle"
      count={1}
      description="Download the bounded JSON artifact. The frontend also filters unsafe metadata keys defensively before display."
      actions={
        <button
          className="secondary-action"
          type="button"
          onClick={() => downloadEvidenceBundle(agentId, displayBundle, exportedAt)}
        >
          Download Evidence Bundle JSON
        </button>
      }
    >
      <AGCPMetaGrid
        items={[
          { label: "exported_at", value: formatTimestamp(exportedAt) },
          { label: "exported_by", value: "Not exposed by current backend response" },
          { label: "agent_id", value: agentId },
          { label: "policy_decisions", value: String(counts.policy_decisions) },
          { label: "check_results", value: String(counts.check_results) },
          { label: "audit_logs", value: String(counts.audit_logs) }
        ]}
      />
      <details className="evidence-json-details">
        <summary>canonical_json_export</summary>
        <pre className="evidence-json-block">
          {JSON.stringify(displayBundle, null, 2)}
        </pre>
      </details>
    </EvidenceSection>
  );
}

function EvidenceSection({
  actions,
  children,
  count,
  description,
  eyebrow,
  title
}: {
  actions?: ReactNode;
  children: ReactNode;
  count: number;
  description: string;
  eyebrow: string;
  title: string;
}) {
  return (
    <AGCPPanel className="evidence-explorer-section">
      <AGCPSectionHeader
        eyebrow={eyebrow}
        title={title}
        description={description}
        meta={<AGCPBadge tone={count > 0 ? "purple" : "muted"}>{count}</AGCPBadge>}
        actions={actions}
      />
      {children}
    </AGCPPanel>
  );
}

function RecordCardHeader({
  badge,
  title,
  tone
}: {
  badge: string;
  title: string;
  tone: "danger" | "info" | "ok" | "purple" | "warn";
}) {
  return (
    <header className="evidence-record-card-header">
      <strong>{title}</strong>
      <AGCPBadge tone={tone}>{badge}</AGCPBadge>
    </header>
  );
}

function SafeMetadataBlock({ metadata }: { metadata: EvidenceMetadata }) {
  return (
    <details className="evidence-metadata-details">
      <summary>safe metadata</summary>
      <pre className="metadata-block">{metadataText(metadata)}</pre>
    </details>
  );
}

function EvidenceEmpty({ children }: { children: ReactNode }) {
  return <div className="evidence-empty-copy">{children}</div>;
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

function downloadEvidenceBundle(
  agentId: string,
  bundle: unknown,
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
