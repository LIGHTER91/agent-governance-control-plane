# [Codex] Implement telemetry persistence models

Status: Completed in V0 backend milestone.

## Objective

Persist agent runs and trace events so telemetry can become reviewable evidence.

## Context

The telemetry schemas existed before persistence. The backend needed database
records for agent runs and trace events without adding streaming infrastructure
or runtime enforcement.

## Completed scope

- Added SQLAlchemy persistence models for `AgentRunRecord` and
  `TraceEventRecord`.
- Added `agent_runs` and `trace_events` tables.
- Linked telemetry records to `Agent` where appropriate.
- Added Alembic migration coverage.
- Added model and persistence tests.

## Non-goals preserved

- No telemetry ingestion endpoint behavior beyond the scoped persistence work.
- No Kafka, queues, streaming, OpenTelemetry exporter, or runtime gateway.
- No raw prompts, credentials, or sensitive payload storage.

## Validation

Covered by backend tests and migration checks in the completed V0 backend
milestone.
