# [Codex] Implement Agent Registry API

## Objective

Add CRUD API endpoints for Agent Registry.

## Context

Users need to register, list, inspect, update, and retire agents.

## Scope

- Add create agent endpoint.
- Add list agents endpoint.
- Add get agent by id endpoint.
- Add update agent endpoint.
- Add retire/suspend status update support.
- Add request/response schemas.
- Add OpenAPI examples if supported.

## Non-goals

- Do not implement frontend.
- Do not implement policy engine.
- Do not implement complex RBAC.
- Do not add audit logging unless the audit issue is already complete.

## Acceptance criteria

- CRUD endpoints work.
- Invalid inputs return clear validation errors.
- API tests cover create/list/get/update.

## Expected tests/checks

- API tests for successful create/list/get/update.
- API tests for invalid enum values.
- API tests for missing required fields.

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
