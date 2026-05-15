from agent_governance_api.models import Environment, PolicyDecisionValue, RiskLevel
from agent_governance_api.policy_evaluator import (
    PolicyEvaluationRule,
    evaluate_policy,
)


def test_evaluator_returns_allow_decision() -> None:
    result = evaluate_policy(
        agent_context={"agent_id": "agent-1"},
        action_context={"tool_name": "read_docs"},
        environment=Environment.DEVELOPMENT,
        risk_level=RiskLevel.LOW,
        rules=[
            PolicyEvaluationRule(
                policy_id="policy-tool-access",
                rule_id="rule-read-docs",
                tool_name="read_docs",
                decision=PolicyDecisionValue.ALLOW,
                reason="The requested tool is allowed for this context.",
            )
        ],
    )

    assert result.decision is PolicyDecisionValue.ALLOW
    assert result.reason == "The requested tool is allowed for this context."
    assert result.policy_id == "policy-tool-access"
    assert result.rule_id == "rule-read-docs"


def test_evaluator_returns_deny_decision() -> None:
    result = evaluate_policy(
        agent_context={"agent_id": "agent-1"},
        action_context={"tool_name": "send_email"},
        environment=Environment.PRODUCTION,
        risk_level=RiskLevel.HIGH,
        rules=[
            PolicyEvaluationRule(
                policy_id="policy-email-access",
                rule_id="rule-deny-email",
                agent_id="agent-1",
                tool_name="send_email",
                decision="deny",
                reason="This agent cannot use send_email.",
            )
        ],
    )

    assert result.decision is PolicyDecisionValue.DENY
    assert result.reason == "This agent cannot use send_email."
    assert result.policy_id == "policy-email-access"
    assert result.rule_id == "rule-deny-email"


def test_evaluator_returns_require_human_review_decision() -> None:
    result = evaluate_policy(
        agent_context={"agent_id": "agent-1"},
        action_context={"tool_name": "create_ticket"},
        environment="production",
        risk_level="critical",
        rules=[
            PolicyEvaluationRule(
                policy_id="policy-critical-risk",
                rule_id="rule-critical-review",
                environment=Environment.PRODUCTION,
                risk_level=RiskLevel.CRITICAL,
                decision=PolicyDecisionValue.REQUIRE_HUMAN_REVIEW,
                reason="Critical production actions require human review.",
            )
        ],
    )

    assert result.decision is PolicyDecisionValue.REQUIRE_HUMAN_REVIEW
    assert result.reason == "Critical production actions require human review."
    assert result.policy_id == "policy-critical-risk"
    assert result.rule_id == "rule-critical-review"


def test_evaluator_returns_not_applicable_decision() -> None:
    result = evaluate_policy(
        agent_context={"agent_id": "agent-1"},
        action_context={"tool_name": "read_docs"},
        environment=Environment.STAGING,
        risk_level=RiskLevel.MEDIUM,
        rules=[
            PolicyEvaluationRule(
                policy_id="policy-production-only",
                rule_id="rule-production-only",
                environment=Environment.PRODUCTION,
                decision=PolicyDecisionValue.DENY,
                reason="Production-only rule.",
            )
        ],
    )

    assert result.decision is PolicyDecisionValue.NOT_APPLICABLE
    assert result.reason == "No policy rule matched the request."
    assert result.policy_id is None
    assert result.rule_id is None


def test_evaluator_uses_decision_precedence_when_multiple_rules_match() -> None:
    result = evaluate_policy(
        agent_context={"agent_id": "agent-1"},
        action_context={"tool_name": "send_email"},
        environment=Environment.PRODUCTION,
        risk_level=RiskLevel.HIGH,
        rules=[
            PolicyEvaluationRule(
                policy_id="policy-allow",
                rule_id="rule-allow-email",
                tool_name="send_email",
                decision=PolicyDecisionValue.ALLOW,
                reason="Email is generally allowed.",
            ),
            PolicyEvaluationRule(
                policy_id="policy-review",
                rule_id="rule-high-risk-review",
                risk_level=RiskLevel.HIGH,
                decision=PolicyDecisionValue.REQUIRE_HUMAN_REVIEW,
                reason="High-risk actions require review.",
            ),
            PolicyEvaluationRule(
                policy_id="policy-deny",
                rule_id="rule-production-deny",
                environment=Environment.PRODUCTION,
                decision=PolicyDecisionValue.DENY,
                reason="Production email is denied.",
            ),
        ],
    )

    assert result.decision is PolicyDecisionValue.DENY
    assert result.reason == "Production email is denied."
    assert result.policy_id == "policy-deny"
    assert result.rule_id == "rule-production-deny"
