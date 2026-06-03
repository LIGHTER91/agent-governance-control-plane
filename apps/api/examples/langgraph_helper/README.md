# LangGraph Helper Spike

This example is a small, dependency-free helper for LangGraph-style callers. It
shows where a graph node or tool wrapper can ask AGCP's Runtime Gateway for a
decision before the caller executes a local tool.

This is not a production adapter package and does not depend on LangGraph. AGCP
does not execute tools. The caller remains responsible for honoring
`proceed=false`, pausing for human review, and resuming only after a successful
Runtime Gateway resume check.

```python
import os

from examples.langgraph_helper import AGCPClient, governed_tool_call


def create_ticket(ticket_ref: str) -> dict[str, str]:
    return {"ticket_ref": ticket_ref, "status": "queued"}


client = AGCPClient(
    base_url="http://127.0.0.1:8000",
    api_key=os.environ["AGCP_SERVICE_ACTOR_API_KEY"],
)

result = governed_tool_call(
    client=client,
    tool=create_ticket,
    agent_id="11111111-1111-4111-8111-111111111111",
    run_id="22222222-2222-4222-8222-222222222222",
    request_id="support-run-001:create-ticket",
    correlation_id="support-run-001",
    tool_name="create_ticket",
    action_summary="Create an internal support ticket.",
    action_type="ticket_create",
    purpose="support_followup",
    environment="development",
    risk_level="medium",
    metadata={"langgraph_node": "support_followup"},
    tool_args=("ticket-draft-001",),
)

if result.branch == "allowed":
    tool_result = result.tool_result
elif result.branch == "requires_review":
    # Pause the graph and resume later through resume_after_approval(...).
    pass
else:
    # Denied or not applicable: stop or branch safely.
    pass
```

Send only bounded governance context such as IDs, tool/action labels, purpose,
environment, risk level, and safe metadata. Do not send secrets, credentials,
raw user prompts, raw source contents, retrieved chunks, or tool payloads.

Service actor keys should be read from environment or a secret manager and never
logged. A real adapter package should add retries, observability hooks, stronger
typing around LangGraph state, and setup guidance after this spike proves the
boundary.

## Local Runtime Gateway Validation

`validate_local_gateway.py` provides a local validation harness. It is still an
example, not a production SDK or a LangGraph package.

Dry-run mode uses in-memory Runtime Gateway responses and is safe to run without
starting the API:

```powershell
cd apps/api
uv run python examples/langgraph_helper/validate_local_gateway.py
```

Expected dry-run behavior:

- `allow` returns `branch=allowed` and executes the caller-owned fake tool.
- `deny` returns `branch=denied` and does not execute the fake tool.
- `review` returns `branch=requires_review` and does not execute the fake tool.
- resume dry-run calls the helper resume path and reports an approved allow
  response shape.

Live mode calls a local AGCP Runtime Gateway. Start the API with service auth
enabled and configure only hashed keys on the server side:

```powershell
cd apps/api
$env:AGCP_RUNTIME_ENFORCEMENT_ENABLED = "true"
$env:AGCP_REQUIRE_SERVICE_AUTH = "true"
$env:AGCP_SERVICE_ACTOR_API_KEY = "<set-a-local-random-secret>"
$digestBytes = [System.Security.Cryptography.SHA256]::HashData(
  [System.Text.Encoding]::UTF8.GetBytes($env:AGCP_SERVICE_ACTOR_API_KEY)
)
$digest = [System.BitConverter]::ToString($digestBytes).Replace("-", "").ToLower()
$env:AGCP_SERVICE_ACTOR_API_KEYS = "service:langgraph-local=sha256:$digest"
$env:AGCP_SERVICE_ACTOR_SCOPES = "service:langgraph-local=runtime:decision,runtime:resume"
$env:AGCP_SERVICE_ACTOR_SCOPE_RULES = '{"service:langgraph-local":{"environments":["development"],"runtime_modes":["simulation","enforcement"],"tool_names":["*"]}}'
uv run uvicorn agent_governance_api.main:app --reload
```

In another shell, provide an existing local Agent ID and run the validation. The
API key is read from the environment and is never printed by the script:

```powershell
cd apps/api
$env:AGCP_SERVICE_ACTOR_API_KEY = "<same-local-random-secret>"
$env:AGCP_LANGGRAPH_HELPER_AGENT_ID = "<existing-agent-uuid>"
$env:AGCP_LANGGRAPH_HELPER_RUN_ID = "<new-or-existing-run-uuid>"
$env:AGCP_LANGGRAPH_HELPER_BASE_URL = "http://127.0.0.1:8000"
$env:AGCP_LANGGRAPH_HELPER_MODE = "simulation"
uv run python examples/langgraph_helper/validate_local_gateway.py --live
```

Live output reports the actual decisions from your local policies. To validate
specific allow, deny, or human-review outcomes, configure local PolicyRules for
the tool names `langgraph_helper_allow`, `langgraph_helper_deny`, and
`langgraph_helper_review`, then run:

```powershell
uv run python examples/langgraph_helper/validate_local_gateway.py --live --scenarios allow,deny,review
```

Live resume validation is skipped unless you provide IDs from a real
HumanApproval flow:

```powershell
$env:AGCP_LANGGRAPH_HELPER_RESUME_ID = "<resume-id>"
$env:AGCP_LANGGRAPH_HELPER_ORIGINAL_REQUEST_ID = "<original-request-id>"
$env:AGCP_LANGGRAPH_HELPER_RESUME_TOOL_NAME = "<original-tool-name>"
$env:AGCP_LANGGRAPH_HELPER_HUMAN_APPROVAL_ID = "<human-approval-uuid>"
$env:AGCP_LANGGRAPH_HELPER_POLICY_DECISION_ID = "<policy-decision-uuid>"
$env:AGCP_LANGGRAPH_HELPER_ACTION_REF = "<original-action-ref>"
uv run python examples/langgraph_helper/validate_local_gateway.py --live
```

The script intentionally does not create Agents, Policies, PolicyRules, or
HumanApprovals. It validates the helper boundary against the local gateway while
keeping setup and caller-side enforcement explicit.
