# Codex Prompt Library

## Implement one issue

```text
Read AGENTS.md and issue #<number>.

Implement the issue with the smallest safe change.

Hard constraints:
- Stay in scope.
- Do not add unrelated features.
- Do not introduce new production dependencies without justification.
- Add or update tests.
- Run relevant checks.
- Provide final report with completed items, tests run, files changed, and risks.
```

## Review a PR

```text
Review this PR as a senior software engineer working on an Agent Governance Control Plane.

Focus on:
- scope creep;
- missing tests;
- security regressions;
- auditability;
- domain model consistency;
- over-engineering;
- accidental compliance claims;
- maintainability.

Do not bikeshed formatting unless it affects correctness.
```

## Refactor safely

```text
Refactor only the files needed for <goal>.

Do not change external behavior.

Add or update tests proving behavior is unchanged.

Do not rename public domain concepts unless explicitly requested.

Report all behavior changes, if any.
```

## Add tests only

```text
Add tests for <behavior>.

Do not change production code unless required to make tests possible.

If production code changes are needed, explain why.
```

## Investigate without modifying

```text
Investigate <problem>.

Do not modify files.

Return:
- likely cause;
- relevant files;
- proposed fix;
- risk level;
- test plan.
```

## Update documentation after implementation

```text
Update documentation to reflect the implemented behavior.

Do not add marketing claims.

Do not claim legal compliance.

Keep terminology aligned with docs/DOMAIN_MODEL.md.
```
