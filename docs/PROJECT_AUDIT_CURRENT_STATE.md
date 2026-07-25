# AGCP Current-State Project Audit

Date: 2026-07-25

Scope: documentation, backlog, backend, frontend, migrations, local demo,
validation, and product-boundary review. This stabilization pass did not add
product features or redesign validated frontend surfaces.

## 1. Executive verdict

**Is AGCP close to the original product idea? Mostly.**

AGCP implements the main governance spine promised by the product idea:
registered Agents and owners, declared access and inventory, deterministic
Policies, runtime PolicyDecisions, HumanApprovals, PolicyVersion review and
activation, immutable audit records, metadata-only CheckResults, and bounded
Evidence Bundle export. The strongest frontend workflows expose that spine
without presenting AGCP as an orchestrator or legal certification product.

The qualification is important:

- **Local V1 / portfolio demo readiness:** advanced prototype. The host-side
  backend and frontend checks pass, and the deterministic seed/demo path is
  implemented. This audit could not re-run the full clean PostgreSQL/Compose
  path because the Docker daemon was unavailable, so isolated end-to-end
  validation remains pending.
- **Production / enterprise readiness:** not ready. Human identity is a local
  development abstraction, RBAC is narrow, callers must enforce `proceed`,
  there is no production adapter package, production deployment,
  observability, retention, operational runbook, enterprise directory, or
  complete Service Actor administration and rotation workflow.

Maturity summary:

| Stage | Current assessment |
| --- | --- |
| Local demo | Strong, with clean isolated PostgreSQL revalidation pending in this environment |
| Product alpha | Early alpha: the core workflows are coherent, but Agent onboarding, guided checks, identity, and integration hardening are incomplete |
| Beta | Not ready |
| Production | Not ready |
| Enterprise | Not ready |

## 2. Product promise assessment

| Area | Status | Implemented evidence | Remaining gap | Priority |
| --- | --- | --- | --- | --- |
| Know your agents | Mostly done | Agent Registry, owner/environment/status/risk fields, Agent Governance Profile, activity, approvals, Access Grants, and safe inventory references | No onboarding/edit workflow, shallow search/filtering, and limited relationship editing | P1 |
| Control risky actions | Mostly done | Deterministic PolicyRules, active PolicyVersion evaluation, Runtime Gateway decision/resume, HumanApproval, explicit reviewed activation, single-active guard, and live-edit guardrails | Caller must honor `proceed`; Access Grants are not automatic enforcement; auth/RBAC is minimal | P0/P2 |
| Prove what happened | Mostly done | Append-only AuditLog APIs, TraceEvents, PolicyDecisions, CheckResults, HumanApprovals, review/activation evidence, and bounded Evidence Bundle JSON | No PDF/signature/archive package, general evidence search, retention policy, or external GRC/SIEM export | P2 |

## 3. Backend assessment

| Area | Classification | Implemented evidence | Remaining gap or risk |
| --- | --- | --- | --- |
| Agent Registry | Mostly done | Agent model and create/list/read/update APIs; ownership, environment, status, risk, activity, approvals, and governance profile tests | Product onboarding/edit workflow is absent; list/read models remain lightweight |
| Inventories | Done for V1 scope | Capability, Source, ModelAsset, and DataUsageProfile models/APIs, safety filtering, audit events, and tests | Mutation workflows are mostly API-only; inventory is governance metadata, not a scanner or catalog |
| Access Grants | Mostly done | Create/read/update plus explicit suspend/revoke/reactivate/expire transitions, Agent-scoped reads, audit evidence, and frontend workflow | Declarative only; no automatic external IAM or Runtime Gateway enforcement |
| Policies and PolicyRules | Mostly done | Deterministic validated condition JSON, CRUD/lifecycle APIs, audit events, evaluator, contextual fields, `check_*` matching, and live-edit guard | Legacy unversioned fallback remains and can confuse source-of-truth expectations |
| PolicyVersion lifecycle | Done for V1 scope | Immutable aggregate snapshots, draft update, submit, approve/reject, explicit activation, replacement, single-active index, archive, rollback draft, audit events, and tests | Historical PolicyDecision backfill decision remains unresolved; DSL source storage is intentionally secondary |
| Policy review workflow | Done for V1 scope | Dedicated PolicyVersionReviewRequest, duplicate-pending guard, reviewer assignment, approve/reject, safe diff, explicit activation, and current-actor checks | No reviewer directory, notifications, request-info, unassign, or enterprise separation of duties |
| Runtime Gateway | Mostly done | Simulation/enforcement contracts, idempotency, safe context resolution, deterministic decisions, HumanApproval creation, resume, activity, failure strategy, and tests | AGCP never executes tools; reliable enforcement depends on every caller honoring `proceed` |
| Telemetry | Mostly done | Idempotent ingestion, AgentRun/TraceEvent persistence, shared active-version loader, PolicyDecision/HumanApproval creation, and tests | It remains a separate ingestion path and has no production ingestion/operations package |
| Metadata pre-checks | Mostly done | CheckTool/CheckResult persistence, metadata-only adapter boundary, feature-flagged PolicyCheckStep execution, `check_*` evaluation, evidence summaries, seed/demo, and tests | Guided PolicyCheckStep authoring is absent; failure behavior is evidence intent, not automatic enforcement; no scanners |
| HumanApproval | Mostly done | Explicit pending/approve/reject/cancel lifecycle, RBAC checks, runtime linkage, audit evidence, frontend review actions, and tests | Runtime assignment, request-info, notification, expiry automation, and enterprise identity are missing |
| Evidence Bundle | Mostly done | Safe Agent-scoped JSON containing audit, runs, traces, decisions, approvals, grants, inventories, DataUsageProfiles, CheckResults, and PolicyVersion references | JSON-only; no signing, PDF, archive, retention, or broad evidence index |
| AuditLog | Done as a foundation | Append-only public behavior, mutation events, review/activation events, export/denial events, metadata safety, and tests | No retention/archive strategy, tamper-evident signing, or external export pipeline |
| Authentication/RBAC | Risky | Local ActorContext, selected human role checks, config Service Actor keys/scopes, strict mode, and optional DB registry | No login, OIDC/SAML/JWT, persisted users/roles/teams, broad authorization model, or enterprise directory |
| Service Actors | Partial | Config auth, endpoint and fine-grained scopes, optional DB-backed registry, hashed key metadata, read-only admin APIs, and seed helpers | Registry is disabled by default; no public mutation workflow, rotation endpoints, owner restrictions, or complete denied-scope audit |
| Migrations | Mostly done; online validation pending | One linear Alembic chain through `202607010001`; offline PostgreSQL SQL generation passed | Empty-database online upgrade was not revalidated because Docker was unavailable |
| Local demo | Mostly done; clean validation pending | Deterministic seed, first-class `--print-runtime-payload`, one-command metadata pre-check demo, and focused seed tests | Full clean Compose/PostgreSQL/API/web run could not execute in this audit environment |

No backend area is classified as Overbuilt, but the policy/version/check
surface is now mature enough that workflow depth, identity, adapters, and
operations should take precedence over adding more domain objects.

## 4. Frontend assessment

Host validation passed `npm run check`, `npm run build`, and the standalone
smoke suite. Rendered browser validation against the isolated stack was not
possible because Docker was unavailable.

| Surface | Classification | Validated implementation | Remaining workflow gap |
| --- | --- | --- | --- |
| Overview | Mostly done | Connected narrative for know/control/prove, current actor, Agents, reviews, Policies, and Runtime activity with honest empty/error states | Operating summaries remain lightweight; no broad search or evidence index |
| Agents | Partial | Backend-backed Agent list and Governance Profile detail with activity, approvals, grants, inventory refs, and manual evidence action | Read-only; no register/edit/governance relationship workflow |
| Policy Studio | Done for V1 authoring | Preserved IDE layout, backend folders, Blocks/Code DSL synchronization, local compile validation, draft/review/activation, rollback, archive, and guarded delete | No guided PolicyCheckStep persistence, limited operator persistence/version browsing |
| Human Approval Studio | Mostly done | Unified Runtime HumanApproval and PolicyVersion review work items, assignment for policy reviews, approve/reject, diff/evidence, explicit activation, and role-aware hints | Request-info, runtime assignment, notifications, reviewer directory, and enterprise identity are absent |
| Runtime Decisions | Mostly done | Backend-backed decision/activity timeline with PolicyVersion/fallback context, checks, approvals, and evidence links; no fake simulation | Detail, filtering, pagination, and CheckResult drill-down remain lightweight |
| Evidence & Audit | Mostly done for V1 | Consolidated manual Evidence Bundle explorer with Subject, Policy Decision, CheckResults, Human Review, Policy Review, Audit Trail, and bounded JSON download | No general audit/evidence list, PDF/signing, retention, or external export |
| Access & Data | Mostly done | Workflow-first Source/DataUsageProfile/AccessGrant/Model/Capability review, readiness, safe metadata, and grant lifecycle transitions | No guided check authoring, grant approval workflow, or automatic enforcement |
| Integrations | Partial | Honest Integration Hub guidance and optional read-only Service Actor registry summary | No production adapter package, setup verification, key management, or caller-enforcement test harness |
| Settings/Admin | Missing as a product workflow | Honest placeholder only | Enterprise identity, users/teams/roles, Service Actor mutation/rotation, and operational settings |

Disproportionately mature surfaces are Policy Studio and the policy review
half of Human Approval Studio. The weakest product workflows are Agents and
Settings/Admin. The standalone `/audit` route is a placeholder; the real V1
audit workflow lives in Evidence & Audit. Agents is backend-backed but still
closer to a record viewer than a complete workflow. Integration Hub is guidance
rather than an operational integration surface. These limitations are honest
and preferable to fake enterprise functionality.

## 5. Documentation assessment

Accurate after this stabilization pass:

- `README.md`;
- `apps/api/README.md`;
- `apps/web/README.md`;
- `docs/ROADMAP.md`;
- `docs/TASKS.md`;
- `docs/FRONTEND_PRODUCT_BLUEPRINT.md`;
- `docs/DOMAIN_MODEL.md`;
- `docs/CONTEXTUAL_RUNTIME_GOVERNANCE_DESIGN.md`;
- `docs/POLICY_STUDIO_DSL_DESIGN.md`;
- `docs/POLICY_PRE_CHECKS_DESIGN.md`;
- `docs/POLICY_CHECK_STEP_AUTHORING_DESIGN.md`;
- `docs/POLICY_VERSIONING_REVIEW_DESIGN.md`;
- `docs/POLICY_VERSION_ACTIVE_ROLLOUT.md` for the unresolved historical
  backfill decision;
- `docs/POLICY_STUDIO_ISSUE_ALIGNMENT.md`;
- `docs/issues/README.md`.

Contradictory statements corrected in this pass:

- “V0 backend only” was replaced by the local V1 / advanced prototype
  maturity statement.
- Policy review UI, assignment, diff, activation, rollback, and live-edit
  guardrails are no longer listed as missing design work.
- Runtime Decisions and Evidence & Audit are no longer described as placeholder
  or future consolidation work.
- The Overview, Access & Data, backend Policy folders, Policy Canvas, metadata
  pre-check demo, and Human Approval Studio are marked implemented.
- Runtime context, DataUsageProfile resolution, telemetry active-version use,
  and CHECK-versus-PolicyCheckStep frontend behavior now match the code.

Stale as current-status sources, retained as history:

- `docs/V0_GOVERNANCE_FLOW.md` describes the original executable V0 slice, not
  current product maturity.
- Individual `docs/issues/*.md` files preserve seed-issue history and do not
  track the complete current implementation or remote GitHub state.

Merge/archive candidates:

- keep design documents focused on durable contracts and move implementation
  status into this audit, `ROADMAP.md`, and `TASKS.md`;
- keep the V0 flow and numbered issue documents in a clearly historical
  archive/navigation section;
- avoid duplicating long status narratives across the three README files.

## 6. Test and validation assessment

| Check | Result |
| --- | --- |
| Backend tests | Passed: 1,099 tests |
| Ruff lint | Passed |
| Ruff format check | Passed: 137 files already formatted |
| Alembic offline PostgreSQL SQL generation | Passed through head `202607010001` |
| Alembic online empty PostgreSQL upgrade | Not run: Docker daemon unavailable |
| Frontend `npm run check` | Passed: TypeScript plus smoke |
| Frontend production build | Passed: all 13 app routes generated/compiled |
| Frontend standalone smoke | Passed |
| Compose config | Passed |
| Isolated `scripts/validate-clean.ps1` | Safely stopped before mutation: Docker daemon unavailable |
| Docker stack and metadata demo | Not run in this audit environment |
| Browser/E2E | Missing; isolated rendered flow could not run without Docker |

Backend coverage is broad across models, APIs, RBAC, metadata safety, runtime,
telemetry, PolicyVersion review, evidence, and deterministic demo seeding.
Frontend smoke protects important copy, endpoint, policy, evidence, and
no-fake-feature boundaries. The main quality gap is browser E2E for the actual
Agent -> Policy -> Runtime Decision -> CheckResult -> HumanApproval ->
activation -> Evidence Bundle workflow.

## 7. Top risks

1. **Minimal authentication/RBAC.** Local ActorContext and narrow role checks
   are insufficient for enterprise identity and separation of duties.
2. **Caller responsibility for honoring `proceed`.** AGCP records the decision;
   a faulty integration can still execute a denied or review-gated action.
3. **Agent workflow depth.** The central “know your agents” promise lacks
   onboarding, editing, and governed relationship authoring.
4. **PolicyCheckStep authoring gap.** Runtime execution and evidence exist, but
   non-developers cannot author real persisted steps in Policy Studio.
5. **Legacy unversioned Policy fallback.** Necessary compatibility behavior
   creates two possible policy sources of truth.
6. **Documentation drift.** Status-heavy design documents have contradicted
   implemented behavior and can misdirect work.
7. **Production deployment and observability.** There is no production
   deployment target, metrics/logging runbook, retention plan, backup plan, or
   operational incident procedure.
8. **Service Actor rotation/admin gaps.** Registry mutation, rotation,
   ownership restrictions, and complete audit workflows are absent.
9. **Historical PolicyDecision backfill decision.** Nullable historical
   version references are honest, but the long-term evidence policy is
   unresolved.
10. **No production adapter package.** Integration Hub and examples do not yet
    provide a supported Python/LangGraph enforcement boundary with failure,
    timeout, idempotency, and resume tests.

## 8. Recommended roadmap

### P0 — stabilize before public demonstration

| Task | Reason | Areas | Effort | Dependencies |
| --- | --- | --- | --- | --- |
| Run `scripts/validate-clean.ps1` with Docker available and record the result | Proves empty PostgreSQL migration, API, seed, pre-check, evidence, and cleanup behavior | Tests/docs | Small | Docker Desktop |
| Add one clean browser E2E governance flow | Static checks do not prove the hero workflows render and interact together | Frontend/tests | Medium | Passing clean stack |
| Resolve the remaining out-of-scope status contradictions listed above | Keeps one current source of truth and prevents obsolete issue work | Docs | Small | This audit |

### P1 — strengthen product alpha

| Task | Reason | Areas | Effort | Dependencies |
| --- | --- | --- | --- | --- |
| Agent onboarding and governance editing workflow | Completes the weakest part of “know your agents” | Frontend/backend/tests/docs | Medium | Current Agent/inventory APIs |
| Guided PolicyCheckStep authoring in Policy Studio | Makes implemented metadata pre-checks usable without seed scripts or raw API calls | Frontend/backend/tests/docs | Large | PolicyVersion snapshot compatibility and current Policy Studio UX |
| Production-quality Python/LangGraph runtime adapter | Reduces the risk that callers ignore `proceed` and proves timeout/idempotency/resume behavior | Package/backend/tests/docs | Large | Stable Runtime Gateway and Service Actor contract |

### P2 — beta preparation

| Task | Reason | Areas | Effort | Dependencies |
| --- | --- | --- | --- | --- |
| Identity, RBAC, and separation-of-duties hardening | Required for credible multi-user review and activation | Backend/frontend/security/tests/docs | Large | Enterprise auth design choice |
| Service Actor administration and key rotation | Required for managed production integrations | Backend/frontend/tests/docs | Large | Identity/admin authorization |
| Decide historical PolicyDecision backfill policy | Clarifies historical evidence without inventing provenance | Backend/docs/tests | Medium | Production evidence requirements |
| Evidence package and retention design | JSON alone is insufficient for many audit workflows | Backend/frontend/docs/tests | Large | Identity, storage, retention requirements |

### P3 — enterprise/later

| Task | Reason | Areas | Effort | Dependencies |
| --- | --- | --- | --- | --- |
| Production deployment, observability, backup, and incident runbooks | Required for supported operations | Platform/backend/docs/tests | Large | Beta architecture and security decisions |
| Enterprise directories and team/org ownership resolution | Enables durable owner- and role-based authorization | Backend/frontend/security | Large | Identity foundation |
| SIEM/GRC and additional runtime integrations | Extends evidence and runtime reach after the core is supportable | Integrations/docs/tests | Large | Adapter, auth, and evidence contracts |

## 9. Exact next three implementation tasks

Based on the verified gaps, not on model expansion:

1. Agent onboarding and governance editing workflow.
2. Guided PolicyCheckStep authoring in Policy Studio.
3. One production-quality Python/LangGraph Runtime Gateway adapter.

Identity/RBAC remains the highest production risk, but the three tasks above
are the most focused continuation of the current product alpha. Identity and
separation-of-duties hardening is the first beta-preparation program and must
precede enterprise deployment.
