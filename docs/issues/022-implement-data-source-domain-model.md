# [Codex] Implement Data Source domain model

## Objective

Add the initial Data Source domain model for agent data-access declarations.

## Context

The control plane must answer which data sources agents can access while avoiding storage of sensitive payloads or credentials.

## Scope

- Add Data Source model.
- Add fields such as id, name, description, source_type, owning_team, environment, sensitivity_label, status, created_at, updated_at.
- Add validation schemas.
- Add migration if persistence exists.
- Document that connection secrets and raw sensitive data are not stored.

## Non-goals

- Do not connect to external data systems.
- Do not ingest customer records or raw files.
- Do not build data lineage.
- Do not implement permissions in this issue.

## Acceptance criteria

- Data Source model exists and validates required fields.
- Model avoids secrets and raw sensitive payloads.
- Migration exists if DB layer is present.
- Tests cover valid and invalid Data Source records.

## Expected tests/checks

- Unit tests for Data Source validation.
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
