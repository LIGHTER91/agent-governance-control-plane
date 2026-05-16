# [Codex] Add V0 governance flow demo

Status: Completed in V0 backend milestone.

## Objective

Document and test a deterministic end-to-end V0 backend governance scenario.

## Context

The backend supports the complete V0 flow and needed a single executable test to
demonstrate how the pieces fit together.

## Completed scope

- Added an executable backend-only pytest scenario.
- Covered:
  - agent creation
  - active policy/rule seed
  - telemetry `tool_call_requested`
  - TraceEventRecord creation
  - PolicyDecision with `require_human_review`
  - pending HumanApproval creation
  - `human_approval_requested` AuditLog
  - Evidence Bundle export
  - ID navigation across the evidence chain
- Added `docs/V0_GOVERNANCE_FLOW.md`.

## Non-goals preserved

- No frontend.
- No auth/RBAC.
- No notifications.
- No runtime blocking.
- No Docker.
- No compliance claims.

## Validation

Covered by `apps/api/tests/test_v0_governance_flow.py` in the completed V0
backend milestone.
