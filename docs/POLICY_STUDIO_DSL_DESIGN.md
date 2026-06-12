# Policy Studio DSL Design

This document completes the formal design for issue #76: the controlled Policy
Studio DSL used by the `/policies` frontend.

The DSL is an authoring and review layer for deterministic AGCP policy
configuration. It is not a runtime policy engine, not arbitrary code, and not a
legal or compliance certification language.

## Purpose

Policy Studio needs a human-readable authoring surface that helps reviewers
understand:

- what runtime request context a PolicyRule matches;
- which inventory, review, and check-result facts must be present;
- which decision AGCP should return;
- which evidence records explain the decision.

The DSL gives the frontend a compact representation of the existing
`PolicyRule.condition` JSON while keeping the backend and Runtime Gateway on the
same deterministic condition model. Users may work in Blocks mode or Code DSL
mode, but both modes compile to the same bounded condition JSON.

## Product Boundary

The DSL must stay inside AGCP's governance boundary:

- AGCP remains a governance and evidence control plane, not an orchestrator.
- The DSL never executes tools.
- The DSL never executes arbitrary Python, JavaScript, SQL, CEL, Rego, Cedar,
  shell, templates, or user-defined functions.
- Runtime Gateway and telemetry evaluate active `PolicyVersion` snapshots, not
  the DSL source text.
- Unsupported DSL syntax is reported and blocks saving from Policy Studio; it
  must not be silently persisted as if it were enforceable.
- Local validation is parser and compile validation only. It is not production
  simulation and does not invent impact counts.

## V1 Grammar

The implemented frontend parser accepts a narrow, line-oriented format:

```text
policy <policy_name> {
  scope <display_scope>

  when <field> <operator> <value>
    and <field> <operator> <value>

  check <field> <operator> <value> required

  then <decision>("required reason")
  prove decision, checks, reviewer, evidence_bundle
}
```

### Structural Lines

These lines are structural for readability and are not compiled into
`PolicyRule.condition`:

- `policy <name> {`
- `scope <display_scope>`
- `prove ...`
- `}`
- blank lines and `//` comments

The policy name is slugified and used as the local draft rule name. Scope is a
display hint only in V1.

### WHEN Lines

`when` and subsequent `and` lines describe runtime request and declared context
fields:

```text
when system.environment == "production"
  and action.risk in ["high", "critical"]
  and tool.name == "external_api_call"
```

These compile to fields in `PolicyRule.condition`. The runtime evaluator uses
the compiled JSON after the corresponding `PolicyVersion` is activated.

### CHECK Lines

`check` lines describe resolved inventory facts, review metadata, and
CheckResult summary fields:

```text
check access_grant.status == "active" required
check data_usage.review_status == "approved" required
check check.outcome == "pass" required
```

The `required` suffix is accepted for readability and stripped by the parser.
V1 CHECK lines do not create or edit `PolicyCheckStep` records. They compile
only to deterministic condition fields.

### THEN Line

The `then` line sets the runtime decision and required reason:

```text
then require_review("High-risk production action requires governance review.")
```

Supported decisions:

- `allow("reason")`
- `deny("reason")`
- `require_review("reason")`
- `require_human_review("reason")`
- `not_applicable("reason")`

`require_review` is an authoring alias for `require_human_review`. A non-empty
reason is required before the frontend can save a compiled draft.

### PROVE Line

The current canonical PROVE line is:

```text
prove decision, checks, reviewer, evidence_bundle
```

PROVE is evidence intent for review readability. It is not a proof engine, not a
runtime clause, and not a separate persisted backend condition in V1. Evidence
is produced by the existing AGCP records:

- `PolicyDecision`
- `CheckResult`
- `HumanApproval` and PolicyVersion reviewer metadata when applicable
- `AuditLog`
- Evidence Bundle JSON export

## Operators And Values

The parser supports:

- equality-style expressions: `field == value`
- list expressions: `field in ["a", "b"]`
- comparison tokens: `>=`, `<=`, `>`, `<`

The current durable compile target is still field-value condition JSON. The
frontend serializer emits only `==` for scalar values and `in` for arrays.
Comparison tokens are parsed as values, but the operator itself is not persisted
in `PolicyRule.condition`. Until the backend condition schema stores operators,
comparison syntax should be treated as editor input for the supported field
value, not as a general runtime comparison language.

Supported values:

- quoted strings: `"production"`
- booleans: `true`, `false`
- numbers: `0.8`
- arrays of strings: `["source_a", "source_b"]`

Validation rules:

- `reason` is required.
- `check_min_confidence` must be a number between `0` and `1`.
- unknown fields are unsupported.
- malformed expressions are unsupported.
- unsupported lines block Save draft in Policy Studio.
- invalid backend payloads still surface backend validation errors.

`source_ids` compiles to a string array. Runtime matching for `source_ids` uses
the existing deterministic source overlap behavior once the rule is part of an
active `PolicyVersion`.

## Supported Field Mapping

The DSL uses display labels where useful, but compiles to the existing
`PolicyRule.condition` keys.

| Group | DSL label | Condition key | Notes |
| --- | --- | --- | --- |
| THEN | decision | `decision` | Set by the `then` statement. |
| THEN | reason | `reason` | Set by the reason argument in `then`. |
| WHEN | agent.id | `agent_id` | Direct agent identifier match. |
| WHEN | tool.name | `tool_name` | Runtime tool/action name. |
| WHEN | system.environment | `environment` | Runtime environment such as production. |
| WHEN | action.risk | `risk_level` | Declared risk level. |
| WHEN | action.type | `action_type` | Runtime action type. |
| WHEN | capability.id | `capability_id` | Declared capability identifier. |
| WHEN | source.id | `source_id` | Single declared source identifier. |
| WHEN | source.ids | `source_ids` | Array with any-overlap runtime behavior. |
| WHEN | model.id | `model_id` | Declared model identifier. |
| WHEN | request.purpose | `purpose` | Declared request purpose. |
| WHEN | data.classification | `data_classification` | Runtime data classification. |
| WHEN | data.contains_personal_data | `contains_personal_data` | Boolean. |
| WHEN | data.contains_sensitive_data | `contains_sensitive_data` | Boolean. |
| CHECK | capability.type | `capability_type` | Resolved capability metadata. |
| CHECK | capability.status | `capability_status` | Resolved capability status. |
| CHECK | source.status | `source_status` | Resolved source status. |
| CHECK | source.classification | `source_data_classification` | Resolved source classification. |
| CHECK | source.contains_personal_data | `source_contains_personal_data` | Boolean. |
| CHECK | source.contains_sensitive_data | `source_contains_sensitive_data` | Boolean. |
| CHECK | model.type | `model_type` | Resolved model type. |
| CHECK | model.provider | `model_provider` | Resolved model provider. |
| CHECK | model.provider_type | `model_provider_type` | Internal or external provider class. |
| CHECK | model.status | `model_status` | Resolved model status. |
| CHECK | access_grant.status | `access_grant_status` | Declarative AccessGrant status. |
| CHECK | data_usage.review_status | `data_usage_review_status` | DataUsageProfile review state. |
| CHECK | data_usage.allowed_purpose | `data_usage_allowed_purpose` | Allowed purpose metadata. |
| CHECK | data_usage.prohibited_purpose | `data_usage_prohibited_purpose` | Prohibited purpose metadata. |
| CHECK | check.type | `check_type` | Safe CheckResult type summary. |
| CHECK | check.outcome | `check_outcome` | Safe CheckResult outcome summary. |
| CHECK | check.target_type | `check_target_type` | Safe CheckResult target type. |
| CHECK | check.target_id | `check_target_id` | Safe CheckResult target identifier. |
| CHECK | check.tool_id | `check_tool_id` | Safe CheckTool identifier. |
| CHECK | check.min_confidence | `check_min_confidence` | Number between 0 and 1. |

The parser also accepts condition keys directly, for example
`risk_level == "high"` or `check_outcome == "pass"`, but display labels are the
preferred authoring syntax.

## Compile Target

Policy Studio compiles DSL or Blocks state into a stable sorted
`PolicyRule.condition` JSON object. Example:

```json
{
  "action_type": "external_api_call",
  "decision": "require_human_review",
  "environment": "production",
  "reason": "High-risk production action requires governance review.",
  "risk_level": "high"
}
```

Save draft uses existing backend APIs to create or update a draft
`PolicyVersion` snapshot. The reviewed runtime artifact is the snapshot of:

- Policy fields;
- associated PolicyRule condition JSON;
- associated PolicyCheckStep configuration when present.

DSL source is not the runtime source of truth. If a future version stores DSL
source as safe display metadata, it must remain non-executable and secondary to
the compiled snapshot.

## Blocks And Templates

Blocks mode and Code DSL mode are two views of the same supported condition
fields. The frontend keeps one canonical editor state for the compiled
condition surface: Code DSL edits are parsed into condition JSON, while Blocks
edits update supported condition fields and regenerate the DSL preview. Save
draft uses the validated compiled condition object, not a separate hidden form
state.

Blocks mode groups fields by:

- WHEN: request/runtime matching fields;
- CHECK: inventory, review, and check summary fields;
- THEN: decision and reason;
- PROVE: evidence intent.

Built-in templates are static authoring helpers. They prefill local editor
state only, never create backend records automatically, and never imply that
production runtime behavior changes before explicit Save draft, review, and
activation.

If the editor contains unsupported DSL lines or backend condition fields not
represented in Blocks, Blocks editing is guarded to avoid silently dropping
state. The user must remove unsupported syntax in Code DSL or use a supported
condition path before saving.

## PolicyVersion, Review Diff, Runtime, And Telemetry

The PolicyVersion workflow is the safety boundary for policy changes:

- Save draft creates or updates a draft snapshot.
- Submit for review creates a PolicyVersionReviewRequest.
- Approval records reviewer intent; it does not activate the version.
- Activation is explicit and is not called Publish.
- Runtime Gateway and telemetry evaluate active `PolicyVersion` snapshots when
  available, with fallback to unversioned Policy/PolicyRule records for
  unversioned policies.
- `PolicyDecision.policy_version_id` is populated for new decisions when the
  matched rule comes from an active version.

Review diffs should compare compiled snapshots, not arbitrary DSL text. The
important diff units are:

- changed Policy fields;
- changed PolicyRule condition fields;
- changed PolicyCheckStep configuration;
- review metadata;
- activation and supersession evidence.

## Examples

Each example below shows the authoring DSL, compiled JSON sketch, plain-language
summary, and runtime effect. Runtime effect applies only after the draft is
reviewed, approved, and explicitly activated.

### 1. External High-Risk Action Requires Human Review

```text
policy external_action_control {
  scope production_systems

  when system.environment == "production"
    and action.type == "external_api_call"
    and action.risk in ["high", "critical"]

  then require_review("High-risk external action in production requires governance review.")
  prove decision, checks, reviewer, evidence_bundle
}
```

Compiled JSON sketch:

```json
{
  "action_type": "external_api_call",
  "decision": "require_human_review",
  "environment": "production",
  "reason": "High-risk external action in production requires governance review.",
  "risk_level": ["high", "critical"]
}
```

Summary: production external API calls with high or critical risk require human
review.

Runtime effect after activation: Runtime Gateway and telemetry return
`require_human_review` for matching requests and record PolicyDecision evidence.

### 2. Confidential Data Vectorization Guard

```text
policy confidential_vectorization_guard {
  scope data_governance

  when action.type == "vectorization"
    and data.classification == "confidential"
    and source.classification == "confidential"
    and model.provider_type == "external"
    and model.type == "embedding"

  check data_usage.review_status == "approved" required
  check data_usage.allowed_purpose == "vectorization" required
  check access_grant.status == "active" required
  check check.outcome == "pass" required

  then require_review("Vectorizing confidential data with an external embedding model requires approved usage and active access.")
  prove decision, checks, reviewer, evidence_bundle
}
```

Compiled JSON sketch:

```json
{
  "access_grant_status": "active",
  "action_type": "vectorization",
  "check_outcome": "pass",
  "data_classification": "confidential",
  "data_usage_allowed_purpose": "vectorization",
  "data_usage_review_status": "approved",
  "decision": "require_human_review",
  "model_provider_type": "external",
  "model_type": "embedding",
  "reason": "Vectorizing confidential data with an external embedding model requires approved usage and active access.",
  "source_data_classification": "confidential"
}
```

Summary: confidential vectorization through an external embedding provider is
review-gated and expects approved data usage, active access, and passing checks.

Runtime effect after activation: matching runtime requests are escalated to
human review. The caller/orchestrator remains responsible for honoring
`proceed=false`.

### 3. External Model Usage Guard

```text
policy external_model_usage_guard {
  scope model_governance

  when model.provider_type == "external"
    and action.risk == "high"

  check model.status == "active" required
  check check.type == "model_asset_status" required
  check check.outcome == "pass" required

  then require_review("External high-risk model usage requires model governance review.")
  prove decision, checks, reviewer, evidence_bundle
}
```

Compiled JSON sketch:

```json
{
  "check_outcome": "pass",
  "check_type": "model_asset_status",
  "decision": "require_human_review",
  "model_provider_type": "external",
  "model_status": "active",
  "reason": "External high-risk model usage requires model governance review.",
  "risk_level": "high"
}
```

Summary: high-risk use of external model providers requires reviewer oversight
when model status and check outcome match.

Runtime effect after activation: matching decisions carry the active
`policy_version_id` and can appear in Evidence Bundle summaries.

### 4. Require Active Access Grant

```text
policy require_active_grant {
  scope source_access

  when source.ids in ["customer_cases", "contract_repository"]
    and request.purpose == "retrieval"

  check access_grant.status == "active" required

  then allow("Retrieval may proceed when an active Access Grant covers the requested source.")
  prove decision, checks, reviewer, evidence_bundle
}
```

Compiled JSON sketch:

```json
{
  "access_grant_status": "active",
  "decision": "allow",
  "purpose": "retrieval",
  "reason": "Retrieval may proceed when an active Access Grant covers the requested source.",
  "source_ids": ["customer_cases", "contract_repository"]
}
```

Summary: retrieval from listed sources is allowed only when the resolved access
grant status is active.

Runtime effect after activation: `source_ids` uses overlap matching with the
request source list. This is still governance policy evaluation; AccessGrants
are not credentials and AGCP does not execute the retrieval.

### 5. Hard Deny Restricted Data In Production

```text
policy hard_deny_restricted_data {
  scope production_data_boundary

  when system.environment == "production"
    and data.classification == "restricted"
    and data.contains_sensitive_data == true

  check source.status == "active" required

  then deny("Restricted sensitive data cannot be used by this production policy path.")
  prove decision, checks, reviewer, evidence_bundle
}
```

Compiled JSON sketch:

```json
{
  "contains_sensitive_data": true,
  "data_classification": "restricted",
  "decision": "deny",
  "environment": "production",
  "reason": "Restricted sensitive data cannot be used by this production policy path.",
  "source_status": "active"
}
```

Summary: restricted sensitive data in production is denied for the matching
policy path.

Runtime effect after activation: Runtime Gateway returns `deny` and
`proceed=false` for matching requests. The caller must still enforce that
decision at the integration boundary.

## Unsupported Syntax

The V1 DSL intentionally rejects broad language features:

- nested boolean logic;
- OR groups;
- NOT expressions;
- arithmetic;
- regex;
- function calls except the decision reason form;
- imports/includes;
- variables;
- loops;
- comments that carry hidden semantics;
- arbitrary JSON blocks;
- direct PolicyCheckStep authoring;
- direct activation or publish statements.

Unsupported lines are reported by local validation and block saving in Policy
Studio. This protects reviewers from believing that text was enforced when the
compiled `PolicyRule.condition` does not contain it.

## Non-Goals

- No generic policy engine.
- No OPA/Rego, Cedar, CEL, SQL, Python, or JavaScript execution.
- No production simulation engine.
- No direct Publish command.
- No automatic activation after approval.
- No legal certification claims.
- No fake impact metrics or compliance scores.
- No orchestration or AGCP-side tool execution.

## Future Work

Future work should remain narrowly scoped:

- decide whether DSL source should be saved as safe display metadata in
  `PolicyVersion` snapshots;
- add a full bidirectional Blocks editor for all supported fields;
- add explicit operator persistence only if the backend condition schema and
  runtime evaluator are extended safely;
- add OR-style authoring only after deterministic semantics and review diffs
  are designed;
- add PolicyCheckStep authoring after versioning/review and check execution
  semantics are stable;
- add richer field help and examples without introducing fake production
  simulation.
