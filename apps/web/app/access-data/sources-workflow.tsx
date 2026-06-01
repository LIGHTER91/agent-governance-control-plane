"use client";

import { useEffect, useMemo, useState } from "react";
import { ApiRequestError, getApiBaseUrl } from "../lib/api";
import {
  AccessGrantRecord,
  DataUsageProfile,
  SourceMetadata,
  SourceRecord,
  fetchAccessGrants,
  fetchSourceUsageProfile,
  fetchSources
} from "../lib/sources";

type SourcesState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; sources: SourceRecord[] };

type ProfileState =
  | { status: "idle" }
  | { status: "loading"; sourceId: string }
  | { status: "missing"; sourceId: string }
  | { status: "error"; sourceId: string; message: string }
  | { status: "ready"; sourceId: string; profile: DataUsageProfile };

type RelatedGrantState =
  | { status: "idle" }
  | { status: "loading"; sourceId: string }
  | { status: "error"; sourceId: string; message: string }
  | { status: "ready"; sourceId: string; grants: AccessGrantRecord[] };

type UsageSignal = {
  label: string;
  status: "listed_allowed" | "listed_prohibited" | "no_signal";
  detail: string;
};

type FieldRow = [string, string | number | boolean | null | undefined];

const usageQuestions = [
  {
    label: "RAG retrieval",
    tokens: ["rag", "retrieval", "retrieve", "search"]
  },
  {
    label: "Vectorization / embedding",
    tokens: ["vector", "vectorization", "embedding", "semantic_search_indexing"]
  },
  {
    label: "Summarization",
    tokens: ["summarization", "summarize", "summary"]
  },
  {
    label: "Training",
    tokens: ["training", "model_training", "fine_tuning", "training_data"]
  },
  {
    label: "External model usage",
    tokens: [
      "external_model",
      "external_models",
      "external_provider",
      "external_llm",
      "third_party_model"
    ]
  }
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

function sourceErrorMessage(error: unknown) {
  return error instanceof Error
    ? error.message
    : "Unable to load Sources from the backend.";
}

function profileErrorState(error: unknown, sourceId: string): ProfileState {
  if (error instanceof ApiRequestError) {
    if (error.status === 404) {
      return { status: "missing", sourceId };
    }

    return {
      status: "error",
      sourceId,
      message: `Data Usage Profile request failed with status ${error.status}.`
    };
  }

  return {
    status: "error",
    sourceId,
    message:
      error instanceof Error
        ? error.message
        : "Unable to load the Data Usage Profile from the backend."
  };
}

function relatedGrantErrorMessage(error: unknown) {
  return error instanceof Error
    ? error.message
    : "Unable to load Access Grants from the backend.";
}

export function SourcesWorkflow() {
  const [sourcesState, setSourcesState] = useState<SourcesState>({
    status: "loading"
  });
  const [selectedSource, setSelectedSource] = useState<SourceRecord | null>(null);
  const [profileState, setProfileState] = useState<ProfileState>({
    status: "idle"
  });
  const [relatedGrantState, setRelatedGrantState] = useState<RelatedGrantState>({
    status: "idle"
  });

  useEffect(() => {
    const controller = new AbortController();

    setSourcesState({ status: "loading" });
    fetchSources(controller.signal)
      .then((sources) => {
        setSourcesState({ status: "ready", sources });
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) {
          return;
        }

        setSourcesState({ status: "error", message: sourceErrorMessage(error) });
      });

    return () => {
      controller.abort();
    };
  }, []);

  async function handleSelectSource(source: SourceRecord) {
    const controller = new AbortController();

    setSelectedSource(source);
    setProfileState({ status: "loading", sourceId: source.id });
    setRelatedGrantState({ status: "loading", sourceId: source.id });

    fetchSourceUsageProfile(source.id, controller.signal)
      .then((profile) => {
        setProfileState({
          status: "ready",
          sourceId: source.id,
          profile
        });
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) {
          return;
        }

        setProfileState(profileErrorState(error, source.id));
      });

    fetchAccessGrants(controller.signal)
      .then((grants) => {
        setRelatedGrantState({
          status: "ready",
          sourceId: source.id,
          grants: grants.filter(
            (grant) =>
              grant.target_type === "source" && grant.target_id === source.id
          )
        });
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) {
          return;
        }

        setRelatedGrantState({
          status: "error",
          sourceId: source.id,
          message: relatedGrantErrorMessage(error)
        });
      });
  }

  return (
    <div className="access-data-workflow">
      <WorkflowBoundary />
      <section className="source-workspace" aria-label="Source Data Usage workflow">
        <SourcesPanel
          onSelectSource={handleSelectSource}
          selectedSourceId={selectedSource?.id || null}
          sourcesState={sourcesState}
        />
        <SourceReviewPanel
          profileState={profileState}
          relatedGrantState={relatedGrantState}
          source={selectedSource}
        />
      </section>
    </div>
  );
}

function WorkflowBoundary() {
  return (
    <section className="policy-boundary">
      <strong>Data Usage Profiles are governance metadata</strong>
      <p>
        This workflow reviews safe Source metadata for runtime context and
        evidence collection. It does not inspect raw Source contents, scan
        documents, connect external DLP tools, or certify legal compliance.
      </p>
    </section>
  );
}

function SourcesPanel({
  onSelectSource,
  selectedSourceId,
  sourcesState
}: {
  onSelectSource: (source: SourceRecord) => void;
  selectedSourceId: string | null;
  sourcesState: SourcesState;
}) {
  return (
    <section className="evidence-section source-list-panel">
      <header className="evidence-section-header">
        <div>
          <h3>Sources</h3>
          <p>GET /sources from {getApiBaseUrl()}</p>
        </div>
        <span>{sourcesState.status === "ready" ? sourcesState.sources.length : 0}</span>
      </header>

      {sourcesState.status === "loading" ? (
        <div className="state-message compact" aria-live="polite">
          <strong>Loading Sources</strong>
          <p>Requesting Source inventory records from the backend.</p>
        </div>
      ) : null}

      {sourcesState.status === "error" ? (
        <div className="state-message error compact" role="alert">
          <strong>Unable to load Sources</strong>
          <p>{sourcesState.message}</p>
        </div>
      ) : null}

      {sourcesState.status === "ready" && sourcesState.sources.length === 0 ? (
        <div className="state-message compact">
          <strong>No Sources found</strong>
          <p>
            Source records will appear here after the backend Source inventory
            API has data.
          </p>
        </div>
      ) : null}

      {sourcesState.status === "ready" && sourcesState.sources.length > 0 ? (
        <ul className="source-list">
          {sourcesState.sources.map((source) => (
            <li key={source.id}>
              <button
                className={
                  selectedSourceId === source.id ? "source-selected" : undefined
                }
                type="button"
                onClick={() => onSelectSource(source)}
              >
                <span className="source-list-header">
                  <strong>{source.name}</strong>
                  <span className={`table-pill policy-${source.status}`}>
                    {formatValue(source.status)}
                  </span>
                </span>
                <span>
                  {formatValue(source.source_type)} / {formatValue(source.risk_level)}
                </span>
                <span className="id-cell">{source.id}</span>
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}

function SourceReviewPanel({
  profileState,
  relatedGrantState,
  source
}: {
  profileState: ProfileState;
  relatedGrantState: RelatedGrantState;
  source: SourceRecord | null;
}) {
  if (!source) {
    return (
      <section className="evidence-section source-review-panel">
        <SectionHeader title="Source review" count={0} />
        <div className="state-message compact">
          <strong>No Source selected</strong>
          <p>
            Select a Source to load its Data Usage Profile and review safe
            governance metadata.
          </p>
        </div>
      </section>
    );
  }

  return (
    <div className="source-review-stack">
      <SourceSummary source={source} />
      <ProfileStatus profileState={profileState} source={source} />
      {profileState.status === "ready" ? (
        <>
          <UsageQuestions profile={profileState.profile} />
          <DataUsageProfileDetails profile={profileState.profile} />
        </>
      ) : null}
      <RelatedAccessGrants relatedGrantState={relatedGrantState} />
    </div>
  );
}

function SourceSummary({ source }: { source: SourceRecord }) {
  const sourceRows: FieldRow[] = [
    ["source_id", source.id],
    ["name", source.name],
    ["source_type", source.source_type],
    ["status", source.status],
    ["risk_level", source.risk_level],
    ["external_ref", source.external_ref],
    ["owner", source.owner_name],
    ["owner_type", source.owner_type],
    ["owner_id", source.owner_id],
    ["owner_contact_email", source.owner_contact_email],
    ["created_at", formatTimestamp(source.created_at)],
    ["updated_at", formatTimestamp(source.updated_at)]
  ];

  return (
    <section className="evidence-section">
      <SectionHeader title="source_governance_context" count={sourceRows.length} />
      <dl className="evidence-fields">
        {sourceRows.map(([label, value]) => (
          <div key={label}>
            <dt>{label}</dt>
            <dd className={label.endsWith("_id") ? "id-cell" : undefined}>
              {plainValue(value)}
            </dd>
          </div>
        ))}
      </dl>
      <details className="profile-technical-details">
        <summary>Safe Source metadata</summary>
        <pre className="source-metadata-block">{metadataText(source.metadata)}</pre>
      </details>
    </section>
  );
}

function ProfileStatus({
  profileState,
  source
}: {
  profileState: ProfileState;
  source: SourceRecord;
}) {
  return (
    <section className="evidence-section">
      <header className="evidence-section-header">
        <div>
          <h3>Data Usage Profile</h3>
          <p>GET /sources/{"{source_id}"}/usage-profile</p>
        </div>
        <span>{profileState.status}</span>
      </header>

      {profileState.status === "loading" ? (
        <div className="state-message compact" aria-live="polite">
          <strong>Loading Data Usage Profile</strong>
          <p>Requesting governance metadata for {source.name}.</p>
        </div>
      ) : null}

      {profileState.status === "missing" ? (
        <div className="state-message compact">
          <strong>No Data Usage Profile found</strong>
          <p>
            This Source has inventory metadata, but no linked review profile
            yet. Runtime context can only use Source metadata that exists.
          </p>
        </div>
      ) : null}

      {profileState.status === "error" ? (
        <div className="state-message error compact" role="alert">
          <strong>Unable to load Data Usage Profile</strong>
          <p>{profileState.message}</p>
        </div>
      ) : null}

      {profileState.status === "ready" ? (
        <div className="state-message compact success-state">
          <strong>Data Usage Profile loaded</strong>
          <p>
            Review status is {formatValue(profileState.profile.review_status)}.
            This is governance metadata and does not certify legal compliance.
          </p>
        </div>
      ) : null}
    </section>
  );
}

function UsageQuestions({ profile }: { profile: DataUsageProfile }) {
  const signals = usageQuestions.map((question) =>
    usageSignal(profile, question.label, question.tokens)
  );

  return (
    <section className="evidence-section">
      <SectionHeader title="review_questions" count={signals.length} />
      <div className="usage-signal-grid">
        {signals.map((signal) => (
          <article className="usage-signal-card" key={signal.label}>
            <span className={`usage-signal ${signal.status}`}>
              {signalStatusLabel(signal.status)}
            </span>
            <strong>{signal.label}</strong>
            <p>{signal.detail}</p>
          </article>
        ))}
      </div>
    </section>
  );
}

function DataUsageProfileDetails({ profile }: { profile: DataUsageProfile }) {
  const reviewedBy =
    profile.reviewed_by_actor_type && profile.reviewed_by_actor_id
      ? `${profile.reviewed_by_actor_type}:${profile.reviewed_by_actor_id}`
      : null;
  const rows: FieldRow[] = [
    ["profile_id", profile.id],
    ["source_id", profile.source_id],
    ["data_classification", profile.data_classification],
    ["contains_personal_data", plainValue(profile.contains_personal_data)],
    ["contains_sensitive_data", plainValue(profile.contains_sensitive_data)],
    ["residency", profile.residency],
    ["retention_policy", profile.retention_policy],
    ["data_owner", profile.data_owner],
    ["review_status", profile.review_status],
    ["reviewed_by", reviewedBy],
    ["reviewed_at", formatTimestamp(profile.reviewed_at)],
    ["review_expires_at", formatTimestamp(profile.review_expires_at)],
    ["dpia_required", plainValue(profile.dpia_required)],
    ["dpia_reference", profile.dpia_reference],
    ["created_at", formatTimestamp(profile.created_at)],
    ["updated_at", formatTimestamp(profile.updated_at)]
  ];

  return (
    <section className="evidence-section">
      <SectionHeader title="data_usage_profile_fields" count={rows.length} />
      <dl className="evidence-fields">
        {rows.map(([label, value]) => (
          <div key={label}>
            <dt>{label}</dt>
            <dd className={label.endsWith("_id") ? "id-cell" : undefined}>
              {plainValue(value)}
            </dd>
          </div>
        ))}
      </dl>
      <section className="data-usage-lists" aria-label="Data usage lists">
        <ProfileList title="data_categories" values={profile.data_categories} />
        <ProfileList title="allowed_purposes" values={profile.allowed_purposes} />
        <ProfileList
          title="prohibited_purposes"
          values={profile.prohibited_purposes}
        />
        <ProfileList
          title="allowed_processing"
          values={profile.allowed_processing}
        />
        <ProfileList
          title="prohibited_processing"
          values={profile.prohibited_processing}
        />
      </section>
      <details className="profile-technical-details">
        <summary>Safe Data Usage Profile metadata</summary>
        <pre className="source-metadata-block">{metadataText(profile.metadata)}</pre>
      </details>
    </section>
  );
}

function ProfileList({ title, values }: { title: string; values: string[] }) {
  return (
    <div>
      <h4>{title}</h4>
      {values.length === 0 ? (
        <p>No values recorded.</p>
      ) : (
        <ul className="chip-list">
          {values.map((value) => (
            <li key={value}>{value}</li>
          ))}
        </ul>
      )}
    </div>
  );
}

function RelatedAccessGrants({
  relatedGrantState
}: {
  relatedGrantState: RelatedGrantState;
}) {
  return (
    <section className="evidence-section">
      <SectionHeader
        title="related_source_access_grants"
        count={
          relatedGrantState.status === "ready"
            ? relatedGrantState.grants.length
            : 0
        }
      />
      {relatedGrantState.status === "idle" ? (
        <div className="state-message compact">
          <strong>No Source selected</strong>
          <p>Related Access Grants load after selecting a Source.</p>
        </div>
      ) : null}

      {relatedGrantState.status === "loading" ? (
        <div className="state-message compact" aria-live="polite">
          <strong>Loading Access Grants</strong>
          <p>Filtering GET /access-grants for grants targeting this Source.</p>
        </div>
      ) : null}

      {relatedGrantState.status === "error" ? (
        <div className="state-message error compact" role="alert">
          <strong>Unable to load related Access Grants</strong>
          <p>{relatedGrantState.message}</p>
        </div>
      ) : null}

      {relatedGrantState.status === "ready" &&
      relatedGrantState.grants.length === 0 ? (
        <div className="state-message compact">
          <strong>No related Access Grants found</strong>
          <p>
            This page did not find Agent Access Grants targeting the selected
            Source. Agent-specific access remains visible on Agent Governance
            Profiles and Evidence Bundles.
          </p>
        </div>
      ) : null}

      {relatedGrantState.status === "ready" &&
      relatedGrantState.grants.length > 0 ? (
        <div className="table-scroll">
          <table className="data-table source-grants-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Name</th>
                <th>Agent ID</th>
                <th>Status</th>
                <th>Risk</th>
                <th>Reason</th>
                <th>Expires</th>
              </tr>
            </thead>
            <tbody>
              {relatedGrantState.grants.map((grant) => (
                <tr key={grant.id}>
                  <td className="id-cell">{grant.id}</td>
                  <td>{grant.name}</td>
                  <td className="id-cell">{grant.subject_id}</td>
                  <td>{formatValue(grant.status)}</td>
                  <td>{formatValue(grant.risk_level)}</td>
                  <td>{plainValue(grant.reason)}</td>
                  <td>{formatTimestamp(grant.expires_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </section>
  );
}

function SectionHeader({ title, count }: { title: string; count: number }) {
  return (
    <header className="evidence-section-header">
      <h3>{title}</h3>
      <span>{count}</span>
    </header>
  );
}

function usageSignal(
  profile: DataUsageProfile,
  label: string,
  tokens: string[]
): UsageSignal {
  const allowedMatches = matchingValues(
    [...profile.allowed_purposes, ...profile.allowed_processing],
    tokens
  );
  const prohibitedMatches = matchingValues(
    [...profile.prohibited_purposes, ...profile.prohibited_processing],
    tokens
  );

  if (prohibitedMatches.length > 0) {
    return {
      label,
      status: "listed_prohibited",
      detail: `Listed in prohibited profile fields: ${prohibitedMatches.join(", ")}.`
    };
  }

  if (allowedMatches.length > 0) {
    return {
      label,
      status: "listed_allowed",
      detail: `Listed in allowed profile fields: ${allowedMatches.join(", ")}.`
    };
  }

  return {
    label,
    status: "no_signal",
    detail:
      "No explicit allowed or prohibited profile entry. Review the Source owner and policy context before use."
  };
}

function matchingValues(values: string[], tokens: string[]) {
  return values.filter((value) => {
    const normalizedValue = normalizeForMatch(value);
    return tokens.some((token) => normalizedValue.includes(normalizeForMatch(token)));
  });
}

function normalizeForMatch(value: string) {
  return value.toLowerCase().replace(/[\s-]+/g, "_");
}

function signalStatusLabel(status: UsageSignal["status"]) {
  if (status === "listed_allowed") {
    return "Listed allowed";
  }

  if (status === "listed_prohibited") {
    return "Listed prohibited";
  }

  return "No explicit signal";
}
