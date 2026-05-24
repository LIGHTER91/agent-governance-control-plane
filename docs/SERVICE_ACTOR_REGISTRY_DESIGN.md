# Service Actor Registry Design

## Status

Design plus a disabled-by-default backend foundation. The backend now has
SQLAlchemy models, an Alembic migration, internal lookup helpers, and a
registry-backed service actor authentication path behind
`AGCP_SERVICE_ACTOR_REGISTRY_ENABLED=true`. It does not add public registry CRUD
endpoints, frontend UI, key rotation endpoints, or production-ready key
management.

AGCP currently authenticates service actors through configuration:

- `X-AGCP-API-Key`;
- `AGCP_SERVICE_ACTOR_API_KEYS`;
- `AGCP_SERVICE_ACTOR_SCOPES`;
- `AGCP_SERVICE_ACTOR_SCOPE_RULES`;
- `AGCP_REQUIRE_SERVICE_AUTH`.

That config-based path remains the default behavior. When
`AGCP_SERVICE_ACTOR_REGISTRY_ENABLED=true`, runtime and telemetry service actor
authentication can resolve keys from the DB-backed registry. Endpoint/action
scopes and fine-grained rules still come from config. This design describes how
the registry can eventually own service actors, scopes, fine-grained rules, and
API key lifecycle.

AGCP remains an Agent Governance Control Plane. A service actor registry should
govern machine integrations that call AGCP; it should not turn AGCP into an
orchestrator, tool executor, identity provider, or compliance certification
product.

## Goals

- Persist stable service actor identities. Foundation implemented for service
  actor records.
- Persist API key metadata and hashed key material. Foundation implemented for
  API key records.
- Reuse the API key rotation lifecycle from
  `docs/SERVICE_ACTOR_API_KEY_ROTATION_DESIGN.md`.
- Move endpoint/action scopes and fine-grained rules out of environment
  variables when production-like key management is needed. Not implemented yet.
- Keep raw keys, credentials, request headers, raw prompts, and private customer
  data out of storage, logs, audit metadata, responses, and Evidence Bundles.
- Preserve local config-based auth as the default behavior.

## Non-goals

- Do not enable registry-backed auth by default.
- Do not add registry CRUD APIs until real user/admin authentication exists.
- Do not add OIDC, SAML, JWT, users, teams, or role tables here.
- Do not implement team or organization-unit ownership resolution here.
- Do not grant service actors Evidence Bundle export or HumanApproval review by
  default.
- Do not claim production-ready authentication.

## Service Actor Identity Model

A service actor represents a machine integration, runtime adapter, telemetry
ingestor, or trusted internal service that calls AGCP.

The stable ActorContext shape remains:

```text
actor_type = "service"
actor_id = "service:<stable-id>"
```

Rules:

- `actor_id` is stable, non-secret, and globally unique.
- `actor_id` identifies the service actor, not a specific API key version.
- API key rotation must not change `actor_id`.
- `actor_id` should appear in AuditLog, HumanApproval requester fields,
  TraceEventRecord-related evidence, and Evidence Bundles where service actor
  identity is relevant.
- `actor_id` must not contain raw API keys, tokens, credentials, customer data,
  or environment-specific secrets.

Examples:

```text
service:langgraph-support-prod
service:telemetry-ingestor-staging
service:runtime-wrapper-dev
```

## Service Actor Status Lifecycle

The registry should track service actor lifecycle separately from API key
lifecycle.

Recommended service actor statuses:

- `active`: actor can authenticate if a valid key and scopes match.
- `disabled`: actor is temporarily blocked; keys are not accepted.
- `retired`: actor is no longer used; keys should be revoked or expired.

Status rules:

- `disabled` is reversible and useful for incident response or rollout pauses.
- `retired` should be treated as terminal for normal operations.
- Disabling or retiring an actor should fail closed before telemetry,
  Runtime Gateway, PolicyDecision, HumanApproval, or action AuditLog records are
  created for the requested integration call.
- Actor status changes must append safe AuditLog events.

## Registry Tables

The persistence foundation implements `service_actors`,
`service_actor_api_keys`, `service_actor_scopes`, and
`service_actor_scope_rules`. Runtime and telemetry registry-auth actors read
endpoint/action scopes and fine-grained rules from these persisted rows when
`AGCP_SERVICE_ACTOR_REGISTRY_ENABLED=true`; config-auth actors continue to use
environment settings.

### `service_actors`

Suggested fields:

| Field | Purpose |
| --- | --- |
| `id` | Internal UUID primary key. |
| `actor_id` | Stable identity such as `service:runtime-prod`. Unique. |
| `display_name` | Human-readable name. |
| `description` | Safe operational description. |
| `status` | `active`, `disabled`, or `retired`. |
| `environment` | Optional primary environment, if useful. |
| `owner_type` | Optional owner reference for accountability. |
| `owner_id` | Optional owner reference for accountability. |
| `created_at` | Creation timestamp. |
| `created_by_actor_type` | Actor type that created the service actor. |
| `created_by_actor_id` | Actor ID that created the service actor. |
| `updated_at` | Last metadata or status update timestamp. |
| `disabled_at` | Timestamp for disabled status. |
| `retired_at` | Timestamp for retired status. |

The optional owner fields are for accountability and future scoping. They do not
implement team or organization-unit membership resolution by themselves.

### `service_actor_api_keys`

Suggested fields:

| Field | Purpose |
| --- | --- |
| `id` | Internal UUID primary key. |
| `service_actor_id` | FK to `service_actors.id`. |
| `key_id` | Non-secret key identifier. Unique. |
| `key_hash` | Non-reversible hash of the secret portion. |
| `hash_algorithm` | Versioned hash algorithm identifier. |
| `status` | `active`, `retiring`, `revoked`, or `expired`. |
| `created_at` | Creation timestamp. |
| `created_by_actor_type` | Actor type that created the key. |
| `created_by_actor_id` | Actor ID that created the key. |
| `activated_at` | Timestamp when the key became usable. |
| `retiring_at` | Timestamp when planned rotation started. |
| `grace_expires_at` | Timestamp when a retiring key stops being accepted. |
| `expires_at` | Hard expiration timestamp. |
| `revoked_at` | Revocation timestamp. |
| `last_used_at` | Last successful use timestamp. |
| `last_used_endpoint` | Last endpoint family. |

Raw API keys and full request headers must never be stored. Full key hashes
should not appear in AuditLog metadata or Evidence Bundles.

### `service_actor_scopes`

Implemented as a persistence foundation. Auth does not read these rows yet.

Fields:

| Field | Purpose |
| --- | --- |
| `id` | Internal UUID primary key. |
| `service_actor_id` | FK to `service_actors.id`. |
| `scope` | Endpoint/action scope string. |
| `created_at` | Creation timestamp. |
| `created_by_actor_type` | Future actor type that granted the scope. Not implemented yet. |
| `created_by_actor_id` | Future actor ID that granted the scope. Not implemented yet. |

Initial scope values should match the existing config model:

- `telemetry:write`;
- `runtime:decision`;
- `runtime:resume`.

Potential future scopes must remain explicit and separate:

- `evidence:read`;
- `human_approval:read`;
- `human_approval:review`.

Service actors should not receive Evidence Bundle export or HumanApproval review
scopes by default.

### `service_actor_scope_rules`

Implemented as a persistence foundation. Auth does not read these rows yet.

Fields:

| Field | Purpose |
| --- | --- |
| `id` | Internal UUID primary key. |
| `service_actor_id` | FK to `service_actors.id`. |
| `agent_ids` | JSON list of allowed Agent IDs or `*`. |
| `environments` | JSON list of allowed environments or `*`. |
| `runtime_modes` | JSON list of allowed runtime modes or `*`. |
| `tool_names` | JSON list of allowed tool names or `*`. |
| `created_at` | Creation timestamp. |
| `updated_at` | Last rule metadata update timestamp. |
| `created_by_actor_type` | Future actor type that created the rule. Not implemented yet. |
| `created_by_actor_id` | Future actor ID that created the rule. Not implemented yet. |

This mirrors the current `AGCP_SERVICE_ACTOR_SCOPE_RULES` behavior without
inventing a broader authorization engine.

## API Key Rotation Connection

The registry is intended to become the persistence layer for the key lifecycle defined in
`docs/SERVICE_ACTOR_API_KEY_ROTATION_DESIGN.md`.

Key states:

- `active`;
- `retiring`;
- `revoked`;
- `expired`.

The current registry-backed auth path accepts only active service actors with
active or retiring non-expired API keys. Future rotation workflows should
support:

- multiple key rows for the same service actor;
- two valid keys during a planned rotation grace period;
- immediate revocation for suspected compromise;
- hard expiration after `expires_at` or `grace_expires_at`;
- safe `last_used_at` updates for active and retiring keys;
- failed usage events that do not store raw key material.

Rotation changes which key versions can authenticate. It must not change the
service actor `actor_id` or broaden scopes.

## Request-time Resolution

DB-backed request-time resolution runs before creating governance records for
telemetry or Runtime Gateway requests when
`AGCP_SERVICE_ACTOR_REGISTRY_ENABLED=true`.

1. Extract `X-AGCP-API-Key`.
2. Hash the submitted key with the existing SHA-256 hash format.
3. Load the matching key and service actor from the registry.
4. Reject unknown, revoked, expired, disabled, or retired identities.
5. Compare the submitted secret hash to `key_hash` with timing-safe comparison.
6. Resolve `ActorContext(actor_type="service", actor_id=service_actor.actor_id)`.
7. Check endpoint/action scope from persisted `ServiceActorScope` records.
8. Check persisted `ServiceActorScopeRule` Agent, environment, runtime mode,
   and tool-name rules.
9. Only then continue into telemetry ingestion, runtime decision, or runtime
   resume behavior.

Invalid auth must fail closed for Runtime Gateway enforcement calls. AGCP does
not execute tools; wrappers and adapters must honor `proceed`.

## Owner-based Restrictions

Owner-based service actor restrictions remain future work.

The registry can store safe accountability references such as:

- `owner_type`;
- `owner_id`.

It can also later support owner-reference scope rules, but this should wait
until identity direction is clearer. Direct owner references are not a substitute
for team membership or organization-unit resolution.

Future owner-based rules should be conservative:

- service actors may act for explicitly listed Agent IDs;
- service actors may act for Agents whose `owner_type = "service"` and
  `owner_id` exactly matches the service actor;
- team, user, or organization-unit ownership should require explicit resolver
  logic before it grants access.

## Audit Events

Registry lifecycle changes should append immutable AuditLog records with safe
metadata.

Recommended event types:

- `service_actor_created`;
- `service_actor_updated`;
- `service_actor_disabled`;
- `service_actor_retired`;
- `service_actor_scope_granted`;
- `service_actor_scope_revoked`;
- `service_actor_scope_rule_created`;
- `service_actor_scope_rule_removed`;
- `service_actor_key_created`;
- `service_actor_key_rotated`;
- `service_actor_key_revoked`;
- `service_actor_key_expired`;
- `service_actor_key_auth_failed`.

Recommended entity fields:

```text
entity_type = "service_actor"
entity_id = service_actor.actor_id
```

Safe metadata may include:

- `service_actor_id`;
- `key_id`;
- `previous_key_id`;
- `new_key_id`;
- `scope`;
- `agent_id`;
- `environment`;
- `runtime_mode`;
- `tool_name`;
- `status`;
- `reason`;
- `failure_reason`;
- `grace_expires_at`;
- `expires_at`.

Unsafe metadata includes raw API keys, full key hashes, request headers, raw
request bodies, raw prompts, credentials, authorization values, and private
customer data.

Failed usage audit should be careful:

- unknown malformed keys can record `failure_reason = "unknown_key"` without the
  supplied value;
- known `key_id` with a bad secret can record
  `failure_reason = "hash_mismatch"`;
- revoked or expired keys can record `failure_reason = "revoked"` or
  `failure_reason = "expired"`;
- repeated failures may need rate limiting or aggregation to avoid audit noise.

## Migration Path From Config

The registry should not require a flag day.

Suggested migration path:

1. Keep current config-based auth unchanged. Implemented.
2. Add database tables and internal registry services behind tests. Implemented
   for service actors, API key records, endpoint/action scopes, and
   fine-grained scope rules.
3. Add a registry read path behind an explicit feature flag such as
   `AGCP_SERVICE_ACTOR_REGISTRY_ENABLED`. Implemented for service actor API key
   authentication on runtime and telemetry integration endpoints.
4. Provide a one-way import tool or documented manual process that converts
   existing safe config entries into service actor records and hashed key rows.
   Implemented as the internal `scripts/seed_service_actor_registry.py` helper
   for hashed API key config only.
5. Provide a one-way import tool for existing config scopes and fine-grained
   rules. Implemented as the internal
   `scripts/seed_service_actor_registry_scopes.py` helper.
6. Validate parity in staging by comparing accepted/rejected service actor
   behavior.
7. Enable registry-backed auth in production-like environments.

The import process must not require raw keys from existing deployments. The
current helper reads only `AGCP_SERVICE_ACTOR_API_KEYS` entries that already use
`sha256:<digest>`, creates missing `service_actors` and
`service_actor_api_keys` rows, and never prints or persists raw API keys.

The scope helper reads `AGCP_SERVICE_ACTOR_SCOPES` and
`AGCP_SERVICE_ACTOR_SCOPE_RULES`, creates missing `service_actor_scopes` rows,
and appends non-duplicate `service_actor_scope_rules` rows for existing service
actors. It is dry-run by default, writes only with `--apply`, preserves existing
persisted records, reports missing service actors, and does not read, print, or
persist raw API keys. Config values remain the source of truth while the
registry flag is disabled or when the config-auth path is used.

Manual seeding workflow:

1. Keep `AGCP_SERVICE_ACTOR_REGISTRY_ENABLED=false`.
2. Ensure migrations have been applied.
3. Keep only hashed entries in `AGCP_SERVICE_ACTOR_API_KEYS`.
4. Run `uv run python scripts/seed_service_actor_registry.py` from `apps/api`
   to preview created actor/key IDs.
5. Run `uv run python scripts/seed_service_actor_registry.py --apply` from
   `apps/api` to create missing registry records.
6. Run `uv run python scripts/seed_service_actor_registry_scopes.py` from
   `apps/api` to preview scope/rule rows and missing actors.
7. Run `uv run python scripts/seed_service_actor_registry_scopes.py --apply`
   from `apps/api` to create missing scope/rule rows.
8. Validate one test service actor in a controlled environment with
   `AGCP_SERVICE_ACTOR_REGISTRY_ENABLED=true`.
9. Roll back by setting `AGCP_SERVICE_ACTOR_REGISTRY_ENABLED=false`.

## Rollout Strategy

Recommended phases:

1. Design and document the registry. Completed.
2. Add persistence models and migrations. Completed for service actors, API key
   records, endpoint/action scopes, and fine-grained scope rules.
3. Add internal lookup services with no public CRUD endpoints. Completed for
   lookup by actor ID, key ID, and key hash behind the disabled feature flag.
4. Add authentication lookup using the registry behind a feature flag.
   Completed for runtime and telemetry integration endpoints.
5. Wire persisted endpoint/action scopes and fine-grained rules into auth behind
   the registry flag. Completed for runtime and telemetry integration endpoints.
6. Add audit events for actor, scope, rule, and key lifecycle changes.
7. Add migration/import tooling for existing config-based service actors.
   Completed for local/manual seeding of hashed API key config and config-based
   scope/rule records.
8. Add admin endpoints only after real user auth and admin RBAC exist.
9. Consider frontend UI only after admin endpoints and user auth exist.

This keeps the registry inside the modular monolith and avoids adding a new
service boundary.

## Failure Modes And Rollback

### Registry Database Unavailable

If registry lookup fails, strict runtime enforcement should fail closed. The
wrapper must not execute tools without an authenticated decision.

The current implementation uses config auth when the registry flag is disabled
and registry auth when the flag is enabled. It does not implement an automatic
dual-read fallback.

### Bad Migration

If imported scopes are wrong, a service actor may be over-allowed or
under-allowed.

Mitigations:

- compare config and DB decisions in staging;
- start with read-only validation tools;
- keep the ability to disable the registry flag and return to config auth during
  rollout;
- audit registry changes;
- provide a quick way to disable an actor or revoke a key.

### Compromised Key

Use the rotation design: create a replacement key, revoke the compromised key,
and monitor failed usage. Revoked keys should not be reactivated.

### Accidental Actor Disablement

If an actor is disabled accidentally, re-enable the actor only after verifying
the intended scopes and keys. Append an audit event for the status change.

### Rollback From DB Registry To Config

Rollback may be necessary if DB-backed auth causes outages.

Safe rollback requirements:

- preserve existing config entries until DB auth is proven;
- avoid deleting config secrets during rollout;
- keep the feature flag reversible;
- document which deployment source of truth is active;
- audit when registry-backed auth is enabled or disabled if runtime settings are
  mutated through future admin APIs.

## Operational Risks

### Split Sources Of Truth

Config and DB can diverge during migration. Keep dual-read mode temporary and
make the active source of truth explicit in deployment configuration.

### Overbroad Scopes

Moving scopes to the database does not make them safe by itself. Scope review,
least privilege defaults, and safe denied-scope auditing remain necessary.

### Missing User Auth

Without real user auth, public registry CRUD endpoints would be unsafe. Registry
management should start as internal services or controlled operator tooling
until OIDC/SAML/JWT and admin RBAC exist.

### Team And Organization-unit Gaps

The registry cannot infer team membership or organization-unit ownership. Those
checks remain out of scope until an identity resolver exists.

### Secret Leakage

Raw keys can leak through logs, error messages, admin tooling, or import
scripts. Redact API-key-like values by default and never store raw keys.

### Audit Volume

Failed key usage and scope denials can generate many audit records. Later
implementation may need throttling or aggregation while preserving useful
security evidence.

## Out Of Scope Until Enterprise Auth Exists

The following should wait for real user auth, OIDC/SAML/JWT, and admin RBAC:

- public registry CRUD endpoints;
- frontend registry management UI;
- assigning service actor owners through team or organization-unit membership;
- granting service actors Evidence Bundle export by default;
- allowing service actors to approve, reject, or cancel HumanApprovals;
- policy-admin or auditor management of service actor records through the UI;
- broad delegated administration workflows.

## Open Questions

- Should a future migration mode compare config and registry auth decisions
  before operators switch an environment to registry-backed auth?
- Should scopes be attached only to service actors, or can individual keys be
  narrower than the actor?
- Should service actors have environment as a top-level field, a scope rule, or
  both?
- What minimum admin identity is required before CRUD endpoints are safe?
- Should failed auth events become AuditLog rows immediately, or should repeated
  failures be aggregated first?
