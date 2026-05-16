# [Codex] Include HumanApproval records in Evidence Bundle

Status: Completed in V0 backend milestone.

## Objective

Include human approval records in the JSON Evidence Bundle for one agent.

## Context

The Evidence Bundle needs to show who approved, rejected, cancelled, or is still
reviewing governance-relevant decisions.

## Completed scope

- Added `human_approvals` to `GET /agents/{agent_id}/evidence-bundle`.
- Included fields needed for review:
  - approval ID
  - agent ID
  - policy decision ID
  - status
  - requester actor fields
  - reviewer actor fields
  - reason and decision note
  - timestamps
- Preserved existing Evidence Bundle structure.
- Added tests for linked policy decisions and unknown agent behavior.

## Non-goals preserved

- No PDF export.
- No cryptographic signing.
- No frontend.
- No workflow changes.
- No legal compliance claims.

## Validation

Covered by Evidence Bundle API tests in the completed V0 backend milestone.
