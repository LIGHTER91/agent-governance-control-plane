# Tasks

This file is a lightweight project tracker. GitHub Issues should become the
source of truth once the repository is managed primarily through GitHub.

## Current Milestone

Runtime Gateway foundation: Done as a V0/V1 foundation, not production-ready.

Implemented runtime foundation:

```text
Runtime request
-> TraceEventRecord
-> Policy evaluation
-> PolicyDecision
-> optional HumanApproval
-> AuditLog
-> Evidence Bundle links
-> wrapper/adapter decides whether local tool execution proceeds
```

Important caveat: AGCP does not execute tools. Runtime enforcement depends on
wrappers or adapters consistently calling AGCP and honoring `proceed`.
Minimal config-based service actor API key authentication exists for runtime and
telemetry endpoints, including endpoint/action scopes and
`AGCP_REQUIRE_SERVICE_AUTH=true` strict mode. Config-based fine-grained service
actor rules now cover Agent ID, environment, runtime mode, and tool-name
restrictions through `AGCP_SERVICE_ACTOR_SCOPE_RULES`. The DB-backed service
actor registry can authenticate active service actors with active or retiring
non-expired keys behind `AGCP_SERVICE_ACTOR_REGISTRY_ENABLED=true`, and DB
persistence exists for endpoint/action scopes and fine-grained rules. This is
not production-grade auth: config auth remains the default, registry-backed
scope/rule auth must be explicitly enabled, there is no persisted API key
rotation implementation, no owner-based service actor restrictions, no
OIDC/SAML/JWT, and no team membership resolver.
Minimal HumanApproval review RBAC and Evidence Bundle export RBAC exist,
including direct user owner Evidence Bundle export, but they are local role
checks, not full enterprise authorization. Evidence Bundle successful exports
and denied attempts against known Agents are audited with safe metadata. A
minimal Capability inventory API exists for governed tools, APIs, integrations,
workflow actions, and other operations, and a minimal Source inventory API
exists for governed data and knowledge sources. A minimal Model inventory API
exists for governed model assets. A minimal Access Grant inventory API exists
for declared Agent access to governed targets, and Agents can read their own
Access Grants through `GET /agents/{agent_id}/access-grants`. AccessGrant is the
association layer for Agent-to-Capability, Agent-to-Source, and
Agent-to-ModelAsset declarations for now. Access Grants are not enforced by
runtime policy evaluation yet and are not included in Evidence Bundle yet. A
compact read-only Agent Governance Profile endpoint now surfaces Agent metadata,
recent activity, HumanApproval summary, Access Grants with safe inventory
target references, policy/rule ID references, and an Evidence Bundle export
hint without embedding Evidence Bundle contents. Policy and PolicyRule
management APIs exist for auditable lifecycle records and deterministic rule
conditions. The
frontend has a minimal dashboard shell, a read-only Agent list page backed by
`GET /agents`, a read-only Agent detail page backed by `GET /agents/{agent_id}`,
`GET /agents/{agent_id}/activity`, and
`GET /agents/{agent_id}/human-approvals`, read-only Runtime Gateway overview
and Runtime activity pages, a Human Approvals page with pending review actions,
and a read-only Evidence Bundle page backed by
`GET /agents/{agent_id}/evidence-bundle`, but no login/auth UI, no role-aware
frontend behavior, no Agent edit form, no broad activity filtering or
pagination, and no Evidence Bundle PDF/download/signature actions.

References:

- `docs/RUNTIME_GATEWAY_DESIGN.md`
- `docs/RUNTIME_GATEWAY_ENFORCEMENT_MODE.md`
- `docs/RUNTIME_GATEWAY_RESUME_ENDPOINT.md`
- `docs/LANGGRAPH_INTEGRATION_DESIGN.md`
- `docs/IDENTITY_AUTH_RBAC_DESIGN.md`
- `docs/SERVICE_ACTOR_API_KEY_DESIGN.md`
- `docs/SERVICE_ACTOR_API_KEY_ROTATION_DESIGN.md`
- `docs/SERVICE_ACTOR_REGISTRY_DESIGN.md`
- `docs/SERVICE_ACTOR_SCOPES_DESIGN.md`
- `docs/SERVICE_ACTOR_FINE_GRAINED_SCOPES_DESIGN.md`
- `docs/HUMAN_APPROVAL_RBAC_DESIGN.md`
- `docs/EVIDENCE_BUNDLE_RBAC_DESIGN.md`

## Next Tasks

Recommended order:

1. Extend Evidence Bundle for Access Grants and safe Capability, Source, and
   ModelAsset references.
2. Use Access Grants as optional policy context without replacing
   PolicyDecision records.
3. Add Permission domain model only if AccessGrant target semantics prove
   insufficient.
4. Add Policy management UI.
5. Add frontend auth and role-aware UI later.
6. Add CORS/proxy setup guidance if needed for local frontend/backend use.
7. Add OpenAPI examples for `GET /human-approvals` if missing.
8. Design team and organization-unit ownership resolution for Evidence Bundle
    export.
9. Add owner-based service actor scopes design.
10. Add safe denied-scope audit events.
11. Add admin management for persisted service actor scope and rule records.
12. Implement service actor API key rotation and admin workflows after registry
    management behavior is designed.
13. Add tests for overriding the Actor dependency with a non-development actor.
14. Add deeper separation-of-duties checks for HumanApproval review.
15. Add broad filtering and pagination for Runtime and Agent activity only
    after the backend read models need it.

## Backlog

- [ ] Add owner-based service actor scopes design.
- [ ] Add safe denied-scope audit events.
- [ ] Add admin management for persisted service actor scope and rule records.
- [ ] Implement service actor API key rotation and admin workflows after
      registry management behavior is designed.
- [ ] Add tests for overriding the Actor dependency with a non-development
      actor.
- [ ] Design team and organization-unit ownership resolution for Evidence
      Bundle export.
- [ ] Add deeper separation-of-duties checks for HumanApproval review.
- [ ] Add Policy management UI.
- [ ] Add Evidence Bundle PDF/download/signature actions later.
- [ ] Add CORS/proxy setup guidance if needed for local frontend/backend use.
- [ ] Add OpenAPI examples for `GET /human-approvals` if missing.
- [ ] Add frontend auth and role-aware UI.
- [ ] Add broad filtering and pagination for Runtime and Agent activity only
      after the backend read models need it.
- [ ] Extend Evidence Bundle for Access Grants and safe Capability, Source, and
      ModelAsset references.
- [ ] Use Access Grants as optional policy context without replacing
      PolicyDecision records.
- [ ] Implement Permission domain model only if AccessGrant target semantics
      prove insufficient.
- [ ] Extend Evidence Bundle for Capability, Data Source, Model, and Permission
      records.
- [ ] Add policy versioning design.
- [ ] Add approval notification design.
- [ ] Add retention policy design.
- [ ] Add production deployment design.
- [ ] Add LangGraph production adapter package only if explicitly requested.

## In Progress

Empty.

## Implementation Complete, Validation Pending

Use this section when implementation is complete but tests/checks cannot run
because the local environment is missing required tooling, services, or
credentials.

- [ ] Wire DB-backed service actor registry lookup into integration auth behind
      `AGCP_SERVICE_ACTOR_REGISTRY_ENABLED=true`.
      Implementation complete; validation pending only for online
      `uv run alembic upgrade head` against a reachable local PostgreSQL
      instance.
- [ ] Add DB-backed service actor scope and fine-grained rule persistence.
      Implementation complete; validation pending only for online
      `uv run alembic upgrade head` against a reachable local PostgreSQL
      instance.
- [ ] Wire persisted service actor scopes and fine-grained rules into auth
      behind the registry flag.
      Implementation complete; validation pending only for online
      `uv run alembic upgrade head` against a reachable local PostgreSQL
      instance.
- [ ] Import service actor scopes and fine-grained rules into registry.
      Implementation complete; validation pending only for online
      `uv run alembic upgrade head` against a reachable local PostgreSQL
      instance.
- [ ] Add capability inventory model.
      Implementation complete; validation pending only for online
      `uv run alembic upgrade head` against a reachable local PostgreSQL
      instance.
- [ ] Add source inventory model.
      Implementation complete; validation pending only for online
      `uv run alembic upgrade head` against a reachable local PostgreSQL
      instance.
- [ ] Add model inventory model.
      Implementation complete; validation pending only for online
      `uv run alembic upgrade head` against a reachable local PostgreSQL
      instance.
- [ ] Add access grant inventory model.
      Implementation complete; validation pending only for online
      `uv run alembic upgrade head` against a reachable local PostgreSQL
      instance.

## Done

- [x] Create Codex-ready documentation starter.
- [x] Initialize repository skeleton.
- [x] Add backend skeleton.
- [x] Add CI quality gates.
- [x] Add database and migrations baseline.
- [x] Implement Agent domain model.
- [x] Refactor Agent owner identity model.
- [x] Implement immutable AuditLog model.
- [x] Implement Agent Registry API.
- [x] Add audit records for Agent mutations.
- [x] Implement Policy, PolicyRule, and PolicyDecision domain models.
- [x] Add Policy management API with audit records for create, update, and
      status changes.
- [x] Add PolicyRule management API with audit records for deterministic rule
      conditions.
- [x] Implement simple deterministic Policy evaluator.
- [x] Add PolicyRule adapter for persisted rules.
- [x] Add PolicyDecision persistence service.
- [x] Define telemetry AgentRun and TraceEvent schemas.
- [x] Add AgentRunRecord and TraceEventRecord persistence.
- [x] Enforce TraceEventRecord to AgentRunRecord integrity.
- [x] Add telemetry event ingestion endpoint.
- [x] Add telemetry idempotency / duplicate protection.
- [x] Evaluate policies for telemetry `tool_call_requested` events.
- [x] Link PolicyDecision records to TraceEventRecord.
- [x] Implement HumanApproval model.
- [x] Implement Human Approval API with explicit transitions.
- [x] Enforce HumanApproval `agent_id` and `policy_decision_id` consistency.
- [x] Automatically create pending HumanApproval when telemetry policy decision
      requires human review.
- [x] Add audit log for automatically requested HumanApproval.
- [x] Add Evidence Bundle JSON export for one agent.
- [x] Include HumanApproval records in Evidence Bundle.
- [x] Include automatically created HumanApproval evidence chain in Evidence
      Bundle.
- [x] Add metadata safety baseline for telemetry, audit, and evidence export.
- [x] Add OpenAPI documentation examples for core backend endpoints.
- [x] Add executable V0 governance flow demo.
- [x] Consolidate V0 backend milestone documentation.
- [x] Add Runtime Gateway design proposal.
- [x] Add Runtime Gateway request/response schemas.
- [x] Implement Runtime Gateway simulation endpoint.
- [x] Add Runtime Gateway OpenAPI examples.
- [x] Add Runtime Gateway failure strategy design.
- [x] Add Runtime Gateway failure policy configuration design.
- [x] Add minimal runtime failure policy configuration.
- [x] Add Runtime Gateway failure-path tests.
- [x] Apply runtime failure default to selected policy evaluation failures.
- [x] Add Runtime Gateway enforcement mode design.
- [x] Implement Runtime Gateway enforcement mode behind explicit config.
- [x] Add Runtime Gateway evidence chain tests.
- [x] Add minimal runtime tool wrapper example.
- [x] Add generic runtime adapter example with retry and idempotency.
- [x] Add HumanApproval resume pattern design.
- [x] Add Runtime Gateway resume endpoint design.
- [x] Add Runtime Gateway resume schemas.
- [x] Implement Runtime Gateway resume endpoint.
- [x] Add Runtime Gateway resume OpenAPI examples.
- [x] Update generic runtime adapter example with resume flow.
- [x] Add LangGraph integration design.
- [x] Add dependency-free LangGraph adapter spike.
- [x] Add identity, authentication, actor model, and RBAC design.
- [x] Add local `ActorContext` development actor abstraction.
- [x] Use `ActorContext` in telemetry ingestion.
- [x] Add service actor and API key authentication design.
- [x] Implement minimal config-based service actor API key authentication for
      telemetry and Runtime Gateway endpoints.
- [x] Add service actor scopes design.
- [x] Implement endpoint/action service actor scopes for telemetry and Runtime
      Gateway endpoints.
- [x] Add strict service authentication mode for telemetry and Runtime Gateway
      endpoints with `AGCP_REQUIRE_SERVICE_AUTH`.
- [x] Add service actor fine-grained scopes design.
- [x] Implement config-based fine-grained service actor scopes for Agent ID,
      environment, runtime mode, and tool-name restrictions.
- [x] Add service actor API key rotation design.
- [x] Add DB-backed service actor registry design.
- [x] Add DB-backed service actor and API key registry persistence foundation
      behind a disabled feature flag.
- [x] Add registry import or manual seeding guidance for existing config-based
      service actors.
- [x] Add HumanApproval RBAC design.
- [x] Implement minimal RBAC checks for HumanApproval approve/reject/cancel.
- [x] Add Evidence Bundle RBAC design.
- [x] Implement minimal RBAC checks for Evidence Bundle export.
- [x] Add frontend dashboard shell.
- [x] Add read-only frontend Agent list page.
- [x] Add read-only frontend Agent detail page.
- [x] Add read-only frontend Runtime Gateway page.
- [x] Add read-only frontend Human Approvals page.
- [x] Add read-only frontend Evidence Bundle page.
- [x] Add Agent activity/timeline backend endpoint.
- [x] Add Agent activity/timeline frontend section.
- [x] Add HumanApproval review actions UI for pending approvals.
- [x] Validate HumanApproval review actions frontend behavior.
- [x] Add successful Evidence Bundle export audit event.
- [x] Add denied Evidence Bundle export audit event for known Agents.
- [x] Add direct user owner access for Evidence Bundle export.
- [x] Add Runtime activity backend endpoint.
- [x] Add Runtime activity frontend page.
- [x] Add read-only Agent Governance Profile backend endpoint.

## Blocked

Empty.

## Rule For Codex

Codex may update this file only when explicitly asked.

Codex must not move a task to Done unless:

- implementation is complete;
- tests were added or updated where relevant;
- relevant checks were run successfully;
- remaining risks were reported.

If checks cannot be run because the environment is missing, Codex must place or
report the task as "implementation complete, validation pending" instead of Done.
