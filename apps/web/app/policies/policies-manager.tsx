"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { ApiRequestError, getApiBaseUrl } from "../lib/api";
import {
  POLICY_RULE_ACCESS_GRANT_STATUSES,
  POLICY_RULE_CAPABILITY_STATUSES,
  POLICY_RULE_CAPABILITY_TYPES,
  POLICY_RULE_CHECK_OUTCOMES,
  POLICY_RULE_CHECK_TARGET_TYPES,
  POLICY_RULE_CHECK_TYPES,
  POLICY_RULE_DATA_CLASSIFICATIONS,
  POLICY_RULE_DATA_USAGE_REVIEW_STATUSES,
  POLICY_RULE_DECISIONS,
  POLICY_RULE_ENVIRONMENTS,
  POLICY_RULE_MODEL_PROVIDERS,
  POLICY_RULE_MODEL_PROVIDER_TYPES,
  POLICY_RULE_MODEL_STATUSES,
  POLICY_RULE_MODEL_TYPES,
  POLICY_RULE_RISK_LEVELS,
  POLICY_RULE_SOURCE_STATUSES,
  POLICY_STATUSES,
  PolicyPayload,
  PolicyRecord,
  PolicyRuleDecision,
  PolicyRulePayload,
  PolicyRuleRecord,
  PolicyStatus,
  createPolicy,
  createPolicyRule,
  fetchPolicies,
  fetchPolicyRulesForPolicy,
  updatePolicy,
  updatePolicyRule
} from "../lib/policies";

type PoliciesState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; policies: PolicyRecord[] };

type RulesState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; rules: PolicyRuleRecord[] };

type FormState = {
  name: string;
  description: string;
  status: PolicyStatus;
};

type BooleanField = "" | "true" | "false";

type RuleFormState = {
  name: string;
  description: string;
  decision: PolicyRuleDecision;
  reason: string;
  agentId: string;
  toolName: string;
  environment: string;
  riskLevel: string;
  actionType: string;
  capabilityId: string;
  sourceIds: string;
  modelId: string;
  purpose: string;
  dataClassification: string;
  containsPersonalData: BooleanField;
  containsSensitiveData: BooleanField;
  capabilityType: string;
  capabilityStatus: string;
  sourceStatus: string;
  sourceDataClassification: string;
  sourceContainsPersonalData: BooleanField;
  sourceContainsSensitiveData: BooleanField;
  modelType: string;
  modelProvider: string;
  modelProviderType: string;
  modelStatus: string;
  accessGrantStatus: string;
  dataUsageReviewStatus: string;
  dataUsageAllowedPurpose: string;
  dataUsageProhibitedPurpose: string;
  checkType: string;
  checkOutcome: string;
  checkTargetType: string;
  checkTargetId: string;
  checkToolId: string;
  checkMinConfidence: string;
};

type SaveMessage =
  | { status: "success"; message: string }
  | { status: "error"; message: string }
  | null;

const emptyCreateForm: FormState = {
  name: "",
  description: "",
  status: "draft"
};

const emptyRuleForm: RuleFormState = {
  name: "",
  description: "",
  decision: "require_human_review",
  reason: "",
  agentId: "",
  toolName: "",
  environment: "",
  riskLevel: "",
  actionType: "",
  capabilityId: "",
  sourceIds: "",
  modelId: "",
  purpose: "",
  dataClassification: "",
  containsPersonalData: "",
  containsSensitiveData: "",
  capabilityType: "",
  capabilityStatus: "",
  sourceStatus: "",
  sourceDataClassification: "",
  sourceContainsPersonalData: "",
  sourceContainsSensitiveData: "",
  modelType: "",
  modelProvider: "",
  modelProviderType: "",
  modelStatus: "",
  accessGrantStatus: "",
  dataUsageReviewStatus: "",
  dataUsageAllowedPurpose: "",
  dataUsageProhibitedPurpose: "",
  checkType: "",
  checkOutcome: "",
  checkTargetType: "",
  checkTargetId: "",
  checkToolId: "",
  checkMinConfidence: ""
};

const policyColumns = ["Name", "Status", "Description", "Updated", "ID", "View"];
const ruleColumns = ["Name", "Decision", "Check condition", "Updated", "ID", "Edit"];

type ConditionObject = Record<string, string | boolean | number | string[]>;

function formatValue(value: string | null | undefined) {
  if (!value) {
    return "Not set";
  }

  return value
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function formatTimestamp(value: string) {
  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleString();
}

function formFromPolicy(policy: PolicyRecord): FormState {
  return {
    name: policy.name,
    description: policy.description || "",
    status: policy.status
  };
}

function payloadFromForm(form: FormState): PolicyPayload {
  const description = form.description.trim();

  return {
    name: form.name.trim(),
    description: description ? description : null,
    status: form.status
  };
}

function policyChanged(policy: PolicyRecord, form: FormState) {
  const payload = payloadFromForm(form);

  return (
    payload.name !== policy.name ||
    payload.description !== policy.description ||
    payload.status !== policy.status
  );
}

function parseCondition(condition: string): Record<string, unknown> {
  try {
    const parsed = JSON.parse(condition) as unknown;
    return parsed && typeof parsed === "object" && !Array.isArray(parsed)
      ? (parsed as Record<string, unknown>)
      : {};
  } catch {
    return {};
  }
}

function conditionString(condition: Record<string, unknown>, key: string) {
  const value = condition[key];
  return typeof value === "string" ? value : "";
}

function conditionBoolean(condition: Record<string, unknown>, key: string): BooleanField {
  const value = condition[key];
  if (value === true) {
    return "true";
  }
  if (value === false) {
    return "false";
  }
  return "";
}

function conditionSourceIds(condition: Record<string, unknown>) {
  const sourceIds = condition.source_ids;
  if (Array.isArray(sourceIds)) {
    return sourceIds
      .filter((item): item is string => typeof item === "string")
      .join(", ");
  }
  return conditionString(condition, "source_id");
}

function formFromRule(rule: PolicyRuleRecord): RuleFormState {
  const condition = parseCondition(rule.condition);
  const decision = POLICY_RULE_DECISIONS.includes(
    conditionString(condition, "decision") as PolicyRuleDecision
  )
    ? (conditionString(condition, "decision") as PolicyRuleDecision)
    : "require_human_review";

  return {
    ...emptyRuleForm,
    name: rule.name,
    description: rule.description || "",
    decision,
    reason: conditionString(condition, "reason"),
    agentId: conditionString(condition, "agent_id"),
    toolName: conditionString(condition, "tool_name"),
    environment: conditionString(condition, "environment"),
    riskLevel: conditionString(condition, "risk_level"),
    actionType: conditionString(condition, "action_type"),
    capabilityId: conditionString(condition, "capability_id"),
    sourceIds: conditionSourceIds(condition),
    modelId: conditionString(condition, "model_id"),
    purpose: conditionString(condition, "purpose"),
    dataClassification: conditionString(condition, "data_classification"),
    containsPersonalData: conditionBoolean(condition, "contains_personal_data"),
    containsSensitiveData: conditionBoolean(condition, "contains_sensitive_data"),
    capabilityType: conditionString(condition, "capability_type"),
    capabilityStatus: conditionString(condition, "capability_status"),
    sourceStatus: conditionString(condition, "source_status"),
    sourceDataClassification: conditionString(condition, "source_data_classification"),
    sourceContainsPersonalData: conditionBoolean(
      condition,
      "source_contains_personal_data"
    ),
    sourceContainsSensitiveData: conditionBoolean(
      condition,
      "source_contains_sensitive_data"
    ),
    modelType: conditionString(condition, "model_type"),
    modelProvider: conditionString(condition, "model_provider"),
    modelProviderType: conditionString(condition, "model_provider_type"),
    modelStatus: conditionString(condition, "model_status"),
    accessGrantStatus: conditionString(condition, "access_grant_status"),
    dataUsageReviewStatus: conditionString(condition, "data_usage_review_status"),
    dataUsageAllowedPurpose: conditionString(condition, "data_usage_allowed_purpose"),
    dataUsageProhibitedPurpose: conditionString(
      condition,
      "data_usage_prohibited_purpose"
    ),
    checkType: conditionString(condition, "check_type"),
    checkOutcome: conditionString(condition, "check_outcome"),
    checkTargetType: conditionString(condition, "check_target_type"),
    checkTargetId: conditionString(condition, "check_target_id"),
    checkToolId: conditionString(condition, "check_tool_id"),
    checkMinConfidence:
      typeof condition.check_min_confidence === "number"
        ? String(condition.check_min_confidence)
        : ""
  };
}

function setOptionalString(
  condition: ConditionObject,
  key: string,
  value: string
) {
  const normalized = value.trim();
  if (normalized) {
    condition[key] = normalized;
  }
}

function setOptionalBoolean(
  condition: ConditionObject,
  key: string,
  value: BooleanField
) {
  if (value === "true") {
    condition[key] = true;
  }
  if (value === "false") {
    condition[key] = false;
  }
}

function sourceIdValues(sourceIds: string) {
  return sourceIds
    .split(",")
    .map((value) => value.trim())
    .filter(Boolean);
}

function buildRuleCondition(form: RuleFormState):
  | { condition: ConditionObject; error: null }
  | { condition: null; error: string } {
  const reason = form.reason.trim();
  if (!reason) {
    return { condition: null, error: "PolicyRule condition reason is required." };
  }

  const condition: ConditionObject = {
    decision: form.decision,
    reason
  };

  setOptionalString(condition, "agent_id", form.agentId);
  setOptionalString(condition, "tool_name", form.toolName);
  setOptionalString(condition, "environment", form.environment);
  setOptionalString(condition, "risk_level", form.riskLevel);
  setOptionalString(condition, "action_type", form.actionType);
  setOptionalString(condition, "capability_id", form.capabilityId);

  const sourceIds = sourceIdValues(form.sourceIds);
  if (sourceIds.length === 1) {
    condition.source_id = sourceIds[0];
  } else if (sourceIds.length > 1) {
    condition.source_ids = sourceIds;
  }

  setOptionalString(condition, "model_id", form.modelId);
  setOptionalString(condition, "purpose", form.purpose);
  setOptionalString(condition, "data_classification", form.dataClassification);
  setOptionalBoolean(
    condition,
    "contains_personal_data",
    form.containsPersonalData
  );
  setOptionalBoolean(
    condition,
    "contains_sensitive_data",
    form.containsSensitiveData
  );
  setOptionalString(condition, "capability_type", form.capabilityType);
  setOptionalString(condition, "capability_status", form.capabilityStatus);
  setOptionalString(condition, "source_status", form.sourceStatus);
  setOptionalString(
    condition,
    "source_data_classification",
    form.sourceDataClassification
  );
  setOptionalBoolean(
    condition,
    "source_contains_personal_data",
    form.sourceContainsPersonalData
  );
  setOptionalBoolean(
    condition,
    "source_contains_sensitive_data",
    form.sourceContainsSensitiveData
  );
  setOptionalString(condition, "model_type", form.modelType);
  setOptionalString(condition, "model_provider", form.modelProvider);
  setOptionalString(condition, "model_provider_type", form.modelProviderType);
  setOptionalString(condition, "model_status", form.modelStatus);
  setOptionalString(condition, "access_grant_status", form.accessGrantStatus);
  setOptionalString(
    condition,
    "data_usage_review_status",
    form.dataUsageReviewStatus
  );
  setOptionalString(
    condition,
    "data_usage_allowed_purpose",
    form.dataUsageAllowedPurpose
  );
  setOptionalString(
    condition,
    "data_usage_prohibited_purpose",
    form.dataUsageProhibitedPurpose
  );
  setOptionalString(condition, "check_type", form.checkType);
  setOptionalString(condition, "check_outcome", form.checkOutcome);
  setOptionalString(condition, "check_target_type", form.checkTargetType);
  setOptionalString(condition, "check_target_id", form.checkTargetId);
  setOptionalString(condition, "check_tool_id", form.checkToolId);

  const confidence = form.checkMinConfidence.trim();
  if (confidence) {
    const numericConfidence = Number(confidence);
    if (
      !Number.isFinite(numericConfidence) ||
      numericConfidence < 0 ||
      numericConfidence > 1
    ) {
      return {
        condition: null,
        error: "check_min_confidence must be a number between 0 and 1."
      };
    }
    condition.check_min_confidence = numericConfidence;
  }

  return { condition, error: null };
}

function payloadFromRuleForm(
  policy: PolicyRecord,
  form: RuleFormState
):
  | { payload: PolicyRulePayload; error: null }
  | { payload: null; error: string } {
  const name = form.name.trim();
  if (!name) {
    return { payload: null, error: "PolicyRule name is required." };
  }

  const result = buildRuleCondition(form);
  if (result.error) {
    return { payload: null, error: result.error };
  }

  const description = form.description.trim();
  return {
    payload: {
      policy_id: policy.id,
      name,
      description: description ? description : null,
      condition: JSON.stringify(result.condition)
    },
    error: null
  };
}

function ruleChanged(rule: PolicyRuleRecord, policy: PolicyRecord, form: RuleFormState) {
  const result = payloadFromRuleForm(policy, form);
  if (!result.payload) {
    return true;
  }
  const payload = result.payload;

  return (
    payload.name !== rule.name ||
    payload.description !== rule.description ||
    payload.condition !== rule.condition
  );
}

function conditionPreview(form: RuleFormState) {
  const result = buildRuleCondition(form);
  if (result.error) {
    return "Complete required condition fields to preview deterministic JSON.";
  }
  return JSON.stringify(result.condition, null, 2);
}

function ruleDecision(rule: PolicyRuleRecord) {
  return conditionString(parseCondition(rule.condition), "decision");
}

function ruleCheckSummary(rule: PolicyRuleRecord) {
  const condition = parseCondition(rule.condition);
  const checkType = conditionString(condition, "check_type");
  const outcome = conditionString(condition, "check_outcome");
  const targetType = conditionString(condition, "check_target_type");

  if (!checkType && !outcome && !targetType) {
    return "No check outcome match";
  }

  return [checkType, outcome, targetType].filter(Boolean).join(" / ");
}

function detailMessage(detail: unknown): string | null {
  if (!detail) {
    return null;
  }

  if (typeof detail === "string") {
    return detail;
  }

  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => detailMessage(item))
      .filter((item): item is string => Boolean(item));
    return messages.length > 0 ? messages.join(" ") : null;
  }

  if (typeof detail === "object") {
    const detailObject = detail as Record<string, unknown>;

    if ("detail" in detailObject) {
      return detailMessage(detailObject.detail);
    }

    if (typeof detailObject.msg === "string") {
      const location = Array.isArray(detailObject.loc)
        ? detailObject.loc.join(".")
        : null;
      return location ? `${location}: ${detailObject.msg}` : detailObject.msg;
    }
  }

  return null;
}

function errorMessage(error: unknown, fallback: string) {
  if (error instanceof ApiRequestError) {
    const message = detailMessage(error.detail);
    return message || error.message;
  }

  return error instanceof Error ? error.message : fallback;
}

export function PoliciesManager() {
  const [state, setState] = useState<PoliciesState>({ status: "loading" });
  const [rulesState, setRulesState] = useState<RulesState>({ status: "idle" });
  const [selectedPolicyId, setSelectedPolicyId] = useState<string | null>(null);
  const [selectedRuleId, setSelectedRuleId] = useState<string | null>(null);
  const [createForm, setCreateForm] = useState<FormState>(emptyCreateForm);
  const [editForm, setEditForm] = useState<FormState>(emptyCreateForm);
  const [ruleForm, setRuleForm] = useState<RuleFormState>(emptyRuleForm);
  const [saveMessage, setSaveMessage] = useState<SaveMessage>(null);
  const [ruleMessage, setRuleMessage] = useState<SaveMessage>(null);
  const [creating, setCreating] = useState(false);
  const [updating, setUpdating] = useState(false);
  const [savingRule, setSavingRule] = useState(false);

  const selectedPolicy = useMemo(() => {
    if (state.status !== "ready" || !selectedPolicyId) {
      return null;
    }

    return (
      state.policies.find((policy) => policy.id === selectedPolicyId) || null
    );
  }, [selectedPolicyId, state]);

  const selectedRule = useMemo(() => {
    if (rulesState.status !== "ready" || !selectedRuleId) {
      return null;
    }

    return rulesState.rules.find((rule) => rule.id === selectedRuleId) || null;
  }, [rulesState, selectedRuleId]);

  const loadPolicies = useCallback(async (signal?: AbortSignal) => {
    setState({ status: "loading" });

    try {
      const policies = await fetchPolicies(signal);
      setState({ status: "ready", policies });
    } catch (error: unknown) {
      if (signal?.aborted) {
        return;
      }

      setState({
        status: "error",
        message: errorMessage(
          error,
          "Unable to load Policy records from the backend."
        )
      });
    }
  }, []);

  const loadRules = useCallback(
    async (policyId: string, signal?: AbortSignal) => {
      setRulesState({ status: "loading" });

      try {
        const rules = await fetchPolicyRulesForPolicy(policyId, signal);
        setRulesState({ status: "ready", rules });
      } catch (error: unknown) {
        if (signal?.aborted) {
          return;
        }

        setRulesState({
          status: "error",
          message: errorMessage(
            error,
            "Unable to load PolicyRule records from the backend."
          )
        });
      }
    },
    []
  );

  useEffect(() => {
    const controller = new AbortController();

    void loadPolicies(controller.signal);

    return () => {
      controller.abort();
    };
  }, [loadPolicies]);

  useEffect(() => {
    if (state.status !== "ready") {
      return;
    }

    if (state.policies.length === 0) {
      setSelectedPolicyId(null);
      setEditForm(emptyCreateForm);
      return;
    }

    const selected =
      state.policies.find((policy) => policy.id === selectedPolicyId) ||
      state.policies[0];
    setSelectedPolicyId(selected.id);
    setEditForm(formFromPolicy(selected));
  }, [selectedPolicyId, state]);

  useEffect(() => {
    setSelectedRuleId(null);
    setRuleForm(emptyRuleForm);
    setRuleMessage(null);

    if (!selectedPolicyId) {
      setRulesState({ status: "idle" });
      return;
    }

    const controller = new AbortController();
    void loadRules(selectedPolicyId, controller.signal);

    return () => {
      controller.abort();
    };
  }, [loadRules, selectedPolicyId]);

  async function handleCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setCreating(true);
    setSaveMessage(null);

    try {
      const created = await createPolicy(payloadFromForm(createForm));
      setState((currentState) => {
        if (currentState.status !== "ready") {
          return { status: "ready", policies: [created] };
        }

        return {
          status: "ready",
          policies: [...currentState.policies, created]
        };
      });
      setCreateForm(emptyCreateForm);
      setSelectedPolicyId(created.id);
      setEditForm(formFromPolicy(created));
      setSaveMessage({
        status: "success",
        message: "Policy created. PolicyRules define executable conditions."
      });
    } catch (error: unknown) {
      setSaveMessage({
        status: "error",
        message: errorMessage(error, "Unable to create Policy.")
      });
    } finally {
      setCreating(false);
    }
  }

  async function handleUpdate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!selectedPolicy) {
      return;
    }

    if (!policyChanged(selectedPolicy, editForm)) {
      setSaveMessage({
        status: "error",
        message: "No Policy fields changed."
      });
      return;
    }

    setUpdating(true);
    setSaveMessage(null);

    try {
      const updated = await updatePolicy(selectedPolicy.id, payloadFromForm(editForm));
      setState((currentState) => {
        if (currentState.status !== "ready") {
          return { status: "ready", policies: [updated] };
        }

        return {
          status: "ready",
          policies: currentState.policies.map((policy) =>
            policy.id === updated.id ? updated : policy
          )
        };
      });
      setEditForm(formFromPolicy(updated));
      setSaveMessage({
        status: "success",
        message:
          updated.status === "active"
            ? "Policy saved. Active policies can affect future PolicyDecision outcomes."
            : "Policy saved."
      });
    } catch (error: unknown) {
      setSaveMessage({
        status: "error",
        message: errorMessage(error, "Unable to update Policy.")
      });
    } finally {
      setUpdating(false);
    }
  }

  async function handleSaveRule(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!selectedPolicy) {
      setRuleMessage({
        status: "error",
        message: "Select a Policy before saving PolicyRules."
      });
      return;
    }

    const result = payloadFromRuleForm(selectedPolicy, ruleForm);
    if (!result.payload) {
      setRuleMessage({ status: "error", message: result.error });
      return;
    }
    const rulePayload = result.payload;

    if (selectedRule && !ruleChanged(selectedRule, selectedPolicy, ruleForm)) {
      setRuleMessage({
        status: "error",
        message: "No PolicyRule fields changed."
      });
      return;
    }

    setSavingRule(true);
    setRuleMessage(null);

    try {
      const savedRule = selectedRule
        ? await updatePolicyRule(selectedRule.id, {
            name: rulePayload.name,
            description: rulePayload.description,
            condition: rulePayload.condition
          })
        : await createPolicyRule(rulePayload);

      setRulesState((currentState) => {
        if (currentState.status !== "ready") {
          return { status: "ready", rules: [savedRule] };
        }

        const existingRule = currentState.rules.some(
          (rule) => rule.id === savedRule.id
        );
        return {
          status: "ready",
          rules: existingRule
            ? currentState.rules.map((rule) =>
                rule.id === savedRule.id ? savedRule : rule
              )
            : [...currentState.rules, savedRule]
        };
      });
      setSelectedRuleId(savedRule.id);
      setRuleForm(formFromRule(savedRule));
      setRuleMessage({
        status: "success",
        message: selectedRule
          ? "PolicyRule saved. Future Runtime Gateway decisions may use this condition."
          : "PolicyRule created. Future Runtime Gateway decisions may use this condition."
      });
    } catch (error: unknown) {
      setRuleMessage({
        status: "error",
        message: errorMessage(error, "Unable to save PolicyRule.")
      });
    } finally {
      setSavingRule(false);
    }
  }

  function handleSelect(policy: PolicyRecord) {
    setSelectedPolicyId(policy.id);
    setEditForm(formFromPolicy(policy));
    setSaveMessage(null);
  }

  function handleSelectRule(rule: PolicyRuleRecord) {
    setSelectedRuleId(rule.id);
    setRuleForm(formFromRule(rule));
    setRuleMessage(null);
  }

  function handleNewRule() {
    setSelectedRuleId(null);
    setRuleForm(emptyRuleForm);
    setRuleMessage(null);
  }

  return (
    <div className="policy-workspace">
      <section className="policy-boundary" aria-label="Policy UI scope">
        <strong>Policy lifecycle and constrained rule editing</strong>
        <p>
          PolicyRules define executable conditions. This UI uses structured
          fields for deterministic request, inventory, and check outcome
          matching instead of a generic policy language.
        </p>
      </section>

      {saveMessage ? (
        <div
          className={`form-message ${saveMessage.status}`}
          role={saveMessage.status === "error" ? "alert" : "status"}
        >
          {saveMessage.message}
        </div>
      ) : null}

      <div className="policy-manager-grid">
        <PoliciesTable
          selectedPolicyId={selectedPolicyId}
          state={state}
          onSelect={handleSelect}
        />

        <div className="policy-form-stack">
          <PolicyForm
            form={createForm}
            isSaving={creating}
            mode="create"
            onChange={setCreateForm}
            onSubmit={handleCreate}
          />

          <PolicyForm
            form={editForm}
            isSaving={updating}
            mode="edit"
            onChange={setEditForm}
            onSubmit={handleUpdate}
            policy={selectedPolicy}
          />
        </div>
      </div>

      <PolicyRulesSection
        form={ruleForm}
        isSaving={savingRule}
        message={ruleMessage}
        onChange={setRuleForm}
        onNewRule={handleNewRule}
        onSelectRule={handleSelectRule}
        onSubmit={handleSaveRule}
        policy={selectedPolicy}
        rulesState={rulesState}
        selectedRuleId={selectedRuleId}
      />
    </div>
  );
}

function PoliciesTable({
  onSelect,
  selectedPolicyId,
  state
}: {
  onSelect: (policy: PolicyRecord) => void;
  selectedPolicyId: string | null;
  state: PoliciesState;
}) {
  if (state.status === "loading") {
    return (
      <section className="data-panel" aria-live="polite">
        <div className="state-message">
          <strong>Loading policies</strong>
          <p>Requesting Policy records from {getApiBaseUrl()}.</p>
        </div>
      </section>
    );
  }

  if (state.status === "error") {
    return (
      <section className="data-panel" role="alert">
        <div className="state-message error">
          <strong>Unable to load policies</strong>
          <p>{state.message}</p>
          <p>
            Check that the backend is running and that
            NEXT_PUBLIC_AGCP_API_BASE_URL points to the API base URL.
          </p>
        </div>
      </section>
    );
  }

  if (state.policies.length === 0) {
    return (
      <section className="data-panel">
        <div className="state-message">
          <strong>No policies found</strong>
          <p>
            Create a Policy lifecycle record before adding PolicyRules through
            the constrained rule editor.
          </p>
        </div>
      </section>
    );
  }

  return (
    <section className="data-panel" aria-label="Policy list">
      <div className="table-scroll">
        <table className="data-table policy-table">
          <thead>
            <tr>
              {policyColumns.map((column) => (
                <th key={column} scope="col">
                  {column}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {state.policies.map((policy) => (
              <tr
                className={
                  policy.id === selectedPolicyId ? "selected-row" : undefined
                }
                key={policy.id}
              >
                <td>{policy.name}</td>
                <td>
                  <span className={`table-pill policy-${policy.status}`}>
                    {formatValue(policy.status)}
                  </span>
                </td>
                <td>{formatValue(policy.description)}</td>
                <td>{formatTimestamp(policy.updated_at)}</td>
                <td className="id-cell">{policy.id}</td>
                <td>
                  <button
                    className="table-action-button edit"
                    onClick={() => onSelect(policy)}
                    type="button"
                  >
                    View
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function PolicyForm({
  form,
  isSaving,
  mode,
  onChange,
  onSubmit,
  policy
}: {
  form: FormState;
  isSaving: boolean;
  mode: "create" | "edit";
  onChange: (form: FormState) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  policy?: PolicyRecord | null;
}) {
  const isEdit = mode === "edit";
  const disabled = isSaving || (isEdit && !policy);

  return (
    <section className="policy-form-panel">
      <header className="policy-form-header">
        <div>
          <strong>{isEdit ? "Edit selected Policy" : "Create Policy"}</strong>
          <p>
            {isEdit
              ? "Update lifecycle fields. PolicyRules are edited below."
              : "Create the lifecycle container before adding executable PolicyRules."}
          </p>
        </div>
        {isEdit && policy ? (
          <span className={`table-pill policy-${policy.status}`}>
            {formatValue(policy.status)}
          </span>
        ) : null}
      </header>

      {isEdit && !policy ? (
        <div className="state-message compact">
          <strong>No Policy selected</strong>
          <p>Select a Policy from the list before editing lifecycle fields.</p>
        </div>
      ) : (
        <form className="policy-form" onSubmit={onSubmit}>
          <label>
            <span>Name</span>
            <input
              disabled={disabled}
              onChange={(event) =>
                onChange({ ...form, name: event.target.value })
              }
              required
              type="text"
              value={form.name}
            />
          </label>

          <label>
            <span>Description</span>
            <textarea
              disabled={disabled}
              onChange={(event) =>
                onChange({ ...form, description: event.target.value })
              }
              value={form.description}
            />
          </label>

          <label>
            <span>Status</span>
            <select
              disabled={disabled}
              onChange={(event) =>
                onChange({
                  ...form,
                  status: event.target.value as PolicyStatus
                })
              }
              value={form.status}
            >
              {POLICY_STATUSES.map((status) => (
                <option key={status} value={status}>
                  {formatValue(status)}
                </option>
              ))}
            </select>
          </label>

          <div className="policy-form-warning">
            Active policies may affect future PolicyDecision records. PolicyRule
            edits below can affect future Runtime Gateway decisions.
          </div>

          <button className="secondary-action" disabled={disabled} type="submit">
            {isSaving
              ? isEdit
                ? "Saving Policy"
                : "Creating Policy"
              : isEdit
                ? "Save Policy"
                : "Create Policy"}
          </button>
        </form>
      )}
    </section>
  );
}

function PolicyRulesSection({
  form,
  isSaving,
  message,
  onChange,
  onNewRule,
  onSelectRule,
  onSubmit,
  policy,
  rulesState,
  selectedRuleId
}: {
  form: RuleFormState;
  isSaving: boolean;
  message: SaveMessage;
  onChange: (form: RuleFormState) => void;
  onNewRule: () => void;
  onSelectRule: (rule: PolicyRuleRecord) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  policy: PolicyRecord | null;
  rulesState: RulesState;
  selectedRuleId: string | null;
}) {
  return (
    <section className="policy-rule-workspace" aria-label="PolicyRule editor">
      <header className="policy-rule-header">
        <div>
          <strong>PolicyRule conditions</strong>
          <p>
            Constrained authoring for deterministic PolicyRule fields, including
            check_* outcome matching.
          </p>
        </div>
        <button
          className="secondary-action compact-action"
          disabled={!policy || isSaving}
          onClick={onNewRule}
          type="button"
        >
          New PolicyRule
        </button>
      </header>

      <div className="policy-rule-warning">
        Changing PolicyRules can affect future Runtime Gateway decisions.
        CheckResults are evidence inputs, not legal certification.
      </div>

      {message ? (
        <div
          className={`form-message ${message.status}`}
          role={message.status === "error" ? "alert" : "status"}
        >
          {message.message}
        </div>
      ) : null}

      <div className="policy-rule-grid">
        <PolicyRulesTable
          onSelectRule={onSelectRule}
          policy={policy}
          rulesState={rulesState}
          selectedRuleId={selectedRuleId}
        />
        <PolicyRuleForm
          form={form}
          isSaving={isSaving}
          onChange={onChange}
          onSubmit={onSubmit}
          policy={policy}
          selectedRuleId={selectedRuleId}
        />
      </div>
    </section>
  );
}

function PolicyRulesTable({
  onSelectRule,
  policy,
  rulesState,
  selectedRuleId
}: {
  onSelectRule: (rule: PolicyRuleRecord) => void;
  policy: PolicyRecord | null;
  rulesState: RulesState;
  selectedRuleId: string | null;
}) {
  if (!policy || rulesState.status === "idle") {
    return (
      <section className="data-panel">
        <div className="state-message">
          <strong>No Policy selected</strong>
          <p>Select a Policy before loading PolicyRules.</p>
        </div>
      </section>
    );
  }

  if (rulesState.status === "loading") {
    return (
      <section className="data-panel" aria-live="polite">
        <div className="state-message">
          <strong>Loading PolicyRules</strong>
          <p>Requesting GET /policies/{"{policy_id}"}/rules.</p>
        </div>
      </section>
    );
  }

  if (rulesState.status === "error") {
    return (
      <section className="data-panel" role="alert">
        <div className="state-message error">
          <strong>Unable to load PolicyRules</strong>
          <p>{rulesState.message}</p>
        </div>
      </section>
    );
  }

  if (rulesState.rules.length === 0) {
    return (
      <section className="data-panel">
        <div className="state-message">
          <strong>No PolicyRules found</strong>
          <p>
            Add a constrained PolicyRule condition for the selected Policy.
          </p>
        </div>
      </section>
    );
  }

  return (
    <section className="data-panel" aria-label="PolicyRule list">
      <div className="table-scroll">
        <table className="data-table policy-rule-table">
          <thead>
            <tr>
              {ruleColumns.map((column) => (
                <th key={column} scope="col">
                  {column}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rulesState.rules.map((rule) => (
              <tr
                className={rule.id === selectedRuleId ? "selected-row" : undefined}
                key={rule.id}
              >
                <td>{rule.name}</td>
                <td>{formatValue(ruleDecision(rule))}</td>
                <td>{ruleCheckSummary(rule)}</td>
                <td>{formatTimestamp(rule.updated_at)}</td>
                <td className="id-cell">{rule.id}</td>
                <td>
                  <button
                    className="table-action-button edit"
                    onClick={() => onSelectRule(rule)}
                    type="button"
                  >
                    Edit
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function PolicyRuleForm({
  form,
  isSaving,
  onChange,
  onSubmit,
  policy,
  selectedRuleId
}: {
  form: RuleFormState;
  isSaving: boolean;
  onChange: (form: RuleFormState) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  policy: PolicyRecord | null;
  selectedRuleId: string | null;
}) {
  const disabled = isSaving || !policy;

  function update<K extends keyof RuleFormState>(
    key: K,
    value: RuleFormState[K]
  ) {
    onChange({ ...form, [key]: value });
  }

  return (
    <section className="policy-form-panel">
      <header className="policy-form-header">
        <div>
          <strong>
            {selectedRuleId ? "Edit selected PolicyRule" : "Create PolicyRule"}
          </strong>
          <p>
            Structured fields produce deterministic condition JSON for POST
            /policy-rules and PATCH /policy-rules/{"{rule_id}"}.
          </p>
        </div>
      </header>

      {!policy ? (
        <div className="state-message compact">
          <strong>No Policy selected</strong>
          <p>Select a Policy before creating or editing PolicyRules.</p>
        </div>
      ) : (
        <form className="policy-form policy-rule-form" onSubmit={onSubmit}>
          <div className="rule-form-grid">
            <TextField
              disabled={disabled}
              label="Rule name"
              onChange={(value) => update("name", value)}
              required
              value={form.name}
            />
            <TextField
              disabled={disabled}
              label="Description"
              onChange={(value) => update("description", value)}
              value={form.description}
            />
          </div>

          <div className="rule-form-grid">
            <SelectField
              disabled={disabled}
              label="Decision"
              onChange={(value) =>
                update("decision", value as PolicyRuleDecision)
              }
              options={POLICY_RULE_DECISIONS}
              value={form.decision}
            />
            <TextField
              disabled={disabled}
              label="Reason"
              onChange={(value) => update("reason", value)}
              required
              value={form.reason}
            />
          </div>

          <fieldset>
            <legend>Request context</legend>
            <div className="rule-form-grid">
              <TextField
                disabled={disabled}
                label="agent_id"
                onChange={(value) => update("agentId", value)}
                value={form.agentId}
              />
              <TextField
                disabled={disabled}
                label="tool_name"
                onChange={(value) => update("toolName", value)}
                value={form.toolName}
              />
              <SelectField
                disabled={disabled}
                label="environment"
                onChange={(value) => update("environment", value)}
                options={POLICY_RULE_ENVIRONMENTS}
                optional
                value={form.environment}
              />
              <SelectField
                disabled={disabled}
                label="risk_level"
                onChange={(value) => update("riskLevel", value)}
                options={POLICY_RULE_RISK_LEVELS}
                optional
                value={form.riskLevel}
              />
              <TextField
                disabled={disabled}
                label="action_type"
                onChange={(value) => update("actionType", value)}
                value={form.actionType}
              />
              <TextField
                disabled={disabled}
                label="capability_id"
                onChange={(value) => update("capabilityId", value)}
                value={form.capabilityId}
              />
              <TextField
                disabled={disabled}
                label="source_id / source_ids"
                onChange={(value) => update("sourceIds", value)}
                placeholder="Comma-separated UUIDs"
                value={form.sourceIds}
              />
              <TextField
                disabled={disabled}
                label="model_id"
                onChange={(value) => update("modelId", value)}
                value={form.modelId}
              />
              <TextField
                disabled={disabled}
                label="purpose"
                onChange={(value) => update("purpose", value)}
                value={form.purpose}
              />
              <SelectField
                disabled={disabled}
                label="data_classification"
                onChange={(value) => update("dataClassification", value)}
                options={POLICY_RULE_DATA_CLASSIFICATIONS}
                optional
                value={form.dataClassification}
              />
              <BooleanSelectField
                disabled={disabled}
                label="contains_personal_data"
                onChange={(value) => update("containsPersonalData", value)}
                value={form.containsPersonalData}
              />
              <BooleanSelectField
                disabled={disabled}
                label="contains_sensitive_data"
                onChange={(value) => update("containsSensitiveData", value)}
                value={form.containsSensitiveData}
              />
            </div>
          </fieldset>

          <fieldset>
            <legend>Resolved inventory context</legend>
            <div className="rule-form-grid">
              <SelectField
                disabled={disabled}
                label="capability_type"
                onChange={(value) => update("capabilityType", value)}
                options={POLICY_RULE_CAPABILITY_TYPES}
                optional
                value={form.capabilityType}
              />
              <SelectField
                disabled={disabled}
                label="capability_status"
                onChange={(value) => update("capabilityStatus", value)}
                options={POLICY_RULE_CAPABILITY_STATUSES}
                optional
                value={form.capabilityStatus}
              />
              <SelectField
                disabled={disabled}
                label="source_status"
                onChange={(value) => update("sourceStatus", value)}
                options={POLICY_RULE_SOURCE_STATUSES}
                optional
                value={form.sourceStatus}
              />
              <SelectField
                disabled={disabled}
                label="source_data_classification"
                onChange={(value) => update("sourceDataClassification", value)}
                options={POLICY_RULE_DATA_CLASSIFICATIONS}
                optional
                value={form.sourceDataClassification}
              />
              <BooleanSelectField
                disabled={disabled}
                label="source_contains_personal_data"
                onChange={(value) => update("sourceContainsPersonalData", value)}
                value={form.sourceContainsPersonalData}
              />
              <BooleanSelectField
                disabled={disabled}
                label="source_contains_sensitive_data"
                onChange={(value) => update("sourceContainsSensitiveData", value)}
                value={form.sourceContainsSensitiveData}
              />
              <SelectField
                disabled={disabled}
                label="model_type"
                onChange={(value) => update("modelType", value)}
                options={POLICY_RULE_MODEL_TYPES}
                optional
                value={form.modelType}
              />
              <SelectField
                disabled={disabled}
                label="model_provider"
                onChange={(value) => update("modelProvider", value)}
                options={POLICY_RULE_MODEL_PROVIDERS}
                optional
                value={form.modelProvider}
              />
              <SelectField
                disabled={disabled}
                label="model_provider_type"
                onChange={(value) => update("modelProviderType", value)}
                options={POLICY_RULE_MODEL_PROVIDER_TYPES}
                optional
                value={form.modelProviderType}
              />
              <SelectField
                disabled={disabled}
                label="model_status"
                onChange={(value) => update("modelStatus", value)}
                options={POLICY_RULE_MODEL_STATUSES}
                optional
                value={form.modelStatus}
              />
              <SelectField
                disabled={disabled}
                label="access_grant_status"
                onChange={(value) => update("accessGrantStatus", value)}
                options={POLICY_RULE_ACCESS_GRANT_STATUSES}
                optional
                value={form.accessGrantStatus}
              />
              <SelectField
                disabled={disabled}
                label="data_usage_review_status"
                onChange={(value) => update("dataUsageReviewStatus", value)}
                options={POLICY_RULE_DATA_USAGE_REVIEW_STATUSES}
                optional
                value={form.dataUsageReviewStatus}
              />
              <TextField
                disabled={disabled}
                label="data_usage_allowed_purpose"
                onChange={(value) => update("dataUsageAllowedPurpose", value)}
                value={form.dataUsageAllowedPurpose}
              />
              <TextField
                disabled={disabled}
                label="data_usage_prohibited_purpose"
                onChange={(value) => update("dataUsageProhibitedPurpose", value)}
                value={form.dataUsageProhibitedPurpose}
              />
            </div>
          </fieldset>

          <fieldset>
            <legend>CheckResult outcome match</legend>
            <div className="rule-form-grid">
              <SelectField
                disabled={disabled}
                label="check_type"
                onChange={(value) => update("checkType", value)}
                options={POLICY_RULE_CHECK_TYPES}
                optional
                value={form.checkType}
              />
              <SelectField
                disabled={disabled}
                label="check_outcome"
                onChange={(value) => update("checkOutcome", value)}
                options={POLICY_RULE_CHECK_OUTCOMES}
                optional
                value={form.checkOutcome}
              />
              <SelectField
                disabled={disabled}
                label="check_target_type"
                onChange={(value) => update("checkTargetType", value)}
                options={POLICY_RULE_CHECK_TARGET_TYPES}
                optional
                value={form.checkTargetType}
              />
              <TextField
                disabled={disabled}
                label="check_target_id"
                onChange={(value) => update("checkTargetId", value)}
                value={form.checkTargetId}
              />
              <TextField
                disabled={disabled}
                label="check_tool_id"
                onChange={(value) => update("checkToolId", value)}
                value={form.checkToolId}
              />
              <TextField
                disabled={disabled}
                inputMode="decimal"
                label="check_min_confidence"
                max="1"
                min="0"
                onChange={(value) => update("checkMinConfidence", value)}
                step="0.01"
                type="number"
                value={form.checkMinConfidence}
              />
            </div>
          </fieldset>

          <details className="condition-preview">
            <summary>Deterministic condition JSON preview</summary>
            <pre>{conditionPreview(form)}</pre>
          </details>

          <button className="secondary-action" disabled={disabled} type="submit">
            {isSaving
              ? "Saving PolicyRule"
              : selectedRuleId
                ? "Save PolicyRule"
                : "Create PolicyRule"}
          </button>
        </form>
      )}
    </section>
  );
}

function TextField({
  disabled,
  inputMode,
  label,
  max,
  min,
  onChange,
  placeholder,
  required,
  step,
  type = "text",
  value
}: {
  disabled: boolean;
  inputMode?: "decimal";
  label: string;
  max?: string;
  min?: string;
  onChange: (value: string) => void;
  placeholder?: string;
  required?: boolean;
  step?: string;
  type?: string;
  value: string;
}) {
  return (
    <label>
      <span>{label}</span>
      <input
        disabled={disabled}
        inputMode={inputMode}
        max={max}
        min={min}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        required={required}
        step={step}
        type={type}
        value={value}
      />
    </label>
  );
}

function SelectField({
  disabled,
  label,
  onChange,
  optional,
  options,
  value
}: {
  disabled: boolean;
  label: string;
  onChange: (value: string) => void;
  optional?: boolean;
  options: readonly string[];
  value: string;
}) {
  return (
    <label>
      <span>{label}</span>
      <select
        disabled={disabled}
        onChange={(event) => onChange(event.target.value)}
        value={value}
      >
        {optional ? <option value="">Do not match</option> : null}
        {options.map((option) => (
          <option key={option} value={option}>
            {formatValue(option)}
          </option>
        ))}
      </select>
    </label>
  );
}

function BooleanSelectField({
  disabled,
  label,
  onChange,
  value
}: {
  disabled: boolean;
  label: string;
  onChange: (value: BooleanField) => void;
  value: BooleanField;
}) {
  return (
    <label>
      <span>{label}</span>
      <select
        disabled={disabled}
        onChange={(event) => onChange(event.target.value as BooleanField)}
        value={value}
      >
        <option value="">Do not match</option>
        <option value="true">True</option>
        <option value="false">False</option>
      </select>
    </label>
  );
}
