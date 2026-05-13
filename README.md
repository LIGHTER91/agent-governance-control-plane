# Agent Governance Control Plane

A future enterprise platform to govern AI agents in production through a central registry, policy-driven runtime controls, audit trails, human oversight workflows, and evidence bundles.

This repository is intentionally prepared for Codex-assisted development. It starts with product, architecture, governance, and task-tracking documents before implementation.

## Product thesis

Organizations will deploy AI agents faster than they can govern them.

This project aims to answer:

> Which agents exist, what are they allowed to do, what did they actually do, who approved their scope, which policies were applied, and what evidence can be produced for audit?

## Non-goal

This is **not** an agent orchestrator.  
It must not replace LangGraph, n8n, Dataiku, CrewAI, AutoGen, Azure AI, AWS Bedrock, or other execution frameworks.

It is a **governance/control-plane layer** above existing agent stacks.

## Initial technical decisions

The initial implementation should start as a modular monolith:

- Python: 3.11
- Dependency manager: uv
- Backend: FastAPI
- Validation: Pydantic v2
- ORM: SQLAlchemy 2.x
- Persistence: PostgreSQL
- Migrations: Alembic
- Tests: pytest
- Lint/format: ruff
- Frontend later: Next.js + TypeScript
- Deployment initially: Docker Compose
- Avoid microservices, Kafka, Kubernetes, OPA, GraphQL, or complex RBAC until justified.

`packages/*` are internal Python packages/modules used by the backend. They are not independently deployed services.

## Repository map

```text
.
├── AGENTS.md                         # Primary Codex rules
├── docs/
│   ├── 00_START_HERE.md
│   ├── PRODUCT_CHARTER.md
│   ├── SCOPE_AND_NON_GOALS.md
│   ├── DOMAIN_MODEL.md
│   ├── ARCHITECTURE_PRINCIPLES.md
│   ├── TARGET_ARCHITECTURE.md
│   ├── SECURITY_AND_PRIVACY_GUARDRAILS.md
│   ├── COMPLIANCE_POSITIONING.md
│   ├── ROADMAP.md
│   ├── TASKS.md
│   ├── DECISIONS.md
│   ├── CODEX_WORKFLOW.md
│   ├── CODEX_PROMPTS.md
│   ├── RISK_REGISTER.md
│   └── issues/                       # GitHub issues ready to copy/create
├── .github/
│   ├── ISSUE_TEMPLATE/
│   └── pull_request_template.md
├── scripts/
│   └── create_github_issues.sh
├── apps/
│   ├── api/
│   └── web/
└── packages/
    ├── domain/
    ├── policy/
    ├── audit/
    └── telemetry/
```

## How to use this repo with Codex

1. Create a GitHub repo.
2. Copy this starter into it.
3. Commit the documentation first.
4. Create GitHub issues from `docs/issues/`.
5. Ask Codex to implement one issue at a time.
6. Start with the backend skeleton, then add CI quality gates before database work.
7. Require tests, small diffs, and a final report for every task.
8. Do not let Codex mark work as done without successful checks and human review.

## Local quality commands

Documentation baseline:

```bash
test -f AGENTS.md
test -f README.md
test -f docs/PRODUCT_CHARTER.md
test -f docs/DOMAIN_MODEL.md
test -f docs/CODEX_WORKFLOW.md
test -f docs/TASKS.md
```

Backend baseline, once `apps/api/pyproject.toml` exists:

```bash
cd apps/api
uv sync
uv run uvicorn agent_governance_api.main:app --reload
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

The backend CI workflow runs the same `uv sync`, pytest, and ruff checks from `apps/api`.

## Definition of "done"

A task is not done unless:

- the requested scope is implemented;
- no out-of-scope feature was added;
- tests were added or updated;
- relevant checks were run successfully;
- the diff is small enough to review;
- the PR summary lists what was done, what was not done, and remaining risks.

If implementation is complete but checks cannot run because local tooling or services are missing, the task is "implementation complete, validation pending", not done.
