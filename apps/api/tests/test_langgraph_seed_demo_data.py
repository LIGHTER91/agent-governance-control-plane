import json

import pytest

from examples.langgraph_helper import seed_demo_data as seed


class FakeSeedClient:
    def __init__(
        self,
        *,
        agents: list[seed.JsonObject] | None = None,
        policies: list[seed.JsonObject] | None = None,
        rules: list[seed.JsonObject] | None = None,
    ) -> None:
        self.agents = list(agents or [])
        self.policies = list(policies or [])
        self.rules_by_policy: dict[str, list[seed.JsonObject]] = {}
        for rule in rules or []:
            self.rules_by_policy.setdefault(str(rule["policy_id"]), []).append(rule)
        self.calls: list[tuple[str, str, dict[str, object] | None]] = []

    def get_json(self, path: str) -> object:
        self.calls.append(("GET", path, None))
        if path == "/agents":
            return self.agents
        if path == "/policies":
            return self.policies
        if path.startswith("/policies/") and path.endswith("/rules"):
            policy_id = path.removeprefix("/policies/").removesuffix("/rules")
            return self.rules_by_policy.get(policy_id, [])
        raise AssertionError(f"Unexpected GET {path}")

    def post_json(
        self,
        path: str,
        payload: dict[str, object],
    ) -> seed.JsonObject:
        self.calls.append(("POST", path, dict(payload)))
        if path == "/agents":
            saved = {**payload, "id": "agent-001"}
            self.agents.append(saved)
            return saved
        if path == "/policies":
            saved = {**payload, "id": "policy-001"}
            self.policies.append(saved)
            return saved
        if path == "/policy-rules":
            policy_id = str(payload["policy_id"])
            saved = {
                **payload,
                "id": f"rule-{len(self.rules_by_policy.get(policy_id, [])) + 1}",
            }
            self.rules_by_policy.setdefault(policy_id, []).append(saved)
            return saved
        raise AssertionError(f"Unexpected POST {path}")

    def patch_json(
        self,
        path: str,
        payload: dict[str, object],
    ) -> seed.JsonObject:
        self.calls.append(("PATCH", path, dict(payload)))
        if path.startswith("/policy-rules/"):
            rule_id = path.removeprefix("/policy-rules/")
            for rules in self.rules_by_policy.values():
                for index, rule in enumerate(rules):
                    if rule["id"] == rule_id:
                        saved = {**rule, **payload}
                        rules[index] = saved
                        return saved
        raise AssertionError(f"Unexpected PATCH {path}")


def test_demo_plan_contains_only_local_fake_validation_records() -> None:
    plan = seed.build_demo_plan()

    assert plan.agent_payload["name"] == seed.DEMO_AGENT_NAME
    assert plan.agent_payload["framework"] == "LangGraph"
    assert plan.agent_payload["environment"] == "development"
    assert plan.policy_payload["name"] == seed.DEMO_POLICY_NAME
    assert [rule.tool_name for rule in plan.rules] == [
        "langgraph_helper_allow",
        "langgraph_helper_deny",
        "langgraph_helper_review",
    ]
    assert [rule.decision for rule in plan.rules] == [
        "allow",
        "deny",
        "require_human_review",
    ]
    serialized = json.dumps(
        {
            "agent": plan.agent_payload,
            "policy": plan.policy_payload,
            "rules": [rule.condition for rule in plan.rules],
        }
    ).lower()
    assert "api_key" not in serialized
    assert "secret" not in serialized
    assert "token" not in serialized


def test_apply_demo_seed_creates_missing_agent_policy_and_rules() -> None:
    client = FakeSeedClient()

    result = seed.apply_demo_seed(client, seed.build_demo_plan())

    assert result.agent_id == "agent-001"
    assert result.policy_id == "policy-001"
    assert [(record.entity_type, record.status) for record in result.records] == [
        ("agent", "created"),
        ("policy", "created"),
        ("policy_rule", "created"),
        ("policy_rule", "created"),
        ("policy_rule", "created"),
    ]
    assert [call[:2] for call in client.calls] == [
        ("GET", "/agents"),
        ("POST", "/agents"),
        ("GET", "/policies"),
        ("POST", "/policies"),
        ("GET", "/policies/policy-001/rules"),
        ("POST", "/policy-rules"),
        ("POST", "/policy-rules"),
        ("POST", "/policy-rules"),
    ]


def test_apply_demo_seed_reuses_existing_matching_records() -> None:
    plan = seed.build_demo_plan()
    policy_id = "policy-001"
    rules = [
        {**seed._rule_payload(policy_id=policy_id, rule=rule), "id": rule.scenario}
        for rule in plan.rules
    ]
    client = FakeSeedClient(
        agents=[{**plan.agent_payload, "id": "agent-001"}],
        policies=[{**plan.policy_payload, "id": policy_id}],
        rules=rules,
    )

    result = seed.apply_demo_seed(client, plan)

    assert all(record.status == "exists" for record in result.records)
    assert not any(call[0] in {"POST", "PATCH"} for call in client.calls)


def test_apply_demo_seed_updates_existing_mismatched_rule() -> None:
    plan = seed.build_demo_plan()
    policy_id = "policy-001"
    stale_rule = {
        **seed._rule_payload(policy_id=policy_id, rule=plan.rules[0]),
        "id": "rule-allow",
        "condition": json.dumps({"decision": "deny"}),
    }
    client = FakeSeedClient(
        agents=[{**plan.agent_payload, "id": "agent-001"}],
        policies=[{**plan.policy_payload, "id": policy_id}],
        rules=[stale_rule],
    )

    result = seed.apply_demo_seed(client, plan)

    assert ("policy_rule", "Local demo LangGraph helper allow rule", "updated") in [
        (record.entity_type, record.name, record.status) for record in result.records
    ]
    assert any(
        call[:2] == ("PATCH", "/policy-rules/rule-allow") for call in client.calls
    )


def test_main_dry_run_does_not_print_api_key(monkeypatch, capsys) -> None:
    monkeypatch.setenv("AGCP_SERVICE_ACTOR_API_KEY", "test-service-actor-key")

    exit_code = seed.main([])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "LangGraph helper demo seed (dry-run)" in captured.out
    assert "test-service-actor-key" not in captured.out
    assert "test-service-actor-key" not in captured.err


def test_duplicate_demo_names_are_rejected() -> None:
    with pytest.raises(seed.SeedError):
        seed._find_by_name(
            [{"name": seed.DEMO_AGENT_NAME}, {"name": seed.DEMO_AGENT_NAME}],
            seed.DEMO_AGENT_NAME,
        )
