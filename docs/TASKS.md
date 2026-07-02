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
summaries for PolicyDecision-linked or Agent-scoped records. Review Inbox read
models also surface safe metadata-only CheckResult summaries for Runtime
HumanApproval records linked to PolicyDecisions. Runtime Gateway can
optionally execute active authored PolicyCheckSteps linked to matched
PolicyRules through the metadata-only CheckTool adapter boundary and persist
linked CheckResults behind
`AGCP_RUNTIME_METADATA_PRE_CHECKS_ENABLED=true`, but this is disabled by
default and does not change final runtime decisions. `failure_behavior` is
recorded as evidence intent only. A formal CheckTool adapter boundary now
defines safe request/result objects, execution modes, and metadata-only local
checks for AccessGrant status, Data Usage Profile status, Source
status/classification, ModelAsset status/provider type, and Capability status.
Persistent PolicyCheckStep check types now include `source_classification` and
`model_provider_type`, wired through the same metadata-only adapter. Adapter
metadata keeps provider labels separate from `external`/`local`/`unknown`
provider type classifications and records DPIA reference presence without
copying DPIA references into CheckResult metadata. Scanner adapters, public
CRUD APIs for CheckTool/CheckResult management, arbitrary webhooks/callbacks,
and pre-check-driven enforcement remain out of scope.
The local Docker demo loads its safe Runtime Gateway payload through the
first-class `scripts/seed_full_stack_demo.py --print-runtime-payload` path so
it uses the same `src` import bootstrap as the seed command instead of fragile
inline Python imports.
Runtime Gateway now evaluates active PolicyVersion snapshots where available,
including versioned PolicyRule conditions and versioned PolicyCheckStep
snapshots for metadata pre-check selection, while preserving unversioned
fallback for Policies without an active PolicyVersion. Telemetry policy
evaluation now uses the same active-version loader as Runtime Gateway. The
active PolicyVersion rollout and telemetry migration plan is documented in
`docs/POLICY_VERSION_ACTIVE_ROLLOUT.md`: new Runtime Gateway decisions can
store `policy_version_id`, new telemetry decisions can store
`policy_version_id` when an active version is used, historical PolicyDecisions
remain nullable, and the single-active-version invariant is enforced by API
validation plus a database-level partial unique index.
The frontend has a minimal dashboard shell, a read-only Agent list page backed
by `GET /agents`, a read-only Agent detail and Agent Governance
Profile UI backed by `GET /agents/{agent_id}/governance-profile`,
`GET /agents/{agent_id}/activity`, and
`GET /agents/{agent_id}/human-approvals`, a workflow-first Access & Data page
backed by `GET /access-grants`, `GET /sources`,
`GET /sources/{source_id}/usage-profile`, `GET /models`, and
`GET /capabilities`, a read-only Runtime Decisions timeline backed by
`GET /runtime/tool-calls/activity`, a Human Approvals page with pending review
actions, and a workflow-first Evidence & Audit explorer backed by
`GET /agents/{agent_id}/evidence-bundle`. Access & Data reviews real governed
metadata for Sources, Data Usage Profiles, Access Grants, Models, and
Capabilities; shows metadata check readiness without a score; filters unsafe
metadata before rendering summaries; preserves explicit Access Grant lifecycle
transitions; and does not inspect raw source content, run scanners, simulate
production impact, or certify legal compliance. It also has an Integration Hub page
that explains Custom Runtime Gateway API, LangGraph, n8n, Dataiku, MCP, and
generic webhook/API connection patterns without making AGCP execute tools or
replace orchestrators, but no login/auth UI, no broad enterprise role-aware
frontend behavior, no Agent edit form, no dedicated inventory or
PolicyCheckStep management UI, no broad activity filtering or pagination, and
no Evidence Bundle PDF/signature actions.
The `/policies` route is now an IDE-style Policy Studio rather than a raw
Policy CRUD form. It includes repository-style Policy/PolicyRule navigation,
honest Local backend / Policy repository labeling, backend-backed Policy
folders, static templates, editable Blocks canvas and Code DSL modes,
`WHEN -> CHECK -> THEN -> PROVE`, deterministic frontend compilation to
supported `PolicyRule.condition` JSON, compact IDE-style Blocks nodes with
consistent icons and visible connectors, Code DSL as the precise escape hatch,
local validation, generated JSON preview, unsupported-DSL save blocking, and
Save draft through draft `PolicyVersion` snapshots. Saved drafts no longer
rehydrate the editor from live PolicyRule fallback state; reload prefers the
latest draft PolicyVersion snapshot, then active PolicyVersion baseline, then
live PolicyRule fallback. Templates are static helpers, not backend records.
Policy folder grouping is persisted through `PolicyFolder` records and
nullable Policy `folder_id`; uncategorized Policies stay honest with
`folder_id = null`. Compact folder create, rename, move, and delete-empty
controls are backend-backed; deleting non-empty folders remains blocked until
Policies are moved elsewhere. Tags and repository/workspace metadata are still not
persisted, so Policy Studio must not render fake repositories, fake synced
workspace state, or fake tag chips. Policy Studio V1 keeps backend references
secondary in the repository and inspector, and the Blocks canvas, Code DSL,
compile bar, and local validation console all reflect the current editor state.
Local validation is not runtime simulation. Draft versions do not affect runtime
until explicit activation. Draft PolicyVersions with pending review requests are
immutable and require a new draft for additional changes. Submit for review
creates a dedicated pending PolicyVersionReviewRequest for a saved draft
snapshot, and a minimal Policy Reviews queue can approve or reject that request
without activating the version. Approved review requests can now be activated
explicitly with Activate approved version; replacement of an existing active
version requires explicit `replace_active` intent. Policy Reviews now show a
deterministic metadata-only Policy Review Diff with baseline type, changed
condition fields, runtime-effect copy, and activation/supersession audit
references when available. There is no Publish action.
This satisfies much of the Policy Studio authoring surface and the reduced #56
review/activation path. Rollback draft creation from prior PolicyVersion
evidence is implemented and remains review/activation-gated. Minimal reviewer
assignment for pending PolicyVersion review requests is implemented as
governance metadata: assignment does not approve, reject, activate, notify, or
change runtime state. Policy Reviews now fetches `GET /me` to display the
current actor and disable unavailable approve/reject/assign/activate actions
with honest reasons, but backend RBAC remains authoritative. Historical
PolicyDecision backfill remains a follow-up.
Policy Studio reads selected-draft review state through the narrow
`GET /policy-versions/{policy_version_id}/review-state` endpoint instead of
depending on the global reviewer/admin queue.
Legacy live Policy and PolicyRule mutation endpoints remain for bootstrap and
unversioned fallback Policies, but active-versioned Policies now have live-edit
guardrails: direct Policy and PolicyRule mutations are blocked with
`policy_live_edit_blocked` audit evidence and guidance to use draft
PolicyVersion review instead. Safe Policy archive/delete actions are
implemented: archive keeps evidence/history and is blocked while an active
PolicyVersion exists; delete is limited to draft-only Policies with no
versions, reviews, runtime decisions, linked HumanApproval history, or
meaningful audit history.

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
- `docs/POLICY_STUDIO_DSL_DESIGN.md`
- `docs/POLICY_VERSIONING_REVIEW_DESIGN.md`
- `docs/POLICY_VERSION_ACTIVE_ROLLOUT.md`
- `docs/POLICY_STUDIO_ISSUE_ALIGNMENT.md`
- `docs/FRONTEND_PRODUCT_BLUEPRINT.md`
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
   product acceptance bar; otherwise create narrower follow-ups for explicit
   operator persistence and PolicyCheckStep authoring.
2. Mark #76 implemented for V1 because
   `docs/POLICY_STUDIO_DSL_DESIGN.md` now defines the controlled DSL grammar,
   compile target, PROVE semantics, storage boundary, and diff behavior.
3. Treat minimal reviewer assignment as implemented; decide optional unassign
   behavior and richer role-aware frontend actions only after identity/RBAC are
   stronger.
4. Implement remaining #68 follow-ups from
   `docs/POLICY_VERSION_ACTIVE_ROLLOUT.md`: decide historical PolicyDecision
   backfill before publish-like or complete historical source-of-truth
   semantics.
5. Keep any future activation refinements explicit and avoid direct Publish
   wording.
6. Add guided PolicyCheckStep UI support only after versioning, review, and
   simulation semantics have a safe implementation path.
7. Use `docs/FRONTEND_PRODUCT_BLUEPRINT.md` as the #74 frontend product
   baseline: preserve validated Policy Studio and Review Inbox UX, and keep new
   pages workflow-first instead of API-shaped CRUD.
8. Use Access Grants as optional policy context without replacing
   PolicyDecision records.
9. Continue deepening Access & Data drill-downs only where they support
   approval, evidence, policy decisions, or metadata-only check authoring.
10. Add Permission domain model only if AccessGrant target semantics prove
   insufficient.
11. Add frontend auth and role-aware UI later.
12. Add CORS/proxy setup guidance if needed for local frontend/backend use.
13. Add OpenAPI examples for `GET /human-approvals` if missing.
14. Design team and organization-unit ownership resolution for Evidence Bundle
    export.
15. Add owner-based service actor scopes design.
16. Add safe denied-scope audit events.
17. Add admin management for persisted service actor scope and rule records.
18. Implement service actor API key rotation and admin workflows after registry
    management behavior is designed.
19. Add tests for overriding the Actor dependency with a non-development actor.
20. Add deeper separation-of-duties checks for HumanApproval review.
21. Add broad filtering and pagination for Runtime and Agent activity only
    after the backend read models need it.
22. Turn Integration Hub guidance into focused adapter packages only after
    stronger auth, caller enforcement, and packaging boundaries are designed.
23. Prototype a minimal dependency-free LangGraph adapter helper with fake tool
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
- [x] Add formal controlled Policy Studio DSL design document for #76,
      including grammar, supported fields/operators, compile targets,
      versioning/storage, diffs, and unsupported-field handling.
- [x] Implement rollback draft UX for prior PolicyVersion evidence without
      direct runtime rollback or automatic activation.
- [x] Implement the remaining narrowed #56 policy review workflow contract:
      reviewer assignment without automatic approval, activation, notification,
      or runtime changes.
- [ ] Decide whether historical PolicyDecision backfill is needed; if so,
      implement it as an explicit audited/admin migration path, not automatic
      runtime behavior.
- [ ] Add richer explicit activation UX only after review diff and assignment
      behavior is validated.
- [x] Add focused AccessGrant and inventory review workflows only where they
      support approval, evidence, or policy decisions.
- [ ] Add Evidence Bundle PDF/download/signature actions later.
- [ ] Add CORS/proxy setup guidance if needed for local frontend/backend use.
- [ ] Add OpenAPI examples for `GET /human-approvals` if missing.
- [x] Add minimal `/me`-backed current actor display and advisory role-aware
      PolicyVersion review actions without broad frontend auth.
- [x] Add legacy live Policy/PolicyRule mutation guardrails for Policies with
      an active PolicyVersion.
- [x] Add safe Policy archive/delete actions in Policy Studio and the backend,
      with archive retaining evidence/history and delete limited to draft-only
      Policies with no governance history.
- [x] Add backend-backed Policy folders to Policy Studio, including API-backed
      folder creation, list, move, and delete behavior with no fake repository
      folders.
- [x] Add editable Policy Canvas support for supported V1 condition fields while
      preserving the compact IDE-style WHEN/CHECK/THEN/PROVE layout and Code DSL
      escape hatch.
- [x] Fix Policy Studio authoring regressions so Save draft preserves the
      saved draft editor state and Blocks mode remains a compact IDE-style
      WHEN/CHECK/THEN/PROVE canvas.
- [x] Add frontend product blueprint for #74, documenting Policy Studio and
      Review Inbox as validated surfaces plus remaining workflow-first frontend
      gaps.
- [x] Implement the Overview page product narrative from #74 with
      know/control/prove workflow cards, current actor context, attention queue,
      runtime activity state, local metadata pre-check demo guidance, and no
      fake dashboard metrics.
- [x] Polish Access & Data into a workflow-first governed metadata workspace
      backed by AccessGrant, Source, DataUsageProfile, ModelAsset, and
      Capability APIs, with metadata check readiness and no raw-content,
      scanner, compliance-score, or production-simulation claims.
- [ ] Add full frontend auth and broader role-aware UI later.
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
- [x] Define Policy Pre-Check CheckTool adapter boundary and metadata-only
      safe request/result contract.
- [x] Wire Runtime Gateway metadata-only PolicyCheckStep execution through the
      CheckTool adapter boundary behind the existing feature flag.
- [x] Add initial policy versioning and review guardrails foundation.
- [x] Design PolicyCheckStep authoring model.
- [x] Add PolicyCheckStep persistence and API support for metadata-only checks.
- [x] Wire optional Runtime Gateway metadata pre-check execution to authored
      active PolicyCheckSteps behind the existing disabled feature flag.
- [x] Add persistent metadata-only PolicyCheckStep check types for Source
      classification and ModelAsset provider type.
- [x] Add deterministic local demo seed and documentation for metadata-only
      Runtime Gateway pre-check validation with active PolicyVersion evidence.
- [x] Add one-command Docker Compose local metadata pre-check demo script.
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
- [x] Consolidate Evidence & Audit into a workflow-first evidence explorer with
      Subject, Policy Decision, Metadata CheckResults, Human Review, Policy
      Review, Audit Trail, and Export bundle sections.
- [x] Add Agent activity/timeline backend endpoint.
- [x] Add Agent activity/timeline frontend section.
- [x] Add HumanApproval review actions UI for pending approvals.
- [x] Validate HumanApproval review actions frontend behavior.
- [x] Add Integration Hub product surface for runtime connection patterns.
- [x] Add successful Evidence Bundle export audit event.
- [x] Add denied Evidence Bundle export audit event for known Agents.
- [x] Add direct user owner access for Evidence Bundle export.
- [x] Add Runtime activity backend endpoint.
- [x] Add Runtime Decisions frontend timeline for request, context, active
      PolicyVersion or fallback policy, metadata checks, HumanApproval, and
      Evidence Bundle milestones.
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
- [x] Expose safe metadata-only CheckResult summaries in Review Inbox Evidence
      Preview for HumanApproval-linked PolicyDecisions.
- [x] Add optional contextual runtime request fields from the contextual runtime
      governance design.
- [x] Add Policy Studio issue alignment and roadmap cleanup for #58, #76, #56,
      #68, #57, #74, #61, and #50.
- [x] Add active PolicyVersion rollout and telemetry migration plan for #68.
- [x] Migrate telemetry ingestion to the active-version runtime loader while
      preserving unversioned fallback, idempotency, and HumanApproval behavior.
- [x] Add a single-active PolicyVersion guard with API fail-fast behavior and a
      database-level partial unique index.
- [x] Add PolicyVersion-backed Policy Studio Save draft with draft snapshot
      create/update APIs and no runtime activation side effects.
- [x] Add backend-backed PolicyVersion Submit for review and a minimal Policy
      Reviews queue with no runtime activation side effects.
- [x] Add explicit Activate approved version workflow for approved
      PolicyVersion review requests with `replace_active` supersede handling.
- [x] Add deterministic metadata-only Policy Review Diff and activation
      evidence references for PolicyVersion review requests.

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
