# [Spike] Runtime Gateway design proposal

## Objective

Investigate a minimal runtime gateway design without implementing production code.

## Context

Runtime control is likely the key differentiator, but it should be designed before implementation.

## Scope

- Propose gateway responsibilities.
- Propose request/response schema for tool calls.
- Explain allow/deny/manual_review flow.
- Identify security risks.
- Recommend next implementation issue.

## Non-goals

- Do not implement gateway.
- Do not add dependencies.
- Do not modify application code.

## Acceptance criteria

- Design doc is added under docs.
- Trade-offs are explicit.
- Follow-up implementation issue is proposed.

## Expected tests/checks

- No code tests required.
- Documentation review only.

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
