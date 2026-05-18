# Runtime Gateway Resume Endpoint

## Status

Design proposal only. The backend does not currently implement
`POST /runtime/tool-calls/resume`. This document defines the intended V1
contract for resuming a governed tool call after HumanApproval.

The Agent Governance Control Plane remains a governance and evidence layer. It
does not execute tools, schedule workflows, own queues, or replace the
application runtime. The wrapper or adapter remains responsible for actual tool
execution.

## Purpose

Runtime Gateway enforcement can return `require_human_review` for a governed
tool call. In that case the wrapper must block local execution and wait for a
human reviewer to approve or reject the HumanApproval.

The resume endpoint answers one narrow question after review:

```text
May the wrapper now proceed with the previously blocked action?
```

It should:

- verify the HumanApproval exists and belongs to the original evidence chain;
- verify the approval status is compatible with resume;
- verify the submitted resume context still matches the original blocked
  request;
- preserve idempotency for repeated resume checks;
- record safe resume evidence when possible;
- return `proceed = true` only when the wrapper may execute the tool.

It should not:

- execute the tool;
- call external systems;
- hold workflow state beyond governance evidence;
- create a scheduler or queue worker;
- turn AGCP into an orchestrator.

## Proposed Endpoint

```http
POST /runtime/tool-calls/resume
```

The endpoint is intended for wrappers that previously received
`decision = "require_human_review"` from
`POST /runtime/tool-calls/decision`.

## Request Contract

### Fields

| Field | Required | Purpose |
| --- | --- | --- |
| `resume_id` | Yes | Stable idempotency key for this resume attempt. |
| `original_request_id` | Yes | The original Runtime Gateway `request_id` that produced `require_human_review`. |
| `agent_id` | Yes | Registered Agent owning the original request. |
| `run_id` | Yes | Agent Run containing the original request and resume attempt. |
| `tool_name` | Yes | Tool name from the original governed action. |
| `human_approval_id` | Yes | HumanApproval created for the original blocked action. |
| `policy_decision_id` | Yes | Original PolicyDecision that required human review. |
| `action_ref` | Yes | Safe application-owned reference to the local attempted action. |
| `correlation_id` | Yes | Integration correlation ID for review and tracing. |
| `metadata` | No | Safe metadata only. No raw prompts, credentials, or raw tool payloads. |

`action_ref` must be stable for the local attempted action and must not contain
raw tool inputs, raw prompts, credentials, authorization headers, private
customer data, or raw tool outputs.

### Example Request

```json
{
  "resume_id": "runtime-request-001:resume:001",
  "original_request_id": "runtime-request-001",
  "agent_id": "11111111-1111-4111-8111-111111111111",
  "run_id": "22222222-2222-4222-8222-222222222222",
  "tool_name": "send_email",
  "human_approval_id": "77777777-7777-4777-8777-777777777777",
  "policy_decision_id": "66666666-6666-4666-8666-666666666666",
  "action_ref": "support-ticket-123:follow-up-email",
  "correlation_id": "support-run-001",
  "metadata": {
    "ticket_category": "support"
  }
}
```

## Response Contract

### Fields

| Field | Purpose |
| --- | --- |
| `resume_id` | Echoes the stable resume idempotency key. |
| `original_request_id` | Echoes the original blocked request ID. |
| `decision` | `allow`, `deny`, `require_human_review`, or `not_applicable`. |
| `proceed` | `true` only when the wrapper may execute the tool. |
| `reason` | Safe explanation for the resume decision. |
| `human_approval_status` | Current HumanApproval status used for the decision. |
| `trace_event_id` | Resume TraceEventRecord ID when recorded. |
| `policy_decision_id` | Original PolicyDecision ID in V1. A future version may add a separate resume decision ID. |
| `human_approval_id` | HumanApproval used for resume validation. |

### Example Approved Response

```json
{
  "resume_id": "runtime-request-001:resume:001",
  "original_request_id": "runtime-request-001",
  "decision": "allow",
  "proceed": true,
  "reason": "Human approval is approved and the resume context matches.",
  "human_approval_status": "approved",
  "trace_event_id": "88888888-8888-4888-8888-888888888888",
  "policy_decision_id": "66666666-6666-4666-8666-666666666666",
  "human_approval_id": "77777777-7777-4777-8777-777777777777"
}
```

### Example Pending Response

```json
{
  "resume_id": "runtime-request-001:resume:001",
  "original_request_id": "runtime-request-001",
  "decision": "require_human_review",
  "proceed": false,
  "reason": "Human approval is still pending.",
  "human_approval_status": "pending",
  "trace_event_id": "88888888-8888-4888-8888-888888888888",
  "policy_decision_id": "66666666-6666-4666-8666-666666666666",
  "human_approval_id": "77777777-7777-4777-8777-777777777777"
}
```

## V1 Behavior

### Approved Approval And Matching Context

If the HumanApproval status is `approved` and the submitted context matches the
original blocked action:

- return `decision = "allow"`;
- return `proceed = true`;
- record a resume TraceEventRecord if persistence is available;
- do not execute the tool.

The wrapper may execute the local tool after receiving this response.

### Rejected Approval

If the HumanApproval status is `rejected`:

- return `decision = "deny"`;
- return `proceed = false`;
- explain that the action was rejected by review;
- do not create a new HumanApproval.

The wrapper must not execute the tool.

### Cancelled Approval

If the HumanApproval status is `cancelled`:

- return `decision = "deny"`;
- return `proceed = false`;
- explain that the approval request was cancelled.

The wrapper must treat the original action as blocked.

### Expired Approval

If the HumanApproval status is `expired`, or `expires_at` has passed:

- return `decision = "deny"`;
- return `proceed = false`;
- explain that the approval is expired.

V1 should reject resume after expiry even if the approval was previously
approved. Later designs can decide whether approved decisions may have a
separate execution window.

### Pending Approval

If the HumanApproval status is `pending`:

- return `decision = "require_human_review"`;
- return `proceed = false`;
- preserve `human_approval_id` in the response.

The wrapper should continue polling, wait for notification, or time out
according to its own integration behavior.

### Context Changed

If the submitted resume context does not match the original blocked action:

- return `decision = "deny"` or a clear conflict response;
- return `proceed = false`;
- explain which safe context field failed to match when possible.

V1 should compare at least:

- `agent_id`;
- `run_id`;
- `original_request_id`;
- `tool_name`;
- `policy_decision_id`;
- `human_approval_id`;
- `action_ref`.

Later versions can add a structured context hash and policy version references.

### Unknown Approval

If `human_approval_id` is unknown:

- return `404`;
- do not create a resume TraceEventRecord;
- do not create a PolicyDecision;
- do not claim evidence was recorded.

### Mismatched IDs

The endpoint must reject mismatched chains. Examples:

- `human_approval_id` exists but belongs to a different Agent;
- `human_approval_id` does not point to the submitted `policy_decision_id`;
- `policy_decision_id` belongs to a different Agent;
- `policy_decision_id` is not linked to the original `TraceEventRecord`;
- `original_request_id` does not match the original trace event external event
  ID;
- `tool_name` differs from the original request.

These should return `400`, `404`, or `409` depending on whether the problem is
missing data, invalid input, or evidence-chain conflict. In all cases,
`proceed` must not be `true`.

## Idempotency Rules

Resume idempotency is separate from the original decision idempotency.

Recommended keys:

- original decision key: `agent_id`, `run_id`, `original_request_id`;
- resume key: `agent_id`, `run_id`, `resume_id`.

Rules:

- `resume_id` must be stable for one resume attempt.
- Retries with the same `resume_id` must return the existing resume response.
- A duplicate resume request must not create duplicate TraceEventRecord rows.
- A duplicate resume request must not create duplicate PolicyDecision rows if a
  future resume PolicyDecision is added.
- A duplicate resume request must not create duplicate AuditLog rows.
- A new action after rejection, cancellation, expiry, or material context change
  must use a new original `request_id`, not reuse the old approval.
- The wrapper remains responsible for preventing duplicate local tool
  execution after receiving an allow response.

The control plane can make resume checks idempotent. It cannot guarantee that a
local tool or external system is idempotent.

## Evidence Expectations

The resume endpoint should keep the evidence chain navigable without nesting
large objects.

### Original Blocked Action

```text
TraceEventRecord(original tool_call_requested)
  -> PolicyDecision(require_human_review)
  -> HumanApproval(pending)
  -> AuditLog(human_approval_requested)
```

### Human Review

```text
HumanApproval(approved, rejected, cancelled, or expired)
  -> AuditLog(human_approval_approved or human_approval_rejected)
```

Cancellation and expiration should also be auditable when implemented as
explicit mutations.

### Resume Attempt

```text
TraceEventRecord(resume requested)
  -> original PolicyDecision reference
  -> HumanApproval reference
```

V1 can use the original `policy_decision_id` in the response. A later version
may add an optional resume PolicyDecision to distinguish:

- original decision: `require_human_review`;
- resume decision: `allow`, `deny`, or `require_human_review`.

### Optional AuditLog

An AuditLog for resume checks may be useful when:

- a resume attempt returns `proceed = true`;
- a resume attempt is rejected due to stale context;
- a replay attempt is detected;
- a resume attempt references mismatched evidence.

If AuditLog is required for a resume mutation and audit persistence fails, the
transaction should roll back. The endpoint should not claim evidence it did not
store.

### Evidence Bundle

Evidence Bundle export should eventually include:

- original TraceEventRecord ID;
- original PolicyDecision ID;
- HumanApproval ID and final status;
- review AuditLog IDs;
- resume TraceEventRecord ID;
- optional resume PolicyDecision ID;
- safe action references and summaries;
- no raw prompts, credentials, authorization headers, raw tool payloads, or
  private customer data.

## Security Risks

### Replay Attack

An attacker or buggy integration could reuse an old approval for a different
action. V1 must bind resume to `agent_id`, `run_id`, `original_request_id`,
`tool_name`, `policy_decision_id`, `human_approval_id`, and `action_ref`.

### Stale Approval

The reviewed context may be outdated by the time resume is requested. V1 should
deny obvious mismatches and later add context hashes, approval windows, and
policy version checks.

### Changed Context

Agent environment, risk level, policy version, tool name, or local application
state may have changed. The endpoint should not silently allow execution when
the submitted context no longer matches the reviewed action.

### Duplicate Execution

Idempotent resume responses do not automatically make tool execution
idempotent. The wrapper must use local execution locks or external idempotency
keys before calling side-effecting tools.

### Wrapper Bypass

The endpoint protects only integrations that call it. Direct tool calls outside
the wrapper are outside AGCP's control. Later evidence coverage reporting can
help identify bypass.

### Missing Auth/RBAC

Current development actors are placeholders. Production resume behavior needs
real Actor identity for:

- the reviewer;
- the integration calling resume;
- authorization to inspect HumanApproval state;
- authorization to proceed after approval.

### Unsafe Metadata

Resume metadata must use the same centralized safe metadata rules as telemetry,
audit, and runtime decisions. Unsafe keys or raw sensitive payloads must be
rejected before persistence.

## Recommended Follow-up Issues

1. Add Pydantic schemas for `RuntimeToolCallResumeRequest` and
   `RuntimeToolCallResumeResponse`.
2. Add `POST /runtime/tool-calls/resume` behind tests, without executing tools.
3. Add idempotency for `agent_id`, `run_id`, and `resume_id`.
4. Add chain validation for `original_request_id`, `policy_decision_id`, and
   `human_approval_id`.
5. Add context matching using `tool_name`, `action_ref`, Agent environment, and
   risk level.
6. Add approval expiration enforcement for resume.
7. Add resume TraceEventRecord persistence.
8. Decide whether V1 needs a resume PolicyDecision or should reference the
   original PolicyDecision only.
9. Add optional AuditLog records for successful resume, stale context, and
   replay detection.
10. Add Evidence Bundle links for original request, approval review, and resume
    attempt.
11. Add wrapper example updates showing resume polling and resume request
    handling without raw payloads.
12. Add auth/RBAC design for reviewers and runtime integrations before
    production enforcement.

## Open Questions

- Should an approved HumanApproval permit exactly one successful resume decision
  or many idempotent retries of the same resume decision?
- Should resume re-evaluate current policy, or only validate the original
  approved PolicyDecision and context?
- Should a resume `allow` create a new PolicyDecision, or should the original
  PolicyDecision remain the only decision record?
- Which context fields are mandatory for V1 before a context hash exists?
- Should approval expiry be based on review time, resume time, or execution
  completion time reported later by telemetry?
- Should rejected or stale resume attempts create AuditLog records immediately,
  or only TraceEventRecord evidence?
