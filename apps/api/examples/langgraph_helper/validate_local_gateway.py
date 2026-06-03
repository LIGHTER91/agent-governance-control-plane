"""Validate the LangGraph helper against a local AGCP Runtime Gateway.

The script defaults to dry-run mode. Use ``--live`` only after starting the
local API and configuring a Service Actor API key through environment variables.
"""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from uuid import uuid4

if __package__ in {None, ""}:
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from examples.langgraph_helper import (  # noqa: E402
    AGCPClient,
    AGCPHelperError,
    GovernedToolResult,
    ResumeDecision,
    governed_tool_call,
    resume_after_approval,
)
from examples.langgraph_helper.helper import JsonObject  # noqa: E402

DEFAULT_BASE_URL = "http://127.0.0.1:8000"
DEFAULT_AGENT_ID = "11111111-1111-4111-8111-111111111111"
DEFAULT_RUN_ID = "22222222-2222-4222-8222-222222222222"
DEFAULT_POLICY_DECISION_ID = "66666666-6666-4666-8666-666666666666"
DEFAULT_HUMAN_APPROVAL_ID = "77777777-7777-4777-8777-777777777777"
SCENARIO_DECISIONS = {
    "allow": ("allow", True, None),
    "deny": ("deny", False, None),
    "review": ("require_human_review", False, DEFAULT_HUMAN_APPROVAL_ID),
}


@dataclass(frozen=True)
class ValidationConfig:
    base_url: str
    api_key: str | None
    agent_id: str
    run_id: str
    mode: str
    scenarios: tuple[str, ...]
    timeout_seconds: float

    @property
    def api_key_configured(self) -> bool:
        return self.api_key is not None


@dataclass(frozen=True)
class ScenarioRecord:
    scenario: str
    decision: str
    proceed: bool
    branch: str
    tool_executed: bool
    policy_decision_id: str | None
    human_approval_id: str | None


@dataclass(frozen=True)
class ResumeRecord:
    decision: str
    proceed: bool
    branch: str
    human_approval_status: str


class DryRunTransport:
    """In-memory transport that proves helper behavior without a server."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, JsonObject, dict[str, str], float]] = []

    def __call__(
        self,
        url: str,
        payload: JsonObject,
        headers: Mapping[str, str],
        timeout_seconds: float,
    ) -> JsonObject:
        self.calls.append((url, payload, dict(headers), timeout_seconds))
        if url.endswith("/runtime/tool-calls/resume"):
            return _dry_run_resume_response(payload)
        scenario = _scenario_from_request_id(str(payload["request_id"]))
        return _dry_run_decision_response(payload, scenario=scenario)


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    config = load_config(os.environ, args)

    try:
        if args.live:
            if not config.api_key_configured:
                print(
                    "Live validation requires AGCP_SERVICE_ACTOR_API_KEY. "
                    "The key is read from the environment and is not printed.",
                    file=sys.stderr,
                )
                return 2
            records = run_live_decision_validation(config)
            _print_records(records, live=True)
            resume_record = maybe_run_live_resume_validation(os.environ, config)
            if resume_record is None:
                print(
                    "Live resume validation skipped; set resume env vars after "
                    "creating and approving a HumanApproval."
                )
            else:
                _print_resume_record(resume_record, live=True)
            return 0

        records, resume_record = run_dry_run_validation(config)
        _print_records(records, live=False)
        _print_resume_record(resume_record, live=False)
        return 0
    except AGCPHelperError as exc:
        print(f"Validation failed: {exc}", file=sys.stderr)
        return 1


def load_config(
    environ: Mapping[str, str],
    args: argparse.Namespace,
) -> ValidationConfig:
    scenarios = _parse_scenarios(args.scenarios)
    return ValidationConfig(
        base_url=environ.get("AGCP_LANGGRAPH_HELPER_BASE_URL", DEFAULT_BASE_URL),
        api_key=environ.get("AGCP_SERVICE_ACTOR_API_KEY"),
        agent_id=environ.get("AGCP_LANGGRAPH_HELPER_AGENT_ID", DEFAULT_AGENT_ID),
        run_id=environ.get("AGCP_LANGGRAPH_HELPER_RUN_ID", DEFAULT_RUN_ID),
        mode=environ.get("AGCP_LANGGRAPH_HELPER_MODE", "simulation"),
        scenarios=scenarios,
        timeout_seconds=float(
            environ.get("AGCP_LANGGRAPH_HELPER_TIMEOUT_SECONDS", "5.0")
        ),
    )


def run_dry_run_validation(
    config: ValidationConfig,
) -> tuple[list[ScenarioRecord], ResumeRecord]:
    transport = DryRunTransport()
    client = AGCPClient(
        base_url=config.base_url,
        api_key=config.api_key,
        timeout_seconds=config.timeout_seconds,
        transport=transport,
    )
    records = [_run_scenario(client, config, scenario) for scenario in config.scenarios]
    resume_decision = resume_after_approval(
        client=client,
        resume_id="langgraph-helper-review:resume:001",
        original_request_id="langgraph-helper-review",
        agent_id=config.agent_id,
        run_id=config.run_id,
        tool_name="langgraph_helper_review",
        human_approval_id=DEFAULT_HUMAN_APPROVAL_ID,
        policy_decision_id=DEFAULT_POLICY_DECISION_ID,
        action_ref="local-validation-review",
        correlation_id="langgraph-helper-local-validation",
        metadata={"langgraph_node": "local_validation"},
    )
    return records, _resume_record(resume_decision)


def run_live_decision_validation(config: ValidationConfig) -> list[ScenarioRecord]:
    client = AGCPClient(
        base_url=config.base_url,
        api_key=config.api_key,
        timeout_seconds=config.timeout_seconds,
    )
    return [_run_scenario(client, config, scenario) for scenario in config.scenarios]


def maybe_run_live_resume_validation(
    environ: Mapping[str, str],
    config: ValidationConfig,
) -> ResumeRecord | None:
    required_names = (
        "AGCP_LANGGRAPH_HELPER_RESUME_ID",
        "AGCP_LANGGRAPH_HELPER_ORIGINAL_REQUEST_ID",
        "AGCP_LANGGRAPH_HELPER_RESUME_TOOL_NAME",
        "AGCP_LANGGRAPH_HELPER_HUMAN_APPROVAL_ID",
        "AGCP_LANGGRAPH_HELPER_POLICY_DECISION_ID",
        "AGCP_LANGGRAPH_HELPER_ACTION_REF",
    )
    if any(not environ.get(name) for name in required_names):
        return None

    client = AGCPClient(
        base_url=config.base_url,
        api_key=config.api_key,
        timeout_seconds=config.timeout_seconds,
    )
    decision = resume_after_approval(
        client=client,
        resume_id=environ["AGCP_LANGGRAPH_HELPER_RESUME_ID"],
        original_request_id=environ["AGCP_LANGGRAPH_HELPER_ORIGINAL_REQUEST_ID"],
        agent_id=config.agent_id,
        run_id=config.run_id,
        tool_name=environ["AGCP_LANGGRAPH_HELPER_RESUME_TOOL_NAME"],
        human_approval_id=environ["AGCP_LANGGRAPH_HELPER_HUMAN_APPROVAL_ID"],
        policy_decision_id=environ["AGCP_LANGGRAPH_HELPER_POLICY_DECISION_ID"],
        action_ref=environ["AGCP_LANGGRAPH_HELPER_ACTION_REF"],
        correlation_id=environ.get(
            "AGCP_LANGGRAPH_HELPER_CORRELATION_ID",
            "langgraph-helper-local-validation",
        ),
        metadata={"langgraph_node": "local_validation_resume"},
    )
    return _resume_record(decision)


def _run_scenario(
    client: AGCPClient,
    config: ValidationConfig,
    scenario: str,
) -> ScenarioRecord:
    tool_calls: list[str] = []

    def fake_tool(action_ref: str) -> dict[str, str]:
        tool_calls.append(action_ref)
        return {"action_ref": action_ref, "status": "executed_by_caller"}

    result = governed_tool_call(
        client=client,
        tool=fake_tool,
        agent_id=config.agent_id,
        run_id=config.run_id,
        request_id=_request_id(scenario),
        correlation_id="langgraph-helper-local-validation",
        tool_name=f"langgraph_helper_{scenario}",
        action_summary=f"Validate local LangGraph helper {scenario} scenario.",
        mode=config.mode,
        action_type="local_validation",
        purpose="integration_validation",
        environment="development",
        risk_level="low",
        metadata={"langgraph_node": "local_validation"},
        tool_args=(f"local-validation-{scenario}",),
    )
    return _scenario_record(
        scenario=scenario,
        result=result,
        tool_call_count=len(tool_calls),
    )


def _scenario_record(
    *,
    scenario: str,
    result: GovernedToolResult,
    tool_call_count: int,
) -> ScenarioRecord:
    if result.tool_executed and tool_call_count != 1:
        raise RuntimeError(
            "Allowed scenario did not execute the fake tool exactly once."
        )
    if not result.tool_executed and tool_call_count != 0:
        raise RuntimeError("Blocked scenario executed the fake tool.")

    return ScenarioRecord(
        scenario=scenario,
        decision=result.decision.decision,
        proceed=result.decision.proceed,
        branch=result.branch,
        tool_executed=result.tool_executed,
        policy_decision_id=result.decision.policy_decision_id,
        human_approval_id=result.decision.human_approval_id,
    )


def _resume_record(decision: ResumeDecision) -> ResumeRecord:
    return ResumeRecord(
        decision=decision.decision,
        proceed=decision.proceed,
        branch=decision.branch,
        human_approval_status=decision.human_approval_status,
    )


def _dry_run_decision_response(payload: JsonObject, *, scenario: str) -> JsonObject:
    decision, proceed, human_approval_id = SCENARIO_DECISIONS[scenario]
    return {
        "request_id": payload["request_id"],
        "agent_id": payload["agent_id"],
        "run_id": payload["run_id"],
        "tool_name": payload["tool_name"],
        "decision": decision,
        "proceed": proceed,
        "reason": f"Dry-run {scenario} validation response.",
        "trace_event_id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
        "policy_decision_id": DEFAULT_POLICY_DECISION_ID,
        "human_approval_id": human_approval_id,
    }


def _dry_run_resume_response(payload: JsonObject) -> JsonObject:
    return {
        "resume_id": payload["resume_id"],
        "original_request_id": payload["original_request_id"],
        "agent_id": payload["agent_id"],
        "run_id": payload["run_id"],
        "tool_name": payload["tool_name"],
        "decision": "allow",
        "proceed": True,
        "reason": "Dry-run resume validation response.",
        "human_approval_status": "approved",
        "trace_event_id": "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
        "policy_decision_id": payload["policy_decision_id"],
        "human_approval_id": payload["human_approval_id"],
    }


def _scenario_from_request_id(request_id: str) -> str:
    for scenario in SCENARIO_DECISIONS:
        if request_id.endswith(f":{scenario}"):
            return scenario
    return "allow"


def _request_id(scenario: str) -> str:
    return f"langgraph-helper-local-{uuid4()}:{scenario}"


def _parse_scenarios(raw_value: str) -> tuple[str, ...]:
    scenarios = tuple(
        dict.fromkeys(
            scenario.strip().lower()
            for scenario in raw_value.split(",")
            if scenario.strip()
        )
    )
    unsupported = sorted(
        scenario for scenario in scenarios if scenario not in SCENARIO_DECISIONS
    )
    if unsupported:
        raise ValueError(f"Unsupported scenarios: {', '.join(unsupported)}.")
    return scenarios or ("allow", "deny", "review")


def _print_records(records: Sequence[ScenarioRecord], *, live: bool) -> None:
    mode_label = "live" if live else "dry-run"
    print(f"LangGraph helper local validation ({mode_label})")
    for record in records:
        proceed = str(record.proceed).lower()
        tool_executed = str(record.tool_executed).lower()
        print(
            f"scenario={record.scenario} decision={record.decision} "
            f"proceed={proceed} branch={record.branch} "
            f"tool_executed={tool_executed} "
            f"policy_decision_id={record.policy_decision_id} "
            f"human_approval_id={record.human_approval_id}"
        )


def _print_resume_record(record: ResumeRecord, *, live: bool) -> None:
    mode_label = "live" if live else "dry-run"
    proceed = str(record.proceed).lower()
    print(
        f"resume={mode_label} decision={record.decision} proceed={proceed} "
        f"branch={record.branch} "
        f"human_approval_status={record.human_approval_status}"
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Validate the dependency-free LangGraph helper locally. Dry-run mode "
            "does not call AGCP; --live calls the configured Runtime Gateway."
        )
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Call the local AGCP Runtime Gateway instead of using dry-run responses.",
    )
    parser.add_argument(
        "--scenarios",
        default="allow,deny,review",
        help="Comma-separated scenarios to run: allow, deny, review.",
    )
    return parser


if __name__ == "__main__":
    raise SystemExit(main())
