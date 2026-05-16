# [Codex] Add telemetry idempotency

Status: Completed in V0 backend milestone.

## Objective

Avoid duplicate trace event records when integrations retry telemetry
submission.

## Context

Clients may retry `POST /telemetry/events`. The same external event should not
create duplicate evidence rows.

## Completed scope

- Added `external_event_id` support for telemetry events.
- Enforced uniqueness by `(agent_id, run_id, external_event_id)`.
- Updated telemetry ingestion so duplicates return the existing event response.
- Preserved the same `external_event_id` for different runs when scoped by
  `(agent_id, run_id)`.
- Added tests for duplicate handling and integrity preservation.

## Non-goals preserved

- No policy evaluation changes beyond duplicate response preservation.
- No queues, streaming, runtime gateway, or new dependencies.

## Validation

Covered by telemetry ingestion and persistence tests in the completed V0 backend
milestone.
