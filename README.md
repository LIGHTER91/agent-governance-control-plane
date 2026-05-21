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
plane. Runtime Gateway foundations and minimal config-based service actor API
key authentication now exist, including endpoint scopes, config-based
fine-grained scope rules, and an explicit service-auth-required mode for runtime
and telemetry endpoints. Minimal RBAC exists for HumanApproval review actions
and Evidence Bundle export. Full user authentication, OIDC/SAML, team
membership resolution, full frontend workflows, notifications, production
deployment, API key rotation, and enterprise integrations are intentionally not
implemented yet.

## Implemented Capabilities

- FastAPI backend skeleton with health endpoint.
- PostgreSQL-targeted SQLAlchemy 2.x models and Alembic migrations.
- Agent Registry API.
- Agent ownership model using `owner_type`, `owner_id`, `owner_name`, and
  optional contact email.
- Immutable application-level AuditLog foundation.
- Deterministic Policy, PolicyRule, and PolicyDecision domain models.
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
- JSON Evidence Bundle export for one agent.
- Minimal Evidence Bundle export RBAC for `auditor`, `platform_admin`, and
  direct user owners.
- Service actors cannot export Evidence Bundles by default.
- Evidence chain coverage across TraceEventRecord, PolicyDecision,
  HumanApproval, and related AuditLog.
- Central metadata safety filtering for telemetry, audit, and evidence export.
- OpenAPI examples for core backend endpoints.
- Runtime Gateway simulation endpoint for governed tool-call decisions.
- Runtime Gateway enforcement mode behind explicit
  `AGCP_RUNTIME_ENFORCEMENT_ENABLED=true`.
- Runtime resume endpoint for checking whether a previously blocked action may
  proceed after HumanApproval.
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
- Next.js dashboard shell.
- Read-only frontend Agent list page backed by `GET /agents`.
- Read-only frontend Agent detail page backed by `GET /agents/{agent_id}`,
  `GET /agents/{agent_id}/human-approvals`, and optional Evidence Bundle
  access.
- Read-only frontend Runtime Gateway overview page.
- Read-only frontend Human Approvals page backed by `GET /human-approvals`.
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
- `GET /agents/{agent_id}/activity`
- `PATCH /agents/{agent_id}`
- `GET /agents/{agent_id}/evidence-bundle`

Agent activity returns a read-only timeline sorted newest first. It is intended
for product navigation; Evidence Bundle JSON export remains the canonical review
export.

Telemetry:

- `POST /telemetry/events`

Runtime Gateway:

- `POST /runtime/tool-calls/decision`
- `POST /runtime/tool-calls/resume`

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

- Policy CRUD API.
- Tool, Data Source, Model, and Permission domain models.
- Full authentication and broad RBAC beyond the implemented local checks.
- User login, OIDC, SAML, or JWT auth.
- Team membership or organization-unit ownership resolution.
- DB-backed service actor or API key registry.
- API key rotation and persistent API key management.
- Owner-based service actor restrictions.
- Team or organization-unit based Evidence Bundle access checks.
- Safe audit events for denied service actor scope checks.
- Full frontend workflows beyond the dashboard shell, read-only Agent list,
  read-only Agent detail, read-only Runtime Gateway overview, read-only Human
  Approvals list, and read-only Evidence Bundle viewer.
- Frontend login or role-aware UI.
- Agent edit forms.
- Dedicated Agent activity or runtime/policy timeline endpoints and frontend
  sections.
- HumanApproval approve, reject, and cancel buttons in the UI.
- Evidence Bundle PDF/download/signature actions in the UI.
- Human approval notifications.
- Production SDKs or framework adapters.
- Docker Compose or production deployment.
- Policy versioning and Runtime Gateway telemetry mode on the runtime decision
  endpoint.
- Retention policies.
- Signed or PDF evidence bundles.
- SIEM/GRC integrations.
- Legal compliance certification claims.

## Next Roadmap Items

Near-term recommended work:

1. Add Agent activity/timeline backend endpoint.
2. Add Agent activity/timeline frontend section.
3. Add HumanApproval review actions UI later.
4. Add Runtime decisions/activity page.
5. Add Policy CRUD UI after backend Policy CRUD exists.
6. Add frontend auth and role-aware UI later.
7. Add CORS/proxy setup guidance if needed for local frontend/backend use.
8. Add OpenAPI examples for `GET /human-approvals` if missing.
9. Add broader owner-based access checks.
10. Add API key rotation design.
11. Add owner-based service actor scopes design.
12. Add safe audit events for denied service actor scope checks.
13. Add DB-backed service actor registry design.
14. Implement Tool, Data Source, Model, and Permission domain models.
15. Add Policy and PolicyRule CRUD APIs with audit logging.

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
