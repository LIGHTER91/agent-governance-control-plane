# LangGraph Adapter Boundary Design

## Status

Design only. This document defines the boundary for a future focused LangGraph
adapter or helper package. It does not implement a package, add a LangGraph
dependency, change Runtime Gateway behavior, or make AGCP an orchestrator.

AGCP remains a governance and evidence control plane. LangGraph applications
keep their graph, state, checkpoints, nodes, tools, and deployment model.

## Critical Assessment: Is LangGraph The Right First Adapter Target?

LangGraph is a good first adapter target because its applications usually have
clear tool invocation boundaries. A governed tool wrapper, ToolNode wrapper, or
application-owned tool registry can call AGCP before the side-effecting action
happens. That boundary is easier to reason about than a broad workflow system
where every step could be a custom action.

LangGraph also helps adoption. Many teams can understand a small wrapper around
selected tools before they are ready for a full SDK or production integration.
The adapter can demonstrate the core AGCP value:

- capture what the Agent tried to do;
- evaluate deterministic policy;
- return `allow`, `deny`, `require_human_review`, or `not_applicable`;
- create evidence records;
- let the LangGraph application decide whether to execute, stop, branch, or
  pause.

The adapter must not make AGCP execute tools itself. AGCP cannot safely own
LangGraph state, checkpointing, tool credentials, business-specific retries, or
external side effects. If AGCP executed tools, it would become an orchestrator
or tool runner, which is outside the product boundary.

The Runtime Gateway call should happen immediately before the governed tool or
external action executes. The caller is responsible for honoring
`proceed=true/false`. If the caller ignores `proceed=false`, AGCP can still
record evidence that a decision was returned, but it cannot physically stop the
action. That is why the adapter must make enforcement responsibility visible
instead of hiding it behind magical control flow.

The main risk is an adapter that feels too automatic. If it silently executes a
tool after review, hides denied decisions, swallows Runtime Gateway failures, or
sends full LangGraph state to AGCP, it will be harder to audit and easier to
misuse. A V1 adapter should stay small, explicit, and boring: construct safe
payloads, call AGCP, return a decision object, and provide optional branch
helpers.

Service Actors and scoped API keys are the right auth shape for this adapter.
LangGraph callers are machine integrations, not human reviewers. The adapter
should use a Service Actor API key with endpoint/action scopes such as
`runtime:decision` and `runtime:resume`, plus fine-grained rules for Agent IDs,
environments, runtime modes, and tool names. The adapter must never log
plaintext keys.

## 1. Integration Goal

The adapter should help a LangGraph application call AGCP at a governed action
boundary.

It should:

- construct Runtime Gateway decision requests;
- pass stable Agent and run identifiers;
- pass safe contextual fields such as tool name, action type, capability ID,
  source IDs, model ID, purpose, classification, and personal or sensitive data
  signals;
- call AGCP with a Service Actor identity;
- return a typed decision object to the LangGraph flow;
- optionally expose helper functions for branch selection;
- preserve evidence links for Runtime activity, Agent activity, HumanApproval,
  AuditLog, and Evidence Bundle review.

It should not:

- execute tools through AGCP;
- replace LangGraph nodes, graph routing, checkpoints, memory, or deployment;
- hide denied decisions;
- bypass HumanApproval;
- store raw prompts, raw source contents, raw tool payloads, credentials, or
  private customer data;
- claim legal compliance certification.

## 2. Runtime Call Pattern

The core flow is:

```text
LangGraph node/tool wrapper
-> AGCP Runtime Gateway decision request
-> AGCP returns decision and proceed
-> LangGraph caller executes tool, stops, branches, or pauses
-> AGCP persists runtime event and evidence records
-> optional resume check after HumanApproval
```

In the strongest enforcement pattern, the adapter wraps the selected tool and
calls:

```http
POST /runtime/tool-calls/decision
```

before invoking the underlying tool.

Example decision request:

```json
{
  "request_id": "langgraph-thread-123:send_email:001",
  "agent_id": "11111111-1111-4111-8111-111111111111",
  "run_id": "langgraph-thread-123",
  "correlation_id": "support-case-456",
  "tool_name": "send_email",
  "action_type": "external_message",
  "capability_id": "22222222-2222-4222-8222-222222222222",
  "source_ids": ["33333333-3333-4333-8333-333333333333"],
  "model_id": "44444444-4444-4444-8444-444444444444",
  "purpose": "customer_support_answering",
  "data_classification": "confidential",
  "contains_personal_data": true,
  "contains_sensitive_data": false,
  "mode": "enforcement",
  "action_summary": "Send a support follow-up email.",
  "metadata": {
    "langgraph_node": "support_followup",
    "tool_binding": "send_email"
  }
}
```

Example response:

```json
{
  "request_id": "langgraph-thread-123:send_email:001",
  "agent_id": "11111111-1111-4111-8111-111111111111",
  "run_id": "langgraph-thread-123",
  "tool_name": "send_email",
  "decision": "require_human_review",
  "proceed": false,
  "reason": "Email tool use requires human review.",
  "trace_event_id": "55555555-5555-4555-8555-555555555555",
  "policy_decision_id": "66666666-6666-4666-8666-666666666666",
  "human_approval_id": "77777777-7777-4777-8777-777777777777"
}
```

Decision handling:

| Decision | `proceed` | LangGraph caller behavior |
| --- | --- | --- |
| `allow` | `true` | Execute the local tool. |
| `deny` | `false` | Do not execute; return or branch to a controlled denial path. |
| `require_human_review` | `false` | Do not execute; pause, interrupt, or branch to pending review. |
| `not_applicable` | `false` by current conservative behavior | Follow explicit caller failure/default behavior. |

## 3. Adapter Responsibilities

The adapter may:

- build Runtime Gateway payloads;
- generate or accept stable `request_id` values;
- pass `agent_id`, `run_id`, and `request_id`;
- pass `tool_name`, `action_type`, `capability_id`, `source_ids`, `model_id`,
  `purpose`, `data_classification`, `contains_personal_data`, and
  `contains_sensitive_data`;
- call AGCP;
- validate that the response contains a recognized decision and boolean
  `proceed`;
- expose a decision object to LangGraph;
- provide optional branch helpers such as `allow`, `deny`, `review`, and
  `error`;
- retry idempotently for safe transient failures when configured.

The adapter must not:

- call the original tool unless the LangGraph caller chooses to do so after
  checking the decision;
- execute tools on AGCP's behalf;
- hide denied or review-required decisions;
- bypass HumanApproval;
- auto-resume a graph without the caller's explicit resume flow;
- serialize full LangGraph state;
- store raw prompts, raw source contents, raw tool inputs, raw tool outputs,
  tokens, credentials, or authorization headers;
- claim that the integration certifies legal compliance.

## 4. Enforcement Model

AGCP returns a decision. LangGraph enforces the decision.

The adapter should make this boundary hard to miss:

- `decision` tells the caller what AGCP decided.
- `proceed` tells the caller whether the governed action may continue.
- The LangGraph application decides how to represent denial, review, and
  errors in its graph state.
- AGCP records evidence, but it does not physically stop a tool that the caller
  invokes outside the governed wrapper.

If a developer calls the original tool directly, or ignores `proceed=false`,
AGCP can show that the Runtime Gateway returned a blocking decision, but the
actual side effect happened outside the governed boundary. Future adapter
hardening may add coverage reporting, but V1 should document the limitation
plainly.

Recommended enforcement placement:

```text
LangGraph decides to call governed tool
-> adapter calls Runtime Gateway
-> if allow/proceed=true: application invokes tool
-> if deny: application returns controlled denial
-> if require_human_review: application pauses or branches
```

This avoids an adapter that secretly owns graph control flow.

## 5. HumanApproval And Resume

When AGCP returns `require_human_review`:

- `proceed` is `false`;
- the adapter must not execute the tool;
- the response may include `human_approval_id`;
- the LangGraph application should store the decision fields in graph state or
  an application-owned pending-action store;
- the graph may pause, interrupt, return a pending status, or branch to an
  operator workflow.

Resume flow:

```text
HumanApproval is approved in AGCP
-> LangGraph application receives, polls, or is triggered to resume
-> adapter calls POST /runtime/tool-calls/resume
-> AGCP verifies approval and original request context
-> AGCP returns proceed=true only when resume is valid
-> LangGraph caller executes the original local tool
```

The adapter should preserve:

- original `agent_id`;
- original `run_id`;
- original `request_id`;
- `human_approval_id`;
- a stable resume ID for idempotency.

The adapter should not own LangGraph checkpointing. It can provide helper
functions, but the application decides whether to use LangGraph interrupts,
external queues, polling, or a manual reviewer flow.

## 6. Service Actor Auth

The adapter should authenticate as a Service Actor because it represents a
machine integration.

Recommended auth behavior:

- use `X-AGCP-API-Key`;
- load the plaintext key from the LangGraph application's secret manager or
  environment, not from AGCP frontend pages;
- never print, log, serialize, or store the plaintext key;
- treat key IDs and key status metadata as safe, but not key material;
- support key rotation by allowing deployers to replace the configured key
  without changing `actor_id`;
- fail closed on authentication errors in enforcement mode unless the caller
  explicitly configures a different local behavior.

Required scopes:

- `runtime:decision` for `POST /runtime/tool-calls/decision`;
- `runtime:resume` for `POST /runtime/tool-calls/resume`;
- optionally `telemetry:write` for telemetry-only reporting through
  `POST /telemetry/events`.

Fine-grained rules should constrain:

- Agent IDs the adapter may act for;
- environments such as `development`, `staging`, or `production`;
- runtime modes such as `simulation` or `enforcement`;
- tool names the adapter may govern.

This keeps the adapter focused on integration identity. It is not full IAM,
does not replace user authentication, and does not grant credentials to the
underlying business tools.

## 7. Minimal Package/API Shape

The first package shape should be deliberately small.

### `AGCPClient`

Responsibilities:

- hold base URL, timeout, and Service Actor API key configuration;
- call `POST /runtime/tool-calls/decision`;
- call `POST /runtime/tool-calls/resume`;
- optionally call `POST /telemetry/events`;
- validate response shape;
- avoid logging request bodies or API keys.

Sketch:

```python
client = AGCPClient(
    base_url="https://agcp.example",
    api_key=os.environ["AGCP_SERVICE_ACTOR_API_KEY"],
    timeout_seconds=5,
)
```

### `governed_tool_call(...)`

Responsibilities:

- accept safe action context;
- construct a Runtime Gateway request;
- return a decision object;
- optionally execute a caller-supplied function only when explicitly configured
  by the application.

Recommended design for V1:

```python
decision = client.governed_tool_call(
    agent_id=agent_id,
    run_id=run_id,
    request_id=request_id,
    tool_name="send_email",
    action_type="external_message",
    purpose="customer_support_answering",
    source_ids=[source_id],
    mode="enforcement",
    action_summary="Send a support follow-up email.",
    metadata={"langgraph_node": "support_followup"},
)
```

The safest default is to return the decision object and let the LangGraph flow
call the underlying tool. If a helper executes a function, its name and docs
must make that responsibility explicit, for example
`execute_if_allowed(...)`.

### `decision_to_branch(...)`

Responsibilities:

- convert AGCP decisions into LangGraph-friendly branch names;
- preserve the original decision for evidence and debugging;
- avoid hiding denial or review-required decisions.

Example branch names:

- `allowed`;
- `denied`;
- `requires_review`;
- `not_applicable`;
- `integration_error`.

### `resume_after_approval(...)`

Responsibilities:

- call `POST /runtime/tool-calls/resume`;
- preserve original request identifiers;
- return a resume decision object;
- let the LangGraph caller execute the original action only when resume returns
  `proceed=true`.

Sketch:

```python
resume = client.resume_after_approval(
    agent_id=agent_id,
    run_id=run_id,
    original_request_id=request_id,
    human_approval_id=human_approval_id,
    resume_id=resume_id,
)
```

No production package should be created in this issue. This API shape is a
design target for a later implementation issue.

## 8. Evidence And Telemetry

A correctly integrated LangGraph adapter should produce reviewable records in:

- Runtime activity: decision and resume records from Runtime Gateway trace
  events;
- Agent activity: Agent-scoped timeline entries for runtime decisions,
  HumanApprovals, and audit events;
- Evidence Bundle: Agent metadata, TraceEvents, PolicyDecisions, optional
  PolicyVersion references, CheckResults, HumanApprovals, AuditLogs,
  AccessGrants, inventory references, and DataUsageProfile summaries;
- AuditLog: HumanApproval creation and other governance-relevant events.

The adapter should preserve evidence navigation by using stable IDs:

- one `agent_id` for the registered AGCP Agent;
- one `run_id` per LangGraph invocation/thread/run;
- one `request_id` per governed tool attempt;
- one resume ID per resume attempt.

Evidence should contain safe summaries and references, not raw graph state or
tool payloads.

Telemetry-only pilots may still call:

```http
POST /telemetry/events
```

This can collect visibility and policy evidence, but it does not block tool
execution. The design should be clear when a flow is telemetry-only,
simulation, or enforcement.

## 9. Failure Modes

### AGCP Unavailable

The adapter should use a short timeout and explicit failure policy.

Recommended defaults:

- enforcement mode: fail closed for high-risk tools;
- simulation mode: return an integration error or simulation fallback;
- telemetry-only mode: continue locally only if the caller accepts missing
  telemetry and records local diagnostics.

### Auth Failure

Authentication failure means the Service Actor key is missing, invalid,
revoked, expired, disabled, or lacks required scopes.

In enforcement mode, the adapter should not execute the governed tool unless
the application has explicitly chosen a local fail-open policy. The adapter must
not log the key.

### Timeout

Timeouts should be treated like AGCP unavailability. Retrying is acceptable
only when the same `request_id` is reused for the same governed attempt.

### Malformed Response

If AGCP returns a response without a known `decision` or boolean `proceed`, the
adapter should treat it as unsafe. In enforcement mode, do not execute the tool.

### Denied Decision

The adapter should not call the tool. It should return a denial object or branch
label that LangGraph can route to a controlled response.

### Review Required

The adapter should not call the tool. It should return review context including
`human_approval_id` and preserve original request identifiers for resume.

### Caller Ignores Decision

AGCP cannot stop an action that is executed outside the governed wrapper. The
adapter should document this explicitly and should make the decision object
visible so the caller cannot accidentally ignore it.

### Unsafe Metadata

The adapter should avoid sending suspicious fields such as `api_key`, `token`,
`password`, `secret`, `authorization`, `raw_prompt`, `raw_tool_input`, and
`raw_tool_output`. If AGCP rejects metadata, enforcement mode should block the
action by default.

## 10. Non-goals

- No production adapter package in this issue.
- No AGCP-side tool execution.
- No LangGraph orchestration replacement.
- No graph runner, planner, checkpoint manager, or state store inside AGCP.
- No frontend UI changes in this issue.
- No raw prompt, raw source content, raw tool input, raw tool output, token,
  credential, or unsafe payload storage.
- No OIDC/SAML/JWT or broad enterprise IAM in the adapter design.
- No legal compliance certification claims.
- No compliance scoring.

## Relationship To Existing Docs

- `docs/LANGGRAPH_INTEGRATION_DESIGN.md` describes the broader integration
  concept.
- `docs/examples/langgraph_adapter_spike.py` demonstrates a dependency-free
  wrapper spike.
- `apps/api/examples/langgraph_helper/` contains the dependency-free helper
  prototype with fake-tool tests, local Runtime Gateway validation guidance,
  and no LangGraph dependency.
- `docs/RUNTIME_GATEWAY_DESIGN.md` describes the Runtime Gateway contract.
- `docs/RUNTIME_GATEWAY_RESUME_ENDPOINT.md` describes resume semantics after
  HumanApproval.
- `docs/SERVICE_ACTOR_API_KEY_DESIGN.md` and
  `docs/SERVICE_ACTOR_SCOPES_DESIGN.md` describe integration identity and
  scoped API keys.

## Recommended Follow-up Issue

Decide whether a production LangGraph adapter package is needed after local
Runtime Gateway validation with Service Actor auth. That follow-up should define
failure policy defaults, packaging boundaries, and LangGraph-specific state
integration before adding any LangGraph dependency.
