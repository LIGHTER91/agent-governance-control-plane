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

## Initial technical hypothesis

The initial implementation should start as a modular monolith:

- Backend: FastAPI
- Persistence: PostgreSQL
- Migrations: Alembic
- Models/validation: Pydantic
- Tests: pytest
- Frontend later: Next.js + TypeScript
- Deployment initially: Docker Compose
- Avoid microservices, Kafka, Kubernetes, OPA, GraphQL, or complex RBAC until justified.

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
6. Require tests, small diffs, and a final report for every task.
7. Do not let Codex mark work as done without CI or human review.

## Definition of "done"

A task is not done unless:

- the requested scope is implemented;
- no out-of-scope feature was added;
- tests were added or updated;
- relevant checks were run;
- the diff is small enough to review;
- the PR summary lists what was done, what was not done, and remaining risks.
