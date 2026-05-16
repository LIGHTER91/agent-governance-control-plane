# [Codex] Auto-create HumanApproval for require_human_review decisions

Status: Completed in V0 backend milestone.

## Objective

Automatically create a pending HumanApproval when telemetry-triggered policy
evaluation returns `require_human_review`.

## Context

The V0 governance flow needs policy evaluation to create a durable human review
request without implementing notifications or runtime blocking.

## Completed scope

- Updated telemetry ingestion for `tool_call_requested` events.
- When `PolicyDecision.decision == require_human_review`, created a pending
  `HumanApproval`.
- Linked the approval to the same agent and the created policy decision.
- Used the development actor placeholder.
- Appended `human_approval_requested`.
- Kept TraceEventRecord, PolicyDecision, HumanApproval, and AuditLog in one
  transaction.
- Preserved idempotency for duplicate telemetry retries.
- Returned `human_approval_id` in telemetry responses when created.

## Non-goals preserved

- No runtime blocking.
- No notifications.
- No frontend.
- No auth/RBAC.
- No workflow engine.

## Validation

Covered by telemetry ingestion tests in the completed V0 backend milestone.
