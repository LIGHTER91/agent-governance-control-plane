# [Codex] Implement agent run event ingestion endpoint

## Objective

Add API endpoint to ingest telemetry events.

## Context

Generic ingestion allows early integrations without framework-specific adapters.

## Scope

- Add endpoint to receive AgentRun/TraceEvent payloads.
- Validate payloads.
- Persist accepted events.
- Return clear validation errors.
- Add tests.

## Non-goals

- Do not build streaming ingestion.
- Do not add Kafka.
- Do not add SDK.
- Do not implement dashboard timeline.

## Acceptance criteria

- Valid events are accepted and stored.
- Invalid events are rejected.
- No sensitive payloads are logged.

## Expected tests/checks

- API test for valid event.
- API test for invalid event.
- Test logs do not include raw sensitive payload if applicable.

## Codex instructions

Read `AGENTS.md` first.

Implement only this issue with the smallest safe change.

Do not add unrelated features or dependencies.

Before finishing, provide:
1. completed items;
2. files changed;
3. tests/checks run;
4. validation status;
5. known limitations;
6. recommended follow-up tasks.
