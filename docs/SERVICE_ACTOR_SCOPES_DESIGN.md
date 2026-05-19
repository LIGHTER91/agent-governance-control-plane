# Service Actor Scopes Design

## Status

Design proposal. Service actor API key authentication exists as a minimal
configuration-based foundation for runtime and telemetry integration endpoints.
It identifies a caller as:

```text
actor_type = "service"
actor_id = "service:<stable-id>"
```

It does not yet authorize that service actor beyond key validity. This document
defines a pragmatic V1 scope model for service actors without adding database
tables, a full RBAC engine, or user authentication.

AGCP remains an Agent Governance Control Plane. Service actor scopes should
govern integrations that call AGCP; they should not turn AGCP into an
orchestrator, tool executor, identity provider, or compliance certification
product.

## Why Scopes Are Needed

Minimal API key authentication answers "which service called this endpoint?"
It does not answer "what is this service allowed to do?"

Without scopes, a valid service key could become too broad:

- a telemetry-only integration could call runtime decision endpoints;
- a staging adapter could submit production runtime requests;
- one service actor could act for every Agent;
- a runtime service could export Evidence Bundles or read AuditLogs;
- a leaked key could create broader governance evidence than intended.

Scopes limit blast radius and make service actor behavior reviewable while the
project still avoids a full enterprise IAM implementation.

## Scope Dimensions

### Endpoint And Action Scope

Endpoint/action scope controls which API capabilities a service actor may call.
Examples:

- telemetry ingestion;
- runtime decision checks;
- runtime resume checks;
- Agent read access;
- Evidence Bundle export;
- HumanApproval read or review actions.

Endpoint scope should be checked before creating TraceEventRecord,
PolicyDecision, HumanApproval, or AuditLog records, except for a safe denied
scope audit event if that behavior is enabled.

### Agent Scope

Agent scope controls which registered Agents a service actor may act for.

V1 should support one or both of:

- explicit Agent IDs;
- owner references, such as `owner_type = "service"` and
  `owner_id = "service:<stable-id>"`.

Explicit Agent IDs are easiest to reason about. Owner-based scope is useful for
service-owned Agents, but it should not accidentally grant access to team-owned
or organization-owned Agents without an explicit mapping.

### Environment Scope

Environment scope controls where a service actor can operate:

- `development`;
- `staging`;
- `production`.

Production should be more restrictive than development or staging. A service
actor that can submit development telemetry should not automatically be allowed
to request production enforcement decisions.

### Runtime Mode Scope

Runtime mode scope controls which Runtime Gateway modes a service actor can use:

- `simulation`;
- `enforcement`;
- future telemetry mode on the runtime endpoint if implemented.

Enforcement mode should require both:

- the existing global `AGCP_RUNTIME_ENFORCEMENT_ENABLED=true` flag;
- service actor scope that explicitly allows enforcement.

### Evidence And Export Scope

Evidence/export scope controls whether a service actor can read generated
evidence such as Evidence Bundles.

Evidence read access is more sensitive than telemetry write or runtime decision
access because it may reveal operational governance history. It should be
separate from runtime scopes.

### Human Approval Scope

HumanApproval scope should distinguish:

- reading approval status for a runtime integration;
- approving, rejecting, or cancelling an approval.

Service actors should not be allowed to review HumanApproval records by default.
Human review is a human governance action unless a later design defines a narrow
machine-to-machine delegation case.

## Minimal V1 Scopes

Recommended initial scope names:

| Scope | Meaning | Initial service actor default |
| --- | --- | --- |
| `telemetry:write` | Submit telemetry events. | Allowed when explicitly configured. |
| `runtime:decision` | Call `POST /runtime/tool-calls/decision`. | Allowed when explicitly configured. |
| `runtime:resume` | Call `POST /runtime/tool-calls/resume`. | Allowed when explicitly configured. |
| `agent:read` | Read minimal Agent metadata needed by adapters. | Optional, explicit only. |
| `evidence:read` | Export or read Evidence Bundles. | Denied by default. |
| `human_approval:read` | Read approval status. | Denied by default unless a resume flow requires it. |
| `human_approval:review` | Approve, reject, or cancel HumanApprovals. | Denied by default. |

Additional scopes that should remain future work:

- `agent:write`;
- `policy:read`;
- `policy:write`;
- `audit_log:read`;
- `service_actor:admin`.

## Initial Service Actor Permissions

The first service actor scope implementation should allow only integration
actions that already exist in the backend:

- `telemetry:write`;
- `runtime:decision`;
- `runtime:resume`;
- optionally `agent:read` for adapters that need to verify minimal Agent
  metadata.

These scopes should still be constrained by Agent, environment, and runtime mode
where possible.

Example service actors:

| Service actor | Intended scopes |
| --- | --- |
| `service:telemetry-ingestor-staging` | `telemetry:write` for staging Agents only. |
| `service:langgraph-runtime-prod` | `runtime:decision`, `runtime:resume` for explicitly mapped production Agents. |
| `service:demo-adapter-dev` | `telemetry:write`, `runtime:decision`, `runtime:resume` for development Agents only. |

## Denied By Default

The following should not be allowed for service actors by default:

- `human_approval:review`;
- `policy:write`;
- `agent:write`;
- `evidence:read`, unless explicitly granted;
- `audit_log:read`, unless explicitly granted;
- broad access to all Agents;
- production enforcement mode;
- any access for unknown service actors;
- any access when configured scopes are missing.

This keeps service API keys focused on runtime integration, not governance
administration.

## Interaction Rules

### Agent Ownership

Agent ownership is represented by:

- `owner_type`;
- `owner_id`;
- `owner_name`;
- `owner_contact_email`.

For service actors, V1 can allow owner-based access when:

```text
actor_type = "service"
actor_id = "service:<stable-id>"
agent.owner_type = "service"
agent.owner_id = "service:<stable-id>"
```

If the Agent is owned by a team, user, or organization unit, the service actor
should need an explicit Agent ID or owner mapping. Team ownership should not
implicitly grant access to every service actor used by that team.

### Environment

Environment restrictions should be checked against the Agent environment and
the request context when present.

Recommended rules:

- a missing environment scope denies access outside local development;
- production access must be explicit;
- enforcement in production requires both environment and runtime mode scope;
- development fallback behavior may remain available only in local/dev mode.

### Service Actor ID

`actor_id` is the stable identity used in AuditLog, HumanApproval, and Evidence
Bundle records. It is not a secret and should not be derived from a raw API key.

Scope configuration should attach to the service actor ID, not to the raw key.
This lets key rotation change authentication material without changing
governance evidence identity.

### Endpoint-Level Restrictions

Endpoint scope should be checked before narrower resource checks:

1. resolve service actor from API key;
2. verify endpoint/action scope;
3. verify Agent scope;
4. verify environment scope;
5. verify runtime mode scope if relevant;
6. execute the existing endpoint workflow.

Unknown or invalid API keys should fail before endpoint code creates governance
records.

## Safe Defaults

V1 should use conservative defaults:

- missing scopes deny;
- unknown service actor denies;
- invalid API key denies before records are created;
- unsafe metadata is rejected regardless of scopes;
- production runtime and telemetry endpoints require valid service auth when
  production auth mode is enabled;
- local development may preserve the current `development/dev-placeholder`
  fallback when no API key is provided;
- enforcement mode requires both global enablement and explicit service actor
  scope;
- broad wildcard scope should be avoided at first and, if ever supported, should
  be limited to local/dev or platform-admin controlled configuration.

## Audit And Evidence Implications

Successful service actions should record the resolved actor:

```json
{
  "actor_type": "service",
  "actor_id": "service:langgraph-runtime-prod"
}
```

Denied scope checks should be auditable where it is safe and useful, especially
for production runtime endpoints. A denied scope audit event should include only
safe facts:

- service actor ID if known;
- endpoint or action family;
- Agent ID if safely known;
- environment if safely known;
- denial reason category, such as `missing_scope`.

It must not include:

- raw API keys;
- authorization headers;
- raw prompts;
- raw tool payloads;
- private customer data;
- unsafe metadata.

Evidence Bundles should continue to show service actor identity through
AuditLog, HumanApproval, TraceEventRecord, and PolicyDecision links. They should
not expose raw API keys or sensitive request payloads.

## Minimal Config-Based V1 Implementation Path

V1 should stay configuration-based and avoid database tables until key
management and ownership workflows are clearer.

Suggested path:

1. Extend service actor configuration with scopes.
   - Keep `AGCP_SERVICE_ACTOR_API_KEYS` for hashed key material.
   - Add a simple config value for service actor authorization, such as JSON or
     a local config file.
2. Resolve `X-AGCP-API-Key` to `ActorContext` as today.
3. Resolve an additional service authorization context:
   - `actor_id`;
   - scopes;
   - allowed Agent IDs;
   - allowed owner references;
   - allowed environments;
   - allowed runtime modes.
4. Add endpoint/action checks for:
   - `POST /telemetry/events` -> `telemetry:write`;
   - `POST /runtime/tool-calls/decision` -> `runtime:decision`;
   - `POST /runtime/tool-calls/resume` -> `runtime:resume`.
5. Add Agent and environment checks after the Agent is loaded and before new
   evidence records are created.
6. Add runtime mode checks for simulation and enforcement.
7. Return `401` for invalid or unknown keys.
8. Return `403` for known service actors without required scope.
9. Add safe audit logging for denied scope checks only when doing so will not
   leak secrets or create audit noise.
10. Add tests for missing scope, wrong Agent, wrong environment, wrong runtime
    mode, invalid key, no-key local fallback, and no raw key leakage.

Example future JSON-shaped configuration:

```json
[
  {
    "actor_id": "service:langgraph-runtime-prod",
    "scopes": ["runtime:decision", "runtime:resume"],
    "agent_ids": ["11111111-1111-4111-8111-111111111111"],
    "owner_refs": ["service:langgraph-runtime-prod"],
    "environments": ["production"],
    "runtime_modes": ["simulation", "enforcement"]
  }
]
```

The exact syntax can be decided during implementation. The important V1 rule is
that authorization remains explicit, testable, and separate from raw API key
material.

## Recommended Follow-up Issues

1. Implement config-backed service actor scopes without database tables.
2. Enforce `telemetry:write` on `POST /telemetry/events`.
3. Enforce `runtime:decision` on `POST /runtime/tool-calls/decision`.
4. Enforce `runtime:resume` on `POST /runtime/tool-calls/resume`.
5. Add Agent ID and owner reference restrictions for service actors.
6. Add environment restrictions for service actors.
7. Add runtime mode restrictions, including explicit enforcement permission.
8. Add production mode requiring service auth for runtime and telemetry
   endpoints.
9. Add safe audit events for denied service actor scope checks.
10. Add tests proving raw API keys never appear in logs, AuditLog metadata,
    telemetry metadata, or Evidence Bundles.
11. Design persistent service actor and API key storage only after the
    config-based model is proven.
12. Align service actor scopes with future user RBAC for HumanApproval review
    and Evidence Bundle export.

## Open Questions

- Should service actor authorization config be an environment variable, a local
  file, or both?
- Should `human_approval:read` be required for resume flows, or is the resume
  endpoint itself enough?
- Should service actors ever receive `evidence:read`, or should Evidence Bundle
  export remain human/auditor focused in V1?
- Should denied scope checks always create AuditLog records, or only in
  production auth mode?
- How should wildcard scopes be represented, if they are allowed at all?
