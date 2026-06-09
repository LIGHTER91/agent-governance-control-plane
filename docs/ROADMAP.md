# Roadmap

This roadmap tracks product maturity, not legal compliance status. The project
supports evidence collection and governance workflows; it does not certify that
an organization is compliant with any regulation or standard.

AGCP remains a governance and evidence control plane. It is not an agent
orchestrator and must not be positioned as a replacement for LangGraph, n8n,
Dataiku, CrewAI, AutoGen, cloud AI platforms, MCP servers, or other agent
runtimes.

## Current Reality

The Runtime Gateway foundation was pulled forward from the original roadmap.
The backend now has a significant runtime governance foundation, including
simulation, optional enforcement mode, resume checks, failure-policy basics, and
adapter examples.

This does not make the Runtime Gateway production-ready. Enforcement only works
when wrappers or adapters consistently call AGCP and honor `proceed`. Minimal
config-based service actor API key authentication now exists for runtime and
telemetry endpoints, including endpoint/action scopes and an explicit
service-auth-required mode. Config-based fine-grained service actor scope rules
also exist for Agent ID, environment, runtime mode, and tool-name restrictions.
DB-backed service actor registry auth can also use persisted endpoint/action
scopes and fine-grained rules when explicitly enabled.
Minimal RBAC checks now exist for HumanApproval review actions and Evidence
Bundle export, including direct user owner export. Successful Evidence Bundle
exports and denied attempts against known Agents are audited with safe metadata.
Owner-based service actor restrictions, full user authentication, OIDC/SAML,
team membership resolution, production deployment, and operational hardening are
still missing. The frontend now has a minimal dashboard shell, a read-only Agent
list page backed by the backend Agent Registry API, a read-only Agent detail
page backed by the Agent Registry, Agent activity, HumanApproval, and Evidence
Bundle APIs, a read-only Access & Data page backed by AccessGrant, Source, and
DataUsageProfile APIs, read-only Runtime Gateway overview and activity pages, a
Human Approvals page with pending review actions, and an Evidence Bundle page
backed by the backend Evidence Bundle export API. The Evidence page now loads
bundles only by manual user action, explains the evidence chain, shows safe
export warnings and metadata, and downloads the bounded JSON artifact returned
by the backend. The frontend also has an Integration Hub page for Custom
Runtime Gateway API, LangGraph, n8n, Dataiku, MCP, and generic webhook/API
connection guidance, with optional read-only Service Actor registry summary
metadata when registry admin APIs are enabled. It does not have login,
role-aware views, Agent edit forms,
broad activity filtering or pagination, Evidence Bundle PDF/signature actions,
runtime adapter packages, or enterprise-auth-backed review workflows.

AGCP is now closer to a true governance control plane than a runtime decision
logger: the backend can register Agents, inventory governed Capabilities,
Sources, and ModelAssets, declare Agent Access Grants, manage Policies and
PolicyRules, record runtime decisions and HumanApprovals, export Evidence
Bundles, and return a consolidated Agent Governance Profile. The frontend now
has a minimal Agent Governance Profile UI that consumes
`GET /agents/{agent_id}/governance-profile` and surfaces owner, status,
environment, risk level, Access Grants, recent activity, HumanApproval summary,
inventory references, policy/rule technical references, and an Evidence Bundle
availability hint.

Several important surfaces remain backend-only: Capability, ModelAsset, and
PolicyCheckStep management have APIs but no dedicated frontend management
workflows. Access Grants now have a read-only review UI for declared Agent
access, target references, reason, risk, grantor, expiration, safe metadata,
and links to Agent profiles, Evidence Bundle lookup, and Source/Data Usage
review. Source Data Usage Profiles now have a read-only review UI for
classification, personal/sensitive data flags, allowed and prohibited purposes,
processing constraints, review status, DPIA references, safe metadata, and
Source-targeting Access Grants. Policy and PolicyRule management now have an
IDE-style Policy Studio frontend surface. The Studio uses a repository sidebar,
static authoring templates, Blocks and Code DSL modes, a
`WHEN -> CHECK -> THEN -> PROVE` structure, local validation, deterministic
compilation to supported `PolicyRule.condition` fields, an inspector, and Save
draft through draft `PolicyVersion` snapshots. Unsupported DSL lines block
saving. Templates are static helpers, not backend records. Local validation is
not runtime simulation. Draft versions do not affect runtime until explicit
activation. Submit for review is still disabled, and there is no direct Publish
action. Access Grants are inventory declarations
only; they are not enforced by runtime policy evaluation yet. Evidence Bundle
export includes Agent-scoped Access Grants and safe Capability, Source, and ModelAsset
references plus safe Data Usage Profile summaries for granted Sources, but it
remains a bounded JSON review export rather than a full data catalog or
UI-oriented profile. The frontend Evidence page adds a review-friendly summary
and JSON download action, but JSON remains the canonical bounded export. The
Access & Data workflow and Evidence workflow do not certify legal compliance.
Full user authentication,
OIDC/SAML/JWT, team or organization-unit resolution, production service actor
administration mutations, API key rotation endpoints, runtime adapter
packages, notifications, deployment hardening, and operational runbooks are
still missing.

Contextual runtime governance now has a design path for future decisions that
need Agent, Action, Source, data classification, ModelAsset, provider,
Capability, purpose, environment, AccessGrant, and Approval context. The first
schema slice is implemented as optional runtime request fields and safe
TraceEvent metadata. Policy evaluation can match declared and resolved
contextual fields deterministically, and runtime decisions resolve safe
inventory facts. Metadata-only pre-check execution is available behind
`AGCP_RUNTIME_METADATA_PRE_CHECKS_ENABLED=true`, but default runtime behavior
and enforcement semantics remain unchanged.

Source Data Usage Profile now has a first backend foundation for Source-side
governance metadata needed by contextual runtime decisions, including
classification, personal or sensitive data signals, allowed and prohibited
purposes, processing constraints, review status, and safe DPIA references. It
is exposed through nested Source endpoints and audited with safe metadata.
Evidence Bundle export includes safe profile summaries for Sources referenced
by Agent AccessGrants. Runtime Gateway can resolve profile fields as
deterministic context and optionally run profile status checks, but Data Usage
Profile metadata is not automatically enforced or treated as legal
certification.

Policy Pre-Checks and Control Tools now have a design path for safe,
auditable checks that can inform future contextual PolicyDecisions. The design
starts with metadata-only checks over inventory, Data Usage Profile,
AccessGrant, ModelAsset, Capability, and HumanApproval state. A first backend
persistence and internal helper foundation now exists for CheckTool and
CheckResult records. Internal helpers can evaluate AccessGrant status, Data
Usage Profile review status, and Source, Capability, and ModelAsset inventory
status from persisted metadata only. Runtime Gateway can optionally execute
active authored PolicyCheckSteps linked to matched PolicyRules and persist
linked CheckResults behind an explicit disabled-by-default feature flag. No
scanner integration or automatic enforcement has been implemented. PolicyRules
can now explicitly match safe CheckResult outcome summaries with deterministic
`check_*` fields, so CheckResults remain policy context rather than hidden
decisions. The PolicyCheckStep authoring model is documented in
`docs/POLICY_CHECK_STEP_AUTHORING_DESIGN.md`.

Policy versioning and review guardrails are now partially implemented and
re-scoped in `docs/POLICY_VERSIONING_REVIEW_DESIGN.md`. A minimal backend
`PolicyVersion` aggregate snapshots Policy fields, associated PolicyRules, and
associated PolicyCheckSteps with draft, review, approval, activation,
archive, and rollback-copy APIs. PolicyDecision records can
optionally reference the active PolicyVersion for the selected Policy, and
Evidence Bundle renders safe PolicyVersion summaries on PolicyDecision and
linked CheckResult records. Runtime Gateway evaluates active PolicyVersion
snapshots where available and falls back to unversioned Policy/PolicyRule rows
for Policies without an active version. #56 remains needed but narrowed:
Policy Studio Save draft now writes draft PolicyVersion snapshots, Submit for
review is disabled, formal review request semantics are undecided, and review
UI/inbox/diff behavior has not been implemented.

Policy Studio issue alignment is tracked in
`docs/POLICY_STUDIO_ISSUE_ALIGNMENT.md`. The current implementation satisfies
most of the guided authoring goals from #58, while #76 should remain open or
partial until a formal controlled DSL design document defines grammar,
operators, storage/versioning, and diff behavior. #56 should now focus on the
remaining backend review workflow contract rather than broad versioning
foundation work. Active PolicyVersion rollout planning is documented in
`docs/POLICY_VERSION_ACTIVE_ROLLOUT.md`: Runtime Gateway already uses active
PolicyVersion snapshots with unversioned fallback, telemetry now uses the same
active-version loader, historical PolicyDecisions remain nullable/unversioned,
and the single-active-version invariant is enforced by API validation plus a
database-level partial unique index. Remaining #68 implementation follow-ups
should land before any activation, Publish, or historical-backfill semantics
are exposed as product workflow.

LangGraph integration now has a focused adapter boundary design in
`docs/LANGGRAPH_ADAPTER_DESIGN.md`. It defines where a LangGraph wrapper should
call the Runtime Gateway, how `proceed` enforcement remains the caller's
responsibility, how HumanApproval resume should preserve request identity, and
how Service Actor scoped API keys should be used. It is design-only and does
not create a production adapter package.

The next phase should deepen workflows instead of simply adding more models.
The main product risk is model sprawl without review, approval, evidence, and
policy workflows that help users answer what an Agent is allowed to use, why it
was granted, and how that permission is governed over time.

## Phase 0 - Project Foundation

Status: Completed.

Goal: make development safe, structured, and reviewable.

Completed:

- Repository structure.
- `AGENTS.md`.
- Product and architecture docs.
- Issue templates.
- PR template.
- Initial backlog.
- Backend quality CI.
- Documentation baseline check.
- Backend toolchain decisions.

## Phase 1 - V0 Backend Governance Flow

Status: Completed.

Goal: prove the governance core in a backend-only modular monolith.

Completed capabilities:

- FastAPI backend skeleton.
- PostgreSQL-targeted SQLAlchemy 2.x and Alembic baseline.
- Agent domain model and Agent Registry API.
- Capability inventory model and API for governed tools, APIs, integrations,
  workflow actions, and other operations.
- Source inventory model and API for governed knowledge bases, databases,
  document stores, APIs, buckets, filesystems, and other data or knowledge
  sources.
- Model inventory model and API for governed hosted LLMs, embedding models,
  rerankers, classifiers, vision models, audio models, and other model assets.
- Access grant inventory model and API for declared Agent access to governed
  Capabilities, Sources, ModelAssets, external targets, and other targets.
- Agent ownership model using `owner_type`, `owner_id`, `owner_name`, and
  optional contact email.
- Immutable application-level AuditLog foundation.
- Agent mutation audit records.
- Policy, PolicyRule, and PolicyDecision domain models.
- Minimal deterministic policy evaluator.
- Adapter from persisted active PolicyRule records to evaluator rules.
- PolicyDecision persistence service.
- Telemetry schemas and ingestion endpoint.
- AgentRunRecord and TraceEventRecord persistence.
- Telemetry idempotency.
- Policy evaluation for telemetry `tool_call_requested` events.
- Explicit `TraceEventRecord -> PolicyDecision` relationship.
- HumanApproval model.
- Human Approval API with explicit transitions.
- Automatic pending HumanApproval creation when a telemetry-triggered decision
  is `require_human_review`.
- Human approval audit logging.
- Evidence Bundle JSON export for one agent.
- Evidence Bundle coverage for TraceEventRecord, PolicyDecision,
  HumanApproval, and related AuditLog.
- Evidence Bundle coverage for Agent-scoped Access Grants and safe Capability,
  Source, and ModelAsset references.
- Evidence Bundle coverage for safe CheckResult summaries linked through
  PolicyDecisions or Agent-scoped pre-check records.
- Metadata safety filtering for telemetry, audit, and evidence export.
- OpenAPI examples for core backend endpoints.
- Executable V0 governance flow demo.

The completed V0 flow is:

```text
Agent Registry
-> Telemetry tool_call_requested
-> Policy evaluation
-> PolicyDecision
-> HumanApproval pending when require_human_review
-> AuditLog
-> Evidence Bundle JSON export
```

Reference: `docs/V0_GOVERNANCE_FLOW.md`.

## Phase 2 - Runtime Gateway Foundation

Status: Completed as a V0/V1 foundation; not production-ready.

Goal: provide a governed decision contract and evidence chain for runtime tool
calls without turning AGCP into an orchestrator.

Completed capabilities:

- Runtime Gateway design proposal.
- Runtime Gateway request and response schemas.
- `POST /runtime/tool-calls/decision` in simulation mode.
- Enforcement mode behind explicit configuration with
  `AGCP_RUNTIME_ENFORCEMENT_ENABLED=false` by default.
- Conservative `proceed` behavior:
  - `allow` -> `true`;
  - `deny` -> `false`;
  - `require_human_review` -> `false`;
  - `not_applicable` -> `false`.
- Runtime idempotency by `agent_id`, `run_id`, and `request_id`.
- Runtime TraceEventRecord creation.
- Runtime PolicyDecision persistence.
- Pending HumanApproval creation for runtime decisions that require review.
- Runtime HumanApproval audit logging.
- Runtime evidence bundle coverage tests.
- Runtime failure strategy design.
- Minimal global runtime failure policy config.
- Failure-path and rollback tests.
- OpenAPI examples for Runtime Gateway decision responses.
- HumanApproval resume pattern design.
- Runtime Gateway resume endpoint design.
- Runtime resume request and response schemas.
- `POST /runtime/tool-calls/resume`.
- Runtime resume idempotency by `agent_id`, `run_id`, and `resume_id`.
- Runtime resume TraceEventRecord and AuditLog evidence.
- OpenAPI examples for Runtime Gateway resume responses.
- Read-only `GET /runtime/tool-calls/activity` endpoint sorted newest first.
- Optional contextual runtime request fields for safe Action, Capability,
  Source, ModelAsset, purpose, classification, and sensitivity context.
- Minimal Python runtime wrapper example.
- Generic runtime adapter example with retry, idempotency, and resume handling.
- Runtime Gateway enforcement mode design.
- LangGraph integration design.
- LangGraph adapter boundary design.
- Dependency-free LangGraph adapter spike.

Important limitations:

- The gateway does not execute tools.
- Enforcement depends on wrappers or adapters respecting `proceed`.
- Framework adapters are examples/spikes, not production SDKs.
- Telemetry mode is still handled by `POST /telemetry/events`, not the runtime
  decision endpoint.
- Local `ActorContext` and minimal config-based service actor API key auth are
  implemented for runtime and telemetry endpoints.
- Endpoint/action service actor scopes and `AGCP_REQUIRE_SERVICE_AUTH=true` are
  implemented for runtime and telemetry endpoints.
- Config-based fine-grained service actor scope rules are implemented for Agent
  ID, environment, runtime mode, and tool-name restrictions.
- DB-backed service actor records, scopes, and rules are implemented behind a
  disabled feature flag, but public management APIs and rotation endpoints are
  not implemented.
- Owner-based service actor restrictions, user login, OIDC/SAML, persisted API
  key rotation, and broad user RBAC are not implemented.
- Policy versioning and review guardrails have a minimal backend foundation,
  evidence records can reference active PolicyVersions, and Runtime Gateway can
  evaluate active PolicyVersion snapshots with unversioned fallback. Review UI
  is not implemented.
- Runtime failure policy is global and minimal.
- Optional contextual request fields are accepted and recorded as safe runtime
  context, and deterministic PolicyRules can match those declared fields
  explicitly. Runtime decisions can resolve safe Capability, Source,
  ModelAsset, Data Usage Profile, and AccessGrant facts as deterministic policy
  context, but AccessGrant-aware enforcement and Data Usage Profile enforcement
  are not automatic yet.
- Data Usage Profile persistence, nested Source APIs, and safe Evidence Bundle
  summaries for granted Sources are implemented. Profile-aware Policy
  Pre-Checks and Data Usage Profile-aware runtime enforcement are not
  implemented yet.
- Policy Pre-Checks have CheckTool and CheckResult persistence, internal
  metadata-only execution helpers, optional Runtime Gateway execution behind
  `AGCP_RUNTIME_METADATA_PRE_CHECKS_ENABLED=true`, and safe Evidence Bundle
  summaries. Runtime Gateway can execute active authored PolicyCheckSteps
  linked to matched PolicyRules when the feature flag is enabled.
  `failure_behavior` is recorded as evidence intent only. PolicyRules may
  explicitly match safe CheckResult outcome summaries. Scanner adapters,
  automatic CheckResult-driven enforcement, and external tool execution are not
  implemented.
- Production deployment, monitoring, and operational runbooks are not
  implemented.

## Phase 3 - Identity, Service Actors, API Keys, and RBAC

Status: Started.

Goal: replace development actor placeholders with real actor identity and
minimal authorization checks before production runtime use.

Completed foundation:

- Identity, authentication, actor model, and RBAC design.
- Local `ActorContext` development actor abstraction.
- `ActorContext` usage in telemetry ingestion.
- Service actor and API key authentication design.
- Minimal config-based service actor API key authentication for:
  - `POST /telemetry/events`;
  - `POST /runtime/tool-calls/decision`;
  - `POST /runtime/tool-calls/resume`.
- Default local/dev behavior remains `development/dev-placeholder` when no API
  key is supplied.
- Valid service API keys resolve to `actor_type = "service"` and configured
  `actor_id = "service:<stable-id>"`.
- Endpoint/action service actor scopes for telemetry write, runtime decision,
  and runtime resume.
- Config-based fine-grained service actor scope rules with
  `AGCP_SERVICE_ACTOR_SCOPE_RULES` for Agent ID, environment, runtime mode, and
  tool-name restrictions.
- Service actor API key rotation design.
- DB-backed service actor and API key registry lookup behind
  `AGCP_SERVICE_ACTOR_REGISTRY_ENABLED=false` by default; when enabled, active
  service actors can authenticate with active or retiring non-expired keys.
- DB-backed service actor endpoint/action scope and fine-grained rule
  persistence wired into registry-backed auth behind the feature flag. Config
  auth still reads scopes and rules from environment settings.
- `AGCP_REQUIRE_SERVICE_AUTH=true` rejects missing service keys on runtime and
  telemetry integration endpoints.
- Read-only Service Actor registry admin APIs for service actors, key status
  metadata, scopes, and fine-grained scope rules when the registry feature flag
  is enabled.
- Minimal HumanApproval review RBAC for approve, reject, and cancel actions.
- Minimal Evidence Bundle export RBAC for `auditor`, `platform_admin`, and
  direct user owners.
- Service actors are denied Evidence Bundle export by default.
- Successful Evidence Bundle export audit events.
- Denied Evidence Bundle export audit events for known Agents.
- Next.js dashboard shell.
- Read-only Agent list page backed by `GET /agents`.
- Read-only Agent detail page backed by `GET /agents/{agent_id}`,
  `GET /agents/{agent_id}/activity`,
  `GET /agents/{agent_id}/human-approvals`, and optional Evidence Bundle
  access.
- Read-only Runtime Gateway overview page.
- Read-only Runtime activity page backed by
  `GET /runtime/tool-calls/activity`.
- Read-only Access & Data page backed by `GET /access-grants`, `GET /sources`,
  and `GET /sources/{source_id}/usage-profile` for Access Grant and Source Data
  Usage Profile review.
- Human Approvals page backed by `GET /human-approvals`, with approve, reject,
  and cancel actions shown only for pending approvals.
- Evidence Bundle page backed by `GET /agents/{agent_id}/evidence-bundle`,
  with manual JSON loading, human-readable evidence chain summary, safe export
  warnings, and bounded JSON download.
- Integration Hub page for Custom Runtime Gateway API, LangGraph, n8n, Dataiku,
  MCP, and generic webhook/API connection guidance, with clear copy that AGCP
  governs decisions and evidence but does not execute tools.
- Agent-scoped Access Grant reads through `GET /agents/{agent_id}/access-grants`,
  sorted newest first with `status` and `target_type` filters.
- Policy management API for auditable Policy lifecycle records.
- PolicyRule management API for deterministic rule conditions.
- Policy Studio frontend for Policy and PolicyRule authoring with static
  templates, Blocks and Code DSL modes, deterministic local validation,
  unsupported-DSL save blocking, and Save draft through draft PolicyVersion
  snapshots.
- Evidence Bundle export includes Agent-scoped Access Grants, safe Capability,
  Source, and ModelAsset references, and safe Data Usage Profile summaries for
  granted Sources.
- Metadata-only Policy Pre-Check persistence foundation for CheckTool and
  CheckResult records.
- Metadata-only Policy Pre-Check execution helpers for AccessGrant, Data Usage
  Profile, Source, Capability, and ModelAsset status.
- Safe CheckResult summaries in Evidence Bundle export.
- Optional contextual runtime request fields from
  `docs/CONTEXTUAL_RUNTIME_GOVERNANCE_DESIGN.md`, recorded as safe TraceEvent
  context.
- Deterministic PolicyRule matching for explicit contextual fields, resolved
  inventory context, and safe CheckResult outcome summaries.

Recommended next work:

- Close or mark #58 implemented if the current Policy Studio V1 satisfies the
  product acceptance bar; keep narrower follow-ups for direct no-code block
  editing and PolicyCheckStep authoring.
- Keep #76 open or partial until the controlled DSL has a formal design
  document covering grammar, storage/versioning, diffs, and unsupported-field
  behavior.
- Use the refreshed #56 policy versioning and review guardrails to define
  review request semantics before wiring the frontend Submit for review action.
- Implement the remaining #68 follow-up before exposing activation, Publish, or
  runtime source-of-truth semantics: decide historical PolicyDecision backfill.
- Add guided PolicyCheckStep UI support only after versioning, review, and
  simulation semantics have a safe implementation path.
- Use Access Grants as optional policy context without replacing
  PolicyDecision records.
- Add focused AccessGrant and inventory review workflows where they support
  approvals, evidence, or policy decisions.
- Implement Permission domain model only if AccessGrant target semantics prove
  insufficient.
- Add frontend auth and role-aware UI later.
- Add CORS/proxy setup guidance if needed for local frontend/backend use.
- Add OpenAPI examples for `GET /human-approvals` if missing.
- Design team and organization-unit ownership resolution for Evidence Bundle
  export.
- Add owner-based service actor scopes design.
- Add safe denied-scope audit events.
- Add admin management for persisted service actor scope and rule records.
- Implement service actor API key rotation and admin workflows after registry
  management behavior is designed.
- Add tests for overriding the Actor dependency with a non-development actor.
- Add deeper separation-of-duties checks for HumanApproval review.

Important limitations:

- Auth is still minimal. Config-based auth remains the default behavior.
- Registry-backed service actor auth uses persisted scopes and rules only when
  explicitly enabled; there are no public management APIs for those records.
- Registry-backed service actor auth is disabled by default and does not yet
  include public management APIs or rotation endpoints.
- API key rotation has a design only; persisted rotation is not implemented.
- Owner-based service actor restrictions are not implemented.
- No user login, OIDC, SAML, JWT auth, users table, or roles table exists.
- No team membership or organization-unit resolver exists.
- HumanApproval and Evidence Bundle RBAC are minimal local checks, not full
  enterprise authorization.
- Frontend authentication and role-aware navigation are not implemented.
- The Agent list, Agent detail page, Access & Data page, Runtime activity, and
  Evidence Bundle views require the backend API to be running. The Access &
  Data workflow is read-only. Human Approval review actions are available only
  for pending approvals.
- Access Grant status transition actions are not implemented in the frontend.
- The Agent detail page has no edit form.
- Agent and Runtime activity views do not have broad filtering, search, or
  pagination yet.
- The Evidence page provides bounded JSON download only; PDF export and
  cryptographic signing are not implemented.
- Evidence Bundle export requires the backend actor to have `auditor` or
  `platform_admin` role, or to be the direct user owner of the Agent.
- Local CORS or a frontend proxy may be needed depending on browser/API setup.

References:

- `docs/CONTEXTUAL_RUNTIME_GOVERNANCE_DESIGN.md`
- `docs/DATA_USAGE_PROFILE_DESIGN.md`
- `docs/POLICY_PRE_CHECKS_DESIGN.md`
- `docs/POLICY_VERSIONING_REVIEW_DESIGN.md`
- `docs/POLICY_VERSION_ACTIVE_ROLLOUT.md`
- `docs/POLICY_STUDIO_ISSUE_ALIGNMENT.md`
- `docs/LANGGRAPH_ADAPTER_DESIGN.md`
- `docs/IDENTITY_AUTH_RBAC_DESIGN.md`
- `docs/SERVICE_ACTOR_API_KEY_DESIGN.md`
- `docs/SERVICE_ACTOR_API_KEY_ROTATION_DESIGN.md`
- `docs/SERVICE_ACTOR_REGISTRY_DESIGN.md`
- `docs/SERVICE_ACTOR_SCOPES_DESIGN.md`
- `docs/SERVICE_ACTOR_FINE_GRAINED_SCOPES_DESIGN.md`
- `docs/HUMAN_APPROVAL_RBAC_DESIGN.md`
- `docs/EVIDENCE_BUNDLE_RBAC_DESIGN.md`

## Phase 4 - Product UI And Review Workflows

Status: Started.

Goal: make the backend workflow visible and reviewable for humans.

Planned capabilities:

- Dashboard shell. Completed.
- Agent list page. Completed as read-only.
- Agent detail page. Completed as read-only with the Agent Governance Profile
  UI.
- Agent activity/timeline backend endpoint. Completed as read-only.
- Agent activity/timeline frontend section. Completed as read-only.
- Runtime Gateway overview page. Completed as read-only.
- Runtime decisions/activity backend endpoint. Completed as read-only.
- Runtime decisions/activity page. Completed as read-only.
- Access Grant review UI. Completed as read-only.
- Source Data Usage Profile review UI. Completed as read-only.
- Human Approvals page. Completed with pending review actions.
- Evidence Bundle page. Completed with manual review summary and bounded JSON
  download.
- Agent Governance Profile backend endpoint. Completed.
- Agent Governance Profile frontend UI. Completed.
- Policy Studio IDE. Completed as a frontend authoring surface with
  repository-style Policy/PolicyRule navigation, static templates, Blocks and
  Code DSL modes, deterministic condition JSON compilation, local validation,
  and Save draft through draft PolicyVersion snapshots.
- Integration Hub page. Completed as a frontend product surface for runtime
  connection patterns, Service Actor expectations, setup snippets, and
  non-orchestrator boundaries.
- Policy versioning and review UI after #56 guardrails and #68 historical
  backfill decisions are complete.
- PolicyCheckStep management UI.
- Evidence Bundle PDF and signing actions.
- Frontend auth and role-aware UI later.

## Phase 5 - Enterprise Hardening And Expansion

Status: Not started.

Goal: prepare for serious enterprise usage while preserving the control-plane
boundary.

Planned capabilities:

- OIDC/SAML SSO integration.
- Retention policies.
- Signed or packaged evidence exports.
- Approval workflow enhancements.
- Runtime Gateway active-version rollout hardening and historical
  PolicyDecision backfill guidance.
- Risk review dashboard.
- SIEM/GRC integrations.
- Deeper Agent Governance Profile workflows for reviewing Access Grants,
  policy references, Evidence Bundle links, and inventory changes.
- Policy versioning and rule change review workflow hardening.
- LangGraph integration package only if requested after the spike is proven.
- Minimal dependency-free adapter helper prototype after the boundary design is
  validated with fake tool tests.
- Additional runtime/framework integrations.
- Integration Hub follow-through into adapter packages only after stronger auth,
  caller enforcement responsibilities, and packaging boundaries are designed.
- Compliance framework mapping support for evidence workflows, without claiming
  automatic compliance.

## Readiness Notes

The current platform is strong enough for local demos, deterministic backend
tests, and governance-flow validation across registry, runtime decisions,
inventory, access grants, policy lifecycle, human oversight, evidence export,
and the Agent Governance Profile. It is not ready for production enforcement:
config-based auth remains the default, registry-backed service actor auth is
feature-flagged, HumanApproval and Evidence Bundle RBAC are minimal, user
authentication does not exist, Access Grants are not enforced in runtime policy
evaluation, API key rotation is design-only, Integration Hub is guidance rather
than adapter packaging, several management surfaces are backend-only, and
deployment, observability, and operational controls are still missing.
