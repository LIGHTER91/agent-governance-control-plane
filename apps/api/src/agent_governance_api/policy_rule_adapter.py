import json
from collections import defaultdict
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from agent_governance_api.models import (
    AccessGrantStatus,
    CapabilityStatus,
    CapabilityType,
    CheckResultOutcome,
    CheckResultTargetType,
    DataSourceStatus,
    DataUsageClassification,
    DataUsageReviewStatus,
    Environment,
    ModelAssetStatus,
    ModelAssetType,
    ModelProvider,
    Policy,
    PolicyDecisionValue,
    PolicyRule,
    PolicyStatus,
    PolicyVersion,
    PolicyVersionStatus,
    RiskLevel,
)
from agent_governance_api.policy_evaluator import PolicyEvaluationRule
from agent_governance_api.runtime_gateway import CONTEXT_LABEL_PATTERN
from agent_governance_api.runtime_metadata_pre_checks import (
    RuntimePolicyCheckStep,
    runtime_policy_check_step_from_snapshot,
)

MISSING_RESOLVED_CONTEXT_VALUE = "missing"
MODEL_PROVIDER_TYPE_VALUES = frozenset({"external", "local", "unknown"})

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
        "declared_data_classification",
        "contains_personal_data",
        "contains_sensitive_data",
        "capability_type",
        "capability_status",
        "source_status",
        "source_statuses",
        "source_data_classification",
        "source_data_classifications",
        "source_contains_personal_data",
        "source_contains_sensitive_data",
        "model_type",
        "model_provider",
        "model_provider_type",
        "model_status",
        "access_grant_status",
        "access_grant_statuses",
        "data_usage_review_status",
        "data_usage_review_statuses",
        "data_usage_allowed_purpose",
        "data_usage_allowed_purposes",
        "data_usage_prohibited_purpose",
        "data_usage_prohibited_purposes",
        "check_type",
        "check_outcome",
        "check_target_type",
        "check_target_id",
        "check_min_confidence",
        "check_tool_id",
    }
)


class UnsupportedPolicyRuleConditionError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class RuntimePolicyEvaluationConfig:
    rules: tuple[PolicyEvaluationRule, ...]
    versioned_policy_rule_ids: tuple[UUID, ...] = ()
    versioned_policy_check_steps: tuple[RuntimePolicyCheckStep, ...] = ()


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


def load_runtime_policy_evaluation_config(
    session: Session,
) -> RuntimePolicyEvaluationConfig:
    """Load active PolicyVersion snapshot rules with live-row fallback.

    Runtime Gateway prefers immutable active PolicyVersion snapshots for each
    Policy. Policies without an active version keep the existing live
    Policy/PolicyRule behavior.
    """

    active_versions_by_policy_id = _latest_active_versions_by_policy_id(session)
    ordered_policies = _runtime_policy_order(
        session,
        active_policy_version_policy_ids=set(active_versions_by_policy_id),
    )
    fallback_rules_by_policy_id = _fallback_policy_rules_by_policy_id(
        session,
        [
            policy.id
            for policy in ordered_policies
            if policy.id not in active_versions_by_policy_id
            and policy.status is PolicyStatus.ACTIVE
        ],
    )

    rules: list[PolicyEvaluationRule] = []
    versioned_policy_rule_ids: list[UUID] = []
    versioned_policy_check_steps: list[RuntimePolicyCheckStep] = []
    for policy in ordered_policies:
        active_version = active_versions_by_policy_id.get(policy.id)
        if active_version is not None:
            version_rules = convert_policy_version_to_evaluation_rules(active_version)
            rules.extend(version_rules)
            versioned_policy_rule_ids.extend(
                UUID(str(rule.rule_id))
                for rule in version_rules
                if rule.rule_id is not None
            )
            versioned_policy_check_steps.extend(
                convert_policy_version_check_steps(active_version)
            )
            continue

        rules.extend(
            convert_policy_rule_to_evaluation_rule(policy, rule)
            for rule in fallback_rules_by_policy_id.get(policy.id, ())
        )

    return RuntimePolicyEvaluationConfig(
        rules=tuple(rules),
        versioned_policy_rule_ids=tuple(versioned_policy_rule_ids),
        versioned_policy_check_steps=tuple(versioned_policy_check_steps),
    )


def convert_policy_rule_to_evaluation_rule(
    policy: Policy,
    rule: PolicyRule,
) -> PolicyEvaluationRule:
    return _condition_to_evaluation_rule(
        rule.condition,
        policy_id=policy.id,
        policy_version_id=None,
        rule_id=rule.id,
    )


def convert_policy_version_to_evaluation_rules(
    policy_version: PolicyVersion,
) -> list[PolicyEvaluationRule]:
    return [
        convert_policy_rule_snapshot_to_evaluation_rule(policy_version, snapshot)
        for snapshot in policy_version.rule_snapshots
    ]


def convert_policy_version_check_steps(
    policy_version: PolicyVersion,
) -> list[RuntimePolicyCheckStep]:
    return [
        runtime_policy_check_step_from_snapshot(
            snapshot,
            policy_version_id=policy_version.id,
        )
        for snapshot in policy_version.check_step_snapshots
    ]


def convert_policy_rule_snapshot_to_evaluation_rule(
    policy_version: PolicyVersion,
    rule_snapshot: dict[str, object],
) -> PolicyEvaluationRule:
    return _condition_to_evaluation_rule(
        _snapshot_text(rule_snapshot, "condition"),
        policy_id=policy_version.policy_id,
        policy_version_id=policy_version.id,
        rule_id=_snapshot_uuid(rule_snapshot, "id"),
    )


def _condition_to_evaluation_rule(
    condition_text: str,
    *,
    policy_id: UUID,
    policy_version_id: UUID | None,
    rule_id: UUID,
) -> PolicyEvaluationRule:
    condition = _validated_condition(condition_text)

    return PolicyEvaluationRule(
        policy_id=policy_id,
        policy_version_id=policy_version_id,
        rule_id=rule_id,
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
        declared_data_classification=_declared_data_classification(condition),
        contains_personal_data=_optional_bool(condition, "contains_personal_data"),
        contains_sensitive_data=_optional_bool(condition, "contains_sensitive_data"),
        capability_type=_optional_enum_text(
            condition, "capability_type", CapabilityType
        ),
        capability_status=_optional_enum_text(
            condition,
            "capability_status",
            CapabilityStatus,
            extra_values=(MISSING_RESOLVED_CONTEXT_VALUE,),
        ),
        source_status=_optional_enum_text(
            condition,
            "source_status",
            DataSourceStatus,
            extra_values=(MISSING_RESOLVED_CONTEXT_VALUE,),
        ),
        source_statuses=_optional_enum_text_tuple(
            condition,
            "source_statuses",
            DataSourceStatus,
            extra_values=(MISSING_RESOLVED_CONTEXT_VALUE,),
        ),
        source_data_classification=_optional_enum_text(
            condition,
            "source_data_classification",
            DataUsageClassification,
        ),
        source_data_classifications=_optional_enum_text_tuple(
            condition,
            "source_data_classifications",
            DataUsageClassification,
        ),
        source_contains_personal_data=_optional_bool(
            condition,
            "source_contains_personal_data",
        ),
        source_contains_sensitive_data=_optional_bool(
            condition,
            "source_contains_sensitive_data",
        ),
        model_type=_optional_enum_text(condition, "model_type", ModelAssetType),
        model_provider=_optional_enum_text(condition, "model_provider", ModelProvider),
        model_provider_type=_optional_allowed_text(
            condition,
            "model_provider_type",
            MODEL_PROVIDER_TYPE_VALUES,
        ),
        model_status=_optional_enum_text(
            condition,
            "model_status",
            ModelAssetStatus,
            extra_values=(MISSING_RESOLVED_CONTEXT_VALUE,),
        ),
        access_grant_status=_optional_enum_text(
            condition,
            "access_grant_status",
            AccessGrantStatus,
            extra_values=(MISSING_RESOLVED_CONTEXT_VALUE,),
        ),
        access_grant_statuses=_optional_enum_text_tuple(
            condition,
            "access_grant_statuses",
            AccessGrantStatus,
            extra_values=(MISSING_RESOLVED_CONTEXT_VALUE,),
        ),
        data_usage_review_status=_optional_enum_text(
            condition,
            "data_usage_review_status",
            DataUsageReviewStatus,
            extra_values=(MISSING_RESOLVED_CONTEXT_VALUE,),
        ),
        data_usage_review_statuses=_optional_enum_text_tuple(
            condition,
            "data_usage_review_statuses",
            DataUsageReviewStatus,
            extra_values=(MISSING_RESOLVED_CONTEXT_VALUE,),
        ),
        data_usage_allowed_purpose=_optional_context_label(
            condition,
            "data_usage_allowed_purpose",
        ),
        data_usage_allowed_purposes=_optional_context_label_tuple(
            condition,
            "data_usage_allowed_purposes",
        ),
        data_usage_prohibited_purpose=_optional_context_label(
            condition,
            "data_usage_prohibited_purpose",
        ),
        data_usage_prohibited_purposes=_optional_context_label_tuple(
            condition,
            "data_usage_prohibited_purposes",
        ),
        check_type=_optional_context_label(condition, "check_type"),
        check_outcome=_optional_enum_text(
            condition, "check_outcome", CheckResultOutcome
        ),
        check_target_type=_optional_enum_text(
            condition,
            "check_target_type",
            CheckResultTargetType,
        ),
        check_target_id=_optional_uuid_text(condition, "check_target_id"),
        check_min_confidence=_optional_confidence_threshold(
            condition,
            "check_min_confidence",
        ),
        check_tool_id=_optional_uuid_text(condition, "check_tool_id"),
    )


def _latest_active_versions_by_policy_id(
    session: Session,
) -> dict[UUID, PolicyVersion]:
    statement = (
        select(PolicyVersion)
        .where(PolicyVersion.status == PolicyVersionStatus.ACTIVE)
        .order_by(
            PolicyVersion.policy_id,
            PolicyVersion.version_number,
            PolicyVersion.activated_at,
            PolicyVersion.id,
        )
    )
    selected_versions: dict[UUID, PolicyVersion] = {}
    for version in session.scalars(statement).all():
        current = selected_versions.get(version.policy_id)
        if current is None:
            selected_versions[version.policy_id] = version
            continue
        if _active_version_sort_key(version) > _active_version_sort_key(current):
            selected_versions[version.policy_id] = version
    return selected_versions


def _runtime_policy_order(
    session: Session,
    *,
    active_policy_version_policy_ids: set[UUID],
) -> list[Policy]:
    if active_policy_version_policy_ids:
        predicate = or_(
            Policy.status == PolicyStatus.ACTIVE,
            Policy.id.in_(active_policy_version_policy_ids),
        )
    else:
        predicate = Policy.status == PolicyStatus.ACTIVE

    statement = select(Policy).where(predicate).order_by(Policy.created_at, Policy.id)
    return list(session.scalars(statement).all())


def _fallback_policy_rules_by_policy_id(
    session: Session,
    policy_ids: list[UUID],
) -> dict[UUID, list[PolicyRule]]:
    if not policy_ids:
        return {}

    statement = (
        select(PolicyRule)
        .where(PolicyRule.policy_id.in_(policy_ids))
        .order_by(PolicyRule.created_at, PolicyRule.id)
    )
    rules_by_policy_id: dict[UUID, list[PolicyRule]] = defaultdict(list)
    for rule in session.scalars(statement).all():
        rules_by_policy_id[rule.policy_id].append(rule)
    return rules_by_policy_id


def _active_version_sort_key(policy_version: PolicyVersion) -> tuple[int, str, str]:
    activated_at = policy_version.activated_at
    return (
        policy_version.version_number,
        activated_at.isoformat() if activated_at is not None else "",
        str(policy_version.id),
    )


def _snapshot_text(snapshot: dict[str, object], key: str) -> str:
    value = snapshot.get(key)
    if not isinstance(value, str) or not value.strip():
        raise UnsupportedPolicyRuleConditionError(
            f"PolicyVersion rule snapshot requires a non-empty {key}."
        )
    return value


def _snapshot_uuid(snapshot: dict[str, object], key: str) -> UUID:
    value = _snapshot_text(snapshot, key)
    try:
        return UUID(value)
    except ValueError as exc:
        raise UnsupportedPolicyRuleConditionError(
            f"PolicyVersion rule snapshot {key} must be a UUID string."
        ) from exc


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
    _declared_data_classification(parsed)
    _optional_bool(parsed, "contains_personal_data")
    _optional_bool(parsed, "contains_sensitive_data")
    _optional_enum_text(parsed, "capability_type", CapabilityType)
    _optional_enum_text(
        parsed,
        "capability_status",
        CapabilityStatus,
        extra_values=(MISSING_RESOLVED_CONTEXT_VALUE,),
    )
    _optional_enum_text(
        parsed,
        "source_status",
        DataSourceStatus,
        extra_values=(MISSING_RESOLVED_CONTEXT_VALUE,),
    )
    _optional_enum_text_tuple(
        parsed,
        "source_statuses",
        DataSourceStatus,
        extra_values=(MISSING_RESOLVED_CONTEXT_VALUE,),
    )
    _optional_enum_text(parsed, "source_data_classification", DataUsageClassification)
    _optional_enum_text_tuple(
        parsed,
        "source_data_classifications",
        DataUsageClassification,
    )
    _optional_bool(parsed, "source_contains_personal_data")
    _optional_bool(parsed, "source_contains_sensitive_data")
    _optional_enum_text(parsed, "model_type", ModelAssetType)
    _optional_enum_text(parsed, "model_provider", ModelProvider)
    _optional_allowed_text(parsed, "model_provider_type", MODEL_PROVIDER_TYPE_VALUES)
    _optional_enum_text(
        parsed,
        "model_status",
        ModelAssetStatus,
        extra_values=(MISSING_RESOLVED_CONTEXT_VALUE,),
    )
    _optional_enum_text(
        parsed,
        "access_grant_status",
        AccessGrantStatus,
        extra_values=(MISSING_RESOLVED_CONTEXT_VALUE,),
    )
    _optional_enum_text_tuple(
        parsed,
        "access_grant_statuses",
        AccessGrantStatus,
        extra_values=(MISSING_RESOLVED_CONTEXT_VALUE,),
    )
    _optional_enum_text(
        parsed,
        "data_usage_review_status",
        DataUsageReviewStatus,
        extra_values=(MISSING_RESOLVED_CONTEXT_VALUE,),
    )
    _optional_enum_text_tuple(
        parsed,
        "data_usage_review_statuses",
        DataUsageReviewStatus,
        extra_values=(MISSING_RESOLVED_CONTEXT_VALUE,),
    )
    _optional_context_label(parsed, "data_usage_allowed_purpose")
    _optional_context_label_tuple(parsed, "data_usage_allowed_purposes")
    _optional_context_label(parsed, "data_usage_prohibited_purpose")
    _optional_context_label_tuple(parsed, "data_usage_prohibited_purposes")
    _optional_context_label(parsed, "check_type")
    _optional_enum_text(parsed, "check_outcome", CheckResultOutcome)
    _optional_enum_text(parsed, "check_target_type", CheckResultTargetType)
    _optional_uuid_text(parsed, "check_target_id")
    _optional_confidence_threshold(parsed, "check_min_confidence")
    _optional_uuid_text(parsed, "check_tool_id")
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


def _declared_data_classification(
    condition: dict[str, Any],
) -> DataUsageClassification | None:
    value = _optional_text(condition, "declared_data_classification")
    if value is None:
        return None
    try:
        return DataUsageClassification(value)
    except ValueError as exc:
        raise UnsupportedPolicyRuleConditionError(
            f"Unsupported PolicyRule declared_data_classification: {value}."
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


def _optional_context_label_tuple(
    condition: dict[str, Any],
    key: str,
) -> tuple[str, ...] | None:
    value = condition.get(key)
    if value is None:
        return None
    if not isinstance(value, list) or not value:
        raise UnsupportedPolicyRuleConditionError(
            f"PolicyRule condition field {key} must be a non-empty list "
            "of safe context labels."
        )

    normalized = tuple(_context_label_text(item, key) for item in value)
    if len(set(normalized)) != len(normalized):
        raise UnsupportedPolicyRuleConditionError(
            f"PolicyRule condition field {key} must not contain duplicate values."
        )
    return normalized


def _optional_enum_text(
    condition: dict[str, Any],
    key: str,
    enum_class: type[Any],
    *,
    extra_values: tuple[str, ...] = (),
) -> str | None:
    value = _optional_text(condition, key)
    if value is None:
        return None
    return _enum_text(value, key, enum_class, extra_values=extra_values)


def _optional_enum_text_tuple(
    condition: dict[str, Any],
    key: str,
    enum_class: type[Any],
    *,
    extra_values: tuple[str, ...] = (),
) -> tuple[str, ...] | None:
    value = condition.get(key)
    if value is None:
        return None
    if not isinstance(value, list) or not value:
        raise UnsupportedPolicyRuleConditionError(
            f"PolicyRule condition field {key} must be a non-empty list."
        )

    normalized = tuple(
        _enum_text(item, key, enum_class, extra_values=extra_values) for item in value
    )
    if len(set(normalized)) != len(normalized):
        raise UnsupportedPolicyRuleConditionError(
            f"PolicyRule condition field {key} must not contain duplicate values."
        )
    return normalized


def _enum_text(
    value: object,
    key: str,
    enum_class: type[Any],
    *,
    extra_values: tuple[str, ...] = (),
) -> str:
    if not isinstance(value, str) or not value.strip():
        raise UnsupportedPolicyRuleConditionError(
            f"PolicyRule condition field {key} must be a non-empty string."
        )
    if value in extra_values:
        return value
    try:
        return enum_class(value).value
    except ValueError as exc:
        raise UnsupportedPolicyRuleConditionError(
            f"Unsupported PolicyRule {key}: {value}."
        ) from exc


def _optional_allowed_text(
    condition: dict[str, Any],
    key: str,
    allowed_values: frozenset[str],
) -> str | None:
    value = _optional_text(condition, key)
    if value is None:
        return None
    if value not in allowed_values:
        joined_values = ", ".join(sorted(allowed_values))
        raise UnsupportedPolicyRuleConditionError(
            f"Unsupported PolicyRule {key}: {value}. Expected one of: {joined_values}."
        )
    return value


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


def _optional_confidence_threshold(condition: dict[str, Any], key: str) -> float | None:
    value = condition.get(key)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise UnsupportedPolicyRuleConditionError(
            f"PolicyRule condition field {key} must be a number between 0 and 1."
        )
    threshold = float(value)
    if threshold < 0 or threshold > 1:
        raise UnsupportedPolicyRuleConditionError(
            f"PolicyRule condition field {key} must be a number between 0 and 1."
        )
    return threshold


def _context_label_text(value: object, key: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise UnsupportedPolicyRuleConditionError(
            f"PolicyRule condition field {key} must contain non-empty strings."
        )
    normalized = value.strip()
    if not CONTEXT_LABEL_PATTERN.fullmatch(normalized):
        raise UnsupportedPolicyRuleConditionError(
            f"PolicyRule condition field {key} must contain safe context labels."
        )
    return normalized


def _optional_text(condition: dict[str, Any], key: str) -> str | None:
    value = condition.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise UnsupportedPolicyRuleConditionError(
            f"PolicyRule condition field {key} must be a non-empty string."
        )
    return value
