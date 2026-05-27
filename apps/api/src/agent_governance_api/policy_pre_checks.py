from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from agent_governance_api.metadata_safety import SafeMetadata, redact_sensitive_text
from agent_governance_api.models import (
    AccessGrant,
    AccessGrantStatus,
    AccessGrantSubjectType,
    AccessGrantTargetType,
    Capability,
    CapabilityStatus,
    CheckResult,
    CheckResultConfidence,
    CheckResultOutcome,
    CheckResultTargetType,
    DataSource,
    DataSourceStatus,
    DataUsageProfile,
    DataUsageReviewStatus,
    ModelAsset,
    ModelAssetStatus,
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


def check_access_grant_status(
    session: Session,
    *,
    check_tool_id: UUID,
    agent_id: UUID,
    target_type: AccessGrantTargetType,
    target_id: UUID | None = None,
    external_ref: str | None = None,
    run_id: UUID | None = None,
    trace_event_id: UUID | None = None,
    policy_decision_id: UUID | None = None,
) -> CheckResult:
    """Check an Agent AccessGrant using persisted grant metadata only."""
    metadata = {
        "check_type": "access_grant_status",
        "requested_target_type": target_type.value,
    }
    if target_id is not None:
        metadata["requested_target_id"] = str(target_id)

    if target_id is None and not external_ref:
        return persist_check_result(
            session,
            check_tool_id=check_tool_id,
            agent_id=agent_id,
            run_id=run_id,
            trace_event_id=trace_event_id,
            policy_decision_id=policy_decision_id,
            target_type=CheckResultTargetType.ACCESS_GRANT,
            outcome=CheckResultOutcome.NOT_APPLICABLE,
            confidence=CheckResultConfidence.HIGH,
            summary="AccessGrant check skipped because target reference is missing.",
            reason="A target_id or external_ref is required for AccessGrant checks.",
            metadata=metadata,
        )

    statement = select(AccessGrant).where(
        AccessGrant.subject_type == AccessGrantSubjectType.AGENT,
        AccessGrant.subject_id == agent_id,
        AccessGrant.target_type == target_type,
    )
    if target_id is not None:
        statement = statement.where(AccessGrant.target_id == target_id)
    else:
        statement = statement.where(AccessGrant.external_ref == external_ref)

    access_grants = list(
        session.scalars(
            statement.order_by(AccessGrant.created_at.desc(), AccessGrant.id.desc())
        ).all()
    )
    active_grant = next(
        (
            grant
            for grant in access_grants
            if grant.status is AccessGrantStatus.ACTIVE
            and not _is_datetime_expired(grant.expires_at)
        ),
        None,
    )
    if active_grant is not None:
        return _persist_access_grant_result(
            session,
            check_tool_id=check_tool_id,
            access_grant=active_grant,
            agent_id=agent_id,
            outcome=CheckResultOutcome.PASS,
            confidence=CheckResultConfidence.HIGH,
            summary="Active AccessGrant exists for requested target.",
            reason="The matching AccessGrant is active and not expired.",
            metadata=metadata,
            run_id=run_id,
            trace_event_id=trace_event_id,
            policy_decision_id=policy_decision_id,
        )

    failing_grant = next(
        (
            grant
            for grant in access_grants
            if grant.status
            in {
                AccessGrantStatus.REVOKED,
                AccessGrantStatus.SUSPENDED,
                AccessGrantStatus.EXPIRED,
            }
            or _is_datetime_expired(grant.expires_at)
        ),
        None,
    )
    if failing_grant is not None:
        reason = "The matching AccessGrant is not active."
        if _is_datetime_expired(failing_grant.expires_at):
            reason = "The matching AccessGrant is expired."
        return _persist_access_grant_result(
            session,
            check_tool_id=check_tool_id,
            access_grant=failing_grant,
            agent_id=agent_id,
            outcome=CheckResultOutcome.FAIL,
            confidence=CheckResultConfidence.HIGH,
            summary="AccessGrant is not usable for requested target.",
            reason=reason,
            metadata=metadata,
            run_id=run_id,
            trace_event_id=trace_event_id,
            policy_decision_id=policy_decision_id,
        )

    if access_grants:
        pending_grant = access_grants[0]
        return _persist_access_grant_result(
            session,
            check_tool_id=check_tool_id,
            access_grant=pending_grant,
            agent_id=agent_id,
            outcome=CheckResultOutcome.UNKNOWN,
            confidence=CheckResultConfidence.MEDIUM,
            summary="AccessGrant exists but is not active yet.",
            reason=f"AccessGrant status is {pending_grant.status.value}.",
            metadata=metadata,
            run_id=run_id,
            trace_event_id=trace_event_id,
            policy_decision_id=policy_decision_id,
        )

    return persist_check_result(
        session,
        check_tool_id=check_tool_id,
        agent_id=agent_id,
        run_id=run_id,
        trace_event_id=trace_event_id,
        policy_decision_id=policy_decision_id,
        target_type=CheckResultTargetType.ACCESS_GRANT,
        outcome=CheckResultOutcome.UNKNOWN,
        confidence=CheckResultConfidence.MEDIUM,
        summary="No AccessGrant found for requested target.",
        reason="No persisted AccessGrant matched the Agent and target reference.",
        metadata=metadata,
    )


def check_data_usage_profile_status(
    session: Session,
    *,
    check_tool_id: UUID,
    source_id: UUID,
    agent_id: UUID | None = None,
    run_id: UUID | None = None,
    trace_event_id: UUID | None = None,
    policy_decision_id: UUID | None = None,
) -> CheckResult:
    """Check a Source DataUsageProfile review status without inspecting content."""
    metadata = {
        "check_type": "data_usage_profile_status",
        "source_id": str(source_id),
    }
    profile = session.scalar(
        select(DataUsageProfile).where(DataUsageProfile.source_id == source_id)
    )
    if profile is None:
        return persist_check_result(
            session,
            check_tool_id=check_tool_id,
            agent_id=agent_id,
            run_id=run_id,
            trace_event_id=trace_event_id,
            policy_decision_id=policy_decision_id,
            target_type=CheckResultTargetType.DATA_USAGE_PROFILE,
            outcome=CheckResultOutcome.UNKNOWN,
            confidence=CheckResultConfidence.MEDIUM,
            summary="Data Usage Profile is missing for Source.",
            reason="No DataUsageProfile record exists for the requested Source.",
            metadata=metadata,
        )

    review_expired = _is_datetime_expired(profile.review_expires_at)
    metadata.update(
        {
            "review_status": profile.review_status.value,
            "review_expired": review_expired,
            "data_classification": profile.data_classification.value,
            "contains_personal_data": profile.contains_personal_data,
            "contains_sensitive_data": profile.contains_sensitive_data,
            "dpia_required": profile.dpia_required,
        }
    )
    if profile.review_status is DataUsageReviewStatus.APPROVED and not review_expired:
        return persist_check_result(
            session,
            check_tool_id=check_tool_id,
            agent_id=agent_id,
            run_id=run_id,
            trace_event_id=trace_event_id,
            policy_decision_id=policy_decision_id,
            target_type=CheckResultTargetType.DATA_USAGE_PROFILE,
            target_id=profile.id,
            outcome=CheckResultOutcome.PASS,
            confidence=CheckResultConfidence.HIGH,
            summary="Data Usage Profile is approved and current.",
            reason="The profile review status is approved and review has not expired.",
            metadata=metadata,
        )

    if (
        profile.review_status
        in {DataUsageReviewStatus.REJECTED, DataUsageReviewStatus.EXPIRED}
        or review_expired
    ):
        reason = f"Data Usage Profile review status is {profile.review_status.value}."
        if review_expired:
            reason = "Data Usage Profile review has expired."
        return persist_check_result(
            session,
            check_tool_id=check_tool_id,
            agent_id=agent_id,
            run_id=run_id,
            trace_event_id=trace_event_id,
            policy_decision_id=policy_decision_id,
            target_type=CheckResultTargetType.DATA_USAGE_PROFILE,
            target_id=profile.id,
            outcome=CheckResultOutcome.FAIL,
            confidence=CheckResultConfidence.HIGH,
            summary="Data Usage Profile is not approved for use.",
            reason=reason,
            metadata=metadata,
        )

    return persist_check_result(
        session,
        check_tool_id=check_tool_id,
        agent_id=agent_id,
        run_id=run_id,
        trace_event_id=trace_event_id,
        policy_decision_id=policy_decision_id,
        target_type=CheckResultTargetType.DATA_USAGE_PROFILE,
        target_id=profile.id,
        outcome=CheckResultOutcome.UNKNOWN,
        confidence=CheckResultConfidence.MEDIUM,
        summary="Data Usage Profile review status is not final.",
        reason=f"Data Usage Profile review status is {profile.review_status.value}.",
        metadata=metadata,
    )


def check_source_status(
    session: Session,
    *,
    check_tool_id: UUID,
    source_id: UUID,
    agent_id: UUID | None = None,
    run_id: UUID | None = None,
    trace_event_id: UUID | None = None,
    policy_decision_id: UUID | None = None,
) -> CheckResult:
    """Check a Source inventory status using metadata only."""
    source = session.get(DataSource, source_id)
    if source is None:
        return _persist_missing_inventory_result(
            session,
            check_tool_id=check_tool_id,
            agent_id=agent_id,
            run_id=run_id,
            trace_event_id=trace_event_id,
            policy_decision_id=policy_decision_id,
            target_type=CheckResultTargetType.SOURCE,
            check_type="source_status",
            requested_id_key="source_id",
            requested_id=source_id,
            summary="Source inventory record was not found.",
            reason="No Source exists for the requested source_id.",
        )

    outcome = (
        CheckResultOutcome.PASS
        if source.status is DataSourceStatus.ACTIVE
        else CheckResultOutcome.FAIL
    )
    return persist_check_result(
        session,
        check_tool_id=check_tool_id,
        agent_id=agent_id,
        run_id=run_id,
        trace_event_id=trace_event_id,
        policy_decision_id=policy_decision_id,
        target_type=CheckResultTargetType.SOURCE,
        target_id=source.id,
        outcome=outcome,
        confidence=CheckResultConfidence.HIGH,
        summary=(
            "Source inventory record is active."
            if outcome is CheckResultOutcome.PASS
            else "Source inventory record is not active."
        ),
        reason=f"Source status is {source.status.value}.",
        metadata={
            "check_type": "source_status",
            "source_id": str(source.id),
            "source_status": source.status.value,
        },
    )


def check_capability_status(
    session: Session,
    *,
    check_tool_id: UUID,
    capability_id: UUID,
    agent_id: UUID | None = None,
    run_id: UUID | None = None,
    trace_event_id: UUID | None = None,
    policy_decision_id: UUID | None = None,
) -> CheckResult:
    """Check a Capability inventory status using metadata only."""
    capability = session.get(Capability, capability_id)
    if capability is None:
        return _persist_missing_inventory_result(
            session,
            check_tool_id=check_tool_id,
            agent_id=agent_id,
            run_id=run_id,
            trace_event_id=trace_event_id,
            policy_decision_id=policy_decision_id,
            target_type=CheckResultTargetType.CAPABILITY,
            check_type="capability_status",
            requested_id_key="capability_id",
            requested_id=capability_id,
            summary="Capability inventory record was not found.",
            reason="No Capability exists for the requested capability_id.",
        )

    outcome = (
        CheckResultOutcome.PASS
        if capability.status is CapabilityStatus.ACTIVE
        else CheckResultOutcome.FAIL
    )
    return persist_check_result(
        session,
        check_tool_id=check_tool_id,
        agent_id=agent_id,
        run_id=run_id,
        trace_event_id=trace_event_id,
        policy_decision_id=policy_decision_id,
        target_type=CheckResultTargetType.CAPABILITY,
        target_id=capability.id,
        outcome=outcome,
        confidence=CheckResultConfidence.HIGH,
        summary=(
            "Capability inventory record is active."
            if outcome is CheckResultOutcome.PASS
            else "Capability inventory record is not active."
        ),
        reason=f"Capability status is {capability.status.value}.",
        metadata={
            "check_type": "capability_status",
            "capability_id": str(capability.id),
            "capability_status": capability.status.value,
        },
    )


def check_model_asset_status(
    session: Session,
    *,
    check_tool_id: UUID,
    model_asset_id: UUID,
    agent_id: UUID | None = None,
    run_id: UUID | None = None,
    trace_event_id: UUID | None = None,
    policy_decision_id: UUID | None = None,
) -> CheckResult:
    """Check a ModelAsset inventory status using metadata only."""
    model_asset = session.get(ModelAsset, model_asset_id)
    if model_asset is None:
        return _persist_missing_inventory_result(
            session,
            check_tool_id=check_tool_id,
            agent_id=agent_id,
            run_id=run_id,
            trace_event_id=trace_event_id,
            policy_decision_id=policy_decision_id,
            target_type=CheckResultTargetType.MODEL_ASSET,
            check_type="model_asset_status",
            requested_id_key="model_asset_id",
            requested_id=model_asset_id,
            summary="ModelAsset inventory record was not found.",
            reason="No ModelAsset exists for the requested model_asset_id.",
        )

    outcome = (
        CheckResultOutcome.PASS
        if model_asset.status is ModelAssetStatus.ACTIVE
        else CheckResultOutcome.FAIL
    )
    return persist_check_result(
        session,
        check_tool_id=check_tool_id,
        agent_id=agent_id,
        run_id=run_id,
        trace_event_id=trace_event_id,
        policy_decision_id=policy_decision_id,
        target_type=CheckResultTargetType.MODEL_ASSET,
        target_id=model_asset.id,
        outcome=outcome,
        confidence=CheckResultConfidence.HIGH,
        summary=(
            "ModelAsset inventory record is active."
            if outcome is CheckResultOutcome.PASS
            else "ModelAsset inventory record is not active."
        ),
        reason=f"ModelAsset status is {model_asset.status.value}.",
        metadata={
            "check_type": "model_asset_status",
            "model_asset_id": str(model_asset.id),
            "model_asset_status": model_asset.status.value,
        },
    )


def record_metadata_check_error(
    session: Session,
    *,
    check_tool_id: UUID,
    target_type: CheckResultTargetType,
    summary: str,
    reason: str,
    agent_id: UUID | None = None,
    run_id: UUID | None = None,
    trace_event_id: UUID | None = None,
    policy_decision_id: UUID | None = None,
    target_id: UUID | None = None,
    metadata: SafeMetadata | None = None,
) -> CheckResult:
    """Persist a safe error result for an internal metadata-only check."""
    return persist_check_result(
        session,
        check_tool_id=check_tool_id,
        agent_id=agent_id,
        run_id=run_id,
        trace_event_id=trace_event_id,
        policy_decision_id=policy_decision_id,
        target_type=target_type,
        target_id=target_id,
        outcome=CheckResultOutcome.ERROR,
        confidence=CheckResultConfidence.UNKNOWN,
        summary=summary,
        reason=reason,
        metadata={"check_type": "metadata_check_error", **(metadata or {})},
    )


def _persist_access_grant_result(
    session: Session,
    *,
    check_tool_id: UUID,
    access_grant: AccessGrant,
    agent_id: UUID,
    outcome: CheckResultOutcome,
    confidence: CheckResultConfidence,
    summary: str,
    reason: str,
    metadata: SafeMetadata,
    run_id: UUID | None,
    trace_event_id: UUID | None,
    policy_decision_id: UUID | None,
) -> CheckResult:
    return persist_check_result(
        session,
        check_tool_id=check_tool_id,
        agent_id=agent_id,
        run_id=run_id,
        trace_event_id=trace_event_id,
        policy_decision_id=policy_decision_id,
        target_type=CheckResultTargetType.ACCESS_GRANT,
        target_id=access_grant.id,
        outcome=outcome,
        confidence=confidence,
        summary=summary,
        reason=reason,
        metadata={
            **metadata,
            "access_grant_id": str(access_grant.id),
            "access_grant_status": access_grant.status.value,
            "access_grant_expired": _is_datetime_expired(access_grant.expires_at),
        },
    )


def _persist_missing_inventory_result(
    session: Session,
    *,
    check_tool_id: UUID,
    agent_id: UUID | None,
    run_id: UUID | None,
    trace_event_id: UUID | None,
    policy_decision_id: UUID | None,
    target_type: CheckResultTargetType,
    check_type: str,
    requested_id_key: str,
    requested_id: UUID,
    summary: str,
    reason: str,
) -> CheckResult:
    return persist_check_result(
        session,
        check_tool_id=check_tool_id,
        agent_id=agent_id,
        run_id=run_id,
        trace_event_id=trace_event_id,
        policy_decision_id=policy_decision_id,
        target_type=target_type,
        outcome=CheckResultOutcome.UNKNOWN,
        confidence=CheckResultConfidence.MEDIUM,
        summary=summary,
        reason=reason,
        metadata={
            "check_type": check_type,
            requested_id_key: str(requested_id),
        },
    )


def _is_datetime_expired(value: datetime | None) -> bool:
    if value is None:
        return False
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value <= datetime.now(UTC)
