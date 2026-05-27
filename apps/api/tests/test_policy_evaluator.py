from uuid import uuid4

import pytest

from agent_governance_api.models import (
    DataUsageClassification,
    Environment,
    PolicyDecisionValue,
    RiskLevel,
)
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


@pytest.mark.parametrize(
    ("rule_kwargs", "action_context"),
    [
        (
            {"action_type": "vectorize"},
            {"tool_name": "vectorize_source", "action_type": "vectorize"},
        ),
        (
            {"purpose": "semantic_search_indexing"},
            {
                "tool_name": "vectorize_source",
                "purpose": "semantic_search_indexing",
            },
        ),
        (
            {"data_classification": DataUsageClassification.CONFIDENTIAL},
            {
                "tool_name": "vectorize_source",
                "data_classification": "confidential",
            },
        ),
        (
            {"contains_personal_data": True},
            {
                "tool_name": "vectorize_source",
                "contains_personal_data": True,
            },
        ),
        (
            {"contains_sensitive_data": False},
            {
                "tool_name": "vectorize_source",
                "contains_sensitive_data": False,
            },
        ),
    ],
)
def test_evaluator_matches_contextual_scalar_fields(
    rule_kwargs: dict[str, object],
    action_context: dict[str, object],
) -> None:
    result = evaluate_policy(
        agent_context={"agent_id": "agent-1"},
        action_context=action_context,
        environment=Environment.PRODUCTION,
        risk_level=RiskLevel.HIGH,
        rules=[
            PolicyEvaluationRule(
                decision=PolicyDecisionValue.DENY,
                reason="Contextual action is denied.",
                **rule_kwargs,
            )
        ],
    )

    assert result.decision is PolicyDecisionValue.DENY
    assert result.reason == "Contextual action is denied."


def test_evaluator_matches_contextual_inventory_ids() -> None:
    capability_id = uuid4()
    model_id = uuid4()

    result = evaluate_policy(
        agent_context={"agent_id": "agent-1"},
        action_context={
            "tool_name": "vectorize_source",
            "capability_id": capability_id,
            "model_id": model_id,
        },
        environment=Environment.PRODUCTION,
        risk_level=RiskLevel.HIGH,
        rules=[
            PolicyEvaluationRule(
                decision=PolicyDecisionValue.REQUIRE_HUMAN_REVIEW,
                reason="Capability and model context require review.",
                capability_id=str(capability_id),
                model_id=str(model_id),
            )
        ],
    )

    assert result.decision is PolicyDecisionValue.REQUIRE_HUMAN_REVIEW
    assert result.reason == "Capability and model context require review."


def test_evaluator_matches_source_id_against_multiple_request_sources() -> None:
    source_id = uuid4()
    other_source_id = uuid4()

    result = evaluate_policy(
        agent_context={"agent_id": "agent-1"},
        action_context={
            "tool_name": "vectorize_source",
            "source_ids": [other_source_id, source_id],
        },
        environment=Environment.PRODUCTION,
        risk_level=RiskLevel.HIGH,
        rules=[
            PolicyEvaluationRule(
                decision=PolicyDecisionValue.DENY,
                reason="The requested source is denied.",
                source_id=str(source_id),
            )
        ],
    )

    assert result.decision is PolicyDecisionValue.DENY
    assert result.reason == "The requested source is denied."


def test_evaluator_matches_source_ids_when_any_requested_source_overlaps() -> None:
    source_id = uuid4()
    other_source_id = uuid4()
    unrelated_source_id = uuid4()

    result = evaluate_policy(
        agent_context={"agent_id": "agent-1"},
        action_context={
            "tool_name": "vectorize_source",
            "source_ids": [source_id],
        },
        environment=Environment.PRODUCTION,
        risk_level=RiskLevel.HIGH,
        rules=[
            PolicyEvaluationRule(
                decision=PolicyDecisionValue.DENY,
                reason="One of the governed sources is denied.",
                source_ids=(
                    str(unrelated_source_id),
                    str(other_source_id),
                    str(source_id),
                ),
            )
        ],
    )

    assert result.decision is PolicyDecisionValue.DENY
    assert result.reason == "One of the governed sources is denied."


def test_evaluator_does_not_match_unrelated_source_ids() -> None:
    result = evaluate_policy(
        agent_context={"agent_id": "agent-1"},
        action_context={
            "tool_name": "vectorize_source",
            "source_ids": [uuid4()],
        },
        environment=Environment.PRODUCTION,
        risk_level=RiskLevel.HIGH,
        rules=[
            PolicyEvaluationRule(
                decision=PolicyDecisionValue.DENY,
                reason="Unrelated source should not match.",
                source_ids=(str(uuid4()),),
            )
        ],
    )

    assert result.decision is PolicyDecisionValue.NOT_APPLICABLE


def test_evaluator_preserves_existing_tool_name_matching_without_context() -> None:
    result = evaluate_policy(
        agent_context={"agent_id": "agent-1"},
        action_context={"tool_name": "send_email"},
        environment=Environment.DEVELOPMENT,
        risk_level=RiskLevel.LOW,
        rules=[
            PolicyEvaluationRule(
                decision=PolicyDecisionValue.ALLOW,
                reason="Existing tool-only rules still match.",
                tool_name="send_email",
            )
        ],
    )

    assert result.decision is PolicyDecisionValue.ALLOW
    assert result.reason == "Existing tool-only rules still match."


def test_evaluator_matches_resolved_inventory_context_fields() -> None:
    result = evaluate_policy(
        agent_context={"agent_id": "agent-1"},
        action_context={
            "tool_name": "vectorize_source",
            "declared_data_classification": "public",
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
        environment=Environment.PRODUCTION,
        risk_level=RiskLevel.HIGH,
        rules=[
            PolicyEvaluationRule(
                decision=PolicyDecisionValue.DENY,
                reason="Resolved restricted source vectorization is denied.",
                declared_data_classification="public",
                capability_type="tool",
                capability_status="active",
                source_status="active",
                source_data_classification="restricted",
                source_contains_personal_data=True,
                source_contains_sensitive_data=False,
                model_type="embedding",
                model_provider="openai",
                model_provider_type="external",
                model_status="active",
                access_grant_status="active",
                data_usage_review_status="approved",
                data_usage_allowed_purpose="semantic_search_indexing",
                data_usage_prohibited_purpose="model_training",
            )
        ],
    )

    assert result.decision is PolicyDecisionValue.DENY
    assert result.reason == "Resolved restricted source vectorization is denied."


def test_evaluator_matches_missing_resolved_context_values() -> None:
    result = evaluate_policy(
        agent_context={"agent_id": "agent-1"},
        action_context={
            "tool_name": "vectorize_source",
            "capability_status": "missing",
            "source_statuses": ["missing"],
            "model_status": "missing",
            "access_grant_statuses": ["missing"],
            "data_usage_review_statuses": ["missing"],
        },
        environment=Environment.PRODUCTION,
        risk_level=RiskLevel.HIGH,
        rules=[
            PolicyEvaluationRule(
                decision=PolicyDecisionValue.REQUIRE_HUMAN_REVIEW,
                reason="Missing inventory context requires review.",
                capability_status="missing",
                source_status="missing",
                model_status="missing",
                access_grant_status="missing",
                data_usage_review_status="missing",
            )
        ],
    )

    assert result.decision is PolicyDecisionValue.REQUIRE_HUMAN_REVIEW
    assert result.reason == "Missing inventory context requires review."
