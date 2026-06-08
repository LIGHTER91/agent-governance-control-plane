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
runtime policy evaluation yet. Evidence Bundle export includes Agent-scoped
Access Grants, safe Capability, Source, and ModelAsset references, and safe
Data Usage Profile summaries for granted Sources. A
compact read-only Agent Governance Profile endpoint now surfaces Agent metadata,
recent activity, HumanApproval summary, Access Grants with safe inventory
target references, policy/rule ID references, and an Evidence Bundle export
hint without embedding Evidence Bundle contents. Policy and PolicyRule
management APIs exist for auditable lifecycle records and deterministic rule
conditions. Contextual runtime governance has a design for future decisions
that need Agent, Action, Source, data classification, ModelAsset, provider,
Capability, purpose, environment, AccessGrant, and Approval context. The first
schema slice is implemented as optional Runtime Gateway request fields and safe
TraceEvent metadata, and deterministic PolicyRules can now match those declared
contextual fields explicitly. Runtime decisions now resolve safe Capability,
Source, ModelAsset, Data Usage Profile, and AccessGrant facts as deterministic
policy context while keeping caller-declared fields distinct. Optional
metadata-only pre-check execution can persist CheckResults behind a
disabled-by-default feature flag, but AccessGrant enforcement, Data Usage
Profile enforcement, and broader runtime behavior remain unchanged. Source Data
Usage Profile
now has a first backend foundation for Source-side governance metadata such as
classification, personal or sensitive data signals, purpose and processing
constraints, review status, and safe DPIA references. It is exposed through
nested Source API endpoints and audited with safe metadata. Runtime Gateway can
resolve profile fields as context and optionally run profile status checks, but
profile metadata is not automatically enforced or treated as legal
certification. Policy Pre-Checks
and Control Tools have a
design for safe, auditable checks that can inform future contextual
PolicyDecisions, starting with metadata-only checks over inventory, Data Usage
Profile, AccessGrant, ModelAsset, Capability, and HumanApproval state.
CheckTool and CheckResult persistence and internal execution helpers now exist
as a backend foundation, and Evidence Bundle export includes safe CheckResult
summaries for PolicyDecision-linked or Agent-scoped records. Runtime Gateway can
optionally execute active authored PolicyCheckSteps linked to matched
PolicyRules and persist linked CheckResults behind
`AGCP_RUNTIME_METADATA_PRE_CHECKS_ENABLED=true`, but this is disabled by
default and does not change final runtime decisions. `failure_behavior` is
recorded as evidence intent only. Scanner adapters, public CRUD APIs for
CheckTool/CheckResult management, and pre-check-driven enforcement remain out
of scope.
Runtime Gateway now evaluates active PolicyVersion snapshots where available,
including versioned PolicyRule conditions and versioned PolicyCheckStep
snapshots for metadata pre-check selection, while preserving unversioned
fallback for Policies without an active PolicyVersion. Telemetry policy
evaluation remains on the existing unversioned path. The active PolicyVersion
rollout and telemetry migration plan is documented in
`docs/POLICY_VERSION_ACTIVE_ROLLOUT.md`: new Runtime Gateway decisions can
store `policy_version_id`, telemetry decisions remain unversioned today,
historical PolicyDecisions remain nullable, and the single-active-version
invariant still needs a database-level hardening task before activation is
exposed as product workflow.
The frontend has a minimal dashboard shell, a read-only Agent list page backed
by `GET /agents`, a read-only Agent detail and Agent Governance
Profile UI backed by `GET /agents/{agent_id}/governance-profile`,
`GET /agents/{agent_id}/activity`, and
`GET /agents/{agent_id}/human-approvals`, read-only Runtime Gateway overview
and Runtime activity pages, a Human Approvals page with pending review actions,
and a read-only Evidence Bundle page backed by
`GET /agents/{agent_id}/evidence-bundle`. It also has an Integration Hub page
that explains Custom Runtime Gateway API, LangGraph, n8n, Dataiku, MCP, and
generic webhook/API connection patterns without making AGCP execute tools or
replace orchestrators, but no login/auth UI, no role-aware
frontend behavior, no Agent edit form, no dedicated inventory or
PolicyCheckStep management UI, no broad activity filtering or pagination, and
no Evidence Bundle PDF/download/signature actions.
The `/policies` route is now an IDE-style Policy Studio rather than a raw
Policy CRUD form. It includes repository-style Policy/PolicyRule navigation,
static templates, Blocks and Code DSL modes, `WHEN -> CHECK -> THEN -> PROVE`,
deterministic frontend compilation to supported `PolicyRule.condition` JSON,
local validation, generated JSON preview, unsupported-DSL save blocking, and
Save draft through existing APIs. Templates are static helpers, not backend
records. Local validation is not runtime simulation. Submit for review remains
disabled, and there is no Publish action. This satisfies much of the Policy
Studio authoring surface, but it does not close #56 as a review workflow:
Save draft still writes through existing Policy/PolicyRule APIs, formal review
request semantics are undecided, and activation/telemetry semantics remain #68
work.

Product assessment: AGCP is now an early governance control plane rather than
only a runtime decision logger. It can describe Agents, declared access,
inventory targets, policies, runtime decisions, approvals, audits, evidence,
and a consolidated profile view. The highest product risk is continuing to add
inventory models without deeper workflows that let users review, approve,
enforce, and export evidence for those records.

Validation caveat: migration-backed tasks should still be validated with online
`uv run alembic upgrade head` when a reachable PostgreSQL instance is available.

References:

- `docs/CONTEXTUAL_RUNTIME_GOVERNANCE_DESIGN.md`
- `docs/DATA_USAGE_PROFILE_DESIGN.md`
- `docs/POLICY_PRE_CHECKS_DESIGN.md`
- `docs/POLICY_CHECK_STEP_AUTHORING_DESIGN.md`
- `docs/POLICY_VERSIONING_REVIEW_DESIGN.md`
- `docs/POLICY_VERSION_ACTIVE_ROLLOUT.md`
- `docs/POLICY_STUDIO_ISSUE_ALIGNMENT.md`
- `docs/RUNTIME_GATEWAY_DESIGN.md`
- `docs/RUNTIME_GATEWAY_ENFORCEMENT_MODE.md`
- `docs/RUNTIME_GATEWAY_RESUME_ENDPOINT.md`
- `docs/LANGGRAPH_ADAPTER_DESIGN.md`
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

1. Close or mark #58 implemented if the current Policy Studio V1 satisfies the
   product acceptance bar; otherwise create narrower follow-ups for direct
   no-code block editing and PolicyCheckStep authoring.
2. Keep #76 open or mark partially implemented until a formal
   `docs/POLICY_STUDIO_DSL_DESIGN.md` exists.
3. Use the refreshed #56 design to narrow the remaining policy review workflow
   contract: draft-version Save draft semantics, review request shape, approval
   versus activation, rollback-copy UX, and frontend Submit for review wiring.
4. Implement #68 follow-ups from `docs/POLICY_VERSION_ACTIVE_ROLLOUT.md`:
   migrate telemetry to the active-version runtime loader, decide historical
   PolicyDecision backfill, and add a database-level single-active-version
   guard before activation, Publish, or runtime source-of-truth semantics.
5. Then implement backend Policy Review Workflow APIs and wire the frontend
   Submit for review action to those APIs without adding a direct Publish
   button.
6. Add guided PolicyCheckStep UI support only after versioning, review, and
   simulation semantics have a safe implementation path.
7. Use Access Grants as optional policy context without replacing
   PolicyDecision records.
8. Add focused AccessGrant and inventory review workflows only where they
   support approval, evidence, or policy decisions.
9. Add Permission domain model only if AccessGrant target semantics prove
   insufficient.
10. Add frontend auth and role-aware UI later.
11. Add CORS/proxy setup guidance if needed for local frontend/backend use.
12. Add OpenAPI examples for `GET /human-approvals` if missing.
13. Design team and organization-unit ownership resolution for Evidence Bundle
    export.
14. Add owner-based service actor scopes design.
15. Add safe denied-scope audit events.
16. Add admin management for persisted service actor scope and rule records.
17. Implement service actor API key rotation and admin workflows after registry
    management behavior is designed.
18. Add tests for overriding the Actor dependency with a non-development actor.
19. Add deeper separation-of-duties checks for HumanApproval review.
20. Add broad filtering and pagination for Runtime and Agent activity only
    after the backend read models need it.
21. Turn Integration Hub guidance into focused adapter packages only after
    stronger auth, caller enforcement, and packaging boundaries are designed.
22. Prototype a minimal dependency-free LangGraph adapter helper with fake tool
    tests before adding any LangGraph dependency.

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
- [x] Add IDE-style Policy Studio V1 for guided Policy/PolicyRule authoring
      without raw JSON as the main workflow.
- [ ] Add formal controlled Policy Studio DSL design document for #76,
      including grammar, supported fields/operators, compile targets,
      versioning/storage, diffs, and unsupported-field handling.
- [ ] Implement the narrowed #56 policy review workflow contract:
      draft-version Save draft behavior, review request semantics, explicit
      approval versus activation, and frontend Submit for review wiring.
- [ ] Migrate telemetry ingestion to the active-version runtime loader while
      preserving unversioned fallback, idempotency, and HumanApproval behavior.
- [ ] Decide whether historical PolicyDecision backfill is needed; if so,
      implement it as an explicit audited/admin migration path, not automatic
      runtime behavior.
- [ ] Add a database-level single-active PolicyVersion guard and cleanup
      guidance before any activation or Publish semantics.
- [ ] Implement backend Policy Review Workflow APIs after #56 and #68 are
      settled, then wire the frontend Submit for review action.
- [ ] Add focused AccessGrant and inventory review workflows only where they
      support approval, evidence, or policy decisions.
- [ ] Add Evidence Bundle PDF/download/signature actions later.
- [ ] Add CORS/proxy setup guidance if needed for local frontend/backend use.
- [ ] Add OpenAPI examples for `GET /human-approvals` if missing.
- [ ] Add frontend auth and role-aware UI.
- [ ] Add broad filtering and pagination for Runtime and Agent activity only
      after the backend read models need it.
- [ ] Turn Integration Hub guidance into focused adapter packages only after
      stronger auth, caller enforcement, and packaging boundaries are designed.
- [ ] Prototype a minimal dependency-free LangGraph adapter helper with fake
      tool tests before adding any LangGraph dependency.
- [ ] Use Access Grants as optional policy context without replacing
      PolicyDecision records.
- [ ] Implement Permission domain model only if AccessGrant target semantics
      prove insufficient.
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
- [ ] Implement lightweight Policy, PolicyRule, and PolicyCheckStep versioning
      and review lifecycle support.
      Implementation complete; validation pending only for online
      `uv run alembic upgrade head` against a reachable local PostgreSQL
      instance.
- [ ] Add active PolicyVersion references to PolicyDecision, CheckResult
      evidence context, and Evidence Bundle.
      Implementation complete; validation pending only for online
      `uv run alembic upgrade head` against a reachable local PostgreSQL
      instance.
- [ ] Migrate Runtime Gateway evaluation to active PolicyVersion snapshots.
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
- [x] Extend deterministic PolicyRule matching with explicit contextual fields.
- [x] Resolve safe inventory context for Runtime Gateway policy decisions.
- [x] Add opt-in Runtime Gateway metadata-only pre-check execution.
- [x] Add deterministic CheckResult outcome matching for explicit PolicyRule
      conditions.
- [x] Add initial policy versioning and review guardrails foundation.
- [x] Design PolicyCheckStep authoring model.
- [x] Add PolicyCheckStep persistence and API support for metadata-only checks.
- [x] Wire optional Runtime Gateway metadata pre-check execution to authored
      active PolicyCheckSteps behind the existing disabled feature flag.
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
- [x] Add LangGraph adapter boundary design.
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
- [x] Add Integration Hub product surface for runtime connection patterns.
- [x] Add successful Evidence Bundle export audit event.
- [x] Add denied Evidence Bundle export audit event for known Agents.
- [x] Add direct user owner access for Evidence Bundle export.
- [x] Add Runtime activity backend endpoint.
- [x] Add Runtime activity frontend page.
- [x] Add Capability inventory API.
- [x] Add Source inventory API.
- [x] Add ModelAsset inventory API.
- [x] Add AccessGrant inventory API.
- [x] Add Agent-scoped AccessGrant endpoint.
- [x] Add read-only Agent Governance Profile backend endpoint.
- [x] Add Agent Governance Profile frontend UI.
- [x] Extend Evidence Bundle for Access Grants and safe Capability, Source, and
      ModelAsset references.
- [x] Add contextual runtime governance context design.
- [x] Add Data Usage Profile design for Source governance metadata.
- [x] Add Policy Pre-Checks and Control Tools design.
- [x] Add Data Usage Profile persistence and API support for Source records.
- [x] Add safe Data Usage Profile summaries to Evidence Bundle export.
- [x] Add metadata-only Policy Pre-Check persistence foundation.
- [x] Add metadata-only Policy Pre-Check execution helpers.
- [x] Add safe CheckResult summaries to Evidence Bundle export.
- [x] Add optional contextual runtime request fields from the contextual runtime
      governance design.
- [x] Add Policy Studio issue alignment and roadmap cleanup for #58, #76, #56,
      #68, #57, #74, #61, and #50.
- [x] Add active PolicyVersion rollout and telemetry migration plan for #68.

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
