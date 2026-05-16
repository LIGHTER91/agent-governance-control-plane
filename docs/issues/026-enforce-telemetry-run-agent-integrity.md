# [Codex] Enforce telemetry run-agent integrity

Status: Completed in V0 backend milestone.

## Objective

Prevent trace events from pointing to a run owned by a different agent.

## Context

`TraceEventRecord` stores both `agent_id` and `run_id`. Without a composite
relationship to `AgentRunRecord`, inconsistent evidence could be created.

## Completed scope

- Added a composite uniqueness rule for `agent_runs(agent_id, run_id)`.
- Added a composite foreign key from `trace_events(agent_id, run_id)` to
  `agent_runs(agent_id, run_id)`.
- Updated SQLAlchemy model definitions and migrations.
- Added tests for matching and mismatched agent/run relationships.

## Non-goals preserved

- No telemetry ingestion endpoint change beyond preserving the integrity rule.
- No alternative database or SQLite-only behavior.
- No runtime gateway or policy evaluation changes.

## Validation

Covered by backend persistence tests and PostgreSQL DDL checks in the completed
V0 backend milestone.
