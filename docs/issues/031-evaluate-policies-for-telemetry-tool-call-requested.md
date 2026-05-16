# [Codex] Evaluate policies for telemetry tool_call_requested events

Status: Completed in V0 backend milestone.

## Objective

Evaluate active persisted policies when telemetry reports a requested tool call.

## Context

The backend needed to connect telemetry ingestion, persisted policy rules,
deterministic evaluation, and durable policy decisions.

## Completed scope

- Updated `POST /telemetry/events` for `tool_call_requested` events.
- Required `metadata.tool_name` for tool-call policy evaluation.
- Loaded active policies and policy rules through the adapter.
- Evaluated policies with the deterministic evaluator.
- Persisted a `PolicyDecision` in the same transaction as the trace event.
- Returned the policy decision in the telemetry response.
- Preserved non-tool-call telemetry behavior.
- Added duplicate handling so retrying the same telemetry event does not create
  duplicate policy decisions.

## Non-goals preserved

- No runtime blocking.
- No prevention of event storage when decision is `deny`.
- No Policy CRUD API.
- No auth/RBAC.
- No external policy engines.

## Validation

Covered by telemetry ingestion tests in the completed V0 backend milestone.
