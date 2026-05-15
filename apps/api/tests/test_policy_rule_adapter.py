import json
from collections.abc import Iterator

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
    condition: dict[str, str],
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
