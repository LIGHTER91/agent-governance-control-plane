# AGCP Web App

Next.js product frontend for the Agent Governance Control Plane.

The shared product chrome uses the AGCP Studio visual shell: dark control-plane
sidebar, compact topbar, dense panels, badges, and bounded review/export
surfaces. The connected Agent, Agent detail, Human Approvals, and Evidence
pages use the same AGCP Studio visual language instead of a generic CRUD shell.
The root dashboard is the connected app entry point: it links to the real
governance routes, reads Agent and HumanApproval summary data from existing
backend endpoints, and shows an explicit unavailable state instead of synthetic
metrics when the backend cannot be reached. The Agents page and Agent detail
page read from the backend Agent Registry API, Agent activity API, and
HumanApproval API.
The Access & Data page reads Access Grants, Source inventory records, and
Source Data Usage Profiles for governance review workflows. It can transition
Access Grant statuses through explicit backend lifecycle endpoints while keeping
grants as declarative governance records. The Human Approvals page reads from
the backend HumanApproval API as a governance review queue. The Evidence page
manually loads filtered Evidence Bundle JSON for a single Agent, explains the
human-readable evidence chain, and lets reviewers download the bounded JSON
artifact returned by the backend. The Runtime Gateway
page is a static read-only overview of runtime modes, endpoints, configuration
flags, and current limitations. The Policies page is an IDE-style Policy Studio:
it reads existing Policy and PolicyRule records, offers block and Code DSL
authoring modes, and compiles local editor state back to deterministic
PolicyRule condition JSON before calling the existing Policy APIs. Its Validate
action is local parser/compile validation, not production simulation. Review and
publish workflows remain constrained by backend lifecycle support. The
Integration Hub page explains Custom
Runtime Gateway API, LangGraph, n8n, Dataiku, MCP, and generic webhook/API
connection patterns without turning AGCP into an orchestrator. It can show a
read-only Service Actor registry and API key status summary when the backend
admin APIs are enabled. The remaining sections are placeholders. It
does not implement login, does not render charts, and does not claim production
readiness or legal compliance certification.

## Stack

- Next.js
- React
- TypeScript
- Global CSS through the Next.js app router

## Run Locally

Install dependencies:

```bash
npm install
```

Start the development server:

```bash
npm run dev
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

Open the URL printed by Next.js, usually:

```text
http://localhost:3000
```

## Backend API Configuration

The shared AGCP Studio shell is rendered across the main app routes. The
implemented connected pages call:

```text
GET /agents
GET /agents/{agent_id}
GET /agents/{agent_id}/activity
GET /agents/{agent_id}/human-approvals
GET /sources
GET /sources/{source_id}/usage-profile
GET /access-grants
POST /access-grants/{access_grant_id}/suspend
POST /access-grants/{access_grant_id}/revoke
POST /access-grants/{access_grant_id}/reactivate
POST /access-grants/{access_grant_id}/expire
GET /human-approvals
GET /agents/{agent_id}/evidence-bundle
GET /service-actors
GET /service-actors/{service_actor_id}/api-keys
GET /service-actors/{service_actor_id}/scopes
GET /service-actors/{service_actor_id}/scope-rules
GET /policies
POST /policies
PATCH /policies/{policy_id}
GET /policies/{policy_id}/rules
POST /policy-rules
PATCH /policy-rules/{rule_id}
GET /policy-version-review-requests/{review_request_id}/diff
```

Configure the backend base URL with:

```bash
NEXT_PUBLIC_AGCP_API_BASE_URL=http://127.0.0.1:8000
```

If this variable is not set, the web app defaults to:

```text
http://127.0.0.1:8000
```

The backend API must be running for the root dashboard summary, Agent list,
Agent detail page, Agent activity timeline, Access & Data page, Human Approvals
list, and Evidence Bundle viewer to show data. Depending on your local browser
and API setup, CORS configuration or a Next.js proxy may be needed before
browser requests to the backend succeed. Agent activity requires a backend actor
with `reviewer`, `auditor`, or `platform_admin` role. Evidence Bundle export
also requires a backend actor with `auditor` or `platform_admin` role, or direct
user owner access when the backend allows it. Loading or downloading Evidence
Bundle JSON is a manual action and uses the backend export endpoint, preserving
backend export audit behavior. The Access & Data page treats Access Grants as
declared governance records, not IAM credentials. Access Grant transition
actions update the governance record status only; this does not by itself
guarantee runtime blocking, because runtime enforcement depends on explicit
policies.
DataUsageProfile records remain governance metadata, not legal certification.
The Integration Hub page treats Service Actor registry data as optional,
read-only integration metadata. It never displays plaintext API keys and it
states that runtime callers, not AGCP, execute tools and honor `proceed`.
The Policy Studio uses existing Policy APIs for the Policy container and saves
editor output as draft PolicyVersion snapshots. Code DSL and block editing are
frontend authoring surfaces that compile to deterministic PolicyRule condition
JSON inside the version snapshot. Blocks mode is editable for the supported V1
WHEN, CHECK, and THEN fields and updates the same compiled condition state used
by the Code DSL preview. After Save draft succeeds, the editor keeps the saved
draft content visible while the inspector updates the draft PolicyVersion id and
status. Local validation checks parser support,
required fields, unsupported DSL syntax, selected Policy/PolicyRule state, and
generated JSON shape; it does not simulate runtime impact or claim production
enforcement coverage. Built-in templates are static authoring helpers, not
backend records, and they never save automatically. Draft versions do not
affect runtime until explicit activation. Submit for review creates a dedicated
pending PolicyVersionReviewRequest for a saved draft snapshot; approval or
rejection records reviewer intent but does not activate the version. Approved
review requests can be activated explicitly from the Policy Reviews queue with
Activate approved version; activation changes future runtime policy evaluation
and replacement of an existing active version requires explicit user intent.
The Policy Reviews queue also loads deterministic metadata-only Policy Review
Diff summaries from the backend. These summaries show active/live/no-baseline
comparison state, changed condition fields, runtime-effect copy, and
activation/supersession audit references when available. They do not simulate
production impact or claim legal compliance. When a prior PolicyVersion is
available from the diff or activation evidence, reviewers can create a rollback
draft from that source. The rollback draft does not affect runtime, must be
submitted for review, and still requires explicit activation after approval.
Pending PolicyVersion review requests can also be assigned to an explicit
reviewer actor id. Assignment is governance metadata only: it does not approve,
reject, notify, activate, or change runtime state, and the backend still
enforces reviewer/platform_admin decision rules.
The Policy Reviews queue calls `GET /me` to show the current actor and make
approve/reject/assign/activate buttons advisory-role-aware. Disabled buttons
show reasons such as "Reviewer role required" or "Assigned to another
reviewer", but backend authorization remains the source of truth. There is no
fake reviewer directory; assignments use explicit stable actor ids.
Legacy live Policy and PolicyRule endpoints remain available for bootstrap and
unversioned fallback policies. Once a Policy has an active PolicyVersion,
direct live Policy/PolicyRule mutations are blocked by the backend with
guidance to use Save draft to create a reviewed PolicyVersion.
The UI intentionally has no direct Publish action.

Policy Studio backlog alignment is tracked in
`docs/POLICY_STUDIO_ISSUE_ALIGNMENT.md`. The current UI largely satisfies the
V1 guided authoring goal from #58. The controlled DSL from #76 is formally
documented in `docs/POLICY_STUDIO_DSL_DESIGN.md`: it is a frontend authoring
layer that compiles to deterministic PolicyRule condition JSON, not a runtime
engine or production simulation language. Backend review workflow refinements
should continue to follow the #56 versioning/review guardrail contract and #68
active PolicyVersion rollout decisions before adding publish-like semantics.

## Local Full-Stack Demo

The frontend does not include hardcoded demo records. To run the dashboard
against real local backend data:

```powershell
# Terminal 1: local PostgreSQL, from the repository root
docker compose -f docker-compose.dev.yml up -d postgres

# Terminal 2: backend, from the repository root
cd apps/api
$env:AGCP_DATABASE_URL = "postgresql+psycopg://postgres:postgres@127.0.0.1:5432/agent_governance_control_plane?connect_timeout=5"
uv run alembic upgrade head
uv run python scripts/seed_full_stack_demo.py --apply
uv run uvicorn --app-dir src agent_governance_api.main:app --reload

# Terminal 3: frontend, from the repository root
cd apps/web
npm install
npm run dev
```

On bash-like shells, set the database URL with `export AGCP_DATABASE_URL="..."`
before running Alembic, the seed command, and uvicorn.

Open:

```text
http://localhost:3000/agents
```

You can also open `http://localhost:3000/` for the connected product dashboard
entry point. It links to Agents, Human Approvals, Evidence, Audit, Policies,
and Settings inside the same AGCP Studio shell without embedding demo records
in the frontend.

The backend seed creates one local Agent, one active Policy and PolicyRule, one
runtime event, one PolicyDecision, one pending HumanApproval, and related
AuditLogs. That is enough to exercise the Agent list, Agent detail, Human
Approvals, Activity timeline, and Evidence Bundle pages with real API
responses. The seed excludes secrets, credentials, raw prompts, raw source
contents, raw runtime payloads, and personal data.

Troubleshooting:

- If the UI is empty, run the seed command against the same database the API is
  using and refresh `/agents`.
- If Docker is not running, start Docker Desktop before running
  `docker compose -f docker-compose.dev.yml up -d postgres`.
- If port `5432` is already in use, stop the existing PostgreSQL service or
  change the Compose host port and update `AGCP_DATABASE_URL` to match.
- If Alembic times out, check
  `docker compose -f docker-compose.dev.yml ps` and confirm the backend shell
  has `AGCP_DATABASE_URL` set with the local `postgres:postgres` credentials.
- If the browser cannot reach the API, confirm `NEXT_PUBLIC_AGCP_API_BASE_URL`
  points to the running backend, usually `http://127.0.0.1:8000`.
- If CORS fails, run the frontend from `http://localhost:3000` or add the
  frontend origin to `AGCP_CORS_ALLOWED_ORIGINS` before starting the backend.
- If the backend fails with `ModuleNotFoundError`, run uvicorn from `apps/api`
  with `--app-dir src`.

## Checks

Run the static smoke check:

```bash
npm run smoke
```

Run TypeScript validation:

```bash
npm run typecheck
```

Build the dashboard:

```bash
npm run build
```

## Current Routes

- `/`
- `/agents`
- `/agents/[agentId]`
- `/access-data`
- `/policies`
- `/integrations`
- `/runtime-gateway`
- `/human-approvals`
- `/evidence`
- `/audit`
- `/settings`

## Current Limitations

- No login or auth UI.
- No broad enterprise role-aware frontend behavior. Policy Reviews has a
  minimal `/me`-backed advisory current-actor display, but backend RBAC remains
  authoritative.
- Agent list is read-only.
- Agent detail page is read-only.
- Agent activity timeline is read-only and lightweight.
- Access & Data Source Data Usage workflow is read-only.
- Access Grant status transition actions are available, but they are not
  role-aware and do not create IAM permissions or runtime enforcement.
- Human Approvals is a read-oriented review queue in the current UI.
- Evidence Bundle viewer is manual JSON review and download only; PDF export,
  cryptographic signing, and external GRC/SIEM integrations are not implemented.
- No create, edit, or delete Agent forms.
- No dedicated Agent runtime or policy drill-down page is wired into the
  frontend yet.
- Integration Hub does not implement adapter packages, execute tools, create or
  rotate API keys, or verify that a caller is enforcing Runtime Gateway
  decisions.
- Policy Studio Save draft writes draft PolicyVersion snapshots; Submit for
  review is wired to a dedicated review request, but review approval does not
  activate or publish the version. Activation is a separate approved-review
  action.
- No PDF or signed Evidence Bundle export in the UI.
- Runtime Gateway page is read-only and does not call runtime endpoints.
- No charts or metrics.
- No production deployment configuration.
