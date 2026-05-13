# [Codex] Implement Permission domain model

## Objective

Add the initial Permission domain model linking agents to allowed tools, data sources, and models.

## Context

Permissions help answer what an agent is allowed to do and which declared resources it can access.

## Scope

- Add Permission model.
- Link permissions to an Agent and one target resource type: Tool, Data Source, or Model.
- Include fields such as id, agent_id, resource_type, resource_id, access_level, environment, status, created_at, updated_at.
- Add validation schemas.
- Add migration if persistence exists.

## Non-goals

- Do not implement complex RBAC.
- Do not implement runtime enforcement.
- Do not implement policy evaluation in this issue.
- Do not add workflow approvals.

## Acceptance criteria

- Permission model exists and validates supported resource types.
- Permissions can represent agent access to Tool, Data Source, and Model records.
- Migration exists if DB layer is present.
- Tests cover valid permissions and invalid resource types.

## Expected tests/checks

- Unit tests for Permission validation.
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
