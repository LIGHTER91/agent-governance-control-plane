from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from agent_governance_api.metadata_safety import UNSAFE_METADATA_KEY_PARTS
from agent_governance_api.models import (
    PolicyDecision,
    PolicyVersion,
    PolicyVersionStatus,
)
from agent_governance_api.policy_evaluator import PolicyEvaluationResult


def persist_policy_decision(
    session: Session,
    *,
    agent_id: UUID,
    evaluation_result: PolicyEvaluationResult,
    policy_id: str | UUID | None = None,
    rule_id: str | UUID | None = None,
    trace_event_id: str | UUID | None = None,
    context_hash: str | None = None,
) -> PolicyDecision:
    """Persist a policy decision without committing the caller's transaction."""
    safe_context_hash = _safe_context_hash(context_hash)
    selected_policy_id = _uuid_or_none(policy_id) or _uuid_or_none(
        evaluation_result.policy_id
    )
    selected_rule_id = _uuid_or_none(rule_id) or _uuid_or_none(
        evaluation_result.rule_id
    )
    policy_decision = PolicyDecision(
        agent_id=agent_id,
        policy_id=selected_policy_id,
        policy_version_id=_active_policy_version_id(session, selected_policy_id),
        rule_id=selected_rule_id,
        trace_event_id=_uuid_or_none(trace_event_id),
        decision=evaluation_result.decision,
        reason=evaluation_result.reason,
        context_hash=safe_context_hash,
        created_at=datetime.now(UTC),
    )
    session.add(policy_decision)
    session.flush()

    return policy_decision


def _active_policy_version_id(session: Session, policy_id: UUID | None) -> UUID | None:
    if policy_id is None:
        return None

    active_version = session.scalar(
        select(PolicyVersion)
        .where(
            PolicyVersion.policy_id == policy_id,
            PolicyVersion.status == PolicyVersionStatus.ACTIVE,
        )
        .order_by(
            PolicyVersion.version_number.desc(),
            PolicyVersion.activated_at.desc(),
            PolicyVersion.id.desc(),
        )
    )
    return active_version.id if active_version is not None else None


def _uuid_or_none(value: str | UUID | None) -> UUID | None:
    if value is None:
        return None
    if isinstance(value, UUID):
        return value
    return UUID(value)


def _safe_context_hash(context_hash: str | None) -> str | None:
    if context_hash is None:
        return None
    if not context_hash.strip():
        raise ValueError("PolicyDecision context_hash must not be empty.")
    lowered_context_hash = context_hash.lower()
    if any(part in lowered_context_hash for part in UNSAFE_METADATA_KEY_PARTS):
        raise ValueError(
            "PolicyDecision context_hash must not contain raw sensitive payloads."
        )
    return context_hash
