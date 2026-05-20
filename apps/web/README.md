# AGCP Web Dashboard

Minimal Next.js dashboard shell for the Agent Governance Control Plane.

The shell is intentionally static for now. It does not call the backend, does
not implement login, does not render charts, and does not claim production
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

- No backend calls.
- No login or auth UI.
- No Agent list page data.
- No Policy CRUD.
- No Evidence Bundle viewer.
- No charts or metrics.
- No production deployment configuration.
