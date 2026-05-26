from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from agent_governance_api.metadata_safety import SafeMetadata, redact_sensitive_text
from agent_governance_api.models import (
    CheckResult,
    CheckResultConfidence,
    CheckResultOutcome,
    CheckResultTargetType,
)


def persist_check_result(
    session: Session,
    *,
    check_tool_id: UUID,
    target_type: CheckResultTargetType,
    outcome: CheckResultOutcome,
    summary: str,
    agent_id: UUID | None = None,
    run_id: UUID | None = None,
    trace_event_id: UUID | None = None,
    policy_decision_id: UUID | None = None,
    target_id: UUID | None = None,
    confidence: CheckResultConfidence | None = None,
    reason: str | None = None,
    metadata: SafeMetadata | None = None,
) -> CheckResult:
    """Persist a safe metadata-only pre-check result without committing."""
    if not summary.strip():
        raise ValueError("CheckResult summary must be non-empty.")
    safe_summary = redact_sensitive_text(summary.strip())
    safe_reason = redact_sensitive_text(reason.strip()) if reason is not None else None

    check_result = CheckResult(
        check_tool_id=check_tool_id,
        agent_id=agent_id,
        run_id=run_id,
        trace_event_id=trace_event_id,
        policy_decision_id=policy_decision_id,
        target_type=target_type,
        target_id=target_id,
        outcome=outcome,
        confidence=confidence,
        summary=safe_summary,
        reason=safe_reason,
        metadata_=metadata or {},
        created_at=datetime.now(UTC),
    )
    session.add(check_result)
    session.flush()

    return check_result
