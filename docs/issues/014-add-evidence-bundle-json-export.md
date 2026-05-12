# [Codex] Add Evidence Bundle JSON export

## Objective

Create a first evidence export for one agent.

## Context

Evidence bundles are a core bridge between engineering telemetry and governance review.

## Scope

- Add endpoint to export an agent evidence bundle as JSON.
- Include agent metadata.
- Include related audit logs.
- Include related policy decisions if available.
- Add clear schema.

## Non-goals

- Do not create PDF export.
- Do not sign bundles cryptographically.
- Do not claim legal compliance.
- Do not integrate with GRC tools.

## Acceptance criteria

- JSON export endpoint works for an agent.
- Export contains only safe fields.
- Tests cover successful export and unknown agent.

## Expected tests/checks

- API test for evidence export.
- API test for unknown agent.
- Test export excludes secrets/sensitive payloads.

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
