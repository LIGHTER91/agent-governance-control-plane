# Service Actor and API Key Design

## Status

Design proposal with a minimal local/config-based implementation now in place
for runtime and telemetry integration endpoints. The backend still uses the
local `ActorContext` development placeholder by default when no API key is
provided:

```text
actor_type = "development"
actor_id = "dev-placeholder"
```

The current implementation supports `X-AGCP-API-Key` and
`AGCP_SERVICE_ACTOR_API_KEYS` with SHA-256 key hashes. It does not implement
database tables, API key rotation, service actor scopes, RBAC, OIDC, SAML, JWTs,
or a production identity system.

AGCP remains an Agent Governance Control Plane. It should integrate with agent
frameworks and runtime adapters; it should not become an orchestrator, tool
executor, identity provider, or compliance certification product.

## Why Runtime Integrations Need Service Actors

Runtime and telemetry endpoints are usually called by software integrations, not
by a human user in a browser. Examples include:

- a runtime wrapper calling the Runtime Gateway before a tool call;
- an agent framework adapter sending telemetry events;
- a service integration checking whether a previously blocked tool call can
  resume after HumanApproval;
- CI or internal automation reporting agent activity in a controlled
  environment.

The current development actor is useful for local flow validation, but it is not
enough for production-like governance evidence because every integration appears
as the same actor. Service actors let AGCP answer:

- which integration submitted telemetry;
- which service requested a runtime decision;
- which service requested HumanApproval through policy evaluation;
- which service checked resume status;
- which service actor should be scoped to which Agents, environments, and
  endpoint families.

## Service Actor Identity

A service actor represents a machine integration, runtime adapter, or trusted
service account.

Required identity shape:

```text
actor_type = "service"
actor_id = "service:<stable-id>"
```

Rules:

- `actor_id` must be stable and non-secret.
- `actor_id` must not be an API key, token, credential, or raw client secret.
- `actor_id` should identify the service account or integration, not a single
  key version.
- API key rotation should not change the service actor identity unless the
  integration itself changes.
- Human-readable service names may exist later as metadata, but audit fields
  should use the stable actor ID.

Examples:

```text
actor_type = "service"
actor_id = "service:langgraph-support-prod"

actor_type = "service"
actor_id = "service:telemetry-ingestor-staging"
```

## Affected Endpoints

The first service actor path should focus on machine-called endpoints:

| Endpoint | Why service auth is needed |
| --- | --- |
| `POST /telemetry/events` | Identifies the integration that observed or emitted an Agent Run or Trace Event. |
| `POST /runtime/tool-calls/decision` | Identifies the runtime adapter requesting a governance decision before a governed action. |
| `POST /runtime/tool-calls/resume` | Identifies the integration checking whether a previously blocked action may proceed after HumanApproval. |

Human-facing endpoints such as HumanApproval review and Evidence Bundle export
need user authentication and RBAC, not service API keys by default. Service
actors may still need read or resume permissions in narrow integration-specific
cases, but they should not become broad administrator accounts.

## API Key Behavior

V1 uses an optional API key header for service integrations:

```http
X-AGCP-API-Key: <raw-api-key>
```

The raw key identifies a configured service actor only at request time.

The initial local/config-based implementation uses
`AGCP_SERVICE_ACTOR_API_KEYS` with comma-separated hashed entries:

```text
AGCP_SERVICE_ACTOR_API_KEYS=service:<stable-id>=sha256:<digest>
```

Only SHA-256 key hashes are configured. Raw API keys are accepted only in the
incoming `X-AGCP-API-Key` header for request-time comparison.

Required rules:

- raw API keys must never be stored;
- if persisted later, store only a strong hash of the key;
- raw API keys must never appear in application logs;
- raw API keys must never appear in AuditLog metadata;
- raw API keys must never appear in telemetry metadata;
- raw API keys must never appear in Evidence Bundles;
- raw API keys must not be echoed in API responses;
- key comparison should use a timing-safe comparison when implemented;
- key rotation should support multiple active key hashes during a short
  transition window if needed.

The API key is authentication material. It is not governance evidence. Evidence
should contain the resolved service actor:

```json
{
  "actor_type": "service",
  "actor_id": "service:langgraph-support-prod"
}
```

It should not contain the raw header value or a reversible representation of the
key.

## Current Minimal Approach

### Development Default

Local development keeps the existing default:

```text
actor_type = "development"
actor_id = "dev-placeholder"
```

This keeps tests and demos deterministic while application code continues to use
`ActorContext` instead of hardcoded actor constants.

### Optional API Key Header

Runtime and telemetry integration endpoints can inspect an optional API key
header such as `X-AGCP-API-Key`.

Implemented behavior:

1. If a valid API key is present, resolve it to:
   - `actor_type = "service"`;
   - `actor_id = "service:<stable-id>"`;
2. If the header is missing in local development, return the development actor.
3. If the header is invalid, reject the request before creating records.
4. In production later, require service authentication for runtime and telemetry
   endpoints. This is not implemented yet.

The production requirement should be controlled by explicit configuration. It
should not silently switch a local developer flow into strict auth without a
clear deployment choice.

### Minimal Service Scope

The first implementation should avoid a complex IAM model, but service actors
still need narrow scope.

Recommended minimal scopes:

- allowed endpoint family:
  - telemetry ingestion;
  - runtime decision;
  - runtime resume;
- allowed Agent IDs or owner IDs;
- allowed environments;
- active/disabled status.

This is enough to prevent one leaked or misconfigured integration key from
acting as every Agent in every environment.

## Audit Behavior

When service actor authentication is used, runtime and telemetry flows use the
resolved service actor identity wherever they would otherwise use the
development placeholder.

Expected behavior:

- telemetry-triggered HumanApproval requester fields use:
  - `requested_by_actor_type = "service"`;
  - `requested_by_actor_id = "service:<stable-id>"`.
- runtime-triggered HumanApproval requester fields use the same resolved service
  actor.
- Runtime Gateway decision and resume audit events use the resolved service
  actor where audit records are appended.
- Evidence Bundles show the resolved actor identity in AuditLog and
  HumanApproval records.
- Raw API keys never appear in the evidence chain.

The audit record should describe the governance action, not the secret used to
authenticate it.

Safe example:

```json
{
  "event_type": "human_approval_requested",
  "actor_type": "service",
  "actor_id": "service:langgraph-support-prod",
  "entity_type": "human_approval",
  "summary": "Human approval requested."
}
```

Unsafe example:

```json
{
  "actor_type": "service",
  "actor_id": "service:langgraph-support-prod",
  "metadata": {
    "api_key": "[forbidden]"
  }
}
```

## Failure Behavior

Service authentication failures should happen before telemetry, runtime
decisions, PolicyDecision records, HumanApproval records, or AuditLog records are
created.

Recommended behavior:

- missing key in local development: development actor is allowed if the local
  mode explicitly permits it;
- missing key in production runtime endpoints: reject;
- invalid key: reject;
- disabled service actor: reject;
- service actor outside Agent or environment scope: reject;
- unsafe metadata: reject regardless of service actor validity.

For enforcement mode, invalid or missing service authentication should be
treated as fail-closed. The wrapper should not execute the governed action when
it cannot obtain an authenticated decision.

## Security Risks

### Leaked API Key

A leaked API key could let an attacker submit telemetry, request runtime
decisions, or attempt resume checks as a trusted integration.

Mitigations:

- never log raw keys;
- store only hashes if keys are persisted;
- support key rotation;
- scope keys to Agents, environments, and endpoint families;
- audit service actor usage.

### Weak Key Rotation

If keys cannot be rotated quickly, an exposed key remains useful for too long.

Mitigations:

- include key creation and revocation timestamps later;
- allow disabling a service actor or key;
- support short transition windows for planned rotation.

### Shared Service Accounts

If multiple integrations share one service actor, evidence cannot identify which
integration performed an action.

Mitigations:

- create separate service actors per integration and environment;
- avoid one broad `service:runtime` account;
- use clear stable IDs.

### Overbroad Service Permissions

A service actor with access to all Agents and all endpoint families can bypass
ownership boundaries.

Mitigations:

- require explicit scopes before production use;
- start with Agent or owner scoping;
- review service actor scope in Evidence Bundle and audit views later.

### Bypassing Wrappers

API keys identify callers that use AGCP, but they do not prevent an application
from calling tools directly without the Runtime Gateway.

Mitigations:

- use integration design to make the wrapper the normal path;
- report gateway coverage later;
- audit which actions reached the control plane.

### Logging Keys Accidentally

Middleware, error handlers, reverse proxies, or debug logging can accidentally
record headers.

Mitigations:

- redact `X-AGCP-API-Key` and authorization-like headers by default;
- avoid request body logging;
- keep metadata safety rules centralized;
- keep tests proving raw keys do not appear in responses, logs, audit metadata,
  telemetry metadata, or Evidence Bundles.

## V1 Implementation Sketch

1. Extend `ActorContext` resolution. Implemented for runtime and telemetry
   integration endpoints.
   - Keep local default behavior for development.
   - Add optional `X-AGCP-API-Key` parsing behind configuration. Implemented.
2. Add an in-memory or configuration-backed service actor registry for the first
   development implementation. Implemented as hashed environment configuration.
   - Avoid database tables until rotation, management, and scope requirements
     are clearer.
3. Resolve a valid key to `ActorContext(actor_type="service",
   actor_id="service:<stable-id>")`. Implemented.
4. Require service auth for runtime and telemetry endpoints when production auth
   mode is enabled. Not implemented.
5. Add scope checks for Agent ID, environment, and endpoint family. Not
   implemented.
6. Add tests proving raw keys are not logged, persisted, returned, or exported.
   Implemented for the minimal config-based path.
7. Add persistent hashed API key storage only when a real management workflow is
   needed.

This path keeps the first implementation small while still moving runtime
integrations away from the shared development placeholder.

## Recommended Follow-up Issues

1. Add service actor scopes design.
2. Implement service actor scopes for Agent, environment, and endpoint access.
3. Add production mode requiring service authentication for runtime endpoints
   when production auth mode is enabled.
4. Require service actor authentication for telemetry ingestion when production
   auth mode is enabled.
5. Add API key rotation design and implementation.
6. Add persistent hashed API key storage when key management workflows exist.
7. Add audit visibility for service actor usage.
8. Add documentation for integration owners on request IDs, service actors, and
   safe metadata.

## Open Questions

- Should service actor configuration start as environment variables, a local
  config file, or database-backed records?
- Should runtime decision and telemetry ingestion use separate keys for the same
  integration?
- What is the minimum service scope needed before enforcement mode is safe in a
  production-like deployment?
- Should API key auth be accepted only over TLS-terminated deployments?
- How should service actor key rotation be represented in audit evidence without
  exposing key material?
