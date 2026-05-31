# Agent Governance Control Plane

An Agent Governance Control Plane for registering AI agents, recording what they
do, applying deterministic policy decisions, requesting human oversight, and
exporting reviewable evidence.

The product is a governance layer above existing agent stacks. It is **not** an
agent orchestrator and does not replace LangGraph, n8n, Dataiku, CrewAI,
AutoGen, Azure AI, AWS Bedrock, GCP Vertex AI, MCP servers, or similar runtime
platforms.

This project supports evidence collection and governance workflows. It does not
claim legal compliance certification.

## Product Vision

Organizations are deploying AI agents faster than they can govern them. This
control plane is intended to answer:

- Which AI agents exist?
- Who owns them?
- What are they allowed to do?
- What tools, models, and data sources can they access?
- What did they actually do?
- Which policy allowed, denied, or escalated an action?
- Who approved an agent, policy, action, or exception?
- What evidence can be exported for review?

## Current V0 Backend Status

The V0 backend governance flow is implemented and covered by tests:

```text
Agent Registry
-> Telemetry tool_call_requested
-> deterministic Policy evaluation
-> PolicyDecision
-> pending HumanApproval when decision = require_human_review
-> AuditLog
-> Evidence Bundle JSON export
```

See [V0_GOVERNANCE_FLOW.md](docs/V0_GOVERNANCE_FLOW.md) for the executable demo
scenario.

This is still a V0 backend milestone, not a production-ready enterprise control
plane. Runtime Gateway foundations, inventory APIs, Access Grants, auditable
Policy and PolicyRule management, Agent-scoped access reads, and an Agent
Governance Profile read model now exist. Service actor API key authentication
also exists, with config-based auth as the default and optional DB-backed
registry auth behind an explicit feature flag. Both paths support endpoint
scopes and fine-grained Agent/environment/runtime/tool restrictions, and
runtime and telemetry endpoints can require service authentication. AGCP does
not execute tools; runtime enforcement depends on wrappers or adapters calling
AGCP and honoring `proceed`. Minimal RBAC exists for HumanApproval review
actions and Evidence Bundle export. The frontend now exposes the core read-only
governance views, Runtime activity, pending HumanApproval review actions, and
an Agent Governance Profile UI.
Full user authentication, OIDC/SAML, team membership resolution, enterprise
auth-backed frontend workflows, notifications, production deployment, service
actor admin workflows, API key rotation implementation, and enterprise
integrations are intentionally not implemented yet.

## Implemented Capabilities

- FastAPI backend skeleton with health endpoint.
- PostgreSQL-targeted SQLAlchemy 2.x models and Alembic migrations.
- Agent Registry API.
- Agent ownership model using `owner_type`, `owner_id`, `owner_name`, and
  optional contact email.
- Capability inventory API for governed tools, APIs, integrations, workflow
  actions, and other operations.
- Source inventory API for governed knowledge bases, databases, document
  stores, APIs, buckets, filesystems, and other data or knowledge sources.
- Model inventory API for governed hosted LLMs, embedding models, rerankers,
  classifiers, vision models, audio models, and other model assets.
- Access grant inventory API for declared Agent access to governed
  Capabilities, Sources, ModelAssets, external targets, and other targets.
- Agent-scoped Access Grant read API for asking what a specific Agent is
  allowed to use.
- Read-only Agent Governance Profile endpoint that consolidates Agent metadata,
  recent governance activity, HumanApproval summary, Access Grants, inventory
  target references, policy/rule references, and an Evidence Bundle export hint
  without embedding full Evidence Bundle contents.
- Immutable application-level AuditLog foundation.
- Deterministic Policy, PolicyRule, and PolicyDecision domain models.
- Policy management API with auditable create, update, and status lifecycle
  changes.
- PolicyRule management API for deterministic rule conditions.
- PolicyCheckStep persistence API for declaring metadata-only checks expected
  by PolicyRules. When the disabled-by-default runtime metadata pre-check flag
  is enabled, active steps linked to matched PolicyRules can execute bounded
  metadata-only helpers and persist CheckResults as evidence without changing
  runtime decisions.
- Simple policy evaluator supporting explicit matching fields:
  `agent_id`, `tool_name`, `environment`, and `risk_level`.
- Adapter from persisted active PolicyRule records into evaluator rules.
- PolicyDecision persistence service.
- Telemetry schemas and `POST /telemetry/events` ingestion.
- AgentRunRecord and TraceEventRecord persistence.
- Telemetry idempotency by `(agent_id, run_id, external_event_id)`.
- Policy evaluation for `tool_call_requested` events using
  `metadata.tool_name`.
- Explicit `TraceEventRecord -> PolicyDecision` link.
- HumanApproval model and explicit transition API.
- Automatic pending HumanApproval creation for telemetry decisions that require
  human review.
- Minimal HumanApproval review RBAC for approve, reject, and cancel actions.
- Pending HumanApproval approve, reject, and cancel actions in the frontend.
- JSON Evidence Bundle export for one agent.
- Minimal Evidence Bundle export RBAC for `auditor`, `platform_admin`, and
  direct user owners.
- Service actors cannot export Evidence Bundles by default.
- Safe `evidence_bundle_exported` AuditLog records for successful Evidence
  Bundle exports.
- Safe `evidence_bundle_export_denied` AuditLog records for denied export
  attempts against known Agents.
- Evidence chain coverage across TraceEventRecord, PolicyDecision,
  HumanApproval, and related AuditLog.
- Evidence Bundle coverage for Agent-scoped Access Grants and safe Capability,
  Source, and ModelAsset references.
- Read-only Agent activity endpoint sorted newest first.
- Central metadata safety filtering for telemetry, audit, and evidence export.
- OpenAPI examples for core backend endpoints.
- Runtime Gateway simulation endpoint for governed tool-call decisions.
- Runtime Gateway enforcement mode behind explicit
  `AGCP_RUNTIME_ENFORCEMENT_ENABLED=true`.
- Runtime resume endpoint for checking whether a previously blocked action may
  proceed after HumanApproval.
- Read-only Runtime activity endpoint:
  `GET /runtime/tool-calls/activity`.
- Generic runtime adapter example and dependency-free LangGraph adapter spike.
- Local `ActorContext` abstraction with the default
  `development/dev-placeholder` actor.
- Minimal config-based service actor API key authentication for telemetry and
  Runtime Gateway endpoints.
- Config-based service actor endpoint scopes for telemetry write, runtime
  decision, and runtime resume calls.
- Config-based fine-grained service actor rules through
  `AGCP_SERVICE_ACTOR_SCOPE_RULES` for Agent ID, environment, runtime mode, and
  tool-name restrictions.
- Optional `AGCP_REQUIRE_SERVICE_AUTH=true` mode that rejects missing service
  API keys on runtime and telemetry integration endpoints.
- DB-backed service actor and API key registry lookup behind
  `AGCP_SERVICE_ACTOR_REGISTRY_ENABLED=false` by default; when enabled, active
  service actors can authenticate with active or retiring non-expired registry
  keys.
- DB-backed service actor endpoint/action scope and fine-grained rule
  persistence. Registry-backed actors use these persisted scopes and rules when
  the registry feature flag is enabled; config auth remains the default path.
- Next.js dashboard shell.
- Read-only frontend Agent list page backed by `GET /agents`.
- Read-only frontend Agent detail page backed by
  `GET /agents/{agent_id}/governance-profile`,
  `GET /agents/{agent_id}/activity`,
  `GET /agents/{agent_id}/human-approvals`, and optional manual Evidence
  Bundle access.
- Agent Governance Profile UI showing Agent identity, owner, status,
  environment, risk level, Access Grant summary, recent activity,
  HumanApproval summary, Evidence Bundle availability, inventory/access
  details, and compact technical policy/rule references.
- Read-only frontend Runtime Gateway overview and activity pages.
- Frontend Human Approvals page backed by `GET /human-approvals`, with review
  actions shown only for pending approvals.
- Read-only frontend Evidence Bundle page backed by
  `GET /agents/{agent_id}/evidence-bundle`.

## V0 Governance Flow

The V0 demo exercises this sequence:

1. Create an Agent through `POST /agents`.
2. Insert an active Policy and PolicyRule requiring human review for
   `metadata.tool_name = "send_email"`.
3. Ingest a `tool_call_requested` TraceEvent through `POST /telemetry/events`.
4. Verify an AgentRunRecord and TraceEventRecord are created.
5. Verify a PolicyDecision is created with `require_human_review`.
6. Verify a pending HumanApproval is created and linked to the PolicyDecision.
7. Verify a `human_approval_requested` AuditLog is created.
8. Export `GET /agents/{agent_id}/evidence-bundle`.
9. Verify the Evidence Bundle links the full chain by ID.

Run only the V0 demo:

```bash
cd apps/api
uv run pytest tests/test_v0_governance_flow.py
```

## Main API Endpoints

Agent Registry:

- `POST /agents`
- `GET /agents`
- `GET /agents/{agent_id}`
- `GET /agents/{agent_id}/access-grants`
- `GET /agents/{agent_id}/activity`
- `GET /agents/{agent_id}/governance-profile`
- `PATCH /agents/{agent_id}`
- `GET /agents/{agent_id}/evidence-bundle`

Agent activity returns a read-only timeline sorted newest first. It is intended
for product navigation; Evidence Bundle JSON export remains the canonical review
export.
Agent-scoped access grants return declared Capability, Source, ModelAsset,
external, or other target grants newest first and can be filtered by `status`
and `target_type`.
Agent Governance Profile returns a compact read model for one Agent, including
recent activity, HumanApproval counts, Access Grants with safe inventory target
references, policy/rule ID references, and whether the Evidence Bundle JSON
export is available to the current actor. It does not replace or embed the full
Evidence Bundle.

Telemetry:

- `POST /telemetry/events`

Runtime Gateway:

- `GET /runtime/tool-calls/activity`
- `POST /runtime/tool-calls/decision`
- `POST /runtime/tool-calls/resume`

Runtime activity returns a read-only tool-call activity list sorted newest first.
It is built from persisted Runtime Gateway trace events, linked policy decisions,
and linked human approvals. Fields that are not persisted for a record are
returned as `null` instead of being inferred from fake data.
Older or shared `tool_call_requested` records without a persisted runtime mode
therefore return `mode = null`.

Inventory:

- `POST /capabilities`
- `GET /capabilities`
- `GET /capabilities/{capability_id}`
- `PATCH /capabilities/{capability_id}`
- `POST /sources`
- `GET /sources`
- `GET /sources/{source_id}`
- `PATCH /sources/{source_id}`
- `POST /models`
- `GET /models`
- `GET /models/{model_id}`
- `PATCH /models/{model_id}`
- `POST /access-grants`
- `GET /access-grants`
- `GET /access-grants/{access_grant_id}`
- `PATCH /access-grants/{access_grant_id}`

Capability, Source, and Model inventory records are governance inventory only.
They can be referenced by Access Grants, but do not ingest source contents, do
not call model provider APIs, and do not change policy evaluation.
Access Grants are declared governance records for what an Agent is allowed to
use. For now they are the association layer between Agents and governed
inventory targets; separate AgentCapability, AgentSource, or AgentModel join
tables would duplicate that meaning. They do not enforce runtime access yet and
are not a full IAM system.

Policy Management:

- `POST /policies`
- `GET /policies`
- `GET /policies/{policy_id}`
- `GET /policies/{policy_id}/rules`
- `PATCH /policies/{policy_id}`
- `POST /policy-rules`
- `GET /policy-rules`
- `GET /policy-rules/{rule_id}`
- `GET /policy-rules/{rule_id}/check-steps`
- `PATCH /policy-rules/{rule_id}`
- `POST /policy-check-steps`
- `GET /policy-check-steps`
- `GET /policy-check-steps/{step_id}`
- `PATCH /policy-check-steps/{step_id}`

Policy management records the lifecycle of policies with `draft`, `active`,
`disabled`, and `archived` statuses. PolicyRule management accepts only the
deterministic JSON condition shape already consumed by the evaluator. It does
not add a generic policy language or change runtime evaluation behavior.
PolicyCheckStep records declare metadata-only evidence expectations for
PolicyRules with constrained check types and target selectors. Runtime Gateway
executes active authored steps only when
`AGCP_RUNTIME_METADATA_PRE_CHECKS_ENABLED=true`; CheckResults are evidence
inputs and do not directly change PolicyDecision, `proceed`, or PolicyRule
matching behavior.

Human Approvals:

- `POST /human-approvals`
- `GET /human-approvals`
- `GET /human-approvals/{approval_id}`
- `GET /agents/{agent_id}/human-approvals`
- `POST /human-approvals/{approval_id}/approve`
- `POST /human-approvals/{approval_id}/reject`
- `POST /human-approvals/{approval_id}/cancel`

OpenAPI docs are available from the running backend at `/docs`.

## Run And Test

Install backend dependencies:

```bash
cd apps/api
uv sync
```

Run the API locally:

```bash
uv run uvicorn --app-dir src agent_governance_api.main:app --reload
```

The backend uses a `src` layout, so `--app-dir src` is required when running
from `apps/api`. After startup, `GET /health` should return:

```json
{"status":"ok","service":"Agent Governance Control Plane API","environment":"development"}
```

Run backend tests:

```bash
uv run pytest
```

Run lint and format checks:

```bash
uv run ruff check .
uv run ruff format --check .
```

Run the web dashboard shell:

```bash
cd apps/web
npm install
npm run dev
```

Run web checks:

```bash
npm run smoke
npm run typecheck
npm run build
```

Run database migrations against PostgreSQL:

```bash
uv run alembic upgrade head
```

The backend CI workflow runs `uv sync`, `uv run pytest`,
`uv run ruff check .`, `uv run ruff format --check .`, and
`uv run alembic upgrade head` from `apps/api`.

## Initial Technical Decisions

- Python 3.11
- uv
- FastAPI
- Pydantic v2
- SQLAlchemy 2.x
- Alembic
- PostgreSQL
- pytest
- ruff
- Modular monolith
- Internal Python packages/modules, not independently deployed services

## Intentionally Not Implemented Yet

- Runtime enforcement from Access Grants.
- Dedicated Permission domain model.
- Full authentication and broad RBAC beyond the implemented local checks.
- User login, OIDC, SAML, or JWT auth.
- Team membership or organization-unit ownership resolution.
- DB-backed service actor registry auth is available behind a disabled feature
  flag, with internal hashed-key and scope/rule config seeding helpers. Admin
  workflows and public registry APIs are not complete.
- API key rotation implementation and persistent API key management.
- Owner-based service actor restrictions.
- Team or organization-unit based Evidence Bundle access checks.
- Safe audit events for denied service actor scope checks.
- Full enterprise-auth-backed frontend workflows beyond the current local API
  views and HumanApproval review actions.
- Frontend login or role-aware UI.
- Agent edit forms.
- Broad filtering, search, or pagination for Agent and Runtime activity views.
- Evidence Bundle PDF/download/signature actions in the UI.
- Human approval notifications.
- Production SDKs or framework adapters.
- Docker Compose or production deployment.
- Policy versioning and Runtime Gateway telemetry mode on the runtime decision
  endpoint.
- Pre-check failure behavior enforcement, scanner execution, or CheckResult-
  driven policy decisions.
- Retention policies.
- Signed or PDF evidence bundles.
- SIEM/GRC integrations.
- Legal compliance certification claims.

## Next Roadmap Items

Near-term recommended work:

1. Add Policy management UI for the existing Policy, PolicyRule, and
   PolicyCheckStep APIs.
2. Use Access Grants as optional policy context without replacing
   PolicyDecision records.
3. Add focused AccessGrant and inventory workflows only where they support
   review, approval, or evidence collection.
4. Implement Permission domain model only if AccessGrant target semantics prove
   insufficient.
5. Add frontend auth and role-aware UI.
6. Add CORS/proxy setup guidance if needed for local frontend/backend use.
7. Add OpenAPI examples for `GET /human-approvals` if missing.
8. Design team and organization-unit ownership resolution for Evidence Bundle
   export.
9. Add owner-based service actor scopes design.
10. Add safe audit events for denied service actor scope checks.
11. Implement service actor registry admin management workflow.
12. Implement service actor API key rotation and admin workflows after registry
    import/management behavior is designed.
13. Add deeper separation-of-duties checks for HumanApproval review.
15. Add broad filtering and pagination for Runtime and Agent activity only
    after the backend read models need it.

## Repository Map

```text
.
|-- AGENTS.md
|-- README.md
|-- apps/
|   |-- api/
|   `-- web/
|-- docs/
|   |-- PRODUCT_CHARTER.md
|   |-- DOMAIN_MODEL.md
|   |-- ROADMAP.md
|   |-- TASKS.md
|   `-- V0_GOVERNANCE_FLOW.md
|-- packages/
|   |-- audit/
|   |-- domain/
|   |-- policy/
|   `-- telemetry/
`-- scripts/
```

## Definition Of Done

A task is not done unless:

- the requested scope is implemented;
- no out-of-scope feature was added;
- tests were added or updated;
- relevant checks were run successfully;
- the diff is small enough to review;
- the final report lists what was done, what was not done, and remaining risks.

If implementation is complete but checks cannot run because local tooling,
services, or credentials are missing, the task is "implementation complete,
validation pending", not done.
