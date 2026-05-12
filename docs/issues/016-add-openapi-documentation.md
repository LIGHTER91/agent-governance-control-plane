# [Codex] Add OpenAPI documentation examples

## Objective

Improve API documentation with examples for core endpoints.

## Context

A control plane needs clean contracts for future SDKs and integrations.

## Scope

- Add examples for Agent create/list/get/update.
- Add examples for telemetry ingestion if available.
- Add examples for evidence export if available.
- Ensure terminology matches docs.

## Non-goals

- Do not change endpoint behavior.
- Do not add new endpoints.
- Do not add generated SDK.

## Acceptance criteria

- OpenAPI docs show useful examples.
- Examples do not contain secrets.
- Tests still pass.

## Expected tests/checks

- Existing API tests.
- Optional schema generation check.

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
