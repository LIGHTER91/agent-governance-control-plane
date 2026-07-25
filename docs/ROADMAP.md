# AGCP Roadmap

This roadmap tracks product maturity, not legal compliance. AGCP is a
governance and evidence control plane for Agents that run in existing
orchestrators and runtimes. It does not execute tools, replace those runtimes,
or certify legal compliance.

The detailed evidence behind this roadmap is in
`docs/PROJECT_AUDIT_CURRENT_STATE.md`.

## Current maturity

AGCP is a **local V1 / advanced product prototype**.

- Local demo: strong, with isolated clean PostgreSQL validation pending in the
  current audit environment because Docker was unavailable.
- Product alpha: early.
- Beta: not ready.
- Production: not ready.
- Enterprise: not ready.

The core product promises are substantially implemented:

```text
Know your Agents
-> govern declared access and policy configuration
-> decide and review risky runtime actions
-> export a bounded evidence chain
```

Runtime enforcement still depends on wrappers or adapters calling AGCP and
honoring `proceed`. Access Grants are governance declarations and policy
context, not credentials or automatic IAM enforcement.

## Implemented V1 foundation

### Know your Agents

- Agent Registry with owner, environment, lifecycle status, risk level, and
  framework metadata.
- Agent activity, HumanApproval summary, Agent-scoped Access Grants, and Agent
  Governance Profile.
- Capability, Source, ModelAsset, DataUsageProfile, and AccessGrant inventory
  APIs.
- Workflow-first Access & Data frontend with explicit grant lifecycle actions
  and safe metadata-only readiness.

The main gap is a frontend Agent onboarding/editing workflow that connects
Agents to owners, inventories, and grants.

### Control risky actions

- Deterministic Policy and PolicyRule APIs and evaluator.
- Policy folders and nullable Policy `folder_id`.
- Policy Studio V1 with the preserved IDE layout:
  repository sidebar, center editor, policy structure bar,
  `WHEN -> CHECK -> THEN -> PROVE`, Blocks/Code DSL toggle, compact block list,
  compile bar, local validation console, and right inspector.
- Synchronized Policy Canvas and controlled Code DSL, compiling to
  deterministic condition JSON.
- PolicyVersion draft snapshots, immutable pending reviews, dedicated review
  requests, assignment, approve/reject, safe diff, explicit activation,
  single-active guard, replacement, rollback draft, archive, guarded draft
  delete, and live-edit guardrails.
- Runtime Gateway decision, resume, activity, idempotency, contextual inventory
  resolution, and optional enforcement contract.
- Telemetry evaluation through the same active PolicyVersion loader, with
  unversioned fallback.
- Metadata-only PolicyCheckStep execution behind
  `AGCP_RUNTIME_METADATA_PRE_CHECKS_ENABLED=true`.
- CheckResult evidence and explicit deterministic `check_*` matching.
- Human Approval Studio for Runtime HumanApproval and PolicyVersion reviews,
  preserving the approved Review Inbox layout inside the existing shell.

The main gaps are guided PolicyCheckStep authoring, production identity/RBAC,
and a supported adapter that reliably enforces `proceed`.

### Prove what happened

- Append-only AuditLog foundation for governance mutations and review/runtime
  events.
- PolicyDecision, TraceEvent, AgentRun, HumanApproval, CheckResult, and
  PolicyVersion evidence links.
- Workflow-first Runtime Decisions timeline.
- Consolidated Evidence & Audit explorer with Subject, Policy Decision,
  metadata CheckResults, Human Review, Policy Review, Audit Trail, and bounded
  Evidence Bundle JSON download.
- Deterministic one-command metadata pre-check demo that creates real backend
  evidence.

The main gaps are a general evidence/audit index, PDF/signature/archive
packaging, retention, and external SIEM/GRC export.

### Integration and administration

- Integration Hub guidance for Runtime Gateway API, LangGraph, n8n, Dataiku,
  MCP, and generic API/webhook callers.
- Config-based Service Actor API keys, endpoint scopes, fine-grained Agent /
  environment / runtime mode / tool rules, and strict service-auth mode.
- Optional DB-backed Service Actor registry with hashed-key metadata,
  persisted scopes/rules, read-only admin APIs, and import helpers.
- Local `/me` actor and narrow HumanApproval/Evidence/review RBAC checks.

These are foundations, not enterprise administration. There is no production
adapter package, user login, OIDC/SAML/JWT, user/team directory, broad role
model, public Service Actor mutation/rotation workflow, or production
operations setup.

## P0 — stabilize before public demonstration

1. Run `scripts/validate-clean.ps1` with Docker available and record:
   - clean PostgreSQL volume;
   - online Alembic upgrade to head;
   - `/health` and `/me`;
   - deterministic seed;
   - metadata pre-check result with `require_human_review`,
     `proceed=false`, CheckResults, and HumanApproval;
   - frontend smoke;
   - isolated cleanup.
2. Add one clean browser E2E governance flow across Agent, Policy, Runtime
   Decision, CheckResults, HumanApproval, activation, and Evidence Bundle.
3. Resolve remaining status contradictions in durable design documents without
   changing product semantics.

Exit condition: the isolated stack and browser flow pass from a clean checkout,
and the result is recorded without relying on existing developer data.

## P1 — strengthen product alpha

1. **Agent onboarding and governance editing workflow**
   - register/edit Agent;
   - owner, environment, status, and risk classification;
   - connect Capabilities, Sources, Models, and Access Grants;
   - preserve workflow-first UI.
2. **Guided PolicyCheckStep authoring in Policy Studio**
   - persist real PolicyCheckSteps;
   - constrain check type, target selection, expected outcome, and failure
     behavior;
   - preserve PolicyVersion snapshot compatibility and CheckResult evidence;
   - preserve the existing Policy Studio IDE layout.
3. **Production-quality Python/LangGraph runtime adapter**
   - before-tool decision;
   - mandatory `proceed` enforcement;
   - idempotency, timeout, and failure policy;
   - HumanApproval resume;
   - fake-tool tests and package/example documentation.

Exit condition: the three weakest day-to-day alpha workflows are usable without
raw API calls or seed-specific integration code.

## P2 — beta preparation

1. Identity, authentication, RBAC, and separation-of-duties hardening.
2. Service Actor registry administration, key rotation, ownership restrictions,
   and complete audit coverage.
3. Historical PolicyDecision backfill decision and, only if required, an
   explicit conservative admin/report path.
4. Evidence package, signing, retention, and export design.
5. Runtime/evidence filtering, pagination, and operational read models where
   browser workflows require them.

Exit condition: multi-user review and machine integration are supportable,
auditable, and testable without local development identity assumptions.

## P3 — enterprise/later

1. Production deployment, observability, backup, recovery, and incident
   runbooks.
2. Enterprise user/team/org directory and ownership resolution.
3. SIEM/GRC evidence integrations.
4. Additional supported runtime/framework adapters after the first adapter
   contract is proven.
5. Signed or packaged evidence delivery according to real customer retention
   and review requirements.

## Explicit non-goals

- No orchestration or AGCP-side tool execution.
- No fake production simulation, metrics, scanners, or reviewer directory.
- No Publish action or automatic activation after review.
- No automatic AccessGrant enforcement without explicit PolicyDecision
  semantics.
- No LLM-based policy evaluation, generic workflow engine, or broad policy
  language.
- No compliance, trust, maturity, or numerical risk score.
- No legal certification claim.

## Backlog administration

Issue #56's requested V1 PolicyVersion review lifecycle is implemented in code
and tests. Issue #57's broad workflow-first frontend rebuild is largely
superseded by narrower gaps. The GitHub CLI was unavailable during the current
stabilization pass, so exact comments, follow-up issue bodies, and closure
commands are prepared in `docs/GITHUB_BACKLOG_CLEANUP.md` rather than applied.
