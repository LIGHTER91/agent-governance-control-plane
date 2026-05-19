# Identity, Authentication, Actor Model, and RBAC Design

## Status

Design proposal with a local `ActorContext` development stub implemented. The
current backend does not implement real authentication, authorization, identity
provider integration, service API keys, or persistent RBAC tables.

V0 uses the structured development placeholder:

```text
actor_type = "development"
actor_id = "dev-placeholder"
```

That placeholder is acceptable for local development and early backend flow
validation because the domain model already records `actor_type` and `actor_id`
on AuditLog and HumanApproval records. It is not acceptable for production
because it cannot distinguish users, reviewers, service integrations, or
administrative actors.

This design keeps AGCP positioned as an Agent Governance Control Plane. It does
not turn the product into an identity provider, workflow engine, orchestrator,
or replacement for enterprise IAM.

## Goals

- Replace the development placeholder with an auth-derived Actor without
  changing the AuditLog or HumanApproval model shape.
- Keep the first implementation pragmatic and V1-oriented.
- Support human users, service integrations, system actions, and local
  development.
- Define role and permission expectations before adding enforcement checks.
- Preserve clear evidence about who requested, changed, reviewed, or exported
  governance records.

## Non-goals

- Do not implement auth or RBAC in this design.
- Do not add database tables yet.
- Do not choose a final OIDC, SAML, or enterprise IAM vendor.
- Do not implement a full enterprise permission engine.
- Do not add complex ABAC, policy-as-code, OPA/Rego, Cedar, or workflow
  authorization.
- Do not claim legal compliance certification.

## Why The V0 Placeholder Is Acceptable Only Temporarily

The current backend can create Agents, ingest telemetry, evaluate policies,
create HumanApproval records, approve or reject them, append AuditLog records,
and export Evidence Bundles. These flows need an actor shape even before real
authentication exists.

Using `development/dev-placeholder` in V0 is acceptable because:

- it proves every privileged mutation has a place to store actor identity;
- it keeps AuditLog and HumanApproval schemas compatible with future auth;
- it avoids blocking backend domain work on enterprise IAM decisions;
- it makes local tests deterministic.

It is not production-ready because:

- all users and integrations appear as the same actor;
- reviewer identity is not meaningful;
- separation of duties cannot be enforced;
- service integrations cannot be scoped independently;
- Evidence Bundles cannot show who actually performed privileged actions.

The production path is to replace placeholder construction with a request-scoped
Actor dependency, not to redesign every domain model.

## Actor Model

An Actor is the source responsible for a governance-relevant action.

Initial actor types:

| actor_type | Meaning | Examples |
| --- | --- | --- |
| `user` | Authenticated human user | agent owner, reviewer, auditor, platform admin |
| `service` | Authenticated machine or integration | runtime gateway adapter, telemetry emitter, CI integration |
| `system` | Internal AGCP system action | scheduled expiration, migration-safe maintenance, internal automation |
| `development` | Local development placeholder only | local tests, demo flows, developer workstation |

Actor type should be stored on:

- AuditLog `actor_type`;
- AuditLog `actor_id`;
- HumanApproval `requested_by_actor_type`;
- HumanApproval `requested_by_actor_id`;
- HumanApproval `reviewed_by_actor_type`;
- HumanApproval `reviewed_by_actor_id`.

## actor_id Conventions

`actor_id` must be stable, non-secret, and not primarily an email address.

Recommended conventions:

| actor_type | actor_id convention | Notes |
| --- | --- | --- |
| `user` | `user:<external-id>` | External ID comes from OIDC/SAML or another identity provider later. Email may be profile/contact metadata, not the primary key. |
| `service` | `service:<service-account-id>` | Used for API-key or client-credential integrations such as runtime adapters and telemetry emitters. |
| `system` | `system:<system-actor-id>` | Used only for internal AGCP actions such as future expiration jobs. |
| `development` | `dev-placeholder` | Allowed only for local development, tests, and demos. |

The external identity provider ID should be immutable for the user within the
configured tenant. If an enterprise provider exposes only mutable usernames or
emails, V1 should store a provider subject or stable directory object ID
instead.

## Relationship To Agent Ownership

Agent ownership and Actor identity are related but not identical.

Current Agent ownership fields:

- `owner_type`;
- `owner_id`;
- `owner_name`;
- `owner_contact_email`.

Existing owner ID conventions:

- `owner_type = "user"` -> `owner_id = "user:<external-id>"`;
- `owner_type = "team"` -> `owner_id = "team:<slug>"`;
- `owner_type = "service"` -> `owner_id = "service:<slug>"`;
- `owner_type = "organization_unit"` -> `owner_id = "org_unit:<slug>"`.

Ownership answers who is accountable for an Agent. Actor identity answers who
performed a specific action. A user can act on behalf of a team-owned Agent if
RBAC and ownership rules allow it.

## User-facing Roles

Initial roles should be intentionally small:

| Role | Purpose |
| --- | --- |
| `viewer` | Read limited registry and non-sensitive governance state. |
| `agent_owner` | Manage owned Agents and view evidence for owned Agents. |
| `policy_admin` | Create and update Policies and Policy Rules. |
| `reviewer` | Approve or reject HumanApproval records within assigned scope. |
| `auditor` | View AuditLogs and export Evidence Bundles for review. |
| `platform_admin` | Configure platform-level settings and manage broad access. |

One user may hold multiple roles. V1 should avoid deeply nested role hierarchies
until real customer usage proves the need.

## Permission Matrix

The table below defines the intended first pass. "Scoped" means restricted by
Agent ownership, assigned review scope, environment, or platform configuration.

| Permission | viewer | agent_owner | policy_admin | reviewer | auditor | platform_admin |
| --- | --- | --- | --- | --- | --- | --- |
| Create Agent | No | Yes | No | No | No | Yes |
| Update Agent | No | Scoped | No | No | No | Yes |
| Create Policy | No | No | Yes | No | No | Yes |
| Update Policy | No | No | Yes | No | No | Yes |
| Ingest telemetry | No | No | No | No | No | Scoped service setup |
| Call Runtime Gateway decision endpoint | No | No | No | No | No | Scoped service setup |
| Approve/reject HumanApproval | No | No | No | Scoped | No | Emergency or delegated only |
| Export Evidence Bundle | No | Scoped | No | Scoped read | Yes | Yes |
| View AuditLog | No | Scoped | No | Scoped read | Yes | Yes |

Runtime and telemetry endpoints should usually be called by `service` actors,
not human browser users. A service actor should be scoped to specific Agents,
environments, or integration clients before production enforcement.

## Permission Details

### Create Or Update Agent

Allowed for:

- `agent_owner` for owned or newly assigned Agents;
- `platform_admin` for all Agents.

Rules:

- Agent creation must set `owner_type` and `owner_id`.
- Agent ownership changes should be treated as privileged updates.
- Future implementation should audit owner changes with old and new owner
  references.

### Create Or Update Policy

Allowed for:

- `policy_admin`;
- `platform_admin`.

Rules:

- Policy and Policy Rule mutations must be audited.
- Policy changes should eventually include policy versioning before broad
  enforcement rollout.
- `agent_owner` should not be able to unilaterally weaken global policies for
  owned Agents.

### Ingest Telemetry

Allowed for:

- scoped `service` actors for registered integrations;
- possibly `platform_admin` only for test/debug tools.

Rules:

- Service actor scope should include allowed Agent IDs or integration IDs.
- Unknown Agents remain rejected.
- Unsafe metadata remains rejected regardless of actor.

### Call Runtime Gateway Decision Endpoint

Allowed for:

- scoped `service` actors representing runtime adapters or framework
  integrations.

Rules:

- Service identity should be bound to the Agent or integration it represents.
- Enforcement mode should remain behind explicit configuration.
- Unknown Agents, unsafe metadata, and invalid modes should continue to fail
  before records are created.

### Approve Or Reject HumanApproval

Allowed for:

- `reviewer` within assigned scope;
- `platform_admin` only for emergency or delegated administrative review.

Rules:

- Reviewer actor must be recorded in `reviewed_by_actor_type` and
  `reviewed_by_actor_id`.
- A reviewer should not normally approve their own requested action.
- The approval must belong to the same Agent and PolicyDecision context.
- Only pending approvals can transition.

### Export Evidence Bundle

Allowed for:

- `auditor`;
- `platform_admin`;
- `agent_owner` for owned Agents when organization policy permits;
- `reviewer` only for approvals or Agents in assigned review scope.

Rules:

- Export should remain safe and filtered.
- Export itself should eventually append an AuditLog event such as
  `evidence_bundle_exported`.
- Export permissions may need environment-specific tightening for production
  Agents.

### View AuditLog

Allowed for:

- `auditor`;
- `platform_admin`;
- scoped `agent_owner` and `reviewer` if policy allows.

Rules:

- AuditLog remains append-only from public APIs.
- Audit metadata must stay safe and non-sensitive.
- Viewing logs should not expose raw prompts, credentials, private customer
  data, or raw tool payloads.

## Ownership Rules

### Agent Owner

Agent ownership is defined by `owner_type` and `owner_id`.

Supported owner types:

- `user`;
- `team`;
- `service`;
- `organization_unit`.

V1 should support ownership checks through a small resolver:

```text
actor -> direct user id
actor -> team memberships
actor -> service account ownership
actor -> organization unit membership
```

The resolver can start as a local stub for development and later use identity
provider claims or directory data.

### Team Ownership

For `owner_type = "team"`, a user with `agent_owner` role should be allowed to
manage the Agent only if the identity layer says they are a member or delegated
owner of `owner_id`.

### Service Ownership

For `owner_type = "service"`, service actors may ingest telemetry or call the
Runtime Gateway for the Agent if their service account is explicitly mapped to
that Agent or service owner.

Service ownership does not automatically allow policy administration or human
approval.

### Organization Unit Ownership

For `owner_type = "organization_unit"`, management should require either:

- an authorized user mapped to that unit;
- a platform admin;
- a future delegated owner group.

This should be V1.5 or later unless a real deployment requires it.

### Who Can Approve Decisions For An Agent

Recommended V1 rule:

- A `reviewer` may approve or reject only approvals in their assigned Agent,
  team, environment, or risk scope.
- An `agent_owner` should not automatically be a reviewer for high-risk or
  production actions.
- A `policy_admin` should not automatically approve exceptions to policies they
  administer.
- A `platform_admin` can perform emergency review only if audited clearly.

### Separation Of Duties

For V1, separation of duties should be simple and explicit:

- The actor who requested HumanApproval should not approve the same approval
  unless a platform setting explicitly permits it for development.
- Policy authors should not be the only reviewers of policy exceptions.
- Production and high/critical risk approvals should require reviewer scope
  that is separate from the service actor making the runtime request.

These rules should be enforced before production enforcement mode is used for
high-risk actions.

## Audit Requirements

Every privileged action must include actor identity.

At minimum:

- create/update Agent;
- create/update Policy;
- create/update Policy Rule;
- telemetry ingestion by service actors;
- Runtime Gateway decision calls by service actors;
- HumanApproval create/approve/reject/cancel;
- Evidence Bundle export;
- AuditLog access where audit-read auditing is enabled later.

Requirements:

- `actor_type` and `actor_id` are mandatory for privileged mutations.
- Auth-derived Actor replaces `development/dev-placeholder`.
- AuditLog must record the actor performing the action, not only the Agent
  owner.
- HumanApproval requester fields must record the actor that requested review.
- HumanApproval reviewer fields must record the actor that approved or rejected.
- System actions must use `actor_type = "system"` and a specific `actor_id`,
  not the development placeholder.
- Audit metadata must remain safe and must not include secrets, raw prompts,
  raw tool payloads, authorization headers, or private customer data.

## Integration Options

### Local Development Auth Stub

First implementation should add a request-scoped actor dependency that defaults
to the current development placeholder in local development:

```text
Actor(type="development", id="dev-placeholder", roles=[...])
```

This keeps tests deterministic while forcing application code to request an
Actor through one place.

### API Key For Service Integrations

Runtime adapters and telemetry emitters need machine identity before full
enterprise SSO.

V1 can support API keys or signed service tokens that map to:

- `actor_type = "service"`;
- `actor_id = "service:<service-account-id>"`;
- allowed Agent IDs;
- allowed endpoints;
- allowed environments.

The API key secret must never be stored or logged in plaintext. This design does
not choose the storage mechanism yet.

### OIDC/SAML Later For Enterprise Users

Enterprise users should eventually authenticate through OIDC or SAML.

Expected mapping:

- provider subject -> `actor_id = "user:<external-id>"`;
- group or role claims -> AGCP roles;
- optional directory lookup -> team and organization unit membership.

OIDC/SAML should come after the local actor dependency and service actor path
exist, so product behavior can be tested before enterprise IAM complexity.

## V1 Implementation Path

1. Continue using the local Actor dependency as the auth boundary.
   - Keep replacing hardcoded `development/dev-placeholder` constants at
     mutation call sites with a request-scoped Actor.
   - Keep default local behavior as the development actor.
2. Add API key or service actor support for runtime endpoints.
   - Scope service actors to allowed Agents and endpoint families.
   - Start with telemetry ingestion and Runtime Gateway decision/resume calls.
3. Add RBAC checks for HumanApproval review.
   - Ensure only scoped reviewers can approve, reject, or cancel.
   - Record real reviewer actor fields.
   - Prevent requester self-approval where configured.
4. Add RBAC checks for Evidence Bundle export.
   - Allow auditors and scoped Agent owners.
   - Audit exports when export auditing is implemented.
5. Add OIDC later.
   - Map enterprise user identity to `user:<external-id>`.
   - Map groups or claims to roles and ownership.
   - Keep provider details outside domain models.

This order avoids over-engineering IAM before the product has a stable control
surface, while still moving away from the development placeholder early enough.

## Security Risks And Limitations

- Placeholder actors make V0 evidence useful for flow validation, not for
  production accountability.
- API keys can be over-scoped if service actors are not restricted by Agent,
  environment, or endpoint.
- Group claims can be stale; reviewer scope should not rely only on unchecked
  client-provided data.
- AuditLog access can itself reveal sensitive operational context, even after
  metadata filtering.
- Evidence Bundle export may need stricter controls than ordinary read access.
- Break-glass platform admin actions must be rare and clearly audited.
- Separation of duties is partly organizational; V1 should enforce the rules it
  can prove from structured identity data.

## Recommended Follow-up Issues

1. Replace any future hardcoded development actor constants in new mutation
   paths with the existing request-scoped Actor dependency.
2. Add tests for overriding the Actor dependency once a non-development actor is
   introduced.
3. Add service actor authentication for telemetry and Runtime Gateway endpoints.
4. Add minimal role checks for HumanApproval approve/reject/cancel.
5. Add scoped Evidence Bundle export authorization.
6. Add audit event for Evidence Bundle export.
7. Design service API key storage and rotation.
8. Design OIDC user mapping to `user:<external-id>` and role claims.
9. Design team membership resolution for Agent ownership checks.
10. Add separation-of-duties checks for HumanApproval review.

## Open Questions

- Should `agent_owner` include Agent creation by default, or only updates after
  assignment?
- Should cancellation of HumanApproval be a reviewer action, requester action,
  or platform admin action?
- Which environments require stricter Evidence Bundle export permissions?
- Should service actors be scoped directly to Agent IDs, owner IDs, or
  integration IDs?
- What minimum audit-read logging is needed before auditors use the product in
  production?
