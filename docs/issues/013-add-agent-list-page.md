# [Codex] Add Agent list page

## Objective

Add a minimal page listing registered agents.

## Context

Agent inventory is the first user-facing control-plane view.

## Scope

- Fetch or mock backend agent list depending on API availability.
- Display name, owner, environment, status, risk_level, framework.
- Add empty state.
- Add loading/error states if backend call exists.

## Non-goals

- Do not add charts.
- Do not add create/edit forms unless requested.
- Do not add compliance scoring.

## Acceptance criteria

- Agent list displays required fields.
- Empty state is clear.
- UI terminology matches domain docs.

## Expected tests/checks

- Frontend render test if configured.
- Build check.

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
