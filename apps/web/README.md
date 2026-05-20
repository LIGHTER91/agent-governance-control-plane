# AGCP Web Dashboard

Minimal Next.js dashboard shell for the Agent Governance Control Plane.

The shell is intentionally minimal. The Agents page and Agent detail page read
from the backend Agent Registry API, the Human Approvals page reads from the
backend HumanApproval API, and the Evidence page reads filtered Evidence Bundle
JSON for a single Agent. The Runtime Gateway page is a static read-only overview
of runtime modes, endpoints, configuration flags, and current limitations. The
remaining sections are placeholders. It does not implement login, does not
render charts, and does not claim production readiness or legal compliance
certification.

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

Open the URL printed by Next.js, usually:

```text
http://localhost:3000
```

## Backend API Configuration

The implemented read-only pages call:

```text
GET /agents
GET /agents/{agent_id}
GET /agents/{agent_id}/human-approvals
GET /human-approvals
GET /agents/{agent_id}/evidence-bundle
```

Configure the backend base URL with:

```bash
NEXT_PUBLIC_AGCP_API_BASE_URL=http://127.0.0.1:8000
```

If this variable is not set, the web app defaults to:

```text
http://127.0.0.1:8000
```

The backend API must be running for the Agent list, Agent detail page, Human
Approvals list, and Evidence Bundle viewer to show data. Depending on your local
browser and API setup, CORS configuration or a Next.js proxy may be needed
before browser requests to the backend succeed. Evidence Bundle export also
requires a backend actor with `auditor` or `platform_admin` role.

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
- `/policies`
- `/runtime-gateway`
- `/human-approvals`
- `/evidence`
- `/audit`
- `/settings`

## Current Limitations

- No login or auth UI.
- No role-aware frontend behavior.
- Agent list is read-only.
- Agent detail page is read-only.
- Human Approvals list is read-only.
- Evidence Bundle viewer is read-only JSON inspection.
- No create, edit, or delete Agent forms.
- No approve, reject, or cancel actions in the UI.
- No dedicated Agent runtime or policy timeline endpoint is wired into the
  frontend yet.
- No Policy CRUD.
- No download, PDF, or signed Evidence Bundle export in the UI.
- Runtime Gateway page is read-only and does not call runtime endpoints.
- No charts or metrics.
- No production deployment configuration.
