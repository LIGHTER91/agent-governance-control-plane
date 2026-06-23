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

For the full local development stack, including PostgreSQL, migrations,
backend, and frontend, run this from the repository root:

```bash
docker compose -f compose.dev.yml up --build
```

On Windows PowerShell:

```powershell
.\scripts\dev-up.ps1
```

The API uses a `src` layout, so `--app-dir src` is required when running from
`apps/api`. After startup, `GET /health` should return:

```json
{"status":"ok","service":"Agent Governance Control Plane API","environment":"development"}
```

Local browser requests from the web dashboard are allowed for
`http://localhost:3000` and `http://127.0.0.1:3000` by default. Override the
comma-separated allowlist with `AGCP_CORS_ALLOWED_ORIGINS` when the frontend
runs from another origin:

```powershell
$env:AGCP_CORS_ALLOWED_ORIGINS = "http://localhost:3000,http://127.0.0.1:3001"
```

Start local development PostgreSQL from the repository root:

```powershell
docker compose -f docker-compose.dev.yml up -d postgres
```

Configure the API shell to use that local database:

```powershell
$env:AGCP_DATABASE_URL = "postgresql+psycopg://postgres:postgres@127.0.0.1:5432/agent_governance_control_plane?connect_timeout=5"
```

The Compose database uses the same local database name, user, password, and
PostgreSQL 16 image as CI. The `postgres` password is for local development
only and is not production deployment guidance.

Run database migrations:

```bash
uv run alembic upgrade head
```

Seed local full-stack demo data:

```bash
uv run python scripts/seed_full_stack_demo.py --apply
```

Without `--apply`, the seed command is a dry run. The applied seed creates
local-only records for one Agent, one active Policy and PolicyRule, one
AgentRunRecord, one TraceEventRecord, one PolicyDecision, one pending
HumanApproval, and related AuditLogs. This gives the frontend real backend data
for the Agent list, Agent detail page, Human Approvals page, Activity timeline,
and Evidence Bundle page. It also creates a second local-only metadata
pre-check scenario with one production demo Agent, confidential Source metadata,
an external ModelAsset, active AccessGrants, PolicyCheckSteps, and an active
PolicyVersion snapshot. The seed is deterministic and safe to rerun; existing
demo records are reused by ID.

The demo seed does not create secrets, API keys, credentials, raw prompts, raw
source contents, raw runtime payloads, or personal data. It is local/dev data
only and is not production provisioning.

To validate metadata-only runtime pre-checks end to end, enable the opt-in flag
before starting the API:

```powershell
$env:AGCP_RUNTIME_METADATA_PRE_CHECKS_ENABLED = "true"
uv run uvicorn --app-dir src agent_governance_api.main:app --reload
```

Then call the Runtime Gateway with the seeded metadata demo IDs:

```powershell
curl.exe -X POST http://localhost:8000/runtime/tool-calls/decision `
  -H "Content-Type: application/json" `
  -d '{ "request_id": "metadata-precheck-demo-001", "agent_id": "00000000-0000-4000-8000-000000001101", "run_id": "00000000-0000-4000-8000-000000001a01", "correlation_id": "metadata-precheck-demo", "tool_name": "vectorize_source", "action_summary": "Vectorize a confidential demo source with an external embedding model.", "metadata": { "demo": "metadata_pre_check" }, "mode": "simulation", "action_type": "vectorize", "capability_id": "00000000-0000-4000-8000-000000001201", "source_ids": ["00000000-0000-4000-8000-000000001301"], "model_id": "00000000-0000-4000-8000-000000001401", "purpose": "semantic_search_indexing", "data_classification": "confidential", "contains_personal_data": false, "contains_sensitive_data": true }'
```

Expected result: the response is `require_human_review` with a pending
HumanApproval. Real metadata-only CheckResults are created for Source status,
Source classification, Data Usage Profile status, Capability status, ModelAsset
status, ModelAsset provider type, and AccessGrant status. The Review Inbox and
Evidence Bundle show safe CheckResult summaries; they do not include source
contents, prompts, credentials, scanner findings, or raw payloads. Use a new
`request_id` and `run_id` if you want to create another fresh runtime decision.

Troubleshooting:

- `ModuleNotFoundError: agent_governance_api`: include `--app-dir src` in the
  uvicorn command when running from `apps/api`.
- Docker not running: start Docker Desktop, then rerun
  `docker compose -f docker-compose.dev.yml up -d postgres` from the repository
  root.
- Port `5432` already in use: stop the existing local PostgreSQL service, or
  change the Compose host port and update `AGCP_DATABASE_URL` to match.
- Alembic connection timeout: verify
  `docker compose -f docker-compose.dev.yml ps` shows a healthy `postgres`
  service and confirm `AGCP_DATABASE_URL` includes `postgres:postgres`.
- Empty frontend views: rerun
  `uv run python scripts/seed_full_stack_demo.py --apply` against the backend
  database and refresh `/agents`.
- Browser CORS errors: keep the frontend on the default local origins or update
  `AGCP_CORS_ALLOWED_ORIGINS`.

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
- `GET /agents/{agent_id}/access-grants` returns the Agent's declared access
  grants, sorted newest first. Optional filters: `status` and `target_type`.
- `GET /agents/{agent_id}/activity` returns a read-only activity timeline sorted newest first for product navigation.
- `GET /agents/{agent_id}/governance-profile` returns a compact read-only
  Agent Governance Profile with Agent metadata, owner, recent activity,
  HumanApproval summary, Access Grants with safe target references,
  policy/rule references, and an Evidence Bundle export hint.
- `GET /agents/{agent_id}/evidence-bundle` exports a JSON evidence bundle
  for one agent, including related audit logs, runs, trace events, policy
  decisions, human approvals, Agent-scoped Access Grants, and safe Capability,
  Source, and ModelAsset references plus Data Usage Profile summaries.
- `GET /agents/{agent_id}/human-approvals` lists human approvals for one agent.
- `PATCH /agents/{agent_id}` updates an agent and appends an internal `agent_updated` or `agent_status_changed` audit event.

Agent mutations use the local development actor until authentication exists:

- `actor_type = "development"`
- `actor_id = "dev-placeholder"` by default

For local review workflow testing, the development actor can be configured with
environment variables:

```powershell
$env:AGCP_DEV_ACTOR_ID = "local-admin"
$env:AGCP_DEV_ACTOR_ROLES = "platform_admin,reviewer,auditor"
$env:AGCP_DEV_ACTOR_DISPLAY_NAME = "Local Admin"
```

`AGCP_DEV_ACTOR_ROLES` accepts only `auditor`, `reviewer`, and
`platform_admin`. Invalid roles fail configuration clearly. These settings
apply only to the local development actor returned by `GET /me`; they are not
enterprise authentication, do not create a user directory, and do not bypass
backend RBAC. Clear `AGCP_DEV_ACTOR_ROLES` to test restricted frontend states.

The Agent Governance Profile is a read model for product navigation and the
frontend Agent Governance Profile UI. It does not include full Evidence Bundle
contents and should not be treated as an audit export.

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
- Capabilities can be referenced by Access Grants, but are not enforced by
  runtime policy evaluation yet.

Source Inventory:

- `POST /sources` creates a governed source inventory record and appends
  `source_created`.
- `GET /sources` lists source records.
- `GET /sources/{source_id}` returns one source.
- `PATCH /sources/{source_id}` updates a source and appends `source_updated`
  or `source_status_changed`.
- `POST /sources/{source_id}/usage-profile` creates a Data Usage Profile for
  one Source and appends `data_usage_profile_created`.
- `GET /sources/{source_id}/usage-profile` returns the Source's Data Usage
  Profile.
- `PATCH /sources/{source_id}/usage-profile` updates the Source's Data Usage
  Profile and appends `data_usage_profile_updated` or
  `data_usage_profile_review_status_changed`.
- Sources can represent knowledge bases, databases, document stores, APIs,
  buckets, filesystems, or other governed data or knowledge sources.
- Source metadata rejects unsafe key names such as `api_key`, `token`,
  `password`, `secret`, and `authorization`.
- Source inventory records do not ingest or store source contents, and Sources
  can be referenced by Access Grants but are not enforced yet.
- Data Usage Profiles are declared or validated governance metadata. They can
  describe classification, personal or sensitive data signals, allowed and
  prohibited purposes, allowed and prohibited processing, review status, and
  safe DPIA references. They do not store source contents, document chunks,
  prompts, scanner raw payloads, credentials, or legal compliance
  certifications.
- Data Usage Profile metadata rejects unsafe key names such as `api_key`,
  `token`, `password`, `secret`, and `authorization`.
- Data Usage Profiles are not enforced by Runtime Gateway or policy evaluation
  yet. Evidence Bundle export includes safe Data Usage Profile summaries when
  an Agent AccessGrant references the related Source.

Model Inventory:

- `POST /models` creates a governed model inventory record and appends
  `model_asset_created`.
- `GET /models` lists model asset records.
- `GET /models/{model_id}` returns one model asset.
- `PATCH /models/{model_id}` updates a model asset and appends
  `model_asset_updated` or `model_asset_status_changed`.
- Model assets can represent hosted LLMs, embedding models, rerankers,
  classifiers, vision models, audio models, or other governed model assets.
- Model asset metadata rejects unsafe key names such as `api_key`, `token`,
  `password`, `secret`, and `authorization`.
- Model inventory records do not store credentials or call provider APIs. Model
  assets can be referenced by Access Grants but are not enforced yet.

Access Grant Inventory:

- `POST /access-grants` creates a governed access grant inventory record and
  appends `access_grant_created`.
- `GET /access-grants` lists access grant records.
- `GET /access-grants/{access_grant_id}` returns one access grant.
- `PATCH /access-grants/{access_grant_id}` updates an access grant and appends
  `access_grant_updated` or `access_grant_status_changed`.
- Access grants declare what an Agent is allowed to use, who granted that
  access, why, and whether it is pending review, active, suspended, revoked, or
  expired.
- Access grants are the current association layer between Agents and governed
  inventory targets. They can point to Capability, Source, ModelAsset,
  external, or other targets without adding separate join tables.
- `granted_by_actor_type` and `granted_by_actor_id` are derived from the
  current `ActorContext` on create; callers cannot spoof grantor fields in the
  request body.
- Access grant metadata rejects unsafe key names such as `api_key`, `token`,
  `password`, `secret`, and `authorization`.
- Access grants are governance inventory only. They do not enforce runtime
  access yet and do not replace PolicyDecision, Runtime Gateway, or Human
  Approval records.
- Evidence Bundle export includes Agent-scoped Access Grants, safe Capability,
  Source, and ModelAsset references, and safe Data Usage Profile summaries for
  granted Sources. It also includes safe CheckResult summaries linked to the
  Agent through PolicyDecisions or Agent-scoped pre-check records. It does not
  export source contents, credentials, scanner payloads, or raw payloads.

Policy Management:

- `POST /policies` creates a Policy lifecycle record and appends
  `policy_created`.
- `GET /policies` lists Policy records.
- `GET /policies/{policy_id}` returns one Policy.
- `GET /policies/{policy_id}/rules` lists PolicyRule records for one Policy.
- `PATCH /policies/{policy_id}` updates a Policy and appends `policy_updated`
  or `policy_status_changed`.
- `POST /policies/{policy_id}/archive` sets `Policy.status = archived`,
  appends `policy_archived`, and retains PolicyVersions, PolicyRules,
  PolicyDecisions, review requests, and AuditLogs. Policies with an active
  PolicyVersion are blocked until that version is superseded or otherwise
  deactivated.
- `DELETE /policies/{policy_id}` is limited to draft-only/bootstrap cleanup.
  It succeeds only when the Policy has no PolicyVersion, review request,
  PolicyDecision, linked HumanApproval history, or meaningful audit history.
  Governed Policies return a safe 409 telling callers to archive instead.
- `POST /policy-rules` creates a deterministic PolicyRule and appends
  `policy_rule_created`.
- `GET /policy-rules` lists PolicyRule records.
- `GET /policy-rules/{rule_id}` returns one PolicyRule.
- `GET /policy-rules/{rule_id}/check-steps` lists PolicyCheckStep records
  attached to one PolicyRule.
- `PATCH /policy-rules/{rule_id}` updates a PolicyRule and appends
  `policy_rule_updated`.
- `POST /policy-check-steps` creates a metadata-only check declaration for a
  PolicyRule and appends `policy_check_step_created`.
- `GET /policy-check-steps` lists PolicyCheckStep records.
- `GET /policy-check-steps/{step_id}` returns one PolicyCheckStep.
- `PATCH /policy-check-steps/{step_id}` updates a PolicyCheckStep and appends
  `policy_check_step_updated` or `policy_check_step_status_changed`.
- Policy statuses are `draft`, `active`, `disabled`, and `archived`; there is
  no destructive delete for Policies with governance history.
- PolicyRule conditions must be JSON objects using the deterministic condition
  shape already consumed by the evaluator: required `decision` and `reason`,
  optional `agent_id`, `tool_name`, `environment`, `risk_level`,
  `action_type`, `capability_id`, `source_id` or `source_ids`, `model_id`,
  `purpose`, `data_classification`, `declared_data_classification`,
  `contains_personal_data`, `contains_sensitive_data`, and safe resolved
  inventory fields such as `capability_type`, `capability_status`,
  `source_status`, `source_data_classification`, `model_type`,
  `model_provider`, `model_provider_type`, `model_status`,
  `access_grant_status`, `data_usage_review_status`,
  `data_usage_allowed_purpose`, and `data_usage_prohibited_purpose`.
  Conditions may also explicitly match safe CheckResult summaries through
  `check_type`, `check_outcome`, `check_target_type`, `check_target_id`,
  `check_min_confidence`, and `check_tool_id`.
- Contextual PolicyRule matching is deterministic field matching only. For
  `source_ids`, a rule matches when any declared source ID overlaps the request
  source IDs. List-valued resolved fields match when any rule value overlaps
  the resolved context. Caller-supplied classification and
  personal/sensitive-data flags are declared runtime context, not verified Data
  Usage Profile truth.
- PolicyVersion-backed draft/review/activation is the product path for reviewed
  runtime policy changes. Legacy live Policy and PolicyRule APIs remain for
  bootstrap and unversioned fallback policies, and active-versioned policies
  block direct live edits.
- Metadata-only Policy Pre-Check persistence and internal helper functions
  exist for `CheckTool` and `CheckResult` records. The helpers can check
  AccessGrant status, Data Usage Profile review status, Source
  status/classification, Capability status, and ModelAsset
  status/provider type. The backend also has a formal
  `agent_governance_api.check_tools` adapter boundary with safe
  `CheckToolRequest` and `CheckToolResult` objects, execution modes, and a
  metadata-only adapter for AccessGrant status, Data Usage Profile status,
  Source status/classification, ModelAsset status/provider type, and
  Capability status. The adapter boundary does not add public CheckTool APIs,
  external scanner calls, webhooks, or AGCP-side tool execution. When
  `AGCP_RUNTIME_METADATA_PRE_CHECKS_ENABLED=true`, Runtime Gateway decision
  requests execute active authored PolicyCheckSteps through the metadata-only
  adapter boundary, link results to TraceEvent/PolicyDecision records, and
  persist linked CheckResults. The flag is disabled by default, there are no
  public CheckTool or CheckResult management APIs yet, and
  CheckResults do not automatically change the final decision. A CheckResult
  can affect `decision` or `proceed` only when a PolicyRule explicitly matches
  its safe outcome context.
  CheckResults store safe outcomes, confidence labels, summaries, reasons,
  references, and safe metadata only; they must not store source contents,
  prompts, scanner raw payloads, or credentials.
- PolicyCheckStep records are authoring/configuration only. They declare
  expected metadata-only checks for PolicyRules using constrained check types
  and target selectors. Persistent check types include `source_classification`
  using Source selectors and `model_provider_type` using ModelAsset selectors.
  Runtime Gateway executes active authored steps only when
  `AGCP_RUNTIME_METADATA_PRE_CHECKS_ENABLED=true`; the recorded
  CheckResults remain evidence inputs and affect runtime decisions only through
  explicit deterministic PolicyRule matching. PolicyCheckStep
  `failure_behavior` is not automatically enforced.

Human Approvals:

- `POST /human-approvals` creates a pending human approval for an existing agent and appends `human_approval_requested`.
- `GET /human-approvals/{approval_id}` returns one human approval.
- HumanApproval read responses include safe metadata-only CheckResult summaries
  when the approval is linked to a PolicyDecision that has CheckResults. These
  summaries expose bounded evidence fields such as `check_type`, outcome,
  target, confidence, timestamp, and filtered metadata only.
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
- Decision requests may include optional contextual fields:
  `action_type`, `capability_id`, `source_ids`, `model_id`, `purpose`,
  `data_classification`, `contains_personal_data`, and
  `contains_sensitive_data`. These are recorded as safe context for activity and
  evidence, and active PolicyRules may match them explicitly.
- Runtime decisions resolve safe context from referenced Capability, Source,
  ModelAsset, Data Usage Profile, and Agent AccessGrant records. Resolved facts
  are kept distinct from caller-declared fields and may be recorded in trace
  metadata with `resolved_` prefixes. Missing references are represented as
  `missing`, not as safe or allowed. AccessGrant status is context only; it is
  not automatically enforced yet.
- Optional metadata-only runtime pre-check execution is disabled by default.
  Set `AGCP_RUNTIME_METADATA_PRE_CHECKS_ENABLED=true` to execute active
  authored PolicyCheckSteps linked to matched PolicyRules and persist safe
  CheckResults for referenced Capability, Source, Data Usage Profile,
  ModelAsset, and AccessGrant checks, including Source classification and
  ModelAsset provider type. These checks read persisted metadata only, do not
  execute tools or scanners, and do not directly change `decision` or
  `proceed`; active PolicyRules may explicitly match their safe CheckResult
  outcome context, while `failure_behavior` is recorded as evidence intent
  only.
- `mode = "simulation"` is enabled by default and records the decision/evidence chain without claiming action blocking.
- `mode = "enforcement"` is disabled by default. Set `AGCP_RUNTIME_ENFORCEMENT_ENABLED=true` to accept enforcement requests.
- Enforcement mode reuses the simulation evidence workflow and returns `proceed = true` only for `allow`. `deny`, `require_human_review`, and `not_applicable` return `proceed = false`.
- The gateway never executes tools. The calling wrapper or adapter must enforce the returned `proceed` value.
- `mode = "telemetry"` is not implemented on the runtime endpoint; use `POST /telemetry/events` for telemetry ingestion.
- Runtime metadata rejects unsafe key names such as `api_key`, `token`,
  `password`, `secret`, `authorization`, `raw_content`, `chunks`, and `prompt`.
  Send stable references and short labels instead of raw source contents,
  document chunks, prompts, scanner payloads, credentials, or provider/tool
  payloads.

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

Set the PostgreSQL connection URL with `AGCP_DATABASE_URL`. For the local
Docker Compose database, include the local `postgres` password.

PowerShell example:

```powershell
$env:AGCP_DATABASE_URL = "postgresql+psycopg://postgres:postgres@127.0.0.1:5432/agent_governance_control_plane?connect_timeout=5"
```

If you run a separate local PostgreSQL without a password, omit the password
portion:

```powershell
$env:AGCP_DATABASE_URL = "postgresql+psycopg://postgres@127.0.0.1:5432/agent_governance_control_plane?connect_timeout=5"
```

Bash example:

```bash
export AGCP_DATABASE_URL="postgresql+psycopg://postgres:postgres@127.0.0.1:5432/agent_governance_control_plane?connect_timeout=5"
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
