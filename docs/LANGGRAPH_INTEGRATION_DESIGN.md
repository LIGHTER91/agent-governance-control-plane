# LangGraph Integration Design Proposal

## Status

Design proposal only. No LangGraph integration code exists yet.

This document describes how LangGraph agents could integrate with the Agent
Governance Control Plane (AGCP). AGCP remains a governance and evidence control
plane. It should not become a LangGraph replacement, graph runner, workflow
engine, tool executor, or planner.

The integration should let LangGraph applications keep their existing graph,
state, nodes, tools, and deployment model while calling AGCP for governed
decisions, telemetry, human oversight, and evidence export.

The integration supports governance workflows and evidence collection. It must
not be described as legal compliance certification.

## Goals

- Let a LangGraph application register or reference an AGCP Agent.
- Capture LangGraph run and tool activity as AGCP AgentRunRecord and
  TraceEventRecord evidence.
- Evaluate policies before governed tool calls or external actions when runtime
  decision mode is enabled.
- Persist PolicyDecision records produced by AGCP policy evaluation.
- Create HumanApproval records when a decision requires human review.
- Preserve an Evidence Bundle chain across LangGraph activity, policy decisions,
  human approvals, and audit logs.

## Non-goals

- Do not run LangGraph graphs inside AGCP.
- Do not replace LangGraph state management, routing, checkpoints, tools, or
  graph execution.
- Do not add LangGraph as a backend dependency for the control plane.
- Do not implement an SDK in this design issue.
- Do not store raw prompts, raw tool inputs, raw tool outputs, credentials,
  authorization headers, or private customer data by default.
- Do not implement runtime gateway code in this design issue.

## Integration Points

### Before Tool Call

Wrap selected LangGraph tools so the wrapper calls AGCP before invoking the
underlying tool.

Use this point for:

- `send_email`
- `create_ticket`
- `query_database`
- `call_internal_api`
- tools with external side effects
- tools that access governed data

In runtime decision mode, this is where the adapter would call:

```http
POST /runtime/tool-calls/decision
```

The adapter then acts on the returned decision:

- `allow`: call the wrapped LangGraph tool.
- `deny`: do not call the tool; return a controlled denial result to the graph.
- `require_human_review`: do not call the tool; return a pending-review result
  or interrupt the graph according to the application design.
- `not_applicable`: follow the configured integration default.

Trade-off: strongest governance point, but it adds latency and requires graph
authors to use the wrapper consistently.

### After Tool Result

Report safe summaries after a tool finishes.

Use this point for:

- recording a tool result status;
- recording that an allowed tool call completed;
- capturing safe metadata such as duration, result category, or external
  reference ID.

This should avoid raw tool outputs by default. If later evidence needs output
references, store stable references or summaries rather than payloads.

### Before External Action

Some LangGraph tools are wrappers around external actions. If the action can be
separated from local preparation, AGCP should govern the external action just
before it happens.

Examples:

- before sending an email after drafting it;
- before creating a ticket after classifying it;
- before updating a CRM record after selecting fields.

Trade-off: this can reduce false positives because more context is known, but
it may require more custom integration code around business-specific tools.

### Telemetry-only Tracing

The lowest-friction integration reports LangGraph activity after or around graph
execution through:

```http
POST /telemetry/events
```

This mode can record `tool_call_requested` events and currently triggers AGCP
policy evaluation for that event type, but it does not block LangGraph tool
execution.

Use this point for:

- early pilots;
- evidence collection before enforcement;
- validating agent/run/tool identity mapping;
- observing policy decisions without changing graph control flow.

Trade-off: easiest adoption, but it cannot prevent an action.

### Runtime Decision Mode

Runtime decision mode uses the Runtime Gateway contract described in
`docs/RUNTIME_GATEWAY_DESIGN.md`.

The LangGraph adapter calls AGCP before a governed action and honors the
response. This is the path toward enforcement, but it should come after
telemetry-only and simulation modes have validated policy behavior.

## Mapping LangGraph Concepts To AGCP Concepts

| LangGraph concept | AGCP concept | Notes |
| --- | --- | --- |
| Deployed graph/application | Agent | One registered AGCP Agent should represent the governed LangGraph agent or app. |
| LangGraph invocation/thread/run | AgentRunRecord | The adapter should map a stable LangGraph run/thread/checkpoint reference into AGCP `run_id`. |
| Tool call request | TraceEventRecord | Use `event_type = "tool_call_requested"` and safe metadata such as `tool_name`. |
| Tool call completion | TraceEventRecord | Later use `tool_call_allowed`, `tool_call_denied`, or a completion event when supported by the integration. |
| Runtime gateway decision | PolicyDecision | Persisted by AGCP when policies are evaluated. |
| Human review required | HumanApproval | Created by AGCP when policy decision is `require_human_review`. |
| Reviewable governance chain | Evidence Bundle | Exported through `GET /agents/{agent_id}/evidence-bundle`. |

The mapping should be explicit and stable. A mismatch between LangGraph run IDs
and AGCP run IDs would make evidence hard to navigate.

## Telemetry-only Call Shape

In telemetry-only mode, the wrapper or callback sends a trace event:

```http
POST /telemetry/events
```

Example:

```json
{
  "id": "33333333-3333-4333-8333-333333333333",
  "agent_id": "11111111-1111-4111-8111-111111111111",
  "run_id": "22222222-2222-4222-8222-222222222222",
  "external_event_id": "langgraph-tool-call-001",
  "correlation_id": "langgraph-thread-001",
  "event_type": "tool_call_requested",
  "timestamp": "2026-01-15T12:05:00Z",
  "summary": "LangGraph agent requested send_email tool.",
  "metadata": {
    "tool_name": "send_email",
    "langgraph_node": "support_followup"
  }
}
```

The metadata must remain safe. Do not include raw prompts, full graph state,
raw tool arguments, raw tool outputs, credentials, tokens, or private customer
data.

## Runtime Decision Call Shape

In runtime decision mode, the wrapper calls:

```http
POST /runtime/tool-calls/decision
```

Example request:

```json
{
  "request_id": "langgraph-tool-call-001",
  "agent_id": "11111111-1111-4111-8111-111111111111",
  "run_id": "22222222-2222-4222-8222-222222222222",
  "correlation_id": "langgraph-thread-001",
  "tool_name": "send_email",
  "action_summary": "Send a support follow-up email.",
  "mode": "simulation",
  "metadata": {
    "langgraph_node": "support_followup",
    "ticket_category": "support"
  }
}
```

Example response:

```json
{
  "request_id": "langgraph-tool-call-001",
  "agent_id": "11111111-1111-4111-8111-111111111111",
  "run_id": "22222222-2222-4222-8222-222222222222",
  "tool_name": "send_email",
  "decision": "require_human_review",
  "proceed": false,
  "reason": "Email tool use requires human review.",
  "trace_event_id": "33333333-3333-4333-8333-333333333333",
  "policy_decision_id": "66666666-6666-4666-8666-666666666666",
  "human_approval_id": "77777777-7777-4777-8777-777777777777"
}
```

## Minimal Adapter Shape

### Tool Wrapper

A V1 adapter can start as a wrapper around selected LangGraph tools:

```text
governed_tool(original_tool, tool_name, agcp_client, mode)
```

Responsibilities:

- receive the tool invocation;
- create or reuse `agent_id`, `run_id`, `correlation_id`, and `request_id`;
- summarize the action safely;
- call AGCP in telemetry-only, simulation, or enforcement mode;
- decide whether to call the wrapped tool;
- return a controlled result to LangGraph.

The wrapper must avoid serializing full LangGraph state or raw tool payloads to
AGCP by default.

### Middleware Or Helper Function

For applications that do not want a full SDK, V1 could provide a small helper:

```text
record_or_decide_tool_call(context, tool_name, summary, safe_metadata)
```

This helper would hide AGCP request construction while leaving graph structure
and tool execution in the LangGraph application.

### Optional Client SDK Later

A later SDK could provide:

- typed request/response objects;
- idempotency helpers;
- safe metadata helpers;
- retry policy;
- LangGraph-specific wrappers;
- local simulation utilities.

The SDK should remain optional. AGCP should still expose stable HTTP contracts
that integrations can call directly.

## Modes

### Telemetry-only

- Sends `POST /telemetry/events`.
- Records TraceEventRecord.
- May record PolicyDecision for `tool_call_requested`.
- Does not block tool execution.

Best for first pilots and evidence-only adoption.

### Simulation

- Calls the runtime decision endpoint.
- Records what the decision would be.
- The LangGraph app logs or observes the decision but does not have to obey it.

Best for validating policies and measuring operational impact before
enforcement.

### Enforcement

- Calls the runtime decision endpoint before the tool or external action.
- Honors `allow`, `deny`, `require_human_review`, and configured
  `not_applicable` behavior.

Best only after policies, latency, retry behavior, and failure mode settings
are tested.

## Failure Handling

### Gateway Unavailable

The adapter must have a per-integration failure policy:

- fail-closed: do not execute governed tools;
- fail-open: execute and emit local warnings/evidence later;
- simulation fallback: execute but record that AGCP was unavailable.

Default for high-risk external actions should be fail-closed, but V1 should make
this explicit rather than hidden.

### Timeout

Timeouts should be treated like gateway unavailability. The adapter should use a
short, explicit timeout and record local diagnostics without logging sensitive
payloads.

### Deny

The wrapper should not call the tool. It should return a controlled denial
object or raise an application-specific exception that the LangGraph graph is
designed to handle.

### Require Human Review

The wrapper should not call the tool. It should surface the `human_approval_id`
and a pending-review status to the graph or caller.

Open question: whether the graph should pause, end with pending status, or
resume later is application-specific and should not be owned by AGCP V1.

### Duplicate Request ID

The adapter should reuse the same `request_id` for retries of the same tool
attempt. AGCP should return the existing decision response and avoid duplicate
TraceEventRecord, PolicyDecision, HumanApproval, or AuditLog records.

### Unsafe Metadata

AGCP should reject unsafe metadata. The adapter should catch that validation
error, avoid executing the governed action in enforcement mode, and return a
clear integration error.

## Security Risks

### Leaking Prompts Or Tool Inputs

LangGraph state can include prompts, messages, tool inputs, tool outputs, and
private user data.

Mitigation:

- send action summaries and safe metadata only;
- do not serialize full graph state;
- do not store raw prompts or raw tool payloads by default.

### Bypassing The Wrapper

Developers may call the original tool directly instead of the governed wrapper.

Mitigation:

- document the wrapper as the only governed path;
- later add coverage reporting for governed versus ungoverned tool calls;
- prefer wrapping at a shared tool registration boundary.

### Storing Sensitive Payloads

Even safe-looking tool metadata can contain secrets or private customer data.

Mitigation:

- reuse AGCP metadata safety validation;
- provide adapter-side allowlists for metadata keys;
- reject suspicious key names before sending to AGCP.

### LangGraph Run ID And AGCP Run ID Mismatch

If every tool call gets a new AGCP run ID, Evidence Bundle exports will not show
the real LangGraph run shape.

Mitigation:

- define one AGCP `run_id` per LangGraph invocation/thread/run;
- store LangGraph-specific IDs only as safe metadata or correlation IDs;
- include run ID mapping tests in the adapter.

### Human Approval Resumption

LangGraph applications may need to resume after approval, but AGCP V1 should not
own graph checkpointing or scheduling.

Mitigation:

- return `human_approval_id`;
- let the LangGraph application decide whether to pause, poll, or resume;
- design a later integration-specific resumption pattern after the gateway
  contract is stable.

## Minimal V1 Implementation Path

1. Keep this design as documentation until a LangGraph adapter is explicitly
   requested.
2. Build a tiny example LangGraph-side wrapper in a separate example area, not
   as a backend dependency.
3. Support `tool_call_requested` with `tool_name`, safe summary, and safe
   metadata.
4. Add adapter-side idempotency with stable `request_id`.
5. Add tests with a fake tool function before adding any LangGraph dependency.
6. Add optional LangGraph-specific adapter only after the generic wrapper shape
   is proven.
7. Add enforcement mode behind explicit configuration.
8. Add documentation for fail-open/fail-closed choices per integration.

This path intentionally validates the control-plane contract before adding a
framework dependency.

## Recommended Follow-up Issues

1. Add Runtime Gateway enforcement mode behind explicit configuration.
2. Add runtime failure policy configuration design.
3. Add safe metadata allowlist helper for adapters.
4. Add generic Python tool wrapper example without LangGraph dependency.
5. Add LangGraph adapter spike using the generic wrapper.
6. Add Evidence Bundle tests for LangGraph runtime decision mode.
7. Add documentation for LangGraph run ID to AGCP run ID mapping.

## Open Questions

- Which LangGraph concept should be the canonical source for AGCP `run_id` in
  applications that use threads, checkpoints, or custom run identifiers?
- Should the first LangGraph adapter be callback-based, wrapper-based, or both?
- How should a graph resume after HumanApproval is approved?
- Should deny/review outcomes be returned as tool results or raised as typed
  exceptions?
- What metadata keys should the first adapter allow by default?
