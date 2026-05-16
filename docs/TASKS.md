# Tasks

This file is a lightweight project tracker. GitHub Issues should become the
source of truth once the repository is managed primarily through GitHub.

## Current Milestone

V0 backend governance flow: Done.

Implemented flow:

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

## Next Tasks

Recommended order:

1. Implement Tool domain model.
2. Implement Data Source domain model.
3. Implement Model domain model.
4. Implement Permission domain model.
5. Add Policy CRUD API.
6. Add PolicyRule CRUD API.
7. Add audit records for Policy and PolicyRule mutations.
8. Extend Evidence Bundle with Tool, Data Source, Model, and Permission records
   once those concepts exist.
9. Add dashboard shell.
10. Add agent list page.
11. Prepare Runtime Gateway design proposal.
12. Prepare LangGraph integration design.

## Backlog

- [ ] Implement Tool domain model.
- [ ] Implement Data Source domain model.
- [ ] Implement Model domain model.
- [ ] Implement Permission domain model.
- [ ] Add Policy CRUD API.
- [ ] Add PolicyRule CRUD API.
- [ ] Add audit records for Policy and PolicyRule mutations.
- [ ] Extend Evidence Bundle for Tool, Data Source, Model, and Permission
      records.
- [ ] Add dashboard shell.
- [ ] Add agent list page.
- [ ] Add agent detail page.
- [ ] Add agent run timeline.
- [ ] Add policy decision timeline.
- [ ] Add human approval review view.
- [ ] Add Evidence Bundle viewer.
- [ ] Runtime Gateway design proposal.
- [ ] LangGraph integration design.
- [ ] Authentication and RBAC design.
- [ ] Retention policy design.

## In Progress

Empty.

## Implementation Complete, Validation Pending

Use this section when implementation is complete but tests/checks cannot run
because the local environment is missing required tooling, services, or
credentials.

Empty.

## Done

- [x] Create Codex-ready documentation starter.
- [x] Initialize repository skeleton.
- [x] Add backend skeleton.
- [x] Add CI quality gates.
- [x] Add database and migrations baseline.
- [x] Implement Agent domain model.
- [x] Refactor Agent owner identity model.
- [x] Implement immutable AuditLog model.
- [x] Implement Agent Registry API.
- [x] Add audit records for Agent mutations.
- [x] Implement Policy, PolicyRule, and PolicyDecision domain models.
- [x] Implement simple deterministic Policy evaluator.
- [x] Add PolicyRule adapter for persisted rules.
- [x] Add PolicyDecision persistence service.
- [x] Define telemetry AgentRun and TraceEvent schemas.
- [x] Add AgentRunRecord and TraceEventRecord persistence.
- [x] Enforce TraceEventRecord to AgentRunRecord integrity.
- [x] Add telemetry event ingestion endpoint.
- [x] Add telemetry idempotency / duplicate protection.
- [x] Evaluate policies for telemetry `tool_call_requested` events.
- [x] Link PolicyDecision records to TraceEventRecord.
- [x] Implement HumanApproval model.
- [x] Implement Human Approval API with explicit transitions.
- [x] Enforce HumanApproval `agent_id` and `policy_decision_id` consistency.
- [x] Automatically create pending HumanApproval when telemetry policy decision
      requires human review.
- [x] Add audit log for automatically requested HumanApproval.
- [x] Add Evidence Bundle JSON export for one agent.
- [x] Include HumanApproval records in Evidence Bundle.
- [x] Include automatically created HumanApproval evidence chain in Evidence
      Bundle.
- [x] Add metadata safety baseline for telemetry, audit, and evidence export.
- [x] Add OpenAPI documentation examples for core backend endpoints.
- [x] Add executable V0 governance flow demo.
- [x] Consolidate V0 backend milestone documentation.

## Blocked

Empty.

## Rule For Codex

Codex may update this file only when explicitly asked.

Codex must not move a task to Done unless:

- implementation is complete;
- tests were added or updated where relevant;
- relevant checks were run successfully;
- remaining risks were reported.

If checks cannot be run because the environment is missing, Codex must place or
report the task as "implementation complete, validation pending" instead of Done.
