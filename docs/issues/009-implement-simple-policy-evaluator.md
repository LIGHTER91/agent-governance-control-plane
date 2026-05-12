# [Codex] Implement simple Policy evaluator

## Objective

Implement a minimal deterministic evaluator for explicit rules.

## Context

The first evaluator should prove policy decision recording without over-engineering.

## Scope

- Implement a simple evaluator function/service.
- Support explicit allow/deny/manual_review rules based on agent id, tool name, environment, and risk level.
- Return a PolicyDecision object or DTO.
- Add reason string explaining the decision.

## Non-goals

- Do not implement a DSL.
- Do not use LLM evaluation.
- Do not add OPA/Cedar.
- Do not build runtime blocking gateway.

## Acceptance criteria

- Evaluator returns allow/deny/require_human_review/not_applicable.
- Decision includes reason.
- Deterministic tests cover all outcomes.

## Expected tests/checks

- Unit tests for allow.
- Unit tests for deny.
- Unit tests for require_human_review.
- Unit tests for no matching rule.

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
