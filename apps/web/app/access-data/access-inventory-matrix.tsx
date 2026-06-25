"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { ApiRequestError, getApiBaseUrl } from "../lib/api";
import {
  AccessGrantRecord,
  AccessGrantTransitionAction,
  SourceRecord,
  fetchAccessGrants,
  fetchSources,
  transitionAccessGrant
} from "../lib/sources";

type AccessState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; grants: AccessGrantRecord[]; sources: SourceRecord[] };

type GrantStatusFilter =
  | "all"
  | "active"
  | "pending_review"
  | "suspended"
  | "revoked"
  | "expired";

type MatrixColumn = {
  key: string;
  label: string;
  group: "Tool" | "Model" | "Data Source" | "External Target";
  targetType: string;
  targetId: string;
};

const statusFilters: GrantStatusFilter[] = [
  "all",
  "active",
  "pending_review",
  "suspended",
  "revoked",
  "expired"
];

const targetFilters = [
  "all",
  "capability",
  "model_asset",
  "source",
  "external",
  "other"
] as const;

const groupOrder: MatrixColumn["group"][] = [
  "Tool",
  "Model",
  "Data Source",
  "External Target"
];

function accessErrorMessage(error: unknown) {
  if (error instanceof ApiRequestError && error.status === 403) {
    return "Access inventory requires an authorized governance actor.";
  }

  return error instanceof Error
    ? error.message
    : "Unable to load Access Grants from the backend.";
}

function transitionErrorMessage(error: unknown) {
  if (error instanceof ApiRequestError) {
    if (error.status === 404) {
      return "Access Grant not found. Refresh the matrix and try again.";
    }

    if (error.status === 409) {
      return "The backend rejected this transition for the current Access Grant status.";
    }
  }

  return error instanceof Error
    ? error.message
    : "Unable to update Access Grant status.";
}

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

function targetGroup(targetType: string): MatrixColumn["group"] {
  if (targetType === "model_asset") {
    return "Model";
  }

  if (targetType === "source") {
    return "Data Source";
  }

  if (targetType === "external" || targetType === "other") {
    return "External Target";
  }

  return "Tool";
}

function grantTargetId(grant: AccessGrantRecord) {
  return grant.target_id || grant.external_ref || "unscoped";
}

function sourceNameById(sources: SourceRecord[]) {
  return new Map(sources.map((source) => [source.id, source.name]));
}

function targetLabel(grant: AccessGrantRecord, sources: SourceRecord[]) {
  const id = grantTargetId(grant);

  if (grant.target_type === "source") {
    return sourceNameById(sources).get(id) || id;
  }

  return grant.name || id;
}

function buildColumns(grants: AccessGrantRecord[], sources: SourceRecord[]) {
  const seen = new Map<string, MatrixColumn>();

  for (const grant of grants) {
    const targetId = grantTargetId(grant);
    const key = `${grant.target_type}:${targetId}`;

    if (!seen.has(key)) {
      seen.set(key, {
        key,
        label: targetLabel(grant, sources),
        group: targetGroup(grant.target_type),
        targetType: grant.target_type,
        targetId
      });
    }
  }

  return [...seen.values()].sort((left, right) => {
    const groupDelta =
      groupOrder.indexOf(left.group) - groupOrder.indexOf(right.group);

    if (groupDelta !== 0) {
      return groupDelta;
    }

    return left.label.localeCompare(right.label);
  });
}

function transitionActionsForStatus(
  status: string
): AccessGrantTransitionAction[] {
  if (status === "active") {
    return ["suspend", "revoke", "expire"];
  }

  if (status === "pending_review") {
    return ["revoke", "expire"];
  }

  if (status === "suspended") {
    return ["reactivate", "revoke", "expire"];
  }

  return [];
}

function cellTone(status: string) {
  if (status === "active") {
    return "allowed";
  }

  if (status === "pending_review") {
    return "review";
  }

  if (status === "suspended" || status === "revoked") {
    return "suspended";
  }

  if (status === "expired") {
    return "expired";
  }

  return "not-declared";
}

function cellGlyph(status: string) {
  if (status === "active") {
    return "ok";
  }

  if (status === "pending_review") {
    return "!";
  }

  if (status === "suspended" || status === "revoked") {
    return "x";
  }

  if (status === "expired") {
    return "h";
  }

  return "-";
}

function statusCounts(grants: AccessGrantRecord[]) {
  return statusFilters
    .filter((status) => status !== "all")
    .map((status) => ({
      status,
      count: grants.filter((grant) => grant.status === status).length
    }));
}

export function AccessInventoryMatrix() {
  const [state, setState] = useState<AccessState>({ status: "loading" });
  const [statusFilter, setStatusFilter] = useState<GrantStatusFilter>("all");
  const [targetFilter, setTargetFilter] =
    useState<(typeof targetFilters)[number]>("all");
  const [query, setQuery] = useState("");
  const [selectedGrantId, setSelectedGrantId] = useState<string | null>(null);
  const [actionState, setActionState] = useState<
    | { status: "idle" }
    | { status: "loading"; action: AccessGrantTransitionAction }
    | { status: "success"; message: string }
    | { status: "error"; message: string }
  >({ status: "idle" });

  const loadInventory = useCallback((signal?: AbortSignal) => {
    setState({ status: "loading" });

    Promise.all([fetchAccessGrants(signal), fetchSources(signal)])
      .then(([grants, sources]) => {
        setState({ status: "ready", grants, sources });
      })
      .catch((error: unknown) => {
        if (signal?.aborted) {
          return;
        }

        setState({ status: "error", message: accessErrorMessage(error) });
      });
  }, []);

  useEffect(() => {
    const controller = new AbortController();

    loadInventory(controller.signal);

    return () => controller.abort();
  }, [loadInventory]);

  const filteredGrants = useMemo(() => {
    if (state.status !== "ready") {
      return [];
    }

    const normalizedQuery = query.trim().toLowerCase();

    return state.grants.filter((grant) => {
      if (statusFilter !== "all" && grant.status !== statusFilter) {
        return false;
      }

      if (targetFilter !== "all" && grant.target_type !== targetFilter) {
        return false;
      }

      if (!normalizedQuery) {
        return true;
      }

      const searchableValues = [
        grant.id,
        grant.name,
        grant.subject_id,
        grant.target_id,
        grant.external_ref,
        grant.reason
      ]
        .filter((value): value is string => Boolean(value));

      return searchableValues.some((value) =>
        value.toLowerCase().includes(normalizedQuery)
      );
    });
  }, [query, state, statusFilter, targetFilter]);

  const sources = state.status === "ready" ? state.sources : [];
  const columns = useMemo(
    () => buildColumns(filteredGrants, sources).slice(0, 20),
    [filteredGrants, sources]
  );
  const subjects = useMemo(
    () =>
      [...new Set(filteredGrants.map((grant) => grant.subject_id))]
        .sort((left, right) => left.localeCompare(right))
        .slice(0, 42),
    [filteredGrants]
  );
  const grantLookup = useMemo(() => {
    const lookup = new Map<string, AccessGrantRecord>();

    for (const grant of filteredGrants) {
      lookup.set(`${grant.subject_id}:${grant.target_type}:${grantTargetId(grant)}`, grant);
    }

    return lookup;
  }, [filteredGrants]);
  const selectedGrant =
    filteredGrants.find((grant) => grant.id === selectedGrantId) ||
    filteredGrants[0] ||
    null;

  useEffect(() => {
    if (!selectedGrantId && filteredGrants.length > 0) {
      setSelectedGrantId(filteredGrants[0].id);
    }
  }, [filteredGrants, selectedGrantId]);

  async function handleTransition(action: AccessGrantTransitionAction) {
    if (!selectedGrant) {
      return;
    }

    setActionState({ status: "loading", action });

    try {
      const updatedGrant = await transitionAccessGrant(selectedGrant.id, action);
      setState((currentState) =>
        currentState.status === "ready"
          ? {
              status: "ready",
              sources: currentState.sources,
              grants: currentState.grants.map((grant) =>
                grant.id === updatedGrant.id ? updatedGrant : grant
              )
            }
          : currentState
      );
      setSelectedGrantId(updatedGrant.id);
      setActionState({
        status: "success",
        message: `Access Grant ${formatValue(action)} submitted.`
      });
    } catch (error: unknown) {
      setActionState({ status: "error", message: transitionErrorMessage(error) });
    }
  }

  return (
    <div className="access-inventory-route">
      <section className="access-inventory-header" aria-labelledby="access-inventory-title">
        <div>
          <h1 id="access-inventory-title">Access & Inventory Matrix</h1>
          <p>
            Understand what Agents are declared allowed to access. Access Grants are
            declarations, not credentials or IAM permissions.
          </p>
        </div>
        <div className="access-inventory-toolbar">
          <span>
            Source: <strong>{getApiBaseUrl()}</strong>
          </span>
          <button type="button" onClick={() => loadInventory()}>
            Refresh
          </button>
        </div>
      </section>

      <div className="access-inventory-shell">
        <aside className="access-filter-rail" aria-label="Access inventory filters">
          <div className="access-rail-title">
            <strong>Filters</strong>
            <button
              type="button"
              onClick={() => {
                setStatusFilter("all");
                setTargetFilter("all");
                setQuery("");
              }}
            >
              Clear
            </button>
          </div>

          <label>
            <span>Agent or target</span>
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search declarations..."
              spellCheck={false}
            />
          </label>

          <label>
            <span>Access Grant status</span>
            <select
              value={statusFilter}
              onChange={(event) =>
                setStatusFilter(event.target.value as GrantStatusFilter)
              }
            >
              {statusFilters.map((status) => (
                <option key={status} value={status}>
                  {formatValue(status)}
                </option>
              ))}
            </select>
          </label>

          <label>
            <span>Target type</span>
            <select
              value={targetFilter}
              onChange={(event) =>
                setTargetFilter(event.target.value as (typeof targetFilters)[number])
              }
            >
              {targetFilters.map((target) => (
                <option key={target} value={target}>
                  {formatValue(target)}
                </option>
              ))}
            </select>
          </label>

          {state.status === "ready" ? (
            <div className="access-status-list" aria-label="Access Grant status counts">
              {statusCounts(state.grants).map(({ status, count }) => (
                <button
                  className={statusFilter === status ? "active" : ""}
                  key={status}
                  type="button"
                  onClick={() => setStatusFilter(status)}
                >
                  <span className={`matrix-dot ${cellTone(status)}`} />
                  <span>{formatValue(status)}</span>
                  <strong>{count}</strong>
                </button>
              ))}
            </div>
          ) : null}

          <div className="access-boundary-note">
            <strong>Governance boundary</strong>
            <p>
              Matrix cells describe declared access. Runtime callers remain
              responsible for honoring PolicyDecision results.
            </p>
          </div>
        </aside>

        <main className="access-matrix-workspace" aria-label="Access matrix">
          {state.status === "loading" ? (
            <div className="access-state-panel">
              <strong>Loading Access Inventory</strong>
              <p>Requesting Access Grants and Sources from the backend.</p>
            </div>
          ) : null}

          {state.status === "error" ? (
            <div className="access-state-panel error" role="alert">
              <strong>Unable to load Access Inventory</strong>
              <p>{state.message}</p>
            </div>
          ) : null}

          {state.status === "ready" ? (
            filteredGrants.length === 0 ? (
              <div className="access-state-panel">
                <strong>No Access Grants match the current filters</strong>
                <p>Adjust filters to inspect declared Agent access.</p>
              </div>
            ) : (
              <>
                <div className="access-matrix-meta">
                  <span>{filteredGrants.length} grants</span>
                  <span>{subjects.length} agents</span>
                  <span>{columns.length} targets</span>
                </div>
                <div className="access-matrix-scroll">
                  <table className="access-matrix-table">
                    <thead>
                      <tr>
                        <th className="agent-col">Agent</th>
                        {columns.map((column) => (
                          <th key={column.key}>
                            <span>{column.group}</span>
                            {column.label}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {subjects.map((subjectId) => (
                        <tr key={subjectId}>
                          <th scope="row" className="agent-col">
                            <span className="agent-avatar">
                              {subjectId.slice(0, 2).toUpperCase()}
                            </span>
                            <span>
                              <strong>{subjectId}</strong>
                              <em>Agent</em>
                            </span>
                          </th>
                          {columns.map((column) => {
                            const grant = grantLookup.get(
                              `${subjectId}:${column.targetType}:${column.targetId}`
                            );
                            const status = grant?.status || "not_declared";
                            const tone = cellTone(status);

                            return (
                              <td key={`${subjectId}-${column.key}`}>
                                <button
                                  className={`matrix-cell ${tone}`}
                                  type="button"
                                  disabled={!grant}
                                  onClick={() => {
                                    if (grant) {
                                      setSelectedGrantId(grant.id);
                                    }
                                  }}
                                  aria-label={`${subjectId} ${column.label}: ${formatValue(status)}`}
                                  title={formatValue(status)}
                                >
                                  {cellGlyph(status)}
                                </button>
                              </td>
                            );
                          })}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <div className="matrix-legend" aria-label="Matrix legend">
                  <span><i className="matrix-dot allowed" />Allowed</span>
                  <span><i className="matrix-dot review" />Review required</span>
                  <span><i className="matrix-dot suspended" />Suspended / revoked</span>
                  <span><i className="matrix-dot expired" />Expired</span>
                  <span><i className="matrix-dot not-declared" />Not declared</span>
                </div>
              </>
            )
          ) : null}
        </main>

        <aside className="access-inspector" aria-label="Selected Access Grant">
          <div className="access-inspector-accent" />
          {selectedGrant ? (
            <>
              <header>
                <span className="inspector-avatar">
                  {selectedGrant.subject_id.slice(0, 2).toUpperCase()}
                </span>
                <div>
                  <strong>{selectedGrant.name || selectedGrant.subject_id}</strong>
                  <p>{formatValue(selectedGrant.target_type)}</p>
                </div>
              </header>

              <dl className="access-detail-list">
                <div>
                  <dt>Permission</dt>
                  <dd>
                    <span className={`table-pill grant-${selectedGrant.status}`}>
                      {formatValue(selectedGrant.status)}
                    </span>
                  </dd>
                </div>
                <div>
                  <dt>Subject</dt>
                  <dd>{selectedGrant.subject_id}</dd>
                </div>
                <div>
                  <dt>Target</dt>
                  <dd>{grantTargetId(selectedGrant)}</dd>
                </div>
                <div>
                  <dt>Risk Level</dt>
                  <dd>{formatValue(selectedGrant.risk_level)}</dd>
                </div>
                <div>
                  <dt>Granted by</dt>
                  <dd>
                    {selectedGrant.granted_by_actor_type}:{selectedGrant.granted_by_actor_id}
                  </dd>
                </div>
                <div>
                  <dt>Expires</dt>
                  <dd>{formatTimestamp(selectedGrant.expires_at)}</dd>
                </div>
              </dl>

              <section className="access-inspector-section">
                <strong>Evidence references</strong>
                <Link href={`/agents/${selectedGrant.subject_id}`}>
                  Agent Governance Profile
                </Link>
                <Link href="/evidence">Evidence Bundle lookup</Link>
              </section>

              <section className="access-inspector-section">
                <strong>Lifecycle actions</strong>
                <div className="access-action-grid">
                  {transitionActionsForStatus(selectedGrant.status).length === 0 ? (
                    <p>Terminal governance status. No transition action is available.</p>
                  ) : (
                    transitionActionsForStatus(selectedGrant.status).map((action) => (
                      <button
                        className={`access-action ${action}`}
                        disabled={actionState.status === "loading"}
                        key={action}
                        type="button"
                        onClick={() => void handleTransition(action)}
                      >
                        {actionState.status === "loading" &&
                        actionState.action === action
                          ? `${formatValue(action)}...`
                          : formatValue(action)}
                      </button>
                    ))
                  )}
                </div>
                {actionState.status === "success" ? (
                  <p className="access-action-message success">{actionState.message}</p>
                ) : null}
                {actionState.status === "error" ? (
                  <p className="access-action-message error">{actionState.message}</p>
                ) : null}
              </section>

              <div className="access-boundary-note">
                <strong>Access Grants are declarations</strong>
                <p>They are not credentials and do not configure IAM.</p>
              </div>
            </>
          ) : (
            <div className="access-state-panel">
              <strong>No Access Grant selected</strong>
              <p>Select a matrix cell to inspect a declaration.</p>
            </div>
          )}
        </aside>
      </div>
    </div>
  );
}
