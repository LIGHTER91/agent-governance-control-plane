"use client";

import { useEffect, useMemo, useState } from "react";
import {
  AGCPBadge,
  AGCPEmptyState,
  AGCPErrorState,
  AGCPMetaGrid,
  AGCPPanel,
  AGCPSectionHeader,
  AGCPTimelineItem
} from "../../agcp-studio/primitives";
import { ApiRequestError, getApiBaseUrl } from "../../lib/api";
import type {
  AgentActivityItem,
  AgentActivityMetadataValue,
  AgentGovernanceProfile,
  AgentGovernanceProfileAccessGrant,
  AgentGovernanceProfileHumanApproval,
  AgentRecord
} from "../../lib/agents";
import {
  fetchAgentActivity,
  fetchAgentGovernanceProfile
} from "../../lib/agents";
import { EvidenceBundle, fetchEvidenceBundle } from "../../lib/evidence";
import { fetchAgentHumanApprovals } from "../../lib/human-approvals";
import type { HumanApprovalRecord } from "../../lib/human-approvals";

type AgentDetailState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | {
      status: "ready";
      profile: AgentGovernanceProfile;
      humanApprovals: HumanApprovalRecord[];
    };

type EvidenceState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; bundle: EvidenceBundle };

type ActivityState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; items: AgentActivityItem[] };

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

function activityErrorMessage(error: unknown) {
  if (error instanceof ApiRequestError) {
    if (error.status === 403) {
      return "Agent activity requires reviewer, auditor, or platform_admin role.";
    }

    if (error.status === 404) {
      return "Agent not found.";
    }
  }

  return error instanceof Error
    ? error.message
    : "Unable to load Agent activity from the backend.";
}

function ownerDisplay(agent: AgentRecord) {
  return agent.owner_name || agent.owner_id;
}

function badgeTone(value: string | null | undefined) {
  if (value === "active" || value === "approved" || value === "allow" || value === "low") {
    return "ok";
  }

  if (value === "pending" || value === "require_human_review" || value === "medium") {
    return "warn";
  }

  if (
    value === "disabled" ||
    value === "archived" ||
    value === "deny" ||
    value === "rejected" ||
    value === "cancelled" ||
    value === "high" ||
    value === "critical"
  ) {
    return "danger";
  }

  return "info";
}

export function AgentDetail({ agentId }: { agentId: string }) {
  const [state, setState] = useState<AgentDetailState>({ status: "loading" });
  const [activityState, setActivityState] = useState<ActivityState>({
    status: "loading"
  });
  const [evidenceState, setEvidenceState] = useState<EvidenceState>({
    status: "idle"
  });

  useEffect(() => {
    const controller = new AbortController();

    setState({ status: "loading" });
    setActivityState({ status: "loading" });
    setEvidenceState({ status: "idle" });

    Promise.all([
      fetchAgentGovernanceProfile(agentId, controller.signal),
      fetchAgentHumanApprovals(agentId, controller.signal)
    ])
      .then(([profile, humanApprovals]) => {
        setState({ status: "ready", profile, humanApprovals });
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) {
          return;
        }

        setState({ status: "error", message: agentErrorMessage(error) });
      });

    fetchAgentActivity(agentId, controller.signal)
      .then((items) => {
        setActivityState({ status: "ready", items });
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) {
          return;
        }

        setActivityState({
          status: "error",
          message: activityErrorMessage(error)
        });
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
      <AGCPPanel aria-live="polite">
        <AGCPEmptyState title="Loading Agent detail">
          Requesting `GET /agents/{"{agent_id}"}/governance-profile` and
          related HumanApproval records from {getApiBaseUrl()}.
        </AGCPEmptyState>
      </AGCPPanel>
    );
  }

  if (state.status === "error") {
    return (
      <AGCPPanel>
        <AGCPErrorState title="Unable to load Agent detail">
          {state.message} Check that the backend is running and that
          NEXT_PUBLIC_AGCP_API_BASE_URL points to the API base URL.
        </AGCPErrorState>
      </AGCPPanel>
    );
  }

  return (
    <>
      <AgentHeader agent={state.profile.agent} />
      <AgentGovernanceProfileSection profile={state.profile} />
      <ActivityTimelineSection activityState={activityState} />
      <HumanApprovalsSection humanApprovals={state.humanApprovals} />
      <EvidenceAccessSection
        evidenceHint={state.profile.evidence_bundle}
        evidenceState={evidenceState}
        onLoadEvidence={handleLoadEvidence}
      />
      <RuntimePolicyPlaceholder />
    </>
  );
}

function ActivityTimelineSection({
  activityState
}: {
  activityState: ActivityState;
}) {
  const sortedItems = useMemo(() => {
    if (activityState.status !== "ready") {
      return [];
    }

    return [...activityState.items].sort((left, right) => {
      const rightTime = Date.parse(right.timestamp);
      const leftTime = Date.parse(left.timestamp);

      if (Number.isNaN(rightTime) || Number.isNaN(leftTime)) {
        return right.timestamp.localeCompare(left.timestamp);
      }

      return rightTime - leftTime;
    });
  }, [activityState]);

  return (
    <>
      <h3 className="section-title">Activity / Timeline</h3>
      <section className="detail-card" aria-label="Agent activity timeline">
        <div className="detail-card-header">
          <div>
            <strong>Governance activity</strong>
            <p>
              Reads `GET /agents/{"{agent_id}"}/activity` for a lightweight
              navigation view across trace events, PolicyDecision records,
              HumanApproval records, and AuditLog entries.
            </p>
          </div>
        </div>

        {activityState.status === "loading" ? (
          <div className="state-message compact" aria-live="polite">
            <strong>Loading Agent activity</strong>
            <p>Requesting the read-only activity timeline from the backend.</p>
          </div>
        ) : null}

        {activityState.status === "error" ? (
          <div className="state-message error compact" role="alert">
            <strong>Unable to load Agent activity</strong>
            <p>{activityState.message}</p>
          </div>
        ) : null}

        {activityState.status === "ready" && sortedItems.length === 0 ? (
          <div className="state-message compact">
            <strong>No activity records for this Agent</strong>
            <p>
              Trace events, policy decisions, HumanApprovals, and audit entries
              will appear here after backend governance workflows run.
            </p>
          </div>
        ) : null}

        {activityState.status === "ready" && sortedItems.length > 0 ? (
          <ol className="agcp-timeline">
            {sortedItems.map((item) => (
              <ActivityTimelineItem item={item} key={`${item.type}-${item.id}`} />
            ))}
          </ol>
        ) : null}
      </section>
    </>
  );
}

function ActivityTimelineItem({ item }: { item: AgentActivityItem }) {
  const severity = item.severity || "info";
  const relatedIds = activityRelatedIds(item);
  const metadataEntries = activityMetadataEntries(item);

  return (
    <AGCPTimelineItem
      badge={formatValue(item.type)}
      tone={badgeTone(severity)}
      title={item.title}
      timestamp={formatTimestamp(item.timestamp)}
    >
      <p>{item.summary || "No summary provided."}</p>
      {relatedIds.length > 0 || metadataEntries.length > 0 ? (
        <div className="activity-technical">
          {relatedIds.length > 0 ? (
            <details>
              <summary>Related IDs</summary>
              <dl className="activity-related" aria-label="Related activity IDs">
                {relatedIds.map(([label, value]) => (
                  <div key={label}>
                    <dt>{label}</dt>
                    <dd>{value}</dd>
                  </div>
                ))}
              </dl>
            </details>
          ) : null}

          {metadataEntries.length > 0 ? (
            <details>
              <summary>Filtered metadata</summary>
              <dl className="activity-related" aria-label="Filtered metadata">
                {metadataEntries.map(([label, value]) => (
                  <div key={label}>
                    <dt>{label}</dt>
                    <dd>{value}</dd>
                  </div>
                ))}
              </dl>
            </details>
          ) : null}
        </div>
      ) : null}
    </AGCPTimelineItem>
  );
}

function activityRelatedIds(item: AgentActivityItem): Array<[string, string]> {
  if (item.related_ids && Object.keys(item.related_ids).length > 0) {
    return Object.entries(item.related_ids);
  }

  return [
    ["trace_event_id", item.trace_event_id],
    ["policy_decision_id", item.policy_decision_id],
    ["human_approval_id", item.human_approval_id],
    ["audit_log_id", item.audit_log_id],
    ["run_id", item.run_id]
  ].filter(([, value]) => Boolean(value)) as Array<[string, string]>;
}

function activityMetadataEntries(item: AgentActivityItem): Array<[string, string]> {
  if (!item.metadata) {
    return [];
  }

  return Object.entries(item.metadata).map(([key, value]) => [
    key,
    formatMetadataValue(value)
  ]);
}

function formatMetadataValue(value: AgentActivityMetadataValue) {
  if (value === null) {
    return "null";
  }

  return String(value);
}

function AgentHeader({ agent }: { agent: AgentRecord }) {
  return (
    <section className="agcp-agent-hero">
      <div>
        <span className="agcp-eyebrow">Agent Registry</span>
        <h2>{agent.name}</h2>
        <div className="agcp-agent-hero-badges">
          <AGCPBadge tone={badgeTone(agent.status)}>
            {formatValue(agent.status)}
          </AGCPBadge>
          <AGCPBadge tone={badgeTone(agent.risk_level)}>
            {formatValue(agent.risk_level)} risk
          </AGCPBadge>
          <AGCPBadge tone={badgeTone(agent.environment)}>
            {formatValue(agent.environment)}
          </AGCPBadge>
          <AGCPBadge tone="info">{formatValue(agent.framework)}</AGCPBadge>
        </div>
        <p>
          Product governance overview for ownership, lifecycle state, risk
          classification, human oversight, activity, and evidence access.
        </p>
      </div>
      <aside className="agcp-owner-card">
        <span>Owner</span>
        <strong>{ownerDisplay(agent)}</strong>
        <p>{agent.owner_id}</p>
      </aside>
    </section>
  );
}

function AgentGovernanceProfileSection({
  profile
}: {
  profile: AgentGovernanceProfile;
}) {
  const agent = profile.agent;
  const pendingCount = profile.human_approvals.by_status.pending || 0;
  const accessCounts = accessGrantCounts(profile.access_grants);
  const summaryItems = [
    {
      label: "Owner",
      value: ownerDisplay(agent),
      detail: `${formatValue(profile.owner.owner_type)} owner reference.`
    },
    {
      label: "Lifecycle",
      value: formatValue(profile.status),
      detail: "Current Agent Registry status."
    },
    {
      label: "Environment",
      value: formatValue(profile.environment),
      detail: "Deployment environment used for governance context."
    },
    {
      label: "Risk",
      value: formatValue(profile.risk_level),
      detail: "Risk classification stored on the Agent record."
    },
    {
      label: "Access Grants",
      value: String(profile.access_grants.length),
      detail: accessGrantSummary(accessCounts)
    },
    {
      label: "Recent Activity",
      value: String(profile.recent_activity.items.length),
      detail: `Newest ${profile.recent_activity.limit} profile activity records.`
    },
    {
      label: "Pending Human Approvals",
      value: String(pendingCount),
      detail: `${profile.human_approvals.total_count} total linked review records.`
    },
    {
      label: "Evidence Bundle",
      value:
        profile.evidence_bundle.access === "allowed" ? "Available" : "Restricted",
      detail: "Profile hint only; export is loaded on request."
    }
  ];

  const overviewFields = [
    ["owner", ownerDisplay(agent)],
    ["owner_type", profile.owner.owner_type],
    ["owner_contact_email", profile.owner.owner_contact_email],
    ["description", agent.description],
    ["framework", agent.framework]
  ];

  const technicalFields = [
    ["agent_id", agent.id],
    ["description", agent.description],
    ["owner_id", profile.owner.owner_id],
    ["owner_name", profile.owner.owner_name],
    ["created_at", formatTimestamp(agent.created_at)],
    ["updated_at", formatTimestamp(agent.updated_at)]
  ];

  return (
    <>
      <h3 className="section-title">Agent Governance Profile</h3>
      <AGCPPanel>
        <AGCPSectionHeader
          eyebrow="governance profile"
          title="Agent overview"
          description="Connected profile from GET /agents/{agent_id}/governance-profile."
          meta={<AGCPBadge tone="purple">backend record</AGCPBadge>}
        />
        <AGCPMetaGrid
          items={overviewFields.map(([label, value]) => ({
            label: String(label),
            value: plainValue(value)
          }))}
        />
        <details className="profile-technical-details">
          <summary>Agent technical reference</summary>
          <dl className="activity-related">
            {technicalFields.map(([label, value]) => (
              <div key={label}>
                <dt>{label}</dt>
                <dd>{plainValue(value)}</dd>
              </div>
            ))}
          </dl>
        </details>
      </AGCPPanel>

      <section
        className="detail-summary-grid profile-summary-grid"
        aria-label="Governance summary"
      >
        {summaryItems.map((item) => (
          <article className="work-item" key={item.label}>
            <span className="status-label foundation">{item.label}</span>
            <strong>{item.value}</strong>
            <p>{item.detail}</p>
          </article>
        ))}
      </section>

      <ProfileHumanApprovalSummary profile={profile} />
      <ProfileRecentActivitySummary profile={profile} />
      <InventoryAccessSection accessGrants={profile.access_grants} />
      <PolicyTechnicalReferences profile={profile} />
    </>
  );
}

function ProfileHumanApprovalSummary({
  profile
}: {
  profile: AgentGovernanceProfile;
}) {
  const statusCounts = Object.entries(profile.human_approvals.by_status);

  return (
    <section className="detail-card profile-section">
      <div className="detail-card-header">
        <div>
          <strong>HumanApproval summary</strong>
          <p>
            Pending and recent review state from the governance profile. Review
            actions remain in the full Human approvals table below.
          </p>
        </div>
      </div>

      {statusCounts.length === 0 ? (
        <div className="state-message compact">
          <strong>No HumanApproval summary records</strong>
          <p>The profile did not return any HumanApproval records.</p>
        </div>
      ) : (
        <div
          className="detail-count-grid profile-approval-counts"
          aria-label="HumanApproval status counts"
        >
          {statusCounts.map(([status, count]) => (
            <div key={status}>
              <span>{formatValue(status)}</span>
              <strong>{count}</strong>
            </div>
          ))}
        </div>
      )}

      {profile.human_approvals.recent.length > 0 ? (
        <ul className="profile-compact-list">
          {profile.human_approvals.recent.map((approval) => (
            <li key={approval.id}>
              <div>
                <strong>{formatValue(approval.status)}</strong>
                <p>{approval.reason || "No reason was persisted."}</p>
              </div>
              <details>
                <summary>Technical reference</summary>
                <dl className="activity-related">
                  {humanApprovalTechnicalRows(approval).map(([label, value]) => (
                    <div key={label}>
                      <dt>{label}</dt>
                      <dd>{value}</dd>
                    </div>
                  ))}
                </dl>
              </details>
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}

function ProfileRecentActivitySummary({
  profile
}: {
  profile: AgentGovernanceProfile;
}) {
  return (
    <>
      <h3 className="section-title">Recent activity summary</h3>
      <section className="detail-card" aria-label="Recent profile activity">
        <div className="detail-card-header">
          <div>
            <strong>Profile activity</strong>
            <p>
              Compact newest-first activity from the profile endpoint. The full
              Activity / Timeline section remains below.
            </p>
          </div>
        </div>
        {profile.recent_activity.items.length === 0 ? (
          <div className="state-message compact">
            <strong>No recent governance activity in profile</strong>
            <p>
              Trace events, policy decisions, HumanApprovals, and audit entries
              will appear after governance workflows run.
            </p>
          </div>
        ) : (
          <ol className="agcp-timeline profile-activity-list">
            {profile.recent_activity.items.map((item) => (
              <ActivityTimelineItem item={item} key={`${item.type}-${item.id}`} />
            ))}
          </ol>
        )}
      </section>
    </>
  );
}

function InventoryAccessSection({
  accessGrants
}: {
  accessGrants: AgentGovernanceProfileAccessGrant[];
}) {
  const groups = [
    ["Capabilities", grantsByTargetType(accessGrants, "capability")],
    ["Sources", grantsByTargetType(accessGrants, "source")],
    ["Model assets", grantsByTargetType(accessGrants, "model_asset")],
    ["External grants", grantsByTargetType(accessGrants, "external")]
  ] as const;

  return (
    <>
      <h3 className="section-title">Inventory access</h3>
      <section className="profile-access-grid" aria-label="Inventory access grants">
        {groups.map(([title, grants]) => (
          <section className="detail-card" key={title}>
            <div className="detail-card-header">
              <div>
                <strong>{title}</strong>
                <p>{grants.length} grants declared for this Agent.</p>
              </div>
            </div>
            {grants.length === 0 ? (
              <div className="state-message compact">
                <strong>No {title.toLowerCase()}</strong>
                <p>The governance profile did not return this target type.</p>
              </div>
            ) : (
              <ul className="profile-grant-list">
                {grants.map((grant) => (
                  <li key={grant.id}>
                    <div className="activity-badges">
                      <span className="table-pill">
                        {formatValue(grant.status)}
                      </span>
                      <span className={`table-pill risk-${grant.risk_level}`}>
                        {formatValue(grant.risk_level)}
                      </span>
                    </div>
                    <strong>{grant.target?.name || grant.name}</strong>
                    <p>{grant.reason || grant.description || "No grant reason."}</p>
                    <dl className="runtime-activity-fields profile-grant-fields">
                      <RuntimeField
                        label="target"
                        value={grant.target?.name || grant.external_ref}
                      />
                      <RuntimeField
                        label="inventory_type"
                        value={grant.target?.inventory_type}
                      />
                      <RuntimeField label="provider" value={grant.target?.provider} />
                      <RuntimeField
                        label="expires_at"
                        value={formatTimestamp(grant.expires_at)}
                      />
                    </dl>
                    <details>
                      <summary>Technical references</summary>
                      <dl className="activity-related">
                        {accessGrantTechnicalRows(grant).map(([label, value]) => (
                          <div key={label}>
                            <dt>{label}</dt>
                            <dd>{value}</dd>
                          </div>
                        ))}
                      </dl>
                    </details>
                  </li>
                ))}
              </ul>
            )}
          </section>
        ))}
      </section>
    </>
  );
}

function PolicyTechnicalReferences({
  profile
}: {
  profile: AgentGovernanceProfile;
}) {
  const policyRows = [
    ["policy_decision_count", String(profile.policy_summary.policy_decision_count)],
    [
      "referenced_policy_ids",
      technicalList(profile.policy_summary.referenced_policy_ids)
    ],
    ["referenced_rule_ids", technicalList(profile.policy_summary.referenced_rule_ids)]
  ];

  return (
    <section className="detail-card profile-section">
      <div className="detail-card-header">
        <div>
          <strong>Policy and rule references</strong>
          <p>
            Technical references derived from persisted PolicyDecision records.
            Policy editing and simulation remain separate future workflows.
          </p>
        </div>
      </div>
      <details className="profile-technical-details">
        <summary>Policy/rule technical references</summary>
        <dl className="activity-related">
          {policyRows.map(([label, value]) => (
            <div key={label}>
              <dt>{label}</dt>
              <dd>{value}</dd>
            </div>
          ))}
        </dl>
      </details>
    </section>
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
      <AGCPPanel aria-label="Agent Human Approvals">
        <AGCPSectionHeader
          eyebrow="human oversight"
          title="Linked HumanApproval records"
          description="Read-only review context from the backend. Runtime continuation remains outside this page."
          meta={<AGCPBadge tone="purple">{humanApprovals.length} records</AGCPBadge>}
        />
        {humanApprovals.length === 0 ? (
          <AGCPEmptyState title="No HumanApproval records for this Agent">
            Pending, approved, rejected, cancelled, or expired review records
            will appear here after backend governance flows request human
            oversight.
          </AGCPEmptyState>
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
      </AGCPPanel>
    </>
  );
}

function EvidenceAccessSection({
  evidenceHint,
  evidenceState,
  onLoadEvidence
}: {
  evidenceHint: AgentGovernanceProfile["evidence_bundle"];
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

        <dl
          className="runtime-activity-fields evidence-hint-fields"
          aria-label="Evidence Bundle availability hint"
        >
          <RuntimeField
            label="availability"
            value={evidenceHint.available ? "available" : "not_available"}
          />
          <RuntimeField label="access" value={evidenceHint.access} />
          <RuntimeField label="export_format" value={evidenceHint.export_format} />
          <RuntimeField label="export_path" value={evidenceHint.export_path} />
        </dl>

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

function RuntimeField({
  label,
  value
}: {
  label: string;
  value: string | number | boolean | null | undefined;
}) {
  return (
    <div>
      <dt>{label}</dt>
      <dd className={label.endsWith("_id") ? "id-cell" : undefined}>
        {plainValue(value)}
      </dd>
    </div>
  );
}

function accessGrantCounts(
  accessGrants: AgentGovernanceProfileAccessGrant[]
): Record<"capability" | "source" | "model_asset" | "external" | "other", number> {
  return accessGrants.reduce(
    (counts, grant) => {
      if (
        grant.target_type === "capability" ||
        grant.target_type === "source" ||
        grant.target_type === "model_asset" ||
        grant.target_type === "external"
      ) {
        counts[grant.target_type] += 1;
      } else {
        counts.other += 1;
      }

      return counts;
    },
    { capability: 0, source: 0, model_asset: 0, external: 0, other: 0 }
  );
}

function accessGrantSummary(
  counts: Record<"capability" | "source" | "model_asset" | "external" | "other", number>
) {
  const parts = ([
    ["capability", counts.capability],
    ["source", counts.source],
    ["model asset", counts.model_asset],
    ["external", counts.external],
    ["other", counts.other]
  ] as Array<[string, number]>)
    .filter(([, count]) => count > 0)
    .map(([label, count]) => `${count} ${label}`);

  return parts.length > 0
    ? `${parts.join(", ")} grants in profile.`
    : "No access grants returned in profile.";
}

function grantsByTargetType(
  accessGrants: AgentGovernanceProfileAccessGrant[],
  targetType: string
) {
  return accessGrants.filter((grant) => grant.target_type === targetType);
}

function humanApprovalTechnicalRows(
  approval: AgentGovernanceProfileHumanApproval
): Array<[string, string]> {
  return [
    ["human_approval_id", approval.id],
    ["agent_id", approval.agent_id],
    ["policy_decision_id", approval.policy_decision_id],
    [
      "requested_by",
      `${approval.requested_by_actor_type}:${approval.requested_by_actor_id}`
    ],
    [
      "reviewed_by",
      approval.reviewed_by_actor_type && approval.reviewed_by_actor_id
        ? `${approval.reviewed_by_actor_type}:${approval.reviewed_by_actor_id}`
        : null
    ],
    ["created_at", formatTimestamp(approval.created_at)],
    ["reviewed_at", formatTimestamp(approval.reviewed_at)],
    ["expires_at", formatTimestamp(approval.expires_at)]
  ].filter(([, value]) => Boolean(value)) as Array<[string, string]>;
}

function accessGrantTechnicalRows(
  grant: AgentGovernanceProfileAccessGrant
): Array<[string, string]> {
  return [
    ["access_grant_id", grant.id],
    ["grant_type", grant.grant_type],
    ["subject_type", grant.subject_type],
    ["subject_id", grant.subject_id],
    ["target_type", grant.target_type],
    ["target_id", grant.target_id],
    ["external_ref", grant.external_ref],
    ["target_status", grant.target?.status],
    ["target_external_ref", grant.target?.external_ref],
    [
      "granted_by",
      `${grant.granted_by_actor_type}:${grant.granted_by_actor_id}`
    ],
    ["created_at", formatTimestamp(grant.created_at)],
    ["updated_at", formatTimestamp(grant.updated_at)]
  ].filter(([, value]) => Boolean(value)) as Array<[string, string]>;
}

function technicalList(values: string[]) {
  return values.length > 0 ? values.join(", ") : "None";
}

function RuntimePolicyPlaceholder() {
  return (
    <>
      <h3 className="section-title">Runtime / policy decisions</h3>
      <section className="placeholder-panel">
        <p>
          The Activity / Timeline section provides lightweight navigation across
          linked runtime and policy records. A dedicated runtime decision
          drill-down view remains future work.
        </p>
      </section>
    </>
  );
}
