# [Codex] Add PolicyDecision persistence service

Status: Completed in V0 backend milestone.

## Objective

Persist deterministic policy evaluation results as `PolicyDecision` records for
evidence and audit navigation.

## Context

The evaluator can produce a decision result, but policy decisions need durable
records. The service also needed caller-owned transaction behavior so future
workflows could commit related records atomically.

## Completed scope

- Added `persist_policy_decision`.
- Persisted decision, reason, agent, policy, rule, optional trace event, optional
  context hash, and created timestamp.
- Preserved `policy_id` and `rule_id` when available.
- Refactored the service so callers own commit and rollback.
- Added tests for all supported decision values and safe context handling.

## Non-goals preserved

- No telemetry-triggered evaluation in this issue.
- No runtime blocking.
- No Policy CRUD API.
- No external policy engine.

## Validation

Covered by policy decision service tests in the completed V0 backend milestone.
