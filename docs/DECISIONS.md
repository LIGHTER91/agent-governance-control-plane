# Architecture Decision Log

Use this file to track important project decisions.

For large decisions, create a separate ADR in `docs/adr/`.

## Decision format

```md
## ADR-000X — Title

Date: YYYY-MM-DD

Status: proposed | accepted | rejected | superseded

Context:
...

Decision:
...

Consequences:
...

Alternatives considered:
...
```

## ADR-0001 — Start with a modular monolith

Date: 2026-05-08

Status: accepted

Context:
The product domain is not mature enough to justify microservices. The first objective is to validate the governance core: registry, policies, audit logs, decisions, and evidence.

Decision:
Start with a modular monolith.

Consequences:
- Faster development.
- Simpler local setup.
- Easier testing.
- Clearer refactoring path later.
- Risk of module boundaries becoming blurry if not enforced.

Alternatives considered:
- Microservices from day one.
- Serverless architecture.
- Event-driven architecture with Kafka.

## ADR-0002 — Do not build an orchestrator

Date: 2026-05-08

Status: accepted

Context:
The project should be a governance/control-plane layer above existing agent stacks, not a replacement for execution frameworks.

Decision:
The platform will integrate with orchestrators rather than replace them.

Consequences:
- Stronger positioning.
- Lower implementation scope.
- Need for clean integration APIs.
- Need to avoid feature creep into workflow execution.
