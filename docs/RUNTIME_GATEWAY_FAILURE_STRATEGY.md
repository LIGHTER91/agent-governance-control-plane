# Runtime Gateway Failure Strategy

## Status

Design proposal only. The current backend implements Runtime Gateway
request/response schemas, simulation mode, and enforcement mode behind
`AGCP_RUNTIME_ENFORCEMENT_ENABLED=false` by default. Telemetry mode for
`POST /runtime/tool-calls/decision` is not implemented yet.

This document defines failure behavior for future Runtime Gateway modes. It does
not implement enforcement, change existing endpoint behavior, add SDK behavior,
or claim legal compliance.

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

## Recommended Follow-up Issues

1. Add enforcement failure-path tests for the configured runtime endpoint.
2. Add an enforcement failure-policy configuration model.
3. Add audit logging for enforcement and failure-policy configuration changes.
4. Add tests for fail-closed behavior on unknown Agent, unsafe metadata,
   database errors, policy errors, and `not_applicable`.
5. Add tests for high and critical risk fail-closed defaults.
6. Add an explicit design for representing runtime failure decisions without
   overloading `not_applicable`.
7. Add Evidence Bundle coverage for future runtime failure records.
8. Add integration guidance for client-side behavior when the gateway is
   unavailable or times out.

## Open Questions

- Should a future failure decision use a new decision value or stay as an error
  response outside `RuntimeToolCallDecisionResponse`?
- Should low-risk development actions ever fail open by default, or only by
  explicit per-tool configuration?
- How much local buffering should adapters provide when the gateway is
  unavailable?
- What latency budget should trigger a policy timeout in enforcement mode?
- Should enforcement configuration be versioned before production use?
