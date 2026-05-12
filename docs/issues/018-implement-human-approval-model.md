# [Codex] Implement Human Approval model

## Objective

Add initial domain model for human approval workflows.

## Context

Human oversight is central to agent governance for risky actions.

## Scope

- Add HumanApproval model.
- Add statuses: pending, approved, rejected, expired, cancelled.
- Link approval to agent and optionally policy decision.
- Add migration and validation tests.

## Non-goals

- Do not build UI.
- Do not send emails or Slack messages.
- Do not implement workflow engine.

## Acceptance criteria

- Model exists and validates statuses.
- Can link approval to an agent.
- Tests cover status validation.

## Expected tests/checks

- Unit tests for statuses.
- Persistence tests if DB exists.

## Codex instructions

Read `AGENTS.md` first.

Implement only this issue with the smallest safe change.

Do not add unrelated features or dependencies.

Before finishing, provide:
1. completed items;
2. files changed;
3. tests/checks run;
4. known limitations;
5. recommended follow-up tasks.
