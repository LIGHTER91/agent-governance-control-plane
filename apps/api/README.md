# Agent Governance API

Minimal FastAPI backend for the Agent Governance Control Plane.

## Local commands

Install dependencies:

```bash
uv sync
```

Run the API:

```bash
uv run uvicorn --app-dir src agent_governance_api.main:app --reload
```

The API uses a `src` layout, so `--app-dir src` is required when running from
`apps/api`. After startup, `GET /health` should return:

```json
{"status":"ok","service":"Agent Governance Control Plane API","environment":"development"}
```

Run tests:

```bash
uv run pytest
```

Run lint and format checks:

```bash
uv run ruff check .
uv run ruff format --check .
```

## API endpoints

OpenAPI docs are available at `/docs` and include V0 governance flow examples
for the core backend endpoints.

Agent Registry:

- `POST /agents` creates an agent and appends an internal `agent_created` audit event.
- `GET /agents` lists agents.
- `GET /agents/{agent_id}` returns one agent.
- `GET /agents/{agent_id}/activity` returns a read-only activity timeline sorted newest first for product navigation.
- `GET /agents/{agent_id}/evidence-bundle` exports a JSON evidence bundle for one agent, including related audit logs, runs, trace events, policy decisions, and human approvals.
- `GET /agents/{agent_id}/human-approvals` lists human approvals for one agent.
- `PATCH /agents/{agent_id}` updates an agent and appends an internal `agent_updated` or `agent_status_changed` audit event.

Agent mutations use the development actor placeholder until authentication exists:

- `actor_type = "development"`
- `actor_id = "dev-placeholder"`

Capability Inventory:

- `POST /capabilities` creates a governed capability inventory record and
  appends `capability_created`.
- `GET /capabilities` lists capability records.
- `GET /capabilities/{capability_id}` returns one capability.
- `PATCH /capabilities/{capability_id}` updates a capability and appends
  `capability_updated` or `capability_status_changed`.
- Capabilities can represent tools, APIs, integrations, workflow actions, or
  other governed operations.
- Capability metadata rejects unsafe key names such as `api_key`, `token`,
  `password`, `secret`, and `authorization`.
- Capabilities are not linked to Agents yet.

Source Inventory:

- `POST /sources` creates a governed source inventory record and appends
  `source_created`.
- `GET /sources` lists source records.
- `GET /sources/{source_id}` returns one source.
- `PATCH /sources/{source_id}` updates a source and appends `source_updated`
  or `source_status_changed`.
- Sources can represent knowledge bases, databases, document stores, APIs,
  buckets, filesystems, or other governed data or knowledge sources.
- Source metadata rejects unsafe key names such as `api_key`, `token`,
  `password`, `secret`, and `authorization`.
- Source inventory records do not ingest or store source contents, and Sources
  are not linked to Agents yet.

Human Approvals:

- `POST /human-approvals` creates a pending human approval for an existing agent and appends `human_approval_requested`.
- `GET /human-approvals/{approval_id}` returns one human approval.
- `POST /human-approvals/{approval_id}/approve` approves a pending approval and appends `human_approval_approved`.
- `POST /human-approvals/{approval_id}/reject` rejects a pending approval and appends `human_approval_rejected`.
- `POST /human-approvals/{approval_id}/cancel` cancels a pending approval and appends `human_approval_cancelled`.
- Human approval transitions are explicit; there is no generic update or delete endpoint.

Telemetry:

- `POST /telemetry/events` ingests a validated trace event for an existing agent.
- If no agent run exists for the submitted `(agent_id, run_id)`, the API creates an internal `AgentRunRecord` and attaches the event to it.
- If the matching agent run already exists, the API attaches the event to that run.
- Telemetry ingestion is idempotent by `(agent_id, run_id, external_event_id)`. If `external_event_id` is omitted, the submitted trace event `id` is used as the external event id.
- The same `external_event_id` may be used for a different run because the uniqueness rule is scoped to `(agent_id, run_id)`.
- `tool_call_requested` events must include `metadata.tool_name`; these events are evaluated against active persisted policies and return the resulting policy decision. A `deny` decision is recorded but does not block event storage.
- Policy decisions created from telemetry include an explicit `trace_event_id` link back to the triggering trace event.
- If a telemetry-triggered policy decision is `require_human_review`, the API creates one pending human approval, links it to the policy decision, appends `human_approval_requested`, and returns `human_approval_id`.
- Other telemetry event types are stored without creating a policy decision.
- Telemetry metadata rejects unsafe key names such as `api_key`, `token`, `password`, `secret`, and `authorization`.

Runtime Gateway:

- `GET /runtime/tool-calls/activity` returns read-only Runtime Gateway tool-call activity sorted newest first from persisted trace, policy decision, and human approval links.
- Older or shared `tool_call_requested` records without a persisted runtime mode return `mode = null`.
- `POST /runtime/tool-calls/decision` accepts governed tool-call decision requests.
- `mode = "simulation"` is enabled by default and records the decision/evidence chain without claiming action blocking.
- `mode = "enforcement"` is disabled by default. Set `AGCP_RUNTIME_ENFORCEMENT_ENABLED=true` to accept enforcement requests.
- Enforcement mode reuses the simulation evidence workflow and returns `proceed = true` only for `allow`. `deny`, `require_human_review`, and `not_applicable` return `proceed = false`.
- The gateway never executes tools. The calling wrapper or adapter must enforce the returned `proceed` value.
- `mode = "telemetry"` is not implemented on the runtime endpoint; use `POST /telemetry/events` for telemetry ingestion.

Service actor API keys:

- Runtime and telemetry integration endpoints accept `X-AGCP-API-Key`.
- Configure hashed keys with `AGCP_SERVICE_ACTOR_API_KEYS`, for example `service:demo=sha256:<digest>`.
- Configure endpoint scopes with `AGCP_SERVICE_ACTOR_SCOPES`, for example `service:demo=telemetry:write,runtime:decision,runtime:resume`.
- Configure minimal fine-grained service actor rules with
  `AGCP_SERVICE_ACTOR_SCOPE_RULES`, for example
  `{"service:demo":{"agent_ids":["*"],"environments":["development"],"runtime_modes":["simulation"],"tool_names":["send_email"]}}`.
- Fine-grained rules currently cover `agent_ids`, `environments`,
  `runtime_modes`, and `tool_names`. Owner-based restrictions are not
  implemented yet.
- `POST /telemetry/events` requires `telemetry:write` for service actors.
- `POST /runtime/tool-calls/decision` requires `runtime:decision` for service actors.
- `POST /runtime/tool-calls/resume` requires `runtime:resume` for service actors.
- `GET /runtime/tool-calls/activity` is a human-facing read endpoint for reviewer, auditor, or platform admin actors; service actors cannot read it by default.
- Missing API keys keep the local `development/dev-placeholder` fallback by default.
- Set `AGCP_REQUIRE_SERVICE_AUTH=true` to reject missing API keys on runtime and telemetry integration endpoints.
- In strict service-auth mode, service actors also need a matching fine-grained rule before telemetry or runtime records are created.
- Raw API keys must not be stored, logged, echoed in responses, or included in audit, telemetry, or evidence metadata.
- `AGCP_SERVICE_ACTOR_REGISTRY_ENABLED=false` by default. With the flag disabled,
  runtime and telemetry auth remain config-based. With the flag enabled, service
  actor API keys are resolved from the DB-backed registry and only active
  service actors with active or retiring non-expired keys can authenticate. For
  registry-backed actors, endpoint/action scopes and fine-grained rules are read
  from `service_actor_scopes` and `service_actor_scope_rules`.
- DB-backed `service_actor_scopes` and `service_actor_scope_rules` tables exist
  for registry auth. Config-auth actors still use `AGCP_SERVICE_ACTOR_SCOPES`
  and `AGCP_SERVICE_ACTOR_SCOPE_RULES`.
- This is not production-ready authentication. There are no public registry CRUD
  APIs, key rotation endpoints, OIDC/SAML/JWT, or human RBAC yet.

Manual registry seeding from hashed config:

```powershell
# Dry run. Reads AGCP_SERVICE_ACTOR_API_KEYS and writes nothing.
uv run python scripts/seed_service_actor_registry.py

# Apply. Creates missing service_actors and service_actor_api_keys records.
uv run python scripts/seed_service_actor_registry.py --apply

# Dry run. Reads AGCP_SERVICE_ACTOR_SCOPES and AGCP_SERVICE_ACTOR_SCOPE_RULES.
uv run python scripts/seed_service_actor_registry_scopes.py

# Apply. Creates missing service_actor_scopes and service_actor_scope_rules rows.
uv run python scripts/seed_service_actor_registry_scopes.py --apply
```

The key seeding helper imports only `service:<stable-id>=sha256:<digest>`
entries from `AGCP_SERVICE_ACTOR_API_KEYS`. Raw API keys must never be
committed, logged, or passed to either helper. The scope seeding helper imports
`AGCP_SERVICE_ACTOR_SCOPES` and `AGCP_SERVICE_ACTOR_SCOPE_RULES` only for
existing `service_actors`, avoids duplicate scope rows, appends non-duplicate
fine-grained rules, preserves existing records, and reports missing service
actors. Unsupported fine-grained rule fields are rejected by config validation.

Suggested rollout:

1. Keep `AGCP_SERVICE_ACTOR_REGISTRY_ENABLED=false`.
2. Run migrations and seed the registry from hashed config.
3. Dry-run, then apply the key seed helper in a controlled environment.
4. Dry-run, then apply the scope/rule seed helper and review missing actors.
5. Test one service actor with the registry flag enabled.
6. Roll back by setting `AGCP_SERVICE_ACTOR_REGISTRY_ENABLED=false`.

## Database migrations

Set the PostgreSQL connection URL with `AGCP_DATABASE_URL`.

PowerShell example:

```powershell
$env:AGCP_DATABASE_URL = "postgresql+psycopg://postgres@127.0.0.1:5432/agent_governance_control_plane?connect_timeout=5"
```

If your local PostgreSQL requires a password, include it in the URL:

```powershell
$env:AGCP_DATABASE_URL = "postgresql+psycopg://postgres:postgres@127.0.0.1:5432/agent_governance_control_plane?connect_timeout=5"
```

Bash example:

```bash
export AGCP_DATABASE_URL="postgresql+psycopg://postgres@127.0.0.1:5432/agent_governance_control_plane?connect_timeout=5"
```

Run migrations:

```bash
uv run alembic upgrade head
```

Inspect current migration state:

```bash
uv run alembic current
```

Create a future autogenerated migration after models exist:

```bash
uv run alembic revision --autogenerate -m "describe change"
```
