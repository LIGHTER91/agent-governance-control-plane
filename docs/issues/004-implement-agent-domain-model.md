git po# [Codex] Implement Agent domain model

## Objective

Implement the Agent domain model and validation enums.

## Context

Agent Registry is the first core module of the control plane.

## Scope

- Add Agent model.
- Add Environment enum: development, staging, production.
- Add AgentStatus enum: draft, under_review, approved, active, suspended, retired.
- Add RiskLevel enum: low, medium, high, critical.
- Add fields: id, name, description, owner_type, owner_id, owner_name, owner_contact_email, environment, status, risk_level, framework, created_at, updated_at.
- Add DB migration if persistence exists.

## Non-goals

- Do not implement CRUD endpoints.
- Do not implement policy engine.
- Do not implement audit logging yet.

## Acceptance criteria

- Domain model exists and validates allowed enum values.
- Invalid enum values are rejected.
- Migration exists if DB layer is present.

## Expected tests/checks

- Unit tests for enum validation.
- Model persistence test if DB exists.

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
