# AGENTS.md — Codex operating rules

These instructions apply to the whole repository.

## Project identity

This repository implements an **Agent Governance Control Plane**.

The product vision is a complete enterprise platform to govern AI agents in production through:

- agent registry;
- tool/data/model access declarations;
- policy-driven runtime governance;
- audit trails;
- human oversight;
- evidence bundles;
- risk-oriented monitoring;
- enterprise integrations.

## Product boundaries

This project is **not** an agent orchestrator.

Do not build or imply replacement for:

- LangGraph;
- n8n;
- Dataiku;
- CrewAI;
- AutoGen;
- OpenAI Assistants;
- Azure AI;
- AWS Bedrock;
- GCP Vertex AI;
- MCP servers.

The control plane must integrate with existing stacks instead of replacing them.

## Core product question

Every feature should help answer at least one of these:

1. Which AI agents exist?
2. Who owns them?
3. What are they allowed to do?
4. Which tools, models, and data sources can they access?
5. What did they actually do?
6. Which policy allowed, denied, or escalated the action?
7. Who approved the agent, policy, or exception?
8. What evidence can be exported for review or audit?

If a feature does not support one of these questions, do not implement it unless explicitly requested.

## Architecture rules

Default architecture until changed by a human:

- modular monolith;
- explicit domain modules;
- API-first backend;
- PostgreSQL as primary database;
- immutable audit records;
- simple policy evaluator before complex policy engines;
- Docker Compose before Kubernetes;
- boring technology over fashionable technology.

Do **not** introduce these unless explicitly requested and justified:

- microservices;
- Kafka or distributed event streaming;
- Kubernetes;
- service mesh;
- OPA/Rego;
- Cedar;
- GraphQL;
- Redis;
- temporal/workflow engines;
- complex RBAC frameworks;
- vector databases;
- LLM-based policy evaluation.

## Initial stack hypothesis

Backend:

- Python;
- FastAPI;
- Pydantic;
- SQLAlchemy or SQLModel;
- Alembic;
- pytest;
- ruff;
- mypy or pyright if configured.

Frontend, when requested:

- Next.js;
- TypeScript;
- simple UI first;
- no chart-heavy dashboard unless required.

## Domain vocabulary

Use these domain terms consistently:

- Agent;
- Agent Owner;
- Environment;
- Agent Status;
- Risk Level;
- Model;
- Tool;
- Data Source;
- Permission;
- Policy;
- Policy Rule;
- Policy Decision;
- Agent Run;
- Trace Event;
- Audit Log;
- Human Approval;
- Evidence Bundle;
- Incident.

Do not invent compliance scores, risk scores, trust scores, maturity scores, or regulatory labels unless explicitly requested.

Avoid terms like:

- "AI Act compliant = true";
- "ISO 42001 certified";
- "compliance score";
- "fully compliant";
- "guaranteed safe".

Prefer:

- evidence collection;
- control coverage;
- review status;
- audit export;
- policy decision;
- risk classification;
- human oversight required.

## Security and privacy rules

Never hardcode secrets.

Never log:

- API keys;
- tokens;
- credentials;
- raw sensitive user data;
- raw prompts that may contain secrets;
- private customer data.

Every mutation of these entities must eventually create an audit record:

- Agent;
- Tool Access;
- Data Source Access;
- Policy;
- Policy Rule;
- Human Approval;
- Environment Promotion;
- Risk Classification.

Audit records must be append-only from public APIs.

## Development rules

For every implementation task:

1. Read the issue and relevant docs first.
2. Restate the scope internally.
3. Implement the smallest safe change.
4. Do not expand scope.
5. Add or update tests.
6. Run relevant checks if possible.
7. Review your own diff.
8. Report:
   - completed items;
   - files changed;
   - tests/checks run;
   - known limitations;
   - follow-up tasks.

Do not mark work as done if tests fail or were not run.

## Git rules

Use small branches.

Preferred branch naming:

```text
feature/001-repo-skeleton
feature/agent-registry
feature/audit-log
feature/policy-model
fix/<short-description>
```

Do not make large cross-cutting refactors unless explicitly requested.

## Documentation rules

When adding a major domain concept, update the relevant documentation:

- `docs/DOMAIN_MODEL.md`
- `docs/ARCHITECTURE_PRINCIPLES.md`
- `docs/DECISIONS.md`
- `docs/TASKS.md`

Documentation must not claim legal compliance. It may describe evidence support for compliance workflows.

## Definition of done

A Codex task is complete only when:

- scope is implemented;
- out-of-scope work was avoided;
- tests were added or updated;
- tests/checks were run or inability to run them is clearly stated;
- no secrets are introduced;
- public API behavior is documented;
- remaining risks are listed.
