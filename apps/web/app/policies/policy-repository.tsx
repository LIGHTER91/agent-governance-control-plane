"use client";

import { useState, type FormEvent } from "react";
import type {
  PolicyFolderRecord,
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

type PolicyFoldersState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; folders: PolicyFolderRecord[] };

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

type PolicyFolderGroup = {
  folder: PolicyFolderRecord | null;
  id: string;
  label: string;
  policies: PolicyRecord[];
};

export function PolicyRepository({
  mode,
  onModeChange,
  onCreateFolder,
  onDeleteFolder,
  onMovePolicyToFolder,
  onNewPolicy,
  onOpenTemplates,
  onRenameFolder,
  onRefresh,
  onSelectPolicy,
  onSelectRule,
  onUseTemplate,
  policiesState,
  policyFoldersState,
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
  onCreateFolder: (name: string) => void;
  onDeleteFolder: (folder: PolicyFolderRecord) => void;
  onMovePolicyToFolder: (policy: PolicyRecord, folderId: string | null) => void;
  onNewPolicy: () => void;
  onOpenTemplates: () => void;
  onRenameFolder: (folder: PolicyFolderRecord, name: string) => void;
  onRefresh: () => void;
  onSelectPolicy: (policy: PolicyRecord) => void;
  onSelectRule: (rule: PolicyRuleRecord) => void;
  onUseTemplate: (template: PolicyTemplate) => void;
  policiesState: PoliciesState;
  policyFoldersState: PolicyFoldersState;
  policyVersionsState: PolicyVersionsState;
  query: string;
  rulesState: RulesState;
  selectedDraftVersion: PolicyVersionRecord | null;
  selectedPolicyId: string | null;
  selectedRuleId: string | null;
  setQuery: (query: string) => void;
}) {
  const normalizedQuery = query.trim().toLowerCase();
  const [isCreatingFolder, setIsCreatingFolder] = useState(false);
  const [newFolderDraft, setNewFolderDraft] = useState("");

  function submitNewFolder(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const normalizedName = newFolderDraft.trim();
    if (!normalizedName) {
      return;
    }
    onCreateFolder(normalizedName);
    setNewFolderDraft("");
    setIsCreatingFolder(false);
  }

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
            <small>Policies and folders load from the AGCP backend.</small>
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
            title="Repository filters are not available in V1."
            type="button"
            aria-label="Repository filters are not available in V1"
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
        {isCreatingFolder ? (
          <form className="ps2-folder-inline-form" onSubmit={submitNewFolder}>
            <input
              aria-label="New policy folder name"
              autoFocus
              onChange={(event) => setNewFolderDraft(event.target.value)}
              placeholder="Folder name"
              value={newFolderDraft}
            />
            <button disabled={!newFolderDraft.trim()} type="submit">
              Create folder
            </button>
            <button
              onClick={() => {
                setIsCreatingFolder(false);
                setNewFolderDraft("");
              }}
              type="button"
            >
              Cancel
            </button>
          </form>
        ) : (
          <button
            className="ps2-folder-action"
            onClick={() => setIsCreatingFolder(true)}
            type="button"
          >
            <PolicyIcon name="folder" size={13} />
            New folder
          </button>
        )}
      </div>

      <div className="ps2-list-scroll">
        {mode === "policies" ? (
          <PolicyList
            normalizedQuery={normalizedQuery}
            onDeleteFolder={onDeleteFolder}
            onMovePolicyToFolder={onMovePolicyToFolder}
            onRenameFolder={onRenameFolder}
            onSelectPolicy={onSelectPolicy}
            onSelectRule={onSelectRule}
            policyFoldersState={policyFoldersState}
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
  onDeleteFolder,
  onMovePolicyToFolder,
  onRenameFolder,
  onSelectPolicy,
  onSelectRule,
  policyFoldersState,
  policiesState,
  rulesState,
  selectedPolicyId,
  selectedRuleId
}: {
  normalizedQuery: string;
  onDeleteFolder: (folder: PolicyFolderRecord) => void;
  onMovePolicyToFolder: (policy: PolicyRecord, folderId: string | null) => void;
  onRenameFolder: (folder: PolicyFolderRecord, name: string) => void;
  onSelectPolicy: (policy: PolicyRecord) => void;
  onSelectRule: (rule: PolicyRuleRecord) => void;
  policyFoldersState: PolicyFoldersState;
  policiesState: PoliciesState;
  rulesState: RulesState;
  selectedPolicyId: string | null;
  selectedRuleId: string | null;
}) {
  const [editingFolderId, setEditingFolderId] = useState<string | null>(null);
  const [folderNameDraft, setFolderNameDraft] = useState("");
  const [deleteFolderId, setDeleteFolderId] = useState<string | null>(null);

  if (policiesState.status === "loading") {
    return (
      <div className="ps2-repo-state compact">
        <strong>Loading Policy repository</strong>
        <span>Loading persisted policies from the AGCP backend.</span>
      </div>
    );
  }

  if (policiesState.status === "error") {
    return (
      <div className="ps2-repo-state compact error" role="alert">
        <strong>Policy repository unavailable</strong>
        <span>{policiesState.message}</span>
        <small>Policies load from the AGCP backend. No fallback policies are shown.</small>
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
            ? "The AGCP backend returned an empty policy repository."
            : "No persisted policies match this search."}
        </span>
      </div>
    );
  }

  const grouped = groupPoliciesByFolder(filtered, policyFoldersState);
  const folders =
    policyFoldersState.status === "ready" ? policyFoldersState.folders : [];

  return (
    <>
      {policyFoldersState.status === "loading" ? (
        <div className="ps2-repo-state compact">
          <span>Loading policy folder labels from the backend.</span>
        </div>
      ) : null}
      {policyFoldersState.status === "error" ? (
        <div className="ps2-repo-state compact error" role="alert">
          <span>{policyFoldersState.message}</span>
          <small>Folder moves are disabled until folder labels load.</small>
        </div>
      ) : null}
      {grouped.map((group) => (
        <details
          className={`ps2-policy-folder ${
            group.policies.some((policy) => policy.id === selectedPolicyId)
              ? "has-selected"
              : ""
          }`}
          data-folder-id={group.id}
          data-folder-name={group.label}
          key={group.id}
          open
        >
          <summary className="ps2-folder-row">
            <PolicyIcon name="folder" size={14} />
            <span>{group.label}</span>
            <small>
              {group.policies.length}{" "}
              {group.policies.length === 1 ? "policy" : "policies"}
            </small>
          </summary>
          {group.folder ? (
            <div
              className="ps2-folder-actions"
              aria-label={`Folder actions for ${group.label}`}
            >
              <button
                onClick={() => {
                  setEditingFolderId(group.folder?.id || null);
                  setFolderNameDraft(group.folder?.name || "");
                  setDeleteFolderId(null);
                }}
                title={`Rename ${group.label}`}
                type="button"
              >
                <PolicyIcon name="edit" size={12} />
                Rename folder
              </button>
              <button
                className="danger"
                disabled={group.policies.length > 0}
                onClick={() => {
                  setDeleteFolderId(group.folder?.id || null);
                  setEditingFolderId(null);
                }}
                title={
                  group.policies.length > 0
                    ? "Move policies out of this folder before deleting it."
                    : `Delete empty folder ${group.label}`
                }
                type="button"
              >
                <PolicyIcon name="trash" size={12} />
                Delete empty folder
              </button>
            </div>
          ) : null}
          {group.folder && editingFolderId === group.folder.id ? (
            <form
              className="ps2-folder-inline-form nested"
              onSubmit={(event) => {
                event.preventDefault();
                const normalizedName = folderNameDraft.trim();
                if (!normalizedName) {
                  return;
                }
                onRenameFolder(group.folder as PolicyFolderRecord, normalizedName);
                setEditingFolderId(null);
                setFolderNameDraft("");
              }}
            >
              <input
                aria-label={`Rename ${group.label} folder`}
                autoFocus
                onChange={(event) => setFolderNameDraft(event.target.value)}
                value={folderNameDraft}
              />
              <button disabled={!folderNameDraft.trim()} type="submit">
                Save
              </button>
              <button
                onClick={() => {
                  setEditingFolderId(null);
                  setFolderNameDraft("");
                }}
                type="button"
              >
                Cancel
              </button>
            </form>
          ) : null}
          {group.folder && deleteFolderId === group.folder.id ? (
            <div className="ps2-folder-confirm">
              <span>Delete empty folder?</span>
              <button
                onClick={() => {
                  onDeleteFolder(group.folder as PolicyFolderRecord);
                  setDeleteFolderId(null);
                }}
                type="button"
              >
                Confirm delete
              </button>
              <button onClick={() => setDeleteFolderId(null)} type="button">
                Cancel
              </button>
            </div>
          ) : null}
          {group.policies.length === 0 ? (
            <div className="ps2-repo-state compact">
              <span>No policies in this folder.</span>
            </div>
          ) : null}
          {group.policies.map((policy) => (
            <div className="ps2-policy-entry-row" key={policy.id}>
              <button
                className={`ps2-entry ${policy.id === selectedPolicyId ? "active" : ""}`}
                onClick={() => onSelectPolicy(policy)}
                type="button"
              >
                <span
                  className="ps2-entry-dot"
                  style={{ color: statusColor(policy.status) }}
                >
                  <PolicyIcon name="policy" size={13} />
                </span>
                <span className="ps2-entry-body">
                  <span className="ps2-entry-name">{policyFileName(policy)}</span>
                  <span
                    className="ps2-entry-meta"
                    title={`Policy reference: ${policy.id}`}
                  >
                    {policy.description || `Updated ${formatVersionTimestamp(policy.updated_at)}`} / ref{" "}
                    {shortReference(policy.id)}
                  </span>
                </span>
                <span className={`ps2-entry-chip chip ${statusChip(policy.status)}`}>
                  {policy.status}
                </span>
              </button>
              <label className="ps2-folder-move">
                <span>Folder</span>
                <select
                  aria-label={`Move ${policy.name} to policy folder`}
                  disabled={policyFoldersState.status !== "ready"}
                  onChange={(event) =>
                    onMovePolicyToFolder(
                      policy,
                      event.target.value ? event.target.value : null
                    )
                  }
                  value={policy.folder_id || ""}
                >
                  <option value="">Uncategorized</option>
                  {folders.map((folder) => (
                    <option key={folder.id} value={folder.id}>
                      {folder.name}
                    </option>
                  ))}
                </select>
              </label>
            </div>
          ))}
        </details>
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
          <span>No saved versions</span>
          <strong>Draft not saved</strong>
        </div>
      ) : null}
      {policyVersionsState.status === "ready" && versions.length === 0 ? (
        <div className="ps2-version-row active">
          <span>No saved PolicyVersions</span>
          <strong>Repository returned none</strong>
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
        <span>Select a policy to inspect its saved rules.</span>
      </div>
    );
  }

  if (rulesState.status === "loading") {
    return (
      <div className="ps2-repo-state compact">
        <span>Loading saved PolicyRules...</span>
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
        <span>No saved PolicyRules yet. Save draft creates a draft PolicyVersion snapshot.</span>
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
            <span
              className="ps2-entry-meta"
              title={`PolicyRule reference: ${rule.id}`}
            >
              {rule.description || "Saved rule source"} / ref {shortReference(rule.id)}
            </span>
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

function groupPoliciesByFolder(
  policies: PolicyRecord[],
  policyFoldersState: PolicyFoldersState
): PolicyFolderGroup[] {
  const folders =
    policyFoldersState.status === "ready" ? policyFoldersState.folders : [];
  const knownFolderIds = new Set(folders.map((folder) => folder.id));
  const groups: PolicyFolderGroup[] = folders.map((folder) => ({
    id: folder.id,
    label: folder.name,
    folder,
    policies: policies.filter((policy) => policy.folder_id === folder.id)
  }));
  const uncategorized = policies.filter((policy) => !policy.folder_id);
  groups.push({
    id: "uncategorized",
    label: "Uncategorized",
    folder: null,
    policies: uncategorized
  });

  const unavailable =
    policyFoldersState.status === "ready"
      ? policies.filter(
          (policy) => policy.folder_id && !knownFolderIds.has(policy.folder_id)
        )
      : policies.filter((policy) => policy.folder_id);
  if (unavailable.length > 0) {
    groups.push({
      id:
        policyFoldersState.status === "ready"
          ? "folder-unavailable"
          : "folder-labels-loading",
      label:
        policyFoldersState.status === "ready"
          ? "Folder unavailable"
          : "Folder labels loading",
      folder: null,
      policies: unavailable
    });
  }

  return groups.filter((group) => group.policies.length > 0 || group.id !== "uncategorized");
}

function shortReference(value: string) {
  if (value.length <= 12) {
    return value;
  }
  return `${value.slice(0, 8)}...${value.slice(-4)}`;
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
