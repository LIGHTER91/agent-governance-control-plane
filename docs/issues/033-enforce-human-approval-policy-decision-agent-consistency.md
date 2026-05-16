# [Codex] Enforce HumanApproval policy decision agent consistency

Status: Completed in V0 backend milestone.

## Objective

Prevent a HumanApproval from referencing a PolicyDecision that belongs to a
different agent.

## Context

Human approvals are governance evidence. If `agent_id` and
`policy_decision_id` point to different agents, the evidence chain becomes
misleading.

## Completed scope

- Verified the referenced `PolicyDecision` exists when supplied.
- Verified `PolicyDecision.agent_id == HumanApproval.agent_id`.
- Rejected mismatches with a clear client error.
- Preserved existing create, approve, reject, and cancel behavior.
- Added tests for matching, mismatched, and unknown policy decision cases.

## Non-goals preserved

- No PolicyDecision model changes.
- No auth/RBAC.
- No notifications.
- No workflow engine.

## Validation

Covered by HumanApproval API tests in the completed V0 backend milestone.
