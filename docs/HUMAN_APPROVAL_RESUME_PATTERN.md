# Human Approval Resume Pattern

## Status

Design plus minimal V1 implementation. The current backend can create pending
HumanApproval records, approve, reject, cancel, audit those transitions, include
them in Evidence Bundle export, and check runtime resume attempts through
`POST /runtime/tool-calls/resume`. It does not implement notifications,
workflow queues, production SDK behavior, or production framework adapters.

This document defines a safe resume pattern for governed actions that receive
`require_human_review` from the Runtime Gateway. The Agent Governance Control
Plane remains a governance and evidence layer. It does not execute tools,
schedule agent work, or replace the application runtime.

## Problem

Runtime Gateway enforcement can return:

```json
{
  "decision": "require_human_review",
  "proceed": false,
  "human_approval_id": "77777777-7777-4777-8777-777777777777"
}
```

When this happens, the wrapper must not execute the tool immediately. A human
reviewer must approve or reject the pending HumanApproval through a separate
workflow. The integration then needs a safe way to resume or retry the original
action after approval without creating duplicate executions, duplicate approval
records, or a broken evidence chain.

The control plane can hold the governance state, but it cannot safely own the
business execution because it does not know the application checkpoint, local
tool implementation, user-facing response flow, or framework-specific resume
mechanics.

## Lifecycle

1. The agent requests a governed tool call or external action.
2. The wrapper calls `POST /runtime/tool-calls/decision`.
3. The Runtime Gateway evaluates policy and returns `require_human_review`,
   `proceed = false`, and `human_approval_id`.
4. The wrapper blocks local execution and stores a safe local reference to the
   attempted action. It must not store raw prompts, credentials, or raw tool
   payloads in AGCP metadata.
5. A human reviewer approves or rejects the HumanApproval through the
   HumanApproval API.
6. The integration later checks approval status or receives a notification.
7. If approved, the integration may retry or resume the action with the same
   original request reference or a derived `resume_id`.
8. The evidence chain remains linked across the original request, approval
   decision, and any later resume attempt.

If the approval is rejected, cancelled, expired, or stale, the wrapper must not
execute the tool.

## Current HumanApproval API Baseline

The current API supports:

- `POST /human-approvals`
- `GET /human-approvals`
- `GET /human-approvals/{approval_id}`
- `GET /agents/{agent_id}/human-approvals`
- `POST /human-approvals/{approval_id}/approve`
- `POST /human-approvals/{approval_id}/reject`
- `POST /human-approvals/{approval_id}/cancel`

Current transition behavior is intentionally narrow:

- created approvals start as `pending`;
- only `pending` approvals can be approved, rejected, or cancelled;
- reviewer fields use the development placeholder until authentication exists;
- each mutation appends an AuditLog record;
- `policy_decision_id`, when present, must belong to the same Agent.

This is enough to record review state, but not enough to resume an action by
itself.

## Pattern Options

### Polling Approval Status

The wrapper stores the blocked action reference and periodically calls
`GET /human-approvals/{approval_id}`.

Benefits:

- simple to implement;
- no notification infrastructure;
- works with the current HumanApproval API;
- easy to reason about in tests and local demos.

Trade-offs:

- adds polling load;
- introduces delay between approval and resume;
- each integration must handle timeouts, expiration, and local state cleanup.

### Webhook Or Callback Later

AGCP sends a callback to the integration after approval or rejection.

Benefits:

- lower latency after review;
- avoids polling loops;
- better user experience for long-running workflows.

Trade-offs:

- requires endpoint registration and authentication;
- needs retry, signing, delivery logs, and replay protection;
- more operational complexity than V1 needs.

### Retry With Same `request_id`

The wrapper retries the same Runtime Gateway request after approval using the
same `agent_id`, `run_id`, and `request_id`.

Benefits:

- simple client-side idempotency story;
- clearly points to the original attempted action.

Trade-offs:

- the current idempotency behavior returns the existing decision for the same
  request, so using the same `request_id` cannot safely mean both "same blocked
  request" and "new approved execution attempt" without an explicit resume
  contract;
- mutating the meaning of the original decision would weaken audit navigation;
- duplicate client retries could accidentally execute the tool more than once if
  the wrapper is not careful.

The same `request_id` should be used for retries of the original decision
request. A future resume flow should prefer a distinct resume identifier linked
to the original request.

### Explicit Resume Endpoint

AGCP exposes an explicit resume endpoint:

```http
POST /runtime/tool-calls/resume
```

A minimal request would include:

```json
{
  "resume_id": "runtime-request-001:resume:001",
  "original_request_id": "runtime-request-001",
  "agent_id": "11111111-1111-4111-8111-111111111111",
  "run_id": "22222222-2222-4222-8222-222222222222",
  "human_approval_id": "77777777-7777-4777-8777-777777777777",
  "tool_name": "send_email",
  "action_summary": "Resume approved support follow-up email.",
  "metadata": {
    "ticket_category": "support"
  }
}
```

The endpoint would verify that:

- the HumanApproval exists;
- it belongs to the same Agent;
- it links to the original PolicyDecision;
- its status is `approved`;
- it has not expired;
- the resume request matches the original governed action closely enough for V1;
- the `resume_id` has not already produced an execution decision.

Benefits:

- explicit evidence for the resume attempt;
- avoids changing the original RuntimeToolCallDecisionResponse;
- supports idempotent resume retries;
- keeps tool execution in the wrapper.

Trade-offs:

- requires new API behavior;
- needs a strict action-matching rule;
- still needs the integration to hold or reconstruct the local action safely.

### Queue-based Worker Later

A future integration could enqueue blocked actions and have a worker resume them
after approval.

Benefits:

- useful for asynchronous or long-running agent applications;
- can centralize retry and timeout behavior inside the integration.

Trade-offs:

- introduces queue semantics outside AGCP;
- easy to slide toward workflow orchestration if boundaries are not explicit;
- requires careful deduplication to prevent repeated execution.

AGCP should not own the queue worker in V1. It can provide decisions, approval
state, and evidence identifiers that a worker uses.

## Recommended V1 Pattern

V1 should use polling plus an explicit resume request.

The recommended flow is:

1. Wrapper calls `POST /runtime/tool-calls/decision`.
2. If `require_human_review`, wrapper blocks local execution and stores:
   - `agent_id`;
   - `run_id`;
   - original `request_id`;
   - `trace_event_id`;
   - `policy_decision_id`;
   - `human_approval_id`;
   - safe local action reference owned by the integration.
3. Integration polls `GET /human-approvals/{approval_id}` until the approval is
   approved, rejected, cancelled, expired, or timed out.
4. If approved, integration sends an explicit resume request with a stable
   derived `resume_id`.
5. AGCP verifies approval state and records a resume attempt.
6. AGCP returns whether the wrapper may proceed.
7. Wrapper executes the tool only if the resume decision returns `proceed =
   true`.

V1 should not automatically execute the tool from AGCP after approval. The
wrapper remains responsible for execution because it owns the local runtime
state, tool implementation, credentials, and user interaction.

The dependency-free example at
`docs/examples/generic_runtime_adapter_example.py` demonstrates both the
blocking side of this pattern and a minimal resume check for arbitrary local
tool functions. It preserves `original_request_id`, `human_approval_id`, and
`policy_decision_id`, uses a stable `resume_id`, and still leaves actual tool
execution inside the wrapper.

## Idempotency Rules

Idempotency must prevent both duplicate evidence and duplicate execution.

Recommended rules:

- The original `request_id` remains stable for the first attempted governed
  action.
- Retries of the original Runtime Gateway request reuse the same `request_id`
  and return the same blocked decision.
- A resume attempt uses a derived `resume_id`, for example
  `runtime-request-001:resume:001`.
- The resume idempotency key should be `agent_id`, `run_id`, and `resume_id`.
- A duplicate resume request returns the existing resume decision response.
- A resume request must reference the original `request_id`,
  `policy_decision_id`, and `human_approval_id`.
- The HumanApproval must remain linked to the original PolicyDecision.
- A rejected, cancelled, expired, or stale approval must not be resumable.
- The wrapper must ensure the local tool execution is idempotent or guarded by
  its own execution lock.

The control plane can prevent duplicate governance records. It cannot by itself
guarantee that a client-side tool implementation is idempotent.

## Evidence Chain Design

The original blocked action should produce:

```text
TraceEventRecord(original request)
  -> PolicyDecision(require_human_review)
  -> HumanApproval(pending)
  -> AuditLog(human_approval_requested)
```

Review should add:

```text
HumanApproval(approved or rejected)
  -> AuditLog(human_approval_approved or human_approval_rejected)
```

An approved resume attempt adds runtime evidence without executing the tool:

```text
TraceEventRecord(resume attempt)
  -> original PolicyDecision reference
  -> HumanApproval reference
  -> AuditLog(runtime_tool_call_resume_checked)
```

If the wrapper executes the tool after an approved resume decision, future
telemetry may add:

```text
TraceEventRecord(tool_call_allowed or tool_call_completed)
```

Evidence Bundle export should make these links navigable without duplicating
large nested objects:

- original `trace_event_id`;
- original `policy_decision_id`;
- `human_approval_id`;
- review audit log IDs;
- resume `trace_event_id`;
- original `policy_decision_id` used for resume validation;
- resume audit log IDs;
- safe summaries and metadata only.

The bundle should not expose raw prompts, credentials, raw tool payloads,
authorization headers, or private customer data.

## Approval State Semantics

### Approved

Approval means a reviewer accepted the governed action represented by the
original PolicyDecision and safe summary. It does not mean AGCP has executed the
tool. The wrapper may only execute after the future resume contract confirms
that the approval is still valid for the attempted action.

### Rejected

Rejected means the wrapper must not execute the action. A later new attempt
should use a new request ID and should be evaluated as a new governed action.

### Cancelled

Cancelled means the approval request was withdrawn or invalidated. The wrapper
must not execute based on it.

### Expired

Expired approvals should not be resumable. The expiration check should compare
the approval expiry to the resume attempt time, not merely to the original
request time.

### Stale

An approval can become stale if relevant context changed after review, such as:

- tool name changed;
- action summary changed materially;
- Agent risk level changed;
- Agent environment changed;
- policy or rule version changed;
- local application state no longer matches the reviewed action.

V1 should treat obvious stale context as not resumable. Later versions can add a
structured context hash or policy version check.

## Risks

### Stale Approval

The reviewer may approve an action whose context changes before execution.
Mitigation: include original request identifiers, safe action summary, tool
name, Agent, environment, risk level, and later context hash in the resume
validation.

### Approval After Context Changed

Policies, Agent ownership, or risk classification may change while approval is
pending. Mitigation: record original policy and rule references, and decide
whether resume should re-evaluate current policy or honor the original approved
decision. V1 should prefer re-checking enough context to avoid surprising
execution.

### Duplicated Execution

A client retry after approval could execute the tool twice. Mitigation: require
stable `resume_id`, return existing resume decisions for duplicate requests, and
expect the wrapper to guard the actual tool execution.

### Malicious Replay

An old approval could be replayed for a different action. Mitigation: require
matching `agent_id`, `run_id`, original `request_id`, `policy_decision_id`,
`human_approval_id`, `tool_name`, and safe action reference. Later auth/RBAC
must also bind reviewer identity and integration identity.

### Expired Approvals

An approval may remain pending too long. Mitigation: use `expires_at`, reject
resume after expiry, and record expiration/cancellation behavior.

### Placeholder Reviewer Identity

Current reviewer identity uses the development placeholder because auth/RBAC is
not implemented. This is acceptable for V0 evidence shape, but not for
production-grade oversight. Future work must replace placeholders with real
Actor identity without changing the HumanApproval model shape.

### Wrapper Bypass

The wrapper may be skipped, or a tool may be called directly. Mitigation:
integrations should make the governed wrapper the only approved action path and
later compare runtime evidence against expected action coverage.

## Recommended Follow-up Issues

1. Add `GET /human-approvals/{approval_id}` examples focused on polling for
   pending, approved, rejected, cancelled, and expired states.
2. Add approval expiration enforcement before resume if not already covered by
   current status checks.
3. Add stronger context matching for resume attempts using structured context
   hashes.
4. Add authentication and real Actor identity for reviewers and integrations.
5. Add optional webhook notification design for approval status changes.
6. Add wrapper guidance showing how to store local blocked-action references
   without storing raw prompts or raw tool payloads in AGCP.
7. Add policy versioning or decision version references before broad
   enforcement rollout.

## Open Questions

- Should resume re-evaluate current policy, or honor the original approved
  PolicyDecision if the reviewed context matches?
- Should a single HumanApproval unlock exactly one resume attempt, or multiple
  idempotent retries of the same resume attempt?
- What should happen if a reviewer approves after `expires_at` has passed?
- Which fields are enough for V1 context matching before a structured context
  hash exists?
- Should the resume endpoint return `allow`, `deny`, or a separate
  `approval_validated` style result?
- How should integrations report that the tool actually executed after a
  successful resume decision?
