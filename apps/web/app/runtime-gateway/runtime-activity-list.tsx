"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import {
  AGCPBadge,
  AGCPEmptyState,
  AGCPErrorState,
  AGCPMetaGrid,
  AGCPPanel,
  AGCPTimelineItem
} from "../agcp-studio/primitives";
import { ApiRequestError, getApiBaseUrl } from "../lib/api";
import { fetchRuntimeToolCallActivity } from "../lib/runtime";
import type {
  RuntimeCheckResultSummary,
  RuntimeToolCallActivityItem
} from "../lib/runtime";

type RuntimeActivityState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; items: RuntimeToolCallActivityItem[] };

const primaryIdFields = [
  "trace_event_id",
  "policy_decision_id",
  "human_approval_id",
  "policy_version_id",
  "policy_id",
  "policy_rule_id"
] as const;

type BadgeTone = "default" | "ok" | "warn" | "danger" | "info" | "purple" | "muted";

const unsafeMetadataTerms = [
  "api_key",
  "authorization",
  "chunk",
  "content",
  "credential",
  "password",
  "payload",
  "prompt",
  "raw",
  "secret",
  "source_content",
  "token"
];

function formatValue(value: string | null | undefined) {
  if (!value) {
    return "Not attached";
  }

  return value
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function formatTimestamp(value: string | null | undefined) {
  if (!value) {
    return "Not persisted";
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleString();
}

function formatProceed(value: boolean | null) {
  if (value === null) {
    return "Not persisted";
  }

  return value ? "true" : "false";
}

function activityErrorMessage(error: unknown) {
  if (error instanceof ApiRequestError && error.status === 403) {
    return "Runtime activity requires reviewer, auditor, or platform_admin role.";
  }

  return error instanceof Error
    ? error.message
    : "Unable to load Runtime activity from the backend.";
}

function badgeToneForDecision(decision: RuntimeToolCallActivityItem["decision"]): BadgeTone {
  if (decision === "allow") {
    return "ok";
  }

  if (decision === "deny") {
    return "danger";
  }

  if (decision === "require_human_review") {
    return "warn";
  }

  return "muted";
}

function relatedValue(item: RuntimeToolCallActivityItem, keys: string[]) {
  const record = item as unknown as Record<string, unknown>;

  for (const key of keys) {
    const directValue = record[key];

    if (typeof directValue === "string" && directValue.length > 0) {
      return directValue;
    }

    const relatedValue = item.related_ids?.[key];

    if (relatedValue) {
      return relatedValue;
    }
  }

  return null;
}

function sourceIds(item: RuntimeToolCallActivityItem) {
  if (Array.isArray(item.source_ids) && item.source_ids.length > 0) {
    return item.source_ids.join(", ");
  }

  return relatedValue(item, ["source_ids", "source_id"]);
}

function contextRows(item: RuntimeToolCallActivityItem) {
  return [
    ["Environment", relatedValue(item, ["environment"])],
    ["Action type", relatedValue(item, ["action_type"])],
    ["Capability", relatedValue(item, ["capability_id"])],
    ["Source", sourceIds(item)],
    ["Model", relatedValue(item, ["model_id"])],
    ["Purpose", relatedValue(item, ["purpose"])],
    [
      "Classification",
      relatedValue(item, ["source_data_classification", "data_classification"])
    ]
  ].filter(([, value]) => Boolean(value)) as Array<[string, string]>;
}

function runtimeRelatedIds(
  item: RuntimeToolCallActivityItem
): Array<[string, string]> {
  const explicitIds = primaryIdFields
    .map((field) => [field, item[field]] as const)
    .filter(([, value]) => Boolean(value)) as Array<[string, string]>;

  const relatedIds = Object.entries(item.related_ids || {});
  const seen = new Set(explicitIds.map(([field]) => field));

  for (const [field, value] of relatedIds) {
    if (!seen.has(field)) {
      explicitIds.push([field, value]);
      seen.add(field);
    }
  }

  return explicitIds;
}

function safeMetadataEntries(metadata: RuntimeCheckResultSummary["metadata"]) {
  return Object.entries(metadata || {}).filter(([key, value]) => {
    if (value === null || value === undefined) {
      return false;
    }

    const normalizedKey = key.toLowerCase();

    return !unsafeMetadataTerms.some((term) => normalizedKey.includes(term));
  });
}

function safeMetadataValue(value: unknown) {
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }

  return "structured metadata";
}

function evidenceLink(agentId: string) {
  return `/evidence?agent_id=${encodeURIComponent(agentId)}`;
}

export function RuntimeActivityList() {
  const [state, setState] = useState<RuntimeActivityState>({
    status: "loading"
  });
  const [selectedId, setSelectedId] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();

    fetchRuntimeToolCallActivity(controller.signal)
      .then((items) => {
        setState({ status: "ready", items });
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) {
          return;
        }

        setState({ status: "error", message: activityErrorMessage(error) });
      });

    return () => {
      controller.abort();
    };
  }, []);

  const sortedItems = useMemo(() => {
    if (state.status !== "ready") {
      return [];
    }

    return [...state.items].sort((left, right) => {
      const rightTime = Date.parse(right.timestamp);
      const leftTime = Date.parse(left.timestamp);

      if (Number.isNaN(rightTime) || Number.isNaN(leftTime)) {
        return right.timestamp.localeCompare(left.timestamp);
      }

      return rightTime - leftTime;
    });
  }, [state]);

  const selectedItem =
    sortedItems.find((item) => item.id === selectedId) || sortedItems[0] || null;

  useEffect(() => {
    if (sortedItems.length === 0) {
      return;
    }

    if (!selectedId || !sortedItems.some((item) => item.id === selectedId)) {
      setSelectedId(sortedItems[0].id);
    }
  }, [selectedId, sortedItems]);

  if (state.status === "loading") {
    return (
      <AGCPPanel className="runtime-decisions-state">
        <strong>Loading Runtime activity</strong>
        <p>Requesting Runtime Gateway tool-call activity from {getApiBaseUrl()}.</p>
      </AGCPPanel>
    );
  }

  if (state.status === "error") {
    return (
      <AGCPErrorState title="Unable to load Runtime activity">
        {state.message} Check that the backend is running and that
        NEXT_PUBLIC_AGCP_API_BASE_URL points to the API base URL.
      </AGCPErrorState>
    );
  }

  if (sortedItems.length === 0) {
    return (
      <AGCPEmptyState title="No Runtime activity records">
        No runtime decisions recorded yet. Run .\scripts\dev-demo.ps1 to create a
        local metadata pre-check decision. API docs are available at
        http://localhost:8000/docs.
      </AGCPEmptyState>
    );
  }

  return (
    <section className="runtime-decisions-workspace" aria-label="Runtime decisions">
      <AGCPPanel className="runtime-decisions-list-panel">
        <header className="agcp-section-header">
          <div>
            <span className="agcp-eyebrow">Runtime activity</span>
            <h3>Decision timeline</h3>
          </div>
        </header>
        <p className="runtime-panel-copy">
          Reads <code>GET /runtime/tool-calls/activity</code> from {getApiBaseUrl()}.
          Items are real persisted governance records, newest first.
        </p>
        <div className="runtime-decision-list" role="list">
          {sortedItems.map((item) => (
            <button
              aria-current={selectedItem?.id === item.id ? "true" : undefined}
              className="runtime-decision-row"
              key={item.id}
              onClick={() => setSelectedId(item.id)}
              type="button"
            >
              <span className="runtime-decision-row-header">
                <AGCPBadge tone={badgeToneForDecision(item.decision)}>
                  {formatValue(item.decision)}
                </AGCPBadge>
                <span>{formatTimestamp(item.timestamp)}</span>
              </span>
              <strong>{item.tool_name || "Tool call"}</strong>
              <span>
                Agent {shortId(item.agent_id)} - proceed={formatProceed(item.proceed)}
              </span>
            </button>
          ))}
        </div>
      </AGCPPanel>

      {selectedItem ? <RuntimeDecisionDetail item={selectedItem} /> : null}
    </section>
  );
}

function RuntimeDecisionDetail({ item }: { item: RuntimeToolCallActivityItem }) {
  const policyVersionId = relatedValue(item, ["policy_version_id"]);
  const policyId = relatedValue(item, ["policy_id"]);
  const policyRuleId = relatedValue(item, ["policy_rule_id"]);
  const relatedIds = runtimeRelatedIds(item);
  const context = contextRows(item);
  const checkResults = item.check_results || [];

  return (
    <AGCPPanel className="runtime-decisions-detail-panel">
      <header className="agcp-section-header">
        <div>
          <span className="agcp-eyebrow">Selected decision</span>
          <h3>{item.tool_name || "Runtime tool call"}</h3>
        </div>
      </header>
      <div className="runtime-detail-header">
        <div>
          <div className="runtime-detail-badges">
            <AGCPBadge tone={badgeToneForDecision(item.decision)}>
              {formatValue(item.decision)}
            </AGCPBadge>
            <AGCPBadge tone={item.proceed ? "ok" : "warn"}>
              proceed={formatProceed(item.proceed)}
            </AGCPBadge>
            <AGCPBadge>{formatValue(item.mode)}</AGCPBadge>
          </div>
          <p>{item.reason || "No reason was persisted for this activity record."}</p>
        </div>
        <Link className="runtime-evidence-link" href={evidenceLink(item.agent_id)}>
          Open Evidence
        </Link>
      </div>

      <ol className="agcp-timeline runtime-decision-timeline">
        <AGCPTimelineItem badge="1" title="Runtime request received">
          <p>
            AGCP received a governed runtime decision request. AGCP does not execute the
            tool; the caller owns the final execution boundary.
          </p>
          <AGCPMetaGrid
            items={[
              { label: "Agent", value: item.agent_id },
              { label: "Run", value: item.run_id },
              { label: "Request", value: item.request_id || "Not attached" },
              { label: "Trace event", value: item.trace_event_id }
            ]}
          />
        </AGCPTimelineItem>

        <AGCPTimelineItem badge="2" title="Context resolved">
          {context.length > 0 ? (
            <AGCPMetaGrid
              items={context.map(([label, value]) => ({
                label,
                value
              }))}
            />
          ) : (
            <p>No resolved inventory context attached.</p>
          )}
        </AGCPTimelineItem>

        <AGCPTimelineItem badge="3" title="Policy evaluated">
          <p>
            AGCP evaluated the request against an active PolicyVersion when available, with
            fallback to the unversioned policy/rule path for policies that have not moved to
            active-version evaluation.
          </p>
          <AGCPMetaGrid
            items={[
              {
                label: "PolicyVersion",
                value: policyVersionId
                  ? `${policyVersionId}${item.policy_version_number ? ` v${item.policy_version_number}` : ""}`
                  : "No active PolicyVersion reference attached"
              },
              { label: "Fallback policy", value: policyId || "Not attached" },
              { label: "Policy rule", value: policyRuleId || "Not attached" },
              { label: "Decision", value: formatValue(item.decision) },
              { label: "Runtime mode", value: formatValue(item.mode) }
            ]}
          />
        </AGCPTimelineItem>

        <AGCPTimelineItem badge="4" title="Metadata checks">
          {checkResults.length > 0 ? (
            <div className="runtime-check-list">
              {checkResults.map((result, index) => (
                <RuntimeCheckResultCard
                  key={result.id || `${result.check_type}-${index}`}
                  result={result}
                />
              ))}
            </div>
          ) : (
            <p>
              No metadata pre-check results attached. CheckResult detail is available in the
              Evidence Bundle when linked through the existing safe evidence read model.
            </p>
          )}
        </AGCPTimelineItem>

        <AGCPTimelineItem badge="5" title="Human review">
          {item.human_approval_id ? (
            <>
              <p>
                A HumanApproval is linked to this decision. Review status and reviewer action
                live in the Review Inbox.
              </p>
              <AGCPMetaGrid
                items={[
                  {
                    label: "HumanApproval",
                    value: item.human_approval_id
                  },
                  {
                    label: "Status",
                    value: item.human_approval_status || "Available in Review Inbox"
                  },
                  {
                    label: "Requested at",
                    value: formatTimestamp(item.human_approval_requested_at)
                  }
                ]}
              />
              <Link className="runtime-inline-link" href="/human-approvals">
                Open Review Inbox
              </Link>
            </>
          ) : (
            <p>No human review was required for this decision.</p>
          )}
        </AGCPTimelineItem>

        <AGCPTimelineItem badge="6" title="Evidence">
          <p>
            Evidence contains PolicyDecision, CheckResults, reviews, and audit trail when
            available. The bundle remains a bounded JSON audit/review artifact, not a legal
            certification.
          </p>
          <Link className="runtime-inline-link" href={evidenceLink(item.agent_id)}>
            Open Evidence Bundle
          </Link>
        </AGCPTimelineItem>
      </ol>

      {relatedIds.length > 0 ? (
        <details className="runtime-related-details">
          <summary>Technical references</summary>
          <AGCPMetaGrid
            items={relatedIds.map(([label, value]) => ({
              label,
              value
            }))}
          />
        </details>
      ) : null}
    </AGCPPanel>
  );
}

function RuntimeCheckResultCard({ result }: { result: RuntimeCheckResultSummary }) {
  const metadataEntries = safeMetadataEntries(result.metadata);

  return (
    <article className="runtime-check-card">
      <div className="runtime-check-card-header">
        <strong>{formatValue(result.check_type)}</strong>
        <AGCPBadge tone={result.outcome === "passed" ? "ok" : "warn"}>
          {formatValue(result.outcome)}
        </AGCPBadge>
      </div>
      <AGCPMetaGrid
        items={[
          { label: "Target type", value: result.target_type || "Not attached" },
          { label: "Target id", value: result.target_id || "Not attached" },
          {
            label: "Confidence",
            value:
              typeof result.confidence === "number"
                ? result.confidence.toFixed(2)
                : "Not attached"
          },
          { label: "Created", value: formatTimestamp(result.created_at) }
        ]}
      />
      {metadataEntries.length > 0 ? (
        <dl className="runtime-check-metadata" aria-label="Safe check metadata">
          {metadataEntries.map(([key, value]) => (
            <div key={key}>
              <dt>{key}</dt>
              <dd>{safeMetadataValue(value)}</dd>
            </div>
          ))}
        </dl>
      ) : null}
    </article>
  );
}

function shortId(value: string | null | undefined) {
  if (!value) {
    return "not attached";
  }

  return value.length > 12 ? `${value.slice(0, 8)}...` : value;
}
