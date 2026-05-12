# Repository Structure

## Intended structure

```text
apps/
  api/        # backend API
  web/        # frontend dashboard

packages/
  domain/     # shared domain vocabulary and models
  policy/     # policy model and evaluator
  audit/      # audit log module
  telemetry/  # event schemas and ingestion models

docs/
  issues/     # GitHub issues ready to create
  adr/        # architecture decision records
```

## Rule

Do not add new top-level folders unless there is a clear reason.

## Backend module boundaries

- Agent Registry belongs to domain/api.
- Policy evaluation belongs to policy.
- Audit recording belongs to audit.
- Agent run events belong to telemetry.
- Compliance mapping belongs to docs/evidence later, not V0 code.
