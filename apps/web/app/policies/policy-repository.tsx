"use client";

import type {
  PolicyRecord,
  PolicyRuleRecord,
  PolicyVersionRecord
} from "../lib/policies";
import { POLICY_TEMPLATES, PolicyTemplate, policyFileName } from "./policy-dsl";
import { PolicyIcon } from "./policy-icons";

type PoliciesState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; policies: PolicyRecord[] };

type RepositoryMode = "policies" | "templates";

type RulesState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; rules: PolicyRuleRecord[] };

type PolicyVersionsState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; versions: PolicyVersionRecord[] };

export function PolicyRepository({
  mode,
  onModeChange,
  onNewPolicy,
  onOpenTemplates,
  onRefresh,
  onSelectPolicy,
  onSelectRule,
  onUseTemplate,
  policiesState,
  policyVersionsState,
  query,
  rulesState,
  selectedDraftVersion,
  selectedPolicyId,
  selectedRuleId,
  setQuery
}: {
  mode: RepositoryMode;
  onModeChange: (mode: RepositoryMode) => void;
  onNewPolicy: () => void;
  onOpenTemplates: () => void;
  onRefresh: () => void;
  onSelectPolicy: (policy: PolicyRecord) => void;
  onSelectRule: (rule: PolicyRuleRecord) => void;
  onUseTemplate: (template: PolicyTemplate) => void;
  policiesState: PoliciesState;
  policyVersionsState: PolicyVersionsState;
  query: string;
  rulesState: RulesState;
  selectedDraftVersion: PolicyVersionRecord | null;
  selectedPolicyId: string | null;
  selectedRuleId: string | null;
  setQuery: (query: string) => void;
}) {
  const normalizedQuery = query.trim().toLowerCase();

  return (
    <aside className="ps2-list-pane" aria-label="Policy repository">
      <div className="ps2-pane-head">
        <div className="ps2-repo-brand">
          <span className="ps2-repo-mark" aria-hidden="true">
            <PolicyIcon name="sparkle" size={17} />
          </span>
          <span>AGCP Studio</span>
        </div>
        <div className="ps2-repo-label">Policy repository</div>
        <div className="ps2-repo-select">
          <PolicyIcon name="repository" size={15} />
          <span>
            <strong>Local backend</strong>
            <small>Policies are loaded from the AGCP API.</small>
          </span>
          <PolicyIcon name="chevronDown" size={14} />
        </div>
        <div className="ps2-mode-row">
          <button
            className={`ps2-mode-btn ${mode === "policies" ? "p-on" : ""}`}
            onClick={() => onModeChange("policies")}
            type="button"
          >
            Policies
          </button>
          <button
            className={`ps2-mode-btn ${mode === "templates" ? "t-on" : ""}`}
            onClick={() => onModeChange("templates")}
            type="button"
          >
            Templates
          </button>
        </div>
        <div className="ps2-repo-search-row">
          <label className="ps2-search">
            <PolicyIcon name="search" size={14} />
            <input
              onChange={(event) => setQuery(event.target.value)}
              placeholder={
                mode === "templates" ? "Search templates..." : "Search policies"
              }
              type="search"
              value={query}
            />
          </label>
          <button
            disabled
            title="Backend filters are not configured yet."
            type="button"
            aria-label="Backend filters not configured"
          >
            <PolicyIcon name="filter" size={14} />
          </button>
          <button onClick={onRefresh} type="button" aria-label="Refresh policies">
            <PolicyIcon name="refresh" size={14} />
          </button>
          <button onClick={onNewPolicy} type="button" aria-label="New policy">
            <PolicyIcon name="plus" size={14} />
          </button>
        </div>
      </div>

      <div className="ps2-list-scroll">
        {mode === "policies" ? (
          <PolicyList
            normalizedQuery={normalizedQuery}
            onSelectPolicy={onSelectPolicy}
            onSelectRule={onSelectRule}
            policiesState={policiesState}
            rulesState={rulesState}
            selectedPolicyId={selectedPolicyId}
            selectedRuleId={selectedRuleId}
          />
        ) : (
          <TemplateList
            normalizedQuery={normalizedQuery}
            onOpenTemplates={onOpenTemplates}
            onUseTemplate={onUseTemplate}
          />
        )}
      </div>

      <PolicyVersionPanel
        policyVersionsState={policyVersionsState}
        selectedDraftVersion={selectedDraftVersion}
      />

      <button className="ps2-new-btn" onClick={onNewPolicy} type="button">
        <PolicyIcon name="plus" size={14} />
        New policy
      </button>
    </aside>
  );
}

function PolicyList({
  normalizedQuery,
  onSelectPolicy,
  onSelectRule,
  policiesState,
  rulesState,
  selectedPolicyId,
  selectedRuleId
}: {
  normalizedQuery: string;
  onSelectPolicy: (policy: PolicyRecord) => void;
  onSelectRule: (rule: PolicyRuleRecord) => void;
  policiesState: PoliciesState;
  rulesState: RulesState;
  selectedPolicyId: string | null;
  selectedRuleId: string | null;
}) {
  if (policiesState.status === "loading") {
    return (
      <div className="ps2-repo-state compact">
        <strong>Loading Policy repository</strong>
        <span>GET /policies from the AGCP API is in progress.</span>
      </div>
    );
  }

  if (policiesState.status === "error") {
    return (
      <div className="ps2-repo-state compact error" role="alert">
        <strong>Backend unavailable</strong>
        <span>{policiesState.message}</span>
        <small>Policies are loaded from the AGCP API. No fallback policies are shown.</small>
      </div>
    );
  }

  const filtered = policiesState.policies.filter((policy) =>
    `${policy.name} ${policy.status} ${policy.id}`
      .toLowerCase()
      .includes(normalizedQuery)
  );

  if (filtered.length === 0) {
    return (
      <div className="ps2-repo-state compact">
        <strong>No backend policies</strong>
        <span>
          {policiesState.policies.length === 0
            ? "The AGCP API returned an empty Policy repository."
            : "No backend Policy records match this search."}
        </span>
      </div>
    );
  }

  const grouped = groupPoliciesByDomain(filtered);

  return (
    <>
      {grouped.map((group) => (
        <section className="ps2-policy-folder" key={group.label}>
          <div className="ps2-folder-row">
            <PolicyIcon name="folder" size={14} />
            <span>{group.label}</span>
          </div>
          {group.policies.map((policy) => (
            <button
              className={`ps2-entry ${policy.id === selectedPolicyId ? "active" : ""}`}
              key={policy.id}
              onClick={() => onSelectPolicy(policy)}
              type="button"
            >
              <span className="ps2-entry-dot" style={{ color: statusColor(policy.status) }}>
                <PolicyIcon name="policy" size={13} />
              </span>
              <span className="ps2-entry-body">
                <span className="ps2-entry-name">{policyFileName(policy)}</span>
                <span className="ps2-entry-meta">{policy.id}</span>
              </span>
              <span className={`ps2-entry-chip chip ${statusChip(policy.status)}`}>
                {policy.status}
              </span>
            </button>
          ))}
        </section>
      ))}
      <div className="ps2-section-lbl">Policy rules</div>
      <PolicyRuleList
        onSelectRule={onSelectRule}
        rulesState={rulesState}
        selectedRuleId={selectedRuleId}
      />
    </>
  );
}

function PolicyVersionPanel({
  policyVersionsState,
  selectedDraftVersion
}: {
  policyVersionsState: PolicyVersionsState;
  selectedDraftVersion: PolicyVersionRecord | null;
}) {
  const versions =
    policyVersionsState.status === "ready"
      ? [...policyVersionsState.versions].sort(
          (left, right) => right.version_number - left.version_number
        )
      : [];

  return (
    <div className="ps2-version-panel">
      <div className="ps2-section-lbl">Policy versions</div>
      {policyVersionsState.status === "loading" ? (
        <div className="ps2-version-row">
          <span>Loading versions</span>
          <strong>backend</strong>
        </div>
      ) : null}
      {policyVersionsState.status === "error" ? (
        <div className="ps2-version-row">
          <span>Unable to load versions</span>
          <strong>error</strong>
        </div>
      ) : null}
      {policyVersionsState.status === "idle" ? (
        <div className="ps2-version-row active">
          <span>No backend versions</span>
          <strong>Draft not saved</strong>
        </div>
      ) : null}
      {policyVersionsState.status === "ready" && versions.length === 0 ? (
        <div className="ps2-version-row active">
          <span>No PolicyVersions</span>
          <strong>Backend returned none</strong>
        </div>
      ) : null}
      {versions.map((version) => (
        <div
          className={`ps2-version-row ${
            selectedDraftVersion?.id === version.id ? "active" : ""
          }`}
          key={version.id}
        >
          <span>v{version.version_number}</span>
          <strong>{version.status.replace(/_/g, " ")}</strong>
          <small>{formatVersionTimestamp(version.updated_at)}</small>
        </div>
      ))}
    </div>
  );
}

function PolicyRuleList({
  onSelectRule,
  rulesState,
  selectedRuleId
}: {
  onSelectRule: (rule: PolicyRuleRecord) => void;
  rulesState: RulesState;
  selectedRuleId: string | null;
}) {
  if (rulesState.status === "idle") {
    return (
      <div className="ps2-repo-state compact">
        <span>Select a Policy to load GET /policies/{"{policy_id}"}/rules.</span>
      </div>
    );
  }

  if (rulesState.status === "loading") {
    return (
      <div className="ps2-repo-state compact">
        <span>Loading PolicyRules...</span>
      </div>
    );
  }

  if (rulesState.status === "error") {
    return (
      <div className="ps2-repo-state compact error">
        <span>{rulesState.message}</span>
      </div>
    );
  }

  if (rulesState.rules.length === 0) {
    return (
      <div className="ps2-repo-state compact">
        <span>No PolicyRules yet. Save draft creates a draft PolicyVersion snapshot.</span>
      </div>
    );
  }

  return (
    <>
      {rulesState.rules.map((rule) => (
        <button
          className={`ps2-entry ps2-rule-entry ${
            rule.id === selectedRuleId ? "active" : ""
          }`}
          key={rule.id}
          onClick={() => onSelectRule(rule)}
          type="button"
        >
          <span className="ps2-entry-dot ps2-rule-dot">
            <PolicyIcon name="code" size={13} />
          </span>
          <span className="ps2-entry-body">
            <span className="ps2-entry-name">
              {rule.name || "policy_rule"}.rule.agcp
            </span>
            <span className="ps2-entry-meta">{rule.id}</span>
          </span>
          <span className="ps2-entry-chip chip chip-review">rule</span>
        </button>
      ))}
    </>
  );
}

function TemplateList({
  normalizedQuery,
  onOpenTemplates,
  onUseTemplate
}: {
  normalizedQuery: string;
  onOpenTemplates: () => void;
  onUseTemplate: (template: PolicyTemplate) => void;
}) {
  const filtered = POLICY_TEMPLATES.filter((template) =>
    `${template.name} ${template.description} ${template.tags.join(" ")}`
      .toLowerCase()
      .includes(normalizedQuery)
  );

  return (
    <>
      <div className="ps2-section-lbl">Built-in templates</div>
      {filtered.map((template) => (
        <div className="ps2-entry ps2-template-entry" key={template.id}>
          <span className="ps2-entry-dot ps2-template-dot" />
          <span className="ps2-entry-body">
            <span className="ps2-entry-name">{template.name}</span>
            <span className="ps2-entry-meta">{template.tags.join(" / ")}</span>
          </span>
          <button
            className="ps2-entry-chip chip chip-draft ps2-use-template"
            onClick={() => onUseTemplate(template)}
            type="button"
          >
            Use
          </button>
        </div>
      ))}
      <button
        className="ps2-drawer-link"
        onClick={onOpenTemplates}
        type="button"
      >
        Open templates drawer
      </button>
    </>
  );
}

function groupPoliciesByDomain(policies: PolicyRecord[]) {
  return [{ label: "Backend Policy records", policies }];
}

function statusChip(status: PolicyRecord["status"]) {
  if (status === "active") {
    return "chip-active";
  }
  if (status === "draft") {
    return "chip-draft";
  }
  if (status === "disabled") {
    return "chip-review";
  }
  return "chip-unsaved";
}

function statusColor(status: PolicyRecord["status"]) {
  if (status === "active") {
    return "var(--green)";
  }
  if (status === "draft") {
    return "var(--orange)";
  }
  if (status === "disabled") {
    return "var(--sky)";
  }
  return "var(--text-muted)";
}

function formatVersionTimestamp(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "No timestamp";
  }
  return date.toLocaleDateString(undefined, {
    day: "2-digit",
    month: "short",
    year: "numeric"
  });
}
