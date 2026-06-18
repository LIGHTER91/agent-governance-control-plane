from collections.abc import Iterator
from dataclasses import fields
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from agent_governance_api.check_tools import (
    ACCESS_GRANT_STATUS,
    CAPABILITY_STATUS,
    DATA_USAGE_PROFILE_STATUS,
    MODEL_ASSET_STATUS,
    MODEL_PROVIDER_TYPE,
    SOURCE_CLASSIFICATION,
    SOURCE_STATUS,
    CheckToolExecutionMode,
    CheckToolRequest,
    CheckToolResult,
    MetadataOnlyCheckToolAdapter,
)
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
    CheckResultConfidence,
    CheckResultOutcome,
    CheckResultTargetType,
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


def test_check_tool_request_has_no_raw_content_fields() -> None:
    field_names = {field.name for field in fields(CheckToolRequest)}

    assert "raw_prompt" not in field_names
    assert "prompt" not in field_names
    assert "raw_content" not in field_names
    assert "source_content" not in field_names
    assert "api_key" not in field_names
    assert "token" not in field_names
    assert "external_url" not in field_names


def test_check_tool_request_rejects_unsafe_metadata_keys() -> None:
    with pytest.raises(ValueError, match="unsafe key"):
        CheckToolRequest(
            check_type=SOURCE_STATUS,
            declared_metadata={"raw_prompt": "do-not-store"},
        )


def test_check_tool_result_rejects_unsafe_metadata_keys() -> None:
    with pytest.raises(ValueError, match="unsafe key"):
        CheckToolResult(
            check_type=SOURCE_STATUS,
            target_type=CheckResultTargetType.SOURCE,
            outcome=CheckResultOutcome.UNKNOWN,
            confidence=CheckResultConfidence.MEDIUM,
            summary="Source status unknown.",
            metadata={"authorization_header": "Bearer do-not-store"},
        )


def test_metadata_only_access_grant_status_passes_for_active_grant(
    session: Session,
) -> None:
    adapter = MetadataOnlyCheckToolAdapter()
    agent_id = uuid4()
    source = create_source(session, status=DataSourceStatus.ACTIVE)
    access_grant = create_access_grant(
        session,
        agent_id=agent_id,
        target_type=AccessGrantTargetType.SOURCE,
        target_id=source.id,
        status=AccessGrantStatus.ACTIVE,
        expires_at=datetime.now(UTC) + timedelta(days=1),
    )

    result = adapter.run(
        session,
        CheckToolRequest(
            check_type=ACCESS_GRANT_STATUS,
            agent_id=agent_id,
            source_id=source.id,
            policy_version_id=uuid4(),
        ),
    )

    assert result.target_type is CheckResultTargetType.ACCESS_GRANT
    assert result.target_id == access_grant.id
    assert result.outcome is CheckResultOutcome.PASS
    assert result.confidence is CheckResultConfidence.HIGH
    assert result.metadata["access_grant_status"] == "active"
    assert "policy_version_id" in result.metadata


def test_metadata_only_access_grant_status_unknown_without_grant(
    session: Session,
) -> None:
    adapter = MetadataOnlyCheckToolAdapter()
    result = adapter.run(
        session,
        CheckToolRequest(
            check_type=ACCESS_GRANT_STATUS,
            agent_id=uuid4(),
            source_id=uuid4(),
        ),
    )

    assert result.outcome is CheckResultOutcome.UNKNOWN
    assert result.confidence is CheckResultConfidence.MEDIUM
    assert result.target_id is None


def test_metadata_only_data_usage_profile_status_passes_for_approved_profile(
    session: Session,
) -> None:
    adapter = MetadataOnlyCheckToolAdapter()
    source = create_source(session, status=DataSourceStatus.ACTIVE)
    profile = create_data_usage_profile(
        session,
        source_id=source.id,
        review_status=DataUsageReviewStatus.APPROVED,
        review_expires_at=datetime.now(UTC) + timedelta(days=30),
    )

    result = adapter.run(
        session,
        CheckToolRequest(check_type=DATA_USAGE_PROFILE_STATUS, source_id=source.id),
    )

    assert result.target_type is CheckResultTargetType.DATA_USAGE_PROFILE
    assert result.target_id == profile.id
    assert result.outcome is CheckResultOutcome.PASS
    assert result.metadata["review_status"] == "approved"


def test_metadata_only_source_status_pass_fail_and_unknown(
    session: Session,
) -> None:
    adapter = MetadataOnlyCheckToolAdapter()
    active_source = create_source(session, status=DataSourceStatus.ACTIVE)
    disabled_source = create_source(session, status=DataSourceStatus.DISABLED)

    active_result = adapter.run(
        session,
        CheckToolRequest(check_type=SOURCE_STATUS, source_id=active_source.id),
    )
    disabled_result = adapter.run(
        session,
        CheckToolRequest(check_type=SOURCE_STATUS, source_id=disabled_source.id),
    )
    missing_result = adapter.run(
        session,
        CheckToolRequest(check_type=SOURCE_STATUS, source_id=uuid4()),
    )

    assert active_result.outcome is CheckResultOutcome.PASS
    assert disabled_result.outcome is CheckResultOutcome.FAIL
    assert missing_result.outcome is CheckResultOutcome.UNKNOWN


def test_metadata_only_source_classification_uses_safe_profile_metadata(
    session: Session,
) -> None:
    adapter = MetadataOnlyCheckToolAdapter()
    source = create_source(session, status=DataSourceStatus.ACTIVE)
    create_data_usage_profile(
        session,
        source_id=source.id,
        review_status=DataUsageReviewStatus.APPROVED,
        legal_basis="api_key=do-not-store",
    )

    result = adapter.run(
        session,
        CheckToolRequest(check_type=SOURCE_CLASSIFICATION, source_id=source.id),
    )

    assert result.outcome is CheckResultOutcome.PASS
    assert result.metadata["data_classification"] == "confidential"
    assert result.metadata["contains_personal_data"] is True
    assert "legal_basis" not in result.metadata
    assert "do-not-store" not in str(result.metadata)


def test_metadata_only_model_asset_status_and_provider_type(
    session: Session,
) -> None:
    adapter = MetadataOnlyCheckToolAdapter()
    model_asset = create_model_asset(session, status=ModelAssetStatus.ACTIVE)

    status_result = adapter.run(
        session,
        CheckToolRequest(check_type=MODEL_ASSET_STATUS, model_id=model_asset.id),
    )
    provider_result = adapter.run(
        session,
        CheckToolRequest(check_type=MODEL_PROVIDER_TYPE, model_id=model_asset.id),
    )

    assert status_result.outcome is CheckResultOutcome.PASS
    assert status_result.metadata["model_asset_status"] == "active"
    assert provider_result.outcome is CheckResultOutcome.PASS
    assert provider_result.metadata["model_provider_type"] == "openai"


def test_metadata_only_capability_status_pass_fail_and_unknown(
    session: Session,
) -> None:
    adapter = MetadataOnlyCheckToolAdapter()
    active_capability = create_capability(session, status=CapabilityStatus.ACTIVE)
    retired_capability = create_capability(session, status=CapabilityStatus.RETIRED)

    active_result = adapter.run(
        session,
        CheckToolRequest(
            check_type=CAPABILITY_STATUS,
            capability_id=active_capability.id,
        ),
    )
    retired_result = adapter.run(
        session,
        CheckToolRequest(
            check_type=CAPABILITY_STATUS,
            capability_id=retired_capability.id,
        ),
    )
    missing_result = adapter.run(
        session,
        CheckToolRequest(check_type=CAPABILITY_STATUS, capability_id=uuid4()),
    )

    assert active_result.outcome is CheckResultOutcome.PASS
    assert retired_result.outcome is CheckResultOutcome.FAIL
    assert missing_result.outcome is CheckResultOutcome.UNKNOWN


def test_unknown_metadata_only_check_type_returns_safe_error(
    session: Session,
) -> None:
    adapter = MetadataOnlyCheckToolAdapter()

    result = adapter.run(session, CheckToolRequest(check_type="secret_scanner"))

    assert result.outcome is CheckResultOutcome.ERROR
    assert result.confidence is CheckResultConfidence.UNKNOWN
    assert result.metadata == {
        "check_type": "secret_scanner",
        "error_type": "unsupported_check_type",
        "execution_mode": "metadata_only",
    }


def test_adapter_rejects_non_metadata_only_execution_mode(session: Session) -> None:
    adapter = MetadataOnlyCheckToolAdapter()

    with pytest.raises(Exception, match="metadata_only"):
        adapter.run(
            session,
            CheckToolRequest(
                check_type=SOURCE_STATUS,
                execution_mode=CheckToolExecutionMode.SAMPLE_BASED_EXTERNAL_SCANNER,
            ),
        )


def test_result_to_check_result_payload_contains_only_safe_context() -> None:
    request = CheckToolRequest(
        check_type=SOURCE_STATUS,
        agent_id=uuid4(),
        run_id=uuid4(),
        trace_event_id=uuid4(),
        policy_decision_id=uuid4(),
        policy_version_id=uuid4(),
        policy_rule_id=uuid4(),
        policy_check_step_id=uuid4(),
        request_id="local-request-1",
        source_id=uuid4(),
        purpose="support",
        data_classification="internal",
    )
    result = CheckToolResult(
        check_type=SOURCE_STATUS,
        target_type=CheckResultTargetType.SOURCE,
        target_id=request.source_id,
        outcome=CheckResultOutcome.PASS,
        confidence=CheckResultConfidence.HIGH,
        summary="Source status is active api_key=do-not-store",
        reason="No raw source content was inspected.",
        metadata={"source_status": "active"},
    )

    payload = result.to_check_result_payload(request, check_tool_id=uuid4())

    assert payload["summary"] == "Source status is active api_key=[REDACTED]"
    assert payload["metadata"]["policy_version_id"] == str(request.policy_version_id)
    assert payload["metadata"]["policy_check_step_id"] == str(
        request.policy_check_step_id
    )
    assert "raw_prompt" not in str(payload)
    assert "do-not-store" not in str(payload)


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


def create_access_grant(
    session: Session,
    *,
    agent_id: UUID,
    target_type: AccessGrantTargetType,
    target_id: UUID,
    status: AccessGrantStatus,
    expires_at: datetime | None = None,
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
        reason="Governance review approved.",
        expires_at=expires_at,
        risk_level=RiskLevel.MEDIUM,
        metadata_={"ticket": "GOV-123"},
    )
    session.add(access_grant)
    session.flush()
    return access_grant


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
