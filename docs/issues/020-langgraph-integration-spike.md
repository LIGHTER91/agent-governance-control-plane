# [Spike] LangGraph integration design

## Objective

Investigate the smallest useful LangGraph integration path.

## Context

One framework adapter can validate the control-plane integration model.

## Scope

- Identify where to instrument LangGraph runs.
- Propose event mapping to telemetry schema.
- Propose minimal SDK/middleware shape.
- List limitations and security concerns.

## Non-goals

- Do not implement integration.
- Do not add LangGraph as dependency yet.
- Do not modify backend code.

## Acceptance criteria

- Design doc is created.
- Required events are mapped to telemetry schema.
- Follow-up implementation issue is proposed.

## Expected tests/checks

- No code tests required.
- Documentation review only.

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
