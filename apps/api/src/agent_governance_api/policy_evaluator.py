from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from agent_governance_api.models import (
    AccessGrantStatus,
    CapabilityStatus,
    CapabilityType,
    DataSourceStatus,
    DataUsageClassification,
    DataUsageReviewStatus,
    Environment,
    ModelAssetStatus,
    ModelAssetType,
    ModelProvider,
    PolicyDecisionValue,
    RiskLevel,
)

ContextScalar = str | UUID | StrEnum | bool
ContextValue = ContextScalar | None
ContextListScalar = ContextScalar

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
    declared_data_classification: DataUsageClassification | str | None = None
    contains_personal_data: bool | None = None
    contains_sensitive_data: bool | None = None
    capability_type: CapabilityType | str | None = None
    capability_status: CapabilityStatus | str | None = None
    source_status: DataSourceStatus | str | None = None
    source_statuses: tuple[DataSourceStatus | str, ...] | None = None
    source_data_classification: DataUsageClassification | str | None = None
    source_data_classifications: tuple[DataUsageClassification | str, ...] | None = None
    source_contains_personal_data: bool | None = None
    source_contains_sensitive_data: bool | None = None
    model_type: ModelAssetType | str | None = None
    model_provider: ModelProvider | str | None = None
    model_provider_type: str | None = None
    model_status: ModelAssetStatus | str | None = None
    access_grant_status: AccessGrantStatus | str | None = None
    access_grant_statuses: tuple[AccessGrantStatus | str, ...] | None = None
    data_usage_review_status: DataUsageReviewStatus | str | None = None
    data_usage_review_statuses: tuple[DataUsageReviewStatus | str, ...] | None = None
    data_usage_allowed_purpose: str | None = None
    data_usage_allowed_purposes: tuple[str, ...] | None = None
    data_usage_prohibited_purpose: str | None = None
    data_usage_prohibited_purposes: tuple[str, ...] | None = None


@dataclass(frozen=True, slots=True)
class PolicyEvaluationResult:
    decision: PolicyDecisionValue
    reason: str
    agent_id: str
    policy_id: str | UUID | None = None
    rule_id: str | UUID | None = None
    matched_rule_ids: tuple[str | UUID, ...] = ()


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
    source_ids = _context_values(action_context, "source_id", "source_ids")
    model_id = _optional_context_value(action_context, "model_id")
    purpose = _optional_context_value(action_context, "purpose")
    data_classification = _optional_context_value(
        action_context,
        "data_classification",
    )
    declared_data_classification = _optional_context_value(
        action_context,
        "declared_data_classification",
    )
    contains_personal_data = _optional_context_value(
        action_context,
        "contains_personal_data",
    )
    contains_sensitive_data = _optional_context_value(
        action_context,
        "contains_sensitive_data",
    )
    capability_type = _optional_context_value(action_context, "capability_type")
    capability_status = _optional_context_value(action_context, "capability_status")
    source_statuses = _context_values(
        action_context,
        "source_status",
        "source_statuses",
    )
    source_data_classifications = _context_values(
        action_context,
        "source_data_classification",
        "source_data_classifications",
    )
    source_contains_personal_data = _optional_context_value(
        action_context,
        "source_contains_personal_data",
    )
    source_contains_sensitive_data = _optional_context_value(
        action_context,
        "source_contains_sensitive_data",
    )
    model_type = _optional_context_value(action_context, "model_type")
    model_provider = _optional_context_value(action_context, "model_provider")
    model_provider_type = _optional_context_value(
        action_context,
        "model_provider_type",
    )
    model_status = _optional_context_value(action_context, "model_status")
    access_grant_statuses = _context_values(
        action_context,
        "access_grant_status",
        "access_grant_statuses",
    )
    data_usage_review_statuses = _context_values(
        action_context,
        "data_usage_review_status",
        "data_usage_review_statuses",
    )
    data_usage_allowed_purposes = _context_values(
        action_context,
        "data_usage_allowed_purpose",
        "data_usage_allowed_purposes",
    )
    data_usage_prohibited_purposes = _context_values(
        action_context,
        "data_usage_prohibited_purpose",
        "data_usage_prohibited_purposes",
    )

    matching_rules: list[tuple[tuple[int, int, int], PolicyEvaluationRule]] = []
    matched_rule_ids: list[str | UUID] = []
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
            declared_data_classification=declared_data_classification,
            contains_personal_data=contains_personal_data,
            contains_sensitive_data=contains_sensitive_data,
            capability_type=capability_type,
            capability_status=capability_status,
            source_statuses=source_statuses,
            source_data_classifications=source_data_classifications,
            source_contains_personal_data=source_contains_personal_data,
            source_contains_sensitive_data=source_contains_sensitive_data,
            model_type=model_type,
            model_provider=model_provider,
            model_provider_type=model_provider_type,
            model_status=model_status,
            access_grant_statuses=access_grant_statuses,
            data_usage_review_statuses=data_usage_review_statuses,
            data_usage_allowed_purposes=data_usage_allowed_purposes,
            data_usage_prohibited_purposes=data_usage_prohibited_purposes,
        ):
            decision = PolicyDecisionValue(rule.decision)
            rank = (
                DECISION_PRECEDENCE[decision],
                _specificity(rule),
                -index,
            )
            matching_rules.append((rank, rule))
            if rule.rule_id is not None:
                matched_rule_ids.append(rule.rule_id)

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
        matched_rule_ids=tuple(matched_rule_ids),
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
    source_ids: tuple[ContextListScalar, ...],
    model_id: ContextValue,
    purpose: ContextValue,
    data_classification: ContextValue,
    declared_data_classification: ContextValue,
    contains_personal_data: ContextValue,
    contains_sensitive_data: ContextValue,
    capability_type: ContextValue,
    capability_status: ContextValue,
    source_statuses: tuple[ContextListScalar, ...],
    source_data_classifications: tuple[ContextListScalar, ...],
    source_contains_personal_data: ContextValue,
    source_contains_sensitive_data: ContextValue,
    model_type: ContextValue,
    model_provider: ContextValue,
    model_provider_type: ContextValue,
    model_status: ContextValue,
    access_grant_statuses: tuple[ContextListScalar, ...],
    data_usage_review_statuses: tuple[ContextListScalar, ...],
    data_usage_allowed_purposes: tuple[ContextListScalar, ...],
    data_usage_prohibited_purposes: tuple[ContextListScalar, ...],
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
        and _matches(rule.declared_data_classification, declared_data_classification)
        and _matches(rule.contains_personal_data, contains_personal_data)
        and _matches(rule.contains_sensitive_data, contains_sensitive_data)
        and _matches(rule.capability_type, capability_type)
        and _matches(rule.capability_status, capability_status)
        and _multi_matches(
            expected=rule.source_status,
            expected_values=rule.source_statuses,
            actual_values=source_statuses,
        )
        and _multi_matches(
            expected=rule.source_data_classification,
            expected_values=rule.source_data_classifications,
            actual_values=source_data_classifications,
        )
        and _matches(rule.source_contains_personal_data, source_contains_personal_data)
        and _matches(
            rule.source_contains_sensitive_data,
            source_contains_sensitive_data,
        )
        and _matches(rule.model_type, model_type)
        and _matches(rule.model_provider, model_provider)
        and _matches(rule.model_provider_type, model_provider_type)
        and _matches(rule.model_status, model_status)
        and _multi_matches(
            expected=rule.access_grant_status,
            expected_values=rule.access_grant_statuses,
            actual_values=access_grant_statuses,
        )
        and _multi_matches(
            expected=rule.data_usage_review_status,
            expected_values=rule.data_usage_review_statuses,
            actual_values=data_usage_review_statuses,
        )
        and _multi_matches(
            expected=rule.data_usage_allowed_purpose,
            expected_values=rule.data_usage_allowed_purposes,
            actual_values=data_usage_allowed_purposes,
        )
        and _multi_matches(
            expected=rule.data_usage_prohibited_purpose,
            expected_values=rule.data_usage_prohibited_purposes,
            actual_values=data_usage_prohibited_purposes,
        )
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
    actual_source_ids: tuple[ContextListScalar, ...],
) -> bool:
    return _multi_matches(
        expected=source_id,
        expected_values=source_ids,
        actual_values=actual_source_ids,
    )


def _multi_matches(
    *,
    expected: ContextValue,
    expected_values: tuple[ContextScalar, ...] | None,
    actual_values: tuple[ContextListScalar, ...],
) -> bool:
    if expected is None and expected_values is None:
        return True
    if not actual_values:
        return False

    expected_items: list[ContextScalar] = []
    if expected is not None:
        expected_items.append(expected)
    if expected_values:
        expected_items.extend(expected_values)

    actual = {_normalize(value) for value in actual_values}
    return any(_normalize(item) in actual for item in expected_items)


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
            rule.declared_data_classification,
            rule.contains_personal_data,
            rule.contains_sensitive_data,
            rule.capability_type,
            rule.capability_status,
            rule.source_status,
            rule.source_data_classification,
            rule.source_contains_personal_data,
            rule.source_contains_sensitive_data,
            rule.model_type,
            rule.model_provider,
            rule.model_provider_type,
            rule.model_status,
            rule.access_grant_status,
            rule.data_usage_review_status,
            rule.data_usage_allowed_purpose,
            rule.data_usage_prohibited_purpose,
        )
    ) + sum(
        bool(value)
        for value in (
            rule.source_ids,
            rule.source_statuses,
            rule.source_data_classifications,
            rule.access_grant_statuses,
            rule.data_usage_review_statuses,
            rule.data_usage_allowed_purposes,
            rule.data_usage_prohibited_purposes,
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
    if isinstance(value, str | UUID | StrEnum | bool):
        return value
    raise TypeError(
        "Policy evaluation context values must be strings, UUIDs, enums, or booleans."
    )


def _context_values(
    action_context: Mapping[str, object],
    singular_key: str,
    plural_key: str,
) -> tuple[ContextListScalar, ...]:
    singular_value = action_context.get(singular_key)
    plural_values = action_context.get(plural_key)
    values: list[ContextListScalar] = []

    if singular_value is not None:
        values.append(_context_list_value(singular_value, singular_key))

    if plural_values is None:
        return tuple(values)
    if isinstance(plural_values, str | UUID | StrEnum | bool):
        values.append(_context_list_value(plural_values, plural_key))
        return tuple(values)
    if isinstance(plural_values, Mapping):
        raise TypeError(
            f"Policy evaluation {plural_key} context must be a scalar "
            "or iterable of scalar values."
        )
    if isinstance(plural_values, Iterable):
        values.extend(_context_list_value(value, plural_key) for value in plural_values)
        return tuple(values)

    raise TypeError(
        f"Policy evaluation {plural_key} context must be a scalar "
        "or iterable of scalar values."
    )


def _context_list_value(value: object, key: str) -> ContextListScalar:
    if isinstance(value, str | UUID | StrEnum | bool):
        return value
    raise TypeError(f"Policy evaluation {key} values must be scalar values.")


def _normalize(value: ContextScalar) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, StrEnum):
        return value.value
    return str(value)
