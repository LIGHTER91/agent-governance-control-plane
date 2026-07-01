"use client";

import Link from "next/link";
import type { ReactNode } from "react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { ApiRequestError, getApiBaseUrl } from "../lib/api";
import {
  AccessGrantRecord,
  AccessGrantTransitionAction,
  CapabilityRecord,
  DataUsageProfile,
  ModelAssetRecord,
  SourceRecord,
  fetchAccessGrants,
  fetchCapabilities,
  fetchModels,
  fetchSourceUsageProfile,
  fetchSources,
  transitionAccessGrant
} from "../lib/sources";

type LoadState<T> =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; data: T };

type UsageProfilesPayload = {
  profiles: DataUsageProfile[];
  missingSourceIds: string[];
  erroredSourceIds: Array<{ sourceId: string; message: string }>;
};

type GrantStatusFilter =
  | "all"
  | "active"
  | "pending_review"
  | "suspended"
  | "revoked"
  | "expired";

type ReadinessTone = "ready" | "missing" | "error" | "loading" | "not-wired";

type ReadinessItem = {
  checkType: string;
  title: string;
  tone: ReadinessTone;
  headline: string;
  detail: string;
};

const grantStatusFilters: GrantStatusFilter[] = [
  "all",
  "active",
  "pending_review",
  "suspended",
  "revoked",
  "expired"
];

const unsafeMetadataTerms = [
  "raw",
  "prompt",
  "secret",
  "token",
  "credential",
  "api_key",
  "password",
  "source_content",
  "private_payload",
  "authorization"
];

function emptyState<T>(): LoadState<T> {
  return { status: "loading" };
}

function loadErrorMessage(error: unknown, label: string) {
  if (error instanceof ApiRequestError) {
    if (error.status === 403) {
      return `${label} require an authorized governance actor.`;
    }

    if (error.status === 404) {
      return `${label} are not wired in this backend.`;
    }

    return `${label} could not load from the AGCP API.`;
  }

  return error instanceof Error ? error.message : `${label} could not load.`;
}

function transitionErrorMessage(error: unknown) {
  if (error instanceof ApiRequestError) {
    if (error.status === 404) {
      return "Access Grant not found. Refresh Access & Data and try again.";
    }

    if (error.status === 409) {
      return "The backend rejected this transition for the current Access Grant status.";
    }

    if (error.status === 403) {
      return "This actor is not authorized to transition the Access Grant.";
    }
  }

  return error instanceof Error
    ? error.message
    : "Unable to update Access Grant status.";
}

function formatValue(value: string | number | boolean | null | undefined) {
  if (value === null || value === undefined || value === "") {
    return "Not set";
  }

  if (typeof value === "boolean") {
    return value ? "Yes" : "No";
  }

  if (typeof value === "number") {
    return String(value);
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

function shortId(value: string | null | undefined) {
  if (!value) {
    return "Not set";
  }

  return value.length > 12 ? `${value.slice(0, 8)}...${value.slice(-4)}` : value;
}

function statusTone(status: string | null | undefined) {
  if (!status) {
    return "muted";
  }

  if (["active", "approved", "pass"].includes(status)) {
    return "ok";
  }

  if (["pending_review", "needs_review", "draft", "expired"].includes(status)) {
    return "warn";
  }

  if (["suspended", "revoked", "rejected", "disabled", "retired"].includes(status)) {
    return "danger";
  }

  return "info";
}

function normalizeClass(value: string | null | undefined) {
  return (value || "not_set").replace(/[^a-zA-Z0-9_-]/g, "_").toLowerCase();
}

function isSafeMetadataKey(key: string) {
  const normalized = key.toLowerCase();
  return !unsafeMetadataTerms.some((term) => normalized.includes(term));
}

function sanitizeMetadata(value: unknown): unknown {
  if (Array.isArray(value)) {
    return value.map((item) => sanitizeMetadata(item));
  }

  if (value && typeof value === "object") {
    return Object.fromEntries(
      Object.entries(value as Record<string, unknown>)
        .filter(([key]) => isSafeMetadataKey(key))
        .map(([key, nestedValue]) => [key, sanitizeMetadata(nestedValue)])
    );
  }

  return value;
}

function metadataEntries(metadata: Record<string, unknown> | null | undefined) {
  if (!metadata) {
    return [];
  }

  return Object.entries(metadata)
    .filter(([key]) => isSafeMetadataKey(key))
    .map(([key, value]) => [key, sanitizeMetadata(value)] as const)
    .filter(([, value]) => {
      if (value && typeof value === "object" && !Array.isArray(value)) {
        return Object.keys(value as Record<string, unknown>).length > 0;
      }

      return true;
    });
}

function formatMetadataValue(value: unknown) {
  if (value === null || value === undefined || value === "") {
    return "Not set";
  }

  if (typeof value === "string" || typeof value === "number") {
    return String(value);
  }

  if (typeof value === "boolean") {
    return value ? "true" : "false";
  }

  return JSON.stringify(value);
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

function providerType(provider: string | null | undefined) {
  if (!provider) {
    return "unknown";
  }

  return provider === "local" ? "local" : "external";
}

function chipValues(values: string[]) {
  return values.length > 0 ? values : ["Not set"];
}

function accessGrantTargetKey(grant: AccessGrantRecord) {
  return grant.target_id || grant.external_ref || "unscoped";
}

function accessGrantTargetLabel(
  grant: AccessGrantRecord,
  sourcesById: Map<string, SourceRecord>,
  modelsById: Map<string, ModelAssetRecord>,
  capabilitiesById: Map<string, CapabilityRecord>
) {
  const targetId = accessGrantTargetKey(grant);

  if (grant.target_type === "source") {
    return sourcesById.get(targetId)?.name || targetId;
  }

  if (grant.target_type === "model_asset") {
    return modelsById.get(targetId)?.name || targetId;
  }

  if (grant.target_type === "capability") {
    return capabilitiesById.get(targetId)?.name || targetId;
  }

  return targetId;
}

async function loadUsageProfilesForSources(
  sources: SourceRecord[],
  signal?: AbortSignal
): Promise<UsageProfilesPayload> {
  const results = await Promise.all(
    sources.map(async (source) => {
      try {
        return {
          sourceId: source.id,
          status: "profile" as const,
          profile: await fetchSourceUsageProfile(source.id, signal)
        };
      } catch (error: unknown) {
        if (error instanceof ApiRequestError && error.status === 404) {
          return {
            sourceId: source.id,
            status: "missing" as const
          };
        }

        return {
          sourceId: source.id,
          status: "error" as const,
          message: loadErrorMessage(error, "Data Usage Profiles")
        };
      }
    })
  );

  const payload: UsageProfilesPayload = {
    profiles: [],
    missingSourceIds: [],
    erroredSourceIds: []
  };

  for (const result of results) {
    if (result.status === "profile") {
      payload.profiles.push(result.profile);
    } else if (result.status === "missing") {
      payload.missingSourceIds.push(result.sourceId);
    } else {
      payload.erroredSourceIds.push({
        sourceId: result.sourceId,
        message: result.message
      });
    }
  }

  return payload;
}

function StatePanel({
  tone = "default",
  title,
  children
}: {
  tone?: "default" | "error" | "warn";
  title: string;
  children: ReactNode;
}) {
  return (
    <div className={`access-data-state ${tone}`}>
      <strong>{title}</strong>
      <p>{children}</p>
    </div>
  );
}

function SectionShell({
  id,
  eyebrow,
  title,
  description,
  children
}: {
  id: string;
  eyebrow: string;
  title: string;
  description: string;
  children: ReactNode;
}) {
  return (
    <section className="access-data-section" id={id} aria-labelledby={`${id}-title`}>
      <header className="access-data-section-header">
        <div>
          <span>{eyebrow}</span>
          <h2 id={`${id}-title`}>{title}</h2>
          <p>{description}</p>
        </div>
      </header>
      {children}
    </section>
  );
}

function SafeMetadataPreview({
  title,
  metadata
}: {
  title: string;
  metadata: Record<string, unknown> | null | undefined;
}) {
  const entries = metadataEntries(metadata);

  return (
    <details className="access-metadata-preview">
      <summary>{title}</summary>
      {entries.length === 0 ? (
        <p>No safe metadata values to display.</p>
      ) : (
        <dl>
          {entries.slice(0, 6).map(([key, value]) => (
            <div key={key}>
              <dt>{key}</dt>
              <dd>{formatMetadataValue(value)}</dd>
            </div>
          ))}
        </dl>
      )}
      {entries.length > 6 ? (
        <p>{entries.length - 6} additional safe metadata values omitted.</p>
      ) : null}
    </details>
  );
}

function StatusPill({ value }: { value: string | null | undefined }) {
  return (
    <span className={`access-pill ${statusTone(value)} status-${normalizeClass(value)}`}>
      {formatValue(value)}
    </span>
  );
}

function MiniField({
  label,
  value
}: {
  label: string;
  value: string | number | boolean | null | undefined;
}) {
  return (
    <div>
      <dt>{label}</dt>
      <dd>{formatValue(value)}</dd>
    </div>
  );
}

function IdField({ label, value }: { label: string; value: string | null | undefined }) {
  return (
    <div>
      <dt>{label}</dt>
      <dd className="access-mono" title={value || undefined}>
        {shortId(value)}
      </dd>
    </div>
  );
}

export function AccessInventoryMatrix() {
  const [sourcesState, setSourcesState] =
    useState<LoadState<SourceRecord[]>>(emptyState);
  const [usageProfilesState, setUsageProfilesState] =
    useState<LoadState<UsageProfilesPayload>>(emptyState);
  const [accessGrantsState, setAccessGrantsState] =
    useState<LoadState<AccessGrantRecord[]>>(emptyState);
  const [modelsState, setModelsState] =
    useState<LoadState<ModelAssetRecord[]>>(emptyState);
  const [capabilitiesState, setCapabilitiesState] =
    useState<LoadState<CapabilityRecord[]>>(emptyState);
  const [grantStatusFilter, setGrantStatusFilter] =
    useState<GrantStatusFilter>("all");
  const [grantQuery, setGrantQuery] = useState("");
  const [selectedGrantId, setSelectedGrantId] = useState<string | null>(null);
  const [transitionNote, setTransitionNote] = useState("");
  const [actionState, setActionState] = useState<
    | { status: "idle" }
    | { status: "loading"; action: AccessGrantTransitionAction }
    | { status: "success"; message: string }
    | { status: "error"; message: string }
  >({ status: "idle" });

  const loadAccessData = useCallback((signal?: AbortSignal) => {
    setSourcesState({ status: "loading" });
    setUsageProfilesState({ status: "loading" });
    setAccessGrantsState({ status: "loading" });
    setModelsState({ status: "loading" });
    setCapabilitiesState({ status: "loading" });

    fetchSources(signal)
      .then((sources) => {
        setSourcesState({ status: "ready", data: sources });

        if (sources.length === 0) {
          setUsageProfilesState({
            status: "ready",
            data: { profiles: [], missingSourceIds: [], erroredSourceIds: [] }
          });
          return;
        }

        loadUsageProfilesForSources(sources, signal)
          .then((profiles) => {
            setUsageProfilesState({ status: "ready", data: profiles });
          })
          .catch((error: unknown) => {
            if (!signal?.aborted) {
              setUsageProfilesState({
                status: "error",
                message: loadErrorMessage(error, "Data Usage Profiles")
              });
            }
          });
      })
      .catch((error: unknown) => {
        if (!signal?.aborted) {
          setSourcesState({
            status: "error",
            message: loadErrorMessage(error, "Data Sources")
          });
          setUsageProfilesState({
            status: "error",
            message: "Data Usage Profiles require Sources to load first."
          });
        }
      });

    fetchAccessGrants(signal)
      .then((grants) => {
        setAccessGrantsState({ status: "ready", data: grants });
      })
      .catch((error: unknown) => {
        if (!signal?.aborted) {
          setAccessGrantsState({
            status: "error",
            message: loadErrorMessage(error, "Access Grants")
          });
        }
      });

    fetchModels(signal)
      .then((models) => {
        setModelsState({ status: "ready", data: models });
      })
      .catch((error: unknown) => {
        if (!signal?.aborted) {
          setModelsState({
            status: "error",
            message: loadErrorMessage(error, "Models")
          });
        }
      });

    fetchCapabilities(signal)
      .then((capabilities) => {
        setCapabilitiesState({ status: "ready", data: capabilities });
      })
      .catch((error: unknown) => {
        if (!signal?.aborted) {
          setCapabilitiesState({
            status: "error",
            message: loadErrorMessage(error, "Capabilities")
          });
        }
      });
  }, []);

  useEffect(() => {
    const controller = new AbortController();

    loadAccessData(controller.signal);

    return () => controller.abort();
  }, [loadAccessData]);

  const sources = sourcesState.status === "ready" ? sourcesState.data : [];
  const usageProfiles =
    usageProfilesState.status === "ready"
      ? usageProfilesState.data.profiles
      : [];
  const accessGrants =
    accessGrantsState.status === "ready" ? accessGrantsState.data : [];
  const models = modelsState.status === "ready" ? modelsState.data : [];
  const capabilities =
    capabilitiesState.status === "ready" ? capabilitiesState.data : [];

  const sourcesById = useMemo(
    () => new Map(sources.map((source) => [source.id, source])),
    [sources]
  );
  const usageProfilesBySourceId = useMemo(
    () => new Map(usageProfiles.map((profile) => [profile.source_id, profile])),
    [usageProfiles]
  );
  const modelsById = useMemo(
    () => new Map(models.map((model) => [model.id, model])),
    [models]
  );
  const capabilitiesById = useMemo(
    () =>
      new Map(capabilities.map((capability) => [capability.id, capability])),
    [capabilities]
  );

  const sourceGrantCounts = useMemo(() => {
    const counts = new Map<string, number>();

    for (const grant of accessGrants) {
      if (grant.target_type === "source" && grant.target_id) {
        counts.set(grant.target_id, (counts.get(grant.target_id) || 0) + 1);
      }
    }

    return counts;
  }, [accessGrants]);

  const filteredGrants = useMemo(() => {
    const normalizedQuery = grantQuery.trim().toLowerCase();

    return accessGrants.filter((grant) => {
      if (grantStatusFilter !== "all" && grant.status !== grantStatusFilter) {
        return false;
      }

      if (!normalizedQuery) {
        return true;
      }

      const searchable = [
        grant.id,
        grant.name,
        grant.subject_type,
        grant.subject_id,
        grant.target_type,
        grant.target_id,
        grant.external_ref,
        grant.reason
      ].filter((value): value is string => Boolean(value));

      return searchable.some((value) =>
        value.toLowerCase().includes(normalizedQuery)
      );
    });
  }, [accessGrants, grantQuery, grantStatusFilter]);

  const selectedGrant =
    filteredGrants.find((grant) => grant.id === selectedGrantId) ||
    filteredGrants[0] ||
    null;

  useEffect(() => {
    if (filteredGrants.length === 0) {
      setSelectedGrantId(null);
      return;
    }

    if (!selectedGrantId || !filteredGrants.some((grant) => grant.id === selectedGrantId)) {
      setSelectedGrantId(filteredGrants[0].id);
    }
  }, [filteredGrants, selectedGrantId]);

  useEffect(() => {
    setActionState({ status: "idle" });
    setTransitionNote("");
  }, [selectedGrantId]);

  const readinessItems = useMemo<ReadinessItem[]>(() => {
    const sourceClassificationCount = usageProfiles.filter((profile) =>
      Boolean(profile.data_classification)
    ).length;

    return [
      readinessFromArrayState(
        "access_grant_status",
        "Access Grant status",
        accessGrantsState,
        "Access Grant status metadata is available for policy checks.",
        "No Access Grants are registered yet."
      ),
      readinessFromUsageProfiles(
        "data_usage_profile_status",
        "Data Usage Profile status",
        usageProfilesState,
        sources.length
      ),
      readinessFromArrayState(
        "source_status",
        "Source status",
        sourcesState,
        "Source status metadata is available for policy checks.",
        "No Sources are registered yet."
      ),
      sourceClassificationCount > 0
        ? {
            checkType: "source_classification",
            title: "Source classification",
            tone: "ready",
            headline: `${sourceClassificationCount} profile(s) with classification`,
            detail:
              "Data classification is available through Source Data Usage Profiles."
          }
        : {
            checkType: "source_classification",
            title: "Source classification",
            tone:
              usageProfilesState.status === "loading"
                ? "loading"
                : usageProfilesState.status === "error"
                  ? "error"
                  : "missing",
            headline:
              usageProfilesState.status === "loading"
                ? "Loading profile metadata"
                : usageProfilesState.status === "error"
                  ? "Profile metadata unavailable"
                  : "No classification metadata loaded",
            detail:
              usageProfilesState.status === "error"
                ? usageProfilesState.message
                : "Classification checks need Data Usage Profiles with data_classification."
          },
      readinessFromArrayState(
        "model_asset_status",
        "Model Asset status",
        modelsState,
        "Model status metadata is available for policy checks.",
        "No Models are registered yet."
      ),
      modelsState.status === "ready" && models.length > 0
        ? {
            checkType: "model_provider_type",
            title: "Model provider type",
            tone: "ready",
            headline: `${models.length} model provider value(s)`,
            detail:
              "Provider type is derived from provider metadata as local, external, or unknown."
          }
        : {
            checkType: "model_provider_type",
            title: "Model provider type",
            tone:
              modelsState.status === "loading"
                ? "loading"
                : modelsState.status === "error"
                  ? "error"
                  : "missing",
            headline:
              modelsState.status === "loading"
                ? "Loading model metadata"
                : modelsState.status === "error"
                  ? "Model metadata unavailable"
                  : "No model provider metadata loaded",
            detail:
              modelsState.status === "error"
                ? modelsState.message
                : "Provider type checks need Model records with provider metadata."
          },
      readinessFromArrayState(
        "capability_status",
        "Capability status",
        capabilitiesState,
        "Capability status metadata is available for policy checks.",
        "No Capabilities are registered yet."
      ),
      {
        checkType: "policy_check_step_authoring",
        title: "PolicyCheckStep authoring",
        tone: "not-wired",
        headline: "Not wired yet",
        detail:
          "This page shows metadata readiness only; it does not create CheckTools or PolicyCheckSteps."
      }
    ];
  }, [
    accessGrantsState,
    capabilitiesState,
    models,
    modelsState,
    sources.length,
    sourcesState,
    usageProfiles,
    usageProfilesState
  ]);

  async function handleTransition(action: AccessGrantTransitionAction) {
    if (!selectedGrant) {
      return;
    }

    setActionState({ status: "loading", action });

    try {
      const updatedGrant = await transitionAccessGrant(
        selectedGrant.id,
        action,
        transitionNote
      );
      setAccessGrantsState((currentState) =>
        currentState.status === "ready"
          ? {
              status: "ready",
              data: currentState.data.map((grant) =>
                grant.id === updatedGrant.id ? updatedGrant : grant
              )
            }
          : currentState
      );
      setSelectedGrantId(updatedGrant.id);
      setTransitionNote("");
      setActionState({
        status: "success",
        message: `Access Grant ${formatValue(action)} submitted.`
      });
    } catch (error: unknown) {
      setActionState({ status: "error", message: transitionErrorMessage(error) });
    }
  }

  return (
    <div className="access-data-route">
      <section className="access-data-hero" aria-labelledby="access-data-title">
        <div>
          <span className="access-data-eyebrow">Governed metadata workspace</span>
          <h1 id="access-data-title">Access & Data</h1>
          <p>
            Understand the governed data, access grants, models, and capabilities that AGCP uses for metadata-only policy checks.
          </p>
        </div>
        <div className="access-data-api">
          <span>Local API</span>
          <strong>{getApiBaseUrl()}</strong>
          <button type="button" onClick={() => loadAccessData()}>
            Refresh
          </button>
        </div>
      </section>

      <section className="access-data-boundary" aria-label="Access and Data boundaries">
        <ul>
          <li>AGCP stores and evaluates governance metadata.</li>
          <li>AGCP does not inspect raw source content by default.</li>
          <li>AGCP does not certify legal compliance.</li>
        </ul>
      </section>

      <nav className="access-data-nav" aria-label="Related governance workflows">
        <Link href="/policies">Policy Studio</Link>
        <Link href="/runtime-gateway">Runtime Decisions</Link>
        <Link href="/human-approvals">Review Inbox</Link>
        <Link href="/evidence">Evidence & Audit</Link>
      </nav>

      <main className="access-data-workspace">
        <SectionShell
          id="data-sources"
          eyebrow="Declared inventory"
          title="Data Sources"
          description="Review governed Sources and the Source-side metadata used by policy context and evidence exports."
        >
          {sourcesState.status === "loading" ? (
            <StatePanel title="Loading Data Sources">
              Requesting governed Source records from GET /sources.
            </StatePanel>
          ) : null}
          {sourcesState.status === "error" ? (
            <StatePanel tone="error" title="Unable to load Data Sources">
              {sourcesState.message}
            </StatePanel>
          ) : null}
          {sourcesState.status === "ready" && sources.length === 0 ? (
            <StatePanel title="No Sources registered yet">
              AGCP has no Source inventory records to evaluate for metadata-only
              checks.
            </StatePanel>
          ) : null}
          {sourcesState.status === "ready" && sources.length > 0 ? (
            <div className="access-record-grid">
              {sources.map((source) => {
                const profile = usageProfilesBySourceId.get(source.id);

                return (
                  <article className="access-record-card" key={source.id}>
                    <header>
                      <div>
                        <span>{formatValue(source.source_type)}</span>
                        <h3>{source.name}</h3>
                      </div>
                      <StatusPill value={source.status} />
                    </header>
                    <p>{source.description || "No Source description recorded."}</p>
                    <dl className="access-field-grid">
                      <MiniField label="Risk Level" value={source.risk_level} />
                      <MiniField
                        label="Classification"
                        value={profile?.data_classification || null}
                      />
                      <MiniField
                        label="Usage Profile"
                        value={profile ? profile.review_status : "missing"}
                      />
                      <MiniField
                        label="Access Grants"
                        value={sourceGrantCounts.get(source.id) || 0}
                      />
                      <IdField label="Source ID" value={source.id} />
                      <MiniField label="Owner" value={source.owner_name} />
                    </dl>
                    <SafeMetadataPreview
                      title="Safe Source metadata"
                      metadata={source.metadata}
                    />
                  </article>
                );
              })}
            </div>
          ) : null}
        </SectionShell>

        <SectionShell
          id="data-usage-profiles"
          eyebrow="Purpose and processing constraints"
          title="Data Usage Profiles"
          description="Data Usage Profiles are governance metadata for classification, purpose, processing, review status, and evidence context."
        >
          {usageProfilesState.status === "loading" ? (
            <StatePanel title="Loading Data Usage Profiles">
              Requesting each Source Data Usage Profile from
              GET /sources/&#123;source_id&#125;/usage-profile.
            </StatePanel>
          ) : null}
          {usageProfilesState.status === "error" ? (
            <StatePanel tone="error" title="Unable to load Data Usage Profiles">
              {usageProfilesState.message}
            </StatePanel>
          ) : null}
          {usageProfilesState.status === "ready" &&
          usageProfilesState.data.profiles.length === 0 ? (
            <StatePanel title="No Data Usage Profile found">
              {sources.length === 0
                ? "No Source records are available, so no Data Usage Profiles can be loaded."
                : "Loaded Sources did not return Data Usage Profile records."}
            </StatePanel>
          ) : null}
          {usageProfilesState.status === "ready" &&
          usageProfilesState.data.erroredSourceIds.length > 0 ? (
            <StatePanel tone="warn" title="Some profiles could not load">
              {usageProfilesState.data.erroredSourceIds.length} Source profile
              request(s) returned an error. Other loaded profile metadata remains
              visible.
            </StatePanel>
          ) : null}
          {usageProfilesState.status === "ready" &&
          usageProfilesState.data.missingSourceIds.length > 0 ? (
            <StatePanel title="Missing profile records">
              {usageProfilesState.data.missingSourceIds.length} Source record(s)
              did not return a Data Usage Profile.
            </StatePanel>
          ) : null}
          {usageProfilesState.status === "ready" &&
          usageProfilesState.data.profiles.length > 0 ? (
            <div className="access-record-grid two-column">
              {usageProfilesState.data.profiles.map((profile) => {
                const source = sourcesById.get(profile.source_id);

                return (
                  <article className="access-record-card" key={profile.id}>
                    <header>
                      <div>
                        <span>{source?.name || "Source"}</span>
                        <h3>{formatValue(profile.data_classification)}</h3>
                      </div>
                      <StatusPill value={profile.review_status} />
                    </header>
                    <dl className="access-field-grid">
                      <MiniField
                        label="Personal data"
                        value={profile.contains_personal_data}
                      />
                      <MiniField
                        label="Sensitive data"
                        value={profile.contains_sensitive_data}
                      />
                      <MiniField label="DPIA required" value={profile.dpia_required} />
                      <MiniField label="Data owner" value={profile.data_owner} />
                      <MiniField
                        label="Reviewed at"
                        value={formatTimestamp(profile.reviewed_at)}
                      />
                      <MiniField
                        label="Review expires"
                        value={formatTimestamp(profile.review_expires_at)}
                      />
                    </dl>
                    <div className="access-chip-block">
                      <strong>Allowed purposes</strong>
                      <ul>
                        {chipValues(profile.allowed_purposes).map((value) => (
                          <li key={value}>{formatValue(value)}</li>
                        ))}
                      </ul>
                    </div>
                    <div className="access-chip-block danger">
                      <strong>Prohibited purposes</strong>
                      <ul>
                        {chipValues(profile.prohibited_purposes).map((value) => (
                          <li key={value}>{formatValue(value)}</li>
                        ))}
                      </ul>
                    </div>
                    <SafeMetadataPreview
                      title="Safe Data Usage Profile metadata"
                      metadata={profile.metadata}
                    />
                  </article>
                );
              })}
            </div>
          ) : null}
        </SectionShell>

        <SectionShell
          id="access-grants"
          eyebrow="Declared access"
          title="Access Grants"
          description="Access Grants are declared governance records, not IAM permissions. Transition actions update the governance record status only."
        >
          {accessGrantsState.status === "loading" ? (
            <StatePanel title="Loading Access Grants">
              Requesting declared access from GET /access-grants.
            </StatePanel>
          ) : null}
          {accessGrantsState.status === "error" ? (
            <StatePanel tone="error" title="Unable to load Access Grants">
              {accessGrantsState.message}
            </StatePanel>
          ) : null}
          {accessGrantsState.status === "ready" && accessGrants.length === 0 ? (
            <StatePanel title="No Access Grants registered yet">
              AGCP has no declared access records. Nothing is invented or inferred
              in this view.
            </StatePanel>
          ) : null}
          {accessGrantsState.status === "ready" && accessGrants.length > 0 ? (
            <div className="access-grant-review">
              <div className="access-grant-list-panel">
                <div className="access-grant-tools">
                  <label>
                    <span>Filter by status</span>
                    <select
                      value={grantStatusFilter}
                      onChange={(event) =>
                        setGrantStatusFilter(event.target.value as GrantStatusFilter)
                      }
                    >
                      {grantStatusFilters.map((status) => (
                        <option key={status} value={status}>
                          {formatValue(status)}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label>
                    <span>Search declaration</span>
                    <input
                      value={grantQuery}
                      onChange={(event) => setGrantQuery(event.target.value)}
                      placeholder="Agent, target, reason..."
                      spellCheck={false}
                    />
                  </label>
                </div>
                <div className="access-grant-list" aria-label="Access Grant declarations">
                  {filteredGrants.length === 0 ? (
                    <StatePanel title="No Access Grants match the current filters">
                      Clear the status filter or search term to review declared
                      access.
                    </StatePanel>
                  ) : (
                    filteredGrants.map((grant) => (
                      <button
                        aria-current={selectedGrant?.id === grant.id}
                        className="access-grant-row"
                        key={grant.id}
                        type="button"
                        onClick={() => setSelectedGrantId(grant.id)}
                      >
                        <span>
                          <strong>{grant.name}</strong>
                          <em>
                            {formatValue(grant.subject_type)} {shortId(grant.subject_id)}
                          </em>
                        </span>
                        <span>
                          {accessGrantTargetLabel(
                            grant,
                            sourcesById,
                            modelsById,
                            capabilitiesById
                          )}
                        </span>
                        <StatusPill value={grant.status} />
                      </button>
                    ))
                  )}
                </div>
              </div>

              <aside className="access-grant-detail" aria-label="Selected Access Grant">
                {selectedGrant ? (
                  <>
                    <header>
                      <span>Access Grant workflow</span>
                      <h3>{selectedGrant.name}</h3>
                      <p>
                        Grants describe intended Agent access and are not
                        automatically enforced by the Runtime Gateway; runtime
                        enforcement depends on policies.
                      </p>
                    </header>
                    <dl className="access-field-grid detail">
                      <MiniField label="Status" value={selectedGrant.status} />
                      <MiniField label="Grant type" value={selectedGrant.grant_type} />
                      <MiniField label="Target type" value={selectedGrant.target_type} />
                      <MiniField label="Risk Level" value={selectedGrant.risk_level} />
                      <IdField label="Subject ID" value={selectedGrant.subject_id} />
                      <IdField
                        label="Target"
                        value={accessGrantTargetKey(selectedGrant)}
                      />
                      <MiniField
                        label="Granted by"
                        value={`${selectedGrant.granted_by_actor_type}:${selectedGrant.granted_by_actor_id}`}
                      />
                      <MiniField
                        label="Expires"
                        value={formatTimestamp(selectedGrant.expires_at)}
                      />
                    </dl>
                    <p className="access-detail-copy">
                      {selectedGrant.reason || "No governance reason recorded."}
                    </p>
                    <div className="access-reference-links">
                      <Link href={`/agents/${selectedGrant.subject_id}`}>
                        Agent Governance Profile
                      </Link>
                      <Link href="/evidence">Evidence Bundle lookup</Link>
                      {selectedGrant.target_type === "source" ? (
                        <a href="#data-usage-profiles">Source/Data Usage workflow</a>
                      ) : null}
                    </div>
                    <SafeMetadataPreview
                      title="Safe Metadata"
                      metadata={selectedGrant.metadata}
                    />
                    <section className="access-transition-box">
                      <strong>Access Grant transition actions</strong>
                      <label>
                        <span>Transition note</span>
                        <input
                          value={transitionNote}
                          onChange={(event) => setTransitionNote(event.target.value)}
                          placeholder="Optional governance note"
                        />
                      </label>
                      <div>
                        {transitionActionsForStatus(selectedGrant.status).length === 0 ? (
                          <p>Terminal governance status. No transition action is available.</p>
                        ) : (
                          transitionActionsForStatus(selectedGrant.status).map(
                            (action) => (
                              <button
                                className={`access-transition ${action}`}
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
                            )
                          )
                        )}
                      </div>
                      <p>
                        Updates the governance record status only; this does not
                        by itself guarantee runtime blocking.
                      </p>
                      {actionState.status === "success" ? (
                        <p className="access-action-message success">
                          {actionState.message}
                        </p>
                      ) : null}
                      {actionState.status === "error" ? (
                        <p className="access-action-message error">
                          {actionState.message}
                        </p>
                      ) : null}
                    </section>
                  </>
                ) : (
                  <StatePanel title="No Access Grant selected">
                    Select a declaration to inspect status, target context, and
                    lifecycle actions.
                  </StatePanel>
                )}
              </aside>
            </div>
          ) : null}
        </SectionShell>

        <SectionShell
          id="models"
          eyebrow="Governed model inventory"
          title="Models"
          description="Review ModelAsset metadata used by model status and provider-type policy checks."
        >
          {modelsState.status === "loading" ? (
            <StatePanel title="Loading Models">
              Requesting governed ModelAsset records from GET /models.
            </StatePanel>
          ) : null}
          {modelsState.status === "error" ? (
            <StatePanel tone="error" title="Unable to load Models">
              {modelsState.message}
            </StatePanel>
          ) : null}
          {modelsState.status === "ready" && models.length === 0 ? (
            <StatePanel title="No Models registered yet">
              Model provider and status checks have no ModelAsset metadata to
              evaluate.
            </StatePanel>
          ) : null}
          {modelsState.status === "ready" && models.length > 0 ? (
            <div className="access-record-grid">
              {models.map((model) => (
                <article className="access-record-card" key={model.id}>
                  <header>
                    <div>
                      <span>{formatValue(model.model_type)}</span>
                      <h3>{model.name}</h3>
                    </div>
                    <StatusPill value={model.status} />
                  </header>
                  <p>{model.description || "No Model description recorded."}</p>
                  <dl className="access-field-grid">
                    <MiniField label="Provider" value={model.provider} />
                    <MiniField
                      label="Provider type"
                      value={providerType(model.provider)}
                    />
                    <MiniField label="Risk Level" value={model.risk_level} />
                    <MiniField label="Owner" value={model.owner_name} />
                    <MiniField label="Version" value={model.version} />
                    <IdField label="Model ID" value={model.id} />
                  </dl>
                  <SafeMetadataPreview
                    title="Safe Model metadata"
                    metadata={model.metadata}
                  />
                </article>
              ))}
            </div>
          ) : null}
        </SectionShell>

        <SectionShell
          id="capabilities"
          eyebrow="Governed action surface"
          title="Capabilities"
          description="Review governed tools, APIs, integrations, and workflow actions declared as Capability metadata."
        >
          {capabilitiesState.status === "loading" ? (
            <StatePanel title="Loading Capabilities">
              Requesting Capability records from GET /capabilities.
            </StatePanel>
          ) : null}
          {capabilitiesState.status === "error" ? (
            <StatePanel tone="error" title="Unable to load Capabilities">
              {capabilitiesState.message}
            </StatePanel>
          ) : null}
          {capabilitiesState.status === "ready" && capabilities.length === 0 ? (
            <StatePanel title="No Capabilities registered yet">
              Capability status checks have no governed action metadata to
              evaluate.
            </StatePanel>
          ) : null}
          {capabilitiesState.status === "ready" && capabilities.length > 0 ? (
            <div className="access-record-grid">
              {capabilities.map((capability) => (
                <article className="access-record-card" key={capability.id}>
                  <header>
                    <div>
                      <span>{formatValue(capability.capability_type)}</span>
                      <h3>{capability.name}</h3>
                    </div>
                    <StatusPill value={capability.status} />
                  </header>
                  <p>{capability.description || "No Capability description recorded."}</p>
                  <dl className="access-field-grid">
                    <MiniField label="Risk Level" value={capability.risk_level} />
                    <MiniField label="External ref" value={capability.external_ref} />
                    <IdField label="Capability ID" value={capability.id} />
                  </dl>
                  <SafeMetadataPreview
                    title="Safe Capability metadata"
                    metadata={capability.metadata}
                  />
                </article>
              ))}
            </div>
          ) : null}
        </SectionShell>

        <SectionShell
          id="metadata-check-readiness"
          eyebrow="Policy pre-check inputs"
          title="Metadata Check Readiness"
          description="This panel shows whether backend metadata exists for metadata-only checks. It does not execute a runtime decision or produce a score."
        >
          <div className="access-readiness-grid">
            {readinessItems.map((item) => (
              <article className={`access-readiness-card ${item.tone}`} key={item.checkType}>
                <span>{item.checkType}</span>
                <h3>{item.title}</h3>
                <strong>{item.headline}</strong>
                <p>{item.detail}</p>
              </article>
            ))}
          </div>
        </SectionShell>

        <section className="access-demo-callout" aria-labelledby="access-demo-title">
          <div>
            <span className="access-data-eyebrow">Local metadata pre-check</span>
            <h2 id="access-demo-title">Run the metadata pre-check demo</h2>
            <p>
              The local demo creates real local metadata, calls the Runtime
              Gateway, persists CheckResults, and shows the resulting evidence in
              Runtime Decisions, Review Inbox, and Evidence & Audit. It is
              local/demo-only with no fake production simulation.
            </p>
          </div>
          <code>.\scripts\dev-demo.ps1</code>
        </section>
      </main>
    </div>
  );
}

function readinessFromArrayState<T>(
  checkType: string,
  title: string,
  state: LoadState<T[]>,
  readyDetail: string,
  emptyDetail: string
): ReadinessItem {
  if (state.status === "loading") {
    return {
      checkType,
      title,
      tone: "loading",
      headline: "Loading metadata",
      detail: "AGCP is requesting the supporting backend records."
    };
  }

  if (state.status === "error") {
    return {
      checkType,
      title,
      tone: "error",
      headline: "API unavailable",
      detail: state.message
    };
  }

  if (state.data.length === 0) {
    return {
      checkType,
      title,
      tone: "missing",
      headline: "Missing metadata",
      detail: emptyDetail
    };
  }

  return {
    checkType,
    title,
    tone: "ready",
    headline: `${state.data.length} record(s) available`,
    detail: readyDetail
  };
}

function readinessFromUsageProfiles(
  checkType: string,
  title: string,
  state: LoadState<UsageProfilesPayload>,
  sourceCount: number
): ReadinessItem {
  if (state.status === "loading") {
    return {
      checkType,
      title,
      tone: "loading",
      headline: "Loading profile metadata",
      detail: "AGCP is requesting Source Data Usage Profiles."
    };
  }

  if (state.status === "error") {
    return {
      checkType,
      title,
      tone: "error",
      headline: "API unavailable",
      detail: state.message
    };
  }

  if (sourceCount === 0) {
    return {
      checkType,
      title,
      tone: "missing",
      headline: "No Sources registered",
      detail: "Data Usage Profile checks need Source inventory records first."
    };
  }

  if (state.data.profiles.length === 0) {
    return {
      checkType,
      title,
      tone: "missing",
      headline: "No profile metadata loaded",
      detail: "Loaded Sources did not return Data Usage Profile records."
    };
  }

  return {
    checkType,
    title,
    tone: "ready",
    headline: `${state.data.profiles.length} profile(s) available`,
    detail:
      "Data Usage Profile review status metadata is available for policy checks."
  };
}
