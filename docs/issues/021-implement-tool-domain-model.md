# [Codex] Implement Tool domain model

## Objective

Add the initial Tool domain model for agent capability declarations.

## Context

The control plane must answer which tools an agent can access before policy decisions and evidence exports become meaningful.

## Scope

- Add Tool model.
- Add fields such as id, name, description, category, owning_team, environment, status, created_at, updated_at.
- Add validation schemas.
- Add migration if persistence exists.
- Keep names aligned with `docs/DOMAIN_MODEL.md`.

## Non-goals

- Do not implement tool execution.
- Do not build an orchestration layer.
- Do not store credentials, API keys, or raw connection secrets.
- Do not implement permissions in this issue.

## Acceptance criteria

- Tool model exists and validates required fields.
- Tool records do not contain secrets.
- Migration exists if DB layer is present.
- Tests cover valid and invalid Tool records.

## Expected tests/checks

- Unit tests for Tool validation.
- Persistence tests if DB exists.
- Existing backend tests.
- `ruff check .` if configured.

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
