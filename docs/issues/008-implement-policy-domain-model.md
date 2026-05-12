# [Codex] Implement Policy domain model

## Objective

Add initial Policy, PolicyRule, and PolicyDecision models.

## Context

Policy decisions are the core mechanism for governance.

## Scope

- Add Policy model.
- Add PolicyRule model.
- Add PolicyDecision model.
- Add decision enum: allow, deny, require_human_review, not_applicable.
- Add migration.
- Add validation schemas.

## Non-goals

- Do not build a complex DSL.
- Do not add OPA/Rego.
- Do not implement runtime gateway.
- Do not call LLMs for policy decisions.

## Acceptance criteria

- Models and enums exist.
- Invalid decision values are rejected.
- Migrations work.

## Expected tests/checks

- Unit tests for policy decision enum.
- Persistence tests if DB exists.

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
