from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from agent_governance_api.models import (
    Environment,
    PolicyDecisionValue,
    RiskLevel,
)

ContextValue = str | UUID | StrEnum | None

DECISION_PRECEDENCE = {
    PolicyDecisionValue.DENY: 3,
    PolicyDecisionValue.REQUIRE_HUMAN_REVIEW: 2,
    PolicyDecisionValue.ALLOW: 1,
    PolicyDecisionValue.NOT_APPLICABLE: 0,
}


@dataclass(frozen=True, slots=True)
class PolicyEvaluationRule:
    decision: PolicyDecisionValue | str
    reason: str
    policy_id: str | UUID | None = None
    rule_id: str | UUID | None = None
    agent_id: str | UUID | None = None
    tool_name: str | None = None
    environment: Environment | str | None = None
    risk_level: RiskLevel | str | None = None


@dataclass(frozen=True, slots=True)
class PolicyEvaluationResult:
    decision: PolicyDecisionValue
    reason: str
    agent_id: str
    policy_id: str | UUID | None = None
    rule_id: str | UUID | None = None


def evaluate_policy(
    *,
    agent_context: Mapping[str, object],
    action_context: Mapping[str, object],
    environment: Environment | str,
    risk_level: RiskLevel | str,
    rules: Iterable[PolicyEvaluationRule],
) -> PolicyEvaluationResult:
    agent_id = _required_context_value(agent_context, "agent_id")
    tool_name = _optional_context_value(action_context, "tool_name")

    matching_rules: list[tuple[tuple[int, int, int], PolicyEvaluationRule]] = []
    for index, rule in enumerate(rules):
        if _rule_matches(
            rule,
            agent_id=agent_id,
            tool_name=tool_name,
            environment=environment,
            risk_level=risk_level,
        ):
            decision = PolicyDecisionValue(rule.decision)
            rank = (
                DECISION_PRECEDENCE[decision],
                _specificity(rule),
                -index,
            )
            matching_rules.append((rank, rule))

    if not matching_rules:
        return PolicyEvaluationResult(
            decision=PolicyDecisionValue.NOT_APPLICABLE,
            reason="No policy rule matched the request.",
            agent_id=str(agent_id),
        )

    _, selected_rule = max(matching_rules, key=lambda item: item[0])
    return PolicyEvaluationResult(
        decision=PolicyDecisionValue(selected_rule.decision),
        reason=selected_rule.reason,
        agent_id=str(agent_id),
        policy_id=selected_rule.policy_id,
        rule_id=selected_rule.rule_id,
    )


def _rule_matches(
    rule: PolicyEvaluationRule,
    *,
    agent_id: ContextValue,
    tool_name: ContextValue,
    environment: ContextValue,
    risk_level: ContextValue,
) -> bool:
    return (
        _matches(rule.agent_id, agent_id)
        and _matches(rule.tool_name, tool_name)
        and _matches(rule.environment, environment)
        and _matches(rule.risk_level, risk_level)
    )


def _matches(expected: ContextValue, actual: ContextValue) -> bool:
    if expected is None:
        return True
    if actual is None:
        return False
    return _normalize(expected) == _normalize(actual)


def _specificity(rule: PolicyEvaluationRule) -> int:
    return sum(
        value is not None
        for value in (
            rule.agent_id,
            rule.tool_name,
            rule.environment,
            rule.risk_level,
        )
    )


def _required_context_value(
    context: Mapping[str, object],
    key: str,
) -> ContextValue:
    value = context.get(key)
    if value is None:
        raise ValueError(f"{key} is required in policy evaluation context.")
    return _context_value(value)


def _optional_context_value(
    context: Mapping[str, object],
    key: str,
) -> ContextValue:
    value = context.get(key)
    if value is None:
        return None
    return _context_value(value)


def _context_value(value: object) -> ContextValue:
    if isinstance(value, str | UUID | StrEnum):
        return value
    raise TypeError(
        "Policy evaluation context values must be strings, UUIDs, or enums."
    )


def _normalize(value: ContextValue) -> str:
    if isinstance(value, StrEnum):
        return value.value
    return str(value)
