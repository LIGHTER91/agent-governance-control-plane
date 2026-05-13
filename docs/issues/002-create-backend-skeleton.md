# [Codex] Create backend skeleton

## Objective

Create a minimal FastAPI backend skeleton with healthcheck and test setup.

## Context

The platform needs a small, boring backend foundation before adding domain features.

Toolchain decisions:
Use Python 3.11, uv, FastAPI, Pydantic v2, pytest, and ruff.

## Scope

- Create FastAPI app under `apps/api`.
- Add `/health` endpoint.
- Add configuration module.
- Add basic logging setup.
- Add uv project metadata for the backend.
- Add pytest configuration.
- Add one API test for `/health`.

## Non-goals

- Do not add Agent Registry.
- Do not add database models.
- Do not add auth.
- Do not add Docker unless explicitly necessary.

## Acceptance criteria

- `GET /health` returns OK.
- Test for health endpoint passes.
- Backend can be run locally with documented command.

## Expected tests/checks

- `pytest`
- `ruff check .` if ruff is configured.

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
