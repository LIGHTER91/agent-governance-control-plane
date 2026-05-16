# [Codex] Link PolicyDecision to TraceEventRecord

Status: Completed in V0 backend milestone.

## Objective

Add an explicit relationship from policy decisions created during telemetry
evaluation to the triggering trace event.

## Context

Context hashes are useful but not enough for evidence navigation. Reviewers need
direct IDs connecting telemetry to policy decisions.

## Completed scope

- Added nullable `trace_event_id` to `PolicyDecision`.
- Added a foreign key from `policy_decisions.trace_event_id` to
  `trace_events.id`.
- Updated SQLAlchemy models and migrations.
- Updated telemetry policy decision persistence to store `trace_event_id`.
- Added tests for telemetry-linked and non-telemetry policy decisions.

## Non-goals preserved

- No Evidence Bundle export changes in this issue.
- No runtime blocking.
- No Policy CRUD API.
- No external policy engines.

## Validation

Covered by policy and telemetry ingestion tests in the completed V0 backend
milestone.
