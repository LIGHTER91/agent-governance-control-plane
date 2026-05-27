from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from agent_governance_api.models import (
    DataUsageClassification,
    Environment,
    PolicyDecisionValue,
    RiskLevel,
)

ContextScalar = str | UUID | StrEnum | bool
ContextValue = ContextScalar | None
SourceContextScalar = str | UUID | StrEnum

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
    action_type: str | None = None
    capability_id: str | UUID | None = None
    source_id: str | UUID | None = None
    source_ids: tuple[str | UUID, ...] | None = None
    model_id: str | UUID | None = None
    purpose: str | None = None
    data_classification: DataUsageClassification | str | None = None
    contains_personal_data: bool | None = None
    contains_sensitive_data: bool | None = None


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
    action_type = _optional_context_value(action_context, "action_type")
    capability_id = _optional_context_value(action_context, "capability_id")
    source_ids = _source_context_values(action_context)
    model_id = _optional_context_value(action_context, "model_id")
    purpose = _optional_context_value(action_context, "purpose")
    data_classification = _optional_context_value(
        action_context,
        "data_classification",
    )
    contains_personal_data = _optional_context_value(
        action_context,
        "contains_personal_data",
    )
    contains_sensitive_data = _optional_context_value(
        action_context,
        "contains_sensitive_data",
    )

    matching_rules: list[tuple[tuple[int, int, int], PolicyEvaluationRule]] = []
    for index, rule in enumerate(rules):
        if _rule_matches(
            rule,
            agent_id=agent_id,
            tool_name=tool_name,
            environment=environment,
            risk_level=risk_level,
            action_type=action_type,
            capability_id=capability_id,
            source_ids=source_ids,
            model_id=model_id,
            purpose=purpose,
            data_classification=data_classification,
            contains_personal_data=contains_personal_data,
            contains_sensitive_data=contains_sensitive_data,
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
    action_type: ContextValue,
    capability_id: ContextValue,
    source_ids: tuple[SourceContextScalar, ...],
    model_id: ContextValue,
    purpose: ContextValue,
    data_classification: ContextValue,
    contains_personal_data: ContextValue,
    contains_sensitive_data: ContextValue,
) -> bool:
    return (
        _matches(rule.agent_id, agent_id)
        and _matches(rule.tool_name, tool_name)
        and _matches(rule.environment, environment)
        and _matches(rule.risk_level, risk_level)
        and _matches(rule.action_type, action_type)
        and _matches(rule.capability_id, capability_id)
        and _source_matches(
            source_id=rule.source_id,
            source_ids=rule.source_ids,
            actual_source_ids=source_ids,
        )
        and _matches(rule.model_id, model_id)
        and _matches(rule.purpose, purpose)
        and _matches(rule.data_classification, data_classification)
        and _matches(rule.contains_personal_data, contains_personal_data)
        and _matches(rule.contains_sensitive_data, contains_sensitive_data)
    )


def _matches(expected: ContextValue, actual: ContextValue) -> bool:
    if expected is None:
        return True
    if actual is None:
        return False
    return _normalize(expected) == _normalize(actual)


def _source_matches(
    *,
    source_id: str | UUID | None,
    source_ids: tuple[str | UUID, ...] | None,
    actual_source_ids: tuple[SourceContextScalar, ...],
) -> bool:
    if source_id is None and source_ids is None:
        return True
    if not actual_source_ids:
        return False

    expected_ids: list[str | UUID] = []
    if source_id is not None:
        expected_ids.append(source_id)
    if source_ids:
        expected_ids.extend(source_ids)

    actual = {_normalize(source) for source in actual_source_ids}
    return any(_normalize(expected) in actual for expected in expected_ids)


def _specificity(rule: PolicyEvaluationRule) -> int:
    return sum(
        value is not None
        for value in (
            rule.agent_id,
            rule.tool_name,
            rule.environment,
            rule.risk_level,
            rule.action_type,
            rule.capability_id,
            rule.source_id,
            rule.model_id,
            rule.purpose,
            rule.data_classification,
            rule.contains_personal_data,
            rule.contains_sensitive_data,
        )
    ) + int(bool(rule.source_ids))


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
    if isinstance(value, str | UUID | StrEnum | bool):
        return value
    raise TypeError(
        "Policy evaluation context values must be strings, UUIDs, enums, or booleans."
    )


def _source_context_values(
    action_context: Mapping[str, object],
) -> tuple[SourceContextScalar, ...]:
    source_id = action_context.get("source_id")
    source_ids = action_context.get("source_ids")
    values: list[SourceContextScalar] = []

    if source_id is not None:
        values.append(_source_context_value(source_id))

    if source_ids is None:
        return tuple(values)
    if isinstance(source_ids, str | UUID | StrEnum):
        values.append(_source_context_value(source_ids))
        return tuple(values)
    if isinstance(source_ids, Mapping):
        raise TypeError(
            "Policy evaluation source_ids context must be a string, UUID, enum, "
            "or iterable of strings, UUIDs, or enums."
        )
    if isinstance(source_ids, Iterable):
        values.extend(_source_context_value(value) for value in source_ids)
        return tuple(values)

    raise TypeError(
        "Policy evaluation source_ids context must be a string, UUID, enum, "
        "or iterable of strings, UUIDs, or enums."
    )


def _source_context_value(value: object) -> SourceContextScalar:
    if isinstance(value, str | UUID | StrEnum):
        return value
    raise TypeError(
        "Policy evaluation source identifiers must be strings, UUIDs, or enums."
    )


def _normalize(value: ContextScalar) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, StrEnum):
        return value.value
    return str(value)
