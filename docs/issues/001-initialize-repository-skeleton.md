# [Codex] Initialize repository skeleton

## Objective

Create the initial project skeleton without implementing business logic.

## Context

The repo must be ready for iterative Codex development. This task creates structure, tooling placeholders, and a clean baseline.

Readiness note:
The repository skeleton is already mostly present. Treat this issue as validation/closure work unless a required placeholder or documented folder is missing.

## Scope

- Add initial backend and frontend folders if missing.
- Add package/module folders for domain, policy, audit, and telemetry.
- Add placeholder README files where useful.
- Keep the repo runnable/documented even if no application code exists yet.

## Non-goals

- Do not implement Agent Registry.
- Do not add a database.
- Do not add frontend UI.
- Do not introduce microservices.

## Acceptance criteria

- Repository structure matches `docs/REPO_STRUCTURE.md`.
- Required docs remain present.
- No business logic is implemented.
- If no structural changes are needed, record the issue as already mostly done and close it only after required checks pass.

## Expected tests/checks

- Run the docs check workflow locally if possible.
- Verify required files exist.

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
