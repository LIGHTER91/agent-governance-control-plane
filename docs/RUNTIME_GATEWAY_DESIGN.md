# Runtime Gateway Design Proposal

## Status

Design proposal only. No runtime gateway code exists yet.

This document describes a possible V1 path for runtime governance in the Agent
Governance Control Plane. It keeps the product boundary clear: the gateway is a
governance and decision layer, not an agent orchestrator, workflow engine, tool
executor, or replacement for LangGraph, n8n, Dataiku, CrewAI, AutoGen, cloud AI
platforms, or MCP servers.

The gateway would support evidence collection and governance workflows. It must
not be described as legal compliance certification.

## Purpose

The Runtime Gateway is the control point an agent stack can call before an agent
performs a governed action. Its purpose is to answer:

- Is this agent known?
- Is this action allowed for this agent, environment, and risk level?
- Which policy allowed, denied, or escalated the action?
- Does a human need to approve the action before it proceeds?
- What evidence was recorded for later review?

The gateway should integrate with existing agent runtimes through SDKs,
middleware, HTTP calls, or framework adapters. It should not schedule agent
steps, decide agent plans, route tasks, or execute tools itself.

## What The Gateway Controls

Initial control surface:

- Tool calls: requests such as `send_email`, `create_ticket`,
  `query_database`, or `call_internal_api`.
- External actions: actions with side effects outside the agent process, such as
  sending a message, creating a record, updating a CRM object, or triggering an
  internal workflow.
- Data access requests: requests to read governed datasets, customer records,
  documents, or internal knowledge sources.

Later control surface:

- Model calls: model access can be governed when the product needs model-level
  restrictions, model inventory, or model usage evidence.

The gateway should control decisions and evidence. It should not own the
business implementation of tools, data connectors, model providers, or agent
orchestration.

## Governed Tool Call Contract

The exact endpoint name can be decided during implementation. A minimal V1
contract could be:

```http
POST /runtime/tool-calls/decision
```

### Request

```json
{
  "request_id": "vendor-request-001",
  "agent_id": "11111111-1111-4111-8111-111111111111",
  "run_id": "22222222-2222-4222-8222-222222222222",
  "correlation_id": "support-run-2026-01-15-001",
  "environment": "development",
  "risk_level": "medium",
  "action_type": "tool_call",
  "tool_name": "send_email",
  "action_summary": "Send a support follow-up email.",
  "requested_at": "2026-01-15T12:05:00Z",
  "metadata": {
    "ticket_category": "support",
    "destination_type": "customer"
  }
}
```

Rules:

- `request_id` is required for idempotency.
- `agent_id` must reference a registered Agent.
- `run_id` groups related actions into an Agent Run.
- `tool_name` is required for `action_type = "tool_call"`.
- `action_summary` must be short and safe for evidence review.
- `metadata` must use the same safe metadata rules as telemetry and audit
  records.
- The request must not include raw prompts, credentials, API keys, tokens,
  authorization headers, private customer data, or raw tool payloads.

### Response

```json
{
  "request_id": "vendor-request-001",
  "agent_id": "11111111-1111-4111-8111-111111111111",
  "run_id": "22222222-2222-4222-8222-222222222222",
  "decision": "require_human_review",
  "proceed": false,
  "reason": "Email tool use requires human review.",
  "trace_event_id": "33333333-3333-4333-8333-333333333333",
  "policy_decision_id": "66666666-6666-4666-8666-666666666666",
  "human_approval_id": "77777777-7777-4777-8777-777777777777"
}
```

Response behavior:

- `allow`: `proceed = true`.
- `deny`: `proceed = false`.
- `require_human_review`: `proceed = false` until a linked HumanApproval is
  approved by a later workflow.
- `not_applicable`: V1 should choose an explicit deployment setting. In
  enforcement mode, the safer default is fail-closed unless a human configures
  fail-open for a specific integration.

Trade-off: a small response is easier for SDKs to adopt, but it means clients
must query the API later for full evidence details. That is acceptable for V1
because Evidence Bundle export already provides the review surface.

## Runtime Flow

1. Agent requests action.
2. The framework adapter or application middleware sends a governed request to
   the Runtime Gateway before executing the action.
3. The gateway validates the Agent, request ID, action type, and safe metadata.
4. The gateway creates or reuses the Agent Run and records a TraceEventRecord
   such as `tool_call_requested`.
5. The gateway loads active Policy and PolicyRule records.
6. Policies are evaluated deterministically.
7. A PolicyDecision is persisted with one of:
   - `allow`
   - `deny`
   - `require_human_review`
   - `not_applicable`
8. If the decision is `require_human_review`, a pending HumanApproval is created.
9. AuditLog records are appended for governance-relevant mutations, including
   HumanApproval creation.
10. The gateway returns a decision response to the agent integration.
11. Evidence Bundle export can later show the chain:
    `TraceEventRecord -> PolicyDecision -> HumanApproval -> AuditLog`.

The gateway should preserve transaction atomicity for records created during a
single decision. It should also preserve request idempotency, so client retries
do not create duplicate trace events, decisions, approvals, or audit entries.

## Operating Modes

### Telemetry Ingestion Mode

This is the current V0 behavior.

- The agent or integration reports what happened.
- The backend records telemetry.
- For `tool_call_requested`, the backend can evaluate policies and record a
  PolicyDecision.
- The backend does not block the action.

Use when:

- integrations are early;
- teams need visibility before enforcement;
- adding a blocking hop would be too risky.

Trade-off: easiest adoption, but bypass is possible because the agent can act
without waiting for a gateway decision.

### Simulation Mode

The integration calls the gateway before or after an action, but the decision is
advisory.

- The gateway evaluates policies.
- The response says what would have happened in enforcement mode.
- The client is not required to obey the decision.

Use when:

- validating policies before enforcement;
- measuring false positives;
- proving latency and reliability;
- training teams on review workflows.

Trade-off: good for policy tuning, but it still does not prevent risky actions.

### Enforcement Mode

The integration calls the gateway before executing the action and must honor the
decision.

- `allow` lets the action proceed.
- `deny` blocks the action.
- `require_human_review` blocks the action until a human approval workflow
  produces an approval.
- `not_applicable` follows an explicit configured default.

Use when:

- the integration can tolerate a decision hop;
- policies have been tested;
- bypass controls are understood;
- failure handling is agreed.

Trade-off: strongest control, but it adds latency, reliability requirements, and
operational consequences if the gateway is unavailable.

## Risks And Trade-offs

### Latency

Every enforcement request adds a network call and policy evaluation time.

Mitigations:

- Keep V1 evaluator deterministic and local to the backend.
- Avoid external policy engines until justified.
- Define latency budgets per integration.
- Cache static policy inputs only after correctness rules are clear.

### Bypass

Agents or tools may execute without calling the gateway.

Mitigations:

- Start with integrations where the call path is controllable.
- Add evidence showing which actions came through the gateway.
- Later add integration health checks or coverage reporting.

### Partial Failures

A trace event, decision, approval, or audit record could fail mid-flow.

Mitigations:

- Use a single transaction for decision records created together.
- Return clear retryable and non-retryable errors.
- Preserve idempotency by `agent_id`, `run_id`, and request ID.

### Duplicate Requests

Clients may retry a request after a timeout.

Mitigations:

- Require `request_id`.
- Make retries return the existing decision response.
- Do not create duplicate HumanApproval or AuditLog records for the same
  governed request.

### Policy Drift

Policies can change between simulation, enforcement, and later review.

Mitigations:

- Record `policy_id`, `rule_id`, and later policy version when versioning
  exists.
- Include policy and rule references in evidence exports.
- Add policy versioning before high-stakes enforcement.

### Sensitive Data Leakage

Governed requests may accidentally include raw prompts, credentials, private
customer data, or raw tool payloads.

Mitigations:

- Reuse centralized safe metadata validation.
- Require summaries and references instead of raw payloads.
- Reject unsafe metadata keys.
- Do not log request bodies.

### Human Approval Delays

Human review can block an action for too long.

Mitigations:

- Include explicit pending state in responses.
- Add expiration and cancellation behavior.
- Later add notifications and escalation paths.
- Let integrations define what they do while a request is pending.

## Minimal V1 Implementation Path

1. Add a runtime decision schema for governed tool calls.
2. Add a runtime decision endpoint for `tool_call_requested`.
3. Reuse existing Agent lookup, Agent Run creation, TraceEventRecord
   persistence, PolicyRule adapter, evaluator, PolicyDecision persistence,
   HumanApproval creation, AuditLog, and Evidence Bundle behavior.
4. Add idempotency by `agent_id`, `run_id`, and `request_id`.
5. Implement telemetry ingestion mode and simulation mode first.
6. Add enforcement mode behind an explicit configuration flag.
7. Define a fail-open/fail-closed setting before production enforcement.
8. Add tests for allow, deny, require human review, not applicable, duplicates,
   unsupported metadata, and transaction rollback.
9. Add a small local integration example only after the endpoint behavior is
   stable.

V1 should stay inside the existing FastAPI modular monolith. It should not add
Kafka, Kubernetes, OPA/Rego, Cedar, Redis, a workflow engine, GraphQL, or a new
service boundary.

## Recommended Follow-up Issues

1. Add runtime governed tool call request and response schemas.
2. Add Runtime Gateway decision endpoint in telemetry ingestion mode.
3. Add Runtime Gateway simulation mode.
4. Add Runtime Gateway enforcement mode behind explicit configuration.
5. Add runtime request idempotency and duplicate response behavior.
6. Add runtime failure policy design for fail-open and fail-closed behavior.
7. Add runtime evidence bundle coverage tests.
8. Add Policy and PolicyRule versioning design.
9. Add HumanApproval notification design.
10. Add one framework adapter design, starting with LangGraph only after the
    gateway contract is stable.

## Open Questions

- Should `not_applicable` default to fail-closed in all enforcement deployments,
  or should the default be per integration?
- What is the minimum policy versioning needed before enforcement mode is safe?
- Should HumanApproval approval automatically unlock a pending request, or
  should integrations poll/query and decide how to resume?
- What latency budget is acceptable for the first real integration?
- How should gateway coverage be reported when some actions are still submitted
  only through telemetry ingestion mode?
