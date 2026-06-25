from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Protocol
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from agent_governance_api.metadata_safety import (
    SafeMetadata,
    filter_safe_metadata,
    redact_sensitive_text,
    reject_unsafe_metadata_keys,
)
from agent_governance_api.models import (
    AccessGrant,
    AccessGrantStatus,
    AccessGrantSubjectType,
    AccessGrantTargetType,
    Capability,
    CapabilityStatus,
    CheckResultConfidence,
    CheckResultOutcome,
    CheckResultTargetType,
    DataSource,
    DataSourceStatus,
    DataUsageProfile,
    DataUsageReviewStatus,
    ModelAsset,
    ModelAssetStatus,
    ModelProvider,
)


class CheckToolExecutionMode(StrEnum):
    METADATA_ONLY = "metadata_only"
    EXTERNAL_REFERENCE_LOOKUP = "external_reference_lookup"
    SAMPLE_BASED_EXTERNAL_SCANNER = "sample_based_external_scanner"
    HUMAN_REVIEW_REQUIRED = "human_review_required"


class CheckToolError(Exception):
    """Safe adapter-boundary error for unsupported check execution."""


@dataclass(frozen=True, slots=True)
class CheckToolRequest:
    check_type: str
    agent_id: UUID | None = None
    run_id: UUID | None = None
    request_id: str | None = None
    trace_event_id: UUID | None = None
    policy_decision_id: UUID | None = None
    policy_version_id: UUID | None = None
    policy_rule_id: UUID | None = None
    policy_check_step_id: UUID | None = None
    target_type: CheckResultTargetType | None = None
    target_id: UUID | None = None
    source_id: UUID | None = None
    model_id: UUID | None = None
    capability_id: UUID | None = None
    purpose: str | None = None
    data_classification: str | None = None
    declared_metadata: Mapping[str, object] = field(default_factory=dict)
    resolved_inventory_metadata: Mapping[str, object] = field(default_factory=dict)
    execution_mode: CheckToolExecutionMode = CheckToolExecutionMode.METADATA_ONLY

    def __post_init__(self) -> None:
        check_type = self.check_type.strip().lower()
        if not check_type:
            raise ValueError("CheckToolRequest check_type must be non-empty.")
        object.__setattr__(self, "check_type", check_type)
        object.__setattr__(
            self,
            "declared_metadata",
            _safe_request_metadata(
                self.declared_metadata,
                field_name="declared_metadata",
            ),
        )
        object.__setattr__(
            self,
            "resolved_inventory_metadata",
            _safe_request_metadata(
                self.resolved_inventory_metadata,
                field_name="resolved_inventory_metadata",
            ),
        )


@dataclass(frozen=True, slots=True)
class CheckToolResult:
    check_type: str
    target_type: CheckResultTargetType
    outcome: CheckResultOutcome
    summary: str
    target_id: UUID | None = None
    confidence: CheckResultConfidence | None = None
    reason: str | None = None
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        check_type = self.check_type.strip().lower()
        if not check_type:
            raise ValueError("CheckToolResult check_type must be non-empty.")
        summary = redact_sensitive_text(self.summary.strip())
        if not summary:
            raise ValueError("CheckToolResult summary must be non-empty.")
        reason = (
            redact_sensitive_text(self.reason.strip())
            if self.reason is not None
            else None
        )
        object.__setattr__(self, "check_type", check_type)
        object.__setattr__(self, "summary", summary)
        object.__setattr__(self, "reason", reason)
        object.__setattr__(
            self,
            "metadata",
            _safe_result_metadata(self.metadata),
        )

    def to_check_result_payload(
        self,
        request: CheckToolRequest,
        *,
        check_tool_id: UUID,
    ) -> dict[str, object]:
        metadata = {
            **_request_reference_metadata(request),
            **dict(self.metadata),
            "check_type": self.check_type,
        }
        return {
            "check_tool_id": check_tool_id,
            "agent_id": request.agent_id,
            "run_id": request.run_id,
            "trace_event_id": request.trace_event_id,
            "policy_decision_id": request.policy_decision_id,
            "target_type": self.target_type,
            "target_id": self.target_id,
            "outcome": self.outcome,
            "confidence": self.confidence,
            "summary": self.summary,
            "reason": self.reason,
            "metadata": _safe_result_metadata(metadata),
        }


class CheckToolAdapter(Protocol):
    name: str
    execution_mode: CheckToolExecutionMode
    supported_check_types: frozenset[str]

    def run(self, session: Session, request: CheckToolRequest) -> CheckToolResult:
        """Return a safe check result without executing governed tools."""


ACCESS_GRANT_STATUS = "access_grant_status"
DATA_USAGE_PROFILE_STATUS = "data_usage_profile_status"
SOURCE_STATUS = "source_status"
SOURCE_CLASSIFICATION = "source_classification"
MODEL_ASSET_STATUS = "model_asset_status"
MODEL_PROVIDER_TYPE = "model_provider_type"
CAPABILITY_STATUS = "capability_status"
MODEL_PROVIDER_CLASS_EXTERNAL = "external"
MODEL_PROVIDER_CLASS_LOCAL = "local"
MODEL_PROVIDER_CLASS_UNKNOWN = "unknown"

SUPPORTED_METADATA_ONLY_CHECK_TYPES = frozenset(
    {
        ACCESS_GRANT_STATUS,
        DATA_USAGE_PROFILE_STATUS,
        SOURCE_STATUS,
        SOURCE_CLASSIFICATION,
        MODEL_ASSET_STATUS,
        MODEL_PROVIDER_TYPE,
        CAPABILITY_STATUS,
    }
)


class MetadataOnlyCheckToolAdapter:
    name = "agcp_metadata_only_check_tool_adapter"
    execution_mode = CheckToolExecutionMode.METADATA_ONLY
    supported_check_types = SUPPORTED_METADATA_ONLY_CHECK_TYPES

    def run(self, session: Session, request: CheckToolRequest) -> CheckToolResult:
        if request.execution_mode is not CheckToolExecutionMode.METADATA_ONLY:
            raise CheckToolError(
                "Only metadata_only execution is implemented for local "
                "CheckTool adapters."
            )

        if request.check_type == ACCESS_GRANT_STATUS:
            return self._check_access_grant_status(session, request)
        if request.check_type == DATA_USAGE_PROFILE_STATUS:
            return self._check_data_usage_profile_status(session, request)
        if request.check_type == SOURCE_STATUS:
            return self._check_source_status(session, request)
        if request.check_type == SOURCE_CLASSIFICATION:
            return self._check_source_classification(session, request)
        if request.check_type == MODEL_ASSET_STATUS:
            return self._check_model_asset_status(session, request)
        if request.check_type == MODEL_PROVIDER_TYPE:
            return self._check_model_provider_type(session, request)
        if request.check_type == CAPABILITY_STATUS:
            return self._check_capability_status(session, request)

        return _result(
            request,
            target_type=CheckResultTargetType.EXTERNAL,
            outcome=CheckResultOutcome.ERROR,
            confidence=CheckResultConfidence.UNKNOWN,
            summary="Unsupported metadata-only CheckTool check_type.",
            reason="No local metadata-only adapter is registered for this check_type.",
            metadata={"error_type": "unsupported_check_type"},
        )

    def _check_access_grant_status(
        self,
        session: Session,
        request: CheckToolRequest,
    ) -> CheckToolResult:
        if request.agent_id is None:
            return _missing_context_result(
                request,
                target_type=CheckResultTargetType.ACCESS_GRANT,
                missing_context_field="agent_id",
            )
        target = _access_grant_target_from_request(request)
        if target is None:
            return _missing_context_result(
                request,
                target_type=CheckResultTargetType.ACCESS_GRANT,
                missing_context_field="access_grant_target",
            )

        target_type, target_id = target
        statement = (
            select(AccessGrant)
            .where(
                AccessGrant.subject_type == AccessGrantSubjectType.AGENT,
                AccessGrant.subject_id == request.agent_id,
                AccessGrant.target_type == target_type,
                AccessGrant.target_id == target_id,
            )
            .order_by(AccessGrant.created_at.desc(), AccessGrant.id.desc())
        )
        access_grants = list(session.scalars(statement).all())
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
            return _access_grant_result(
                request,
                active_grant,
                outcome=CheckResultOutcome.PASS,
                confidence=CheckResultConfidence.HIGH,
                summary="Active AccessGrant exists for requested target.",
                reason="The matching AccessGrant is active and not expired.",
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
            return _access_grant_result(
                request,
                failing_grant,
                outcome=CheckResultOutcome.FAIL,
                confidence=CheckResultConfidence.HIGH,
                summary="AccessGrant is not usable for requested target.",
                reason=reason,
            )

        if access_grants:
            pending_grant = access_grants[0]
            return _access_grant_result(
                request,
                pending_grant,
                outcome=CheckResultOutcome.UNKNOWN,
                confidence=CheckResultConfidence.MEDIUM,
                summary="AccessGrant exists but is not active yet.",
                reason=f"AccessGrant status is {pending_grant.status.value}.",
            )

        return _result(
            request,
            target_type=CheckResultTargetType.ACCESS_GRANT,
            outcome=CheckResultOutcome.UNKNOWN,
            confidence=CheckResultConfidence.MEDIUM,
            summary="No AccessGrant found for requested target.",
            reason="No persisted AccessGrant matched the Agent and target reference.",
            metadata={
                "requested_target_type": target_type.value,
                "requested_target_id": str(target_id),
            },
        )

    def _check_data_usage_profile_status(
        self,
        session: Session,
        request: CheckToolRequest,
    ) -> CheckToolResult:
        source_id = _source_id_from_request(request)
        if source_id is None:
            return _missing_context_result(
                request,
                target_type=CheckResultTargetType.DATA_USAGE_PROFILE,
                missing_context_field="source_id",
            )
        profile = _data_usage_profile_for_source(session, source_id)
        if profile is None:
            return _result(
                request,
                target_type=CheckResultTargetType.DATA_USAGE_PROFILE,
                outcome=CheckResultOutcome.UNKNOWN,
                confidence=CheckResultConfidence.MEDIUM,
                summary="Data Usage Profile is missing for Source.",
                reason="No DataUsageProfile record exists for the requested Source.",
                metadata={"source_id": str(source_id)},
            )

        review_expired = _is_datetime_expired(profile.review_expires_at)
        metadata = _data_usage_profile_metadata(profile, review_expired)
        if (
            profile.review_status is DataUsageReviewStatus.APPROVED
            and not review_expired
        ):
            return _result(
                request,
                target_type=CheckResultTargetType.DATA_USAGE_PROFILE,
                target_id=profile.id,
                outcome=CheckResultOutcome.PASS,
                confidence=CheckResultConfidence.HIGH,
                summary="Data Usage Profile is approved and current.",
                reason=(
                    "The profile review status is approved and review has not expired."
                ),
                metadata=metadata,
            )
        if (
            profile.review_status
            in {DataUsageReviewStatus.REJECTED, DataUsageReviewStatus.EXPIRED}
            or review_expired
        ):
            reason = (
                f"Data Usage Profile review status is {profile.review_status.value}."
            )
            if review_expired:
                reason = "Data Usage Profile review has expired."
            return _result(
                request,
                target_type=CheckResultTargetType.DATA_USAGE_PROFILE,
                target_id=profile.id,
                outcome=CheckResultOutcome.FAIL,
                confidence=CheckResultConfidence.HIGH,
                summary="Data Usage Profile is not approved for use.",
                reason=reason,
                metadata=metadata,
            )
        return _result(
            request,
            target_type=CheckResultTargetType.DATA_USAGE_PROFILE,
            target_id=profile.id,
            outcome=CheckResultOutcome.UNKNOWN,
            confidence=CheckResultConfidence.MEDIUM,
            summary="Data Usage Profile review status is not final.",
            reason=(
                f"Data Usage Profile review status is {profile.review_status.value}."
            ),
            metadata=metadata,
        )

    def _check_source_status(
        self,
        session: Session,
        request: CheckToolRequest,
    ) -> CheckToolResult:
        source_id = _source_id_from_request(request)
        if source_id is None:
            return _missing_context_result(
                request,
                target_type=CheckResultTargetType.SOURCE,
                missing_context_field="source_id",
            )
        source = session.get(DataSource, source_id)
        if source is None:
            return _missing_inventory_result(
                request,
                target_type=CheckResultTargetType.SOURCE,
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
        return _result(
            request,
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
                "source_id": str(source.id),
                "source_status": source.status.value,
            },
        )

    def _check_source_classification(
        self,
        session: Session,
        request: CheckToolRequest,
    ) -> CheckToolResult:
        source_id = _source_id_from_request(request)
        if source_id is None:
            return _missing_context_result(
                request,
                target_type=CheckResultTargetType.DATA_USAGE_PROFILE,
                missing_context_field="source_id",
            )
        profile = _data_usage_profile_for_source(session, source_id)
        if profile is None:
            return _result(
                request,
                target_type=CheckResultTargetType.DATA_USAGE_PROFILE,
                outcome=CheckResultOutcome.UNKNOWN,
                confidence=CheckResultConfidence.MEDIUM,
                summary="Source classification metadata is unavailable.",
                reason=("No DataUsageProfile record exists for the requested Source."),
                metadata={"source_id": str(source_id)},
            )
        return _result(
            request,
            target_type=CheckResultTargetType.DATA_USAGE_PROFILE,
            target_id=profile.id,
            outcome=CheckResultOutcome.PASS,
            confidence=CheckResultConfidence.HIGH,
            summary="Source classification metadata is available.",
            reason="The classification was read from the Source DataUsageProfile.",
            metadata=_data_usage_profile_metadata(
                profile,
                _is_datetime_expired(profile.review_expires_at),
            ),
        )

    def _check_model_asset_status(
        self,
        session: Session,
        request: CheckToolRequest,
    ) -> CheckToolResult:
        model_id = _model_id_from_request(request)
        if model_id is None:
            return _missing_context_result(
                request,
                target_type=CheckResultTargetType.MODEL_ASSET,
                missing_context_field="model_id",
            )
        model_asset = session.get(ModelAsset, model_id)
        if model_asset is None:
            return _missing_inventory_result(
                request,
                target_type=CheckResultTargetType.MODEL_ASSET,
                requested_id_key="model_id",
                requested_id=model_id,
                summary="ModelAsset inventory record was not found.",
                reason="No ModelAsset exists for the requested model_id.",
            )
        outcome = (
            CheckResultOutcome.PASS
            if model_asset.status is ModelAssetStatus.ACTIVE
            else CheckResultOutcome.FAIL
        )
        return _result(
            request,
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
            metadata=_model_asset_metadata(model_asset),
        )

    def _check_model_provider_type(
        self,
        session: Session,
        request: CheckToolRequest,
    ) -> CheckToolResult:
        model_id = _model_id_from_request(request)
        if model_id is None:
            return _missing_context_result(
                request,
                target_type=CheckResultTargetType.MODEL_ASSET,
                missing_context_field="model_id",
            )
        model_asset = session.get(ModelAsset, model_id)
        if model_asset is None:
            return _missing_inventory_result(
                request,
                target_type=CheckResultTargetType.MODEL_ASSET,
                requested_id_key="model_id",
                requested_id=model_id,
                summary="ModelAsset provider metadata was not found.",
                reason="No ModelAsset exists for the requested model_id.",
            )
        return _result(
            request,
            target_type=CheckResultTargetType.MODEL_ASSET,
            target_id=model_asset.id,
            outcome=CheckResultOutcome.PASS,
            confidence=CheckResultConfidence.HIGH,
            summary="ModelAsset provider metadata is available.",
            reason="The provider and model type were read from ModelAsset metadata.",
            metadata=_model_asset_metadata(model_asset),
        )

    def _check_capability_status(
        self,
        session: Session,
        request: CheckToolRequest,
    ) -> CheckToolResult:
        capability_id = _capability_id_from_request(request)
        if capability_id is None:
            return _missing_context_result(
                request,
                target_type=CheckResultTargetType.CAPABILITY,
                missing_context_field="capability_id",
            )
        capability = session.get(Capability, capability_id)
        if capability is None:
            return _missing_inventory_result(
                request,
                target_type=CheckResultTargetType.CAPABILITY,
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
        return _result(
            request,
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
                "capability_id": str(capability.id),
                "capability_status": capability.status.value,
                "capability_type": capability.capability_type.value,
                "risk_level": capability.risk_level.value,
            },
        )


def _result(
    request: CheckToolRequest,
    *,
    target_type: CheckResultTargetType,
    outcome: CheckResultOutcome,
    confidence: CheckResultConfidence,
    summary: str,
    reason: str,
    target_id: UUID | None = None,
    metadata: Mapping[str, object] | None = None,
) -> CheckToolResult:
    return CheckToolResult(
        check_type=request.check_type,
        target_type=target_type,
        target_id=target_id,
        outcome=outcome,
        confidence=confidence,
        summary=summary,
        reason=reason,
        metadata={
            **_request_reference_metadata(request),
            **dict(metadata or {}),
            "execution_mode": request.execution_mode.value,
        },
    )


def _access_grant_result(
    request: CheckToolRequest,
    access_grant: AccessGrant,
    *,
    outcome: CheckResultOutcome,
    confidence: CheckResultConfidence,
    summary: str,
    reason: str,
) -> CheckToolResult:
    return _result(
        request,
        target_type=CheckResultTargetType.ACCESS_GRANT,
        target_id=access_grant.id,
        outcome=outcome,
        confidence=confidence,
        summary=summary,
        reason=reason,
        metadata={
            "access_grant_id": str(access_grant.id),
            "access_grant_status": access_grant.status.value,
            "access_grant_expired": _is_datetime_expired(access_grant.expires_at),
            "requested_target_type": access_grant.target_type.value,
            "requested_target_id": str(access_grant.target_id),
        },
    )


def _missing_context_result(
    request: CheckToolRequest,
    *,
    target_type: CheckResultTargetType,
    missing_context_field: str,
) -> CheckToolResult:
    return _result(
        request,
        target_type=target_type,
        outcome=CheckResultOutcome.NOT_APPLICABLE,
        confidence=CheckResultConfidence.HIGH,
        summary="Metadata-only CheckTool skipped because required context is missing.",
        reason=f"{missing_context_field} is required for {request.check_type}.",
        metadata={"missing_context_field": missing_context_field},
    )


def _missing_inventory_result(
    request: CheckToolRequest,
    *,
    target_type: CheckResultTargetType,
    requested_id_key: str,
    requested_id: UUID,
    summary: str,
    reason: str,
) -> CheckToolResult:
    return _result(
        request,
        target_type=target_type,
        outcome=CheckResultOutcome.UNKNOWN,
        confidence=CheckResultConfidence.MEDIUM,
        summary=summary,
        reason=reason,
        metadata={requested_id_key: str(requested_id)},
    )


def _safe_request_metadata(
    metadata: Mapping[str, object],
    *,
    field_name: str,
) -> SafeMetadata:
    return filter_safe_metadata(
        reject_unsafe_metadata_keys(
            metadata,
            error_message=f"CheckToolRequest {field_name} contains unsafe key names.",
        )
    )


def _safe_result_metadata(metadata: Mapping[str, object]) -> SafeMetadata:
    return filter_safe_metadata(
        reject_unsafe_metadata_keys(
            metadata,
            error_message="CheckToolResult metadata contains unsafe key names.",
        )
    )


def _request_reference_metadata(request: CheckToolRequest) -> dict[str, object]:
    metadata: dict[str, object] = {"check_type": request.check_type}
    _add_uuid_metadata(metadata, "request_agent_id", request.agent_id)
    _add_uuid_metadata(metadata, "request_run_id", request.run_id)
    if request.request_id is not None:
        metadata["request_id"] = request.request_id
    _add_uuid_metadata(metadata, "trace_event_id", request.trace_event_id)
    _add_uuid_metadata(metadata, "policy_decision_id", request.policy_decision_id)
    _add_uuid_metadata(metadata, "policy_version_id", request.policy_version_id)
    _add_uuid_metadata(metadata, "policy_rule_id", request.policy_rule_id)
    _add_uuid_metadata(metadata, "policy_check_step_id", request.policy_check_step_id)
    if request.target_type is not None:
        metadata["requested_target_type"] = request.target_type.value
    _add_uuid_metadata(metadata, "requested_target_id", request.target_id)
    _add_uuid_metadata(metadata, "source_id", request.source_id)
    _add_uuid_metadata(metadata, "model_id", request.model_id)
    _add_uuid_metadata(metadata, "capability_id", request.capability_id)
    if request.purpose is not None:
        metadata["purpose"] = request.purpose
    if request.data_classification is not None:
        metadata["data_classification"] = request.data_classification
    return metadata


def _add_uuid_metadata(
    metadata: dict[str, object],
    key: str,
    value: UUID | None,
) -> None:
    if value is not None:
        metadata[key] = str(value)


def _source_id_from_request(request: CheckToolRequest) -> UUID | None:
    if request.source_id is not None:
        return request.source_id
    if request.target_type is CheckResultTargetType.SOURCE:
        return request.target_id
    return None


def _model_id_from_request(request: CheckToolRequest) -> UUID | None:
    if request.model_id is not None:
        return request.model_id
    if request.target_type is CheckResultTargetType.MODEL_ASSET:
        return request.target_id
    return None


def _capability_id_from_request(request: CheckToolRequest) -> UUID | None:
    if request.capability_id is not None:
        return request.capability_id
    if request.target_type is CheckResultTargetType.CAPABILITY:
        return request.target_id
    return None


def _access_grant_target_from_request(
    request: CheckToolRequest,
) -> tuple[AccessGrantTargetType, UUID] | None:
    if request.capability_id is not None:
        return AccessGrantTargetType.CAPABILITY, request.capability_id
    if request.source_id is not None:
        return AccessGrantTargetType.SOURCE, request.source_id
    if request.model_id is not None:
        return AccessGrantTargetType.MODEL_ASSET, request.model_id
    if request.target_id is None:
        return None
    if request.target_type is CheckResultTargetType.CAPABILITY:
        return AccessGrantTargetType.CAPABILITY, request.target_id
    if request.target_type is CheckResultTargetType.SOURCE:
        return AccessGrantTargetType.SOURCE, request.target_id
    if request.target_type is CheckResultTargetType.MODEL_ASSET:
        return AccessGrantTargetType.MODEL_ASSET, request.target_id
    return None


def _data_usage_profile_for_source(
    session: Session,
    source_id: UUID,
) -> DataUsageProfile | None:
    return session.scalar(
        select(DataUsageProfile).where(DataUsageProfile.source_id == source_id)
    )


def _data_usage_profile_metadata(
    profile: DataUsageProfile,
    review_expired: bool,
) -> dict[str, object]:
    return {
        "source_id": str(profile.source_id),
        "data_usage_profile_id": str(profile.id),
        "review_status": profile.review_status.value,
        "review_expired": review_expired,
        "data_classification": profile.data_classification.value,
        "contains_personal_data": profile.contains_personal_data,
        "contains_sensitive_data": profile.contains_sensitive_data,
        "dpia_required": profile.dpia_required,
        "dpia_reference_present": profile.dpia_reference is not None,
    }


def _model_asset_metadata(model_asset: ModelAsset) -> dict[str, object]:
    return {
        "model_id": str(model_asset.id),
        "model_asset_status": model_asset.status.value,
        "model_type": model_asset.model_type.value,
        "model_provider": model_asset.provider.value,
        "model_provider_type": _model_provider_type(model_asset.provider),
        "risk_level": model_asset.risk_level.value,
    }


def _model_provider_type(provider: ModelProvider) -> str:
    if provider is ModelProvider.LOCAL:
        return MODEL_PROVIDER_CLASS_LOCAL
    if provider is ModelProvider.OTHER:
        return MODEL_PROVIDER_CLASS_UNKNOWN
    return MODEL_PROVIDER_CLASS_EXTERNAL


def _is_datetime_expired(value: datetime | None) -> bool:
    if value is None:
        return False
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value <= datetime.now(UTC)
