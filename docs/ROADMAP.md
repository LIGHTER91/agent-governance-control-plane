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
Minimal RBAC checks now exist for HumanApproval review actions and Evidence
Bundle export, including direct user owner export. Successful Evidence Bundle
exports and denied attempts against known Agents are audited with safe metadata.
Owner-based service actor restrictions, full user authentication, OIDC/SAML,
team membership resolution, production deployment, and operational hardening are
still missing. The frontend now has a minimal dashboard shell, a read-only Agent
list page backed by the backend Agent Registry API, a read-only Agent detail
page backed by the Agent Registry, Agent activity, HumanApproval, and Evidence
Bundle APIs, read-only Runtime Gateway overview and activity pages, a Human
Approvals page with pending review actions, and a read-only Evidence Bundle
page backed by the backend Evidence Bundle export API. It does not have login,
role-aware views, Agent edit forms, broad activity filtering or pagination,
Evidence Bundle PDF/download/signature actions, or enterprise-auth-backed review
workflows.

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
- Minimal Python runtime wrapper example.
- Generic runtime adapter example with retry, idempotency, and resume handling.
- Runtime Gateway enforcement mode design.
- LangGraph integration design.
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
- Owner-based service actor restrictions, user login, OIDC/SAML, persisted API
  key rotation, DB-backed service actor records, and broad user RBAC are not
  implemented.
- Policy versioning is not implemented.
- Runtime failure policy is global and minimal.
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
- DB-backed service actor registry design.
- `AGCP_REQUIRE_SERVICE_AUTH=true` rejects missing service keys on runtime and
  telemetry integration endpoints.
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
- Human Approvals page backed by `GET /human-approvals`, with approve, reject,
  and cancel actions shown only for pending approvals.
- Read-only Evidence Bundle page backed by
  `GET /agents/{agent_id}/evidence-bundle`.

Recommended next work:

- Add Policy and PolicyRule CRUD APIs with audit logging.
- Implement Tool, Data Source, Model, and Permission domain models.
- Add Policy CRUD UI after backend Policy CRUD exists.
- Add frontend auth and role-aware UI later.
- Add CORS/proxy setup guidance if needed for local frontend/backend use.
- Add OpenAPI examples for `GET /human-approvals` if missing.
- Design team and organization-unit ownership resolution for Evidence Bundle
  export.
- Add owner-based service actor scopes design.
- Add safe denied-scope audit events.
- Implement DB-backed service actor registry and API key storage.
- Implement service actor API key rotation after a DB-backed registry exists.
- Add tests for overriding the Actor dependency with a non-development actor.
- Add deeper separation-of-duties checks for HumanApproval review.

Important limitations:

- Auth is still minimal and config-based.
- Fine-grained service actor scopes are still config/env-based.
- No DB-backed service actor or API key registry exists.
- API key rotation has a design only; persisted rotation is not implemented.
- Owner-based service actor restrictions are not implemented.
- No user login, OIDC, SAML, JWT auth, users table, or roles table exists.
- No team membership or organization-unit resolver exists.
- HumanApproval and Evidence Bundle RBAC are minimal local checks, not full
  enterprise authorization.
- Frontend authentication and role-aware navigation are not implemented.
- The Agent list, Agent detail page, Runtime activity, and Evidence Bundle
  views are read-only and require the backend API to be running. Human Approval
  review actions are available only for pending approvals.
- The Agent detail page has no edit form.
- Agent and Runtime activity views do not have broad filtering, search, or
  pagination yet.
- The Evidence page does not provide PDF export, download, or cryptographic
  signing.
- Evidence Bundle export requires the backend actor to have `auditor` or
  `platform_admin` role, or to be the direct user owner of the Agent.
- Local CORS or a frontend proxy may be needed depending on browser/API setup.

References:

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
- Agent detail page. Completed as read-only.
- Agent activity/timeline backend endpoint. Completed as read-only.
- Agent activity/timeline frontend section. Completed as read-only.
- Runtime Gateway overview page. Completed as read-only.
- Runtime decisions/activity backend endpoint. Completed as read-only.
- Runtime decisions/activity page. Completed as read-only.
- Human Approvals page. Completed with pending review actions.
- Evidence Bundle page. Completed as read-only.
- Policy CRUD UI after backend Policy CRUD exists.
- Evidence Bundle download, PDF, and signing actions.
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
- Policy and PolicyRule versioning.
- Risk review dashboard.
- SIEM/GRC integrations.
- Tool, Data Source, Model, and Permission domain coverage.
- Policy and PolicyRule CRUD APIs with audit logging.
- LangGraph integration package only if requested after the spike is proven.
- Additional runtime/framework integrations.
- Compliance framework mapping support for evidence workflows, without claiming
  automatic compliance.

## Readiness Notes

The current backend is strong enough for local demos, deterministic backend
tests, and governance-flow validation. It is not ready for production
enforcement because service auth and fine-grained scopes are still config-based,
HumanApproval and Evidence Bundle RBAC are minimal, user authentication does not
exist, the service actor registry and API key rotation are design-only, and
deployment, observability, and operational controls are still missing.
