# [Codex] Cover automated HumanApproval evidence chain

Status: Completed in V0 backend milestone.

## Objective

Ensure Evidence Bundle export clearly represents the chain created by telemetry
policy evaluation and automatic human approval creation.

## Context

After automatic HumanApproval creation, reviewers need to navigate from the trace
event to the policy decision, approval, and audit log by ID.

## Completed scope

- Ensured Evidence Bundle includes related HumanApproval records.
- Included audit logs related to HumanApprovals in the agent Evidence Bundle.
- Added tests for the chain:
  - TraceEventRecord
  - PolicyDecision
  - HumanApproval
  - `human_approval_requested` AuditLog
- Preserved deterministic JSON export and metadata filtering.

## Non-goals preserved

- No PDF export.
- No cryptographic signing.
- No frontend.
- No runtime blocking.
- No compliance claims.

## Validation

Covered by Evidence Bundle API tests in the completed V0 backend milestone.
