# [Codex] Add database and migrations baseline

## Objective

Add PostgreSQL persistence setup and Alembic migration baseline.

## Context

Core governance entities require durable storage and migration discipline.

## Scope

- Add SQLAlchemy or SQLModel setup.
- Add database session management.
- Add Alembic.
- Create an empty initial migration.
- Add documentation for running migrations.

## Non-goals

- Do not create Agent model yet.
- Do not add audit tables yet.
- Do not add production deployment configs.

## Acceptance criteria

- Migrations can be generated and applied locally.
- DB config uses environment variables.
- No secrets are hardcoded.

## Expected tests/checks

- Run migration command if local DB is available.
- Run backend tests.

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
