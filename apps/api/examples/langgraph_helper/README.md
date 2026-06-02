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
