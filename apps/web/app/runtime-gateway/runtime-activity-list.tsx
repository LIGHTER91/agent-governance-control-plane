"use client";

import { useEffect, useMemo, useState } from "react";
import { ApiRequestError, getApiBaseUrl } from "../lib/api";
import { fetchRuntimeToolCallActivity } from "../lib/runtime";
import type { RuntimeToolCallActivityItem } from "../lib/runtime";

type RuntimeActivityState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; items: RuntimeToolCallActivityItem[] };

const primaryIdFields = [
  "trace_event_id",
  "policy_decision_id",
  "human_approval_id"
] as const;

function formatValue(value: string | null | undefined) {
  if (!value) {
    return "Not persisted";
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

function formatFieldValue(value: string | null | undefined) {
  if (!value) {
    return "Not persisted";
  }

  return value;
}

function activityErrorMessage(error: unknown) {
  if (error instanceof ApiRequestError && error.status === 403) {
    return "Runtime activity requires reviewer, auditor, or platform_admin role.";
  }

  return error instanceof Error
    ? error.message
    : "Unable to load Runtime activity from the backend.";
}

export function RuntimeActivityList() {
  const [state, setState] = useState<RuntimeActivityState>({
    status: "loading"
  });

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

  return (
    <section className="detail-card" aria-label="Runtime activity">
      <div className="detail-card-header">
        <div>
          <strong>Runtime decisions activity</strong>
          <p>
            Reads `GET /runtime/tool-calls/activity` from {getApiBaseUrl()}.
            Items are shown newest-first from persisted governance records.
          </p>
        </div>
      </div>

      {state.status === "loading" ? (
        <div className="state-message compact" aria-live="polite">
          <strong>Loading Runtime activity</strong>
          <p>Requesting Runtime Gateway tool-call activity from the backend.</p>
        </div>
      ) : null}

      {state.status === "error" ? (
        <div className="state-message error compact" role="alert">
          <strong>Unable to load Runtime activity</strong>
          <p>{state.message}</p>
          <p>
            Check that the backend is running and that
            NEXT_PUBLIC_AGCP_API_BASE_URL points to the API base URL.
          </p>
        </div>
      ) : null}

      {state.status === "ready" && sortedItems.length === 0 ? (
        <div className="state-message compact">
          <strong>No Runtime activity records</strong>
          <p>
            Runtime Gateway decisions and resume checks will appear here after
            wrappers or adapters call the backend.
          </p>
        </div>
      ) : null}

      {state.status === "ready" && sortedItems.length > 0 ? (
        <ol className="activity-list runtime-activity-list">
          {sortedItems.map((item) => (
            <RuntimeActivityItem item={item} key={item.id} />
          ))}
        </ol>
      ) : null}
    </section>
  );
}

function RuntimeActivityItem({ item }: { item: RuntimeToolCallActivityItem }) {
  const relatedIds = runtimeRelatedIds(item);

  return (
    <li className="activity-item">
      <div className="activity-item-header">
        <div className="activity-badges">
          <span className="table-pill">{formatValue(item.type)}</span>
          <span className={`table-pill decision-${item.decision || "unknown"}`}>
            {formatValue(item.decision)}
          </span>
          <span className={`table-pill proceed-${String(item.proceed)}`}>
            proceed={formatProceed(item.proceed)}
          </span>
        </div>
        <time dateTime={item.timestamp}>{formatTimestamp(item.timestamp)}</time>
      </div>

      <strong>{formatValue(item.tool_name)}</strong>
      <p>{item.reason || "No reason was persisted for this activity record."}</p>

      <dl className="runtime-activity-fields" aria-label="Runtime activity fields">
        <RuntimeField label="tool_name" value={item.tool_name} />
        <RuntimeField label="mode" value={item.mode} />
        <RuntimeField label="decision" value={item.decision} />
        <RuntimeField label="proceed" value={formatProceed(item.proceed)} />
        <RuntimeField label="agent_id" value={item.agent_id} technical />
        <RuntimeField label="run_id" value={item.run_id} technical />
        <RuntimeField label="request_id" value={item.request_id} technical />
      </dl>

      {relatedIds.length > 0 ? (
        <div className="activity-technical">
          <details>
            <summary>Related IDs</summary>
            <dl className="activity-related" aria-label="Related runtime IDs">
              {relatedIds.map(([label, value]) => (
                <div key={label}>
                  <dt>{label}</dt>
                  <dd>{value}</dd>
                </div>
              ))}
            </dl>
          </details>
        </div>
      ) : null}
    </li>
  );
}

function RuntimeField({
  label,
  technical = false,
  value
}: {
  label: string;
  technical?: boolean;
  value: string | null | undefined;
}) {
  return (
    <div>
      <dt>{label}</dt>
      <dd className={technical ? "id-cell" : undefined}>
        {formatFieldValue(value)}
      </dd>
    </div>
  );
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
