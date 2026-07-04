"use client";

import {
  addConditionField,
  conditionFieldDefinitionsForGroup,
  removeConditionField,
  updateConditionField,
  type ConditionValue,
  type PolicyBlock,
  type PolicyCondition
} from "./policy-dsl";
import { PolicyCanvas } from "./policy-canvas";

export function PolicyBlocksEditor({
  blocks,
  condition,
  onChangeCondition,
  onSelectBlock,
  selectedBlockId
}: {
  blocks: PolicyBlock[];
  condition: PolicyCondition;
  onChangeCondition: (condition: PolicyCondition) => void;
  onSelectBlock: (blockId: string) => void;
  selectedBlockId: string | null;
}) {
  const checkDefinitions = conditionFieldDefinitionsForGroup("check");
  const configuredChecks = checkDefinitions.filter((definition) =>
    Object.prototype.hasOwnProperty.call(condition, definition.field)
  );

  return (
    <>
      <PolicyCanvas
        blocks={blocks}
        condition={condition}
        onChangeCondition={onChangeCondition}
        onSelectBlock={onSelectBlock}
        selectedBlockId={selectedBlockId}
      />
      <section className="ps2-checkstep-authoring" aria-label="PolicyCheckStep authoring">
        <header>
          <div>
            <span>PolicyCheckStep authoring</span>
            <strong>Metadata checks required before the decision</strong>
          </div>
          <small>{configuredChecks.length} configured</small>
        </header>
        <div className="ps2-checkstep-grid">
          {checkDefinitions.map((definition) => {
            const configured = Object.prototype.hasOwnProperty.call(
              condition,
              definition.field
            );
            const value = configured
              ? condition[definition.field]
              : definition.defaultValue;

            return (
              <div
                className={`ps2-checkstep-card ${configured ? "is-configured" : ""}`}
                key={definition.field}
              >
                <div className="ps2-checkstep-copy">
                  <strong>{definition.label}</strong>
                  <span>{definition.help}</span>
                  <code>{definition.field}</code>
                </div>
                <CheckStepValueControl
                  onChange={(nextValue) =>
                    onChangeCondition(
                      configured
                        ? updateConditionField(
                            condition,
                            definition.field,
                            nextValue
                          )
                        : addConditionField(condition, definition.field, nextValue)
                    )
                  }
                  options={[...(definition.options || [])]}
                  type={definition.valueType}
                  value={value}
                />
                <button
                  className="ps2-checkstep-toggle"
                  onClick={() => {
                    onChangeCondition(
                      configured
                        ? removeConditionField(condition, definition.field)
                        : addConditionField(
                            condition,
                            definition.field,
                            definition.defaultValue
                          )
                    );
                    onSelectBlock(`check-${definition.field}`);
                  }}
                  type="button"
                >
                  {configured ? "Remove step" : "Add step"}
                </button>
              </div>
            );
          })}
        </div>
        <p>
          PolicyCheckSteps are metadata-only requirements. They do not execute
          tools and have no runtime effect until the draft PolicyVersion is
          reviewed and activated.
        </p>
        <style jsx>{`
          .ps2-checkstep-authoring {
            border-top: 1px solid rgba(170, 190, 205, .12);
            display: grid;
            gap: 12px;
            padding: 14px 0 0;
          }
          .ps2-checkstep-authoring header {
            align-items: end;
            display: flex;
            justify-content: space-between;
            gap: 12px;
          }
          .ps2-checkstep-authoring header span,
          .ps2-checkstep-authoring header small {
            color: #9b7cff;
            font-family: var(--mono);
            font-size: 9.5px;
            font-weight: 800;
            letter-spacing: .06em;
            text-transform: uppercase;
          }
          .ps2-checkstep-authoring header strong {
            color: #eef3f8;
            display: block;
            font-size: 12px;
            margin-top: 4px;
          }
          .ps2-checkstep-grid {
            display: grid;
            gap: 8px;
            grid-template-columns: repeat(2, minmax(0, 1fr));
          }
          .ps2-checkstep-card {
            background: rgba(9, 20, 28, .82);
            border: 1px solid rgba(180, 198, 214, .13);
            border-radius: 6px;
            display: grid;
            gap: 9px;
            grid-template-columns: minmax(0, 1fr) 132px auto;
            padding: 10px;
          }
          .ps2-checkstep-card.is-configured {
            border-color: rgba(101, 216, 143, .42);
            box-shadow: inset 0 0 0 1px rgba(101, 216, 143, .08);
          }
          .ps2-checkstep-copy {
            display: grid;
            gap: 4px;
            min-width: 0;
          }
          .ps2-checkstep-copy strong {
            color: #eef3f8;
            font-size: 11px;
          }
          .ps2-checkstep-copy span {
            color: #9faabc;
            font-size: 10px;
            line-height: 1.35;
          }
          .ps2-checkstep-copy code {
            color: #65d88f;
            font-family: var(--mono);
            font-size: 9.5px;
          }
          .ps2-checkstep-control {
            display: grid;
            min-width: 0;
          }
          .ps2-checkstep-control input,
          .ps2-checkstep-control select {
            background: rgba(255, 255, 255, .04);
            border: 1px solid rgba(180, 198, 214, .16);
            border-radius: 4px;
            color: #e7eef5;
            font-family: var(--mono);
            font-size: 10px;
            min-height: 30px;
            min-width: 0;
            padding: 4px 6px;
          }
          .ps2-checkstep-toggle {
            align-self: start;
            background: rgba(255, 255, 255, .035);
            border: 1px solid rgba(180, 198, 214, .15);
            border-radius: 4px;
            color: #cbd5df;
            cursor: pointer;
            font-family: var(--mono);
            font-size: 10px;
            min-height: 30px;
            padding: 5px 8px;
            white-space: nowrap;
          }
          .is-configured .ps2-checkstep-toggle {
            border-color: rgba(244, 82, 107, .28);
            color: #ff9bab;
          }
          .ps2-checkstep-authoring p {
            color: #8f9baa;
            font-size: 10.5px;
            line-height: 1.45;
            margin: 0;
          }
          @media (max-width: 1100px) {
            .ps2-checkstep-grid {
              grid-template-columns: 1fr;
            }
            .ps2-checkstep-card {
              grid-template-columns: 1fr;
            }
          }
        `}</style>
      </section>
    </>
  );
}

function CheckStepValueControl({
  onChange,
  options,
  type,
  value
}: {
  onChange: (value: ConditionValue) => void;
  options: string[];
  type: "text" | "number" | "select";
  value: ConditionValue;
}) {
  const stringValue = Array.isArray(value) ? value.join(", ") : String(value ?? "");

  return (
    <label className="ps2-checkstep-control">
      <span className="sr-only">PolicyCheckStep value</span>
      {type === "select" ? (
        <select onChange={(event) => onChange(event.target.value)} value={stringValue}>
          {options.map((option) => (
            <option key={option} value={option}>
              {formatOptionLabel(option)}
            </option>
          ))}
        </select>
      ) : (
        <input
          onChange={(event) => onChange(event.target.value)}
          type={type === "number" ? "number" : "text"}
          value={stringValue}
        />
      )}
    </label>
  );
}

function formatOptionLabel(value: string) {
  return value
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}
