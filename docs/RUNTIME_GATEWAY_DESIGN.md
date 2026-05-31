# Runtime Gateway Design Proposal

## Status

Design plus V0/V1 implementation. Request/response schemas, optional
contextual request fields, simulation mode, enforcement mode behind explicit
configuration, resume checks, and a read-only runtime activity endpoint are
implemented. Runtime Gateway enforcement is disabled by default with
`AGCP_RUNTIME_ENFORCEMENT_ENABLED=false`. Telemetry mode for the runtime
decision endpoint and production SDKs do not exist yet.
Dependency-free adapter examples and a LangGraph adapter spike exist as
documentation/examples only. Runtime and telemetry integration endpoints can
resolve minimal config-based service actor API keys, enforce endpoint/action
scopes, enforce config-based Agent, environment, runtime mode, and tool-name
restrictions, and reject missing keys when `AGCP_REQUIRE_SERVICE_AUTH=true`.
The DB-backed service actor registry can authenticate active service actors with
active or retiring non-expired keys when
`AGCP_SERVICE_ACTOR_REGISTRY_ENABLED=true`, and registry-backed actors use
persisted endpoint/action scopes and fine-grained rules. The registry path is
disabled by default. Owner-based service actor restrictions, full RBAC, user
login, and persisted API key rotation are not implemented.

This document describes the implemented runtime governance foundation and the
remaining V1 path for the Agent Governance Control Plane. It keeps the product
boundary clear: the gateway is a governance and decision layer, not an agent
orchestrator, workflow engine, tool executor, or replacement for LangGraph,
n8n, Dataiku, CrewAI, AutoGen, cloud AI platforms, or MCP servers.

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

A minimal V1 contract is implemented at:

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
  "tool_name": "send_email",
  "action_summary": "Send a support follow-up email.",
  "mode": "simulation",
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
- `tool_name` is required for governed tool call decisions.
- `action_summary` must be short and safe for evidence review.
- `mode` must be one of `telemetry`, `simulation`, or `enforcement`.
- Optional contextual fields can carry safe references and labels:
  `action_type`, `capability_id`, `source_ids`, `model_id`, `purpose`,
  `data_classification`, `contains_personal_data`, and
  `contains_sensitive_data`.
- `metadata` must use the same safe metadata rules as telemetry and audit
  records.
- The request must not include raw prompts, credentials, API keys, tokens,
  authorization headers, private customer data, or raw tool payloads.
- Caller-supplied classifications and personal/sensitive-data booleans are
  recorded as declared context only. They are not legal certification and are
  not verified Data Usage Profile truth. Active PolicyRules may match these
  declared fields explicitly.
- When contextual IDs are supplied, the Runtime Gateway resolves safe facts from
  Capability, Source, ModelAsset, Data Usage Profile, and Agent AccessGrant
  records. Resolved facts are kept distinct from declared fields and may be
  recorded in trace metadata with `resolved_` prefixes.
- Missing Capability, Source, ModelAsset, Data Usage Profile, and AccessGrant
  references are represented as `missing`. Missing inventory is not treated as
  safe.
- AccessGrant and Data Usage Profile facts are deterministic policy context
  only. The gateway does not automatically enforce AccessGrants or legally
  certify data usage.
- Metadata-only pre-check execution is opt-in with
  `AGCP_RUNTIME_METADATA_PRE_CHECKS_ENABLED=true`. When enabled, the gateway
  executes active authored PolicyCheckSteps linked to matched PolicyRules and
  persists safe CheckResults after the TraceEvent and PolicyDecision are
  available. These CheckResults do not directly change the final decision or
  `proceed` value, and `failure_behavior` is evidence intent only for now.

### Response

```json
{
  "request_id": "vendor-request-001",
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

Response behavior:

- `allow`: `proceed = true`.
- `deny`: `proceed = false`.
- `require_human_review`: `proceed = false` until a linked HumanApproval is
  approved by a later workflow.
- `not_applicable`: the initial request/response schema requires
  `proceed = false`. A later runtime endpoint can add explicit fail-open or
  fail-closed configuration before production enforcement.

Trade-off: a small response is easier for SDKs to adopt, but it means clients
must query the API later for full evidence details. That is acceptable for V1
because Evidence Bundle export already provides the review surface.

## Runtime Activity Read Model

The backend also exposes a read-only Runtime Gateway activity endpoint:

```http
GET /runtime/tool-calls/activity
```

It returns runtime tool-call activity sorted newest first. The response is built
from existing persisted TraceEventRecord rows, linked PolicyDecision rows, and
linked HumanApproval rows where available. It does not execute tools, mutate
runtime state, or change policy enforcement behavior.

Safe fields include:

- `agent_id`;
- `run_id`;
- `request_id`;
- `timestamp`;
- `tool_name`;
- `action_type`;
- `capability_id`;
- `source_ids`;
- `model_id`;
- `purpose`;
- `data_classification`;
- `contains_personal_data`;
- `contains_sensitive_data`;
- `mode`;
- `decision`;
- `proceed`;
- `reason`;
- `trace_event_id`;
- `policy_decision_id`;
- `human_approval_id`;
- `related_ids`.

Fields that are not persisted on older or shared records are returned as
`null`. The endpoint must not infer fake runtime details or expose unsafe
metadata.

## Contextual Runtime Governance Path

The next runtime design direction is richer contextual governance for actions
such as RAG retrieval, vectorization, model use, external API calls, and other
agentic operations where `tool_name`, `environment`, and Agent `risk_level` are
not enough.

The design is documented in
`docs/CONTEXTUAL_RUNTIME_GOVERNANCE_DESIGN.md`. The first schema slice is now
implemented: `POST /runtime/tool-calls/decision` accepts optional
`action_type`, `capability_id`, `source_ids`, `model_id`, `purpose`,
`data_classification`, `contains_personal_data`, and
`contains_sensitive_data` fields. These fields are persisted only as safe
TraceEvent metadata and surfaced in Runtime activity/Evidence Bundle records
where available. They do not change policy evaluation or enforcement behavior.

Contextual runtime governance must continue to use references,
classifications, booleans, and short safe summaries instead of raw source
content, prompts, credentials, or provider/tool payloads. AGCP remains the
decision and evidence layer; wrappers and adapters still decide whether local
tool execution proceeds based on `proceed`.

## Minimal Python Wrapper Example

A dependency-free Python example is available at
`docs/examples/runtime_tool_wrapper_example.py`. It shows how an application can
build a RuntimeToolCallDecisionRequest, call
`POST /runtime/tool-calls/decision`, read `decision` and `proceed`, execute the
local tool only when `proceed = true`, and handle `deny`,
`require_human_review`, and `not_applicable` without adding LangGraph or SDK
dependencies.

A more generic adapter-shaped example is available at
`docs/examples/generic_runtime_adapter_example.py`. It demonstrates a reusable
wrapper around arbitrary local tool functions, stable request ID generation,
conservative retry behavior, idempotency expectations, and blocked results for
non-allow decisions.

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

Current implementation note: enforcement mode is accepted only when
`AGCP_RUNTIME_ENFORCEMENT_ENABLED=true`. When disabled, the endpoint rejects
`mode = "enforcement"` before creating runtime records.

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

1. Reuse existing Agent lookup, Agent Run creation, TraceEventRecord
   persistence, PolicyRule adapter, evaluator, PolicyDecision persistence,
   HumanApproval creation, AuditLog, and Evidence Bundle behavior. Implemented.
2. Add idempotency by `agent_id`, `run_id`, and `request_id`. Implemented.
3. Add enforcement mode behind an explicit configuration flag. Implemented.
4. Define a fail-open/fail-closed setting before production enforcement.
   Implemented as a minimal global runtime failure policy.
5. Add tests for allow, deny, require human review, not applicable, duplicates,
   unsupported metadata, and transaction rollback. Implemented for the current
   runtime foundation.
6. Add resume checks for previously blocked actions after HumanApproval.
   Implemented.
7. Add a read-only runtime activity endpoint built from persisted records.
   Implemented.
8. Add optional contextual runtime governance fields only after the design is
   translated into a small backward-compatible schema change. Implemented.
9. Add telemetry mode to the Runtime Gateway decision endpoint only if it proves
   useful beyond the existing `/telemetry/events` behavior.
10. Add a small local integration example only after the endpoint behavior is
   stable. Implemented as documentation/example code.

V1 should stay inside the existing FastAPI modular monolith. It should not add
Kafka, Kubernetes, OPA/Rego, Cedar, Redis, a workflow engine, GraphQL, or a new
service boundary.

## Recommended Follow-up Issues

1. Extend the deterministic evaluator with a small explicit contextual rule
   surface.
2. Add Runtime Gateway telemetry mode if it is useful beyond `/telemetry/events`.
3. Add Policy and PolicyRule versioning design.
4. Add HumanApproval notification design.
5. Add production SDK or framework adapter only if explicitly requested after
   the examples and spike are proven.
6. Add broader filtering or pagination to Runtime activity only after real
   usage requires it.

## Open Questions

- Should `not_applicable` default to fail-closed in all enforcement deployments,
  or should the default be per integration?
- What is the minimum policy versioning needed before enforcement mode is safe?
- Should HumanApproval approval automatically unlock a pending request, or
  should integrations poll/query and decide how to resume?
- What latency budget is acceptable for the first real integration?
- How should gateway coverage be reported when some actions are still submitted
  only through telemetry ingestion mode?
- How should contextual runtime requests handle unknown Source, ModelAsset, or
  Capability references in simulation and enforcement mode?
