# Roadmap

## Phase 0 — Repository and Codex setup

Goal: make development safe, structured, and reviewable.

- Create repo.
- Add AGENTS.md.
- Add product and architecture docs.
- Add issue templates.
- Add PR template.
- Add initial backlog.

## Phase 1 — Product nucleus

Goal: prove the governance core.

Features:

- Agent Registry.
- Agent lifecycle status.
- Tool/data/model declarations.
- Immutable AuditLog.
- Basic Policy model.
- Basic PolicyDecision model.
- Minimal policy evaluator.
- Telemetry event schema.

## Phase 2 — Minimal operational control plane

Goal: make agent behavior observable and reviewable.

Features:

- Agent run event ingestion.
- Agent run timeline.
- Policy decision timeline.
- Human review model.
- Evidence export JSON.
- Basic dashboard.

## Phase 3 — Runtime governance

Goal: move from observation to enforcement/simulation.

Features:

- Runtime gateway prototype.
- Allow/deny/review decisions.
- SDK/middleware for one framework.
- Policy versioning.
- Policy simulation mode.
- Incident creation.

## Phase 4 — Enterprise governance

Goal: prepare for serious enterprise usage.

Features:

- RBAC.
- SSO.
- retention policies.
- audit export.
- evidence bundles.
- approval workflows.
- risk review dashboard.
- integration with SIEM/GRC tools.

## Phase 5 — Platform expansion

Goal: become a complete Agent Governance Control Plane.

Features:

- multiple framework adapters;
- LangGraph integration;
- n8n/Dataiku integration;
- MCP integration;
- cloud AI platform connectors;
- advanced reporting;
- compliance framework mappings;
- marketplace of policy templates.
