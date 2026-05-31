import json
from collections.abc import Iterator
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from agent_governance_api.database import Base
from agent_governance_api.models import (
    Environment,
    Policy,
    PolicyDecisionValue,
    PolicyRule,
    PolicyStatus,
    RiskLevel,
)
from agent_governance_api.policy_evaluator import evaluate_policy
from agent_governance_api.policy_rule_adapter import (
    UnsupportedPolicyRuleConditionError,
    load_active_policy_evaluation_rules,
)


@pytest.fixture()
def session() -> Iterator[Session]:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    try:
        with Session(engine) as session:
            yield session
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_converts_persisted_allow_rule(session: Session) -> None:
    policy, rule = add_policy_rule(
        session,
        condition={
            "decision": "allow",
            "reason": "The requested tool is allowed.",
            "tool_name": "read_docs",
        },
    )

    [evaluation_rule] = load_active_policy_evaluation_rules(session)

    assert evaluation_rule.policy_id == policy.id
    assert evaluation_rule.rule_id == rule.id
    assert evaluation_rule.decision is PolicyDecisionValue.ALLOW
    assert evaluation_rule.reason == "The requested tool is allowed."
    assert evaluation_rule.tool_name == "read_docs"


def test_converts_persisted_deny_rule(session: Session) -> None:
    policy, rule = add_policy_rule(
        session,
        condition={
            "decision": "deny",
            "reason": "Production email is denied for this agent.",
            "agent_id": "agent-1",
            "tool_name": "send_email",
            "environment": "production",
        },
    )

    [evaluation_rule] = load_active_policy_evaluation_rules(session)

    assert evaluation_rule.policy_id == policy.id
    assert evaluation_rule.rule_id == rule.id
    assert evaluation_rule.decision is PolicyDecisionValue.DENY
    assert evaluation_rule.reason == "Production email is denied for this agent."
    assert evaluation_rule.agent_id == "agent-1"
    assert evaluation_rule.tool_name == "send_email"
    assert evaluation_rule.environment is Environment.PRODUCTION


def test_converts_persisted_require_human_review_rule(session: Session) -> None:
    add_policy_rule(
        session,
        condition={
            "decision": "require_human_review",
            "reason": "Critical-risk actions require human review.",
            "risk_level": "critical",
        },
    )

    [evaluation_rule] = load_active_policy_evaluation_rules(session)

    assert evaluation_rule.decision is PolicyDecisionValue.REQUIRE_HUMAN_REVIEW
    assert evaluation_rule.reason == "Critical-risk actions require human review."
    assert evaluation_rule.risk_level is RiskLevel.CRITICAL


def test_converts_persisted_contextual_rule(session: Session) -> None:
    capability_id = uuid4()
    source_id = uuid4()
    model_id = uuid4()
    add_policy_rule(
        session,
        condition={
            "decision": "deny",
            "reason": "Declared confidential vectorization is denied.",
            "tool_name": "vectorize_source",
            "action_type": "vectorize",
            "capability_id": str(capability_id),
            "source_id": str(source_id),
            "model_id": str(model_id),
            "purpose": "semantic_search_indexing",
            "data_classification": "confidential",
            "declared_data_classification": "confidential",
            "contains_personal_data": True,
            "contains_sensitive_data": False,
            "capability_type": "tool",
            "capability_status": "active",
            "source_statuses": ["active"],
            "source_data_classifications": ["restricted"],
            "source_contains_personal_data": True,
            "source_contains_sensitive_data": False,
            "model_type": "embedding",
            "model_provider": "openai",
            "model_provider_type": "external",
            "model_status": "active",
            "access_grant_statuses": ["active"],
            "data_usage_review_statuses": ["approved"],
            "data_usage_allowed_purposes": ["semantic_search_indexing"],
            "data_usage_prohibited_purposes": ["model_training"],
        },
    )

    [evaluation_rule] = load_active_policy_evaluation_rules(session)

    assert evaluation_rule.decision is PolicyDecisionValue.DENY
    assert evaluation_rule.tool_name == "vectorize_source"
    assert evaluation_rule.action_type == "vectorize"
    assert evaluation_rule.capability_id == str(capability_id)
    assert evaluation_rule.source_id == str(source_id)
    assert evaluation_rule.model_id == str(model_id)
    assert evaluation_rule.purpose == "semantic_search_indexing"
    assert evaluation_rule.data_classification == "confidential"
    assert evaluation_rule.declared_data_classification == "confidential"
    assert evaluation_rule.contains_personal_data is True
    assert evaluation_rule.contains_sensitive_data is False
    assert evaluation_rule.capability_type == "tool"
    assert evaluation_rule.capability_status == "active"
    assert evaluation_rule.source_statuses == ("active",)
    assert evaluation_rule.source_data_classifications == ("restricted",)
    assert evaluation_rule.source_contains_personal_data is True
    assert evaluation_rule.source_contains_sensitive_data is False
    assert evaluation_rule.model_type == "embedding"
    assert evaluation_rule.model_provider == "openai"
    assert evaluation_rule.model_provider_type == "external"
    assert evaluation_rule.model_status == "active"
    assert evaluation_rule.access_grant_statuses == ("active",)
    assert evaluation_rule.data_usage_review_statuses == ("approved",)
    assert evaluation_rule.data_usage_allowed_purposes == ("semantic_search_indexing",)
    assert evaluation_rule.data_usage_prohibited_purposes == ("model_training",)


def test_converts_persisted_source_ids_rule(session: Session) -> None:
    source_ids = (uuid4(), uuid4())
    add_policy_rule(
        session,
        condition={
            "decision": "deny",
            "reason": "A governed source is denied.",
            "source_ids": [str(source_id) for source_id in source_ids],
        },
    )

    [evaluation_rule] = load_active_policy_evaluation_rules(session)

    assert evaluation_rule.source_ids == tuple(
        str(source_id) for source_id in source_ids
    )


def test_converts_persisted_check_result_matching_rule(session: Session) -> None:
    target_id = uuid4()
    check_tool_id = uuid4()
    add_policy_rule(
        session,
        condition={
            "decision": "deny",
            "reason": "Failed source pre-check denies vectorization.",
            "tool_name": "vectorize_source",
            "check_type": "source_status",
            "check_outcome": "fail",
            "check_target_type": "source",
            "check_target_id": str(target_id),
            "check_min_confidence": 0.5,
            "check_tool_id": str(check_tool_id),
        },
    )

    [evaluation_rule] = load_active_policy_evaluation_rules(session)

    assert evaluation_rule.check_type == "source_status"
    assert evaluation_rule.check_outcome == "fail"
    assert evaluation_rule.check_target_type == "source"
    assert evaluation_rule.check_target_id == str(target_id)
    assert evaluation_rule.check_min_confidence == 0.5
    assert evaluation_rule.check_tool_id == str(check_tool_id)


def test_ignores_disabled_and_archived_policies(session: Session) -> None:
    add_policy_rule(
        session,
        status=PolicyStatus.DISABLED,
        condition={
            "decision": "deny",
            "reason": "Disabled policy should not be loaded.",
            "tool_name": "send_email",
        },
    )
    add_policy_rule(
        session,
        status=PolicyStatus.ARCHIVED,
        condition={
            "decision": "deny",
            "reason": "Archived policy should not be loaded.",
            "tool_name": "send_email",
        },
    )
    active_policy, active_rule = add_policy_rule(
        session,
        condition={
            "decision": "allow",
            "reason": "Active policy should be loaded.",
            "tool_name": "read_docs",
        },
    )

    [evaluation_rule] = load_active_policy_evaluation_rules(session)

    assert evaluation_rule.policy_id == active_policy.id
    assert evaluation_rule.rule_id == active_rule.id
    assert evaluation_rule.decision is PolicyDecisionValue.ALLOW


def test_rejects_unsupported_condition_fields(session: Session) -> None:
    add_policy_rule(
        session,
        condition={
            "decision": "deny",
            "reason": "Unsupported model matching is not available.",
            "model_name": "gpt-example",
        },
    )

    with pytest.raises(
        UnsupportedPolicyRuleConditionError,
        match="Unsupported PolicyRule condition fields: model_name.",
    ):
        load_active_policy_evaluation_rules(session)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        (
            "action_type",
            "unsafe label",
            "field action_type must be a safe context label",
        ),
        ("capability_id", "not-a-uuid", "field capability_id must be a UUID string"),
        ("source_id", "not-a-uuid", "field source_id must be a UUID string"),
        ("model_id", "not-a-uuid", "field model_id must be a UUID string"),
        ("purpose", "unsafe label", "field purpose must be a safe context label"),
        (
            "data_classification",
            "secret",
            "Unsupported PolicyRule data_classification: secret.",
        ),
        (
            "declared_data_classification",
            "secret",
            "Unsupported PolicyRule declared_data_classification: secret.",
        ),
        (
            "contains_personal_data",
            "true",
            "field contains_personal_data must be a boolean",
        ),
        (
            "contains_sensitive_data",
            "false",
            "field contains_sensitive_data must be a boolean",
        ),
        ("capability_type", "database", "Unsupported PolicyRule capability_type"),
        ("capability_status", "unknown", "Unsupported PolicyRule capability_status"),
        ("source_status", "unknown", "Unsupported PolicyRule source_status"),
        (
            "source_data_classification",
            "secret",
            "Unsupported PolicyRule source_data_classification",
        ),
        (
            "source_contains_personal_data",
            "true",
            "field source_contains_personal_data must be a boolean",
        ),
        ("model_type", "text", "Unsupported PolicyRule model_type"),
        ("model_provider", "made_up", "Unsupported PolicyRule model_provider"),
        (
            "model_provider_type",
            "partner",
            "Unsupported PolicyRule model_provider_type",
        ),
        ("model_status", "unknown", "Unsupported PolicyRule model_status"),
        (
            "access_grant_status",
            "unknown",
            "Unsupported PolicyRule access_grant_status",
        ),
        (
            "data_usage_review_status",
            "unknown",
            "Unsupported PolicyRule data_usage_review_status",
        ),
        (
            "check_type",
            "unsafe label",
            "field check_type must be a safe context label",
        ),
        ("check_outcome", "missing", "Unsupported PolicyRule check_outcome"),
        ("check_target_type", "agent", "Unsupported PolicyRule check_target_type"),
        ("check_target_id", "not-a-uuid", "field check_target_id must be a UUID"),
        ("check_tool_id", "not-a-uuid", "field check_tool_id must be a UUID"),
        (
            "check_min_confidence",
            1.5,
            "field check_min_confidence must be a number between 0 and 1",
        ),
    ],
)
def test_rejects_invalid_contextual_condition_fields(
    session: Session,
    field: str,
    value: object,
    message: str,
) -> None:
    add_policy_rule(
        session,
        condition={
            "decision": "deny",
            "reason": "Invalid contextual field should be rejected.",
            field: value,
        },
    )

    with pytest.raises(UnsupportedPolicyRuleConditionError, match=message):
        load_active_policy_evaluation_rules(session)


def test_rejects_source_id_and_source_ids_together(session: Session) -> None:
    source_id = uuid4()
    add_policy_rule(
        session,
        condition={
            "decision": "deny",
            "reason": "Ambiguous source matching should be rejected.",
            "source_id": str(source_id),
            "source_ids": [str(source_id)],
        },
    )

    with pytest.raises(
        UnsupportedPolicyRuleConditionError,
        match="cannot include both source_id and source_ids",
    ):
        load_active_policy_evaluation_rules(session)


def test_rejects_duplicate_source_ids(session: Session) -> None:
    source_id = str(uuid4())
    add_policy_rule(
        session,
        condition={
            "decision": "deny",
            "reason": "Duplicate source ids should be rejected.",
            "source_ids": [source_id, source_id],
        },
    )

    with pytest.raises(
        UnsupportedPolicyRuleConditionError,
        match="field source_ids must not contain duplicate values",
    ):
        load_active_policy_evaluation_rules(session)


def test_preserves_evaluator_precedence(session: Session) -> None:
    add_policy_rule(
        session,
        condition={
            "decision": "allow",
            "reason": "Email is generally allowed.",
            "tool_name": "send_email",
        },
    )
    add_policy_rule(
        session,
        condition={
            "decision": "require_human_review",
            "reason": "High-risk actions require review.",
            "risk_level": "high",
        },
    )
    add_policy_rule(
        session,
        condition={
            "decision": "deny",
            "reason": "Production email is denied.",
            "environment": "production",
        },
    )

    result = evaluate_policy(
        agent_context={"agent_id": "agent-1"},
        action_context={"tool_name": "send_email"},
        environment=Environment.PRODUCTION,
        risk_level=RiskLevel.HIGH,
        rules=load_active_policy_evaluation_rules(session),
    )

    assert result.decision is PolicyDecisionValue.DENY
    assert result.reason == "Production email is denied."


def add_policy_rule(
    session: Session,
    *,
    condition: dict[str, object],
    status: PolicyStatus = PolicyStatus.ACTIVE,
) -> tuple[Policy, PolicyRule]:
    policy = Policy(
        name="Tool access policy",
        description=None,
        status=status,
    )
    session.add(policy)
    session.flush()

    rule = PolicyRule(
        policy_id=policy.id,
        name="Explicit tool access rule",
        description=None,
        condition=json.dumps(condition),
    )
    session.add(rule)
    session.commit()

    return policy, rule
