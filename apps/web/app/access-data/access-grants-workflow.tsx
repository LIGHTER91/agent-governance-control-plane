"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { getApiBaseUrl } from "../lib/api";
import {
  AccessGrantRecord,
  SourceMetadata,
  fetchAccessGrants
} from "../lib/sources";

type AccessGrantsState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; grants: AccessGrantRecord[] };

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

export function AccessGrantsWorkflow() {
  const [state, setState] = useState<AccessGrantsState>({ status: "loading" });
  const [statusFilter, setStatusFilter] = useState<GrantStatusFilter>("all");
  const [targetFilter, setTargetFilter] = useState<GrantTargetFilter>("all");
  const [subjectFilter, setSubjectFilter] = useState("");

  useEffect(() => {
    const controller = new AbortController();

    setState({ status: "loading" });
    fetchAccessGrants(controller.signal)
      .then((grants) => {
        setState({ status: "ready", grants });
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) {
          return;
        }

        setState({
          status: "error",
          message: accessGrantErrorMessage(error)
        });
      });

    return () => {
      controller.abort();
    };
  }, []);

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
                These records declare governed access. Runtime enforcement happens only through explicit policies and runtime decisions.
              </p>
            </div>
            <AccessGrantFilters
              statusFilter={statusFilter}
              subjectFilter={subjectFilter}
              targetFilter={targetFilter}
              onStatusFilterChange={setStatusFilter}
              onSubjectFilterChange={setSubjectFilter}
              onTargetFilterChange={setTargetFilter}
            />
            <AccessGrantStatusSummary grants={state.grants} />
            <AccessGrantTable grants={filteredGrants} />
          </>
        ) : null}
      </section>
    </section>
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

function AccessGrantTable({ grants }: { grants: AccessGrantRecord[] }) {
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
            </tr>
          ))}
        </tbody>
      </table>
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
