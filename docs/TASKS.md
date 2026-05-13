# Tasks

This file is a lightweight project tracker.

GitHub Issues should become the source of truth once the repository is created.

## Recommended implementation order

1. `001` Initialize repository skeleton - already mostly done; validate and close only after checks pass.
2. `002` Add backend skeleton.
3. `015` Add CI quality gates.
4. `003` Add database and migrations baseline.
5. `004` Implement Agent domain model.
6. `006` Implement immutable AuditLog model.
7. `005` Implement Agent Registry API.
8. `007` Add audit records for Agent mutations.

This order intentionally pulls CI and audit earlier than the original backlog so implementation does not start with avoidable validation or governance debt.

## Backlog

- [ ] Initialize repository skeleton (already mostly done; validation/closure pending).
- [ ] Add backend skeleton.
- [ ] Add CI quality gates.
- [ ] Add database and migrations baseline.
- [ ] Implement Agent domain model.
- [ ] Implement immutable AuditLog model.
- [ ] Implement Agent Registry API.
- [ ] Add audit records for Agent mutations.
- [ ] Implement Tool domain model.
- [ ] Implement Data Source domain model.
- [ ] Implement Model domain model.
- [ ] Implement Permission domain model.
- [ ] Implement Policy domain model.
- [ ] Implement simple Policy evaluator.
- [ ] Define telemetry event schema.
- [ ] Add agent run event ingestion endpoint.
- [ ] Add dashboard shell.
- [ ] Add agent list page.
- [ ] Add evidence bundle JSON export.
- [ ] Add OpenAPI documentation examples.
- [ ] Add security baseline checks.
- [ ] Implement Human Approval model.
- [ ] Runtime Gateway design proposal.
- [ ] LangGraph integration design.

## In progress

Empty.

## Implementation complete, validation pending

Use this section when implementation is complete but tests/checks cannot run because the local environment is missing required tooling, services, or credentials.

Empty.

## Done

- [x] Create Codex-ready documentation starter.

## Blocked

Empty.

## Rule for Codex

Codex may update this file only when explicitly asked.

Codex must not move a task to Done unless:

- implementation is complete;
- tests were added or updated;
- relevant checks were run successfully;
- remaining risks were reported.

If checks cannot be run because the environment is missing, Codex must place or report the task as "implementation complete, validation pending" instead of Done.
