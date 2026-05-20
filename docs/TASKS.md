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
restrictions through `AGCP_SERVICE_ACTOR_SCOPE_RULES`. This is not
production-grade auth: scopes are still config/env-based, there is no DB-backed
key registry, no API key rotation, no owner-based restrictions, no
OIDC/SAML/JWT, and no team membership resolver. Minimal HumanApproval review
RBAC and Evidence Bundle export RBAC exist, but they are local role checks, not
full enterprise authorization. The frontend has a minimal dashboard shell, a
read-only Agent list page backed by `GET /agents`, and a read-only Human
Approvals page backed by `GET /human-approvals`, and a read-only Evidence
Bundle page backed by `GET /agents/{agent_id}/evidence-bundle`, but no
login/auth UI, no role-aware frontend behavior, no approval transition UI, and
no Evidence Bundle PDF/download/signature actions.

References:

- `docs/RUNTIME_GATEWAY_DESIGN.md`
- `docs/RUNTIME_GATEWAY_ENFORCEMENT_MODE.md`
- `docs/RUNTIME_GATEWAY_RESUME_ENDPOINT.md`
- `docs/LANGGRAPH_INTEGRATION_DESIGN.md`
- `docs/IDENTITY_AUTH_RBAC_DESIGN.md`
- `docs/SERVICE_ACTOR_API_KEY_DESIGN.md`
- `docs/SERVICE_ACTOR_SCOPES_DESIGN.md`
- `docs/SERVICE_ACTOR_FINE_GRAINED_SCOPES_DESIGN.md`
- `docs/HUMAN_APPROVAL_RBAC_DESIGN.md`
- `docs/EVIDENCE_BUNDLE_RBAC_DESIGN.md`

## Next Tasks

Recommended order:

1. Add Runtime Gateway page.
2. Add Agent detail page.
3. Add HumanApproval review actions UI later.
4. Add frontend auth and role-aware UI later.
5. Add CORS/proxy setup guidance if needed for local frontend/backend use.
6. Add OpenAPI examples for `GET /human-approvals` if missing.
7. Add owner-based access checks.
8. Add API key rotation design.
9. Add owner-based service actor scopes design.
10. Add safe denied-scope audit events.
11. Add DB-backed service actor registry design.
12. Add audit event for Evidence Bundle export.
13. Add Tool domain model.
14. Add Data Source domain model.
15. Add Model domain model.
16. Add Permission domain model.
17. Add Policy CRUD API.
18. Add PolicyRule CRUD API.
19. Add audit records for Policy and PolicyRule mutations.

## Backlog

- [ ] Add owner-based service actor scopes design.
- [ ] Add safe denied-scope audit events.
- [ ] Add API key rotation design.
- [ ] Add DB-backed service actor registry design.
- [ ] Add audit event for Evidence Bundle export.
- [ ] Add tests for overriding the Actor dependency with a non-development
      actor.
- [ ] Add owner-based access checks for Evidence Bundle export.
- [ ] Add deeper separation-of-duties checks for HumanApproval review.
- [ ] Add agent detail page.
- [ ] Add agent run timeline.
- [ ] Add policy decision timeline.
- [ ] Add human approval review view.
- [ ] Add Runtime Gateway page.
- [ ] Add HumanApproval review actions UI later.
- [ ] Add Evidence Bundle PDF/download/signature actions later.
- [ ] Add CORS/proxy setup guidance if needed for local frontend/backend use.
- [ ] Add OpenAPI examples for `GET /human-approvals` if missing.
- [ ] Add frontend auth and role-aware UI.
- [ ] Implement Tool domain model.
- [ ] Implement Data Source domain model.
- [ ] Implement Model domain model.
- [ ] Implement Permission domain model.
- [ ] Add Policy CRUD API.
- [ ] Add PolicyRule CRUD API.
- [ ] Add audit records for Policy and PolicyRule mutations.
- [ ] Extend Evidence Bundle for Tool, Data Source, Model, and Permission
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

Empty.

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
- [x] Add HumanApproval RBAC design.
- [x] Implement minimal RBAC checks for HumanApproval approve/reject/cancel.
- [x] Add Evidence Bundle RBAC design.
- [x] Implement minimal RBAC checks for Evidence Bundle export.
- [x] Add frontend dashboard shell.
- [x] Add read-only frontend Agent list page.
- [x] Add read-only frontend Human Approvals page.
- [x] Add read-only frontend Evidence Bundle page.

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
