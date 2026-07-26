"use client";

import type {
  PolicyCheckEvidenceRetention,
  PolicyCheckExpectedOutcome,
  PolicyCheckFailureBehavior,
  PolicyCheckStatus,
  PolicyCheckType
} from "../lib/policy-check-steps";
import {
  POLICY_CHECK_EVIDENCE_RETENTION,
  POLICY_CHECK_EXPECTED_OUTCOMES,
  POLICY_CHECK_FAILURE_BEHAVIORS,
  POLICY_CHECK_STATUSES,
  POLICY_CHECK_TYPES,
  isPolicyCheckConditionLinked,
  policyCheckCodePreview,
  policyCheckDefinition,
  policyCheckEvidenceRetentionHelp,
  policyCheckExpectedOutcome,
  policyCheckFailureBehaviorHelp,
  policyCheckSnapshots,
  policyCheckTargetId,
  policyCheckTargetOptions,
  updatePolicyCheckExpectedOutcome,
  updatePolicyCheckTarget,
  updatePolicyCheckType,
  type PolicyCheckDraft,
  type PolicyCheckInventoryState,
  type PolicyCheckValidation
} from "./policy-check-authoring";
import type { PolicyCondition } from "./policy-dsl";
import styles from "./policy-check-inspector.module.css";

export function PolicyCheckInspector({
  check,
  condition,
  editingLocked,
  inventoryState,
  onChange,
  onLinkCondition,
  onRemove,
  validation
}: {
  check: PolicyCheckDraft;
  condition: PolicyCondition;
  editingLocked: boolean;
  inventoryState: PolicyCheckInventoryState;
  onChange: (check: PolicyCheckDraft) => void;
  onLinkCondition: () => void;
  onRemove: () => void;
  validation: PolicyCheckValidation | null;
}) {
  const definition = policyCheckDefinition(check.check_type);
  const targetOptions =
    inventoryState.status === "ready"
      ? policyCheckTargetOptions(check.check_type, inventoryState.inventory)
      : [];
  const selectedTargetId = policyCheckTargetId(check);
  const linked = isPolicyCheckConditionLinked(condition, check);
  const snapshot = policyCheckSnapshots([check], check.policy_rule_id)[0];

  return (
    <section className={styles.root} aria-label="PolicyCheckStep inspector">
      <div className={styles.heading}>
        <div>
          <span>Metadata-only check</span>
          <h2>{definition.label}</h2>
        </div>
        <span
          className={`${styles.validity} ${
            validation?.valid ? styles.valid : styles.invalid
          }`}
        >
          {validation?.valid ? "Valid" : "Needs input"}
        </span>
      </div>

      <p className={styles.description}>{definition.description}</p>
      {editingLocked ? (
        <div className={styles.locked}>
          This draft is immutable while review is pending. Create a new draft
          for check changes.
        </div>
      ) : null}

      <label className={styles.field}>
        <span>Check type</span>
        <select
          disabled={editingLocked}
          onChange={(event) =>
            onChange(
              updatePolicyCheckType(
                check,
                event.target.value as PolicyCheckType
              )
            )
          }
          value={check.check_type}
        >
          {POLICY_CHECK_TYPES.map((checkType) => (
            <option key={checkType} value={checkType}>
              {policyCheckDefinition(checkType).label}
            </option>
          ))}
        </select>
        <small>
          Built-in metadata adapter only. No scanner, webhook, callback, or
          external code execution.
        </small>
      </label>

      <label className={styles.field}>
        <span>Governed target</span>
        <select
          disabled={
            editingLocked ||
            inventoryState.status !== "ready" ||
            targetOptions.length === 0
          }
          onChange={(event) => {
            const target =
              targetOptions.find((option) => option.id === event.target.value) ||
              null;
            onChange(updatePolicyCheckTarget(check, target));
          }}
          value={selectedTargetId}
        >
          <option value="">
            {inventoryState.status === "loading"
              ? "Loading backend inventory…"
              : targetOptions.length === 0
                ? `No ${definition.targetLabel} records available`
                : `Select ${definition.targetLabel}`}
          </option>
          {targetOptions.map((target) => (
            <option key={target.id} value={target.id}>
              {target.label} · {target.detail}
            </option>
          ))}
        </select>
        <small>
          Selector: <code>{check.target_selector}</code>. Runtime observes the
          matching request context; the generated PolicyRule condition pins the
          selected CheckResult target.
        </small>
      </label>

      {inventoryState.status === "error" ? (
        <div className={styles.inventoryMessage}>
          {inventoryState.message} <a href="/access-data">Open Access &amp; Data</a>
        </div>
      ) : null}
      {inventoryState.status === "ready" && targetOptions.length === 0 ? (
        <div className={styles.inventoryMessage}>
          No real {definition.targetLabel} inventory is available.{" "}
          <a href="/access-data">Open Access &amp; Data</a>
        </div>
      ) : null}
      {inventoryState.status === "ready" && inventoryState.profileWarning ? (
        <div className={styles.inventoryMessage}>
          {inventoryState.profileWarning}
        </div>
      ) : null}

      <label className={styles.field}>
        <span>Expected outcome</span>
        <select
          disabled={editingLocked}
          onChange={(event) =>
            onChange(
              updatePolicyCheckExpectedOutcome(
                check,
                event.target.value as PolicyCheckExpectedOutcome
              )
            )
          }
          value={policyCheckExpectedOutcome(check)}
        >
          {POLICY_CHECK_EXPECTED_OUTCOMES.map((outcome) => (
            <option key={outcome} value={outcome}>
              {formatLabel(outcome)}
            </option>
          ))}
        </select>
        <small>
          This is the expected CheckResult fact. The final THEN decision remains
          in the PolicyRule.
        </small>
      </label>

      <button
        className={`${styles.linkButton} ${linked ? styles.linked : ""}`}
        disabled={editingLocked || !selectedTargetId}
        onClick={onLinkCondition}
        type="button"
      >
        {linked
          ? "Expected outcome linked to PolicyRule"
          : "Use expected outcome in PolicyRule"}
      </button>

      <label className={styles.field}>
        <span>Failure behavior</span>
        <select
          disabled={editingLocked}
          onChange={(event) =>
            onChange({
              ...check,
              failure_behavior: event.target
                .value as PolicyCheckFailureBehavior
            })
          }
          value={check.failure_behavior}
        >
          {POLICY_CHECK_FAILURE_BEHAVIORS.map((behavior) => (
            <option key={behavior} value={behavior}>
              {formatLabel(behavior)}
            </option>
          ))}
        </select>
        <small>{policyCheckFailureBehaviorHelp(check.failure_behavior)}</small>
      </label>

      <label className={styles.field}>
        <span>Evidence retention</span>
        <select
          disabled={editingLocked}
          onChange={(event) =>
            onChange({
              ...check,
              evidence_retention: event.target
                .value as PolicyCheckEvidenceRetention
            })
          }
          value={check.evidence_retention}
        >
          {POLICY_CHECK_EVIDENCE_RETENTION.map((retention) => (
            <option key={retention} value={retention}>
              {formatLabel(retention)}
            </option>
          ))}
        </select>
        <small>{policyCheckEvidenceRetentionHelp(check.evidence_retention)}</small>
      </label>

      <label className={styles.field}>
        <span>Status</span>
        <select
          disabled={editingLocked}
          onChange={(event) =>
            onChange({
              ...check,
              status: event.target.value as PolicyCheckStatus
            })
          }
          value={check.status}
        >
          {POLICY_CHECK_STATUSES.map((status) => (
            <option key={status} value={status}>
              {formatLabel(status)}
            </option>
          ))}
        </select>
        <small>Only active checks execute after the reviewed version is activated.</small>
      </label>

      <label className={styles.checkbox}>
        <input
          checked={check.required}
          disabled={editingLocked}
          onChange={(event) =>
            onChange({ ...check, required: event.target.checked })
          }
          type="checkbox"
        />
        <span>
          Required declaration
          <small>
            Persisted authoring intent; it does not add hidden final-decision logic.
          </small>
        </span>
      </label>

      {validation && validation.messages.length > 0 ? (
        <div className={styles.validation}>
          <strong>Check validation</strong>
          <ul>
            {validation.messages.map((message, index) => (
              <li key={`${message.text}-${index}`}>{message.text}</li>
            ))}
          </ul>
        </div>
      ) : null}

      <details className={styles.preview}>
        <summary>Generated preview</summary>
        <span>Persisted PolicyCheckStep snapshot</span>
        <pre>{JSON.stringify(snapshot, null, 2)}</pre>
        <span>Read-only Code DSL representation</span>
        <pre>{policyCheckCodePreview([check])}</pre>
        <span>Final THEN decision remains: {String(condition.decision || "not configured")}</span>
      </details>

      <button
        className={styles.remove}
        disabled={editingLocked}
        onClick={onRemove}
        type="button"
      >
        Remove from draft
      </button>
    </section>
  );
}

function formatLabel(value: string) {
  return value
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}
