# PolicyCheckStep Authoring Design

## Status

Design plus backend persistence/API and opt-in Runtime Gateway execution. The
implementation now includes a PolicyRule-linked `PolicyCheckStep` SQLAlchemy
model, Alembic migration, Pydantic create/update/read schemas, CRUD-style API
endpoints, OpenAPI examples, audit events for create/update/status changes, and
Runtime Gateway execution of active authored steps when
`AGCP_RUNTIME_METADATA_PRE_CHECKS_ENABLED=true`.

This document and implementation do not add frontend UI, PolicyRule evaluation
changes, scanner integrations, external tool execution, or CheckResult-driven
enforcement.

AGCP already has `CheckTool` and `CheckResult` persistence, metadata-only
check helpers, optional Runtime Gateway metadata pre-check execution behind
`AGCP_RUNTIME_METADATA_PRE_CHECKS_ENABLED=false` by default, and Evidence
Bundle summaries for safe CheckResults. Policies can now explicitly drive
Runtime Gateway check selection through authored active PolicyCheckSteps linked
to matched PolicyRules.

## Critical Assessment

Explicit PolicyCheckSteps are needed because implicit runtime pre-check
execution can become hard to explain and audit. If the Runtime Gateway simply
runs every available metadata check whenever a contextual request includes
inventory references, operators cannot easily answer why a check ran, which
policy required it, whether it was required or optional, and how unavailable
checks should be treated.

PolicyCheckStep should not become another decision engine. PolicyRule remains
the deterministic object that says `allow`, `deny`, `require_human_review`, or
`not_applicable`. PolicyCheckStep declares evidence collection requirements:
which bounded check to run, against which runtime target, under which policy or
rule scope, and how missing or failed check execution should be represented for
later evaluation or review.

PolicyCheckStep is also distinct from CheckTool and CheckResult:

- CheckTool defines an available check capability, such as
  `data_usage_profile_status`.
- PolicyCheckStep says a Policy or PolicyRule requires that capability for a
  particular contextual target selector.
- CheckResult records what was observed for one runtime request or governance
  review.
- PolicyDecision remains the final decision record.

The main risks are hidden enforcement and workflow creep. If checks silently
alter `proceed`, AGCP becomes opaque and harder to trust. If check steps allow
branching graphs, arbitrary external calls, retries, dependencies, or script
execution, AGCP starts to look like an orchestrator or workflow engine. That is
outside the product boundary. V1 should stay metadata-only, deterministic,
bounded, and auditable.

External scanners and full data scans should stay out of scope until AGCP has a
safe async model, redaction rules, result retention rules, and clear evidence
contracts. Scanner output can contain sensitive data, detected secrets, or
private customer data. V1 PolicyCheckStep authoring should only reference
metadata already stored safely inside AGCP.

## Problem Statement

Runtime metadata pre-check execution can now persist safe CheckResults when it
is explicitly enabled. That is useful as a foundation, but it is too implicit
for policy authoring. AGCP needs a way for policy authors to declare:

- which checks are expected for a governed action;
- which Policy or PolicyRule requested the check;
- which runtime target the check applies to;
- whether a missing result is acceptable, unknown, or review-worthy;
- what evidence must be retained for audit and Evidence Bundle export.

Without explicit PolicyCheckSteps, CheckResults become useful telemetry but not
clear governance intent.

## Core Concepts

### PolicyCheckStep

A PolicyCheckStep is a constrained authoring record that declares a metadata
check requirement for a Policy or PolicyRule.

Implemented V1 fields:

- `id`;
- `policy_rule_id`;
- `check_tool_id`, nullable when using a built-in metadata-only check type
  without a specific CheckTool record;
- `check_type`;
- `target_selector`;
- `required`;
- `failure_behavior`;
- `min_confidence`, nullable numeric value between 0 and 1;
- `status`, `active`, `disabled`, or `retired`;
- `evidence_retention`, `decision_only`, `evidence_bundle`, or `none`;
- `metadata`, safe-filtered only;
- `created_at`;
- `updated_at`.

Fields such as `policy_id`, `name`, `description`, execution ordering,
branching, and policy-level defaults are intentionally deferred.

### Linked Policy Or PolicyRule

Recommendation: V1 PolicyCheckSteps should attach primarily to `PolicyRule`.

Rationale:

- checks are usually relevant only when a specific contextual rule can match;
- rule-level authoring avoids running checks for unrelated policies;
- Evidence Bundle can explain which rule asked for the evidence;
- PolicyRule lifecycle can govern related check steps.

Policy-level steps may be useful later for broad requirements such as "all
production vectorization policies require AccessGrant checks." That should be
deferred until policy versioning and policy templates are designed.

### Check Tool Binding

V1 should support either:

- `check_tool_id`, referencing an active CheckTool; or
- `check_type`, referencing a built-in metadata-only check type.

Using `check_type` is simpler for early internal checks. Using `check_tool_id`
is better once admins manage CheckTool records. The API accepts a built-in
`check_type` and optionally a compatible `check_tool_id`; when a CheckTool is
provided, its `tool_type` must match the PolicyCheckStep check type.

### Target Selector

Target selector defines what the check runs against from the contextual runtime
request.

V1 target selectors should be explicit strings or a small validated enum, not a
query language. Suggested values:

- `agent`;
- `source_ids`;
- `model_id`;
- `capability_id`;
- `access_grants`.

Examples:

- `source_status` with `source_ids`;
- `data_usage_profile_status` with `source_ids`;
- `model_asset_status` with `model_id`;
- `capability_status` with `capability_id`;
- `access_grant_status` with `access_grants`.

V1 should not accept arbitrary JSONPath, SQL, Python expressions, webhooks, or
template code as target selectors.

### Required Or Optional

`required` indicates whether the check is expected to produce evidence for the
policy decision chain.

Suggested meaning:

- `required = true`: unavailable or missing check evidence must be visible as a
  `unknown` or `error` CheckResult and may later be matched by PolicyRules.
- `required = false`: the check enriches evidence but should not be considered
  missing evidence if unavailable.

Required does not directly deny runtime requests. It defines evidence
expectations.

### Failure Behavior

Failure behavior documents how policy authors expect unavailable or failing
checks to be interpreted in future pre-check-aware decision flows.

Suggested values:

- `fail_closed`;
- `require_human_review`;
- `ignore_if_unavailable`;
- `record_only`.

V1 should persist and expose this intent but should not automatically change
Runtime Gateway decisions until PolicyRule evaluation explicitly supports check
outcome matching.

### Confidence Threshold

`min_confidence` is an optional bounded numeric threshold between 0 and 1. It
is configuration intent, not a compliance score or legal confidence claim.

For metadata-only V1 checks, most results will be `high` or `medium` depending
on whether the record exists and is current. Future scanner adapters may need
more careful confidence semantics, but V1 should avoid false precision and not
derive legal certainty from this value.

### Evidence Requirement

`evidence_retention` indicates whether future CheckResults should be retained
for the PolicyDecision chain, Evidence Bundle, or neither.

Evidence may include:

- check type;
- CheckTool reference;
- CheckResult ID;
- target type and target ID;
- outcome;
- confidence label;
- safe reason;
- safe metadata;
- Policy or PolicyRule reference that required the check.

Evidence must not include raw source content, chunks, prompts, credentials,
detected secret values, scanner raw payloads, or private customer data.

### Result Retention

V1 uses a simple retention hint:

- `decision_only`;
- `evidence_bundle`;
- `none`.

Actual deletion or retention enforcement should be a later platform-wide
retention design. CheckResults are audit-adjacent evidence and should not be
silently mutated or overwritten.

## Relationship To Existing Objects

PolicyCheckStep belongs to policy authoring. It should be managed with the
same caution as PolicyRule because it affects what evidence is collected for
runtime decisions.

Relationships:

- Policy contains lifecycle state and groups rules.
- PolicyRule defines deterministic matching and the final decision intent.
- PolicyCheckStep declares evidence collection requirements for a PolicyRule or
  later a Policy template.
- CheckTool defines an available metadata-only check capability.
- CheckResult records observed facts for one runtime request or review.
- PolicyDecision remains the final decision record.
- HumanApproval may be created later if PolicyRules or failure behavior require
  review.
- Evidence Bundle exports the safe evidence chain.

PolicyCheckStep should not replace PolicyRule, CheckTool, CheckResult, or
HumanApproval. It is the missing authoring link between policy intent and
check evidence.

## V1 Metadata-only Scope

V1 should support only built-in metadata-only check types:

- `access_grant_status`;
- `data_usage_profile_status`;
- `source_status`;
- `capability_status`;
- `model_asset_status`.

These checks read persisted AGCP records and safe metadata. They do not inspect
raw source contents, retrieve documents, call model providers, or execute
external scanner jobs.

Explicitly excluded from V1:

- external scanners;
- arbitrary tool execution;
- workflow graphs;
- long-running jobs;
- full data scans;
- prompt inspection;
- source chunk inspection;
- credential or token checks beyond safe metadata key filtering;
- generic expression languages;
- compliance scoring.

## RAG Vectorization Example

Scenario:

```text
An Agent requests action_type = vectorize for one or more source_ids using an
external embedding ModelAsset.
```

PolicyRule selector:

```json
{
  "tool_name": "vectorize_source",
  "action_type": "vectorize",
  "model_provider_type": "external"
}
```

PolicyCheckSteps:

```json
[
  {
    "check_type": "source_status",
    "target_selector": "source_ids",
    "required": true,
    "failure_behavior": "require_human_review",
    "evidence_retention": "evidence_bundle"
  },
  {
    "check_type": "data_usage_profile_status",
    "target_selector": "source_ids",
    "required": true,
    "failure_behavior": "require_human_review",
    "evidence_retention": "evidence_bundle"
  },
  {
    "check_type": "access_grant_status",
    "target_selector": "access_grants",
    "required": true,
    "failure_behavior": "require_human_review",
    "evidence_retention": "evidence_bundle"
  },
  {
    "check_type": "model_asset_status",
    "target_selector": "model_id",
    "required": true,
    "failure_behavior": "fail_closed",
    "evidence_retention": "evidence_bundle"
  }
]
```

Future PolicyRules can explicitly match check outcome context, for example:

```json
{
  "decision": "deny",
  "reason": "External vectorization is denied when source profile checks fail.",
  "action_type": "vectorize",
  "model_provider_type": "external",
  "check_type": "data_usage_profile_status",
  "check_outcome": "fail"
}
```

The exact check outcome condition shape should be designed before
implementation. It must stay deterministic and explicit.

## Execution Model

Recommended staged approach:

1. Add PolicyCheckStep persistence and API. Implemented.
   - No Runtime Gateway behavior change.
   - Steps can be listed for policies and rules.
   - Mutations are audited.

2. Link PolicyCheckStep to active PolicyRules.
   - Only active PolicyRules can contribute active steps.
   - Disabled or archived Policies do not contribute steps.

3. Execute metadata-only steps behind
   `AGCP_RUNTIME_METADATA_PRE_CHECKS_ENABLED=true`.
   - Resolve runtime inventory context first.
   - Identify matching active PolicyRules using declared and resolved context.
   - Run only active PolicyCheckSteps attached to matching rules.
   - Persist CheckResults linked to Agent, run, TraceEvent, PolicyDecision, and
     safe PolicyCheckStep reference metadata where available.
   - Do not directly alter `decision` or `proceed`.

4. Later add explicit check outcome matching.
   - CheckResults become additional deterministic context only when PolicyRules
     explicitly match check outcome fields.
   - No hidden default deny.
   - No automatic AccessGrant enforcement.

This staged approach keeps current clients working and prevents checks from
becoming an invisible enforcement mechanism.

## Failure Behavior

Failure behavior should be explicit authoring intent, not magic.

Suggested values:

- `fail_closed`: future pre-check-aware evaluation should deny if required
  evidence is unavailable or failed.
- `require_human_review`: future evaluation should escalate uncertainty or
  failure.
- `ignore_if_unavailable`: missing check tool or unavailable result should not
  affect the decision, but may still be recorded.
- `record_only`: persist CheckResults for evidence and let
  PolicyRules decide only if they explicitly match those outcomes.

Initial implementation should record failure behavior but not enforce it
directly. A later issue should define exactly how failure behavior becomes
policy context.

## Safety

PolicyCheckStep and CheckResult handling must not store, log, audit, or export:

- raw source content;
- retrieved chunks;
- full prompts;
- raw tool payloads;
- raw model provider payloads;
- scanner raw payloads;
- API keys;
- tokens;
- credentials;
- authorization headers;
- private customer data;
- detected secret values.

Allowed evidence is limited to safe summaries, labels, outcomes, confidence
labels, safe reasons, target references, and safe metadata after existing
filtering.

AGCP must not claim that a check result certifies legal compliance, GDPR
compliance, or lawful use. Data Usage Profile checks are declared or validated
governance metadata, not legal certification.

## API Shape

Implemented endpoints:

```http
POST /policy-check-steps
GET /policy-check-steps
GET /policy-check-steps/{step_id}
PATCH /policy-check-steps/{step_id}
GET /policy-rules/{rule_id}/check-steps
```

Delete should stay out of scope. Use status lifecycle instead:

- `active`;
- `disabled`;
- `retired`.

Suggested audit events:

- `policy_check_step_created`;
- `policy_check_step_updated`;
- `policy_check_step_status_changed`.

Audit metadata should include safe references and summary fields only. It
should not include raw conditions, raw runtime payloads, scanner payloads, or
secrets.

## Evidence Bundle Implications

Evidence Bundle includes safe CheckResult summaries. When authored runtime
PolicyCheckSteps execute, the CheckResult safe metadata can include
PolicyCheckStep references:

- `policy_check_step_id`;
- linked `policy_id`;
- linked `policy_rule_id`;
- check type or CheckTool reference;
- target selector;
- required flag;
- failure behavior;
- evidence-required flag.

This explains why a CheckResult exists without expanding Evidence Bundle into a
workflow log or policy authoring UI.

## Non-goals

- Do not execute scanners or external tools from PolicyCheckSteps.
- Do not make PolicyCheckStep `failure_behavior` directly change runtime
  `decision` or `proceed`.
- Do not change PolicyRule evaluation in this implementation slice.
- Do not add frontend UI.
- Do not add external scanners.
- Do not execute tools.
- Do not build workflow orchestration.
- Do not add a generic policy language.
- Do not add nested boolean logic.
- Do not add policy simulation.
- Do not claim legal compliance certification.
- Do not add fake compliance scores, risk scores, trust scores, or maturity
  scores.

## Migration Path

Recommended staged implementation:

1. Finalize this design. Done.
2. Add `PolicyCheckStep` persistence linked to PolicyRule first.
   Implemented.
3. Add Pydantic create/update/read schemas and validation for V1 check types
   and target selectors.
   Implemented.
4. Add CRUD-style management endpoints with audit logs.
   Implemented.
5. Include safe PolicyCheckStep reference metadata in CheckResult summaries.
   Implemented for runtime-authored step execution through CheckResult safe
   metadata.
6. Update Runtime Gateway optional pre-check execution to run only authored
   active steps behind `AGCP_RUNTIME_METADATA_PRE_CHECKS_ENABLED=true`.
   Implemented.
7. Add deterministic check outcome context only after the policy evaluator
   contract is designed.
8. Add guided Policy UI support only after versioning, review, and simulation
   semantics are designed.
9. Consider external checker adapters only after async execution, safety, and
   retention rules are designed.

## Open Questions

- Should PolicyCheckSteps attach only to PolicyRule in V1, or should
  Policy-level default steps be supported immediately?
- Should failed checks ever influence decisions automatically, or only through
  explicit PolicyRule condition fields?
- How should AGCP represent check outcome context without introducing a
  generic expression language?
- How should unavailable check tools behave differently in simulation and
  enforcement mode?
- How should check latency budgets be configured?
- Should CheckResults be reused across runtime requests, or should every
  runtime request produce fresh evidence?
- How should PolicyCheckSteps be versioned with Policy and PolicyRule changes?
- Should `failure_behavior` be advisory metadata first, or enforced once
  check-aware evaluation exists?
- How should Evidence Bundle show required checks that did not run?
- What operator role should be allowed to author PolicyCheckSteps before full
  enterprise auth exists?
