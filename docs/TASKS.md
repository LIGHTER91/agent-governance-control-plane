# AGCP Tasks

This is the repository-level task tracker. GitHub Issues should hold individual
implementation discussions. Current maturity and prioritization are documented
in `docs/PROJECT_AUDIT_CURRENT_STATE.md` and `docs/ROADMAP.md`.

## Current milestone

**P0 project stabilization — implementation complete, clean validation
pending.**

This pass:

- aligned current-state documentation with verified code;
- replaced the obsolete “V0 backend only” maturity statement with
  “local V1 / advanced product prototype”;
- consolidated the roadmap and removed completed feature work from the active
  backlog;
- prepared exact GitHub issue cleanup for #56 and #57;
- added isolated validation tooling without changing product semantics.

The full isolated PostgreSQL run remains pending because Docker was unavailable
in the audit environment. No normal AGCP Compose project, container, or volume
was changed.

## Validation record — 2026-07-25

| Check | Status |
| --- | --- |
| `cd apps/api && uv run pytest` | Passed: 1,099 tests |
| `cd apps/api && uv run ruff check .` | Passed |
| `cd apps/api && uv run ruff format --check .` | Passed: 137 files |
| `cd apps/api && uv run alembic upgrade head --sql` | Passed through `202607010001` |
| `cd apps/web && npm run check` | Passed |
| `cd apps/web && npm run build` | Passed: 14 app routes, including Agent register/edit |
| `cd apps/web && npm run smoke` | Passed standalone |
| `docker compose -f compose.dev.yml config` | Passed |
| `scripts/validate-clean.ps1` | Not run past prerequisites: Docker daemon unavailable |
| Online empty PostgreSQL migration | Pending with clean validation |
| Focused Agent workflow browser QA | Passed at 1440x900, 1024x768, and 390x844; tablet compression fixed and rechecked |
| Backend-backed Agent create/edit browser flow | Pending: Docker daemon unavailable |
| Full browser/E2E governance flow | Pending |

## Implemented product foundation

### Agent, inventory, and access

- [x] Agent Registry and ownership model.
- [x] Agent activity and Agent Governance Profile read model/UI.
- [x] Five-step Agent registration and governance editing workflow using real
      backend enums and inventory, with sequential `pending_review` Access
      Grant creation and honest partial-failure retry.
- [x] Capability, Source, ModelAsset, and DataUsageProfile inventory APIs.
- [x] AccessGrant API, Agent-scoped reads, audit events, and explicit lifecycle
      transitions.
- [x] Access & Data workflow with safe metadata and no scanner, IAM, or legal
      certification claims.

### Policy and review

- [x] Deterministic Policy and PolicyRule persistence, APIs, evaluator, audit,
      contextual fields, and safe CheckResult matching.
- [x] Backend-backed Policy folders.
- [x] Policy Studio V1 with repository sidebar, center editor,
      `WHEN -> CHECK -> THEN -> PROVE`, Blocks/Code DSL synchronization,
      compile bar, local validation console, and right inspector.
- [x] PolicyVersion draft snapshots and immutable pending-review behavior.
- [x] Dedicated PolicyVersionReviewRequest creation, assignment,
      approve/reject, deterministic diff, and explicit activation.
- [x] Single-active PolicyVersion guard, replacement, rollback draft,
      non-destructive archive, guarded draft delete, and live-edit guardrails.
- [x] Human Approval Studio for Runtime HumanApproval and PolicyVersion review
      work items inside the preserved AGCP shell.

### Runtime, telemetry, checks, and evidence

- [x] Runtime Gateway decision, resume, activity, idempotency, simulation, and
      opt-in enforcement contracts.
- [x] Telemetry ingestion with the shared active PolicyVersion loader and
      unversioned fallback.
- [x] Metadata-only CheckTool adapter boundary.
- [x] PolicyCheckStep persistence and API.
- [x] Feature-flagged runtime PolicyCheckStep execution with CheckResult
      evidence and explicit `check_*` PolicyRule matching.
- [x] Runtime Decisions workflow.
- [x] Append-only AuditLog foundation and bounded Evidence Bundle JSON.
- [x] Consolidated Evidence & Audit explorer.
- [x] Deterministic seed and one-command metadata pre-check demo.

### Identity and integrations foundation

- [x] Local ActorContext and `/me`.
- [x] Narrow HumanApproval, policy review, Runtime activity, and Evidence
      Bundle authorization checks.
- [x] Config Service Actor API keys, endpoint scopes, strict mode, and
      fine-grained scope rules.
- [x] Optional DB Service Actor registry, persisted scopes/rules, read-only
      admin APIs, and seed/import helpers.
- [x] Integration Hub guidance that preserves the non-orchestrator boundary.

## Implementation complete — validation pending

The following items are implemented and covered by unit/API/static checks, but
must not be marked fully validated until `scripts/validate-clean.ps1` passes
against an empty PostgreSQL volume:

- [ ] Full online Alembic chain through Policy folders.
- [ ] DB-backed Service Actor registry, key, scope, and fine-grained rule
      migrations.
- [ ] DataUsageProfile, CheckTool, CheckResult, and PolicyCheckStep migrations.
- [ ] PolicyVersion, PolicyDecision version reference, single-active guard, and
      PolicyVersionReviewRequest migrations.
- [ ] Isolated Compose bootstrap, seed, Runtime Gateway metadata pre-check,
      Evidence Bundle verification, frontend smoke, and project-scoped cleanup.

Validation command:

```powershell
.\scripts\validate-clean.ps1
```

Use `-KeepRunning` only for intentional browser inspection. The script uses the
`agcp-clean-validation` Compose project and dedicated default host ports. It
must never remove the normal development project or its volumes.

## P0 — stabilize before public demonstration

- [ ] Run and record clean isolated PostgreSQL validation with Docker available.
- [ ] Add one browser E2E governance flow covering Agent, Policy, Runtime
      Decision, CheckResults, HumanApproval, activation, and Evidence Bundle.
- [ ] Refresh the remaining out-of-scope status contradictions identified in
      `docs/PROJECT_AUDIT_CURRENT_STATE.md`.
- [ ] Apply the prepared GitHub issue cleanup in
      `docs/GITHUB_BACKLOG_CLEANUP.md` when authenticated `gh` access is
      available.

## P1 — strengthen product alpha

- [x] Agent onboarding and governance editing workflow.
- [ ] Guided PolicyCheckStep authoring in Policy Studio with PolicyVersion
      snapshot compatibility.
- [ ] Production-quality Python/LangGraph Runtime Gateway adapter with
      mandatory `proceed` enforcement, idempotency, timeouts, failure policy,
      resume, fake-tool tests, and documentation.

## P2 — beta preparation

- [ ] Real user identity, authentication, RBAC, and separation of duties.
- [ ] Enterprise user/team/org ownership resolution.
- [ ] Service Actor mutation/admin workflow and API key rotation.
- [ ] Decide historical PolicyDecision backfill behavior.
- [ ] Evidence package/signing/retention design and implementation.
- [ ] Filtering/pagination and stronger operational read models where required
      by browser workflows.

## P3 — enterprise/later

- [ ] Production deployment and operational runbooks.
- [ ] Observability, backup/recovery, retention enforcement, and incident
      operations.
- [ ] SIEM/GRC evidence integrations.
- [ ] Additional runtime/framework adapters after the first supported adapter
      contract is proven.

## Explicitly not planned as shortcuts

- No AGCP orchestration or tool execution.
- No fake data, production metrics, scanners, reviewers, or simulations.
- No Publish action or automatic activation.
- No automatic AccessGrant/IAM enforcement without explicit policy semantics.
- No legal certification or compliance/risk/trust score.
- No production claim based only on local tests.

## Completion rule

A task moves to done only when:

- implementation is complete and scoped;
- tests are added or updated where relevant;
- relevant checks pass;
- migration-backed work passes online against PostgreSQL;
- frontend work preserves the approved workflow-first UX;
- remaining risks and limitations are recorded.

If required validation cannot run because tooling or services are unavailable,
the status is **Implementation complete — validation pending**.
