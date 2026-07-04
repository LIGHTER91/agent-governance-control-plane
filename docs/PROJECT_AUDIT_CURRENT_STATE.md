# AGCP Current State Project Audit

Date: 2026-07-04

Scope: product idea, roadmap, docs, backend, frontend, dev/demo stack, tests,
and safety posture. This is an audit only; it does not implement fixes or
change production code.

## 1. Executive Summary

- Verdict: **Mostly close to the original AGCP idea**, but still an early
  governance control plane rather than a production-ready enterprise platform.
- The strongest product spine is intact: AGCP helps teams **know agents**,
  **control risky actions**, and **prove what happened** through Agent records,
  Runtime Gateway decisions, HumanApprovals, PolicyVersions, AuditLogs, and
  Evidence Bundles.
- The backend is broader and more coherent than a V0 logger. It has Agent
  Registry, Access/Data inventory, Policy and PolicyVersion lifecycle,
  Runtime Gateway, metadata-only CheckResults, review workflows, and bounded
  evidence export.
- The frontend is now mostly workflow-first. Policy Studio and Human Approval
  Studio are the strongest validated product surfaces. Runtime Decisions,
  Evidence & Audit, Access & Data, and Agent detail are useful but still less
  complete.
- The project has avoided the biggest product-boundary failures: it does not
  execute tools, does not claim legal compliance certification, avoids Publish
  semantics, and repeatedly states that callers must honor `proceed`.
- The biggest backend gap is **identity/auth/RBAC maturity**. Current human
  actor behavior is local-development oriented; enterprise auth, team/org
  resolution, service actor management, and key rotation remain incomplete.
- The biggest frontend risk is technical debt in the shell: [AGCPStudio.tsx](../apps/web/app/agcp-studio/AGCPStudio.tsx)
  is extremely large, mixes shell, legacy prototype data, global CSS, route
  styling, and product logic, and still contains stale prototype copy such as
  `AI Act / ISO`.
- The biggest product risk is over-expanding inventory and policy machinery
  before the review, activation, evidence, and auth workflows become
  operationally mature.
- Testing is strong at backend API/unit level and useful at frontend smoke
  level, but there is little browser/E2E coverage for the real human workflows.
- Documentation is unusually complete, but some docs are now status-heavy,
  partially stale, or internally contradictory about what is "design only" vs
  implemented.

## 2. Product Alignment Verdict

| Area | Verdict | Evidence | Gap | Priority |
| --- | --- | --- | --- | --- |
| Know your agents | Mostly done | `Agent`, owner fields, activity, approvals, governance profile in [models.py](../apps/api/src/agent_governance_api/models.py), [governance_profile.py](../apps/api/src/agent_governance_api/governance_profile.py), [agent-detail.tsx](../apps/web/app/agents/[agentId]/agent-detail.tsx) | No onboarding/edit workflow, limited filtering and relationships | P1 |
| Control risky actions | Mostly done | Runtime Gateway decision/resume APIs in [runtime_gateway_api.py](../apps/api/src/agent_governance_api/runtime_gateway_api.py), HumanApproval APIs, PolicyVersion activation | Enforcement depends on wrappers; Access Grants are context only; auth is local/minimal | P0/P1 |
| Prove what happened | Mostly done | Evidence Bundle builder in [evidence.py](../apps/api/src/agent_governance_api/evidence.py), audit logs, CheckResult summaries, JSON download UI | No PDF/signature, limited evidence search/listing, no retention story | P1 |
| Governance control plane boundary | Strong | Docs and UI repeatedly say AGCP does not execute tools and does not replace orchestrators | Integration Hub is guidance only; future adapter work could blur boundary | P1 |
| Not legal certification | Mostly strong | Smoke tests forbid compliance-score/certification phrases; Evidence page says no legal certification | Legacy `AI Act / ISO` copy remains in [AGCPStudio.tsx](../apps/web/app/agcp-studio/AGCPStudio.tsx) prototype data | P0 |
| Workflow-first UX | Mostly done | Policy Studio IDE, Human Approval Studio, Runtime Decisions timeline, Access & Data workspace | Agents and Settings are still thin; global CSS makes regressions likely | P1 |
| No fake data | Mostly done | Frontend calls real endpoints and uses honest empty states; demo seed creates backend records | Static templates/prototype constants remain in shell and must stay clearly non-runtime | P1 |

## 3. Backend Audit

### Agent Registry

| Classification | Evidence | Notes |
| --- | --- | --- |
| Mostly done | [agents.py](../apps/api/src/agent_governance_api/agents.py), `Agent` model in [models.py](../apps/api/src/agent_governance_api/models.py), [test_agent_registry_api.py](../apps/api/tests/test_agent_registry_api.py) | Agent identity, owner, environment, status, risk, activity, approvals, and profile read model exist. Missing product workflows are edit/onboarding, stronger search/filtering, and deeper relationship navigation. |

### Policies / PolicyRules

| Classification | Evidence | Notes |
| --- | --- | --- |
| Mostly done, with legacy risk | [policies.py](../apps/api/src/agent_governance_api/policies.py), [policy_rules.py](../apps/api/src/agent_governance_api/policy_rules.py), [policy_live_edit_guard.py](../apps/api/src/agent_governance_api/policy_live_edit_guard.py), [policy_evaluator.py](../apps/api/src/agent_governance_api/policy_evaluator.py) | Deterministic condition model is aligned with the product boundary. Live Policy/PolicyRule endpoints remain necessary for bootstrap/fallback, but they are a long-term confusion risk. Active-version live-edit blocking is a good guardrail. |

### PolicyVersion Lifecycle

| Classification | Evidence | Notes |
| --- | --- | --- |
| Mostly done | [policy_versions.py](../apps/api/src/agent_governance_api/policy_versions.py), [policy_version_review_requests.py](../apps/api/src/agent_governance_api/policy_version_review_requests.py), migrations `202606010001`, `202606090001`, tests in [test_policy_versions_api.py](../apps/api/tests/test_policy_versions_api.py) | Draft, review, approval, activation, replacement, rollback draft, archive, and single-active guard exist. Remaining issue is historical PolicyDecision backfill strategy and possible DSL source storage. |

### Review Workflow

| Classification | Evidence | Notes |
| --- | --- | --- |
| Mostly done for V1 | Runtime HumanApproval in [human_approvals.py](../apps/api/src/agent_governance_api/human_approvals.py); policy reviews in [policy_version_review_requests.py](../apps/api/src/agent_governance_api/policy_version_review_requests.py) | Runtime HumanApproval and PolicyVersionReviewRequest are correctly separate. Reviewer assignment exists for policy reviews. Missing: notifications, request-info, runtime assignment, real reviewer directory, enterprise identity, richer separation of duties. |

### Runtime Gateway

| Classification | Evidence | Notes |
| --- | --- | --- |
| Strong foundation, not production-ready | [runtime_gateway_api.py](../apps/api/src/agent_governance_api/runtime_gateway_api.py), [runtime_gateway.py](../apps/api/src/agent_governance_api/runtime_gateway.py), [test_runtime_gateway_api.py](../apps/api/tests/test_runtime_gateway_api.py) | Simulation/enforcement modes, idempotency, resume, active PolicyVersion loader, service actor scopes, and failure behavior are covered. The production weakness is external: wrappers/adapters must consistently call AGCP and honor `proceed`. |

### Metadata Pre-checks

| Classification | Evidence | Notes |
| --- | --- | --- |
| Partial but well bounded | [check_tools.py](../apps/api/src/agent_governance_api/check_tools.py), [runtime_metadata_pre_checks.py](../apps/api/src/agent_governance_api/runtime_metadata_pre_checks.py), [policy_pre_checks.py](../apps/api/src/agent_governance_api/policy_pre_checks.py) | Metadata-only checks are safe and useful. They do not scan raw content, do not auto-enforce `failure_behavior`, and affect decisions only through explicit `check_*` PolicyRule matching. Missing: PolicyCheckStep UI, async/external checker design implementation, public CheckTool/CheckResult management if needed. |

### Evidence Bundle

| Classification | Evidence | Notes |
| --- | --- | --- |
| Mostly done | [evidence.py](../apps/api/src/agent_governance_api/evidence.py), [metadata_safety.py](../apps/api/src/agent_governance_api/metadata_safety.py), [test_evidence_bundle_api.py](../apps/api/tests/test_evidence_bundle_api.py) | Bounded JSON export includes agent, runs, trace events, decisions, approvals, access grants, inventory refs, DataUsageProfile summaries, CheckResults, and safe PolicyVersion references. Missing: PDF/signature/archive, broader evidence search, retention. |

### Access/Data Inventory

| Classification | Evidence | Notes |
| --- | --- | --- |
| Mostly done as governance metadata | [access_grants.py](../apps/api/src/agent_governance_api/access_grants.py), [sources.py](../apps/api/src/agent_governance_api/sources.py), [model_assets.py](../apps/api/src/agent_governance_api/model_assets.py), [capabilities.py](../apps/api/src/agent_governance_api/capabilities.py) | Inventory, DataUsageProfile, and AccessGrant lifecycle are coherent. The UI correctly states these are not IAM credentials. Missing: deeper approval workflows and runtime enforcement semantics if product requires them. |

### Dev Stack / Demo

| Classification | Evidence | Notes |
| --- | --- | --- |
| Strong local demo | [compose.dev.yml](../compose.dev.yml), [scripts/dev-demo.ps1](../scripts/dev-demo.ps1), [seed_full_stack_demo.py](../apps/api/scripts/seed_full_stack_demo.py), [full_stack_demo_seed.py](../apps/api/src/agent_governance_api/full_stack_demo_seed.py) | The demo is honest because it seeds real backend records and calls Runtime Gateway to create CheckResults. Risk: local compose defaults grant `Local Admin` broad roles, which is fine for dev but must stay visibly dev-only. |

### Security/RBAC

| Classification | Evidence | Notes |
| --- | --- | --- |
| Partial / risky for production | [auth.py](../apps/api/src/agent_governance_api/auth.py), [service_actor_registry.py](../apps/api/src/agent_governance_api/service_actor_registry.py), tests in [test_auth.py](../apps/api/tests/test_auth.py) | Service actor API key auth and scopes are meaningful. Human role checks exist for selected read/review/export paths. Missing: user login, OIDC/SAML/JWT, team/org ownership resolver, role persistence, service actor mutation admin, key rotation, owner-based service actor restrictions, denied-scope audit events. |

## 4. Frontend Audit

### Overview

- Verdict: **Mostly aligned**.
- Evidence: [page.tsx](../apps/web/app/page.tsx) mounts `AGCPStudioDashboard`;
  [AGCPStudio.tsx](../apps/web/app/agcp-studio/AGCPStudio.tsx) fetches real
  current actor, agents, approvals, policies, policy reviews, and runtime
  activity.
- Strength: explains know/control/prove and uses honest unavailable states.
- Gap: still lives inside a huge shell file with legacy static prototype
  constants, which increases copy/regression risk.

### Agents

- Verdict: **Partial to mostly done**.
- Evidence: [agents-list.tsx](../apps/web/app/agents/agents-list.tsx),
  [agent-detail.tsx](../apps/web/app/agents/[agentId]/agent-detail.tsx),
  [agents.ts](../apps/web/app/lib/agents.ts).
- Strength: real backend data, owner/status/risk/profile/activity/evidence.
- Gap: read-only; no onboarding/edit flow; limited filtering; can still feel
  like a record viewer rather than a full governance workflow.

### Policy Studio

- Verdict: **Strongest frontend surface**.
- Evidence: [policy-studio.tsx](../apps/web/app/policies/policy-studio.tsx),
  [policy-editor.tsx](../apps/web/app/policies/policy-editor.tsx),
  [policy-canvas.tsx](../apps/web/app/policies/policy-canvas.tsx),
  [policy-dsl.ts](../apps/web/app/policies/policy-dsl.ts),
  [policy-inspector.tsx](../apps/web/app/policies/policy-inspector.tsx).
- Strength: repository, backend-backed folders, Blocks/Code DSL,
  `WHEN -> CHECK -> THEN -> PROVE`, local validation, Save draft, Submit for
  review, review state, activation semantics, no Publish.
- Gaps: PolicyCheckStep authoring UI is not wired; operator persistence is
  limited; version history remains compact; frontend logic is large and
  complex.

### Review Inbox / Human Approvals

- Verdict: **Mostly aligned and visually validated**.
- Evidence: [review-inbox.tsx](../apps/web/app/human-approvals/review-inbox.tsx),
  [human-approvals.ts](../apps/web/app/lib/human-approvals.ts),
  [policies.ts](../apps/web/app/lib/policies.ts).
- Strength: unified runtime approvals and policy reviews; current actor visible;
  approve/reject/assign/activate actions have honest disabled reasons; evidence
  and metadata checks are visible.
- Gaps: request-info and runtime assignment are not wired; no real reviewer
  directory; no notifications; frontend role-aware behavior is advisory.

### Runtime Decisions

- Verdict: **Partial to mostly done**.
- Evidence: [runtime-activity-list.tsx](../apps/web/app/runtime-gateway/runtime-activity-list.tsx),
  [runtime.ts](../apps/web/app/lib/runtime.ts).
- Strength: real runtime activity only, no fake production simulation, clear
  lifecycle language.
- Gaps: decision detail drill-down is still lightweight; filtering/pagination
  are missing; CheckResult detail depends on read model availability and often
  points users to Evidence Bundle.

### Evidence & Audit

- Verdict: **Mostly done for JSON review, partial for enterprise audit**.
- Evidence: [evidence-bundle-viewer.tsx](../apps/web/app/evidence/evidence-bundle-viewer.tsx),
  [evidence.ts](../apps/web/app/lib/evidence.ts).
- Strength: manual load, safe warnings, sectioned evidence chain, JSON download,
  defensive metadata filtering.
- Gaps: no general evidence/audit list endpoint, no PDF/signature/archive, no
  SIEM/GRC export, no retention UX.

### Access & Data

- Verdict: **Mostly done as a metadata review workspace**.
- Evidence: [access-inventory-matrix.tsx](../apps/web/app/access-data/access-inventory-matrix.tsx),
  [access-grants-workflow.tsx](../apps/web/app/access-data/access-grants-workflow.tsx),
  [sources-workflow.tsx](../apps/web/app/access-data/sources-workflow.tsx).
- Strength: explains Access Grants, Source profiles, Models, Capabilities, and
  metadata readiness without claiming enforcement or compliance.
- Gaps: no PolicyCheckStep authoring, no dedicated inventory mutation UI, no
  approval workflow for grants, and lifecycle actions are not role-aware in the
  frontend.

### Other Pages

- Integrations: useful guidance page, not an adapter product. This is honest
  but should not be confused with production integration packages.
- Settings/Admin: very thin. Better as honest placeholder than fake enterprise
  admin, but portfolio/demo users may expect local actor clarity.
- Audit route: currently not a full audit explorer; Evidence & Audit carries
  most of the proof workflow.

## 5. Documentation Audit

### Accurate / Useful

- [AGENTS.md](../AGENTS.md) remains the right product boundary.
- [README.md](../README.md), [apps/api/README.md](../apps/api/README.md), and
  [apps/web/README.md](../apps/web/README.md) explain current capabilities and
  local demo flow well.
- [FRONTEND_PRODUCT_BLUEPRINT.md](FRONTEND_PRODUCT_BLUEPRINT.md) matches the
  current workflow-first direction.
- [POLICY_STUDIO_DSL_DESIGN.md](POLICY_STUDIO_DSL_DESIGN.md) correctly keeps
  DSL as authoring, not runtime execution.
- [POLICY_VERSIONING_REVIEW_DESIGN.md](POLICY_VERSIONING_REVIEW_DESIGN.md) and
  [POLICY_VERSION_ACTIVE_ROLLOUT.md](POLICY_VERSION_ACTIVE_ROLLOUT.md) match
  the implemented review/activation posture.

### Stale / Confusing

- [CONTEXTUAL_RUNTIME_GOVERNANCE_DESIGN.md](CONTEXTUAL_RUNTIME_GOVERNANCE_DESIGN.md)
  starts with "Design only" but later marks several runtime schema/evaluator
  pieces as done. This should be refreshed.
- Root [README.md](../README.md) still includes a manual command using
  `docker-compose.dev.yml` in one section, while the current stack file is
  [compose.dev.yml](../compose.dev.yml). This can confuse local setup.
- [ROADMAP.md](ROADMAP.md) and [TASKS.md](TASKS.md) are accurate but very long
  and status-heavy; they mix roadmap, changelog, design caveats, and backlog.
- [apps/web/README.md](../apps/web/README.md) is highly detailed but now reads
  partly like a product spec. Some content should move into docs or be
  shortened.

### Missing

- A short "demo readiness" checklist for portfolio/public demo.
- A production-readiness gap document focused on auth, deployment, retention,
  observability, and adapter contracts.
- A concise API endpoint matrix generated or manually maintained from the
  routers.
- A browser/E2E test plan for Policy Studio, Review Inbox, Evidence, and
  Access & Data.

### Remove / Merge Candidates

- Consolidate overlapping roadmap/task/status narratives between
  [ROADMAP.md](ROADMAP.md), [TASKS.md](TASKS.md), and the README files.
- Keep design docs focused on durable product contracts; move completion status
  into roadmap/tasks.

## 6. Test Audit

### Strong Coverage

- Backend runtime gateway behavior is heavily tested in
  [test_runtime_gateway_api.py](../apps/api/tests/test_runtime_gateway_api.py).
- Evidence safety and RBAC are well covered in
  [test_evidence_bundle_api.py](../apps/api/tests/test_evidence_bundle_api.py).
- PolicyVersion and PolicyVersionReviewRequest lifecycle tests are strong in
  [test_policy_versions_api.py](../apps/api/tests/test_policy_versions_api.py)
  and [test_policy_version_review_requests_api.py](../apps/api/tests/test_policy_version_review_requests_api.py).
- HumanApproval transitions and RBAC have focused tests in
  [test_human_approval_api.py](../apps/api/tests/test_human_approval_api.py).
- AccessGrant lifecycle tests explicitly prove transitions do not create
  runtime records.
- Frontend [smoke.mjs](../apps/web/scripts/smoke.mjs) catches critical copy,
  endpoint, policy DSL, evidence, access, and no-forbidden-copy regressions.

### Missing Coverage

- Browser/E2E tests for Policy Studio Save draft -> Submit for review ->
  Review Inbox approve -> Activate.
- Browser/E2E tests for Review Inbox runtime approval actions and disabled
  states under restricted actors.
- Browser/E2E tests for Evidence Bundle JSON load/download and unsafe metadata
  filtering.
- Browser/E2E tests for Access & Data lifecycle transitions and empty/error
  states.
- Visual regression coverage for the large AGCP Studio shell.
- Online Alembic validation against a real PostgreSQL instance for migrations
  listed as validation pending.
- End-to-end `scripts/dev-demo.ps1` test outside unit-level seed tests.

### Recommended Tests

- Add a Playwright/Codex browser smoke suite for `/policies`,
  `/human-approvals`, `/runtime-gateway`, `/evidence`, and `/access-data`.
- Add a Compose smoke command that starts the stack, runs `dev-demo.ps1`, and
  verifies `/runtime-gateway`, `/human-approvals`, and `/evidence` show the
  created records.
- Add a docs/setup smoke for the documented compose commands.
- Add frontend tests for no `Publish`, no compliance-score language, and no
  stale `AI Act / ISO` visible copy.

## 7. Top Risks

1. **Auth/RBAC is not production-grade**. Local dev actor and minimal roles are
   useful but not enterprise identity.
2. **Runtime enforcement is integration-dependent**. AGCP returns decisions;
   external wrappers must honor `proceed`.
3. **Frontend shell is too large and fragile**. [AGCPStudio.tsx](../apps/web/app/agcp-studio/AGCPStudio.tsx)
   mixes shell, CSS, legacy prototype state, and connected routes.
4. **Legacy Policy/PolicyRule fallback can confuse users** even with active
   version guardrails.
5. **Historical PolicyDecision backfill is undecided**, so version coverage is
   mixed and must remain honestly presented.
6. **Evidence is JSON-only**. Good for V1, but not enough for enterprise audit
   packaging.
7. **PolicyCheckStep authoring is backend-only**, limiting the usefulness of
   metadata pre-checks for non-developer users.
8. **Docs are long and overlapping**, which makes current truth harder to find.
9. **Some stale prototype copy remains in source**, including `AI Act / ISO`
   in shell constants; even if not visible, it is a positioning hazard.
10. **No real frontend auth UX** means demos can show role-aware hints but not
    enterprise user journeys.

## 8. Recommended Next Roadmap

### P0 - Must Fix Before Showing Demo

| Item | Why it matters | Affected areas | Effort | Type |
| --- | --- | --- | --- | --- |
| Remove or quarantine stale prototype/compliance-adjacent shell constants | Prevent accidental UI/copy regressions such as `AI Act / ISO` | `apps/web/app/agcp-studio/AGCPStudio.tsx`, smoke tests | S | Frontend/test |
| Add a short demo-readiness doc | Makes the current product easy to present honestly | `docs/`, README links | S | Docs |
| Verify documented compose commands | README currently mixes `compose.dev.yml` and `docker-compose.dev.yml` | README files, scripts | S | Docs/test |
| Add one browser smoke for `/policies` and `/human-approvals` | These are the hero surfaces; typecheck is not enough | `apps/web`, browser QA | M | Test |
| Keep no-Publish/no-compliance checks current | Product positioning is a core boundary | `apps/web/scripts/smoke.mjs` | S | Test |

### P1 - Should Improve Before Portfolio/Public Demo

| Item | Why it matters | Affected areas | Effort | Type |
| --- | --- | --- | --- | --- |
| Split AGCPStudio shell/styles from connected product pages | Reduces regression risk and improves maintainability | `AGCPStudio.tsx`, `globals.css`, route CSS | L | Frontend |
| Add Review Inbox E2E flow | Proves runtime and policy reviews work together | HumanApproval + PolicyReview frontend/backend | M | Test |
| Add PolicyCheckStep authoring design-to-UI follow-up | Makes metadata pre-checks usable beyond seeded demo | Policy Studio, policy_check_steps APIs | L | Frontend/backend |
| Refresh Contextual Runtime Governance doc | Remove design-only contradiction | Docs | S | Docs |
| Add Agent edit/onboarding path | Completes "know your agents" workflow | Agents frontend/backend | M | Frontend/backend/test |

### P2 - Good Follow-ups

| Item | Why it matters | Affected areas | Effort | Type |
| --- | --- | --- | --- | --- |
| Historical PolicyDecision backfill decision | Clarifies evidence history | PolicyDecision, migrations/admin docs | M | Backend/docs |
| Evidence PDF/signature design | Enterprise audit expectation | Evidence Bundle | M/L | Backend/frontend/docs |
| Runtime Decisions detail workspace | Makes decision lifecycle easier to inspect | Runtime frontend/read models | M | Frontend/backend |
| AccessGrant review workflow | Moves Access & Data beyond lifecycle toggles | Access/Data, reviews, audit | M/L | Backend/frontend |
| Settings/Admin local actor clarity | Avoids fake enterprise admin while improving demos | Settings page | S | Frontend/docs |

### P3 - Later / Enterprise

| Item | Why it matters | Affected areas | Effort | Type |
| --- | --- | --- | --- | --- |
| OIDC/SAML/JWT and persistent users/roles | Required for real enterprise use | Auth/RBAC, frontend auth | XL | Backend/frontend/security |
| Team/org ownership resolver | Needed for owner-based evidence export | Evidence, auth, agents | L | Backend |
| Service actor key rotation/admin mutations | Required for production integrations | Service actor registry | L | Backend/frontend |
| Adapter packages | Makes Integration Hub real | Runtime Gateway, packages | L | Backend/packages/docs |
| Retention/observability/deployment | Production readiness | Platform docs, infra | XL | Backend/docs/ops |

## 9. Issues / Backlog Recommendations

Do not close issues automatically from this audit.

### Close or mark implemented

- #58 Policy Studio V1 guided authoring, if the current IDE surface is accepted.
- #76 controlled DSL design for V1, because [POLICY_STUDIO_DSL_DESIGN.md](POLICY_STUDIO_DSL_DESIGN.md)
  now defines the grammar, compile target, non-goals, and storage boundary.
- Minimal reviewer assignment, if tracked separately, because backend and UI
  support assignment as governance metadata.

### Keep open

- #56, narrowed to remaining policy workflow hardening: historical backfill,
  DSL source storage decision, optional unassign, and richer role-aware UX.
- #68, narrowed to historical PolicyDecision backfill and rollout hardening.
- Frontend auth / role-aware UI.
- Evidence PDF/signature/export packaging.

### Split

- Split "PolicyCheckStep UI" into:
  - authoring model and UX;
  - backend lifecycle/versioning behavior;
  - Runtime Gateway evidence behavior;
  - browser/E2E coverage.
- Split "Integration Hub" into:
  - docs/guidance page;
  - service actor setup validation;
  - real adapter package(s);
  - production auth/rotation.
- Split "Access & Data" into:
  - inventory read UX;
  - AccessGrant lifecycle;
  - review/approval workflow;
  - runtime policy context usage.

### Create

- Remove stale prototype/compliance-adjacent constants from `AGCPStudio.tsx`.
- Add browser E2E for Policy Studio -> Review Inbox -> Activation.
- Add browser E2E for Runtime metadata pre-check demo evidence path.
- Refresh setup docs to consistently use `compose.dev.yml`.
- Refactor frontend shell/styles into smaller modules without changing UX.
- Decide historical PolicyDecision backfill policy.
- Add production-readiness checklist for auth, deployment, retention, and
  evidence packaging.

## 10. Final Verdict

**Is AGCP now close to the original product idea? Mostly.**

AGCP is no longer just a backend experiment or fake dashboard. It has a real
governance spine: agents, declared access, deterministic policies, runtime
decisions, human approvals, policy review/activation, metadata-only checks,
audit records, and evidence bundles. The frontend increasingly expresses those
as workflows rather than raw API resources, especially in Policy Studio and
Human Approval Studio.

It is not yet a complete enterprise control plane. The remaining gaps are not
cosmetic: production identity, stronger RBAC, adapter enforcement, evidence
packaging, historical version clarity, and frontend maintainability all need
work before AGCP can be positioned as more than a strong local/demo-grade V1.
The right next step is not adding more domain objects. It is hardening the
existing know/control/prove workflows so users can trust the evidence chain and
understand exactly where AGCP stops and their runtime begins.
