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

## Architecture boundary

This repository is a modular monolith.

`packages/*` are internal Python packages/modules consumed by `apps/api`. They are not independently deployed services, microservices, or separate runtime products.

Use package boundaries to keep the domain clear:

- `packages/domain` owns core governance vocabulary and shared domain models.
- `packages/policy` owns policy models and deterministic evaluation.
- `packages/audit` owns append-only audit log models and services.
- `packages/telemetry` owns agent run and trace event schemas.

Do not introduce service boundaries, network calls between packages, queues, or deployment units unless a human explicitly changes the architecture decision.

## Backend module boundaries

- Agent Registry belongs to domain/api.
- Policy evaluation belongs to policy.
- Audit recording belongs to audit.
- Agent run events belong to telemetry.
- Compliance mapping belongs to docs/evidence later, not V0 code.
