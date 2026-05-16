# V0 Governance Flow Demo

This backend-only demo shows the first complete governance path for the Agent
Governance Control Plane. It is implemented as an executable pytest scenario in
`apps/api/tests/test_v0_governance_flow.py`.

The demo answers these product questions:

- Which agent exists?
- What is the agent allowed or required to do for a tool request?
- What did the agent actually request?
- Which policy decision was recorded?
- Was human oversight requested?
- What evidence can be exported for review?

## Scenario

1. Create an Agent through `POST /agents`.
2. Insert an active Policy and Policy Rule requiring human review for
   `metadata.tool_name = "send_email"`.
3. Ingest a `tool_call_requested` event through `POST /telemetry/events`.
4. Verify an `AgentRunRecord` and `TraceEventRecord` are created.
5. Verify a `PolicyDecision` is created with `require_human_review`.
6. Verify a pending `HumanApproval` is created and linked to the
   `PolicyDecision`.
7. Verify a `human_approval_requested` `AuditLog` is created.
8. Export `GET /agents/{agent_id}/evidence-bundle`.
9. Verify the Evidence Bundle links the chain by ID:
   `TraceEventRecord.id -> PolicyDecision.trace_event_id`,
   `PolicyDecision.id -> HumanApproval.policy_decision_id`, and
   `HumanApproval.id -> AuditLog.entity_id`.

## Run It

From `apps/api`:

```bash
uv run pytest tests/test_v0_governance_flow.py
```

The demo is intentionally local and deterministic. It does not add a frontend,
authentication, notifications, runtime blocking, Docker, external policy engines,
or legal compliance claims.
