import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from agent_governance_api.models import (
    Environment,
    Policy,
    PolicyDecisionValue,
    PolicyRule,
    PolicyStatus,
    RiskLevel,
)
from agent_governance_api.policy_evaluator import PolicyEvaluationRule

SUPPORTED_CONDITION_FIELDS = frozenset(
    {
        "decision",
        "reason",
        "agent_id",
        "tool_name",
        "environment",
        "risk_level",
    }
)


class UnsupportedPolicyRuleConditionError(ValueError):
    pass


def load_active_policy_evaluation_rules(session: Session) -> list[PolicyEvaluationRule]:
    statement = (
        select(Policy, PolicyRule)
        .join(PolicyRule, PolicyRule.policy_id == Policy.id)
        .where(Policy.status == PolicyStatus.ACTIVE)
        .order_by(Policy.created_at, Policy.id, PolicyRule.created_at, PolicyRule.id)
    )

    return [
        convert_policy_rule_to_evaluation_rule(policy, rule)
        for policy, rule in session.execute(statement).all()
    ]


def convert_policy_rule_to_evaluation_rule(
    policy: Policy,
    rule: PolicyRule,
) -> PolicyEvaluationRule:
    condition = _validated_condition(rule.condition)

    return PolicyEvaluationRule(
        policy_id=policy.id,
        rule_id=rule.id,
        decision=_decision(condition),
        reason=_required_text(condition, "reason"),
        agent_id=_optional_text(condition, "agent_id"),
        tool_name=_optional_text(condition, "tool_name"),
        environment=_environment(condition),
        risk_level=_risk_level(condition),
    )


def validate_policy_rule_condition(condition: str) -> str:
    _validated_condition(condition)
    return condition


def _validated_condition(condition: str) -> dict[str, Any]:
    parsed = _parse_condition(condition)
    _reject_unsupported_fields(parsed)
    _decision(parsed)
    _required_text(parsed, "reason")
    _optional_text(parsed, "agent_id")
    _optional_text(parsed, "tool_name")
    _environment(parsed)
    _risk_level(parsed)
    return parsed


def _parse_condition(condition: str) -> dict[str, Any]:
    try:
        parsed = json.loads(condition)
    except json.JSONDecodeError as exc:
        raise UnsupportedPolicyRuleConditionError(
            "PolicyRule condition must be a JSON object."
        ) from exc

    if not isinstance(parsed, dict):
        raise UnsupportedPolicyRuleConditionError(
            "PolicyRule condition must be a JSON object."
        )
    return parsed


def _reject_unsupported_fields(condition: dict[str, Any]) -> None:
    unsupported_fields = sorted(set(condition) - SUPPORTED_CONDITION_FIELDS)
    if unsupported_fields:
        joined_fields = ", ".join(unsupported_fields)
        raise UnsupportedPolicyRuleConditionError(
            f"Unsupported PolicyRule condition fields: {joined_fields}."
        )


def _decision(condition: dict[str, Any]) -> PolicyDecisionValue:
    value = _required_text(condition, "decision")
    try:
        return PolicyDecisionValue(value)
    except ValueError as exc:
        raise UnsupportedPolicyRuleConditionError(
            f"Unsupported PolicyRule decision: {value}."
        ) from exc


def _environment(condition: dict[str, Any]) -> Environment | None:
    value = _optional_text(condition, "environment")
    if value is None:
        return None
    try:
        return Environment(value)
    except ValueError as exc:
        raise UnsupportedPolicyRuleConditionError(
            f"Unsupported PolicyRule environment: {value}."
        ) from exc


def _risk_level(condition: dict[str, Any]) -> RiskLevel | None:
    value = _optional_text(condition, "risk_level")
    if value is None:
        return None
    try:
        return RiskLevel(value)
    except ValueError as exc:
        raise UnsupportedPolicyRuleConditionError(
            f"Unsupported PolicyRule risk_level: {value}."
        ) from exc


def _required_text(condition: dict[str, Any], key: str) -> str:
    value = _optional_text(condition, key)
    if value is None:
        raise UnsupportedPolicyRuleConditionError(
            f"PolicyRule condition requires a non-empty {key}."
        )
    return value


def _optional_text(condition: dict[str, Any], key: str) -> str | None:
    value = condition.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise UnsupportedPolicyRuleConditionError(
            f"PolicyRule condition field {key} must be a non-empty string."
        )
    return value
