"""Seed local demo data for LangGraph helper live validation.

This is a local demo helper, not production provisioning. It uses AGCP's public
local APIs so normal audit behavior remains visible.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from urllib import error as urllib_error
from urllib import request as urllib_request
from uuid import uuid4

DEFAULT_BASE_URL = "http://127.0.0.1:8000"
DEMO_AGENT_NAME = "Local demo LangGraph helper agent"
DEMO_POLICY_NAME = "Local demo LangGraph helper policy"
DEMO_OWNER_ID = "team:local-langgraph-helper-demo"


JsonObject = dict[str, object]


class SeedError(Exception):
    """Raised when local demo seed data cannot be created safely."""


@dataclass(frozen=True)
class DemoRule:
    scenario: str
    name: str
    tool_name: str
    decision: str
    reason: str

    @property
    def condition(self) -> dict[str, str]:
        return {
            "decision": self.decision,
            "reason": self.reason,
            "tool_name": self.tool_name,
        }


@dataclass(frozen=True)
class DemoPlan:
    agent_payload: JsonObject
    policy_payload: JsonObject
    rules: tuple[DemoRule, ...]


@dataclass(frozen=True)
class SeedRecord:
    entity_type: str
    name: str
    entity_id: str
    status: str


@dataclass(frozen=True)
class SeedResult:
    agent_id: str
    policy_id: str
    records: tuple[SeedRecord, ...]


class LocalAGCPApiClient:
    def __init__(self, *, base_url: str, timeout_seconds: float = 5.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def get_json(self, path: str) -> object:
        return self._request_json("GET", path)

    def post_json(self, path: str, payload: Mapping[str, object]) -> JsonObject:
        response = self._request_json("POST", path, payload)
        if not isinstance(response, dict):
            raise SeedError("AGCP returned a non-object response.")
        return response

    def patch_json(self, path: str, payload: Mapping[str, object]) -> JsonObject:
        response = self._request_json("PATCH", path, payload)
        if not isinstance(response, dict):
            raise SeedError("AGCP returned a non-object response.")
        return response

    def _request_json(
        self,
        method: str,
        path: str,
        payload: Mapping[str, object] | None = None,
    ) -> object:
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        request = urllib_request.Request(
            f"{self.base_url}{path}",
            data=data,
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            method=method,
        )
        try:
            with urllib_request.urlopen(
                request,
                timeout=self.timeout_seconds,
            ) as response:
                body = response.read().decode("utf-8")
        except urllib_error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            detail = _response_detail(body)
            raise SeedError(f"AGCP {method} {path} failed: {detail}") from exc
        except urllib_error.URLError as exc:
            raise SeedError("Could not reach the local AGCP API.") from exc

        if not body:
            return {}
        try:
            return json.loads(body)
        except json.JSONDecodeError as exc:
            raise SeedError("AGCP returned malformed JSON.") from exc


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    plan = build_demo_plan()
    base_url = args.base_url or os.environ.get(
        "AGCP_LANGGRAPH_HELPER_BASE_URL",
        DEFAULT_BASE_URL,
    )

    if not args.apply:
        _print_dry_run(plan, base_url=base_url)
        return 0

    try:
        result = apply_demo_seed(
            LocalAGCPApiClient(
                base_url=base_url,
                timeout_seconds=args.timeout_seconds,
            ),
            plan,
        )
    except SeedError as exc:
        print(f"Demo seed failed: {exc}", file=sys.stderr)
        return 1

    _print_seed_result(result, base_url=base_url)
    return 0


def build_demo_plan() -> DemoPlan:
    return DemoPlan(
        agent_payload={
            "name": DEMO_AGENT_NAME,
            "description": (
                "Local-only demo Agent for LangGraph helper Runtime Gateway validation."
            ),
            "owner_type": "team",
            "owner_id": DEMO_OWNER_ID,
            "owner_name": "Local LangGraph Helper Demo",
            "owner_contact_email": None,
            "environment": "development",
            "status": "active",
            "risk_level": "low",
            "framework": "LangGraph",
        },
        policy_payload={
            "name": DEMO_POLICY_NAME,
            "description": ("Local-only demo policy for LangGraph helper validation."),
            "status": "active",
        },
        rules=(
            DemoRule(
                scenario="allow",
                name="Local demo LangGraph helper allow rule",
                tool_name="langgraph_helper_allow",
                decision="allow",
                reason="Local demo allows the LangGraph helper allow tool.",
            ),
            DemoRule(
                scenario="deny",
                name="Local demo LangGraph helper deny rule",
                tool_name="langgraph_helper_deny",
                decision="deny",
                reason="Local demo denies the LangGraph helper deny tool.",
            ),
            DemoRule(
                scenario="review",
                name="Local demo LangGraph helper review rule",
                tool_name="langgraph_helper_review",
                decision="require_human_review",
                reason=(
                    "Local demo requires human review for the LangGraph helper "
                    "review tool."
                ),
            ),
        ),
    )


def apply_demo_seed(
    client: object,
    plan: DemoPlan,
) -> SeedResult:
    records: list[SeedRecord] = []
    agent, agent_status = _ensure_named_resource(
        client,
        list_path="/agents",
        create_path="/agents",
        patch_path_template="/agents/{id}",
        name=str(plan.agent_payload["name"]),
        payload=plan.agent_payload,
    )
    records.append(
        SeedRecord(
            entity_type="agent",
            name=str(agent["name"]),
            entity_id=str(agent["id"]),
            status=agent_status,
        )
    )

    policy, policy_status = _ensure_named_resource(
        client,
        list_path="/policies",
        create_path="/policies",
        patch_path_template="/policies/{id}",
        name=str(plan.policy_payload["name"]),
        payload=plan.policy_payload,
    )
    policy_id = str(policy["id"])
    records.append(
        SeedRecord(
            entity_type="policy",
            name=str(policy["name"]),
            entity_id=policy_id,
            status=policy_status,
        )
    )

    existing_rules = _list_objects(client.get_json(f"/policies/{policy_id}/rules"))
    for rule in plan.rules:
        payload = _rule_payload(policy_id=policy_id, rule=rule)
        existing_rule = _find_by_name(existing_rules, rule.name)
        if existing_rule is None:
            saved_rule = client.post_json("/policy-rules", payload)
            rule_status = "created"
        elif _needs_update(existing_rule, payload):
            saved_rule = client.patch_json(
                f"/policy-rules/{existing_rule['id']}", payload
            )
            rule_status = "updated"
        else:
            saved_rule = existing_rule
            rule_status = "exists"

        records.append(
            SeedRecord(
                entity_type="policy_rule",
                name=str(saved_rule["name"]),
                entity_id=str(saved_rule["id"]),
                status=rule_status,
            )
        )

    return SeedResult(
        agent_id=str(agent["id"]),
        policy_id=policy_id,
        records=tuple(records),
    )


def _ensure_named_resource(
    client: object,
    *,
    list_path: str,
    create_path: str,
    patch_path_template: str,
    name: str,
    payload: Mapping[str, object],
) -> tuple[JsonObject, str]:
    existing = _find_by_name(_list_objects(client.get_json(list_path)), name)
    if existing is None:
        return client.post_json(create_path, payload), "created"
    if _needs_update(existing, payload):
        path = patch_path_template.format(id=existing["id"])
        return client.patch_json(path, payload), "updated"
    return existing, "exists"


def _rule_payload(*, policy_id: str, rule: DemoRule) -> JsonObject:
    return {
        "policy_id": policy_id,
        "name": rule.name,
        "description": f"Local-only demo rule for {rule.scenario} validation.",
        "condition": json.dumps(rule.condition, sort_keys=True),
    }


def _needs_update(
    existing: Mapping[str, object], payload: Mapping[str, object]
) -> bool:
    return any(existing.get(key) != value for key, value in payload.items())


def _list_objects(response: object) -> list[JsonObject]:
    if not isinstance(response, list):
        raise SeedError("AGCP returned a non-list response.")
    objects: list[JsonObject] = []
    for item in response:
        if not isinstance(item, dict):
            raise SeedError("AGCP returned a list with non-object items.")
        objects.append(item)
    return objects


def _find_by_name(
    items: Sequence[Mapping[str, object]], name: str
) -> JsonObject | None:
    matches = [dict(item) for item in items if item.get("name") == name]
    if len(matches) > 1:
        raise SeedError(f"Multiple local demo records named {name!r} exist.")
    return matches[0] if matches else None


def _print_dry_run(plan: DemoPlan, *, base_url: str) -> None:
    print("LangGraph helper demo seed (dry-run)")
    print(f"base_url={base_url}")
    print(f"agent={plan.agent_payload['name']}")
    print(f"policy={plan.policy_payload['name']}")
    for rule in plan.rules:
        print(f"rule={rule.name} tool_name={rule.tool_name} decision={rule.decision}")
    print("Run with --apply to create or update only these local demo records.")


def _print_seed_result(result: SeedResult, *, base_url: str) -> None:
    print("LangGraph helper demo seed applied")
    print(f"base_url={base_url}")
    for record in result.records:
        print(
            f"{record.entity_type}={record.name} id={record.entity_id} "
            f"status={record.status}"
        )
    run_id = uuid4()
    print("Use these values for live validation:")
    print(f'$env:AGCP_LANGGRAPH_HELPER_AGENT_ID = "{result.agent_id}"')
    print(f'$env:AGCP_LANGGRAPH_HELPER_RUN_ID = "{run_id}"')
    print('$env:AGCP_LANGGRAPH_HELPER_MODE = "simulation"')
    print(
        "uv run python examples/langgraph_helper/validate_local_gateway.py "
        "--live --scenarios allow,deny,review"
    )


def _response_detail(body: str) -> str:
    try:
        parsed = json.loads(body)
    except json.JSONDecodeError:
        return body or "HTTP request failed."
    if isinstance(parsed, dict):
        detail = parsed.get("detail")
        if isinstance(detail, str):
            return detail
    return body or "HTTP request failed."


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Seed local-only demo Agent and PolicyRules for LangGraph helper "
            "live validation."
        )
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Create or update the local demo records through the local AGCP API.",
    )
    parser.add_argument(
        "--base-url",
        default=None,
        help=(
            "Local AGCP API base URL. Defaults to AGCP_LANGGRAPH_HELPER_BASE_URL "
            "or http://127.0.0.1:8000."
        ),
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=5.0,
        help="HTTP timeout for local AGCP API calls.",
    )
    return parser


if __name__ == "__main__":
    raise SystemExit(main())
