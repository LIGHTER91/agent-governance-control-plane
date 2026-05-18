# Runtime Gateway Failure Strategy

## Status

Design proposal with current implementation notes. The current backend
implements Runtime Gateway request/response schemas, simulation mode,
enforcement mode behind `AGCP_RUNTIME_ENFORCEMENT_ENABLED=false` by default, and
minimal `AGCP_RUNTIME_FAILURE_DEFAULT` handling for internal policy evaluation
failures. Telemetry mode for `POST /runtime/tool-calls/decision` is not
implemented yet.

This document defines failure behavior for current and future Runtime Gateway
modes. It does not add SDK behavior, implement per-agent or per-tool failure
configuration, or claim legal compliance.

## Why Failure Behavior Matters

In telemetry and simulation, a Runtime Gateway failure is mostly an evidence and
operability problem. In enforcement mode, the same failure can become a control
problem because the agent integration may be waiting for a decision before
executing a governed tool call or external action.

Fail-open behavior can preserve application availability, but it can also let an
unknown or risky action proceed without a governance decision. Fail-closed
behavior gives stronger control, but it can block legitimate work during outages
or policy errors. The gateway should therefore make failure behavior explicit,
recordable, and reviewable.

The default posture should be conservative until the product has mature policy
versioning, integration-specific configuration, and operational evidence.

## Failure Categories

### Gateway Unavailable

The integration cannot reach the Runtime Gateway, or the gateway process is down.
The gateway may not be able to record any evidence because it never receives the
request.

### Database Unavailable

The gateway receives the request but cannot read or write PostgreSQL. Agent
lookup, idempotency checks, TraceEventRecord persistence, PolicyDecision
persistence, HumanApproval creation, and AuditLog persistence may all be
unavailable.

### Policy Evaluation Error

Policy loading, PolicyRule conversion, or deterministic evaluation fails. An
example is a persisted PolicyRule condition with unsupported fields.

### Policy Timeout

Policy evaluation does not finish within the configured latency budget. The V0
evaluator is local and deterministic, but future adapters or configuration could
still impose a timeout.

### Duplicate Request Conflict

A request repeats the same `agent_id`, `run_id`, and `request_id`, but the
existing stored records are incomplete, inconsistent, or do not match the
expected runtime decision chain.

### Audit Persistence Failure

The gateway cannot append an AuditLog for a governance-relevant mutation such as
HumanApproval creation.

### PolicyDecision Persistence Failure

The gateway evaluates a policy result but cannot persist the PolicyDecision
record.

### HumanApproval Creation Failure

The policy result is `require_human_review`, but the gateway cannot create the
pending HumanApproval.

### Unsafe Metadata

The request metadata contains unsafe keys such as credentials, tokens,
authorization headers, raw prompts, raw payloads, or private customer data.

### Unknown Agent

The request references an `agent_id` that does not exist in the Agent Registry.

### No Matching Policy / Not Applicable

Policy evaluation succeeds but no active PolicyRule matches the request. The
result is `not_applicable`, not a platform error.

## Default Behavior By Mode

### Telemetry Mode

Telemetry mode should preserve safe observations when possible.

- Gateway unavailable: the integration may buffer or retry locally, but the
  control plane cannot record evidence until it receives the event.
- Database unavailable: return a retryable error; do not pretend the observation
  was recorded.
- Policy evaluation error or timeout: record the TraceEventRecord when safe and
  possible, then record an error-oriented PolicyDecision only after the model
  explicitly supports that representation. Until then, return a clear error.
- Duplicate request conflict: return a conflict response and avoid creating
  duplicate records.
- Audit, PolicyDecision, or HumanApproval persistence failure: rollback the
  transaction so evidence is not partial.
- Unsafe metadata: reject the event. Do not store unsafe metadata.
- Unknown agent: reject the event because evidence must attach to a registered
  Agent.
- `not_applicable`: record the observation and PolicyDecision when evaluation
  runs successfully. Telemetry mode does not claim action blocking.

Telemetry mode should not be described as preventing actions. It is an
observation and evidence path.

### Simulation Mode

Simulation mode should record what the gateway would decide, while being clear
that the integration is not required to block the action.

- Gateway unavailable: the integration should treat the simulation as
  unavailable and may proceed according to its own non-enforcement behavior.
- Database unavailable: return a retryable error; do not claim a simulated
  decision was recorded.
- Policy evaluation error or timeout: return a clear error and rollback any
  partial records.
- Duplicate request conflict: return a conflict response if the existing
  decision chain is incomplete or inconsistent; otherwise return the existing
  response.
- Audit, PolicyDecision, or HumanApproval persistence failure: rollback the
  TraceEventRecord, PolicyDecision, HumanApproval, and AuditLog together.
- Unsafe metadata: reject the request.
- Unknown agent: reject the request.
- `not_applicable`: return `decision = "not_applicable"` and `proceed = false`
  under the current schema rule, while documenting that simulation does not
  enforce action blocking.

Simulation mode should be used to tune policies, inspect evidence, and measure
operational impact before enforcement.

### Enforcement Mode

Enforcement mode should default to fail-closed for ambiguous, unsafe, or
high-risk cases until explicit configuration exists.

- Gateway unavailable: deny by default for high and critical risk actions. Lower
  risk actions may later be configurable, but the initial enforcement default
  should be fail-closed.
- Database unavailable: deny by default because the gateway cannot validate the
  Agent, policies, idempotency, or evidence writes.
- Policy evaluation error: deny by default. A broken policy should not silently
  permit a governed action.
- Policy timeout: deny by default, especially for high and critical risk
  actions.
- Duplicate request conflict: deny until the existing decision chain can be
  reconciled.
- Audit persistence failure: deny and rollback. Enforcement decisions without
  auditability weaken the evidence chain.
- PolicyDecision persistence failure: deny and rollback. The gateway should not
  return an enforcement decision that cannot be recorded.
- HumanApproval creation failure: deny and rollback when the decision requires
  human review.
- Unsafe metadata: deny and do not store unsafe metadata.
- Unknown agent: deny. An unregistered Agent has no governed identity,
  ownership, environment, risk classification, or policy context.
- `not_applicable`: deny by default for now. A later configuration may allow
  fail-open for specific low-risk tools, Agents, or environments.

Enforcement mode should only be enabled after the integration owner accepts the
latency, availability, retry, and failure behavior.

## Representation In Evidence Records

### RuntimeToolCallDecisionResponse

For successful decisions, the response should keep the existing shape:

- `decision`: `allow`, `deny`, `require_human_review`, or `not_applicable`;
- `proceed`: `true` only for `allow`;
- `reason`: concise explanation safe for review;
- `trace_event_id`, `policy_decision_id`, and `human_approval_id` when created.

For failures before a reliable decision is created, the API should return a
clear error response rather than fabricating a successful decision response.
Future enforcement work may add an explicit failure decision representation, but
that should be designed before changing the response schema.

### TraceEventRecord

When a request is safe and the database is available, the gateway should record
a `tool_call_requested` TraceEventRecord before evaluating policy. For failures
that happen after the trace event is created, transaction rollback should avoid
partial evidence unless a dedicated failure TraceEventType is introduced later.

Unsafe metadata must not be stored in TraceEventRecord. If metadata is unsafe,
the request should be rejected before persistence.

### PolicyDecision

PolicyDecision should represent deterministic policy evaluation results. For
now, failures such as database outages, unsupported policy conditions, and
timeouts should not be forced into the four existing decision values unless the
meaning is precise.

`not_applicable` should remain reserved for successful evaluation with no
matching rule. It should not be used as a generic error bucket.

### AuditLog

AuditLog should record governance-relevant mutations, especially HumanApproval
creation and later enforcement configuration changes. If an AuditLog cannot be
written for a mutation that requires auditability, the whole transaction should
rollback.

Future enforcement configuration changes should create audit records such as:

- fail-open/fail-closed default changed;
- per-tool failure behavior changed;
- enforcement mode enabled or disabled;
- risk-level failure behavior changed.

### Evidence Bundle

Evidence Bundle export should show the stored chain for completed decisions:

```text
TraceEventRecord -> PolicyDecision -> HumanApproval -> AuditLog
```

If a request fails before records are persisted, there may be no bundle evidence
for that request. Integration-side logs may exist, but the control plane should
not claim evidence that it did not store.

When future failure decision records are introduced, Evidence Bundle export
should include them with clear reasons and links to the triggering TraceEvent.

## Future Configuration Options

The first enforcement implementation should start with conservative defaults.
Later configuration can relax behavior in specific, reviewable places.

Potential options:

- Per-Agent default decision for `not_applicable`.
- Per-tool fail-open or fail-closed setting.
- Environment-specific behavior, such as fail-open in development and
  fail-closed in production.
- Risk-level-specific behavior, such as fail-closed for high and critical risk.
- Per-integration timeout budgets.
- Per-Agent or per-tool retry policy.
- Explicit handling for gateway unavailable versus policy evaluation failure.
- Approval expiration behavior for `require_human_review`.

All configuration changes should be audited and included in later evidence
exports where relevant.

## Future Failure Policy Configuration Model

The first configurable failure policy should be deliberately small. Its purpose
is to decide what the Runtime Gateway and adapter should do when the gateway
cannot produce a normal policy evaluation result, not to replace the policy
evaluator.

This model is future work. It should not be implemented until the team is ready
to persist configuration, audit configuration changes, and test failure paths.

### Configuration Dimensions

The model should support these dimensions:

- Global default behavior: the baseline for all runtime requests.
- Per-Agent override: behavior for a specific registered Agent.
- Per-tool override: behavior for a specific governed `tool_name`.
- Per-environment override: behavior for development, staging, or production.
- Per-risk-level override: behavior for low, medium, high, or critical risk.

A minimal persisted configuration could contain:

```json
{
  "scope_type": "tool",
  "scope_id": "send_email",
  "environment": "production",
  "risk_level": "high",
  "failure_category": "gateway_unavailable",
  "failure_decision": "fail_closed_deny",
  "reason": "Email tool calls must not proceed without a gateway decision."
}
```

The exact schema should be designed during implementation. V1 should avoid a
large expression language. Simple exact-match scopes are enough.

### Failure Decisions

Supported failure decisions should be:

- `fail_closed_deny`: do not allow the action to proceed.
- `fail_closed_human_review`: do not allow the action to proceed; create or
  request a HumanApproval when persistence is available.
- `fail_open_allow`: allow the action to proceed despite the failure. This must
  be restricted to explicitly configured low-risk cases.
- `record_only`: record the failure when possible, but do not claim blocking.
  This is appropriate for telemetry and simulation contexts, not enforcement
  control.

`fail_open_allow` should never be the global default. It should require a narrow
scope such as low-risk development, a specific low-risk tool, or a specific
Agent whose owner has accepted the behavior.

Current implementation note: the only runtime failure policy configuration
available in code is the global `AGCP_RUNTIME_FAILURE_DEFAULT` value. It accepts
`fail_closed_deny`, `fail_closed_human_review`, and `record_only`.
It is applied only to internal policy evaluation failures where the gateway can
return a controlled decision response. Unknown Agent, unsafe metadata, invalid
mode, enforcement-disabled, and persistence-failure paths remain hard errors.
`fail_open_allow` is intentionally not accepted yet.

### Precedence Rules

When multiple configuration levels match a runtime request, the gateway should
choose the most specific safe match.

Recommended precedence:

1. Hard safety rules.
2. Per-Agent + per-tool + per-environment + per-risk-level exact override.
3. Per-Agent + per-tool override.
4. Per-Agent override.
5. Per-tool override.
6. Per-environment override.
7. Per-risk-level override.
8. Global default.

Hard safety rules always win. These include:

- unsafe metadata always denies;
- unknown Agent always denies;
- high and critical risk actions cannot fail open by default;
- audit persistence failure denies in enforcement when an audited mutation is
  required;
- PolicyDecision persistence failure denies in enforcement when a decision would
  otherwise be returned as successful.

If two equally specific rules conflict, the safer outcome should win in this
order:

1. `fail_closed_deny`
2. `fail_closed_human_review`
3. `record_only`
4. `fail_open_allow`

This is intentionally conservative. It reduces surprising fail-open behavior at
the cost of occasionally blocking work until configuration is cleaned up.

### Safe Defaults

Recommended defaults:

- Enforcement mode default: `fail_closed_deny`.
- Telemetry mode default: `record_only` when safe persistence is available;
  otherwise return a retryable error.
- Simulation mode default: `record_only` for unavailable gateway behavior in
  the adapter, and rollback partial server records when the backend has already
  started a transaction.
- High and critical risk: cannot use `fail_open_allow` unless a later, explicit
  exception model is designed.
- Unknown Agent: always deny.
- Unsafe metadata: always deny and do not persist unsafe metadata.
- Audit persistence failure: deny and rollback in enforcement when audit is
  required.
- PolicyDecision persistence failure: deny and rollback in enforcement when the
  gateway would otherwise return a decision.
- HumanApproval creation failure: deny and rollback when the failure decision or
  policy decision requires human review.

### Representation In RuntimeToolCallDecisionResponse

For V1, failures that happen before a reliable decision can be persisted should
continue to return clear API errors instead of pretending to be normal policy
decisions.

When a future failure policy is successfully applied and recorded, the response
could reuse the existing response shape:

- `decision = "deny"` for `fail_closed_deny`;
- `decision = "require_human_review"` for `fail_closed_human_review`;
- `decision = "allow"` for narrowly configured `fail_open_allow`;
- `decision = "not_applicable"` should not be used for runtime failures;
- `reason` should identify the failure category and selected failure policy;
- `proceed` must follow the normal decision/proceed rules.

The response should not add a new public decision value until the model has a
clear persistence and evidence representation.

### Representation In PolicyDecision

PolicyDecision should remain the record of the outcome returned to the
integration. When a failure policy drives the outcome, the persisted
PolicyDecision should include safe context such as:

- failure category;
- selected failure decision;
- configuration scope that matched;
- configuration version if versioning exists;
- short reason safe for review.

This can be stored through a future structured field or context reference. It
should not store raw prompts, raw tool inputs, raw tool outputs, credentials, or
private data.

`not_applicable` should remain reserved for successful evaluation with no
matching rule. It should not be used as a generic failure bucket.

### Representation In AuditLog

AuditLog should record governance-relevant failure policy events, including:

- failure policy configuration created, changed, disabled, or deleted;
- enforcement mode enabled or disabled;
- fail-open exception configured;
- failure policy selected `fail_closed_human_review` and created a
  HumanApproval;
- failure policy selected `fail_open_allow` for a governed action.

The audit metadata should contain only safe identifiers and summaries:

- configuration ID or version;
- scope type and scope ID;
- failure category;
- failure decision;
- Agent ID;
- tool name;
- environment;
- risk level.

### Representation In Evidence Bundle

Evidence Bundle export should show failure-policy-driven decisions in the same
reviewable chain as normal decisions:

```text
TraceEventRecord -> PolicyDecision -> optional HumanApproval -> AuditLog
```

When a fail-open decision is allowed by configuration, the Evidence Bundle
should make that explicit by including the matched failure policy reference and
the reason. Reviewers should be able to distinguish:

- a normal `allow` from policy evaluation;
- a fail-open `allow` caused by failure policy;
- a fail-closed `deny`;
- a human-review escalation caused by failure policy.

If a failure happens before the backend can persist evidence, the bundle cannot
represent that request. The control plane should not claim evidence it did not
store.

## V1 Versus Future Work

### V1 Implementation Scope

V1 should include only:

- a global default failure policy for enforcement set to `fail_closed_deny`;
- hard safety rules for unknown Agent and unsafe metadata;
- rollback behavior for audit, PolicyDecision, and HumanApproval persistence
  failures;
- tests proving high and critical risk requests do not fail open;
- safe audit records for configuration changes if configuration persistence is
  introduced;
- documentation of adapter behavior when the gateway is unavailable or times
  out.

### Future Work

Later work can add:

- persisted per-Agent overrides;
- persisted per-tool overrides;
- persisted per-environment overrides;
- persisted per-risk-level overrides;
- failure policy versioning;
- fail-open exception review and expiration;
- UI for reviewing configured failure behavior;
- Evidence Bundle references to specific failure policy versions;
- typed failure records if API errors are not enough for review needs.

## Recommended Follow-up Issues

1. Add V1 enforcement failure-path tests for unknown Agent, unsafe metadata,
   database errors, policy errors, audit failures, PolicyDecision persistence
   failures, and HumanApproval creation failures.
2. Add a global enforcement failure policy setting with default
   `fail_closed_deny`.
3. Add hard safety rule tests proving unknown Agent and unsafe metadata always
   deny in enforcement.
4. Add tests proving high and critical risk actions cannot fail open by default.
5. Design and implement persisted failure policy configuration with global,
   Agent, tool, environment, and risk-level scopes.
6. Add audit logging for failure policy configuration changes and fail-open
   exceptions.
7. Add Evidence Bundle references for failure-policy-driven PolicyDecision
   records.
8. Add a design for expiring or reviewing fail-open exceptions.
9. Add integration guidance for adapter behavior when the gateway is unavailable
   or times out.

## Open Questions

- Should a future failure decision use a new decision value or stay as an error
  response outside `RuntimeToolCallDecisionResponse`?
- Should low-risk development actions ever fail open by default, or only by
  explicit per-tool configuration?
- How much local buffering should adapters provide when the gateway is
  unavailable?
- What latency budget should trigger a policy timeout in enforcement mode?
- Should enforcement configuration be versioned before production use?
