# [Codex] Implement immutable AuditLog model

## Objective

Create append-only AuditLog model and persistence.

## Context

Auditability is a core differentiator of the control plane.

## Scope

- Add AuditLog model.
- Add fields: id, event_type, actor_type, actor_id, entity_type, entity_id, summary, metadata, created_at.
- Add migration.
- Add internal service for appending audit records.
- Ensure public API does not expose update/delete audit operations.
- Before full authentication exists, support a system actor or development actor placeholder.

## Non-goals

- Do not build audit dashboard.
- Do not implement cryptographic signing.
- Do not log sensitive payloads.

## Acceptance criteria

- AuditLog records can be appended.
- Every AuditLog record includes actor_type and actor_id.
- No public update/delete endpoint exists.
- Tests verify append behavior.

## Expected tests/checks

- Unit test for audit append service.
- Persistence test for audit records.
- Test that no update/delete route exists if routes are generated.

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
