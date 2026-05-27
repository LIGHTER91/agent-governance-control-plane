import json
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from agent_governance_api.models import (
    DataUsageClassification,
    Environment,
    Policy,
    PolicyDecisionValue,
    PolicyRule,
    PolicyStatus,
    RiskLevel,
)
from agent_governance_api.policy_evaluator import PolicyEvaluationRule
from agent_governance_api.runtime_gateway import CONTEXT_LABEL_PATTERN

SUPPORTED_CONDITION_FIELDS = frozenset(
    {
        "decision",
        "reason",
        "agent_id",
        "tool_name",
        "environment",
        "risk_level",
        "action_type",
        "capability_id",
        "source_id",
        "source_ids",
        "model_id",
        "purpose",
        "data_classification",
        "contains_personal_data",
        "contains_sensitive_data",
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
        action_type=_optional_context_label(condition, "action_type"),
        capability_id=_optional_uuid_text(condition, "capability_id"),
        source_id=_optional_uuid_text(condition, "source_id"),
        source_ids=_optional_uuid_text_tuple(condition, "source_ids"),
        model_id=_optional_uuid_text(condition, "model_id"),
        purpose=_optional_context_label(condition, "purpose"),
        data_classification=_data_classification(condition),
        contains_personal_data=_optional_bool(condition, "contains_personal_data"),
        contains_sensitive_data=_optional_bool(condition, "contains_sensitive_data"),
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
    _optional_context_label(parsed, "action_type")
    _optional_uuid_text(parsed, "capability_id")
    source_id = _optional_uuid_text(parsed, "source_id")
    source_ids = _optional_uuid_text_tuple(parsed, "source_ids")
    if source_id is not None and source_ids is not None:
        raise UnsupportedPolicyRuleConditionError(
            "PolicyRule condition cannot include both source_id and source_ids."
        )
    _optional_uuid_text(parsed, "model_id")
    _optional_context_label(parsed, "purpose")
    _data_classification(parsed)
    _optional_bool(parsed, "contains_personal_data")
    _optional_bool(parsed, "contains_sensitive_data")
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


def _data_classification(condition: dict[str, Any]) -> DataUsageClassification | None:
    value = _optional_text(condition, "data_classification")
    if value is None:
        return None
    try:
        return DataUsageClassification(value)
    except ValueError as exc:
        raise UnsupportedPolicyRuleConditionError(
            f"Unsupported PolicyRule data_classification: {value}."
        ) from exc


def _required_text(condition: dict[str, Any], key: str) -> str:
    value = _optional_text(condition, key)
    if value is None:
        raise UnsupportedPolicyRuleConditionError(
            f"PolicyRule condition requires a non-empty {key}."
        )
    return value


def _optional_context_label(condition: dict[str, Any], key: str) -> str | None:
    value = _optional_text(condition, key)
    if value is None:
        return None
    if not CONTEXT_LABEL_PATTERN.fullmatch(value):
        raise UnsupportedPolicyRuleConditionError(
            f"PolicyRule condition field {key} must be a safe context label."
        )
    return value


def _optional_uuid_text(condition: dict[str, Any], key: str) -> str | None:
    value = _optional_text(condition, key)
    if value is None:
        return None
    return _uuid_text(value, key)


def _optional_uuid_text_tuple(
    condition: dict[str, Any],
    key: str,
) -> tuple[str, ...] | None:
    value = condition.get(key)
    if value is None:
        return None
    if not isinstance(value, list) or not value:
        raise UnsupportedPolicyRuleConditionError(
            f"PolicyRule condition field {key} must be a non-empty list "
            "of UUID strings."
        )

    normalized = tuple(_uuid_text(item, key) for item in value)
    if len(set(normalized)) != len(normalized):
        raise UnsupportedPolicyRuleConditionError(
            f"PolicyRule condition field {key} must not contain duplicate values."
        )
    return normalized


def _uuid_text(value: object, key: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise UnsupportedPolicyRuleConditionError(
            f"PolicyRule condition field {key} must be a UUID string."
        )
    try:
        return str(UUID(value))
    except ValueError as exc:
        raise UnsupportedPolicyRuleConditionError(
            f"PolicyRule condition field {key} must be a UUID string."
        ) from exc


def _optional_bool(condition: dict[str, Any], key: str) -> bool | None:
    value = condition.get(key)
    if value is None:
        return None
    if not isinstance(value, bool):
        raise UnsupportedPolicyRuleConditionError(
            f"PolicyRule condition field {key} must be a boolean."
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
