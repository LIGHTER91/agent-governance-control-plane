# Roadmap

This roadmap tracks product maturity, not legal compliance status. The project
supports evidence collection and governance workflows; it does not certify that
an organization is compliant with any regulation or standard.

## Phase 0 - Repository and Codex setup

Status: Completed.

Goal: make development safe, structured, and reviewable.

Completed:

- Repository structure.
- `AGENTS.md`.
- Product and architecture docs.
- Issue templates.
- PR template.
- Initial backlog.
- Backend quality CI.
- Documentation baseline check.

## Phase 1 - V0 backend governance flow

Status: Completed.

Goal: prove the governance core in a backend-only modular monolith.

Completed capabilities:

- FastAPI backend skeleton.
- PostgreSQL-targeted SQLAlchemy 2.x and Alembic baseline.
- Agent domain model and Agent Registry API.
- Immutable application-level AuditLog foundation.
- Agent mutation audit records.
- Policy, PolicyRule, and PolicyDecision domain models.
- Minimal deterministic policy evaluator.
- Adapter from persisted active PolicyRule records to evaluator rules.
- PolicyDecision persistence service.
- Telemetry schemas and ingestion endpoint.
- AgentRunRecord and TraceEventRecord persistence.
- Telemetry idempotency.
- Policy evaluation for telemetry `tool_call_requested` events.
- Explicit `TraceEventRecord -> PolicyDecision` relationship.
- HumanApproval model.
- Human Approval API with explicit transitions.
- Automatic pending HumanApproval creation when a telemetry-triggered decision
  is `require_human_review`.
- Human approval audit logging.
- Evidence Bundle JSON export for one agent.
- Evidence Bundle coverage for TraceEventRecord, PolicyDecision,
  HumanApproval, and related AuditLog.
- Metadata safety filtering for telemetry, audit, and evidence export.
- OpenAPI examples for core backend endpoints.
- Executable V0 governance flow demo.

The completed V0 flow is:

```text
Agent Registry
-> Telemetry tool_call_requested
-> Policy evaluation
-> PolicyDecision
-> HumanApproval pending when require_human_review
-> AuditLog
-> Evidence Bundle JSON export
```

Reference: `docs/V0_GOVERNANCE_FLOW.md`.

## Phase 2 - Domain coverage and API completeness

Status: Next.

Goal: make the governance domain broader without adding runtime enforcement too
early.

Recommended next work:

- Tool domain model.
- Data Source domain model.
- Model domain model.
- Permission domain model.
- Policy CRUD API.
- PolicyRule CRUD API.
- Audit logging for Policy and PolicyRule mutations.
- Evidence Bundle coverage for Tool, Data Source, Model, and Permission records
  once those records exist.
- Improved local demo seed path for V0 policies once Policy CRUD exists.

## Phase 3 - Minimal operational control plane UI

Status: Not started.

Goal: make the backend workflow visible and reviewable for humans.

Planned capabilities:

- Dashboard shell.
- Agent list page.
- Agent detail page.
- Agent run timeline.
- Policy decision timeline.
- Human approval review view.
- Evidence Bundle viewer.

## Phase 4 - Runtime governance spike

Status: Not started.

Goal: evaluate runtime enforcement or simulation without turning the product into
an orchestrator.

Planned capabilities:

- Runtime Gateway design proposal.
- Runtime gateway prototype.
- Allow/deny/review decision path.
- Policy simulation mode.
- SDK or middleware spike for one framework.
- Incident creation concept.

## Phase 5 - Enterprise governance

Status: Not started.

Goal: prepare for serious enterprise usage.

Planned capabilities:

- Authentication and RBAC.
- SSO integration.
- Retention policies.
- Signed or packaged evidence exports.
- Approval workflow enhancements.
- Risk review dashboard.
- SIEM/GRC integrations.
- Policy versioning.

## Phase 6 - Platform expansion

Status: Not started.

Goal: broaden integrations while preserving the control-plane boundary.

Planned capabilities:

- LangGraph integration.
- n8n/Dataiku integration.
- MCP integration.
- Cloud AI platform connectors.
- Advanced reporting.
- Compliance framework mapping support for evidence workflows, without claiming
  automatic compliance.
- Policy template library.
