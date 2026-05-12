# Architecture Principles

## 1. Start as a modular monolith

A modular monolith is preferred because the domain is still evolving.

Avoid microservices until boundaries are proven.

## 2. Domain model before UI

The value is not the dashboard first.

The value is:

- explicit agents;
- explicit permissions;
- explicit policies;
- explicit policy decisions;
- immutable audit logs;
- traceable evidence.

## 3. Policy decisions must be explainable

Every policy decision should answer:

- what was evaluated;
- which policy/rule was applied;
- what decision was returned;
- when;
- for which agent;
- with what context;
- whether a human review was required.

## 4. Audit logs are append-only

Public APIs must not allow editing or deleting audit records.

## 5. Avoid compliance claims in code

Do not encode labels such as:

```text
is_ai_act_compliant = true
iso_42001_certified = true
compliance_score = 98
```

Use neutral evidence/control fields instead.

## 6. Standards-compatible telemetry

Prefer event schemas that can later map to OpenTelemetry-style traces.

Do not overfit to one framework.

## 7. Integration-friendly by design

The product should be usable with external agent frameworks.

Initial integrations should be minimal:

- generic HTTP event ingestion;
- later SDK/middleware;
- later framework-specific adapters.

## 8. Security from the start

Secrets must not appear in:

- code;
- logs;
- tests;
- fixtures;
- audit records;
- examples.

## 9. Human review remains final

For governance-sensitive decisions, the system should support human oversight.

Do not pretend automated checks solve governance alone.

## 10. Boring infrastructure first

Use simple proven components:

- PostgreSQL;
- FastAPI;
- pytest;
- Docker Compose;
- JSON evidence exports.

Avoid fashionable infrastructure until it solves a real problem.
