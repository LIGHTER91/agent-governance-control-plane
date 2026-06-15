"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ApiRequestError } from "../lib/api";
import type { CurrentActorRecord } from "../lib/current-actor";
import { fetchCurrentActor } from "../lib/current-actor";
import {
  PolicyPayload,
  PolicyRecord,
  PolicyRuleRecord,
  PolicyVersionDraftPayload,
  PolicyVersionReviewDiffRecord,
  PolicyVersionReviewRequestRecord,
  PolicyVersionReviewStateRecord,
  PolicyVersionRecord,
  createPolicy,
  createPolicyVersionReviewRequest,
  createPolicyVersionDraft,
  fetchPolicies,
  fetchPolicyVersionReviewRequestDiff,
  fetchPolicyVersionReviewState,
  fetchPolicyVersionsForPolicy,
  fetchPolicyRulesForPolicy,
  updatePolicyVersionDraft
} from "../lib/policies";
import {
  POLICY_TEMPLATES,
  PolicyTemplate,
  PolicyCondition,
  PolicyValidationMessage,
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

type VersionReviewState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; state: PolicyVersionReviewStateRecord };

type CurrentActorState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; actor: CurrentActorRecord };

export type PolicyStudioEditorSource =
  | { kind: "local_draft" }
  | { kind: "draft_version"; versionId: string; versionNumber: number }
  | { kind: "active_version"; versionId: string; versionNumber: number }
  | { kind: "live_fallback" };

type SaveState = {
  status: "unsaved" | "saving" | "saved" | "save_error";
  message: string;
};

type ReviewState = {
  status: "idle" | "submitting" | "success" | "error";
  message: string;
};

type ReviewDiffState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; diff: PolicyVersionReviewDiffRecord };

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
  const [versionReviewState, setVersionReviewState] = useState<VersionReviewState>({
    status: "idle"
  });
  const [currentActorState, setCurrentActorState] = useState<CurrentActorState>({
    status: "idle"
  });
  const [selectedPolicyId, setSelectedPolicyId] = useState<string | null>(null);
  const [selectedRuleId, setSelectedRuleId] = useState<string | null>(null);
  const [draftVersion, setDraftVersion] = useState<PolicyVersionRecord | null>(
    null
  );
  const [editorSource, setEditorSource] = useState<PolicyStudioEditorSource>({
    kind: "local_draft"
  });
  const [repositoryMode, setRepositoryMode] = useState<"policies" | "templates">(
    "policies"
  );
  const [repositoryQuery, setRepositoryQuery] = useState("");
  const [editorMode, setEditorMode] = useState<"blocks" | "code">("blocks");
  const [dsl, setDsl] = useState(() => templateToDsl(INITIAL_TEMPLATE));
  const preserveEditorOnNextRulesLoadRef = useRef<string | null>(null);
  const [localNote, setLocalNote] = useState("");
  const [selectedBlockId, setSelectedBlockId] = useState<string | null>(null);
  const [showTemplates, setShowTemplates] = useState(false);
  const [saveState, setSaveState] = useState<SaveState>({
    status: "unsaved",
    message: "Unsaved local editor state"
  });
  const [reviewState, setReviewState] = useState<ReviewState>({
    status: "idle",
    message: "Review request not submitted"
  });
  const [reviewDiffState, setReviewDiffState] = useState<ReviewDiffState>({
    status: "idle"
  });
  const [validationRun, setValidationRun] = useState(0);
  const localEditorDirtyRef = useRef(false);
  const savedEditorPolicyRef = useRef<string | null>(null);

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
  const selectedDraftReviewState =
    versionReviewState.status === "ready" &&
    selectedDraftVersion &&
    versionReviewState.state.policy_version_id === selectedDraftVersion.id
      ? versionReviewState.state
      : null;

  const parsed = useMemo(() => parsePolicyDslToPolicyRule(dsl), [dsl]);
  const selectedRuleCondition = useMemo(
    () =>
      editorSource.kind === "live_fallback" && selectedRule
        ? parseRuleCondition(selectedRule)
        : null,
    [editorSource.kind, selectedRule]
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
    if (
      editorSource.kind === "draft_version" &&
      selectedDraftReviewState?.review_status === "pending"
    ) {
      return pendingDraftLockedMessage();
    }

    return null;
  }, [
    editorSource.kind,
    parsed.errors,
    parsed.unsupported,
    selectedDraftReviewState?.review_status,
    selectedRuleUnsupportedFields
  ]);
  const validationMessages = useMemo(
    () => [
      ...localValidationMessages(parsed),
      ...studioStateMessages({
        policiesState,
        editorSource,
        rulesState,
        selectedDraftReviewState,
        reviewState,
        saveDisabledReason,
        saveState,
        selectedDraftVersion,
        selectedPolicy,
        selectedRule,
        selectedRuleUnsupportedFields,
        versionReviewState,
        versionsState
      })
    ],
    [
      parsed,
      policiesState,
      editorSource,
      rulesState,
      selectedDraftReviewState,
      reviewState,
      saveDisabledReason,
      saveState,
      selectedDraftVersion,
      selectedPolicy,
      selectedRule,
      selectedRuleUnsupportedFields,
      versionReviewState,
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

  const loadCurrentActor = useCallback(async (signal?: AbortSignal) => {
    setCurrentActorState({ status: "loading" });

    try {
      const actor = await fetchCurrentActor(signal);
      setCurrentActorState({ status: "ready", actor });
    } catch (error: unknown) {
      if (signal?.aborted) {
        return;
      }

      setCurrentActorState({
        status: "error",
        message: errorMessage(error, "Unable to load current actor from GET /me.")
      });
    }
  }, []);

  const loadRules = useCallback(
    async (
      policy: PolicyRecord,
      signal?: AbortSignal,
      options: { hydrateEditor: boolean } = { hydrateEditor: true }
    ) => {
      setRulesState({ status: "loading" });

      try {
        const rules = await fetchPolicyRulesForPolicy(policy.id, signal);
        setRulesState({ status: "ready", rules });
        if (!options.hydrateEditor) {
          return;
        }
        if (localEditorDirtyRef.current) {
          return;
        }
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
        setEditorSource({ kind: "live_fallback" });
        localEditorDirtyRef.current = false;
        setSaveState({
          status: unsupportedFields.length > 0 ? "save_error" : "unsaved",
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
    async (
      policy: PolicyRecord,
      signal?: AbortSignal,
      options: { hydrateEditor: boolean } = { hydrateEditor: true }
    ) => {
      setVersionsState({ status: "loading" });

      try {
        const versions = await fetchPolicyVersionsForPolicy(policy.id, signal);
        setVersionsState({ status: "ready", versions });
        const latestDraft =
          [...versions]
            .filter((version) => version.status === "draft")
            .sort((left, right) => right.version_number - left.version_number)[0] ||
          null;
        const activeVersion =
          [...versions]
            .filter((version) => version.status === "active")
            .sort((left, right) => right.version_number - left.version_number)[0] ||
          null;
        setDraftVersion(latestDraft);
        if (savedEditorPolicyRef.current === policy.id) {
          return;
        }
        if (!options.hydrateEditor || localEditorDirtyRef.current) {
          return;
        }
        if (latestDraft) {
          hydrateEditorFromPolicyVersion(latestDraft, "draft_version");
          return;
        }
        if (activeVersion) {
          hydrateEditorFromPolicyVersion(activeVersion, "active_version");
          return;
        }

        setEditorSource({ kind: "live_fallback" });
        void loadRules(policy, signal, { hydrateEditor: true });
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
    [loadRules]
  );

  const loadVersionReviewState = useCallback(
    async (policyVersionId: string, signal?: AbortSignal) => {
      setVersionReviewState({ status: "loading" });

      try {
        const state = await fetchPolicyVersionReviewState(policyVersionId, signal);
        setVersionReviewState({ status: "ready", state });
      } catch (error: unknown) {
        if (signal?.aborted) {
          return;
        }

        setVersionReviewState({
          status: "error",
          message:
            error instanceof ApiRequestError && error.status === 403
              ? "Review state unavailable for current actor."
              : errorMessage(error, "Unable to load PolicyVersion review state.")
        });
      }
    },
    []
  );

  useEffect(() => {
    const controller = new AbortController();
    void loadPolicies(controller.signal);
    void loadCurrentActor(controller.signal);
    return () => controller.abort();
  }, [loadCurrentActor, loadPolicies]);

  useEffect(() => {
    if (!selectedPolicy) {
      setRulesState({ status: "idle" });
      setVersionsState({ status: "idle" });
      setDraftVersion(null);
      setEditorSource({ kind: "local_draft" });
      setVersionReviewState({ status: "idle" });
      return;
    }

    const controller = new AbortController();
    const hydrateEditor =
      preserveEditorOnNextRulesLoadRef.current !== selectedPolicy.id;
    if (!hydrateEditor) {
      preserveEditorOnNextRulesLoadRef.current = null;
    }
    localEditorDirtyRef.current = false;
    void loadRules(selectedPolicy, controller.signal, { hydrateEditor: false });
    void loadVersions(selectedPolicy, controller.signal, { hydrateEditor });
    return () => controller.abort();
  }, [loadRules, loadVersions, selectedPolicy]);

  useEffect(() => {
    if (!selectedDraftVersion) {
      setVersionReviewState({ status: "idle" });
      return;
    }

    const controller = new AbortController();
    void loadVersionReviewState(selectedDraftVersion.id, controller.signal);
    return () => controller.abort();
  }, [loadVersionReviewState, selectedDraftVersion]);

  useEffect(() => {
    if (!selectedDraftReviewState?.latest_review_request_id) {
      setReviewDiffState({ status: "idle" });
      return;
    }

    const controller = new AbortController();
    setReviewDiffState({ status: "loading" });
    void fetchPolicyVersionReviewRequestDiff(
      selectedDraftReviewState.latest_review_request_id,
      controller.signal
    )
      .then((diff) => {
        setReviewDiffState({ status: "ready", diff });
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) {
          return;
        }

        setReviewDiffState({
          status: "error",
          message: errorMessage(error, "Unable to load Policy Review Diff.")
        });
      });

    return () => controller.abort();
  }, [selectedDraftReviewState?.latest_review_request_id]);

  function handleSelectPolicy(policy: PolicyRecord) {
    preserveEditorOnNextRulesLoadRef.current = null;
    savedEditorPolicyRef.current = null;
    localEditorDirtyRef.current = false;
    setSelectedPolicyId(policy.id);
    setSelectedRuleId(null);
    setDraftVersion(null);
    setEditorSource({ kind: "local_draft" });
    setVersionReviewState({ status: "idle" });
    setSaveState({ status: "unsaved", message: "Loading selected Policy rules" });
    setReviewState({ status: "idle", message: "Review request not submitted" });
    setRepositoryMode("policies");
  }

  function handleNewPolicy() {
    preserveEditorOnNextRulesLoadRef.current = null;
    savedEditorPolicyRef.current = null;
    localEditorDirtyRef.current = false;
    setSelectedPolicyId(null);
    setSelectedRuleId(null);
    setDraftVersion(null);
    setVersionsState({ status: "idle" });
    setEditorSource({ kind: "local_draft" });
    setVersionReviewState({ status: "idle" });
    setDsl(conditionToDsl("new_policy", defaultCondition()));
    setSaveState({
      status: "unsaved",
      message: "New unsaved Policy draft"
    });
    setReviewState({ status: "idle", message: "Review request not submitted" });
  }

  function handleUseTemplate(template: PolicyTemplate) {
    preserveEditorOnNextRulesLoadRef.current = null;
    savedEditorPolicyRef.current = null;
    localEditorDirtyRef.current = false;
    setSelectedPolicyId(null);
    setSelectedRuleId(null);
    setDraftVersion(null);
    setVersionsState({ status: "idle" });
    setEditorSource({ kind: "local_draft" });
    setVersionReviewState({ status: "idle" });
    setDsl(templateToDsl(template));
    setEditorMode("blocks");
    setSaveState({
      status: "unsaved",
      message: `${template.name} template loaded locally. Save draft to persist.`
    });
    setReviewState({ status: "idle", message: "Review request not submitted" });
  }

  function handleSelectRule(rule: PolicyRuleRecord) {
    preserveEditorOnNextRulesLoadRef.current = null;
    savedEditorPolicyRef.current = null;
    localEditorDirtyRef.current = false;
    const conditionForRule = parseRuleCondition(rule);
    const unsupportedFields = unsupportedConditionFields(conditionForRule);
    setSelectedRuleId(rule.id);
    setEditorSource({ kind: "live_fallback" });
    setDsl(conditionToDsl(selectedPolicy?.name || rule.name, conditionForRule));
    setSaveState({
      status: unsupportedFields.length > 0 ? "save_error" : "unsaved",
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
    setSaveState((current) => ({
      status:
        parsed.errors.length > 0
          ? "save_error"
          : current.status === "saved"
            ? "saved"
            : "unsaved",
      message:
        parsed.errors.length > 0
          ? parsed.errors.join(" ")
          : current.status === "saved"
            ? current.message
            : "Local validation completed"
    }));
  }

  async function handleSaveDraft() {
    const parsedForSave = parsePolicyDslToPolicyRule(dsl);

    if (!parsedForSave.condition) {
      setSaveState({
        status: "save_error",
        message: parsedForSave.errors.join(" ") || "DSL did not compile."
      });
      return;
    }

    if (parsedForSave.unsupported.length > 0) {
      setSaveState({
        status: "save_error",
        message:
          "Remove unsupported DSL lines before saving. Unsupported lines are not persisted by the current compiler."
      });
      return;
    }

    if (selectedRuleUnsupportedFields.length > 0) {
      setSaveState({
        status: "save_error",
        message: `Selected backend PolicyRule contains unsupported condition field(s): ${selectedRuleUnsupportedFields.join(
          ", "
        )}. Saving is blocked to avoid dropping backend fields.`
      });
      return;
    }

    if (!parsedForSave.ruleName.trim()) {
      setSaveState({
        status: "save_error",
        message: "PolicyRule name is required."
      });
      return;
    }

    setSaveState({ status: "saving", message: "Saving draft" });

    try {
      const policy = await ensurePolicyDraft(selectedPolicy, parsedForSave.policyName);
      const versionToUpdate =
        editorSource.kind === "draft_version" &&
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
      setVersionsState((current) =>
        current.status === "ready"
          ? {
              status: "ready",
              versions: upsertPolicyVersionRecord(current.versions, savedVersion)
            }
          : current
      );
      setPoliciesState((current) =>
        current.status === "ready"
          ? {
              status: "ready",
              policies: upsertPolicyRecord(current.policies, policy)
            }
          : current
      );
      preserveEditorOnNextRulesLoadRef.current = policy.id;
      savedEditorPolicyRef.current = policy.id;
      setSelectedPolicyId(policy.id);
      hydrateEditorFromPolicyVersion(savedVersion, "draft_version");
      setSaveState({
        status: "saved",
        message: `Draft version saved: PolicyVersion v${savedVersion.version_number}. It is not active and does not affect runtime until explicitly activated.`
      });
      setReviewState({ status: "idle", message: "Review request not submitted" });
      void loadVersions(policy, undefined, { hydrateEditor: false });
    } catch (error: unknown) {
      const lockMessage = policyDraftLockedErrorMessage(error);
      setSaveState({
        status: "save_error",
        message: lockMessage || errorMessage(error, "Unable to save Policy Studio draft.")
      });
    }
  }

  async function handleCreateNewDraftForChanges() {
    const parsedForSave = parsePolicyDslToPolicyRule(dsl);

    if (!parsedForSave.condition) {
      setSaveState({
        status: "save_error",
        message: parsedForSave.errors.join(" ") || "DSL did not compile."
      });
      return;
    }

    if (parsedForSave.unsupported.length > 0) {
      setSaveState({
        status: "save_error",
        message:
          "Remove unsupported DSL lines before creating a new draft. Unsupported lines are not persisted by the current compiler."
      });
      return;
    }

    if (selectedRuleUnsupportedFields.length > 0) {
      setSaveState({
        status: "save_error",
        message: `Selected backend PolicyRule contains unsupported condition field(s): ${selectedRuleUnsupportedFields.join(
          ", "
        )}. Create a supported draft before saving review changes.`
      });
      return;
    }

    if (!parsedForSave.ruleName.trim()) {
      setSaveState({
        status: "save_error",
        message: "PolicyRule name is required."
      });
      return;
    }

    setSaveState({
      status: "saving",
      message: "Creating new draft for changes"
    });

    try {
      const policy = await ensurePolicyDraft(selectedPolicy, parsedForSave.policyName);
      const draftPayload = buildPolicyVersionDraftPayload({
        condition: parsedForSave.condition,
        draftVersion: null,
        localNote:
          localNote.trim() ||
          "New PolicyVersion draft created from a locked pending-review draft.",
        policy,
        policyName: parsedForSave.policyName,
        rule: selectedRule,
        ruleName: parsedForSave.ruleName
      });
      const savedVersion = await createPolicyVersionDraft(policy.id, draftPayload);

      setDraftVersion(savedVersion);
      setVersionReviewState({ status: "idle" });
      setReviewDiffState({ status: "idle" });
      setVersionsState((current) =>
        current.status === "ready"
          ? {
              status: "ready",
              versions: upsertPolicyVersionRecord(current.versions, savedVersion)
            }
          : current
      );
      setPoliciesState((current) =>
        current.status === "ready"
          ? {
              status: "ready",
              policies: upsertPolicyRecord(current.policies, policy)
            }
          : current
      );
      preserveEditorOnNextRulesLoadRef.current = policy.id;
      savedEditorPolicyRef.current = policy.id;
      setSelectedPolicyId(policy.id);
      hydrateEditorFromPolicyVersion(savedVersion, "draft_version");
      setSaveState({
        status: "saved",
        message: `New draft for changes created: PolicyVersion v${savedVersion.version_number}. Submit for review when ready.`
      });
      setReviewState({ status: "idle", message: "Review request not submitted" });
      void loadVersions(policy, undefined, { hydrateEditor: false });
      void loadVersionReviewState(savedVersion.id);
    } catch (error: unknown) {
      setSaveState({
        status: "save_error",
        message: errorMessage(error, "Unable to create a new PolicyVersion draft.")
      });
    }
  }

  async function handleSubmitReview() {
    const parsedForSubmit = parsePolicyDslToPolicyRule(dsl);
    if (editorSource.kind === "active_version") {
      setReviewState({
        status: "error",
        message: "Create a draft before submitting changes for review."
      });
      return;
    }
    if (editorSource.kind !== "draft_version") {
      setReviewState({
        status: "error",
        message: "Save a draft before submitting for review."
      });
      return;
    }
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
    if (selectedDraftReviewState?.review_status === "pending") {
      setReviewState({
        status: "success",
        message: "Review request already pending."
      });
      return;
    }
    if (saveDisabledReason) {
      setReviewState({ status: "error", message: saveDisabledReason });
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
        message: "Review request submitted. Approval does not activate this version."
      });
      setVersionReviewState({
        status: "ready",
        state: reviewStateFromRequest(request)
      });
      void loadVersionReviewState(selectedDraftVersion.id);
    } catch (error: unknown) {
      const conflictMessage = policyReviewRequestConflictMessage(error);
      if (conflictMessage) {
        setReviewState({
          status: "success",
          message: conflictMessage
        });
        setVersionReviewState({
          status: "ready",
          state: pendingReviewStateForDraft(selectedDraftVersion.id, conflictMessage)
        });
        void loadVersionReviewState(selectedDraftVersion.id);
        return;
      }

      setReviewState({
        status: "error",
        message: errorMessage(error, "Unable to submit PolicyVersion review request.")
      });
    }
  }

  function hydrateEditorFromPolicyVersion(
    version: PolicyVersionRecord,
    kind: "draft_version" | "active_version"
  ) {
    const editorState = policyVersionToEditorState(version);
    const unsupportedFields = unsupportedConditionFields(editorState.condition);

    setSelectedRuleId(editorState.ruleSnapshotId);
    setDsl(editorState.dsl);
    setEditorSource({
      kind,
      versionId: version.id,
      versionNumber: version.version_number
    });
    setSaveState({
      status: unsupportedFields.length > 0 ? "save_error" : "saved",
      message:
        unsupportedFields.length > 0
          ? `PolicyVersion snapshot has unsupported condition field(s): ${unsupportedFields.join(
              ", "
            )}`
          : kind === "draft_version"
            ? `Editing draft PolicyVersion v${version.version_number}. No runtime effect until reviewed and activated.`
            : `Editing active PolicyVersion v${version.version_number} as source baseline. Create a draft before submitting changes for review.`
    });
    setReviewState({ status: "idle", message: "Review request not submitted" });
    localEditorDirtyRef.current = false;
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
            localEditorDirtyRef.current = true;
            setDsl(nextDsl);
            setSaveState({ status: "unsaved", message: "Unsaved local edits" });
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
          onCreateNewDraftForChanges={handleCreateNewDraftForChanges}
          onSaveDraft={handleSaveDraft}
          onSubmitReview={handleSubmitReview}
          onValidate={handleValidate}
          parsed={parsed}
          policyVersionsState={versionsState}
          reviewDiffState={reviewDiffState}
          currentActorState={currentActorState}
          editorSource={editorSource}
          selectedDraftReviewState={selectedDraftReviewState}
          versionReviewState={versionReviewState}
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
  editorSource,
  policiesState,
  rulesState,
  selectedDraftReviewState,
  versionReviewState,
  reviewState,
  saveDisabledReason,
  saveState,
  selectedDraftVersion,
  selectedPolicy,
  selectedRule,
  selectedRuleUnsupportedFields,
  versionsState
}: {
  editorSource: PolicyStudioEditorSource;
  policiesState: PoliciesState;
  rulesState: RulesState;
  selectedDraftReviewState: PolicyVersionReviewStateRecord | null;
  versionReviewState: VersionReviewState;
  reviewState: ReviewState;
  saveDisabledReason: string | null;
  saveState: SaveState;
  selectedDraftVersion: PolicyVersionRecord | null;
  selectedPolicy: PolicyRecord | null;
  selectedRule: PolicyRuleRecord | null;
  selectedRuleUnsupportedFields: string[];
  versionsState: VersionsState;
}): PolicyValidationMessage[] {
  const messages: PolicyValidationMessage[] = [];

  if (policiesState.status === "error") {
    messages.push({
      tone: "attention",
      text: `Backend unavailable for GET /policies: ${policiesState.message}`
    });
  }

  if (rulesState.status === "error") {
    messages.push({
      tone: "attention",
      text: `Backend unavailable for GET /policies/{policy_id}/rules: ${rulesState.message}`
    });
  }

  if (versionsState.status === "error") {
    messages.push({
      tone: "attention",
      text: `Backend unavailable for GET /policies/{policy_id}/versions: ${versionsState.message}`
    });
  }

  if (versionReviewState.status === "error") {
    messages.push({
      tone: "attention",
      text: versionReviewState.message
    });
  }

  messages.push({
    tone: "info",
    text: selectedPolicy
      ? `Selected Policy: ${selectedPolicy.id} (${selectedPolicy.status})`
      : "No persisted Policy selected; Save draft will create a draft Policy container"
  });
  messages.push({
    tone: "info",
    text: selectedRule
      ? `Selected PolicyRule: ${selectedRule.id}. Save draft snapshots this source rule without patching it.`
      : "This draft will save a generated rule snapshot."
  });
  messages.push(editorSourceMessage(editorSource));

  if (selectedDraftVersion) {
    messages.push({
      tone: "success",
      text: `Draft PolicyVersion v${selectedDraftVersion.version_number}: ${selectedDraftVersion.id} (not active). No runtime effect until reviewed and activated.`
    });
    if (selectedDraftVersion.rule_snapshots.length > 1) {
      messages.push({
        tone: "info",
        text: `Selected rule snapshot: first of ${selectedDraftVersion.rule_snapshots.length} deterministic rule snapshots.`
      });
    }
  }

  if (selectedDraftReviewState?.review_status === "pending") {
    messages.push({
      tone: "info",
      text: "Pending review: This draft is locked while review is pending. Create a new draft for additional changes."
    });
  } else if (selectedDraftReviewState) {
    messages.push({
      tone:
        selectedDraftReviewState.review_status === "not_submitted"
          ? "info"
          : "success",
      text: `Review state: ${reviewStatusLabel(
        selectedDraftReviewState.review_status
      )}. ${selectedDraftReviewState.message}`
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
      tone: "attention",
      text: "Selected Policy is active. Save draft creates a draft PolicyVersion; runtime still uses the active version or fallback until explicit activation."
    });
  }

  if (selectedRuleUnsupportedFields.length > 0) {
    messages.push({
      tone: "blocking",
      text: `Selected backend rule has unsupported fields not represented in this editor: ${selectedRuleUnsupportedFields.join(
        ", "
      )}`
    });
  }

  if (saveDisabledReason) {
    messages.push({
      tone: isPendingReviewLockMessage(saveDisabledReason) ? "info" : "blocking",
      text: isPendingReviewLockMessage(saveDisabledReason)
        ? saveDisabledReason
        : `Save draft blocked: ${saveDisabledReason}`
    });
  }

  if (saveState.status === "saved") {
    messages.push({ tone: "success", text: saveState.message });
  }
  if (saveState.status === "save_error") {
    messages.push({
      tone: isPendingReviewLockMessage(saveState.message) ? "info" : "blocking",
      text: saveState.message
    });
  }
  if (reviewState.status === "success") {
    messages.push({ tone: "success", text: reviewState.message });
  }
  if (reviewState.status === "error") {
    messages.push({ tone: "blocking", text: reviewState.message });
  }

  return messages;
}

function upsertPolicyRecord(policies: PolicyRecord[], policy: PolicyRecord) {
  const existingIndex = policies.findIndex((item) => item.id === policy.id);
  if (existingIndex === -1) {
    return [policy, ...policies];
  }

  return policies.map((item) => (item.id === policy.id ? policy : item));
}

function upsertPolicyVersionRecord(
  versions: PolicyVersionRecord[],
  version: PolicyVersionRecord
) {
  const existingIndex = versions.findIndex((item) => item.id === version.id);
  if (existingIndex === -1) {
    return [...versions, version].sort(
      (left, right) => left.version_number - right.version_number
    );
  }

  return versions.map((item) => (item.id === version.id ? version : item));
}

function editorSourceMessage(editorSource: PolicyStudioEditorSource) {
  if (editorSource.kind === "draft_version") {
    return {
      tone: "success" as const,
      text: `Editor source: Editing draft PolicyVersion v${editorSource.versionNumber}. Not active. No runtime effect until reviewed and activated.`
    };
  }
  if (editorSource.kind === "active_version") {
    return {
      tone: "info" as const,
      text: `Editor source: Editing active PolicyVersion v${editorSource.versionNumber} as baseline. Create a draft before submitting changes for review.`
    };
  }
  if (editorSource.kind === "live_fallback") {
    return {
      tone: "attention" as const,
      text: "Editor source: Live PolicyRule fallback. Save a draft before submitting for review."
    };
  }
  return {
    tone: "attention" as const,
    text: "Editor source: Local unsaved draft. Save a draft before submitting for review."
  };
}

function policyVersionToEditorState(version: PolicyVersionRecord) {
  const ruleSnapshot = version.rule_snapshots[0] || {};
  const policyName =
    typeof version.policy_snapshot.name === "string"
      ? version.policy_snapshot.name
      : `policy_version_${version.version_number}`;
  const condition = parseRuleSnapshotCondition(version);

  return {
    condition,
    dsl: conditionToDsl(policyName, condition),
    ruleSnapshotId:
      typeof ruleSnapshot.id === "string" ? ruleSnapshot.id : "snapshot-rule",
    ruleSnapshotName:
      typeof ruleSnapshot.name === "string" ? ruleSnapshot.name : "snapshot_rule"
  };
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
  if (condition && typeof condition === "object" && !Array.isArray(condition)) {
    return stableCondition(condition as PolicyCondition);
  }
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

function reviewStateFromRequest(
  request: PolicyVersionReviewRequestRecord
): PolicyVersionReviewStateRecord {
  return {
    can_submit_review: request.status !== "pending",
    decided_at: request.decided_at,
    latest_review_request_id: request.id,
    message:
      request.status === "pending"
        ? "Review request pending. Approval does not activate this version."
        : "Review request submitted. Approval does not activate this version.",
    policy_version_id: request.policy_version_id,
    requested_at: request.created_at,
    reviewer_actor_id: request.reviewer_actor_id,
    review_status: request.status
  };
}

function pendingReviewStateForDraft(
  policyVersionId: string,
  message: string
): PolicyVersionReviewStateRecord {
  return {
    can_submit_review: false,
    decided_at: null,
    latest_review_request_id: null,
    message,
    policy_version_id: policyVersionId,
    requested_at: null,
    reviewer_actor_id: null,
    review_status: "pending"
  };
}

function reviewStatusLabel(status: PolicyVersionReviewStateRecord["review_status"]) {
  if (status === "not_submitted") {
    return "Not submitted";
  }
  if (status === "pending") {
    return "Pending review";
  }
  if (status === "approved") {
    return "Approved";
  }
  if (status === "rejected") {
    return "Rejected";
  }
  return "Canceled";
}

function pendingDraftLockedMessage() {
  return "This draft is locked because a review is pending. Create a new draft for additional changes.";
}

function isPendingReviewLockMessage(message: string | null | undefined) {
  if (!message) {
    return false;
  }
  return (
    message.includes("review is pending") ||
    message.includes("pending review") ||
    message.includes("already pending")
  );
}

function titleFromSlug(value: string) {
  return slugifyPolicyName(value)
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function errorMessage(error: unknown, fallback: string) {
  if (error instanceof ApiRequestError) {
    const detail =
      typeof error.detail === "object" &&
      error.detail !== null &&
      "detail" in error.detail &&
      typeof error.detail.detail === "string"
        ? error.detail.detail
        : null;
    if (detail?.includes("Direct live Policy")) {
      return `${detail} Use Save draft to create a reviewed PolicyVersion.`;
    }
    return error.message;
  }

  return error instanceof Error ? error.message : fallback;
}

function policyDraftLockedErrorMessage(error: unknown) {
  if (!(error instanceof ApiRequestError) || error.status !== 409) {
    return null;
  }

  const detailText = apiErrorDetailText(error.detail);
  if (
    detailText.includes("Cannot update a draft PolicyVersion") &&
    detailText.includes("pending")
  ) {
    return pendingDraftLockedMessage();
  }

  return null;
}

function policyReviewRequestConflictMessage(error: unknown) {
  if (!(error instanceof ApiRequestError) || error.status !== 409) {
    return null;
  }

  const detailText = apiErrorDetailText(error.detail).toLowerCase();
  if (
    detailText.includes("pending") ||
    detailText.includes("already") ||
    detailText.includes("review request")
  ) {
    return "Review request already pending.";
  }

  return "A review request could not be created because this draft has a conflicting review state. Review state was refreshed.";
}

function apiErrorDetailText(detail: unknown): string {
  if (typeof detail === "string") {
    return detail;
  }
  if (
    detail &&
    typeof detail === "object" &&
    "detail" in detail &&
    typeof detail.detail === "string"
  ) {
    return detail.detail;
  }
  try {
    return JSON.stringify(detail);
  } catch {
    return "";
  }
}
