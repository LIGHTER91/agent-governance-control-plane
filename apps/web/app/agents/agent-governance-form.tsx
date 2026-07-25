"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  useCallback,
  useEffect,
  useMemo,
  useState
} from "react";
import { ApiNetworkError, ApiRequestError } from "../lib/api";
import type {
  AgentGovernanceProfileAccessGrant,
  AgentRecord
} from "../lib/agents";
import {
  createAgent,
  fetchAgentGovernanceProfile,
  updateAgent
} from "../lib/agents";
import {
  createAccessGrant,
  fetchCapabilities,
  fetchModels,
  fetchSources
} from "../lib/sources";
import type { AccessGrantRecord } from "../lib/sources";
import {
  agentFormFromRecord,
  buildAccessGrantPayload,
  buildAgentPatch,
  buildAgentPayload,
  createProposal,
  EMPTY_AGENT_FORM,
  formatGovernanceValue,
  normalizeCapability,
  normalizeModel,
  normalizeSource,
  needsStatusConfirmation,
  validateAgentForm,
  validateProposedGrants
} from "./agent-governance-model";
import type {
  AgentFieldErrors,
  AgentFormField,
  AgentFormValues,
  InventoryState,
  InventoryTarget,
  ProposedAccessGrant,
  ProposedGrantErrors,
  ProposedGrantField,
  ResourceState
} from "./agent-governance-model";
import { AgentGovernedAccessStep } from "./agent-governed-access-step";
import { AgentIdentityStep } from "./agent-identity-step";
import { AgentOwnershipStep } from "./agent-ownership-step";
import { AgentReviewStep } from "./agent-review-step";
import { AgentRuntimeRiskStep } from "./agent-runtime-risk-step";
import {
  AgentSubmissionSummary
} from "./agent-submission-summary";
import type {
  FailedGrantOperation,
  SubmissionState
} from "./agent-submission-summary";
import {
  AGENT_WORKFLOW_STEPS,
  AgentWorkflowSteps
} from "./agent-workflow-steps";

type WorkflowMode = "create" | "edit";
type ProfileLoadState =
  | { status: "ready" }
  | { status: "loading" }
  | { status: "error"; title: string; message: string };

const LOADING_INVENTORY: InventoryState = {
  capabilities: { status: "loading" },
  sources: { status: "loading" },
  models: { status: "loading" }
};

const STEP_FIELDS: Record<number, AgentFormField[]> = {
  0: ["name", "description", "framework"],
  1: ["owner_type", "owner_id", "owner_name", "owner_contact_email"],
  2: ["environment", "status", "risk_level"],
  3: [],
  4: []
};

export function AgentGovernanceForm({
  agentId,
  mode
}: {
  agentId?: string;
  mode: WorkflowMode;
}) {
  const router = useRouter();
  const [profileState, setProfileState] = useState<ProfileLoadState>(
    mode === "edit" ? { status: "loading" } : { status: "ready" }
  );
  const [values, setValues] = useState<AgentFormValues>({
    ...EMPTY_AGENT_FORM
  });
  const [initialValues, setInitialValues] = useState<AgentFormValues>({
    ...EMPTY_AGENT_FORM
  });
  const [inventory, setInventory] =
    useState<InventoryState>(LOADING_INVENTORY);
  const [existingGrants, setExistingGrants] = useState<
    AgentGovernanceProfileAccessGrant[]
  >([]);
  const [proposals, setProposals] = useState<ProposedAccessGrant[]>([]);
  const [currentStep, setCurrentStep] = useState(0);
  const [furthestStep, setFurthestStep] = useState(0);
  const [attemptedSteps, setAttemptedSteps] = useState<Set<number>>(
    () => new Set()
  );
  const [statusConfirmed, setStatusConfirmed] = useState(false);
  const [backendFieldErrors, setBackendFieldErrors] =
    useState<AgentFieldErrors>({});
  const [submissionState, setSubmissionState] = useState<SubmissionState>({
    status: "idle"
  });
  const [createdAgentId, setCreatedAgentId] = useState<string | null>(null);

  const loadInventory = useCallback(async (signal?: AbortSignal) => {
    setInventory(LOADING_INVENTORY);
    const [capabilities, sources, models] = await Promise.allSettled([
      fetchCapabilities(signal),
      fetchSources(signal),
      fetchModels(signal)
    ]);

    if (signal?.aborted) {
      return;
    }

    setInventory({
      capabilities: resourceState(
        capabilities,
        (records) => records.map(normalizeCapability),
        "Capabilities"
      ),
      sources: resourceState(
        sources,
        (records) => records.map(normalizeSource),
        "Sources"
      ),
      models: resourceState(
        models,
        (records) => records.map(normalizeModel),
        "Models"
      )
    });
  }, []);

  const loadProfile = useCallback(
    async (signal?: AbortSignal) => {
      if (mode !== "edit" || !agentId) {
        return;
      }

      setProfileState({ status: "loading" });
      try {
        const profile = await fetchAgentGovernanceProfile(agentId, signal);
        const loadedValues = agentFormFromRecord(profile.agent);
        setValues(loadedValues);
        setInitialValues(loadedValues);
        setExistingGrants(profile.access_grants);
        setProfileState({ status: "ready" });
      } catch (error: unknown) {
        if (signal?.aborted) {
          return;
        }
        setProfileState(profileLoadError(error));
      }
    },
    [agentId, mode]
  );

  useEffect(() => {
    const controller = new AbortController();
    void loadInventory(controller.signal);
    void loadProfile(controller.signal);
    return () => controller.abort();
  }, [loadInventory, loadProfile]);

  const localFieldErrors = useMemo(
    () => validateAgentForm(values),
    [values]
  );
  const allFieldErrors = useMemo(
    () => ({ ...localFieldErrors, ...backendFieldErrors }),
    [backendFieldErrors, localFieldErrors]
  );
  const proposalErrors = useMemo(
    () => validateProposedGrants(proposals),
    [proposals]
  );
  const statusConfirmationRequired = needsStatusConfirmation(
    values,
    mode === "edit" || createdAgentId ? initialValues : undefined
  );
  const agentChanged = useMemo(() => {
    if (mode === "create" && !createdAgentId) {
      return JSON.stringify(values) !== JSON.stringify(EMPTY_AGENT_FORM);
    }
    if (Object.keys(validateAgentForm(values)).length > 0) {
      return JSON.stringify(values) !== JSON.stringify(initialValues);
    }
    return Object.keys(buildAgentPatch(values, initialValues)).length > 0;
  }, [createdAgentId, initialValues, mode, values]);
  const dirty = agentChanged || proposals.length > 0;
  const valid =
    Object.keys(allFieldErrors).length === 0 &&
    Object.keys(proposalErrors).length === 0 &&
    (!statusConfirmationRequired || statusConfirmed);
  const submitting = submissionState.status === "submitting";

  const existingTargetKeys = useMemo(
    () =>
      new Set(
        existingGrants.flatMap((grant) =>
          grant.target_id &&
          (grant.target_type === "capability" ||
            grant.target_type === "source" ||
            grant.target_type === "model_asset")
            ? [`${grant.target_type}:${grant.target_id}`]
            : []
        )
      ),
    [existingGrants]
  );

  useEffect(() => {
    if (!dirty || submitting) {
      return;
    }
    const warnBeforeUnload = (event: BeforeUnloadEvent) => {
      event.preventDefault();
      event.returnValue = "";
    };
    window.addEventListener("beforeunload", warnBeforeUnload);
    return () => window.removeEventListener("beforeunload", warnBeforeUnload);
  }, [dirty, submitting]);

  function handleFieldChange<K extends keyof AgentFormValues>(
    field: K,
    value: AgentFormValues[K]
  ) {
    setValues((current) => ({ ...current, [field]: value }));
    setBackendFieldErrors((current) => {
      if (!(field in current)) {
        return current;
      }
      const next = { ...current };
      delete next[field as AgentFormField];
      return next;
    });
    if (submissionState.status === "error") {
      setSubmissionState({ status: "idle" });
    }
  }

  function handleToggleTarget(target: InventoryTarget) {
    if (existingTargetKeys.has(target.key)) {
      return;
    }
    setProposals((current) => {
      const selected = current.some(
        (proposal) => proposal.target.key === target.key
      );
      return selected
        ? current.filter((proposal) => proposal.target.key !== target.key)
        : [...current, createProposal(target)];
    });
    if (submissionState.status !== "submitting") {
      setSubmissionState({ status: "idle" });
    }
  }

  function handleUpdateProposal(
    targetKey: string,
    field: ProposedGrantField,
    value: string
  ) {
    setProposals((current) =>
      current.map((proposal) =>
        proposal.target.key === targetKey
          ? { ...proposal, [field]: value }
          : proposal
      )
    );
    if (submissionState.status === "error") {
      setSubmissionState({ status: "idle" });
    }
  }

  function handleContinue() {
    setAttemptedSteps((current) => new Set(current).add(currentStep));
    if (!stepIsValid(currentStep, allFieldErrors, proposalErrors)) {
      return;
    }
    if (
      currentStep === 2 &&
      statusConfirmationRequired &&
      !statusConfirmed
    ) {
      return;
    }
    const nextStep = Math.min(
      currentStep + 1,
      AGENT_WORKFLOW_STEPS.length - 1
    );
    setCurrentStep(nextStep);
    setFurthestStep((current) => Math.max(current, nextStep));
  }

  function handleReset() {
    if (dirty && !window.confirm("Discard the current unsaved governance changes?")) {
      return;
    }
    setValues({ ...initialValues });
    setProposals([]);
    setBackendFieldErrors({});
    setStatusConfirmed(false);
    setSubmissionState({ status: "idle" });
    setAttemptedSteps(new Set());
    setCurrentStep(0);
    setFurthestStep(0);
  }

  function handleCancel() {
    if (
      dirty &&
      !window.confirm(
        "Leave this Agent workflow? Unsaved governance changes will be lost."
      )
    ) {
      return;
    }
    const destinationId = createdAgentId || agentId;
    router.push(
      destinationId
        ? `/agents/${encodeURIComponent(destinationId)}`
        : "/agents"
    );
  }

  async function handleSubmit() {
    const currentAgentErrors = validateAgentForm(values);
    const currentProposalErrors = validateProposedGrants(proposals);
    const allSteps = new Set(AGENT_WORKFLOW_STEPS.map((_, index) => index));
    setAttemptedSteps(allSteps);

    if (
      Object.keys(currentAgentErrors).length > 0 ||
      Object.keys(currentProposalErrors).length > 0 ||
      (statusConfirmationRequired && !statusConfirmed)
    ) {
      setSubmissionState({
        status: "error",
        title: "Review required fields",
        message:
          "Resolve the highlighted Agent or Access Grant fields before submitting."
      });
      setCurrentStep(
        firstInvalidStep(
          currentAgentErrors,
          currentProposalErrors,
          statusConfirmationRequired && !statusConfirmed
        )
      );
      return;
    }

    if (!dirty) {
      setSubmissionState({
        status: "error",
        title: "No governance changes to save",
        message: "Change an Agent field or add a new Access Grant declaration."
      });
      return;
    }

    setSubmissionState({
      status: "submitting",
      message: "Saving the Agent before creating selected declarations."
    });

    let resolvedAgentId = createdAgentId || agentId || null;
    let savedAgent: AgentRecord | null = null;

    try {
      if (!resolvedAgentId) {
        savedAgent = await createAgent(buildAgentPayload(values));
        resolvedAgentId = savedAgent.id;
        setCreatedAgentId(savedAgent.id);
      } else if (agentChanged) {
        const patch = buildAgentPatch(values, initialValues);
        if (Object.keys(patch).length > 0) {
          savedAgent = await updateAgent(resolvedAgentId, patch);
        }
      }
    } catch (error: unknown) {
      const mappedFields = backendAgentFieldErrors(error);
      if (Object.keys(mappedFields).length > 0) {
        setBackendFieldErrors(mappedFields);
        setCurrentStep(
          firstInvalidStep(mappedFields, {}, false)
        );
      }
      setSubmissionState(agentMutationError(error, mode));
      return;
    }

    if (!resolvedAgentId) {
      setSubmissionState({
        status: "error",
        title: "Agent could not be resolved",
        message: "The backend did not return a stable Agent identifier."
      });
      return;
    }

    if (savedAgent) {
      const persistedValues = agentFormFromRecord(savedAgent);
      setValues(persistedValues);
      setInitialValues(persistedValues);
      setBackendFieldErrors({});
    }

    if (proposals.length === 0) {
      router.push(`/agents/${encodeURIComponent(resolvedAgentId)}`);
      router.refresh();
      return;
    }

    const successfulTargets = new Set<string>();
    const failedGrants: FailedGrantOperation[] = [];

    for (let index = 0; index < proposals.length; index += 1) {
      const proposal = proposals[index];
      setSubmissionState({
        status: "submitting",
        message: `Creating Access Grant ${index + 1} of ${proposals.length} as Pending Review.`
      });
      try {
        const createdGrant = await createAccessGrant(
          buildAccessGrantPayload(resolvedAgentId, proposal)
        );
        successfulTargets.add(proposal.target.key);
        setExistingGrants((current) => [
          ...current,
          profileGrantFromMutation(createdGrant, proposal.target)
        ]);
      } catch (error: unknown) {
        failedGrants.push({
          targetKey: proposal.target.key,
          targetName: proposal.target.name,
          grantName: proposal.name,
          message: accessGrantMutationError(error)
        });
      }
    }

    if (failedGrants.length > 0) {
      const failedKeys = new Set(
        failedGrants.map((failure) => failure.targetKey)
      );
      setProposals((current) =>
        current.filter((proposal) => failedKeys.has(proposal.target.key))
      );
      setSubmissionState({
        status: "partial",
        agentId: resolvedAgentId,
        successfulGrantCount: successfulTargets.size,
        failedGrants
      });
      return;
    }

    setProposals([]);
    router.push(`/agents/${encodeURIComponent(resolvedAgentId)}`);
    router.refresh();
  }

  if (profileState.status === "loading") {
    return (
      <section className="agent-workflow-route">
        <div className="agent-workflow-load-state" aria-live="polite">
          <strong>Loading Agent governance</strong>
          <p>
            Requesting the persisted Agent Governance Profile and governed
            inventory.
          </p>
        </div>
      </section>
    );
  }

  if (profileState.status === "error") {
    return (
      <section className="agent-workflow-route">
        <div className="agent-workflow-load-state error" role="alert">
          <strong>{profileState.title}</strong>
          <p>{profileState.message}</p>
          <div>
            <button type="button" onClick={() => void loadProfile()}>
              Retry Agent
            </button>
            <Link href="/agents">Back to Agent Registry</Link>
          </div>
        </div>
      </section>
    );
  }

  const displayedFieldErrors = attemptedSteps.has(currentStep)
    ? errorsForStep(currentStep, allFieldErrors)
    : {};
  const displayedProposalErrors = attemptedSteps.has(3)
    ? proposalErrors
    : {};
  const destinationId = createdAgentId || agentId;

  return (
    <section className="agent-workflow-route">
      <header className="agent-workflow-header">
        <div>
          <span>Agent Registry</span>
          <h1>
            {mode === "create" && !createdAgentId
              ? "Register Agent"
              : "Edit Agent governance"}
          </h1>
          <p>
            Build a governed Agent record through identity, ownership, runtime
            classification, declared access, and review.
          </p>
        </div>
        <Link
          href={
            destinationId
              ? `/agents/${encodeURIComponent(destinationId)}`
              : "/agents"
          }
          onClick={(event) => {
            if (
              dirty &&
              !window.confirm(
                "Leave this Agent workflow? Unsaved governance changes will be lost."
              )
            ) {
              event.preventDefault();
            }
          }}
        >
          {destinationId ? "Agent Governance Profile" : "Agent Registry"}
        </Link>
      </header>

      <AgentWorkflowSteps
        currentStep={currentStep}
        furthestStep={furthestStep}
        onSelectStep={setCurrentStep}
      />

      <div className="agent-workflow-layout">
        <main className="agent-workflow-main">
          {currentStep === 0 ? (
            <AgentIdentityStep
              errors={displayedFieldErrors}
              values={values}
              onChange={handleFieldChange}
            />
          ) : null}
          {currentStep === 1 ? (
            <AgentOwnershipStep
              errors={displayedFieldErrors}
              values={values}
              onChange={handleFieldChange}
            />
          ) : null}
          {currentStep === 2 ? (
            <AgentRuntimeRiskStep
              confirmationRequired={statusConfirmationRequired}
              confirmed={statusConfirmed}
              errors={displayedFieldErrors}
              values={values}
              onChange={handleFieldChange}
              onConfirm={setStatusConfirmed}
            />
          ) : null}
          {currentStep === 3 ? (
            <AgentGovernedAccessStep
              existingGrants={existingGrants}
              existingTargetKeys={existingTargetKeys}
              inventory={inventory}
              proposalErrors={displayedProposalErrors}
              proposals={proposals}
              showExistingGrants={mode === "edit" || Boolean(createdAgentId)}
              onRetryInventory={() => void loadInventory()}
              onToggleTarget={handleToggleTarget}
              onUpdateProposal={handleUpdateProposal}
            />
          ) : null}
          {currentStep === 4 ? (
            <AgentReviewStep
              mode={mode}
              proposals={proposals}
              values={values}
            />
          ) : null}

          <AgentSubmissionSummary
            state={submissionState}
            onRetry={() => void handleSubmit()}
          />
        </main>

        <AgentWorkflowContext
          agentChanged={agentChanged}
          dirty={dirty}
          existingGrantCount={existingGrants.length}
          mode={mode}
          proposalCount={proposals.length}
          values={values}
        />
      </div>

      <footer className="agent-workflow-actions">
        <div>
          <button disabled={submitting} type="button" onClick={handleCancel}>
            Cancel
          </button>
          <button
            disabled={submitting || !dirty}
            type="button"
            onClick={handleReset}
          >
            Reset changes
          </button>
        </div>
        <div>
          <button
            disabled={submitting || currentStep === 0}
            type="button"
            onClick={() => setCurrentStep((step) => Math.max(0, step - 1))}
          >
            Back
          </button>
          {currentStep < AGENT_WORKFLOW_STEPS.length - 1 ? (
            <button
              className="primary"
              disabled={submitting}
              type="button"
              onClick={handleContinue}
            >
              Continue
            </button>
          ) : (
            <button
              className="primary"
              disabled={submitting || !valid || !dirty}
              type="button"
              onClick={() => void handleSubmit()}
            >
              {submitting
                ? "Saving..."
                : createdAgentId
                  ? "Retry governance save"
                  : mode === "create"
                    ? "Register Agent"
                    : "Save governance"}
            </button>
          )}
        </div>
      </footer>
    </section>
  );
}

function AgentWorkflowContext({
  agentChanged,
  dirty,
  existingGrantCount,
  mode,
  proposalCount,
  values
}: {
  agentChanged: boolean;
  dirty: boolean;
  existingGrantCount: number;
  mode: WorkflowMode;
  proposalCount: number;
  values: AgentFormValues;
}) {
  return (
    <aside className="agent-workflow-context">
      <header>
        <span>Governance summary</span>
        <strong>{values.name.trim() || "Unnamed Agent"}</strong>
        <p>
          {mode === "create"
            ? "New Agent registration"
            : "Persisted Agent governance update"}
        </p>
      </header>
      <dl>
        <div>
          <dt>Owner</dt>
          <dd>{values.owner_name.trim() || "Not set"}</dd>
        </div>
        <div>
          <dt>Environment</dt>
          <dd>{formatGovernanceValue(values.environment)}</dd>
        </div>
        <div>
          <dt>Status</dt>
          <dd>{formatGovernanceValue(values.status)}</dd>
        </div>
        <div>
          <dt>Risk</dt>
          <dd>{formatGovernanceValue(values.risk_level)}</dd>
        </div>
        <div>
          <dt>Existing grants</dt>
          <dd>{existingGrantCount}</dd>
        </div>
        <div>
          <dt>New declarations</dt>
          <dd>{proposalCount}</dd>
        </div>
      </dl>
      <section>
        <strong>{dirty ? "Unsaved changes" : "No unsaved changes"}</strong>
        <p>
          {agentChanged
            ? "Agent fields will be created or patched."
            : "No Agent field mutation is currently required."}
        </p>
      </section>
      <p className="agent-context-boundary">
        Frontend disabled states are advisory. Backend validation and
        authorization remain authoritative.
      </p>
    </aside>
  );
}

function resourceState<TInput, TOutput>(
  result: PromiseSettledResult<TInput>,
  normalize: (value: TInput) => TOutput,
  label: string
): ResourceState<TOutput> {
  if (result.status === "fulfilled") {
    return { status: "ready", data: normalize(result.value) };
  }
  return {
    status: "error",
    message: resourceErrorMessage(result.reason, label)
  };
}

function profileGrantFromMutation(
  grant: AccessGrantRecord,
  target: InventoryTarget
): AgentGovernanceProfileAccessGrant {
  return {
    ...grant,
    target: {
      target_type: target.target_type,
      id: target.id,
      name: target.name,
      status: target.status,
      risk_level: target.risk_level,
      external_ref: null,
      inventory_type: target.type_label,
      provider: null,
      version: null
    }
  };
}

function resourceErrorMessage(error: unknown, label: string) {
  if (error instanceof ApiNetworkError) {
    return `${label} inventory could not reach the AGCP API.`;
  }
  if (error instanceof ApiRequestError && error.status === 403) {
    return `${label} inventory is not permitted for the current backend actor.`;
  }
  return error instanceof Error
    ? error.message
    : `${label} inventory is unavailable.`;
}

function profileLoadError(error: unknown): ProfileLoadState {
  if (error instanceof ApiRequestError && error.status === 404) {
    return {
      status: "error",
      title: "Agent not found",
      message:
        "The requested Agent does not exist or is no longer available in the registry."
    };
  }
  if (error instanceof ApiRequestError && error.status === 403) {
    return {
      status: "error",
      title: "Agent governance is not permitted",
      message:
        "The backend denied this Agent Governance Profile to the current actor."
    };
  }
  if (error instanceof ApiNetworkError) {
    return {
      status: "error",
      title: "Agent backend unavailable",
      message:
        "The frontend could not reach the AGCP API. No persisted values were replaced."
    };
  }
  return {
    status: "error",
    title: "Unable to load Agent governance",
    message:
      error instanceof Error
        ? error.message
        : "The Agent Governance Profile could not be loaded."
  };
}

function errorsForStep(step: number, errors: AgentFieldErrors) {
  if (step === 4) {
    return errors;
  }
  return STEP_FIELDS[step].reduce<AgentFieldErrors>((visible, field) => {
    if (errors[field]) {
      visible[field] = errors[field];
    }
    return visible;
  }, {});
}

function stepIsValid(
  step: number,
  fieldErrors: AgentFieldErrors,
  proposalErrors: ProposedGrantErrors
) {
  if (step === 3) {
    return Object.keys(proposalErrors).length === 0;
  }
  if (step === 4) {
    return (
      Object.keys(fieldErrors).length === 0 &&
      Object.keys(proposalErrors).length === 0
    );
  }
  return STEP_FIELDS[step].every((field) => !fieldErrors[field]);
}

function firstInvalidStep(
  fieldErrors: AgentFieldErrors,
  proposalErrors: ProposedGrantErrors,
  statusConfirmationMissing: boolean
) {
  if (STEP_FIELDS[0].some((field) => fieldErrors[field])) {
    return 0;
  }
  if (STEP_FIELDS[1].some((field) => fieldErrors[field])) {
    return 1;
  }
  if (
    STEP_FIELDS[2].some((field) => fieldErrors[field]) ||
    statusConfirmationMissing
  ) {
    return 2;
  }
  if (Object.keys(proposalErrors).length > 0) {
    return 3;
  }
  return 4;
}

function backendAgentFieldErrors(error: unknown): AgentFieldErrors {
  if (!(error instanceof ApiRequestError) || error.status !== 422) {
    return {};
  }
  const detail = error.detail;
  if (
    !detail ||
    typeof detail !== "object" ||
    !("detail" in detail) ||
    !Array.isArray(detail.detail)
  ) {
    return {};
  }
  return detail.detail.reduce<AgentFieldErrors>((errors, item) => {
    if (!item || typeof item !== "object") {
      return errors;
    }
    const location = "loc" in item && Array.isArray(item.loc) ? item.loc : [];
    const field = location.at(-1);
    const message = "msg" in item && typeof item.msg === "string" ? item.msg : null;
    if (
      typeof field === "string" &&
      field in EMPTY_AGENT_FORM &&
      message
    ) {
      errors[field as AgentFormField] = message;
    }
    return errors;
  }, {});
}

function agentMutationError(
  error: unknown,
  mode: WorkflowMode
): SubmissionState {
  if (error instanceof ApiRequestError) {
    if (error.status === 403) {
      return {
        status: "error",
        title: "Agent mutation not permitted",
        message:
          "The backend denied this operation for the current actor. Frontend controls do not override backend authorization."
      };
    }
    if (error.status === 404 && mode === "edit") {
      return {
        status: "error",
        title: "Agent not found",
        message:
          "The Agent could not be updated because it no longer exists in the backend."
      };
    }
    if (error.status === 422) {
      return {
        status: "error",
        title: "Backend validation rejected the Agent",
        message: apiDetailMessage(
          error,
          "Review the highlighted fields and backend-supported enum values."
        )
      };
    }
  }
  if (error instanceof ApiNetworkError) {
    return {
      status: "error",
      title: "Agent backend unavailable",
      message:
        "The Agent operation could not reach the backend. No synthetic success was shown."
    };
  }
  return {
    status: "error",
    title: "Unable to save Agent governance",
    message:
      error instanceof Error
        ? error.message
        : "The Agent mutation did not complete."
  };
}

function accessGrantMutationError(error: unknown) {
  if (error instanceof ApiRequestError) {
    if (error.status === 403) {
      return "The backend denied Access Grant creation for the current actor.";
    }
    if (error.status === 404) {
      return "The referenced Agent or inventory target is no longer available.";
    }
    if (error.status === 409) {
      return "The backend reported a duplicate or conflicting Access Grant.";
    }
    if (error.status === 422) {
      return apiDetailMessage(
        error,
        "The backend rejected this Access Grant declaration."
      );
    }
  }
  if (error instanceof ApiNetworkError) {
    return "The Access Grant request could not reach the AGCP API.";
  }
  return error instanceof Error
    ? error.message
    : "The Access Grant operation failed.";
}

function apiDetailMessage(error: ApiRequestError, fallback: string) {
  if (typeof error.detail === "string" && error.detail.trim()) {
    return error.detail;
  }
  if (
    error.detail &&
    typeof error.detail === "object" &&
    "detail" in error.detail &&
    typeof error.detail.detail === "string"
  ) {
    return error.detail.detail;
  }
  return fallback;
}
