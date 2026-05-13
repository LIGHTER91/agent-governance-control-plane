# Codex Workflow

## Source of truth

Use:

- Trello or similar for product-level thinking.
- GitHub Issues for implementation tasks.
- Pull Requests for review and validation.
- `AGENTS.md` for persistent Codex instructions.

## Issue lifecycle

```text
Idea
  ->
Clarified
  ->
Specified
  ->
Ready for Codex
  ->
In progress
  ->
PR opened
  ->
Validation pending, if checks cannot run locally
  ->
Human review
  ->
Merged
  ->
Done
```

## Ready for Codex checklist

An issue is ready for Codex only if it includes:

- objective;
- exact scope;
- explicit non-goals;
- affected modules;
- expected tests;
- acceptance criteria;
- constraints;
- definition of done.

## Standard Codex instruction

Use this when assigning an issue:

```text
Read AGENTS.md and the linked issue.

Implement only the requested scope with the smallest safe change.

Do not introduce new production dependencies unless justified.

Add or update tests.

Run relevant checks successfully.

Before finishing, review your own diff and provide:
1. what was completed;
2. what was not completed;
3. tests/checks run;
4. validation status;
5. risks or follow-up tasks;
6. files changed.

Do not mark the task done if tests fail or cannot be run.
If implementation is complete but tests/checks cannot run because the environment is missing, report "implementation complete, validation pending" and keep the task out of Done.
```

## PR expectations

Every PR should include:

- issue number;
- summary;
- scope;
- non-goals;
- tests run;
- validation status;
- screenshots if UI;
- risks;
- follow-up tasks.

## Human review focus

When reviewing Codex output, check:

- Did it stay in scope?
- Did it invent concepts?
- Did it add dependencies?
- Did it skip tests?
- Did it weaken security?
- Did it make compliance claims?
- Did it create architecture debt?
- Did it alter public API unexpectedly?
