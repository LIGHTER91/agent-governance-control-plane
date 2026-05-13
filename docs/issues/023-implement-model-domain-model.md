# [Codex] Implement Model domain model

## Objective

Add the initial Model domain model for model and endpoint declarations used by agents.

## Context

The control plane must answer which models or model endpoints an agent may use without storing provider credentials.

## Scope

- Add Model model.
- Add fields such as id, provider, model_name, endpoint_alias, deployment_environment, status, created_at, updated_at.
- Add validation schemas.
- Add migration if persistence exists.
- Ensure examples do not include credentials or secret-looking values.

## Non-goals

- Do not call model providers.
- Do not store API keys, tokens, or deployment credentials.
- Do not implement model evaluation.
- Do not implement permissions in this issue.

## Acceptance criteria

- Model declaration exists and validates required fields.
- Secret fields are not part of the model.
- Migration exists if DB layer is present.
- Tests cover valid and invalid Model records.

## Expected tests/checks

- Unit tests for Model validation.
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
