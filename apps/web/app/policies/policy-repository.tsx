"use client";

import { PolicyRecord } from "../lib/policies";
import { PolicyRuleRecord } from "../lib/policies";
import { POLICY_TEMPLATES, PolicyTemplate, policyFileName } from "./policy-dsl";

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

export function PolicyRepository({
  mode,
  onModeChange,
  onNewPolicy,
  onOpenTemplates,
  onSelectPolicy,
  onSelectRule,
  onUseTemplate,
  policiesState,
  query,
  rulesState,
  selectedPolicyId,
  selectedRuleId,
  setQuery
}: {
  mode: RepositoryMode;
  onModeChange: (mode: RepositoryMode) => void;
  onNewPolicy: () => void;
  onOpenTemplates: () => void;
  onSelectPolicy: (policy: PolicyRecord) => void;
  onSelectRule: (rule: PolicyRuleRecord) => void;
  onUseTemplate: (template: PolicyTemplate) => void;
  policiesState: PoliciesState;
  query: string;
  rulesState: RulesState;
  selectedPolicyId: string | null;
  selectedRuleId: string | null;
  setQuery: (query: string) => void;
}) {
  const normalizedQuery = query.trim().toLowerCase();

  return (
    <aside className="ps2-list-pane" aria-label="Policy repository">
      <div className="ps2-pane-head">
        <div className="ps2-pane-title">Policy Studio</div>
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
        <label className="ps2-search">
          <span aria-hidden="true">⌕</span>
          <input
            onChange={(event) => setQuery(event.target.value)}
            placeholder={
              mode === "templates" ? "Search templates..." : "Search policies..."
            }
            type="search"
            value={query}
          />
        </label>
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

      <button className="ps2-new-btn" onClick={onNewPolicy} type="button">
        <span aria-hidden="true">+</span>
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
      <div className="ps2-repo-state">
        <strong>Loading policies</strong>
        <span>GET /policies</span>
      </div>
    );
  }

  if (policiesState.status === "error") {
    return (
      <div className="ps2-repo-state error" role="alert">
        <strong>Unable to load policies</strong>
        <span>{policiesState.message}</span>
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
      <div className="ps2-repo-state">
        <strong>No policies found</strong>
        <span>
          {policiesState.policies.length === 0
            ? "The backend returned an empty Policy repository."
            : "No backend Policy records match this search."}
        </span>
      </div>
    );
  }

  return (
    <>
      <div className="ps2-section-lbl">// Backend policies</div>
      {filtered.map((policy) => (
        <button
          className={`ps2-entry ${policy.id === selectedPolicyId ? "active" : ""}`}
          key={policy.id}
          onClick={() => onSelectPolicy(policy)}
          type="button"
        >
          <span
            className="ps2-entry-dot"
            style={{ background: statusColor(policy.status) }}
          />
          <span className="ps2-entry-body">
            <span className="ps2-entry-name">{policyFileName(policy)}</span>
            <span className="ps2-entry-meta">{policy.id}</span>
          </span>
          <span className={`ps2-entry-chip chip ${statusChip(policy.status)}`}>
            {policy.status}
          </span>
        </button>
      ))}
      <div className="ps2-section-lbl">// PolicyRules</div>
      <PolicyRuleList
        onSelectRule={onSelectRule}
        rulesState={rulesState}
        selectedRuleId={selectedRuleId}
      />
    </>
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
          <span className="ps2-entry-dot ps2-rule-dot" />
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
      <div className="ps2-section-lbl">// Built-in templates</div>
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
