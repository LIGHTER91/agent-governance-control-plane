"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { ApiRequestError, getApiBaseUrl } from "../lib/api";
import {
  POLICY_STATUSES,
  PolicyPayload,
  PolicyRecord,
  PolicyStatus,
  createPolicy,
  fetchPolicies,
  updatePolicy
} from "../lib/policies";

type PoliciesState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; policies: PolicyRecord[] };

type FormState = {
  name: string;
  description: string;
  status: PolicyStatus;
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

const columns = ["Name", "Status", "Description", "Updated", "ID", "View"];

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
  const [selectedPolicyId, setSelectedPolicyId] = useState<string | null>(null);
  const [createForm, setCreateForm] = useState<FormState>(emptyCreateForm);
  const [editForm, setEditForm] = useState<FormState>(emptyCreateForm);
  const [saveMessage, setSaveMessage] = useState<SaveMessage>(null);
  const [creating, setCreating] = useState(false);
  const [updating, setUpdating] = useState(false);

  const selectedPolicy = useMemo(() => {
    if (state.status !== "ready" || !selectedPolicyId) {
      return null;
    }

    return (
      state.policies.find((policy) => policy.id === selectedPolicyId) || null
    );
  }, [selectedPolicyId, state]);

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
      return;
    }

    const selected =
      state.policies.find((policy) => policy.id === selectedPolicyId) ||
      state.policies[0];
    setSelectedPolicyId(selected.id);
    setEditForm(formFromPolicy(selected));
  }, [selectedPolicyId, state]);

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
        message: "Policy created. PolicyRules still define executable conditions."
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

  function handleSelect(policy: PolicyRecord) {
    setSelectedPolicyId(policy.id);
    setEditForm(formFromPolicy(policy));
    setSaveMessage(null);
  }

  return (
    <div className="policy-workspace">
      <section className="policy-boundary" aria-label="Policy UI scope">
        <strong>Policy lifecycle only</strong>
        <p>
          PolicyRules define executable conditions. This page manages Policy
          records and status only; simulation, versioning, and rule editing stay
          out of this slice.
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
            the backend rule API.
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
              {columns.map((column) => (
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
              ? "Update lifecycle fields only. Rule conditions are managed separately."
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
            CRUD, review workflows, and versioning are separate work.
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
