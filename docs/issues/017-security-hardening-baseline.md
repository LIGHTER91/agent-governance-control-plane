# [Codex] Security hardening baseline

## Objective

Add basic security guardrails and tests around secrets/logging.

## Context

The product domain is sensitive; security mistakes in logs or examples are unacceptable.

## Scope

- Review logging configuration.
- Add helper or convention for redacting sensitive keys.
- Add tests for redaction helper if implemented.
- Update docs if needed.

## Non-goals

- Do not add full secret scanning SaaS.
- Do not add complex auth.
- Do not implement enterprise RBAC.

## Acceptance criteria

- Known sensitive keys are redacted.
- Tests cover redaction behavior.
- No examples contain fake real-looking API keys.

## Expected tests/checks

- Unit tests for redaction.
- Existing backend tests.

## Codex instructions

Read `AGENTS.md` first.

Implement only this issue with the smallest safe change.

Do not add unrelated features or dependencies.

Before finishing, provide:
1. completed items;
2. files changed;
3. tests/checks run;
4. validation status;
5. known limitations;
6. recommended follow-up tasks.
