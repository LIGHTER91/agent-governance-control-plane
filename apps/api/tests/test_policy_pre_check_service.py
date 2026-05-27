from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from agent_governance_api.database import Base
from agent_governance_api.models import (
    AccessGrant,
    AccessGrantStatus,
    AccessGrantSubjectType,
    AccessGrantTargetType,
    AccessGrantType,
    ActorType,
    Capability,
    CapabilityStatus,
    CapabilityType,
    CheckResult,
    CheckResultConfidence,
    CheckResultOutcome,
    CheckResultTargetType,
    CheckTool,
    CheckToolStatus,
    CheckToolType,
    DataSource,
    DataSourceStatus,
    DataSourceType,
    DataUsageClassification,
    DataUsageProfile,
    DataUsageReviewStatus,
    ModelAsset,
    ModelAssetStatus,
    ModelAssetType,
    ModelProvider,
    OwnerType,
    RiskLevel,
)
from agent_governance_api.policy_pre_checks import (
    check_access_grant_status,
    check_capability_status,
    check_data_usage_profile_status,
    check_model_asset_status,
    check_source_status,
    persist_check_result,
    record_metadata_check_error,
)


@pytest.fixture()
def session() -> Iterator[Session]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )
    with session_factory() as db_session:
        yield db_session
    Base.metadata.drop_all(engine)
    engine.dispose()


def test_persist_check_result_creates_metadata_only_result(session: Session) -> None:
    check_tool = create_check_tool(session)
    agent_id = uuid4()
    target_id = uuid4()

    check_result = persist_check_result(
        session,
        check_tool_id=check_tool.id,
        agent_id=agent_id,
        target_type=CheckResultTargetType.DATA_USAGE_PROFILE,
        target_id=target_id,
        outcome=CheckResultOutcome.PASS,
        confidence=CheckResultConfidence.HIGH,
        summary="Data Usage Profile allows requested purpose.",
        reason="Purpose is listed in allowed_purposes.",
        metadata={"purpose": "customer_support_answering"},
    )

    stored = session.scalar(
        select(CheckResult).where(CheckResult.id == check_result.id)
    )
    assert stored is not None
    assert stored.check_tool_id == check_tool.id
    assert stored.check_tool.name == "data_usage_profile_checker"
    assert stored.agent_id == agent_id
    assert stored.target_id == target_id
    assert stored.outcome is CheckResultOutcome.PASS
    assert stored.confidence is CheckResultConfidence.HIGH
    assert stored.metadata_ == {"purpose": "customer_support_answering"}


def test_persist_check_result_does_not_commit_caller_transaction(
    session: Session,
) -> None:
    check_tool = create_check_tool(session)

    persist_check_result(
        session,
        check_tool_id=check_tool.id,
        target_type=CheckResultTargetType.SOURCE,
        outcome=CheckResultOutcome.UNKNOWN,
        summary="Source review status is unknown.",
        metadata={},
    )

    assert session.in_transaction()


def test_persist_check_result_rejects_blank_summary(session: Session) -> None:
    check_tool = create_check_tool(session)

    with pytest.raises(ValueError, match="non-empty"):
        persist_check_result(
            session,
            check_tool_id=check_tool.id,
            target_type=CheckResultTargetType.SOURCE,
            outcome=CheckResultOutcome.UNKNOWN,
            summary=" ",
        )


def test_persist_check_result_rejects_unsafe_metadata(session: Session) -> None:
    check_tool = create_check_tool(session)

    with pytest.raises(ValueError, match="unsafe key"):
        persist_check_result(
            session,
            check_tool_id=check_tool.id,
            target_type=CheckResultTargetType.SOURCE,
            outcome=CheckResultOutcome.UNKNOWN,
            summary="Source review status is unknown.",
            metadata={"raw_payload_ref": "do-not-store"},
        )


def test_persist_check_result_redacts_sensitive_assignments(
    session: Session,
) -> None:
    check_tool = create_check_tool(session)

    check_result = persist_check_result(
        session,
        check_tool_id=check_tool.id,
        target_type=CheckResultTargetType.EXTERNAL,
        outcome=CheckResultOutcome.ERROR,
        summary="Checker unavailable api_key=do-not-store",
        reason="authorization=Bearer do-not-store",
    )

    assert "do-not-store" not in check_result.summary
    assert "do-not-store" not in str(check_result.reason)
    assert "[REDACTED]" in check_result.summary
    assert "[REDACTED]" in str(check_result.reason)


def test_check_access_grant_status_passes_for_active_non_expired_grant(
    session: Session,
) -> None:
    check_tool = create_check_tool(
        session,
        name="access_grant_checker",
        tool_type=CheckToolType.ACCESS_GRANT_CHECK,
    )
    agent_id = uuid4()
    source_id = uuid4()
    access_grant = create_access_grant(
        session,
        agent_id=agent_id,
        target_type=AccessGrantTargetType.SOURCE,
        target_id=source_id,
        status=AccessGrantStatus.ACTIVE,
        expires_at=datetime.now(UTC) + timedelta(days=1),
    )

    check_result = check_access_grant_status(
        session,
        check_tool_id=check_tool.id,
        agent_id=agent_id,
        target_type=AccessGrantTargetType.SOURCE,
        target_id=source_id,
    )

    assert check_result.target_type is CheckResultTargetType.ACCESS_GRANT
    assert check_result.target_id == access_grant.id
    assert check_result.outcome is CheckResultOutcome.PASS
    assert check_result.confidence is CheckResultConfidence.HIGH
    assert check_result.metadata_ == {
        "check_type": "access_grant_status",
        "requested_target_type": "source",
        "requested_target_id": str(source_id),
        "access_grant_id": str(access_grant.id),
        "access_grant_status": "active",
        "access_grant_expired": False,
    }


@pytest.mark.parametrize(
    ("status", "expires_at"),
    [
        (AccessGrantStatus.REVOKED, None),
        (AccessGrantStatus.SUSPENDED, None),
        (AccessGrantStatus.EXPIRED, None),
        (AccessGrantStatus.ACTIVE, datetime.now(UTC) - timedelta(days=1)),
    ],
)
def test_check_access_grant_status_fails_for_unusable_grant(
    session: Session,
    status: AccessGrantStatus,
    expires_at: datetime | None,
) -> None:
    check_tool = create_check_tool(
        session,
        name=f"access_grant_checker_{status.value}",
        tool_type=CheckToolType.ACCESS_GRANT_CHECK,
    )
    agent_id = uuid4()
    source_id = uuid4()
    access_grant = create_access_grant(
        session,
        agent_id=agent_id,
        target_type=AccessGrantTargetType.SOURCE,
        target_id=source_id,
        status=status,
        expires_at=expires_at,
    )

    check_result = check_access_grant_status(
        session,
        check_tool_id=check_tool.id,
        agent_id=agent_id,
        target_type=AccessGrantTargetType.SOURCE,
        target_id=source_id,
    )

    assert check_result.target_id == access_grant.id
    assert check_result.outcome is CheckResultOutcome.FAIL
    assert check_result.confidence is CheckResultConfidence.HIGH


def test_check_access_grant_status_unknown_when_no_grant_exists(
    session: Session,
) -> None:
    check_tool = create_check_tool(
        session,
        name="missing_access_grant_checker",
        tool_type=CheckToolType.ACCESS_GRANT_CHECK,
    )

    check_result = check_access_grant_status(
        session,
        check_tool_id=check_tool.id,
        agent_id=uuid4(),
        target_type=AccessGrantTargetType.SOURCE,
        target_id=uuid4(),
    )

    assert check_result.target_id is None
    assert check_result.outcome is CheckResultOutcome.UNKNOWN
    assert check_result.confidence is CheckResultConfidence.MEDIUM


def test_check_access_grant_status_not_applicable_without_target_reference(
    session: Session,
) -> None:
    check_tool = create_check_tool(
        session,
        name="not_applicable_access_grant_checker",
        tool_type=CheckToolType.ACCESS_GRANT_CHECK,
    )

    check_result = check_access_grant_status(
        session,
        check_tool_id=check_tool.id,
        agent_id=uuid4(),
        target_type=AccessGrantTargetType.EXTERNAL,
    )

    assert check_result.outcome is CheckResultOutcome.NOT_APPLICABLE
    assert check_result.confidence is CheckResultConfidence.HIGH
    assert "external_ref" not in check_result.metadata_


def test_check_access_grant_status_does_not_copy_sensitive_grant_reason(
    session: Session,
) -> None:
    check_tool = create_check_tool(
        session,
        name="safe_access_grant_checker",
        tool_type=CheckToolType.ACCESS_GRANT_CHECK,
    )
    agent_id = uuid4()
    target_id = uuid4()
    create_access_grant(
        session,
        agent_id=agent_id,
        target_type=AccessGrantTargetType.CAPABILITY,
        target_id=target_id,
        status=AccessGrantStatus.ACTIVE,
        reason="api_key=do-not-store",
    )

    check_result = check_access_grant_status(
        session,
        check_tool_id=check_tool.id,
        agent_id=agent_id,
        target_type=AccessGrantTargetType.CAPABILITY,
        target_id=target_id,
    )

    persisted_text = (
        f"{check_result.summary} {check_result.reason} {check_result.metadata_}"
    )
    assert "do-not-store" not in persisted_text
    assert "api_key" not in persisted_text


def test_check_data_usage_profile_status_passes_for_approved_current_profile(
    session: Session,
) -> None:
    check_tool = create_check_tool(
        session,
        name="data_usage_profile_status_checker",
        tool_type=CheckToolType.DATA_USAGE_PROFILE_CHECK,
    )
    source = create_source(session, status=DataSourceStatus.ACTIVE)
    profile = create_data_usage_profile(
        session,
        source_id=source.id,
        review_status=DataUsageReviewStatus.APPROVED,
        review_expires_at=datetime.now(UTC) + timedelta(days=30),
    )

    check_result = check_data_usage_profile_status(
        session,
        check_tool_id=check_tool.id,
        source_id=source.id,
    )

    assert check_result.target_type is CheckResultTargetType.DATA_USAGE_PROFILE
    assert check_result.target_id == profile.id
    assert check_result.outcome is CheckResultOutcome.PASS
    assert check_result.metadata_["review_status"] == "approved"
    assert check_result.metadata_["review_expired"] is False


@pytest.mark.parametrize(
    ("review_status", "review_expires_at"),
    [
        (DataUsageReviewStatus.REJECTED, None),
        (DataUsageReviewStatus.EXPIRED, None),
        (DataUsageReviewStatus.APPROVED, datetime.now(UTC) - timedelta(days=1)),
    ],
)
def test_check_data_usage_profile_status_fails_for_unusable_profile(
    session: Session,
    review_status: DataUsageReviewStatus,
    review_expires_at: datetime | None,
) -> None:
    check_tool = create_check_tool(
        session,
        name=f"profile_checker_{review_status.value}",
        tool_type=CheckToolType.DATA_USAGE_PROFILE_CHECK,
    )
    source = create_source(session, status=DataSourceStatus.ACTIVE)
    profile = create_data_usage_profile(
        session,
        source_id=source.id,
        review_status=review_status,
        review_expires_at=review_expires_at,
    )

    check_result = check_data_usage_profile_status(
        session,
        check_tool_id=check_tool.id,
        source_id=source.id,
    )

    assert check_result.target_id == profile.id
    assert check_result.outcome is CheckResultOutcome.FAIL
    assert check_result.confidence is CheckResultConfidence.HIGH


def test_check_data_usage_profile_status_unknown_when_missing_or_pending(
    session: Session,
) -> None:
    check_tool = create_check_tool(
        session,
        name="unknown_profile_checker",
        tool_type=CheckToolType.DATA_USAGE_PROFILE_CHECK,
    )
    source = create_source(session, status=DataSourceStatus.ACTIVE)
    missing_result = check_data_usage_profile_status(
        session,
        check_tool_id=check_tool.id,
        source_id=source.id,
    )
    create_data_usage_profile(
        session,
        source_id=source.id,
        review_status=DataUsageReviewStatus.NEEDS_REVIEW,
    )

    pending_result = check_data_usage_profile_status(
        session,
        check_tool_id=check_tool.id,
        source_id=source.id,
    )

    assert missing_result.outcome is CheckResultOutcome.UNKNOWN
    assert missing_result.target_id is None
    assert pending_result.outcome is CheckResultOutcome.UNKNOWN
    assert pending_result.target_id is not None


def test_check_data_usage_profile_status_does_not_copy_sensitive_profile_text(
    session: Session,
) -> None:
    check_tool = create_check_tool(
        session,
        name="safe_profile_checker",
        tool_type=CheckToolType.DATA_USAGE_PROFILE_CHECK,
    )
    source = create_source(session, status=DataSourceStatus.ACTIVE)
    create_data_usage_profile(
        session,
        source_id=source.id,
        review_status=DataUsageReviewStatus.APPROVED,
        legal_basis="api_key=do-not-store",
        review_expires_at=datetime.now(UTC) + timedelta(days=30),
    )

    check_result = check_data_usage_profile_status(
        session,
        check_tool_id=check_tool.id,
        source_id=source.id,
    )

    persisted_text = (
        f"{check_result.summary} {check_result.reason} {check_result.metadata_}"
    )
    assert "do-not-store" not in persisted_text
    assert "api_key" not in persisted_text


def test_check_source_status_pass_fail_and_unknown(session: Session) -> None:
    check_tool = create_check_tool(
        session,
        name="source_status_checker",
        tool_type=CheckToolType.SOURCE_STATUS_CHECK,
    )
    active_source = create_source(session, status=DataSourceStatus.ACTIVE)
    disabled_source = create_source(session, status=DataSourceStatus.DISABLED)

    active_result = check_source_status(
        session,
        check_tool_id=check_tool.id,
        source_id=active_source.id,
    )
    disabled_result = check_source_status(
        session,
        check_tool_id=check_tool.id,
        source_id=disabled_source.id,
    )
    missing_result = check_source_status(
        session,
        check_tool_id=check_tool.id,
        source_id=uuid4(),
    )

    assert active_result.outcome is CheckResultOutcome.PASS
    assert disabled_result.outcome is CheckResultOutcome.FAIL
    assert missing_result.outcome is CheckResultOutcome.UNKNOWN


def test_check_capability_status_pass_fail_and_unknown(session: Session) -> None:
    check_tool = create_check_tool(
        session,
        name="capability_status_checker",
        tool_type=CheckToolType.CAPABILITY_STATUS_CHECK,
    )
    active_capability = create_capability(session, status=CapabilityStatus.ACTIVE)
    retired_capability = create_capability(session, status=CapabilityStatus.RETIRED)

    active_result = check_capability_status(
        session,
        check_tool_id=check_tool.id,
        capability_id=active_capability.id,
    )
    retired_result = check_capability_status(
        session,
        check_tool_id=check_tool.id,
        capability_id=retired_capability.id,
    )
    missing_result = check_capability_status(
        session,
        check_tool_id=check_tool.id,
        capability_id=uuid4(),
    )

    assert active_result.outcome is CheckResultOutcome.PASS
    assert retired_result.outcome is CheckResultOutcome.FAIL
    assert missing_result.outcome is CheckResultOutcome.UNKNOWN


def test_check_model_asset_status_pass_fail_and_unknown(session: Session) -> None:
    check_tool = create_check_tool(
        session,
        name="model_asset_status_checker",
        tool_type=CheckToolType.MODEL_STATUS_CHECK,
    )
    active_model = create_model_asset(session, status=ModelAssetStatus.ACTIVE)
    disabled_model = create_model_asset(session, status=ModelAssetStatus.DISABLED)

    active_result = check_model_asset_status(
        session,
        check_tool_id=check_tool.id,
        model_asset_id=active_model.id,
    )
    disabled_result = check_model_asset_status(
        session,
        check_tool_id=check_tool.id,
        model_asset_id=disabled_model.id,
    )
    missing_result = check_model_asset_status(
        session,
        check_tool_id=check_tool.id,
        model_asset_id=uuid4(),
    )

    assert active_result.outcome is CheckResultOutcome.PASS
    assert disabled_result.outcome is CheckResultOutcome.FAIL
    assert missing_result.outcome is CheckResultOutcome.UNKNOWN


def test_record_metadata_check_error_persists_safe_error_result(
    session: Session,
) -> None:
    check_tool = create_check_tool(
        session,
        name="metadata_error_checker",
        tool_type=CheckToolType.METADATA_LOOKUP,
    )

    check_result = record_metadata_check_error(
        session,
        check_tool_id=check_tool.id,
        target_type=CheckResultTargetType.SOURCE,
        summary="Metadata lookup failed api_key=do-not-store",
        reason="authorization=Bearer do-not-store",
        metadata={"operation": "source_status"},
    )

    assert check_result.outcome is CheckResultOutcome.ERROR
    assert check_result.confidence is CheckResultConfidence.UNKNOWN
    assert "do-not-store" not in check_result.summary
    assert "do-not-store" not in str(check_result.reason)
    assert check_result.metadata_ == {
        "check_type": "metadata_check_error",
        "operation": "source_status",
    }


def create_check_tool(
    session: Session,
    *,
    name: str = "data_usage_profile_checker",
    tool_type: CheckToolType = CheckToolType.DATA_USAGE_PROFILE_CHECK,
) -> CheckTool:
    check_tool = CheckTool(
        id=uuid4(),
        name=name,
        description="Checks declared Source usage metadata.",
        tool_type=tool_type,
        status=CheckToolStatus.ACTIVE,
        owner_type=OwnerType.TEAM,
        owner_id="team:governance",
        owner_name="Governance",
        metadata_={"source": "internal_metadata"},
    )
    session.add(check_tool)
    session.flush()
    assert isinstance(check_tool.id, UUID)
    return check_tool


def create_access_grant(
    session: Session,
    *,
    agent_id: UUID,
    target_type: AccessGrantTargetType,
    target_id: UUID,
    status: AccessGrantStatus,
    expires_at: datetime | None = None,
    reason: str = "Governance review approved.",
) -> AccessGrant:
    access_grant = AccessGrant(
        id=uuid4(),
        name="Test access grant",
        grant_type=_grant_type_for_target(target_type),
        subject_type=AccessGrantSubjectType.AGENT,
        subject_id=agent_id,
        target_type=target_type,
        target_id=target_id,
        status=status,
        granted_by_actor_type=ActorType.USER,
        granted_by_actor_id="user:governance",
        reason=reason,
        expires_at=expires_at,
        risk_level=RiskLevel.MEDIUM,
        metadata_={"ticket": "GOV-123"},
    )
    session.add(access_grant)
    session.flush()
    return access_grant


def create_source(session: Session, *, status: DataSourceStatus) -> DataSource:
    source = DataSource(
        id=uuid4(),
        name=f"Source {uuid4()}",
        description="Governed source.",
        source_type=DataSourceType.KNOWLEDGE_BASE,
        external_ref="source:test",
        owner_type=OwnerType.TEAM,
        owner_id="team:data",
        owner_name="Data Team",
        status=status,
        risk_level=RiskLevel.MEDIUM,
        metadata_={"domain": "support"},
    )
    session.add(source)
    session.flush()
    return source


def create_data_usage_profile(
    session: Session,
    *,
    source_id: UUID,
    review_status: DataUsageReviewStatus,
    review_expires_at: datetime | None = None,
    legal_basis: str | None = None,
) -> DataUsageProfile:
    profile = DataUsageProfile(
        id=uuid4(),
        source_id=source_id,
        data_classification=DataUsageClassification.CONFIDENTIAL,
        contains_personal_data=True,
        contains_sensitive_data=False,
        data_categories=["customer_data"],
        legal_basis=legal_basis,
        allowed_purposes=["support"],
        prohibited_purposes=["training"],
        allowed_processing=["rag"],
        prohibited_processing=["training"],
        review_status=review_status,
        review_expires_at=review_expires_at,
        dpia_required=True,
        dpia_reference="dpia:DPIA-123",
        metadata_={"catalog_ref": "catalog:source"},
    )
    session.add(profile)
    session.flush()
    return profile


def create_capability(
    session: Session,
    *,
    status: CapabilityStatus,
) -> Capability:
    capability = Capability(
        id=uuid4(),
        name=f"Capability {uuid4()}",
        description="Governed capability.",
        capability_type=CapabilityType.TOOL,
        external_ref="tool:test",
        status=status,
        risk_level=RiskLevel.MEDIUM,
        metadata_={"domain": "support"},
    )
    session.add(capability)
    session.flush()
    return capability


def create_model_asset(
    session: Session,
    *,
    status: ModelAssetStatus,
) -> ModelAsset:
    model_asset = ModelAsset(
        id=uuid4(),
        name=f"Model {uuid4()}",
        description="Governed model.",
        model_type=ModelAssetType.LLM,
        provider=ModelProvider.OPENAI,
        model_ref="model:test",
        owner_type=OwnerType.TEAM,
        owner_id="team:model",
        owner_name="Model Team",
        status=status,
        risk_level=RiskLevel.MEDIUM,
        metadata_={"domain": "support"},
    )
    session.add(model_asset)
    session.flush()
    return model_asset


def _grant_type_for_target(target_type: AccessGrantTargetType) -> AccessGrantType:
    if target_type is AccessGrantTargetType.CAPABILITY:
        return AccessGrantType.CAPABILITY
    if target_type is AccessGrantTargetType.SOURCE:
        return AccessGrantType.SOURCE
    if target_type is AccessGrantTargetType.MODEL_ASSET:
        return AccessGrantType.MODEL
    return AccessGrantType.OTHER
