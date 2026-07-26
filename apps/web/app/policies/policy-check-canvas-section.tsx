"use client";

import type { PolicyCondition } from "./policy-dsl";
import {
  isPolicyCheckConditionLinked,
  policyCheckDefinition,
  policyCheckExpectedOutcome,
  policyCheckTargetName,
  type PolicyCheckDraft,
  type PolicyCheckValidation
} from "./policy-check-authoring";
import { PolicyIcon } from "./policy-icons";
import styles from "./policy-check-canvas-section.module.css";

export function PolicyCheckCanvasSection({
  checks,
  condition,
  onAddCheck,
  onSelectCheck,
  selectedCheckId,
  validationByCheckId
}: {
  checks: PolicyCheckDraft[];
  condition: PolicyCondition;
  onAddCheck: () => void;
  onSelectCheck: (checkId: string) => void;
  selectedCheckId: string | null;
  validationByCheckId: Map<string, PolicyCheckValidation>;
}) {
  return (
    <>
      {checks.length === 0 ? (
        <div className={styles.empty}>
          <strong>No persisted checks</strong>
          <span>
            Add a bounded metadata-only PolicyCheckStep. CheckResults become
            explicit policy context and evidence after review and activation.
          </span>
        </div>
      ) : null}
      {checks.map((check) => {
        const definition = policyCheckDefinition(check.check_type);
        const validation = validationByCheckId.get(check.id);
        const linked = isPolicyCheckConditionLinked(condition, check);
        const valid = validation?.valid ?? false;
        return (
          <button
            aria-pressed={selectedCheckId === check.id}
            className={[
              styles.node,
              selectedCheckId === check.id ? styles.selected : "",
              check.status !== "active" ? styles.disabled : "",
              !valid ? styles.invalid : ""
            ]
              .filter(Boolean)
              .join(" ")}
            key={check.id}
            onClick={() => onSelectCheck(check.id)}
            type="button"
          >
            <span className={styles.icon}>
              <PolicyIcon name="check" size={14} />
            </span>
            <span className={styles.copy}>
              <strong>{definition.label}</strong>
              <span>{policyCheckTargetName(check) || "Governed target required"}</span>
              <small>
                Expect {formatLabel(policyCheckExpectedOutcome(check))} ·{" "}
                {formatLabel(check.failure_behavior)} ·{" "}
                {formatLabel(check.evidence_retention)}
              </small>
            </span>
            <span
              className={[
                styles.state,
                !valid
                  ? styles.stateInvalid
                  : check.status !== "active"
                    ? styles.stateDisabled
                    : styles.stateValid
              ].join(" ")}
            >
              {!valid
                ? "Needs input"
                : check.status !== "active"
                  ? formatLabel(check.status)
                  : linked
                    ? "Condition linked"
                    : "Evidence only"}
            </span>
          </button>
        );
      })}
      <button className={styles.add} onClick={onAddCheck} type="button">
        <PolicyIcon name="plus" size={13} />
        Add check
      </button>
    </>
  );
}

function formatLabel(value: string) {
  return value.replace(/_/g, " ");
}
