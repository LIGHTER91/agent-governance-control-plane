# [Codex] Create dashboard shell

## Objective

Create a minimal frontend shell for the future dashboard.

## Context

The UI should remain simple and reflect governance workflows, not marketing charts.

## Scope

- Create web app skeleton under `apps/web`.
- Add layout with navigation placeholders: Agents, Policies, Audit, Evidence.
- Add README with run command.

## Non-goals

- Do not add charts.
- Do not implement auth.
- Do not implement full design system.
- Do not call backend yet unless already configured.

## Acceptance criteria

- Frontend runs locally.
- Navigation placeholders exist.
- No fake compliance scores are shown.

## Expected tests/checks

- Run frontend build if configured.
- Add basic render test if test setup exists.

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
