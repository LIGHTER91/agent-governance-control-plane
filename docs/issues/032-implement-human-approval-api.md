# [Codex] Implement Human Approval API

Status: Completed in V0 backend milestone.

## Objective

Expose minimal explicit HumanApproval endpoints for requesting, reading, listing,
approving, rejecting, and cancelling approvals.

## Context

Human oversight is a core governance concept. The API needed explicit
transition endpoints rather than a generic update endpoint.

## Completed scope

- Added `POST /human-approvals`.
- Added `GET /human-approvals/{approval_id}`.
- Added `GET /agents/{agent_id}/human-approvals`.
- Added explicit approve, reject, and cancel endpoints.
- Enforced pending-only transitions.
- Used the development actor placeholder until authentication exists.
- Appended audit records for request, approve, reject, and cancel transitions.
- Added API tests for success and invalid transition behavior.

## Non-goals preserved

- No frontend.
- No auth/RBAC.
- No notifications.
- No workflow engine.
- No runtime blocking.

## Validation

Covered by HumanApproval API tests in the completed V0 backend milestone.
