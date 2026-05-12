# [Codex] Define telemetry event schema

## Objective

Define schemas for agent run and trace events.

## Context

The control plane needs a framework-neutral way to receive agent activity.

## Scope

- Add AgentRun schema.
- Add TraceEvent schema.
- Add event types such as model_call_started, model_call_completed, tool_call_requested, tool_call_allowed, tool_call_denied, human_review_requested, error.
- Include correlation_id/run_id.
- Add validation tests.

## Non-goals

- Do not implement ingestion endpoint yet.
- Do not add OpenTelemetry exporter.
- Do not store raw prompts by default.

## Acceptance criteria

- Schemas validate required fields.
- Unknown event types are rejected or handled explicitly.
- Sensitive payload guidance is documented in schema comments/docs.

## Expected tests/checks

- Unit tests for valid event.
- Unit tests for invalid event type.
- Unit tests for missing correlation id.

## Codex instructions

Read `AGENTS.md` first.

Implement only this issue with the smallest safe change.

Do not add unrelated features or dependencies.

Before finishing, provide:
1. completed items;
2. files changed;
3. tests/checks run;
4. known limitations;
5. recommended follow-up tasks.
