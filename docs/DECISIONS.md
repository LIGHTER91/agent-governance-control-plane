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
- Minimal feature-flagged read endpoints can expose safe registry state for
  admin review without exposing plaintext keys or key hashes.
- Public registry mutation endpoints should wait for real user auth, admin
  RBAC, and a one-time-secret key lifecycle design.

Alternatives considered:
- Keep service actors permanently in environment variables.
- Implement a separate identity service.
- Add public service actor CRUD endpoints before user authentication exists.

## ADR-0008 - Policy versioning starts as a bounded snapshot aggregate

Date: 2026-06-01

Status: accepted

Context:
PolicyRules can now match contextual Runtime Gateway fields and deterministic
`check_*` CheckResult outcomes, while PolicyCheckSteps can declare evidence
collection behind a feature flag. Direct active edits can therefore affect
future runtime decisions, but AGCP does not yet have Runtime Gateway
active-version evaluation, PolicyDecision version references, real user auth,
or enterprise review workflows.

Decision:
Implement the first policy versioning foundation as a single `PolicyVersion`
aggregate that snapshots Policy fields, associated PolicyRules, and associated
PolicyCheckSteps. Lifecycle APIs cover draft, review, approval, rejection,
activation, supersession, archive, and rollback-copy. Runtime Gateway and the
policy evaluator continue to use the existing unversioned records until a
separate issue deliberately adds versioned evaluation.

Consequences:
- Policy changes become reviewable, attributable, and reversible without
  introducing a workflow engine or enterprise GRC process.
- The review/activation unit is the whole Policy bundle, which avoids
  mismatched rule/check-step activation in V1.
- Future PolicyRuleVersion and PolicyCheckStepVersion tables can still be added
  if Runtime Gateway needs granular version references.
- Existing Policy and PolicyRule edit APIs remain unblocked for now.

Alternatives considered:
- Add separate PolicyVersion, PolicyRuleVersion, and PolicyCheckStepVersion
  tables immediately.
- Change Runtime Gateway to evaluate only active versions in the same issue.
- Add enterprise approval chains or separation-of-duties workflows before real
  authentication and role modeling exist.

## ADR-0009 - PolicyVersion evidence references precede versioned evaluation

Date: 2026-06-01

Status: accepted

Context:
Before active-version evaluation landed, PolicyVersion persistence existed but
Runtime Gateway evaluated current Policy and PolicyRule rows. Evidence Bundle
needed to explain which reviewed PolicyVersion was active or relevant when a
PolicyDecision was recorded without claiming that version snapshots drove
runtime evaluation yet.

Decision:
Add a nullable direct `policy_version_id` foreign key to PolicyDecision so
runtime and evidence paths can record active PolicyVersion context when it is
known. Evidence Bundle renders compact PolicyVersion summaries on
PolicyDecision records and on CheckResult summaries through their linked
PolicyDecision. CheckResult does not get a separate version column in this
step.

Consequences:
- New evidence can point to reviewed policy configuration while historical
  PolicyDecision rows remain valid with `policy_version_id = null`.
- Runtime Gateway rule loading, rule precedence, and evaluator behavior remain
  unchanged.
- Evidence Bundle avoids full PolicyVersion snapshots and exposes only safe
  identifiers, status, activation time, and safe change summaries.
- A later active-version migration can switch evaluation to PolicyVersion
  snapshots and add granular PolicyRuleVersion or PolicyCheckStepVersion
  references deliberately.

Alternatives considered:
- Store PolicyVersion references only in CheckResult metadata.
- Add direct PolicyVersion columns to both PolicyDecision and CheckResult.
- Change Runtime Gateway to evaluate active PolicyVersion snapshots at the same
  time as adding evidence references.

## ADR-0010 - Runtime Gateway evaluates active PolicyVersion snapshots

Date: 2026-06-01

Status: accepted

Context:
PolicyVersion lifecycle, evidence references, contextual PolicyRule matching,
and `check_*` outcome matching now exist. Continuing to evaluate mutable
Policy/PolicyRule rows in Runtime Gateway would leave reviewed active versions
as evidence-only records and would not prevent direct edits from changing
future runtime behavior.

Decision:
Runtime Gateway now loads a runtime policy evaluation configuration that
prefers active PolicyVersion snapshots per Policy. When a Policy has an active
version, its immutable rule snapshots are adapted into the existing
`PolicyEvaluationRule` shape and its versioned PolicyCheckStep snapshots are
used for metadata pre-check selection when that feature flag is enabled. When a
Policy has no active version, Runtime Gateway falls back to the existing
unversioned active Policy/PolicyRule and PolicyCheckStep row behavior.

Consequences:
- PolicyDecision records from versioned Runtime Gateway matches reference the
  PolicyVersion actually used.
- Existing evaluator precedence and deterministic matching are unchanged.
- Unversioned fallback behavior remains available for policies that have not
  been migrated to active versions.
- The change does not add a generic policy engine, simulation engine,
  enterprise GRC workflow, or legal certification claim.
- Telemetry policy evaluation remains on the existing unversioned path until a
  separate migration is designed.

Alternatives considered:
- Switch all policy evaluation paths to PolicyVersion snapshots at once.
- Require every Policy to have an active version before Runtime Gateway can
  evaluate it.
- Replace the simple deterministic evaluator with a generic policy language.

## ADR-0011 - Policy folders are lightweight organization metadata

Date: 2026-07-01

Status: accepted

Context:
Policy Studio needs real repository grouping without inventing fake folders,
workspaces, sync state, or a repository abstraction that the backend does not
support. Users also need to move Policies between groups without changing
PolicyRule conditions or runtime semantics.

Decision:
Add `PolicyFolder` as a small backend-backed grouping aggregate and nullable
Policy `folder_id`. Policy folders are managed through dedicated folder APIs,
while moving a Policy is a Policy update. `folder_id = null` represents an
uncategorized Policy. Deleting a non-empty folder is blocked until Policies are
moved elsewhere.

Consequences:
- Policy Studio can show real folders and an honest Uncategorized group.
- Folder mutations and Policy moves produce append-only audit records.
- Folder membership does not affect PolicyVersion activation, runtime
  evaluation, or PolicyRule matching.
- Repository/workspace metadata remains out of scope until a separate domain
  need justifies it.

Alternatives considered:
- Keep all grouping local-only in the frontend.
- Add a broader Policy repository/workspace model before a domain need exists.
- Encode folder names in Policy tags or descriptions.
