# Agent Governance API

Minimal FastAPI backend for the Agent Governance Control Plane.

## Local commands

Install dependencies:

```bash
uv sync
```

Run the API:

```bash
uv run uvicorn agent_governance_api.main:app --reload
```

Run tests:

```bash
uv run pytest
```

Run lint and format checks:

```bash
uv run ruff check .
uv run ruff format --check .
```
