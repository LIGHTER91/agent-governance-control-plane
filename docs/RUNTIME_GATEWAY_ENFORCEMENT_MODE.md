# Runtime Gateway Enforcement Mode

## Status

Design proposal only. Runtime Gateway enforcement mode is not implemented yet.
The current Runtime Gateway endpoint supports simulation mode and rejects
telemetry and enforcement modes.

This document defines how enforcement mode should behave when it is implemented
inside the Agent Governance Control Plane. It does not change endpoint behavior,
add an SDK, add a LangGraph integration, or claim legal compliance.

## What Enforcement Mode Means

Enforcement mode means an agent integration asks the Runtime Gateway for a
governance decision before executing a governed action, then honors the returned
`proceed` value.

The gateway is responsible for:

- validating the registered Agent and request shape;
- applying deterministic policy evaluation;
- creating governance evidence such as TraceEventRecord, PolicyDecision,
  HumanApproval, AuditLog, and Evidence Bundle links;
- returning a decision that the integration can enforce.

The gateway is not responsible for:

- executing tools;
- calling external systems on behalf of the agent;
- scheduling or resuming agent workflows;
- replacing LangGraph, n8n, Dataiku, CrewAI, AutoGen, cloud AI platforms, or MCP
  servers.

The adapter or wrapper around the agent runtime remains responsible for the
actual tool invocation. Enforcement only works when that adapter consistently
calls the gateway before the action and refuses to execute when `proceed` is
`false`.

## Simulation Versus Enforcement

| Mode | Purpose | Tool execution responsibility | Decision effect |
| --- | --- | --- | --- |
| Simulation | Evaluate and record what the gateway would decide. | The adapter or application still owns execution behavior. | Advisory for policy tuning and evidence review. |
| Enforcement | Decide whether a governed action may proceed. | The adapter or wrapper must execute only when the gateway returns `proceed = true`. | Binding for the integrated action path. |

Simulation is useful before enforcement because it lets teams test policy
coverage, false positives, latency, idempotency, and evidence quality without
claiming that actions are blocked.

Enforcement is appropriate only after the integration owner accepts the latency,
availability, failure, retry, and human approval behavior. It should be enabled
explicitly, not as an accidental side effect of adding telemetry.

## Enforcement Contract

The enforcement contract uses the same RuntimeToolCallDecisionRequest and
RuntimeToolCallDecisionResponse shape described in
`docs/RUNTIME_GATEWAY_DESIGN.md`.

### Allow

`allow` means the policy evaluator found a matching rule that permits the
governed action.

V1 response behavior:

- `decision = "allow"`
- `proceed = true`
- `trace_event_id` is present when evidence was recorded;
- `policy_decision_id` is present when the decision was persisted;
- `human_approval_id` is null.

Adapter behavior:

- execute the requested tool or external action;
- do not broaden the action beyond the submitted request;
- keep raw prompts, credentials, and raw tool payloads out of logs and metadata.

### Deny

`deny` means the policy evaluator found a matching rule that blocks the governed
action.

V1 response behavior:

- `decision = "deny"`
- `proceed = false`
- `reason` explains the denial in safe reviewable language;
- `trace_event_id` and `policy_decision_id` are present when evidence was
  recorded;
- `human_approval_id` is null.

Adapter behavior:

- do not execute the requested tool or external action;
- return a controlled denial result to the agent application;
- avoid retrying with modified metadata to bypass the denial.

### Require Human Review

`require_human_review` means the policy evaluator found a matching rule that
requires a human decision before the action may proceed.

V1 response behavior:

- `decision = "require_human_review"`
- `proceed = false`
- `human_approval_id` is present when a pending HumanApproval was created;
- `trace_event_id` and `policy_decision_id` are present when evidence was
  recorded.

Adapter behavior:

- do not execute the requested tool or external action;
- surface the pending review state and `human_approval_id`;
- wait for a future approval resolution pattern before resuming or retrying the
  action.

### Not Applicable

`not_applicable` means policy evaluation completed successfully, but no active
PolicyRule matched the request.

V1 response behavior:

- `decision = "not_applicable"`
- `proceed = false`
- `reason` should explain that no applicable policy matched;
- no HumanApproval is created.

Adapter behavior:

- do not execute the requested tool or external action by default;
- treat the result as a policy coverage gap to review;
- do not silently fail open unless a later explicit configuration allows that
  for a specific Agent, tool, environment, or risk level.

## Default V1 Behavior

The initial enforcement behavior should be conservative:

| Decision | V1 `proceed` | Default action |
| --- | --- | --- |
| `allow` | `true` | Adapter may execute the submitted action. |
| `deny` | `false` | Adapter must not execute the action. |
| `require_human_review` | `false` | Adapter must not execute until approval is resolved. |
| `not_applicable` | `false` | Adapter must not execute by default. |

This default reduces the chance that ungoverned actions proceed silently. Later
configuration may allow narrower fail-open behavior, but only with explicit
audited settings.

## Human Approval Handling

When enforcement produces `require_human_review`, the gateway should return
immediately with a pending HumanApproval rather than holding the request open
until a reviewer acts.

V1 behavior:

- create a pending HumanApproval linked to the Agent and PolicyDecision;
- append a `human_approval_requested` AuditLog record;
- return `human_approval_id`;
- set `proceed = false`;
- do not execute the tool through the gateway.

The adapter must not execute the action while the HumanApproval is pending.

Future resume or retry behavior should be designed separately. A likely pattern
is:

1. The adapter stores the original attempted action reference and request ID.
2. A reviewer approves or rejects the HumanApproval through a separate workflow.
3. The application resumes the work only after it has confirmed approval.
4. The resumed action uses a clearly linked follow-up request or an approved
   retry pattern that preserves idempotency and evidence navigation.

AGCP should not own graph checkpointing, queueing, or workflow orchestration for
this pattern. It should provide the governance state and evidence links that an
integration can use.

## Failure Behavior

The default failure posture should follow
`docs/RUNTIME_GATEWAY_FAILURE_STRATEGY.md`: enforcement mode starts fail-closed
for ambiguous, unsafe, or unverifiable cases.

### Gateway Unavailable

If the adapter cannot reach the gateway, it cannot receive a reliable decision
or know whether evidence was recorded. The default enforcement behavior should
be no tool execution, especially for high and critical risk actions.

Later configuration may allow narrower fail-open behavior for low-risk
development actions, but V1 should not assume that.

### Timeout

A timeout should be treated like gateway unavailability. The adapter should use
an explicit timeout and avoid executing the governed action when no decision is
available.

The adapter may record local diagnostics, but it must not log raw prompts, raw
tool payloads, credentials, authorization headers, or private customer data.

### Database Failure

If the gateway cannot read or write PostgreSQL, it cannot validate the Agent,
load policies, preserve idempotency, or create the evidence chain. Enforcement
should return a clear failure and the adapter should not execute the action.

### Audit Failure

If the gateway cannot append required AuditLog records for governance-relevant
mutations such as HumanApproval creation, the transaction should roll back. The
gateway should not return a successful enforcement decision that cannot be
audited where audit is required.

### Unknown Agent

An unknown Agent has no registered owner, environment, risk level, policy
context, or evidence bundle identity. Enforcement should reject or deny the
request, and the adapter should not execute the action.

### Unsafe Metadata

Unsafe metadata should be rejected before persistence. This includes keys or
payloads that suggest credentials, tokens, authorization headers, raw prompts,
raw payloads, or private sensitive data.

The adapter should treat unsafe metadata rejection as a blocking integration
error in enforcement mode.

## Idempotency Requirements

`request_id` must be stable for one attempted governed action. Retries caused by
network errors, client timeouts, or duplicate submissions must reuse the same
`request_id` with the same `agent_id` and `run_id`.

The gateway should use `agent_id`, `run_id`, and `request_id` as the
idempotency key for runtime decisions. A duplicate request should return the
existing decision response and must not create duplicate:

- TraceEventRecord rows;
- PolicyDecision rows;
- HumanApproval rows;
- AuditLog rows;
- Evidence Bundle entries for the same attempted action.

If a duplicate request conflicts with an incomplete or inconsistent stored
evidence chain, enforcement should fail closed until the records can be
reconciled.

## Audit And Evidence Expectations

Every successful enforcement decision should be represented in the evidence
model where applicable:

- TraceEventRecord records the requested governed action.
- PolicyDecision records the deterministic policy result.
- HumanApproval records pending human review when required.
- AuditLog records governance-relevant mutations, especially HumanApproval
  creation and later review actions.
- Evidence Bundle export links the chain for review.

The expected review path for a human-review decision is:

```text
TraceEventRecord -> PolicyDecision -> HumanApproval -> AuditLog
```

For `allow`, `deny`, and `not_applicable`, the chain may not include
HumanApproval, but it should still include the TraceEventRecord and
PolicyDecision when the decision was successfully persisted.

Failures before persistence should return clear errors rather than claiming that
evidence exists. The control plane should not fabricate evidence after a
database, audit, or transaction failure.

## Minimal Implementation Path

1. Enable `mode = "enforcement"` behind explicit configuration.
2. Reuse the existing simulation workflow for Agent lookup, TraceEventRecord
   creation, policy loading, PolicyRule conversion, evaluation, PolicyDecision
   persistence, optional HumanApproval creation, AuditLog, idempotency, and
   Evidence Bundle links.
3. Return `proceed` according to enforcement rules:
   - `allow` -> `true`;
   - `deny` -> `false`;
   - `require_human_review` -> `false`;
   - `not_applicable` -> `false`.
4. Add tests for allow, deny, human review, and not applicable enforcement
   decisions.
5. Add a wrapper example for enforcement mode that executes a tool only when
   `proceed = true`.

Implementation should stay inside the existing FastAPI modular monolith. It
should not add a new service boundary, external policy engine, queue, workflow
engine, SDK dependency, or framework dependency.

## Trade-offs And Limitations

- Enforcement improves control only for integrations that consistently use the
  governed adapter path.
- Fail-closed defaults reduce silent bypass, but they can block legitimate work
  during outages or policy errors.
- Human approval introduces operational delay and needs a later resume or retry
  pattern.
- `not_applicable -> proceed false` is conservative, but it may be noisy until
  policy coverage is mature.
- The gateway cannot prevent direct calls to tools outside the wrapper.
- Evidence is only as complete as the requests that reach the control plane and
  commit successfully.

## Recommended Follow-up Issues

1. Implement Runtime Gateway enforcement mode behind explicit configuration.
2. Add enforcement-mode tests for allow, deny, require human review, and not
   applicable decisions.
3. Add enforcement-mode idempotency tests for duplicate `request_id` retries.
4. Add fail-closed tests for gateway errors, unknown Agent, unsafe metadata,
   audit failure, and PolicyDecision persistence failure.
5. Add an enforcement wrapper example that uses `mode = "enforcement"` and
   documents adapter responsibilities.
6. Design the HumanApproval resume or retry pattern for blocked actions.
7. Design audited configuration for future per-Agent, per-tool, environment,
   and risk-level fail-open or fail-closed settings.
8. Add Evidence Bundle tests for enforcement-mode decisions once the mode is
   implemented.

## Open Questions

- Should an approved HumanApproval unlock the original request ID or require a
  linked follow-up request ID?
- What configuration is required before any low-risk action can fail open?
- Should enforcement be enabled per Agent, per environment, per tool, or all
  three?
- What operational signal should alert teams that adapters are bypassing the
  gateway?
- Should runtime failure decisions get their own persisted representation
  instead of being returned only as API errors?
