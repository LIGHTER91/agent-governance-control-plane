# [Codex] Add audit logs for Agent mutations

## Objective

Create audit records when agents are created or updated.

## Context

Agent lifecycle changes must be reviewable.

## Scope

- On agent create, append `agent_created` audit event.
- On agent update, append `agent_updated` audit event.
- On status change to suspended/retired, append specific event if useful.
- Include actor placeholder if auth is not implemented.

## Non-goals

- Do not implement full auth.
- Do not implement audit export.
- Do not store sensitive raw payloads.

## Acceptance criteria

- Creating an agent creates one audit event.
- Updating an agent creates one audit event.
- Audit metadata is minimal and safe.

## Expected tests/checks

- API test for create produces audit record.
- API test for update produces audit record.
- Test audit event does not include secrets.

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
