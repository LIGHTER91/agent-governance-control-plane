# Issues Backlog Notes

GitHub Issues should be the operational source of truth once issues are created
in GitHub. This directory is a historical and seed backlog for Codex-assisted
implementation. Do not automatically close or create GitHub issues from this
folder without a human explicitly asking for that action.

Issue files are not renamed when their status changes, so existing references
remain stable. Use this README plus `docs/TASKS.md` and `docs/ROADMAP.md` for
the current documentation snapshot.

## Current Milestone Snapshot

The V0 backend governance flow is complete:

```text
Agent Registry
-> Telemetry tool_call_requested
-> Policy evaluation
-> PolicyDecision
-> HumanApproval pending when require_human_review
-> AuditLog
-> Evidence Bundle JSON export
```

This supports evidence collection and governance workflows. It does not claim
legal compliance certification.

## Completed Seed Issues

These initial seed issues are completed as part of the V0 backend milestone:

- `001-initialize-repository-skeleton.md`
- `002-create-backend-skeleton.md`
- `003-add-database-and-migrations.md`
- `004-implement-agent-domain-model.md`
- `005-implement-agent-registry-api.md`
- `006-implement-immutable-audit-log-model.md`
- `007-add-audit-logs-for-agent-mutations.md`
- `008-implement-policy-domain-model.md`
- `009-implement-simple-policy-evaluator.md`
- `010-define-telemetry-event-schema.md`
- `011-implement-agent-run-event-ingestion.md`
- `014-add-evidence-bundle-json-export.md`
- `015-add-ci-quality-gates.md`
- `016-add-openapi-documentation.md`
- `017-security-hardening-baseline.md`
- `018-implement-human-approval-model.md`

## Completed Follow-up Issue Docs

These files were added after the initial backlog to document completed V0 work
that happened as smaller implementation increments:

- `025-implement-telemetry-persistence-models.md`
- `026-enforce-telemetry-run-agent-integrity.md`
- `027-add-telemetry-idempotency.md`
- `028-add-policy-rule-adapter.md`
- `029-add-policy-decision-persistence-service.md`
- `030-link-policy-decision-to-trace-event.md`
- `031-evaluate-policies-for-telemetry-tool-call-requested.md`
- `032-implement-human-approval-api.md`
- `033-enforce-human-approval-policy-decision-agent-consistency.md`
- `034-include-human-approvals-in-evidence-bundle.md`
- `035-auto-create-human-approval-for-review-decisions.md`
- `036-cover-automated-human-approval-evidence-chain.md`
- `037-add-v0-governance-flow-demo.md`
- `038-consolidate-v0-backend-milestone-docs.md`

## Not Started Seed Issues

These seed issues remain future work:

- `012-create-dashboard-shell.md`
- `013-add-agent-list-page.md`
- `019-runtime-gateway-spike.md`
- `020-langgraph-integration-spike.md`
- `021-implement-tool-domain-model.md`
- `022-implement-data-source-domain-model.md`
- `023-implement-model-domain-model.md`
- `024-implement-permission-domain-model.md`

## Known Gaps

- Policy and PolicyRule CRUD APIs are not represented in the initial numbered
  seed backlog and should become future GitHub issues.
- Tool, Data Source, Model, and Permission evidence bundle coverage should wait
  until those domain models exist.
- This folder does not know whether matching GitHub Issues exist, are open, or
  are closed.
