import json
import os

import pytest

from examples.langgraph_helper import AGCPClient
from examples.langgraph_helper import validate_local_gateway as validation


def test_dry_run_validation_exercises_allow_deny_review_and_resume() -> None:
    config = validation.ValidationConfig(
        base_url="http://agcp.local",
        api_key=None,
        agent_id=validation.DEFAULT_AGENT_ID,
        run_id=validation.DEFAULT_RUN_ID,
        mode="simulation",
        scenarios=("allow", "deny", "review"),
        timeout_seconds=1.0,
    )

    records, resume_record = validation.run_dry_run_validation(config)

    assert [(record.scenario, record.branch) for record in records] == [
        ("allow", "allowed"),
        ("deny", "denied"),
        ("review", "requires_review"),
    ]
    assert [record.tool_executed for record in records] == [True, False, False]
    assert records[2].human_approval_id == validation.DEFAULT_HUMAN_APPROVAL_ID
    assert resume_record.branch == "allowed"
    assert resume_record.human_approval_status == "approved"


def test_dry_run_scenario_sends_safe_runtime_gateway_payload() -> None:
    transport = validation.DryRunTransport()
    client = AGCPClient(
        base_url="http://agcp.local",
        api_key="test-service-actor-key",
        timeout_seconds=3.0,
        transport=transport,
    )
    config = validation.ValidationConfig(
        base_url="http://agcp.local",
        api_key="test-service-actor-key",
        agent_id=validation.DEFAULT_AGENT_ID,
        run_id=validation.DEFAULT_RUN_ID,
        mode="simulation",
        scenarios=("allow",),
        timeout_seconds=3.0,
    )

    record = validation._run_scenario(client, config, "allow")

    assert record.branch == "allowed"
    assert len(transport.calls) == 1
    url, payload, headers, timeout_seconds = transport.calls[0]
    assert url == "http://agcp.local/runtime/tool-calls/decision"
    assert headers["X-AGCP-API-Key"] == "test-service-actor-key"
    assert timeout_seconds == 3.0
    assert payload["agent_id"] == validation.DEFAULT_AGENT_ID
    assert payload["run_id"] == validation.DEFAULT_RUN_ID
    assert payload["tool_name"] == "langgraph_helper_allow"
    assert payload["mode"] == "simulation"
    assert payload["metadata"] == {
        "langgraph_node": "local_validation",
        "environment": "development",
        "risk_level": "low",
    }
    assert_no_unsafe_payload_fields(payload)


def test_main_dry_run_does_not_print_api_key(monkeypatch, capsys) -> None:
    monkeypatch.setenv("AGCP_SERVICE_ACTOR_API_KEY", "test-service-actor-key")
    monkeypatch.setenv("AGCP_LANGGRAPH_HELPER_BASE_URL", "http://agcp.local")

    exit_code = validation.main([])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "LangGraph helper local validation (dry-run)" in captured.out
    assert "test-service-actor-key" not in captured.out
    assert "test-service-actor-key" not in captured.err


def test_main_live_requires_api_key_without_printing_secret(
    monkeypatch, capsys
) -> None:
    monkeypatch.delenv("AGCP_SERVICE_ACTOR_API_KEY", raising=False)

    exit_code = validation.main(["--live"])

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "requires AGCP_SERVICE_ACTOR_API_KEY" in captured.err
    assert "X-AGCP-API-Key" not in captured.err


def test_load_config_uses_environment_without_defaulting_to_live_secrets(
    monkeypatch,
) -> None:
    monkeypatch.setenv("AGCP_LANGGRAPH_HELPER_BASE_URL", "http://127.0.0.1:9000")
    monkeypatch.setenv("AGCP_SERVICE_ACTOR_API_KEY", "test-service-actor-key")
    monkeypatch.setenv("AGCP_LANGGRAPH_HELPER_AGENT_ID", validation.DEFAULT_AGENT_ID)
    monkeypatch.setenv("AGCP_LANGGRAPH_HELPER_RUN_ID", validation.DEFAULT_RUN_ID)
    monkeypatch.setenv("AGCP_LANGGRAPH_HELPER_MODE", "enforcement")
    parser = validation._build_parser()
    args = parser.parse_args(["--scenarios", "allow,deny"])

    config = validation.load_config(dict(os.environ), args)

    assert config.base_url == "http://127.0.0.1:9000"
    assert config.api_key_configured is True
    assert config.agent_id == validation.DEFAULT_AGENT_ID
    assert config.run_id == validation.DEFAULT_RUN_ID
    assert config.mode == "enforcement"
    assert config.scenarios == ("allow", "deny")


def test_live_resume_validation_skips_when_resume_env_is_missing() -> None:
    config = validation.ValidationConfig(
        base_url="http://agcp.local",
        api_key="test-service-actor-key",
        agent_id=validation.DEFAULT_AGENT_ID,
        run_id=validation.DEFAULT_RUN_ID,
        mode="simulation",
        scenarios=("allow",),
        timeout_seconds=1.0,
    )

    assert validation.maybe_run_live_resume_validation({}, config) is None


@pytest.mark.parametrize("raw_scenarios", ["unknown", "allow,unknown"])
def test_parse_scenarios_rejects_unknown_values(raw_scenarios: str) -> None:
    with pytest.raises(ValueError):
        validation._parse_scenarios(raw_scenarios)


def assert_no_unsafe_payload_fields(payload: dict[str, object]) -> None:
    serialized = json.dumps(payload).lower()
    unsafe_terms = (
        "api_key",
        "authorization",
        "chunk",
        "credential",
        "password",
        "prompt",
        "raw_content",
        "source_content",
        "secret",
        "token",
    )
    for term in unsafe_terms:
        assert term not in serialized
