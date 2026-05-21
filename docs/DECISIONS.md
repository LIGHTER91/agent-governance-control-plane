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

## ADR-0003 - Backend toolchain baseline

Date: 2026-05-13

Status: accepted

Context:
Implementation readiness requires concrete backend tooling decisions before Codex starts adding application code. The stack should stay boring, testable, and aligned with the modular monolith architecture.

Decision:
Use Python 3.11, uv for dependency management, FastAPI for the backend API, Pydantic v2 for validation, SQLAlchemy 2.x for ORM/persistence, Alembic for migrations, pytest for tests, ruff for linting and formatting, and PostgreSQL as the primary database.

Consequences:
- Backend issues can specify exact tooling instead of reopening stack choices.
- CI can be introduced early with deterministic commands.
- The project avoids SQLModel ambiguity for the initial implementation.
- Dependencies should still be added only by the issue that first needs them.

Alternatives considered:
- SQLModel instead of SQLAlchemy 2.x.
- Poetry or pip-tools instead of uv.
- Leaving Python and dependency versions unspecified until implementation.

## ADR-0004 - Internal packages within a modular monolith

Date: 2026-05-13

Status: accepted

Context:
The repository contains `apps/*` and `packages/*`, which could be mistaken for independently deployed services or future microservices.

Decision:
`packages/*` are internal Python packages/modules used by the backend. They are not independently deployed services. The architecture remains a modular monolith until a human explicitly changes that decision.

Consequences:
- Module boundaries can be expressed in code without introducing service boundaries.
- Local development and CI stay simple.
- Cross-package imports should preserve domain boundaries instead of creating a distributed architecture.

Alternatives considered:
- Treat each package as a deployable service.
- Collapse all code into `apps/api`.

## ADR-0005 - Audit actor placeholders before authentication

Date: 2026-05-13

Status: accepted

Context:
Audit logs need a stable actor model before full authentication exists. Using a vague actor placeholder would create migration pain or inconsistent evidence later.

Decision:
AuditLog must include `actor_type` and `actor_id` from the start. Before full authentication, use a system actor or development actor placeholder, such as `actor_type=system` with `actor_id=system`, or `actor_type=development` with a local developer identifier. Later authentication can replace placeholders without changing the AuditLog model.

Consequences:
- Audit records remain structurally consistent from the first implementation.
- Early APIs can be built without full auth while still preserving audit semantics.
- Tests can assert that audit records always include actor fields.

Alternatives considered:
- Omit actor fields until authentication exists.
- Store only a free-form actor string.
- Implement full authentication before the audit model.

## ADR-0006 - Agent owner identity convention

Date: 2026-05-15

Status: accepted

Context:
Agent ownership must support users, teams, services, and organizational units without treating email as the primary identity. The owner identifier should be stable enough to survive later authentication or identity-provider integration.

Decision:
Use `owner_type` and `owner_id` together as the owner identity convention:

- `owner_type = "user"` -> `owner_id = "user:<external-id>"`;
- `owner_type = "team"` -> `owner_id = "team:<slug>"`;
- `owner_type = "service"` -> `owner_id = "service:<slug>"`;
- `owner_type = "organization_unit"` -> `owner_id = "org_unit:<slug>"`.

Consequences:
- Email remains a contact field, not a primary owner identifier.
- Future identity integration can map external identities into stable owner IDs.
- Agent ownership can represent non-human owners without adding user, team, service, or organization-unit tables yet.

Alternatives considered:
- Use email as the primary owner identifier.
- Store only a free-form owner string.
- Add full identity tables before the Agent model.

## ADR-0007 - Service actor registry as internal control-plane state

Date: 2026-05-21

Status: accepted

Context:
Runtime and telemetry integrations need stable service actor identities, API key
rotation, endpoint/action scopes, and fine-grained restrictions. The current
configuration-based service actor authentication is useful for V0, but it is
not a production-grade source of truth.

Decision:
Design a future database-backed service actor registry inside the existing
modular monolith. The registry will persist service actor identities, API key
metadata, hashed key material, lifecycle state, endpoint/action scopes, and
fine-grained rules. It will not become an identity provider, workflow engine, or
new service boundary.

Consequences:
- Service actor identity remains stable as `actor_type = "service"` and
  `actor_id = "service:<stable-id>"`.
- API key rotation can change credentials without changing governance evidence
  identity.
- Registry mutations must append safe AuditLog events.
- Public registry management endpoints should wait for real user auth and admin
  RBAC.

Alternatives considered:
- Keep service actors permanently in environment variables.
- Implement a separate identity service.
- Add public service actor CRUD endpoints before user authentication exists.
