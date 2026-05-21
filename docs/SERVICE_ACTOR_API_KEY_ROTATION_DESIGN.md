# Service Actor API Key Rotation Design

## Status

Design only. This document does not implement database-backed keys, migrations,
models, rotation endpoints, frontend UI, or changes to the current
configuration-based authentication behavior.

The current backend still authenticates runtime and telemetry service actors
through `X-AGCP-API-Key`, `AGCP_SERVICE_ACTOR_API_KEYS`,
`AGCP_SERVICE_ACTOR_SCOPES`, and `AGCP_SERVICE_ACTOR_SCOPE_RULES`. This is a
useful V0 foundation, but it is not production-grade key management.

AGCP remains an Agent Governance Control Plane. API key rotation should identify
and govern integrations that call AGCP; it should not turn AGCP into an
orchestrator, tool executor, identity provider, or compliance certification
product.

## Goals

- Let service actors rotate API keys without changing `actor_id`.
- Support a short planned rotation window where old and new keys both work.
- Store only safe key material and never persist raw API keys.
- Make key lifecycle changes auditable.
- Keep failed key usage visible without leaking secrets.
- Provide a clean path to a later DB-backed service actor registry.

## Non-goals

- Do not implement key rotation in this issue.
- Do not add tables, migrations, models, or endpoints in this issue.
- Do not change runtime or telemetry authentication behavior in this issue.
- Do not allow service actors to approve HumanApprovals or export Evidence
  Bundles through rotation.
- Do not claim production-ready authentication.

## Key Identity

A service actor remains the stable governance actor:

```text
actor_type = "service"
actor_id = "service:<stable-id>"
```

API keys are credentials for that service actor. Rotation changes key material,
not the service actor identity. AuditLog, HumanApproval, TraceEventRecord, and
Evidence Bundle evidence should continue to show the resolved `actor_id`, not a
raw key.

Future persisted keys should have a non-secret key identifier:

```text
key_id = "sak_live_2026_001"
```

Rules:

- `key_id` is public enough to store in AuditLog metadata.
- `key_id` must not be the raw API key or derived from the secret portion.
- `key_id` should be stable for one key version.
- Raw API keys may include the `key_id` as a prefix so lookup does not require
  scanning every key hash.
- If a key arrives without a recognizable `key_id`, the system should reject it
  without logging the raw value.

## Hashed Key Storage

Future persisted storage should keep only a non-reversible hash of the secret
portion of the API key.

Recommended persisted fields for a later `service_actor_api_keys` table:

| Field | Purpose |
| --- | --- |
| `id` | Internal UUID primary key. |
| `service_actor_id` | Stable actor ID such as `service:runtime-prod`. |
| `key_id` | Non-secret key identifier. Unique. |
| `key_hash` | Non-reversible hash of the secret portion. |
| `hash_algorithm` | Algorithm and version, for example `hmac-sha256:v1` or a later password-hash algorithm. |
| `status` | `active`, `retiring`, `revoked`, or `expired`. |
| `created_at` | Creation timestamp. |
| `created_by_actor_type` | Actor type that created the key. |
| `created_by_actor_id` | Actor ID that created the key. |
| `activated_at` | Timestamp when the key became usable. |
| `retiring_at` | Timestamp when planned rotation started. |
| `grace_expires_at` | Timestamp when a retiring key stops being accepted. |
| `expires_at` | Hard expiration timestamp for time-bound keys. |
| `revoked_at` | Timestamp when the key was revoked. |
| `last_used_at` | Last successful use timestamp. |
| `last_used_endpoint` | Last endpoint family, not a raw request. |

The current config-based implementation uses SHA-256 digests in environment
variables. That is acceptable for local V0 configuration, but future persisted
storage should prefer a versioned hashing strategy with a server-side pepper or
a slow password-hashing algorithm if project dependencies allow it.

Raw API keys, request headers, Authorization values, and full hash values must
never appear in AuditLog metadata, telemetry metadata, application logs,
responses, or Evidence Bundles.

## Key States

### Active

An `active` key is accepted for authentication if:

- the hash matches;
- the key is inside its validity window;
- the owning service actor is enabled;
- endpoint/action and fine-grained scope checks pass.

### Retiring

A `retiring` key is an old key during planned rotation. It remains accepted only
until `grace_expires_at`.

When a retiring key is used successfully, the system may update `last_used_at`
and should make the usage visible to operators so they can see whether an
integration has not switched to the new key yet.

### Revoked

A `revoked` key is denied immediately. Revocation is used for compromise,
decommissioning, or manual operator action.

Revoked keys should not be reactivated. If rollback is needed after revocation,
create a new key instead.

### Expired

An `expired` key is denied because its validity window or rotation grace period
has elapsed. Expiration may be set by scheduled maintenance or evaluated at
request time.

Expired keys should not be accepted even if the service actor itself remains
enabled.

## Planned Rotation Flow

Planned rotation should support two valid keys for the same service actor during
a short grace period.

1. Operator creates a new key for the existing service actor.
2. AGCP stores only the new key hash and safe key metadata.
3. AGCP marks the new key `active`.
4. AGCP marks the old key `retiring` and sets `grace_expires_at`.
5. AGCP appends `service_actor_key_rotated`.
6. Operators deploy the new raw key to the integration.
7. During grace, both keys can authenticate as the same service actor.
8. AGCP records `last_used_at` for whichever key is used.
9. After grace, AGCP marks the old key `expired` or requires explicit
   revocation.

The resolved ActorContext is the same for both keys:

```text
actor_type = "service"
actor_id = "service:<stable-id>"
```

Scopes belong to the service actor and, if needed later, can be narrowed per
key. V1 should start with actor-level scopes to avoid mixing rotation with a new
authorization model.

## Emergency Rotation Flow

Emergency rotation is for suspected compromise.

1. Operator creates a new key for the service actor.
2. Operator revokes the suspected key immediately, or uses the shortest possible
   grace period if an outage would be worse than short-lived exposure.
3. AGCP appends `service_actor_key_revoked` for the old key.
4. AGCP appends `service_actor_key_created` or
   `service_actor_key_rotated` for the replacement key.
5. Runtime and telemetry requests using the revoked key fail closed before
   TraceEventRecord, PolicyDecision, HumanApproval, or governance AuditLog
   records for the requested action are created.

Emergency rotation should favor safety over convenience. A revoked key should
not be accepted during rollback.

## Grace Period

The grace period is the planned overlap where two keys can coexist.

Recommended defaults:

- local development: flexible operator-chosen grace period;
- staging: 24 to 72 hours;
- production: as short as operationally practical, commonly 24 to 72 hours;
- emergency rotation: zero or near-zero grace.

Long grace periods increase exposure after a leaked old key. Very short grace
periods increase outage risk if integrations deploy slowly. The chosen value
should be visible in audit metadata as `grace_expires_at`, but the raw key must
never be logged.

## Audit Events

Key lifecycle events should append immutable AuditLog records.

Recommended event types:

- `service_actor_key_created`;
- `service_actor_key_rotated`;
- `service_actor_key_revoked`;
- `service_actor_key_expired`;
- `service_actor_key_auth_failed`.

Recommended entity fields:

```text
entity_type = "service_actor"
entity_id = service_actor_id
```

Safe metadata may include:

- `service_actor_id`;
- `key_id`;
- `previous_key_id`;
- `new_key_id`;
- `status`;
- `reason`;
- `endpoint_family`;
- `grace_expires_at`;
- `expires_at`;
- `failure_reason`.

Unsafe metadata includes:

- raw API keys;
- full request headers;
- Authorization values;
- key hashes;
- key hash prefixes that could help offline guessing;
- raw request bodies;
- private customer data.

Failed usage audit needs care. For unknown or malformed keys, record a generic
failure such as `failure_reason = "unknown_key"` without storing the supplied
value. For a known `key_id` whose hash does not match, use
`failure_reason = "hash_mismatch"`. For revoked or expired keys, use
`failure_reason = "revoked"` or `failure_reason = "expired"`.

To reduce audit noise and denial-of-service risk, later implementation can
rate-limit or aggregate repeated unknown-key failures, but it should preserve
enough evidence to investigate misuse.

## Rollback Strategy

Planned rotation rollback is allowed only while the old key is still
`retiring`.

If the new key deployment fails during the grace period:

1. Keep the old retiring key accepted.
2. Mark the new key `revoked` if it was distributed incorrectly or may be
   exposed.
3. Optionally move the old key back to `active`.
4. Append a safe audit event, either `service_actor_key_revoked` for the bad new
   key or a later `service_actor_key_rotation_rolled_back` event if the product
   needs a dedicated type.

If the old key is already `revoked` or `expired`, do not reactivate it. Create a
new key and redeploy.

Rollback must not change the service actor identity or broaden scopes. It should
only change which key versions can authenticate the same service actor.

## Request-Time Validation

Future DB-backed validation should follow this order:

1. Extract the raw `X-AGCP-API-Key` header.
2. Parse the non-secret `key_id`, if present.
3. Load the matching key record and service actor.
4. Reject missing, unknown, revoked, or expired keys before creating governance
   records for the requested action.
5. Compare the submitted secret with `key_hash` using timing-safe comparison.
6. Resolve `ActorContext(actor_type="service", actor_id=service_actor_id)`.
7. Check endpoint/action scopes.
8. Check fine-grained Agent, environment, runtime mode, and tool-name rules.
9. Proceed with telemetry or Runtime Gateway behavior only after authentication
   and authorization pass.

Invalid authentication must fail closed for Runtime Gateway enforcement calls.
The wrapper or adapter must not execute the local tool when it cannot obtain an
authenticated decision.

## Operational Risks

### Leaked Active Key

A leaked active key can submit telemetry or request runtime decisions as a
trusted integration. Mitigations include short-lived keys, emergency revocation,
fine-grained scopes, safe audit events, and avoiding broad shared service
actors.

### Long Grace Period

Long overlap means the old key remains useful after the new key is deployed.
Operators should choose the shortest practical grace period and monitor use of
retiring keys.

### Config Drift

During the current config-based phase, different processes can run with
different environment variables. A DB-backed registry should become the source
of truth before production-style rotation.

### Logging Secrets

Middleware, proxies, and debug handlers can leak headers. AGCP should redact
`X-AGCP-API-Key` and authorization-like headers before logs are written.

### Clock Drift

Expiration and grace windows depend on time. Use server-side UTC timestamps and
avoid client-provided validity times.

### Overbroad Service Actors

Rotation does not fix excessive scopes. A new key for an overbroad service actor
is still overbroad. Scope reviews should remain separate from key rotation.

### Rollback Abuse

Rollback can keep old credentials alive longer than intended. Rollback should be
audited and should never reactivate revoked keys.

## Path To DB-backed Service Actor Registry

The rotation model fits naturally into the DB-backed registry design in
`docs/SERVICE_ACTOR_REGISTRY_DESIGN.md`:

- `service_actors` stores stable service actor identity and enabled/disabled
  status.
- `service_actor_api_keys` stores key IDs, hashed secrets, lifecycle state, and
  timestamps.
- service actor scopes move from environment variables into database records.
- lifecycle operations append AuditLog records.
- runtime and telemetry authentication uses the DB registry first.
- local config-based auth can remain a development fallback until production
  configuration is ready.

Suggested implementation phases:

1. Add DB-backed service actor registry design. Completed as design only.
2. Add service actor and key persistence models plus migrations.
3. Add internal service functions for create, rotate, revoke, expire, and
   authenticate key records.
4. Add tests proving raw keys and hashes never enter AuditLog, telemetry
   metadata, responses, or Evidence Bundles.
5. Add guarded administrative endpoints only after user/admin authentication is
   available.

## Open Questions

- Should key-level scopes be supported, or should scopes remain actor-level for
  the first persisted implementation?
- Should expired keys be marked by a scheduled job, request-time evaluation, or
  both?
- What is the minimum audit retention window for failed key usage?
- Should production deployments require keys to expire automatically, or allow
  long-lived keys with manual rotation?
- Should local config-based auth support multiple hashes per service actor for
  development rotation drills, or should rotation wait for DB-backed storage?
