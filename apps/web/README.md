# AGCP Web Dashboard

Minimal Next.js dashboard shell for the Agent Governance Control Plane.

The shell is intentionally minimal. The Agents page reads from the backend
Agent Registry API, while the remaining sections are placeholders. It does not
implement login, does not render charts, and does not claim production
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

Open the URL printed by Next.js, usually:

```text
http://localhost:3000
```

## Backend API Configuration

The Agents page calls:

```text
GET /agents
```

Configure the backend base URL with:

```bash
NEXT_PUBLIC_AGCP_API_BASE_URL=http://127.0.0.1:8000
```

If this variable is not set, the web app defaults to:

```text
http://127.0.0.1:8000
```

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
- `/policies`
- `/runtime-gateway`
- `/human-approvals`
- `/evidence`
- `/audit`
- `/settings`

## Current Limitations

- No login or auth UI.
- No create, edit, or delete Agent forms.
- No Policy CRUD.
- No Evidence Bundle viewer.
- No charts or metrics.
- No production deployment configuration.
