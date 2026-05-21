# Service Actor Fine-Grained Scopes Design

## Status

Design proposal with a minimal config-based implementation now in place for
Agent ID, environment, runtime mode, and tool-name restrictions on telemetry and
Runtime Gateway integration endpoints. The backend still does not implement
owner-based restrictions, Evidence Bundle service scopes, HumanApproval review
scopes, database-backed service actor records, or persisted API key rotation.
The DB-backed service actor registry is documented in
`docs/SERVICE_ACTOR_REGISTRY_DESIGN.md`, but not implemented.

AGCP remains an Agent Governance Control Plane. Fine-grained service actor
scopes should govern which integrations may call AGCP for which Agents and
contexts. They should not turn AGCP into an orchestrator, tool executor,
identity provider, or broad enterprise IAM system.

## Why Endpoint Scopes Are Not Enough

Endpoint/action scopes answer only "can this service actor call this kind of
endpoint?"

Current examples:

- `telemetry:write`
- `runtime:decision`
- `runtime:resume`

That is useful but incomplete. A service actor with `runtime:decision` can still
be too broad if it can request decisions for every Agent, every environment,
every runtime mode, and every tool. Before production-like runtime enforcement,
AGCP also needs to answer:

- which Agents can this service actor act for;
- which Agent owners can this service actor represent;
- which environments are allowed;
- whether enforcement mode is allowed;
- which tools or external actions are in scope;
- whether evidence or approval-related access is allowed.

Endpoint scopes should remain the first gate. Fine-grained restrictions should
be a second gate applied before creating telemetry, runtime, PolicyDecision,
HumanApproval, AuditLog, or Evidence Bundle records.

## Fine-Grained Scope Model

### Endpoint And Action Scopes

Endpoint/action scopes remain the coarse-grained permission names:

| Scope | Existing or future use |
| --- | --- |
| `telemetry:write` | Submit telemetry through `POST /telemetry/events`. |
| `runtime:decision` | Call `POST /runtime/tool-calls/decision`. |
| `runtime:resume` | Call `POST /runtime/tool-calls/resume`. |
| `agent:read` | Read minimal Agent metadata for adapters. |
| `evidence:read` | Export or read Evidence Bundles. Future, explicit only. |
| `human_approval:read` | Read approval status. Future, explicit only. |
| `human_approval:review` | Approve, reject, or cancel HumanApprovals. Denied by default. |

V1 fine-grained restrictions should narrow these scopes. They should not grant
an endpoint/action permission that is missing from `AGCP_SERVICE_ACTOR_SCOPES`.

### Allowed Agent IDs

`agent_ids` is the most explicit restriction. It should list registered Agent
IDs that the service actor may act for.

Rules:

- unknown Agents deny before records are created;
- an empty list means no Agent access;
- broad access must use an explicit wildcard such as `"*"`;
- production and strict service-auth deployments should avoid wildcard access
  unless a platform admin deliberately configures it.

### Allowed Owner References

Owner-based access can reduce configuration churn when a service actor owns a
set of Agents.

Recommended shape:

```json
{
  "owner_refs": [
    {
      "owner_type": "service",
      "owner_id": "service:langgraph-runtime-prod"
    }
  ]
}
```

Rules:

- owner references should match the Agent ownership fields exactly;
- `owner_type = "service"` with `owner_id = actor_id` is the safest first case;
- team, user, or organization-unit ownership should require explicit mapping;
- owner-based access should not imply policy administration, HumanApproval
  review, or Evidence Bundle export.

### Allowed Owner Types

`owner_types` can be useful for coarse local development rules, but it is weak
on its own because it does not identify the specific owner.

Recommended V1 rule: use `owner_types` only together with `owner_refs` or
`agent_ids`. Do not allow a service actor to act for all `team` or all
`organization_unit` Agents just because the owner type matches.

### Allowed Environments

`environments` should restrict service actor access to Agent environments:

- `development`
- `staging`
- `production`

Rules:

- production access must be explicit;
- missing environment access should deny in strict service-auth deployments;
- telemetry for development should not automatically imply telemetry for
  staging or production;
- runtime enforcement for production requires both production environment
  access and enforcement runtime-mode access.

### Allowed Runtime Modes

`runtime_modes` should restrict Runtime Gateway modes:

- `simulation`
- `enforcement`

Rules:

- enforcement must be explicitly allowed;
- enforcement still also requires `AGCP_RUNTIME_ENFORCEMENT_ENABLED=true`;
- missing `runtime_modes` should deny enforcement;
- simulation may be allowed more broadly than enforcement, but only by explicit
  configuration in strict service-auth deployments.

### Allowed Tool Names

`tool_names` can restrict runtime decisions to known governed tools, for
example:

- `send_email`
- `create_ticket`
- `query_database`

Rules:

- tool names should match the safe `tool_name` already submitted in telemetry
  or runtime requests;
- missing `tool_names` can mean "no tool restriction" only when broad access is
  explicit;
- raw tool payloads, prompts, credentials, or authorization headers must not be
  placed in this config or in request metadata.

### Allowed Endpoints And Actions

The existing endpoint/action scopes are the canonical names for endpoint access.
The minimal fine-grained implementation does not include a separate `actions`
field. This keeps endpoint/action access in `AGCP_SERVICE_ACTOR_SCOPES` and
uses `AGCP_SERVICE_ACTOR_SCOPE_RULES` only for Agent, environment, runtime mode,
and tool-name restrictions.

Recommended V1 rule:

1. check `AGCP_SERVICE_ACTOR_SCOPES`;
2. load matching fine-grained rules for the actor;
3. confirm Agent, environment, runtime mode, and tool restrictions.

## Minimal Config-Based V1 Format

Keep V1 config-based and avoid database tables. The existing API key and
endpoint/action scope settings remain:

```text
AGCP_SERVICE_ACTOR_API_KEYS="service:demo-runtime=sha256:<digest>"
AGCP_SERVICE_ACTOR_SCOPES="service:demo-runtime=runtime:decision,runtime:resume"
```

Add one JSON configuration value for fine-grained restrictions:

```text
AGCP_SERVICE_ACTOR_SCOPE_RULES='{
  "service:demo-runtime": {
    "agent_ids": ["11111111-1111-4111-8111-111111111111"],
    "environments": ["development"],
    "runtime_modes": ["simulation"],
    "tool_names": ["send_email"]
  }
}'
```

Suggested fields:

| Field | Meaning |
| --- | --- |
| Top-level key | Service actor ID such as `service:demo-runtime`. Required. |
| `agent_ids` | Allowed Agent IDs, or explicit `"*"` for broad access. Optional but recommended. |
| `environments` | Allowed Agent environments. Optional outside strict mode, explicit in strict mode. |
| `runtime_modes` | Allowed runtime modes. Required for Runtime Gateway enforcement. |
| `tool_names` | Allowed governed tools. Optional, but recommended for runtime decision actors. |

Using JSON is less pleasant than a compact environment string, but it avoids
inventing a brittle parser for multiple dimensions. It also gives the project a
direct migration path to a future local config file or database-backed service
actor registry.

Implementation note: the minimal backend implementation intentionally does not
support `actions`, `owner_refs`, or `owner_types` yet. Endpoint/action access is
still controlled by `AGCP_SERVICE_ACTOR_SCOPES`.

## Interaction With Current Scopes

Current scopes remain mandatory:

- `POST /telemetry/events` requires `telemetry:write`;
- `POST /runtime/tool-calls/decision` requires `runtime:decision`;
- `POST /runtime/tool-calls/resume` requires `runtime:resume`.

Fine-grained rules should only narrow access:

- a service actor without `runtime:decision` still cannot call the runtime
  decision endpoint, even if a fine-grained rule mentions that Agent;
- a service actor with `runtime:decision` but no matching Agent/environment/mode
  rule should be rejected in strict or production-like configurations;
- `evidence:read` should remain denied unless both the endpoint/action scope
  and fine-grained evidence rule exist.

Development actor fallback remains unchanged for local/dev flows unless the
project explicitly removes it later.

Runtime resume checks do not carry a request mode today. The current
implementation treats resume checks as requiring `runtime_modes` containing
`enforcement` or `"*"`, because resume is the path used after a previously
blocked governed action.

## Safe Defaults

V1 should default to conservative behavior:

- missing endpoint/action scope denies for service actors;
- unknown service actor denies;
- invalid API key denies before records are created;
- unknown Agent denies before records are created;
- unsafe metadata denies regardless of scopes;
- enforcement mode requires:
  - `runtime:decision`;
  - a matching fine-grained rule;
  - `runtime_modes` containing `enforcement`;
  - `AGCP_RUNTIME_ENFORCEMENT_ENABLED=true`;
- production environment access requires `environments` containing
  `production`;
- broad Agent access requires explicit `"*"` and should be avoided for
  production enforcement;
- missing fine-grained restrictions may preserve current local/dev behavior, but
  strict service-auth or production-like deployments should deny unless access
  is explicit.

The key trade-off: preserving local/dev compatibility reduces migration pain,
while strict production behavior avoids accidental broad access. V1 should make
that boundary explicit in config and tests.

## Authorization Examples

### One Development Agent, Simulation Only

```text
AGCP_SERVICE_ACTOR_SCOPES="service:demo-dev=runtime:decision"
AGCP_SERVICE_ACTOR_SCOPE_RULES='{
  "service:demo-dev": {
    "agent_ids": ["11111111-1111-4111-8111-111111111111"],
    "environments": ["development"],
    "runtime_modes": ["simulation"],
    "tool_names": ["send_email"]
  }
}'
```

Result:

- `mode = "simulation"` for the listed Agent and tool can proceed to policy
  evaluation.
- `mode = "enforcement"` is rejected because enforcement is not listed.
- Other Agents are rejected.

### Telemetry For Multiple Staging Agents

```text
AGCP_SERVICE_ACTOR_SCOPES="service:staging-telemetry=telemetry:write"
AGCP_SERVICE_ACTOR_SCOPE_RULES='{
  "service:staging-telemetry": {
    "agent_ids": [
      "22222222-2222-4222-8222-222222222222",
      "33333333-3333-4333-8333-333333333333"
    ],
    "environments": ["staging"]
  }
}'
```

Result:

- telemetry for the listed staging Agents is accepted;
- telemetry for production or unknown Agents is rejected;
- runtime decision calls are rejected because `runtime:decision` is missing.

### Enforcement Requires Explicit Allowance

```text
AGCP_RUNTIME_ENFORCEMENT_ENABLED=true
AGCP_SERVICE_ACTOR_SCOPES="service:prod-runtime=runtime:decision"
AGCP_SERVICE_ACTOR_SCOPE_RULES='{
  "service:prod-runtime": {
    "agent_ids": ["44444444-4444-4444-8444-444444444444"],
    "environments": ["production"],
    "runtime_modes": ["simulation"]
  }
}'
```

Result:

- simulation is allowed for the listed production Agent;
- enforcement is rejected because `runtime_modes` does not include
  `enforcement`;
- adding global enforcement config alone is not enough.

### Evidence Export Is Not Implicit

```text
AGCP_SERVICE_ACTOR_SCOPES="service:runtime-only=runtime:decision,runtime:resume"
```

Result:

- runtime decision and resume may be allowed if fine-grained runtime rules also
  match;
- Evidence Bundle export remains unavailable because `evidence:read` is not
  configured;
- human review actions remain unavailable because `human_approval:review` is
  not configured.

## Audit And Evidence Implications

Successful service actions must retain resolved service actor identity:

```json
{
  "actor_type": "service",
  "actor_id": "service:prod-runtime"
}
```

Denied fine-grained scope checks should be auditable where safe, especially in
strict service-auth deployments. Safe denial evidence can include:

- service actor ID if authentication succeeded;
- endpoint/action family;
- Agent ID if it is known and safe to record;
- Agent environment if already loaded;
- denial category, such as `agent_scope_denied`,
  `environment_scope_denied`, `runtime_mode_scope_denied`, or
  `tool_scope_denied`.

Denied-scope audit records must not include:

- raw API keys;
- authorization headers;
- raw prompts;
- raw tool payloads;
- credentials;
- private customer data;
- unsafe metadata.

Evidence Bundles should continue to show successful service actor identity
through AuditLog, HumanApproval requester fields, TraceEventRecord links, and
PolicyDecision links. They should not expose API key material or the full
authorization config.

## Minimal Implementation Path

1. Parse fine-grained config.
   - Add a typed config model for `AGCP_SERVICE_ACTOR_SCOPE_RULES`.
     Implemented for `agent_ids`, `environments`, `runtime_modes`, and
     `tool_names`.
   - Validate actor IDs, environments, runtime modes, and non-empty list values.
     Implemented.
2. Attach constraints to request context.
   - Either extend `ActorContext` with service constraints, or introduce a
     narrow `ServiceActorContext` used only for service actors.
   - Keep raw API key material out of the context.
3. Check restrictions at endpoint boundaries.
   - First require the existing endpoint/action scope.
   - Load and validate the Agent.
   - Check Agent ID, owner reference, environment, runtime mode, and tool name
     before creating new records. Implemented for Agent ID, environment,
     runtime mode, and tool name.
4. Keep development fallback unchanged.
   - `development/dev-placeholder` continues to work in local/dev flows when
     service auth is not required.
   - Strict service-auth deployments should require explicit service config.
5. Add tests.
   - Allowed Agent succeeds.
   - Unknown Agent denies.
   - Wrong Agent denies without creating records.
   - Wrong environment denies without creating records.
   - Enforcement denies unless explicitly allowed.
   - Production denies unless explicitly allowed.
   - Wrong tool denies without creating records.
   - Broad wildcard access works only when explicitly configured.
   - Local development fallback remains unchanged.
   - Raw API keys never appear in responses, AuditLog metadata, telemetry
     metadata, or Evidence Bundles.

## Recommended Follow-up Issues

1. Add owner reference restrictions for service actors.
2. Add service actor Evidence Bundle export scope design once user RBAC
   direction is settled.
3. Add HumanApproval read/review service scope design if a real integration
   needs it.
4. Add safe denied-scope audit event design before enabling denial auditing.
5. Implement the DB-backed service actor registry and API key rotation after
   config-based restrictions are proven.

## Open Questions

- Should fine-grained service actor config live only in an environment variable,
  or should V1 also support a local JSON file path?
- Should missing fine-grained rules preserve current behavior in all local/dev
  modes, or only when `AGCP_REQUIRE_SERVICE_AUTH=false`?
- Should tool-name restrictions apply to telemetry events other than
  `tool_call_requested`?
- Should denied scope checks create AuditLog records immediately, or wait until
  denial-auditing noise and retention rules are clearer?
- Should Evidence Bundle export ever be allowed for service actors, or should it
  remain a human/auditor action in V1?
