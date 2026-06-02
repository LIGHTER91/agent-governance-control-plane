"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { ApiRequestError, getApiBaseUrl } from "../lib/api";
import {
  AccessGrantRecord,
  AccessGrantTransitionAction,
  SourceMetadata,
  fetchAccessGrants,
  transitionAccessGrant
} from "../lib/sources";

type AccessGrantsState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; grants: AccessGrantRecord[] };

type AccessGrantsRefreshState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "success"; message: string }
  | { status: "error"; message: string };

type AccessGrantActionState =
  | { status: "idle" }
  | { status: "loading"; action: AccessGrantTransitionAction }
  | { status: "success"; message: string }
  | { status: "error"; message: string };

type GrantStatusFilter =
  | "all"
  | "pending_review"
  | "active"
  | "suspended"
  | "revoked"
  | "expired";

type GrantTargetFilter =
  | "all"
  | "capability"
  | "source"
  | "model_asset"
  | "external"
  | "other";

const statusFilters: GrantStatusFilter[] = [
  "all",
  "pending_review",
  "active",
  "suspended",
  "revoked",
  "expired"
];

const targetFilters: GrantTargetFilter[] = [
  "all",
  "capability",
  "source",
  "model_asset",
  "external",
  "other"
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

function metadataText(metadata: SourceMetadata) {
  const entries = Object.entries(metadata);

  if (entries.length === 0) {
    return "No safe metadata";
  }

  return JSON.stringify(metadata, null, 2);
}

function accessGrantErrorMessage(error: unknown) {
  return error instanceof Error
    ? error.message
    : "Unable to load Access Grants from the backend.";
}

function accessGrantTransitionErrorMessage(error: unknown) {
  if (error instanceof ApiRequestError) {
    if (error.status === 404) {
      return "Access Grant not found. Refresh the list and try again.";
    }

    if (error.status === 409) {
      return "The backend rejected this transition for the current Access Grant status.";
    }

    if (error.status === 422) {
      return "Transition note must be non-empty when provided.";
    }
  }

  return error instanceof Error
    ? error.message
    : "Unable to update Access Grant status.";
}

function transitionActionsForStatus(
  statusValue: string
): AccessGrantTransitionAction[] {
  if (statusValue === "active") {
    return ["suspend", "revoke", "expire"];
  }

  if (statusValue === "pending_review") {
    return ["revoke", "expire"];
  }

  if (statusValue === "suspended") {
    return ["reactivate", "revoke", "expire"];
  }

  return [];
}

function transitionPastTense(action: AccessGrantTransitionAction) {
  if (action === "suspend") {
    return "suspended";
  }

  if (action === "revoke") {
    return "revoked";
  }

  if (action === "reactivate") {
    return "reactivated";
  }

  return "expired";
}

export function AccessGrantsWorkflow() {
  const [state, setState] = useState<AccessGrantsState>({ status: "loading" });
  const [refreshState, setRefreshState] = useState<AccessGrantsRefreshState>({
    status: "idle"
  });
  const [statusFilter, setStatusFilter] = useState<GrantStatusFilter>("all");
  const [targetFilter, setTargetFilter] = useState<GrantTargetFilter>("all");
  const [subjectFilter, setSubjectFilter] = useState("");

  const loadAccessGrants = useCallback((signal?: AbortSignal) => {
    setState({ status: "loading" });
    setRefreshState({ status: "idle" });

    fetchAccessGrants(signal)
      .then((grants) => {
        setState({ status: "ready", grants });
      })
      .catch((error: unknown) => {
        if (signal?.aborted) {
          return;
        }

        setState({
          status: "error",
          message: accessGrantErrorMessage(error)
        });
      });
  }, []);

  useEffect(() => {
    const controller = new AbortController();

    loadAccessGrants(controller.signal);

    return () => {
      controller.abort();
    };
  }, [loadAccessGrants]);

  const refreshAccessGrants = useCallback(
    async (
      updatedGrant: AccessGrantRecord,
      action: AccessGrantTransitionAction
    ) => {
      setState((currentState) =>
        currentState.status === "ready"
          ? {
              status: "ready",
              grants: currentState.grants.map((grant) =>
                grant.id === updatedGrant.id ? updatedGrant : grant
              )
            }
          : currentState
      );
      setRefreshState({ status: "loading" });

      try {
        const grants = await fetchAccessGrants();
        setState({ status: "ready", grants });
        setRefreshState({
          status: "success",
          message: `Access Grants refreshed after ${transitionPastTense(
            action
          )} status update.`
        });
      } catch (error: unknown) {
        setRefreshState({
          status: "error",
          message: accessGrantErrorMessage(error)
        });
      }
    },
    []
  );

  const filteredGrants = useMemo(() => {
    if (state.status !== "ready") {
      return [];
    }

    const normalizedSubject = subjectFilter.trim().toLowerCase();

    return state.grants.filter((grant) => {
      if (statusFilter !== "all" && grant.status !== statusFilter) {
        return false;
      }

      if (targetFilter !== "all" && grant.target_type !== targetFilter) {
        return false;
      }

      if (
        normalizedSubject &&
        !grant.subject_id.toLowerCase().includes(normalizedSubject)
      ) {
        return false;
      }

      return true;
    });
  }, [state, statusFilter, subjectFilter, targetFilter]);

  return (
    <section className="access-grant-workflow">
      <AccessGrantBoundary />
      <h3 className="section-title">Access Grant workflow</h3>
      <section className="evidence-section">
        <header className="evidence-section-header">
          <div>
            <h3>Access Grants</h3>
            <p>GET /access-grants from {getApiBaseUrl()}</p>
          </div>
          <span>{state.status === "ready" ? state.grants.length : 0}</span>
        </header>

        {state.status === "loading" ? (
          <div className="state-message compact" aria-live="polite">
            <strong>Loading Access Grants</strong>
            <p>Requesting declared governance grants from the backend.</p>
          </div>
        ) : null}

        {state.status === "error" ? (
          <div className="state-message error compact" role="alert">
            <strong>Unable to load Access Grants</strong>
            <p>{state.message}</p>
          </div>
        ) : null}

        {state.status === "ready" ? (
          <>
            <div className="state-message compact success-state">
              <strong>Access Grants loaded</strong>
              <p>
                {
                  "Transition actions update the governance record status. This does not by itself guarantee runtime blocking; runtime enforcement depends on policies and runtime decisions."
                }
              </p>
            </div>
            <AccessGrantRefreshMessage refreshState={refreshState} />
            <AccessGrantFilters
              statusFilter={statusFilter}
              subjectFilter={subjectFilter}
              targetFilter={targetFilter}
              onStatusFilterChange={setStatusFilter}
              onSubjectFilterChange={setSubjectFilter}
              onTargetFilterChange={setTargetFilter}
            />
            <AccessGrantStatusSummary grants={state.grants} />
            <AccessGrantTable
              grants={filteredGrants}
              onTransitionComplete={refreshAccessGrants}
            />
          </>
        ) : null}
      </section>
    </section>
  );
}

function AccessGrantRefreshMessage({
  refreshState
}: {
  refreshState: AccessGrantsRefreshState;
}) {
  if (refreshState.status === "idle") {
    return null;
  }

  if (refreshState.status === "loading") {
    return (
      <p className="review-action-message" aria-live="polite">
        Refreshing Access Grants after status update.
      </p>
    );
  }

  return (
    <p
      className={`review-action-message ${refreshState.status}`}
      role={refreshState.status === "error" ? "alert" : undefined}
    >
      {refreshState.message}
    </p>
  );
}

function AccessGrantBoundary() {
  return (
    <section className="policy-boundary">
      <strong>Access Grants are declared governance records</strong>
      <p>
        Grants describe intended Agent access to Capabilities, Sources,
        ModelAssets, or external targets. They are not credentials, do not create
        IAM permissions, and are not automatically enforced by the Runtime
        Gateway unless PolicyRules explicitly use them as context.
      </p>
    </section>
  );
}

function AccessGrantFilters({
  onStatusFilterChange,
  onSubjectFilterChange,
  onTargetFilterChange,
  statusFilter,
  subjectFilter,
  targetFilter
}: {
  onStatusFilterChange: (value: GrantStatusFilter) => void;
  onSubjectFilterChange: (value: string) => void;
  onTargetFilterChange: (value: GrantTargetFilter) => void;
  statusFilter: GrantStatusFilter;
  subjectFilter: string;
  targetFilter: GrantTargetFilter;
}) {
  return (
    <div className="filter-bar access-grant-filters">
      <label>
        <span>status</span>
        <select
          value={statusFilter}
          onChange={(event) =>
            onStatusFilterChange(event.target.value as GrantStatusFilter)
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
        <span>target_type</span>
        <select
          value={targetFilter}
          onChange={(event) =>
            onTargetFilterChange(event.target.value as GrantTargetFilter)
          }
        >
          {targetFilters.map((targetType) => (
            <option key={targetType} value={targetType}>
              {formatValue(targetType)}
            </option>
          ))}
        </select>
      </label>

      <label>
        <span>subject / agent</span>
        <input
          type="text"
          value={subjectFilter}
          onChange={(event) => onSubjectFilterChange(event.target.value)}
          placeholder="Filter by subject_id"
          spellCheck={false}
        />
      </label>
    </div>
  );
}

function AccessGrantStatusSummary({ grants }: { grants: AccessGrantRecord[] }) {
  const counts = statusFilters
    .filter((status) => status !== "all")
    .map((status) => [
      status,
      grants.filter((grant) => grant.status === status).length
    ] as const);

  return (
    <div className="detail-count-grid access-grant-counts">
      {counts.map(([status, count]) => (
        <div key={status}>
          <span>{formatValue(status)}</span>
          <strong>{count}</strong>
        </div>
      ))}
    </div>
  );
}

function AccessGrantTable({
  grants,
  onTransitionComplete
}: {
  grants: AccessGrantRecord[];
  onTransitionComplete: (
    grant: AccessGrantRecord,
    action: AccessGrantTransitionAction
  ) => Promise<void> | void;
}) {
  if (grants.length === 0) {
    return (
      <div className="state-message compact">
        <strong>No Access Grants match the current filters</strong>
        <p>Adjust status, target type, or subject filters to review grants.</p>
      </div>
    );
  }

  return (
    <div className="table-scroll">
      <table className="data-table access-grants-table">
        <thead>
          <tr>
            <th>ID</th>
            <th>Subject</th>
            <th>Target</th>
            <th>Status</th>
            <th>Risk</th>
            <th>Reason</th>
            <th>Granted By</th>
            <th>Expires</th>
            <th>References</th>
            <th>Safe Metadata</th>
            <th>Created</th>
            <th>Updated</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {grants.map((grant) => (
            <tr key={grant.id}>
              <td className="id-cell">{grant.id}</td>
              <td>
                <span className="table-pill">
                  {formatValue(grant.subject_type)}
                </span>
                <div className="id-cell">{grant.subject_id}</div>
              </td>
              <td>
                <span className="table-pill">
                  {formatValue(grant.target_type)}
                </span>
                <div className="id-cell">
                  {grant.target_id || grant.external_ref || "Not set"}
                </div>
              </td>
              <td>
                <span className={`table-pill grant-${grant.status}`}>
                  {formatValue(grant.status)}
                </span>
              </td>
              <td>{formatValue(grant.risk_level)}</td>
              <td>{plainValue(grant.reason)}</td>
              <td className="id-cell">
                {grant.granted_by_actor_type}:{grant.granted_by_actor_id}
              </td>
              <td>{formatTimestamp(grant.expires_at)}</td>
              <td>
                <GrantReferences grant={grant} />
              </td>
              <td>
                <details className="table-details">
                  <summary>Safe metadata</summary>
                  <pre className="metadata-block">
                    {metadataText(grant.metadata)}
                  </pre>
                </details>
              </td>
              <td>{formatTimestamp(grant.created_at)}</td>
              <td>{formatTimestamp(grant.updated_at)}</td>
              <td>
                <AccessGrantTransitionActions
                  grant={grant}
                  onTransitionComplete={onTransitionComplete}
                />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function AccessGrantTransitionActions({
  grant,
  onTransitionComplete
}: {
  grant: AccessGrantRecord;
  onTransitionComplete: (
    grant: AccessGrantRecord,
    action: AccessGrantTransitionAction
  ) => Promise<void> | void;
}) {
  const [transitionNote, setTransitionNote] = useState("");
  const [actionState, setActionState] = useState<AccessGrantActionState>({
    status: "idle"
  });
  const actions = transitionActionsForStatus(grant.status);

  if (actions.length === 0) {
    return (
      <span className="grant-transition-note">
        Terminal governance status. No transition actions are available.
      </span>
    );
  }

  const loadingAction =
    actionState.status === "loading" ? actionState.action : null;
  const isLoading = loadingAction !== null;

  async function handleTransition(action: AccessGrantTransitionAction) {
    setActionState({ status: "loading", action });

    try {
      const updatedGrant = await transitionAccessGrant(
        grant.id,
        action,
        transitionNote
      );
      await onTransitionComplete(updatedGrant, action);
      setTransitionNote("");
      setActionState({
        status: "success",
        message: `Access Grant ${transitionPastTense(action)}.`
      });
    } catch (error: unknown) {
      setActionState({
        status: "error",
        message: accessGrantTransitionErrorMessage(error)
      });
    }
  }

  return (
    <div className="grant-transition-actions">
      <label className="grant-transition-field">
        <span>Transition note</span>
        <input
          type="text"
          value={transitionNote}
          onChange={(event) => setTransitionNote(event.target.value)}
          placeholder="Optional governance note"
          disabled={isLoading}
        />
      </label>
      <div
        className="grant-transition-buttons"
        aria-label="Access Grant transition actions"
      >
        {actions.map((action) => (
          <button
            key={action}
            className={`table-action-button grant-action-${action}`}
            type="button"
            disabled={isLoading}
            onClick={() => void handleTransition(action)}
          >
            {loadingAction === action
              ? `${formatValue(action)}...`
              : formatValue(action)}
          </button>
        ))}
      </div>
      <p className="grant-transition-help">
        Updates the governance record status only.
      </p>
      {actionState.status === "success" ? (
        <p className="approval-action-status success" aria-live="polite">
          {actionState.message}
        </p>
      ) : null}
      {actionState.status === "error" ? (
        <p className="approval-action-status error" role="alert">
          {actionState.message}
        </p>
      ) : null}
    </div>
  );
}

function GrantReferences({ grant }: { grant: AccessGrantRecord }) {
  return (
    <div className="grant-reference-links">
      {grant.subject_type === "agent" ? (
        <Link className="row-link" href={`/agents/${grant.subject_id}`}>
          Agent Governance Profile
        </Link>
      ) : null}

      {grant.subject_type === "agent" ? (
        <Link className="row-link" href="/evidence">
          Evidence Bundle lookup
        </Link>
      ) : null}

      {grant.target_type === "source" ? (
        <Link className="row-link" href="/access-data">
          Source/Data Usage workflow
        </Link>
      ) : null}

      {grant.subject_type !== "agent" && grant.target_type !== "source" ? (
        <span>Reference-only grant</span>
      ) : null}
    </div>
  );
}
