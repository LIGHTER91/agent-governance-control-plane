# Start here

This repo is prepared to make Codex useful without letting it take the project in the wrong direction.

## What this repo gives you

- Product framing for Agent Governance Control Plane.
- Clear boundaries: governance/control plane, not orchestration.
- Architecture principles for a V0 that can grow into a complete platform.
- Codex rules in `AGENTS.md`.
- GitHub issue templates.
- Initial GitHub issues ready to copy or create with `gh`.
- PR template forcing tests, scope control, and risk reporting.

## Recommended workflow

```text
Product idea
  ↓
Trello / roadmap note
  ↓
GitHub issue with exact scope
  ↓
Codex implementation
  ↓
PR with tests and summary
  ↓
Human review
  ↓
Merge
```

## Golden rule

Codex can execute, refactor, test, and document.

Codex must not own:

- product strategy;
- legal interpretation;
- final architecture decisions;
- acceptance of security-sensitive code;
- definition of "done".
