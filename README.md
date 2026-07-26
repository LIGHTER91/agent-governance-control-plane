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

## Current Maturity

AGCP is a **local V1 / advanced product prototype**. It is no longer a
backend-only V0 milestone, but it is not production-ready or enterprise-ready.
The implemented governance flow includes:

```text
Agent Registry and declared access
-> Policy Studio draft and reviewed PolicyVersion activation
-> Runtime Gateway or telemetry evaluation
-> PolicyDecision and metadata-only CheckResults
-> HumanApproval when decision = require_human_review
-> AuditLog and Evidence Bundle JSON export
```

See [V0_GOVERNANCE_FLOW.md](docs/V0_GOVERNANCE_FLOW.md) for the original
executable backend slice and
[PROJECT_AUDIT_CURRENT_STATE.md](docs/PROJECT_AUDIT_CURRENT_STATE.md) for the
current assessment.

Runtime Gateway, telemetry, inventory APIs, Access Grants, auditable Policy and
PolicyRule management, active PolicyVersion evaluation with unversioned
fallback, Agent Governance Profile, Human Approval Studio, Runtime Decisions,
Evidence & Audit, Access & Data, Overview, Integration Hub, and the
metadata-only pre-check demo now exist. Service actor API key authentication
uses config by default and can use an optional DB-backed registry behind an
explicit feature flag. Both paths support endpoint scopes and fine-grained
Agent/environment/runtime/tool restrictions.

AGCP does not execute tools. Runtime enforcement depends on wrappers or
adapters calling AGCP and honoring `proceed`. Minimal RBAC exists for selected
review, activity, and Evidence Bundle actions.
Full user authentication, OIDC/SAML/JWT, team membership resolution, enterprise
auth-backed frontend workflows, notifications, production deployment, mutating
service actor admin workflows, API key rotation implementation, and adapter
packages for enterprise integrations are intentionally not implemented yet.

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
  metadata-only helpers and persist CheckResults as evidence. CheckResults do
  not enforce anything automatically, but active PolicyRules can explicitly
  match their safe outcome summaries.
- Simple policy evaluator supporting explicit request, resolved inventory, and
  safe CheckResult outcome matching fields.
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
  `development/dev-placeholder` actor and optional local-only
  `AGCP_DEV_ACTOR_*` overrides for dev review workflows.
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
- Service Actor admin read APIs for listing service actors, key status
  metadata, scopes, and fine-grained scope rules when
  `AGCP_SERVICE_ACTOR_REGISTRY_ENABLED=true`.
- Next.js dashboard shell.
- Backend-connected frontend Agent list page backed by `GET /agents`, with a
  dedicated registration action.
- Frontend Agent registration and governance editing workflow at `/agents/new`
  and `/agents/{agent_id}/edit`, covering Identity, Ownership, Runtime & Risk,
  Governed Access, and Review. It uses real inventory endpoints and creates
  selected Access Grants sequentially as `pending_review`, with explicit
  partial-completion retry.
- Read-oriented frontend Agent detail page backed by
  `GET /agents/{agent_id}/governance-profile`,
  `GET /agents/{agent_id}/activity`,
  `GET /agents/{agent_id}/human-approvals`, and optional manual Evidence
  Bundle access.
- Agent Governance Profile UI showing Agent identity, owner, status,
  environment, risk level, Access Grant summary, recent activity,
  HumanApproval summary, Evidence Bundle availability, inventory/access
  details, and compact technical policy/rule references.
- Frontend Policy Studio IDE for Policy and PolicyRule authoring, including
  backend-backed Policy folders, repository navigation, static templates,
  synchronized Blocks and Code DSL modes, deterministic local validation,
  guided inventory-backed PolicyCheckStep authoring, explicit `check_*` outcome
  conditions, complete PolicyVersion check snapshots, PolicyVersion-backed
  Save draft, Submit for review, explicit reviewed activation, rollback draft,
  archive, guarded draft delete, no Publish action, and no fake production
  simulation.
- Workflow-first frontend Runtime Decisions page backed by runtime activity data,
  showing request, context, policy evaluation, metadata checks, human review,
  and evidence milestones without fake production simulation.
- Human Approval Studio backed by Runtime HumanApproval and
  PolicyVersionReviewRequest APIs, with policy review assignment,
  approve/reject, diff, and explicit activation while preserving the approved
  Review Inbox layout.
- Workflow-first Evidence & Audit explorer backed by
  `GET /agents/{agent_id}/evidence-bundle`, with safe evidence-chain sections
  and bounded JSON download.
- Workflow-first Access & Data page for Access Grants, Sources,
  DataUsageProfiles, Models, Capabilities, metadata-check readiness, and
  explicit grant lifecycle transitions.
- Connected Overview page for the know/control/prove product narrative using
  real backend summaries and honest empty/error states.
- Frontend Integration Hub page for Custom Runtime Gateway API, LangGraph,
  n8n, Dataiku, MCP, and generic webhook/API connection guidance, with optional
  read-only Service Actor registry summary metadata.

## Historical V0 Governance Flow

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

Service Actors:

- `GET /service-actors`
- `GET /service-actors/{service_actor_id}`
- `GET /service-actors/{service_actor_id}/api-keys`
- `GET /service-actors/{service_actor_id}/scopes`
- `GET /service-actors/{service_actor_id}/scope-rules`

Service Actor registry admin read APIs are available only when
`AGCP_SERVICE_ACTOR_REGISTRY_ENABLED=true`. API key responses include safe key
metadata such as key ID and status, not plaintext key material.

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

- `POST /policy-folders`
- `GET /policy-folders`
- `PATCH /policy-folders/{folder_id}`
- `DELETE /policy-folders/{folder_id}`
- `POST /policies`
- `GET /policies`
- `GET /policies/{policy_id}`
- `GET /policies/{policy_id}/rules`
- `PATCH /policies/{policy_id}`
- `POST /policies/{policy_id}/archive`
- `DELETE /policies/{policy_id}`
- `POST /policies/{policy_id}/versions/draft`
- `GET /policies/{policy_id}/versions`
- `PATCH /policy-versions/{version_id}/draft`
- `POST /policy-versions/{policy_version_id}/review-requests`
- `GET /policy-versions/{policy_version_id}/review-state`
- `GET /policy-version-review-requests`
- `GET /policy-version-review-requests/{review_request_id}/diff`
- `POST /policy-version-review-requests/{review_request_id}/assign`
- `POST /policy-version-review-requests/{review_request_id}/approve`
- `POST /policy-version-review-requests/{review_request_id}/reject`
- `POST /policy-version-review-requests/{review_request_id}/activate`
- `POST /policy-versions/{version_id}/rollback-draft`
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
Policy Studio persists draft PolicyVersion snapshots. Dedicated review requests
support assignment, approve/reject, deterministic diff, and explicit
activation; approval alone has no runtime effect. The backend enforces one
active version per Policy, supports review-gated rollback drafts, and blocks
legacy live edits for active-versioned Policies.
PolicyCheckStep records declare metadata-only evidence expectations for
PolicyRules with constrained check types and target selectors. Runtime Gateway
executes active authored steps only when
`AGCP_RUNTIME_METADATA_PRE_CHECKS_ENABLED=true`; CheckResults are evidence
inputs and do not directly change PolicyDecision or `proceed`. They may affect
the final decision only when a PolicyRule explicitly matches safe CheckResult
fields such as `check_type` and `check_outcome`.

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

### One-command Local Dev Stack

For normal local product testing, Docker Compose can start PostgreSQL, apply
Alembic migrations, run the FastAPI backend, and run the Next.js frontend:

```bash
docker compose -f compose.dev.yml up --build
```

On Windows PowerShell, the helper script runs the same command from the
repository root:

```powershell
.\scripts\dev-up.ps1
```

Open:

```text
Frontend: http://localhost:3000
Backend:  http://localhost:8000
API docs: http://localhost:8000/docs
Health:   http://localhost:8000/health
```

The Compose stack is local development only. It uses PostgreSQL 16 with local
credentials from `.env.compose.example`, mounts backend and frontend source
code for hot reload, and keeps dependency caches in Docker named volumes. It
does not seed fake data by default; run the demo seed manually when you want
sample records.
For local review workflow testing, the Compose API service defaults to:

```text
AGCP_DEV_ACTOR_ID=local-admin
AGCP_DEV_ACTOR_ROLES=platform_admin,reviewer,auditor
AGCP_DEV_ACTOR_DISPLAY_NAME=Local Admin
```

These values affect only the local development actor returned by `GET /me`.
They are not enterprise auth and do not weaken backend RBAC in production. To
test restricted UI states, set `AGCP_DEV_ACTOR_ROLES=` in a local `.env` file
before starting the Compose stack.

Stop the stack:

```bash
docker compose -f compose.dev.yml down
```

On Windows PowerShell:

```powershell
.\scripts\dev-down.ps1
```

Reset the local Compose database volume only when you intentionally want to
delete local development data:

```bash
docker compose -f compose.dev.yml down -v
```

Optional safe demo seed, after the stack is running:

```bash
docker compose -f compose.dev.yml exec api uv run python scripts/seed_full_stack_demo.py --apply
```

Print the safe metadata pre-check Runtime Gateway payload without applying seed
data:

```bash
docker compose -f compose.dev.yml exec api uv run python scripts/seed_full_stack_demo.py --print-runtime-payload
```

One-command metadata-only pre-check demo, after the stack is running:

```powershell
.\scripts\dev-demo.ps1
```

The demo script checks the Docker Compose services, verifies API health,
confirms `GET /me` returns the local `Local Admin` actor with
`platform_admin`, `reviewer`, and `auditor`, applies migrations, runs the
deterministic full-stack seed, calls the seeded Runtime Gateway scenario, and
prints the real decision, `policy_version_id`, CheckResult count, and
HumanApproval ID. The Compose dev API enables
`AGCP_RUNTIME_METADATA_PRE_CHECKS_ENABLED=true` by default for this local demo.
If your stack was already running before that setting was added, restart it
with `.\scripts\dev-down.ps1` and `.\scripts\dev-up.ps1`.
The script loads the Runtime Gateway payload through
`scripts/seed_full_stack_demo.py --print-runtime-payload`, which uses the same
`src` import path bootstrap as the seed command and prints JSON only.

Validate the entire stack against an isolated clean PostgreSQL volume:

```powershell
.\scripts\validate-clean.ps1
```

The validation script uses Compose project `agcp-clean-validation` and
dedicated default host ports `55432`, `58000`, and `53000`. It checks port
availability before starting, applies all migrations to an empty database,
verifies `/health` and `/me`, runs the deterministic seed and metadata
pre-check scenario, requires `decision=require_human_review`,
`proceed=false`, at least one linked CheckResult, and a HumanApproval
identifier, runs frontend smoke, and removes only its isolated containers and
volumes in a `finally` block. Use `-KeepRunning` only when intentional browser
inspection is needed. The script never runs `down -v` against the normal AGCP
development project.

Troubleshooting the Compose stack:

- Docker Desktop not running: start Docker Desktop, then rerun
  `docker compose -f compose.dev.yml up --build`.
- Port already in use: stop the process using `3000`, `8000`, or `5432`, or
  set `POSTGRES_PORT` in a local `.env` file for the database host port.
- `.next` lock on Windows: stop the stack with `.\scripts\dev-down.ps1`; if the
  lock persists, run `docker compose -f compose.dev.yml down -v` to remove the
  named `.next` development volume.
- Backend migration errors: inspect the `api` and `db` logs with
  `docker compose -f compose.dev.yml logs api db`, fix the migration issue, and
  rerun the stack.
- Empty UI: the stack intentionally does not seed records by default. Run the
  seed command above, then refresh `/agents`.
- Frontend cannot fetch the backend: confirm
  `NEXT_PUBLIC_AGCP_API_BASE_URL=http://localhost:8000` and open
  `http://localhost:8000/health` from the host browser.

### Manual Local Full-Stack Demo

Run a local full-stack demo with real backend data:

```powershell
# 1. From the repository root, start local PostgreSQL 16.
docker compose -f compose.dev.yml up -d db

# 2. Configure the API to use the local Docker database.
cd apps/api
$env:AGCP_DATABASE_URL = "postgresql+psycopg://postgres:postgres@127.0.0.1:5432/agent_governance_control_plane?connect_timeout=5"

# 3. Apply migrations.
uv run alembic upgrade head

# 4. Seed safe local demo records.
uv run python scripts/seed_full_stack_demo.py --apply

# Optional: print the safe Runtime Gateway payload JSON without writing data.
uv run python scripts/seed_full_stack_demo.py --print-runtime-payload

# 5. Start the backend and leave it running in this terminal.
uv run uvicorn --app-dir src agent_governance_api.main:app --reload

# 6. In a second terminal from the repository root, start the frontend.
cd apps/web
npm install
npm run dev

# 7. Open the real backend-backed Agent list.
# http://localhost:3000/agents
```

On bash-like shells, use `export AGCP_DATABASE_URL="..."` instead of the
PowerShell `$env:` assignment. The Compose password is a local development
credential only and is not production configuration.

The seed command creates local-only demo records for one Agent, one active
Policy and PolicyRule, one runtime TraceEvent, one PolicyDecision, one pending
HumanApproval, and related AuditLogs. It also creates a local metadata-only
runtime pre-check scenario with a production demo Agent, confidential Source
metadata, an external ModelAsset, active AccessGrants, authored
PolicyCheckSteps, and an active PolicyVersion snapshot. It does not create
secrets, raw prompts, source contents, credentials, or personal data. The
frontend pages keep calling the backend; no demo data is hardcoded in the web
app.

Optional metadata-only Runtime Gateway validation:

```powershell
# Start the backend with the opt-in flag before calling the Runtime Gateway.
$env:AGCP_RUNTIME_METADATA_PRE_CHECKS_ENABLED = "true"
uv run uvicorn --app-dir src agent_governance_api.main:app --reload

# In another terminal, call the seeded scenario.
curl.exe -X POST http://localhost:8000/runtime/tool-calls/decision `
  -H "Content-Type: application/json" `
  -d '{ "request_id": "metadata-precheck-demo-001", "agent_id": "00000000-0000-4000-8000-000000001101", "run_id": "00000000-0000-4000-8000-000000001a01", "correlation_id": "metadata-precheck-demo", "tool_name": "vectorize_source", "action_summary": "Vectorize a confidential demo source with an external embedding model.", "metadata": { "demo": "metadata_pre_check" }, "mode": "simulation", "action_type": "vectorize", "capability_id": "00000000-0000-4000-8000-000000001201", "source_ids": ["00000000-0000-4000-8000-000000001301"], "model_id": "00000000-0000-4000-8000-000000001401", "purpose": "semantic_search_indexing", "data_classification": "confidential", "contains_personal_data": false, "contains_sensitive_data": true }'
```

Expected result: `require_human_review`, `proceed=false`, a pending
HumanApproval, PolicyDecision linked to the active PolicyVersion, and safe
metadata-only CheckResult summaries visible from the Review Inbox and Evidence
Bundle. The checks read AGCP inventory metadata only; they do not scan or store
source contents.

For the Docker Compose stack, prefer the one-command wrapper from the repository
root:

```powershell
.\scripts\dev-demo.ps1
```

Troubleshooting:

- `ModuleNotFoundError: agent_governance_api`: run uvicorn from `apps/api` with
  `uv run uvicorn --app-dir src agent_governance_api.main:app --reload`; for
  the metadata demo payload, use
  `uv run python scripts/seed_full_stack_demo.py --print-runtime-payload`
  instead of inline `python -c` imports.
- Docker not running: start Docker Desktop, then rerun
  `docker compose -f compose.dev.yml up -d db`.
- Port `5432` already in use: stop the existing local PostgreSQL process, or
  set `POSTGRES_PORT` for `compose.dev.yml` and update
  `AGCP_DATABASE_URL` to match.
- Alembic connection timeout: check
  `docker compose -f compose.dev.yml ps`, confirm the database is
  healthy, and verify `AGCP_DATABASE_URL` includes `postgres:postgres`.
- CORS or browser proxy errors: keep the web app on `http://localhost:3000` or
  add its origin to `AGCP_CORS_ALLOWED_ORIGINS`.
- Empty Agent, Activity, HumanApproval, or Evidence pages: run
  `uv run python scripts/seed_full_stack_demo.py --apply` against the same DB
  used by the backend, then refresh `/agents`.

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
  read APIs exist, but mutating admin workflows are not complete.
- API key rotation implementation and persistent API key management.
- Owner-based service actor restrictions.
- Team or organization-unit based Evidence Bundle access checks.
- Safe audit events for denied service actor scope checks.
- Full enterprise-auth-backed frontend workflows beyond the current local API
  views and HumanApproval review actions.
- Frontend login or broad role-management UI.
- Agent deletion, enterprise owner directory resolution, and Access Grant
  approval inside the Agent workflow.
- Broad filtering, search, or pagination for Agent and Runtime activity views.
- Evidence Bundle PDF/signature/archive packaging.
- Human approval notifications.
- Production SDKs or framework adapters.
- Runtime Integration Hub adapter packages or workflow nodes for LangGraph,
  n8n, Dataiku, MCP, or generic webhook integrations.
- Production deployment.
- Automatic PolicyCheckStep `failure_behavior` enforcement, scanner execution,
  or hidden CheckResult-driven decisions. CheckResults affect decisions only
  when an active PolicyRule explicitly matches safe `check_*` fields.
- Retention policies.
- Signed or PDF evidence bundles.
- SIEM/GRC integrations.
- Legal compliance certification claims.

## Next Roadmap Items

Near-term implementation order:

1. One production-quality Python/LangGraph Runtime Gateway adapter with
   mandatory `proceed` enforcement, idempotency, timeout/failure behavior,
   HumanApproval resume, fake-tool tests, and documentation.
2. Enterprise identity/RBAC and separation-of-duties design for the next
   product maturity stage.

Before a public demonstration, run `scripts/validate-clean.ps1` with Docker
available and add a clean browser E2E governance flow. Beta preparation then
requires real identity/RBAC and separation of duties, Service Actor
administration and rotation, a historical PolicyDecision backfill decision,
and evidence package/retention work. See `docs/ROADMAP.md` for the focused
P0-P3 roadmap.

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
