"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { ApiRequestError } from "../lib/api";
import {
  PolicyPayload,
  PolicyRecord,
  PolicyRuleRecord,
  PolicyVersionDraftPayload,
  PolicyVersionReviewRequestRecord,
  PolicyVersionRecord,
  createPolicy,
  createPolicyVersionReviewRequest,
  createPolicyVersionDraft,
  fetchPolicies,
  fetchPolicyVersionReviewRequests,
  fetchPolicyVersionsForPolicy,
  fetchPolicyRulesForPolicy,
  updatePolicyVersionDraft
} from "../lib/policies";
import {
  POLICY_TEMPLATES,
  PolicyTemplate,
  PolicyCondition,
  compilePolicyRulePreview,
  conditionToDsl,
  defaultCondition,
  localValidationMessages,
  parsePolicyDslToPolicyRule,
  parseRuleCondition,
  policyBlocksFromCondition,
  slugifyPolicyName,
  stableCondition,
  templateToDsl,
  unsupportedConditionFields
} from "./policy-dsl";
import { PolicyEditor } from "./policy-editor";
import { PolicyInspector } from "./policy-inspector";
import { PolicyRepository } from "./policy-repository";
import { PolicyTemplatesDrawer } from "./policy-templates";

type PoliciesState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; policies: PolicyRecord[] };

type RulesState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; rules: PolicyRuleRecord[] };

type VersionsState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; versions: PolicyVersionRecord[] };

type ReviewRequestsState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; requests: PolicyVersionReviewRequestRecord[] };

type SaveState = {
  status: "idle" | "saving" | "success" | "error";
  message: string;
};

type ReviewState = {
  status: "idle" | "submitting" | "success" | "error";
  message: string;
};

const INITIAL_TEMPLATE =
  POLICY_TEMPLATES.find((template) => template.id === "governance_review_gate") ||
  POLICY_TEMPLATES[0];

export function PolicyStudio() {
  const [policiesState, setPoliciesState] = useState<PoliciesState>({
    status: "loading"
  });
  const [rulesState, setRulesState] = useState<RulesState>({ status: "idle" });
  const [versionsState, setVersionsState] = useState<VersionsState>({
    status: "idle"
  });
  const [reviewRequestsState, setReviewRequestsState] =
    useState<ReviewRequestsState>({ status: "idle" });
  const [selectedPolicyId, setSelectedPolicyId] = useState<string | null>(null);
  const [selectedRuleId, setSelectedRuleId] = useState<string | null>(null);
  const [draftVersion, setDraftVersion] = useState<PolicyVersionRecord | null>(
    null
  );
  const [repositoryMode, setRepositoryMode] = useState<"policies" | "templates">(
    "policies"
  );
  const [repositoryQuery, setRepositoryQuery] = useState("");
  const [editorMode, setEditorMode] = useState<"blocks" | "code">("blocks");
  const [dsl, setDsl] = useState(() => templateToDsl(INITIAL_TEMPLATE));
  const [localNote, setLocalNote] = useState("");
  const [selectedBlockId, setSelectedBlockId] = useState<string | null>(null);
  const [showTemplates, setShowTemplates] = useState(false);
  const [saveState, setSaveState] = useState<SaveState>({
    status: "idle",
    message: "Unsaved local editor state"
  });
  const [reviewState, setReviewState] = useState<ReviewState>({
    status: "idle",
    message: "Review request not submitted"
  });
  const [validationRun, setValidationRun] = useState(0);

  const selectedPolicy = useMemo(() => {
    if (policiesState.status !== "ready" || !selectedPolicyId) {
      return null;
    }

    return (
      policiesState.policies.find((policy) => policy.id === selectedPolicyId) ||
      null
    );
  }, [policiesState, selectedPolicyId]);

  const selectedRule = useMemo(() => {
    if (rulesState.status !== "ready" || !selectedRuleId) {
      return null;
    }

    return rulesState.rules.find((rule) => rule.id === selectedRuleId) || null;
  }, [rulesState, selectedRuleId]);

  const latestDraftVersion = useMemo(() => {
    if (versionsState.status !== "ready") {
      return null;
    }

    return (
      [...versionsState.versions]
        .filter((version) => version.status === "draft")
        .sort((left, right) => right.version_number - left.version_number)[0] ||
      null
    );
  }, [versionsState]);

  const selectedDraftVersion =
    draftVersion && draftVersion.policy_id === selectedPolicyId
      ? draftVersion
      : latestDraftVersion;
  const pendingReviewRequest = useMemo(() => {
    if (!selectedDraftVersion || reviewRequestsState.status !== "ready") {
      return null;
    }

    return (
      reviewRequestsState.requests.find(
        (request) =>
          request.policy_version_id === selectedDraftVersion.id &&
          request.status === "pending"
      ) || null
    );
  }, [reviewRequestsState, selectedDraftVersion]);

  const parsed = useMemo(() => parsePolicyDslToPolicyRule(dsl), [dsl]);
  const selectedRuleCondition = useMemo(
    () => (selectedRule ? parseRuleCondition(selectedRule) : null),
    [selectedRule]
  );
  const selectedRuleUnsupportedFields = useMemo(
    () =>
      selectedRuleCondition ? unsupportedConditionFields(selectedRuleCondition) : [],
    [selectedRuleCondition]
  );
  const condition = parsed.condition || defaultCondition();
  const blocks = useMemo(() => policyBlocksFromCondition(condition), [condition]);
  const compiled = useMemo(() => compilePolicyRulePreview(parsed), [parsed]);
  const saveDisabledReason = useMemo(() => {
    if (parsed.errors.length > 0) {
      return parsed.errors.join(" ");
    }
    if (parsed.unsupported.length > 0) {
      return "Remove unsupported DSL lines before saving. They are not persisted by the current PolicyRule condition compiler.";
    }
    if (selectedRuleUnsupportedFields.length > 0) {
      return `Selected backend PolicyRule contains unsupported condition field(s): ${selectedRuleUnsupportedFields.join(
        ", "
      )}. Create a new draft or use a supported rule to avoid dropping fields.`;
    }

    return null;
  }, [parsed.errors, parsed.unsupported, selectedRuleUnsupportedFields]);
  const validationMessages = useMemo(
    () => [
      ...localValidationMessages(parsed),
      ...studioStateMessages({
        policiesState,
        rulesState,
        pendingReviewRequest,
        reviewRequestsState,
        reviewState,
        saveDisabledReason,
        saveState,
        selectedDraftVersion,
        selectedPolicy,
        selectedRule,
        selectedRuleUnsupportedFields,
        versionsState
      })
    ],
    [
      parsed,
      policiesState,
      rulesState,
      pendingReviewRequest,
      reviewRequestsState,
      reviewState,
      saveDisabledReason,
      saveState,
      selectedDraftVersion,
      selectedPolicy,
      selectedRule,
      selectedRuleUnsupportedFields,
      versionsState,
      validationRun
    ]
  );

  const loadPolicies = useCallback(async (signal?: AbortSignal) => {
    setPoliciesState({ status: "loading" });

    try {
      const policies = await fetchPolicies(signal);
      setPoliciesState({ status: "ready", policies });
      if (policies.length > 0) {
        setSelectedPolicyId((current) =>
          current && policies.some((policy) => policy.id === current)
            ? current
            : policies[0].id
        );
      }
    } catch (error: unknown) {
      if (signal?.aborted) {
        return;
      }

      setPoliciesState({
        status: "error",
        message: errorMessage(error, "Unable to load Policy records.")
      });
    }
  }, []);

  const loadRules = useCallback(
    async (policy: PolicyRecord, signal?: AbortSignal) => {
      setRulesState({ status: "loading" });

      try {
        const rules = await fetchPolicyRulesForPolicy(policy.id, signal);
        setRulesState({ status: "ready", rules });
        const firstRule = rules[0] || null;
        const firstCondition = firstRule ? parseRuleCondition(firstRule) : null;
        const unsupportedFields = firstCondition
          ? unsupportedConditionFields(firstCondition)
          : [];
        setSelectedRuleId(firstRule?.id || null);
        setDsl(
          firstRule
            ? conditionToDsl(policy.name, firstCondition || defaultCondition())
            : conditionToDsl(policy.name, defaultCondition())
        );
        setSaveState({
          status: unsupportedFields.length > 0 ? "error" : "idle",
          message:
            unsupportedFields.length > 0
              ? `Loaded PolicyRule has unsupported condition field(s): ${unsupportedFields.join(
                  ", "
                )}`
              : firstRule
                ? "Loaded from backend PolicyRule"
                : "No PolicyRule persisted for selected Policy"
        });
      } catch (error: unknown) {
        if (signal?.aborted) {
          return;
        }

        setRulesState({
          status: "error",
          message: errorMessage(error, "Unable to load PolicyRule records.")
        });
      }
    },
    []
  );

  const loadVersions = useCallback(
    async (policy: PolicyRecord, signal?: AbortSignal) => {
      setVersionsState({ status: "loading" });

      try {
        const versions = await fetchPolicyVersionsForPolicy(policy.id, signal);
        setVersionsState({ status: "ready", versions });
        const latestDraft =
          [...versions]
            .filter((version) => version.status === "draft")
            .sort((left, right) => right.version_number - left.version_number)[0] ||
          null;
        setDraftVersion(latestDraft);
      } catch (error: unknown) {
        if (signal?.aborted) {
          return;
        }

        setVersionsState({
          status: "error",
          message: errorMessage(error, "Unable to load PolicyVersion records.")
        });
        setDraftVersion(null);
      }
    },
    []
  );

  const loadReviewRequests = useCallback(async (signal?: AbortSignal) => {
    setReviewRequestsState({ status: "loading" });

    try {
      const requests = await fetchPolicyVersionReviewRequests("pending", signal);
      setReviewRequestsState({ status: "ready", requests });
    } catch (error: unknown) {
      if (signal?.aborted) {
        return;
      }

      setReviewRequestsState({
        status: "error",
        message: errorMessage(
          error,
          "Unable to load PolicyVersion review requests."
        )
      });
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    void loadPolicies(controller.signal);
    void loadReviewRequests(controller.signal);
    return () => controller.abort();
  }, [loadPolicies, loadReviewRequests]);

  useEffect(() => {
    if (!selectedPolicy) {
      setRulesState({ status: "idle" });
      setVersionsState({ status: "idle" });
      setDraftVersion(null);
      return;
    }

    const controller = new AbortController();
    void loadRules(selectedPolicy, controller.signal);
    void loadVersions(selectedPolicy, controller.signal);
    return () => controller.abort();
  }, [loadRules, loadVersions, selectedPolicy]);

  function handleSelectPolicy(policy: PolicyRecord) {
    setSelectedPolicyId(policy.id);
    setSelectedRuleId(null);
    setDraftVersion(null);
    setSaveState({ status: "idle", message: "Loading selected Policy rules" });
    setReviewState({ status: "idle", message: "Review request not submitted" });
    setRepositoryMode("policies");
  }

  function handleNewPolicy() {
    setSelectedPolicyId(null);
    setSelectedRuleId(null);
    setDraftVersion(null);
    setVersionsState({ status: "idle" });
    setDsl(conditionToDsl("new_policy", defaultCondition()));
    setSaveState({
      status: "idle",
      message: "New unsaved Policy draft"
    });
    setReviewState({ status: "idle", message: "Review request not submitted" });
  }

  function handleUseTemplate(template: PolicyTemplate) {
    setSelectedPolicyId(null);
    setSelectedRuleId(null);
    setDraftVersion(null);
    setVersionsState({ status: "idle" });
    setDsl(templateToDsl(template));
    setEditorMode("blocks");
    setSaveState({
      status: "idle",
      message: `${template.name} template loaded locally. Save draft to persist.`
    });
    setReviewState({ status: "idle", message: "Review request not submitted" });
  }

  function handleSelectRule(rule: PolicyRuleRecord) {
    const conditionForRule = parseRuleCondition(rule);
    const unsupportedFields = unsupportedConditionFields(conditionForRule);
    setSelectedRuleId(rule.id);
    setDsl(conditionToDsl(selectedPolicy?.name || rule.name, conditionForRule));
    setSaveState({
      status: unsupportedFields.length > 0 ? "error" : "idle",
      message:
        unsupportedFields.length > 0
          ? `Selected PolicyRule has unsupported condition field(s): ${unsupportedFields.join(
              ", "
            )}`
          : "Loaded selected PolicyRule"
    });
    setReviewState({ status: "idle", message: "Review request not submitted" });
  }

  function handleValidate() {
    setValidationRun((current) => current + 1);
    setSaveState({
      status: parsed.errors.length > 0 ? "error" : "idle",
      message:
        parsed.errors.length > 0
          ? parsed.errors.join(" ")
          : "Local validation completed"
    });
  }

  async function handleSaveDraft() {
    const parsedForSave = parsePolicyDslToPolicyRule(dsl);

    if (!parsedForSave.condition) {
      setSaveState({
        status: "error",
        message: parsedForSave.errors.join(" ") || "DSL did not compile."
      });
      return;
    }

    if (parsedForSave.unsupported.length > 0) {
      setSaveState({
        status: "error",
        message:
          "Remove unsupported DSL lines before saving. Unsupported lines are not persisted by the current compiler."
      });
      return;
    }

    if (selectedRuleUnsupportedFields.length > 0) {
      setSaveState({
        status: "error",
        message: `Selected backend PolicyRule contains unsupported condition field(s): ${selectedRuleUnsupportedFields.join(
          ", "
        )}. Saving is blocked to avoid dropping backend fields.`
      });
      return;
    }

    if (!parsedForSave.ruleName.trim()) {
      setSaveState({
        status: "error",
        message: "PolicyRule name is required."
      });
      return;
    }

    setSaveState({ status: "saving", message: "Saving draft" });

    try {
      const policy = await ensurePolicyDraft(selectedPolicy, parsedForSave.policyName);
      const versionToUpdate =
        selectedDraftVersion?.policy_id === policy.id &&
        selectedDraftVersion.status === "draft"
          ? selectedDraftVersion
          : null;
      const draftPayload = buildPolicyVersionDraftPayload({
        condition: parsedForSave.condition,
        draftVersion: versionToUpdate,
        localNote,
        policy,
        policyName: parsedForSave.policyName,
        rule: selectedRule,
        ruleName: parsedForSave.ruleName
      });
      const savedVersion = versionToUpdate
        ? await updatePolicyVersionDraft(versionToUpdate.id, draftPayload)
        : await createPolicyVersionDraft(policy.id, draftPayload);

      setDraftVersion(savedVersion);
      setSelectedPolicyId(policy.id);
      setDsl(
        conditionToDsl(
          String(savedVersion.policy_snapshot.name || policy.name),
          parseRuleSnapshotCondition(savedVersion)
        )
      );
      setSaveState({
        status: "success",
        message: `Draft PolicyVersion v${savedVersion.version_number} saved. It is not active and does not affect runtime until explicitly activated.`
      });
      setReviewState({ status: "idle", message: "Review request not submitted" });
      void loadPolicies();
      void loadRules(policy);
      void loadVersions(policy);
    } catch (error: unknown) {
      setSaveState({
        status: "error",
        message: errorMessage(error, "Unable to save Policy Studio draft.")
      });
    }
  }

  async function handleSubmitReview() {
    const parsedForSubmit = parsePolicyDslToPolicyRule(dsl);
    if (!selectedDraftVersion) {
      setReviewState({
        status: "error",
        message: "Save a draft PolicyVersion before submitting for review."
      });
      return;
    }
    if (parsedForSubmit.errors.length > 0 || parsedForSubmit.unsupported.length > 0) {
      setReviewState({
        status: "error",
        message:
          "Run local validation and remove unsupported DSL lines before review submission."
      });
      return;
    }
    if (saveDisabledReason) {
      setReviewState({ status: "error", message: saveDisabledReason });
      return;
    }
    if (pendingReviewRequest) {
      setReviewState({
        status: "error",
        message: "This draft PolicyVersion already has a pending review request."
      });
      return;
    }

    setReviewState({
      status: "submitting",
      message: "Submitting draft PolicyVersion for review"
    });

    try {
      const request = await createPolicyVersionReviewRequest(
        selectedDraftVersion.id,
        {
          request_note:
            localNote.trim() ||
            `Policy Studio review request for draft v${selectedDraftVersion.version_number}.`
        }
      );
      setReviewState({
        status: "success",
        message: `Review requested for draft PolicyVersion v${selectedDraftVersion.version_number}. Approval does not activate this version.`
      });
      setReviewRequestsState((current) =>
        current.status === "ready"
          ? { status: "ready", requests: [request, ...current.requests] }
          : current
      );
      void loadReviewRequests();
    } catch (error: unknown) {
      setReviewState({
        status: "error",
        message: errorMessage(error, "Unable to submit PolicyVersion review request.")
      });
    }
  }

  async function ensurePolicyDraft(
    policy: PolicyRecord | null,
    policyName: string
  ) {
    if (policy) {
      return policy;
    }

    const payload: PolicyPayload = {
      description: "Policy Studio draft container for PolicyVersion snapshots.",
      name: titleFromSlug(policyName),
      status: "draft"
    };

    return createPolicy(payload);
  }

  return (
    <div className="policy-studio-route">
      <div className="ps2-shell">
        <PolicyRepository
          mode={repositoryMode}
          onModeChange={setRepositoryMode}
          onNewPolicy={handleNewPolicy}
          onOpenTemplates={() => setShowTemplates(true)}
          onSelectPolicy={handleSelectPolicy}
          onSelectRule={handleSelectRule}
          onUseTemplate={handleUseTemplate}
          policiesState={policiesState}
          query={repositoryQuery}
          rulesState={rulesState}
          selectedPolicyId={selectedPolicyId}
          selectedRuleId={selectedRuleId}
          setQuery={setRepositoryQuery}
        />

        <PolicyEditor
          blocks={blocks}
          compiled={compiled}
          dsl={dsl}
          editorMode={editorMode}
          onChangeDsl={(nextDsl) => {
            setDsl(nextDsl);
            setSaveState({ status: "idle", message: "Unsaved local edits" });
            setReviewState({
              status: "idle",
              message: "Review request not submitted"
            });
          }}
          onSelectBlock={setSelectedBlockId}
          onSetEditorMode={setEditorMode}
          onValidate={handleValidate}
          selectedBlockId={selectedBlockId}
          validationMessages={validationMessages}
        />

        <PolicyInspector
          compiled={compiled}
          condition={condition}
          localNote={localNote}
          onChangeLocalNote={setLocalNote}
          onSaveDraft={handleSaveDraft}
          onSubmitReview={handleSubmitReview}
          onValidate={handleValidate}
          pendingReviewRequest={pendingReviewRequest}
          parsed={parsed}
          policyVersionsState={versionsState}
          reviewRequestsState={reviewRequestsState}
          reviewState={reviewState}
          saveDisabledReason={saveDisabledReason}
          saveState={saveState}
          selectedDraftVersion={selectedDraftVersion}
          selectedPolicy={selectedPolicy}
          selectedRule={selectedRule}
          selectedRuleUnsupportedFields={selectedRuleUnsupportedFields}
        />

        {showTemplates ? (
          <PolicyTemplatesDrawer
            onClose={() => setShowTemplates(false)}
            onUseTemplate={handleUseTemplate}
          />
        ) : null}
      </div>
    </div>
  );
}

function studioStateMessages({
  policiesState,
  rulesState,
  pendingReviewRequest,
  reviewRequestsState,
  reviewState,
  saveDisabledReason,
  saveState,
  selectedDraftVersion,
  selectedPolicy,
  selectedRule,
  selectedRuleUnsupportedFields,
  versionsState
}: {
  policiesState: PoliciesState;
  rulesState: RulesState;
  pendingReviewRequest: PolicyVersionReviewRequestRecord | null;
  reviewRequestsState: ReviewRequestsState;
  reviewState: ReviewState;
  saveDisabledReason: string | null;
  saveState: SaveState;
  selectedDraftVersion: PolicyVersionRecord | null;
  selectedPolicy: PolicyRecord | null;
  selectedRule: PolicyRuleRecord | null;
  selectedRuleUnsupportedFields: string[];
  versionsState: VersionsState;
}): Array<{ tone: "ok" | "warn" | "error" | "info"; text: string }> {
  const messages: Array<{ tone: "ok" | "warn" | "error" | "info"; text: string }> = [];

  if (policiesState.status === "error") {
    messages.push({
      tone: "warn",
      text: `Backend unavailable for GET /policies: ${policiesState.message}`
    });
  }

  if (rulesState.status === "error") {
    messages.push({
      tone: "warn",
      text: `Backend unavailable for GET /policies/{policy_id}/rules: ${rulesState.message}`
    });
  }

  if (versionsState.status === "error") {
    messages.push({
      tone: "warn",
      text: `Backend unavailable for GET /policies/{policy_id}/versions: ${versionsState.message}`
    });
  }

  if (reviewRequestsState.status === "error") {
    messages.push({
      tone: "warn",
      text: `Backend unavailable for GET /policy-version-review-requests: ${reviewRequestsState.message}`
    });
  }

  messages.push({
    tone: selectedPolicy ? "info" : "warn",
    text: selectedPolicy
      ? `Selected Policy: ${selectedPolicy.id} (${selectedPolicy.status})`
      : "No persisted Policy selected; Save draft will create a draft Policy container"
  });
  messages.push({
    tone: selectedRule ? "info" : "warn",
    text: selectedRule
      ? `Selected PolicyRule: ${selectedRule.id}. Save draft snapshots this source rule without patching it.`
      : "No PolicyRule selected; Save draft will snapshot a generated rule id into a draft PolicyVersion"
  });

  if (selectedDraftVersion) {
    messages.push({
      tone: "ok",
      text: `Draft PolicyVersion v${selectedDraftVersion.version_number}: ${selectedDraftVersion.id} (not active, not submitted for review)`
    });
  }

  if (pendingReviewRequest) {
    messages.push({
      tone: "ok",
      text: `Pending PolicyVersion review request: ${pendingReviewRequest.id}. Approval does not activate this version.`
    });
  }

  if (rulesState.status === "ready" && rulesState.rules.length > 1) {
    messages.push({
      tone: "info",
      text: `${rulesState.rules.length} PolicyRules loaded. Select a rule in the repository before editing to avoid accidental overwrites.`
    });
  }

  if (selectedPolicy?.status === "active") {
    messages.push({
      tone: "warn",
      text: "Selected Policy is active. Save draft creates a draft PolicyVersion; runtime still uses the active version or fallback until explicit activation."
    });
  }

  if (selectedRuleUnsupportedFields.length > 0) {
    messages.push({
      tone: "error",
      text: `Selected backend rule has unsupported fields not represented in this editor: ${selectedRuleUnsupportedFields.join(
        ", "
      )}`
    });
  }

  if (saveDisabledReason) {
    messages.push({ tone: "error", text: `Save draft blocked: ${saveDisabledReason}` });
  }

  if (saveState.status === "success") {
    messages.push({ tone: "ok", text: saveState.message });
  }
  if (saveState.status === "error") {
    messages.push({ tone: "error", text: saveState.message });
  }
  if (reviewState.status === "success") {
    messages.push({ tone: "ok", text: reviewState.message });
  }
  if (reviewState.status === "error") {
    messages.push({ tone: "error", text: reviewState.message });
  }

  return messages;
}

function buildPolicyVersionDraftPayload({
  condition,
  draftVersion,
  localNote,
  policy,
  policyName,
  rule,
  ruleName
}: {
  condition: PolicyCondition;
  draftVersion: PolicyVersionRecord | null;
  localNote: string;
  policy: PolicyRecord;
  policyName: string;
  rule: PolicyRuleRecord | null;
  ruleName: string;
}): PolicyVersionDraftPayload {
  const compiledCondition = JSON.stringify(stableCondition(condition));
  const summary = localNote.trim() || `Policy Studio draft for ${titleFromSlug(policyName)}.`;
  const existingSnapshotRuleId =
    typeof draftVersion?.rule_snapshots[0]?.id === "string"
      ? draftVersion.rule_snapshots[0].id
      : undefined;
  const sourceRuleId =
    rule && rule.policy_id === policy.id ? rule.id : existingSnapshotRuleId;
  return {
    change_summary: summary,
    policy_snapshot: {
      description: policy.description || "Policy Studio draft snapshot.",
      name: titleFromSlug(policyName || policy.name),
      status: policy.status
    },
    rule_snapshots: [
      {
        ...(sourceRuleId ? { id: sourceRuleId } : {}),
        condition: compiledCondition,
        description: "Compiled from Policy Studio DSL/block editor.",
        name: ruleName || "policy_studio_rule"
      }
    ]
  };
}

function parseRuleSnapshotCondition(version: PolicyVersionRecord) {
  const snapshot = version.rule_snapshots[0] || {};
  const condition = snapshot.condition;
  if (typeof condition !== "string") {
    return defaultCondition();
  }

  return parseRuleCondition({
    condition,
    created_at: version.created_at,
    description:
      typeof snapshot.description === "string" ? snapshot.description : null,
    id: typeof snapshot.id === "string" ? snapshot.id : "snapshot-rule",
    name: typeof snapshot.name === "string" ? snapshot.name : "snapshot_rule",
    policy_id: version.policy_id,
    updated_at: version.updated_at
  });
}

function titleFromSlug(value: string) {
  return slugifyPolicyName(value)
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function errorMessage(error: unknown, fallback: string) {
  if (error instanceof ApiRequestError) {
    return error.message;
  }

  return error instanceof Error ? error.message : fallback;
}
