# [Codex] Add CI quality gates

## Objective

Add CI checks for backend tests, linting, and docs presence.

## Context

Codex output must be automatically checked before human review.

## Scope

- Add GitHub Actions workflow for backend tests if backend exists.
- Add lint check if tooling exists.
- Keep docs check.
- Document local commands.

## Non-goals

- Do not add deployment.
- Do not add Docker registry publishing.
- Do not add security scanner unless simple and justified.

## Acceptance criteria

- CI runs on pull requests.
- Failing tests block merge.
- README or docs list commands.

## Expected tests/checks

- Validate workflow syntax if possible.
- Run local commands.

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
