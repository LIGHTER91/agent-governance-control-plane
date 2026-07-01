# AGCP Web App

Next.js product frontend for the Agent Governance Control Plane.

The shared product chrome uses the AGCP Studio visual shell: dark control-plane
sidebar, compact topbar, dense panels, badges, and bounded review/export
surfaces. The connected Agent, Agent detail, Human Approvals, and Evidence
pages use the same AGCP Studio visual language instead of a generic CRUD shell.
The Overview page is the connected product narrative entry point. It explains
AGCP as a governance/evidence control plane for knowing agents, controlling
risky actions, and proving decisions. It reads current actor, Agent,
HumanApproval, Policy, PolicyVersion review, and Runtime activity data from
existing backend endpoints where available, and shows honest unavailable or
empty states instead of synthetic metrics when an API cannot be reached. The
Agents page and Agent detail page read from the backend Agent Registry API,
Agent activity API, and HumanApproval API.
The Access & Data page reads Access Grants, Source inventory records, and
Source Data Usage Profiles for governance review workflows. It can transition
Access Grant statuses through explicit backend lifecycle endpoints while keeping
grants as declarative governance records. The Human Approvals route renders a
Review Inbox experience: Runtime HumanApproval records and PolicyVersion review
requests appear as unified review work items with a left inbox, selected detail
pane, and sections for why review is required, policy decision context, policy
checks, and evidence preview. Runtime HumanApproval evidence previews show safe
metadata-only CheckResult summaries when the linked PolicyDecision has them,
and otherwise show an honest empty state. Unsupported escalation and
request-info flows are shown honestly as not wired yet. The Evidence & Audit
page is now a workflow-first evidence explorer: it manually loads a real
Evidence Bundle for one Agent, organizes Subject, Policy Decision, Metadata
CheckResults, Human Review, Policy Review, Audit Trail, and Export bundle
sections, filters unsafe metadata keys defensively, and lets reviewers download
the bounded JSON artifact returned by the backend. The Runtime Decisions page is a workflow-first
timeline backed by `GET /runtime/tool-calls/activity`; it explains request
receipt, resolved context, active PolicyVersion or fallback policy selection,
metadata checks, HumanApproval linkage, and Evidence Bundle access without
inventing runtime results. The Policies page is an IDE-style Policy Studio:
it reads existing Policy and PolicyRule records, offers block and Code DSL
authoring modes, and compiles local editor state back to deterministic
PolicyRule condition JSON before calling the existing Policy APIs. Its Validate
action is local parser/compile validation, not production simulation. Review and
activation workflows remain constrained by backend lifecycle support. The
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
NEXT_PUBLIC_AGCP_API_BASE_URL=http://localhost:8000
```

If this variable is not set, the web app defaults to:

```text
http://localhost:8000
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
editor output as draft PolicyVersion snapshots. Code DSL is the precise escape
hatch and compiles to deterministic PolicyRule condition JSON inside the
version snapshot. The `/policies` route follows the attached Policy Studio
mockup direction while preserving the app shell: repository sidebar, policy
structure strip, editable Blocks canvas, Code DSL editor, local validation
console, and right inspector. It does not add a route-local navigation rail.
It keeps repository/workspace labels honest: until a backend Policy Repository
or Workspace model exists, the sidebar says Local backend and Policy repository,
and states that Policies and folders load from the AGCP backend. It does not show fake
repositories, synced state, or repository creation affordances. Policy folders
are real backend records loaded from `/policy-folders`; creating, renaming,
moving, and deleting empty folders use backend APIs, moving a Policy writes its
nullable `folder_id`, and Policies without a folder render as Uncategorized.
Tags show an explicit empty state instead of mock folder or tag chips. Blocks mode is an editable compact IDE-style view of the same compiled
condition surface: it groups WHEN, CHECK, THEN, and PROVE nodes, supports adding
and editing supported V1 fields, and keeps dedicated icons, structure arrows,
and canvas connectors. After Save draft succeeds, the editor keeps the saved
draft content visible while the inspector updates the draft PolicyVersion id
and status. On page reload, Policy Studio
hydrates the editor from the latest draft PolicyVersion snapshot when one
exists, then from the active PolicyVersion baseline when available, and only
falls back to live PolicyRule rows for unversioned/bootstrap policies. Local
validation checks parser support, required fields, unsupported DSL syntax,
selected Policy/PolicyRule state, and generated JSON shape; it does not execute
runtime decisions or claim production enforcement coverage. Built-in templates are
static authoring helpers, not backend records, and they never save
automatically. Draft versions do not affect runtime until explicit activation.
Save draft only creates or updates the draft PolicyVersion snapshot; it does not
create a review request. Draft PolicyVersions with a pending review request are
not mutable; Policy Studio shows this as a Pending review status, disables Save
draft and Submit for review, and offers Create new draft for changes so
additional work starts from a separate draft version. That action does not
submit, approve, activate, or change runtime behavior. Policy Studio reads
narrow draft review state through
`GET /policy-versions/{policy_version_id}/review-state` instead of depending on
the global review queue. The global queue remains reviewer/admin oriented.
Submit for review creates a dedicated pending PolicyVersionReviewRequest only
after the user explicitly clicks that action. On success the inspector shows
Pending review, disables Submit for review, and states that approval does not
activate this version. If a pending review request already exists, the UI shows
"Review request already pending." or the disabled reason "A review request is
already pending for this draft." instead of a raw endpoint conflict. Approval or
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
The Docker Compose dev stack configures `GET /me` as `Local Admin` with
`platform_admin`, `reviewer`, and `auditor` roles so review and activation
flows can be tested end-to-end locally. Clear `AGCP_DEV_ACTOR_ROLES` in a local
`.env` file to test restricted UI states. This is local development auth only,
not enterprise authentication.
Legacy live Policy and PolicyRule endpoints remain available for bootstrap and
unversioned fallback policies. Once a Policy has an active PolicyVersion,
direct live Policy/PolicyRule mutations are blocked by the backend with
guidance to use Save draft to create a reviewed PolicyVersion.
Policy Studio also exposes compact lifecycle actions in the inspector: Archive
policy and Delete draft policy. Archive keeps evidence and history and does not
delete PolicyVersions, reviews, runtime decisions, or audit records. Delete is
only available for draft-only policies with no governance history; policies
with versions, reviews, or runtime decisions cannot be deleted and should be
archived instead.
The UI intentionally has no direct Publish action.
Policy repository folders are backend-backed. Create, rename, move, and
delete-empty folder controls call the PolicyFolder APIs; deleting a non-empty
folder remains blocked until policies are moved elsewhere. The Blocks canvas and
Code DSL stay synchronized locally, and Save draft is the persistence boundary
for draft PolicyVersion snapshots.

Policy Studio backlog alignment is tracked in
`docs/POLICY_STUDIO_ISSUE_ALIGNMENT.md`. The current UI largely satisfies the
V1 guided authoring goal from #58. The controlled DSL from #76 is formally
documented in `docs/POLICY_STUDIO_DSL_DESIGN.md`: it is a frontend authoring
layer that compiles to deterministic PolicyRule condition JSON, not a runtime
engine or production simulation language. Backend review workflow refinements
should continue to follow the #56 versioning/review guardrail contract and #68
active PolicyVersion rollout decisions before adding publish-like semantics.
The broader frontend product direction for #74 is documented in
`docs/FRONTEND_PRODUCT_BLUEPRINT.md`. It treats Policy Studio and Review Inbox
as validated AGCPStudio surfaces, captures the remaining workflow-first
frontend gaps, and explicitly rejects API-shaped CRUD regressions, fake metrics,
fake compliance scores, and fake production simulations.

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
- No broad enterprise auth or fake user directory. Policy Reviews has a
  minimal `/me`-backed advisory current-actor display, but backend RBAC remains
  authoritative.
- Agent list is read-only.
- Agent detail page is read-only.
- Agent activity timeline is read-only and lightweight.
- Access & Data Source Data Usage workflow is read-only.
- Access Grant status transition actions are available, but they are not
  role-aware and do not create IAM permissions or runtime enforcement.
- Human Approvals is a read-oriented review queue in the current UI.
- Evidence & Audit is a manual Evidence Bundle explorer and JSON download
  workflow only; it does not provide a general evidence list, PDF export,
  cryptographic signing, or external GRC/SIEM integrations.
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
- Runtime Decisions is read-only and calls the existing runtime activity
  endpoint only; when CheckResult details are not present in that read model,
  it points users to Evidence Bundle instead of inventing pre-check results.
- No charts or metrics.
- No production deployment configuration.
