from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from agent_governance_api.metadata_safety import SafeMetadata
from agent_governance_api.models import (
    AccessGrant,
    AccessGrantStatus,
    AccessGrantSubjectType,
    AccessGrantTargetType,
    Capability,
    DataSource,
    DataUsageProfile,
    DataUsageReviewStatus,
    ModelAsset,
    ModelProvider,
)
from agent_governance_api.runtime_gateway import RuntimeToolCallDecisionRequest

MISSING_RESOLVED_CONTEXT_VALUE = "missing"
MODEL_PROVIDER_TYPE_EXTERNAL = "external"
MODEL_PROVIDER_TYPE_LOCAL = "local"
MODEL_PROVIDER_TYPE_UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class ResolvedRuntimeInventoryContext:
    policy_context: dict[str, object] = field(default_factory=dict)
    trace_metadata: SafeMetadata = field(default_factory=dict)


def resolve_runtime_inventory_context(
    session: Session,
    *,
    agent_id: UUID,
    payload: RuntimeToolCallDecisionRequest,
) -> ResolvedRuntimeInventoryContext:
    builder = _ResolvedRuntimeInventoryContextBuilder()

    _resolve_capability_context(session, payload, builder)
    _resolve_source_and_data_usage_context(session, payload, builder)
    _resolve_model_context(session, payload, builder)
    _resolve_access_grant_context(
        session,
        agent_id=agent_id,
        payload=payload,
        builder=builder,
    )

    return ResolvedRuntimeInventoryContext(
        policy_context=builder.policy_context,
        trace_metadata=builder.trace_metadata,
    )


@dataclass(slots=True)
class _ResolvedRuntimeInventoryContextBuilder:
    policy_context: dict[str, object] = field(default_factory=dict)
    trace_metadata: SafeMetadata = field(default_factory=dict)

    def add_scalar(self, key: str, value: object) -> None:
        self.policy_context[key] = value
        metadata_value = _safe_metadata_value(value)
        if metadata_value is not None:
            self.trace_metadata[f"resolved_{key}"] = metadata_value

    def add_values(self, key: str, values: Iterable[object]) -> None:
        unique_values = _unique_text_values(values)
        if not unique_values:
            return
        self.policy_context[key] = tuple(unique_values)
        self.trace_metadata[f"resolved_{key}"] = ",".join(unique_values)


def _resolve_capability_context(
    session: Session,
    payload: RuntimeToolCallDecisionRequest,
    builder: _ResolvedRuntimeInventoryContextBuilder,
) -> None:
    if payload.capability_id is None:
        return

    capability = session.get(Capability, payload.capability_id)
    if capability is None:
        builder.add_scalar("capability_status", MISSING_RESOLVED_CONTEXT_VALUE)
        builder.trace_metadata["resolved_missing_capability_id"] = str(
            payload.capability_id
        )
        return

    builder.add_scalar("capability_type", capability.capability_type)
    builder.add_scalar("capability_status", capability.status)


def _resolve_source_and_data_usage_context(
    session: Session,
    payload: RuntimeToolCallDecisionRequest,
    builder: _ResolvedRuntimeInventoryContextBuilder,
) -> None:
    if not payload.source_ids:
        return

    sources = _load_sources_by_id(session, payload.source_ids)
    source_statuses: list[str] = []
    missing_source_ids: list[str] = []

    existing_source_ids: list[UUID] = []
    for source_id in payload.source_ids:
        source = sources.get(source_id)
        if source is None:
            source_statuses.append(MISSING_RESOLVED_CONTEXT_VALUE)
            missing_source_ids.append(str(source_id))
            continue
        source_statuses.append(source.status.value)
        existing_source_ids.append(source_id)

    builder.add_values("source_statuses", source_statuses)
    if missing_source_ids:
        builder.trace_metadata["resolved_missing_source_ids"] = ",".join(
            missing_source_ids
        )

    profiles = _load_data_usage_profiles_by_source_id(session, existing_source_ids)
    _resolve_data_usage_context(
        requested_source_ids=payload.source_ids,
        existing_source_ids=set(existing_source_ids),
        profiles=profiles,
        builder=builder,
    )


def _resolve_data_usage_context(
    *,
    requested_source_ids: list[UUID],
    existing_source_ids: set[UUID],
    profiles: dict[UUID, DataUsageProfile],
    builder: _ResolvedRuntimeInventoryContextBuilder,
) -> None:
    classifications: list[str] = []
    review_statuses: list[str] = []
    allowed_purposes: list[str] = []
    prohibited_purposes: list[str] = []
    missing_profile_source_ids: list[str] = []
    contains_personal_values: list[bool] = []
    contains_sensitive_values: list[bool] = []

    now = datetime.now(UTC)
    for source_id in requested_source_ids:
        if source_id not in existing_source_ids:
            review_statuses.append(MISSING_RESOLVED_CONTEXT_VALUE)
            continue

        profile = profiles.get(source_id)
        if profile is None:
            review_statuses.append(MISSING_RESOLVED_CONTEXT_VALUE)
            missing_profile_source_ids.append(str(source_id))
            continue

        classifications.append(profile.data_classification.value)
        review_statuses.append(_effective_data_usage_review_status(profile, now))
        allowed_purposes.extend(profile.allowed_purposes)
        prohibited_purposes.extend(profile.prohibited_purposes)
        contains_personal_values.append(profile.contains_personal_data)
        contains_sensitive_values.append(profile.contains_sensitive_data)

    builder.add_values("source_data_classifications", classifications)
    builder.add_values("data_usage_review_statuses", review_statuses)
    builder.add_values("data_usage_allowed_purposes", allowed_purposes)
    builder.add_values("data_usage_prohibited_purposes", prohibited_purposes)

    if contains_personal_values:
        builder.add_scalar(
            "source_contains_personal_data",
            any(contains_personal_values),
        )
    if contains_sensitive_values:
        builder.add_scalar(
            "source_contains_sensitive_data",
            any(contains_sensitive_values),
        )
    if missing_profile_source_ids:
        builder.trace_metadata["resolved_missing_data_usage_profile_source_ids"] = (
            ",".join(missing_profile_source_ids)
        )


def _resolve_model_context(
    session: Session,
    payload: RuntimeToolCallDecisionRequest,
    builder: _ResolvedRuntimeInventoryContextBuilder,
) -> None:
    if payload.model_id is None:
        return

    model_asset = session.get(ModelAsset, payload.model_id)
    if model_asset is None:
        builder.add_scalar("model_status", MISSING_RESOLVED_CONTEXT_VALUE)
        builder.trace_metadata["resolved_missing_model_id"] = str(payload.model_id)
        return

    builder.add_scalar("model_type", model_asset.model_type)
    builder.add_scalar("model_provider", model_asset.provider)
    builder.add_scalar(
        "model_provider_type", _model_provider_type(model_asset.provider)
    )
    builder.add_scalar("model_status", model_asset.status)


def _resolve_access_grant_context(
    session: Session,
    *,
    agent_id: UUID,
    payload: RuntimeToolCallDecisionRequest,
    builder: _ResolvedRuntimeInventoryContextBuilder,
) -> None:
    target_refs = _runtime_access_grant_target_refs(payload)
    if not target_refs:
        return

    grants = _load_access_grants_by_target(
        session,
        agent_id=agent_id,
        targets=target_refs,
    )
    now = datetime.now(UTC)
    statuses: list[str] = []
    missing_targets: list[str] = []

    for target_type, target_id in target_refs:
        target_grants = grants.get((target_type, target_id), [])
        if not target_grants:
            statuses.append(MISSING_RESOLVED_CONTEXT_VALUE)
            missing_targets.append(f"{target_type.value}:{target_id}")
            continue
        statuses.extend(
            _effective_access_grant_status(grant, now) for grant in target_grants
        )

    builder.add_values("access_grant_statuses", statuses)
    if missing_targets:
        builder.trace_metadata["resolved_missing_access_grant_targets"] = ",".join(
            missing_targets
        )


def _runtime_access_grant_target_refs(
    payload: RuntimeToolCallDecisionRequest,
) -> list[tuple[AccessGrantTargetType, UUID]]:
    refs: list[tuple[AccessGrantTargetType, UUID]] = []
    if payload.capability_id is not None:
        refs.append((AccessGrantTargetType.CAPABILITY, payload.capability_id))
    refs.extend(
        (AccessGrantTargetType.SOURCE, source_id) for source_id in payload.source_ids
    )
    if payload.model_id is not None:
        refs.append((AccessGrantTargetType.MODEL_ASSET, payload.model_id))
    return refs


def _load_sources_by_id(
    session: Session,
    source_ids: list[UUID],
) -> dict[UUID, DataSource]:
    if not source_ids:
        return {}
    statement = select(DataSource).where(DataSource.id.in_(source_ids))
    return {source.id: source for source in session.scalars(statement).all()}


def _load_data_usage_profiles_by_source_id(
    session: Session,
    source_ids: list[UUID],
) -> dict[UUID, DataUsageProfile]:
    if not source_ids:
        return {}
    statement = select(DataUsageProfile).where(
        DataUsageProfile.source_id.in_(source_ids)
    )
    return {profile.source_id: profile for profile in session.scalars(statement).all()}


def _load_access_grants_by_target(
    session: Session,
    *,
    agent_id: UUID,
    targets: list[tuple[AccessGrantTargetType, UUID]],
) -> dict[tuple[AccessGrantTargetType, UUID], list[AccessGrant]]:
    if not targets:
        return {}

    target_types = {target_type for target_type, _target_id in targets}
    target_ids = {target_id for _target_type, target_id in targets}
    statement = (
        select(AccessGrant)
        .where(AccessGrant.subject_type == AccessGrantSubjectType.AGENT)
        .where(AccessGrant.subject_id == agent_id)
        .where(AccessGrant.target_type.in_(target_types))
        .where(AccessGrant.target_id.in_(target_ids))
        .order_by(AccessGrant.created_at, AccessGrant.id)
    )

    grants_by_target: dict[tuple[AccessGrantTargetType, UUID], list[AccessGrant]] = {}
    for grant in session.scalars(statement).all():
        if grant.target_id is None:
            continue
        key = (grant.target_type, grant.target_id)
        grants_by_target.setdefault(key, []).append(grant)
    return grants_by_target


def _effective_access_grant_status(
    access_grant: AccessGrant,
    now: datetime,
) -> str:
    if access_grant.expires_at is not None and access_grant.expires_at <= now:
        return AccessGrantStatus.EXPIRED.value
    return access_grant.status.value


def _effective_data_usage_review_status(
    profile: DataUsageProfile,
    now: datetime,
) -> str:
    if profile.review_expires_at is not None and profile.review_expires_at <= now:
        return DataUsageReviewStatus.EXPIRED.value
    return profile.review_status.value


def _model_provider_type(provider: ModelProvider) -> str:
    if provider is ModelProvider.LOCAL:
        return MODEL_PROVIDER_TYPE_LOCAL
    if provider is ModelProvider.OTHER:
        return MODEL_PROVIDER_TYPE_UNKNOWN
    return MODEL_PROVIDER_TYPE_EXTERNAL


def _unique_text_values(values: Iterable[object]) -> list[str]:
    unique_values: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = _text_value(value)
        if text is None or text in seen:
            continue
        unique_values.append(text)
        seen.add(text)
    return unique_values


def _safe_metadata_value(value: object) -> str | int | float | bool | None:
    if isinstance(value, bool | int | float):
        return value
    return _text_value(value)


def _text_value(value: object) -> str | None:
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, str):
        return value
    if hasattr(value, "value") and isinstance(value.value, str):
        return value.value
    return None
