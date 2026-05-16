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
plane. Authentication, RBAC, frontend workflows, notifications, runtime
blocking, production deployment, and enterprise integrations are intentionally
not implemented yet.

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
- JSON Evidence Bundle export for one agent.
- Evidence chain coverage across TraceEventRecord, PolicyDecision,
  HumanApproval, and related AuditLog.
- Central metadata safety filtering for telemetry, audit, and evidence export.
- OpenAPI examples for core backend endpoints.

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
- `PATCH /agents/{agent_id}`
- `GET /agents/{agent_id}/evidence-bundle`

Telemetry:

- `POST /telemetry/events`

Human Approvals:

- `POST /human-approvals`
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
uv run uvicorn agent_governance_api.main:app --reload
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
- Full authentication and RBAC.
- Frontend or dashboard UI.
- Human approval notifications.
- Runtime gateway or runtime blocking.
- SDKs or framework adapters.
- Docker Compose or production deployment.
- Policy versioning and simulation mode.
- Retention policies.
- Signed or PDF evidence bundles.
- SIEM/GRC integrations.
- Legal compliance certification claims.

## Next Roadmap Items

Near-term recommended work:

1. Implement Tool, Data Source, Model, and Permission domain models.
2. Add Policy and PolicyRule CRUD APIs with audit logging.
3. Add a minimal dashboard shell and agent list page.
4. Design the Runtime Gateway spike without adding enforcement prematurely.
5. Design the first framework integration spike, likely LangGraph.
6. Add authentication/RBAC only after the core domain workflows are stable.

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
