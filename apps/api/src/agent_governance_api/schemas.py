from datetime import datetime
from typing import Any, Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from agent_governance_api.metadata_safety import (
    SafeMetadata,
    filter_safe_metadata,
    reject_unsafe_metadata_keys,
)
from agent_governance_api.models import (
    AccessGrantStatus,
    AccessGrantSubjectType,
    AccessGrantTargetType,
    AccessGrantType,
    ActorType,
    AgentStatus,
    CapabilityStatus,
    CapabilityType,
    CheckResultConfidence,
    CheckResultOutcome,
    CheckResultTargetType,
    CheckToolStatus,
    CheckToolType,
    DataSourceStatus,
    DataSourceType,
    DataUsageClassification,
    DataUsageReviewStatus,
    Environment,
    HumanApprovalStatus,
    ModelAssetStatus,
    ModelAssetType,
    ModelProvider,
    OwnerType,
    PolicyCheckStepCheckType,
    PolicyCheckStepEvidenceRetention,
    PolicyCheckStepFailureBehavior,
    PolicyCheckStepStatus,
    PolicyCheckStepTargetSelector,
    PolicyDecisionValue,
    PolicyStatus,
    PolicyVersionReviewRequestStatus,
    PolicyVersionStatus,
    RiskLevel,
    ServiceActorApiKeyStatus,
    ServiceActorStatus,
)
from agent_governance_api.policy_rule_adapter import validate_policy_rule_condition


class AgentBase(BaseModel):
    name: str
    description: str | None = None
    owner_type: OwnerType
    owner_id: str
    owner_name: str
    owner_contact_email: str | None = None
    environment: Environment
    status: AgentStatus
    risk_level: RiskLevel
    framework: str | None = None


class AgentCreate(AgentBase):
    pass


class AgentUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    description: str | None = None
    owner_type: OwnerType | None = None
    owner_id: str | None = None
    owner_name: str | None = None
    owner_contact_email: str | None = None
    environment: Environment | None = None
    status: AgentStatus | None = None
    risk_level: RiskLevel | None = None
    framework: str | None = None

    @model_validator(mode="before")
    @classmethod
    def reject_null_for_required_fields(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        nullable_fields = {"description", "owner_contact_email", "framework"}
        null_required_fields = sorted(
            field
            for field, value in data.items()
            if value is None and field not in nullable_fields
        )
        if null_required_fields:
            joined_fields = ", ".join(null_required_fields)
            raise ValueError(f"Required fields cannot be null: {joined_fields}")

        return data


class AgentRead(AgentBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime


class CapabilityBase(BaseModel):
    name: str
    description: str | None = None
    capability_type: CapabilityType
    external_ref: str | None = None
    status: CapabilityStatus
    risk_level: RiskLevel
    metadata: SafeMetadata = Field(default_factory=dict)

    @field_validator("metadata")
    @classmethod
    def reject_unsafe_metadata(cls, value: SafeMetadata) -> SafeMetadata:
        return reject_unsafe_metadata_keys(value)


class CapabilityCreate(CapabilityBase):
    pass


class CapabilityUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    description: str | None = None
    capability_type: CapabilityType | None = None
    external_ref: str | None = None
    status: CapabilityStatus | None = None
    risk_level: RiskLevel | None = None
    metadata: SafeMetadata | None = None

    @field_validator("metadata")
    @classmethod
    def reject_unsafe_metadata(cls, value: SafeMetadata | None) -> SafeMetadata | None:
        if value is None:
            return None
        return reject_unsafe_metadata_keys(value)

    @model_validator(mode="before")
    @classmethod
    def reject_null_for_required_fields(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        nullable_fields = {"description", "external_ref"}
        null_required_fields = sorted(
            field
            for field, value in data.items()
            if value is None and field not in nullable_fields
        )
        if null_required_fields:
            joined_fields = ", ".join(null_required_fields)
            raise ValueError(f"Required fields cannot be null: {joined_fields}")

        return data


class CapabilityRead(CapabilityBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    metadata: SafeMetadata = Field(default_factory=dict, validation_alias="metadata_")
    created_at: datetime
    updated_at: datetime


class DataSourceBase(BaseModel):
    name: str
    description: str | None = None
    source_type: DataSourceType
    external_ref: str | None = None
    owner_type: OwnerType
    owner_id: str
    owner_name: str
    owner_contact_email: str | None = None
    status: DataSourceStatus
    risk_level: RiskLevel
    metadata: SafeMetadata = Field(default_factory=dict)

    @field_validator("metadata")
    @classmethod
    def reject_unsafe_metadata(cls, value: SafeMetadata) -> SafeMetadata:
        return reject_unsafe_metadata_keys(value)


class DataSourceCreate(DataSourceBase):
    pass


class DataSourceUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    description: str | None = None
    source_type: DataSourceType | None = None
    external_ref: str | None = None
    owner_type: OwnerType | None = None
    owner_id: str | None = None
    owner_name: str | None = None
    owner_contact_email: str | None = None
    status: DataSourceStatus | None = None
    risk_level: RiskLevel | None = None
    metadata: SafeMetadata | None = None

    @field_validator("metadata")
    @classmethod
    def reject_unsafe_metadata(cls, value: SafeMetadata | None) -> SafeMetadata | None:
        if value is None:
            return None
        return reject_unsafe_metadata_keys(value)

    @model_validator(mode="before")
    @classmethod
    def reject_null_for_required_fields(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        nullable_fields = {"description", "external_ref", "owner_contact_email"}
        null_required_fields = sorted(
            field
            for field, value in data.items()
            if value is None and field not in nullable_fields
        )
        if null_required_fields:
            joined_fields = ", ".join(null_required_fields)
            raise ValueError(f"Required fields cannot be null: {joined_fields}")

        return data


class DataSourceRead(DataSourceBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    metadata: SafeMetadata = Field(default_factory=dict, validation_alias="metadata_")
    created_at: datetime
    updated_at: datetime


class DataUsageProfileBase(BaseModel):
    data_classification: DataUsageClassification
    contains_personal_data: bool = False
    contains_sensitive_data: bool = False
    data_categories: list[str] = Field(default_factory=list)
    legal_basis: str | None = None
    allowed_purposes: list[str] = Field(default_factory=list)
    prohibited_purposes: list[str] = Field(default_factory=list)
    allowed_processing: list[str] = Field(default_factory=list)
    prohibited_processing: list[str] = Field(default_factory=list)
    residency: str | None = None
    retention_policy: str | None = None
    data_owner: str | None = None
    review_status: DataUsageReviewStatus
    reviewed_by_actor_type: ActorType | None = None
    reviewed_by_actor_id: str | None = None
    reviewed_at: datetime | None = None
    review_expires_at: datetime | None = None
    dpia_required: bool = False
    dpia_reference: str | None = None
    metadata: SafeMetadata = Field(default_factory=dict)

    @field_validator(
        "data_categories",
        "allowed_purposes",
        "prohibited_purposes",
        "allowed_processing",
        "prohibited_processing",
    )
    @classmethod
    def validate_string_list(cls, value: list[str]) -> list[str]:
        return _normalize_string_list(value)

    @field_validator("metadata")
    @classmethod
    def reject_unsafe_metadata(cls, value: SafeMetadata) -> SafeMetadata:
        return reject_unsafe_metadata_keys(value)


class DataUsageProfileCreate(DataUsageProfileBase):
    pass


class DataUsageProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data_classification: DataUsageClassification | None = None
    contains_personal_data: bool | None = None
    contains_sensitive_data: bool | None = None
    data_categories: list[str] | None = None
    legal_basis: str | None = None
    allowed_purposes: list[str] | None = None
    prohibited_purposes: list[str] | None = None
    allowed_processing: list[str] | None = None
    prohibited_processing: list[str] | None = None
    residency: str | None = None
    retention_policy: str | None = None
    data_owner: str | None = None
    review_status: DataUsageReviewStatus | None = None
    reviewed_by_actor_type: ActorType | None = None
    reviewed_by_actor_id: str | None = None
    reviewed_at: datetime | None = None
    review_expires_at: datetime | None = None
    dpia_required: bool | None = None
    dpia_reference: str | None = None
    metadata: SafeMetadata | None = None

    @field_validator(
        "data_categories",
        "allowed_purposes",
        "prohibited_purposes",
        "allowed_processing",
        "prohibited_processing",
    )
    @classmethod
    def validate_string_list(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        return _normalize_string_list(value)

    @field_validator("metadata")
    @classmethod
    def reject_unsafe_metadata(cls, value: SafeMetadata | None) -> SafeMetadata | None:
        if value is None:
            return None
        return reject_unsafe_metadata_keys(value)

    @model_validator(mode="before")
    @classmethod
    def reject_null_for_required_fields(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        nullable_fields = {
            "legal_basis",
            "residency",
            "retention_policy",
            "data_owner",
            "reviewed_by_actor_type",
            "reviewed_by_actor_id",
            "reviewed_at",
            "review_expires_at",
            "dpia_reference",
        }
        null_required_fields = sorted(
            field
            for field, value in data.items()
            if value is None and field not in nullable_fields
        )
        if null_required_fields:
            joined_fields = ", ".join(null_required_fields)
            raise ValueError(f"Required fields cannot be null: {joined_fields}")

        return data


class DataUsageProfileRead(DataUsageProfileBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source_id: UUID
    metadata: SafeMetadata = Field(default_factory=dict, validation_alias="metadata_")
    created_at: datetime
    updated_at: datetime


class ModelAssetBase(BaseModel):
    name: str
    description: str | None = None
    model_type: ModelAssetType
    provider: ModelProvider
    model_ref: str | None = None
    version: str | None = None
    owner_type: OwnerType
    owner_id: str
    owner_name: str
    owner_contact_email: str | None = None
    status: ModelAssetStatus
    risk_level: RiskLevel
    metadata: SafeMetadata = Field(default_factory=dict)

    @field_validator("metadata")
    @classmethod
    def reject_unsafe_metadata(cls, value: SafeMetadata) -> SafeMetadata:
        return reject_unsafe_metadata_keys(value)


class ModelAssetCreate(ModelAssetBase):
    pass


class ModelAssetUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    description: str | None = None
    model_type: ModelAssetType | None = None
    provider: ModelProvider | None = None
    model_ref: str | None = None
    version: str | None = None
    owner_type: OwnerType | None = None
    owner_id: str | None = None
    owner_name: str | None = None
    owner_contact_email: str | None = None
    status: ModelAssetStatus | None = None
    risk_level: RiskLevel | None = None
    metadata: SafeMetadata | None = None

    @field_validator("metadata")
    @classmethod
    def reject_unsafe_metadata(cls, value: SafeMetadata | None) -> SafeMetadata | None:
        if value is None:
            return None
        return reject_unsafe_metadata_keys(value)

    @model_validator(mode="before")
    @classmethod
    def reject_null_for_required_fields(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        nullable_fields = {
            "description",
            "model_ref",
            "version",
            "owner_contact_email",
        }
        null_required_fields = sorted(
            field
            for field, value in data.items()
            if value is None and field not in nullable_fields
        )
        if null_required_fields:
            joined_fields = ", ".join(null_required_fields)
            raise ValueError(f"Required fields cannot be null: {joined_fields}")

        return data


class ModelAssetRead(ModelAssetBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    metadata: SafeMetadata = Field(default_factory=dict, validation_alias="metadata_")
    created_at: datetime
    updated_at: datetime


class AccessGrantBase(BaseModel):
    name: str
    description: str | None = None
    grant_type: AccessGrantType
    subject_type: AccessGrantSubjectType
    subject_id: UUID
    target_type: AccessGrantTargetType
    target_id: UUID | None = None
    external_ref: str | None = None
    status: AccessGrantStatus
    reason: str | None = None
    expires_at: datetime | None = None
    risk_level: RiskLevel
    metadata: SafeMetadata = Field(default_factory=dict)

    @field_validator("metadata")
    @classmethod
    def reject_unsafe_metadata(cls, value: SafeMetadata) -> SafeMetadata:
        return reject_unsafe_metadata_keys(value)


class AccessGrantCreate(AccessGrantBase):
    @model_validator(mode="after")
    def validate_target_reference(self) -> Self:
        return _validate_access_grant_target_reference(self)


class AccessGrantUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    description: str | None = None
    grant_type: AccessGrantType | None = None
    subject_type: AccessGrantSubjectType | None = None
    subject_id: UUID | None = None
    target_type: AccessGrantTargetType | None = None
    target_id: UUID | None = None
    external_ref: str | None = None
    status: AccessGrantStatus | None = None
    reason: str | None = None
    expires_at: datetime | None = None
    risk_level: RiskLevel | None = None
    metadata: SafeMetadata | None = None

    @field_validator("metadata")
    @classmethod
    def reject_unsafe_metadata(cls, value: SafeMetadata | None) -> SafeMetadata | None:
        if value is None:
            return None
        return reject_unsafe_metadata_keys(value)

    @model_validator(mode="before")
    @classmethod
    def reject_null_for_required_fields(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        nullable_fields = {
            "description",
            "target_id",
            "external_ref",
            "reason",
            "expires_at",
        }
        null_required_fields = sorted(
            field
            for field, value in data.items()
            if value is None and field not in nullable_fields
        )
        if null_required_fields:
            joined_fields = ", ".join(null_required_fields)
            raise ValueError(f"Required fields cannot be null: {joined_fields}")

        return data


class AccessGrantTransitionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    transition_note: str | None = None

    @field_validator("transition_note")
    @classmethod
    def reject_blank_transition_note(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("AccessGrant transition_note must be non-empty when set.")
        return value


class AccessGrantRead(AccessGrantBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    granted_by_actor_type: ActorType
    granted_by_actor_id: str
    metadata: SafeMetadata = Field(default_factory=dict, validation_alias="metadata_")
    created_at: datetime
    updated_at: datetime


class CheckToolCreate(BaseModel):
    name: str
    description: str | None = None
    tool_type: CheckToolType
    status: CheckToolStatus
    owner_type: OwnerType
    owner_id: str
    owner_name: str
    metadata: SafeMetadata = Field(default_factory=dict)

    @field_validator("name")
    @classmethod
    def reject_blank_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("CheckTool name must be non-empty.")
        return value

    @field_validator("metadata")
    @classmethod
    def reject_unsafe_metadata(cls, value: SafeMetadata) -> SafeMetadata:
        return reject_unsafe_metadata_keys(value)


class CheckToolRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None = None
    tool_type: CheckToolType
    status: CheckToolStatus
    owner_type: OwnerType
    owner_id: str
    owner_name: str
    metadata: SafeMetadata = Field(default_factory=dict, validation_alias="metadata_")
    created_at: datetime
    updated_at: datetime

    @field_validator("metadata", mode="before")
    @classmethod
    def filter_metadata(cls, value: object) -> SafeMetadata:
        if isinstance(value, dict):
            return filter_safe_metadata(value)
        return {}


class CheckResultCreate(BaseModel):
    check_tool_id: UUID
    agent_id: UUID | None = None
    run_id: UUID | None = None
    trace_event_id: UUID | None = None
    policy_decision_id: UUID | None = None
    target_type: CheckResultTargetType
    target_id: UUID | None = None
    outcome: CheckResultOutcome
    confidence: CheckResultConfidence | None = None
    summary: str
    reason: str | None = None
    metadata: SafeMetadata = Field(default_factory=dict)

    @field_validator("summary")
    @classmethod
    def reject_blank_summary(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("CheckResult summary must be non-empty.")
        return value

    @field_validator("metadata")
    @classmethod
    def reject_unsafe_metadata(cls, value: SafeMetadata) -> SafeMetadata:
        return reject_unsafe_metadata_keys(value)


class CheckResultRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    check_tool_id: UUID
    agent_id: UUID | None = None
    run_id: UUID | None = None
    trace_event_id: UUID | None = None
    policy_decision_id: UUID | None = None
    target_type: CheckResultTargetType
    target_id: UUID | None = None
    outcome: CheckResultOutcome
    confidence: CheckResultConfidence | None = None
    summary: str
    reason: str | None = None
    metadata: SafeMetadata = Field(default_factory=dict, validation_alias="metadata_")
    created_at: datetime

    @field_validator("metadata", mode="before")
    @classmethod
    def filter_metadata(cls, value: object) -> SafeMetadata:
        if isinstance(value, dict):
            return filter_safe_metadata(value)
        return {}


class AgentGovernanceProfileOwnerRead(BaseModel):
    owner_type: OwnerType
    owner_id: str
    owner_name: str
    owner_contact_email: str | None = None


class AgentGovernanceProfileTargetReferenceRead(BaseModel):
    target_type: AccessGrantTargetType
    id: UUID
    name: str
    status: str
    risk_level: RiskLevel
    external_ref: str | None = None
    inventory_type: str | None = None
    provider: str | None = None
    version: str | None = None


class AgentGovernanceProfileAccessGrantRead(BaseModel):
    id: UUID
    name: str
    description: str | None = None
    grant_type: AccessGrantType
    subject_type: AccessGrantSubjectType
    subject_id: UUID
    target_type: AccessGrantTargetType
    target_id: UUID | None = None
    external_ref: str | None = None
    status: AccessGrantStatus
    granted_by_actor_type: ActorType
    granted_by_actor_id: str
    reason: str | None = None
    expires_at: datetime | None = None
    risk_level: RiskLevel
    metadata: SafeMetadata = Field(default_factory=dict)
    target: AgentGovernanceProfileTargetReferenceRead | None = None
    created_at: datetime
    updated_at: datetime


class AgentGovernanceProfileRecentActivityRead(BaseModel):
    limit: int
    items: list["AgentActivityItemRead"]


class AgentGovernanceProfileHumanApprovalSummaryRead(BaseModel):
    total_count: int
    by_status: dict[str, int] = Field(default_factory=dict)
    recent: list["EvidenceHumanApprovalRead"]


class AgentGovernanceProfilePolicySummaryRead(BaseModel):
    policy_decision_count: int
    referenced_policy_ids: list[UUID] = Field(default_factory=list)
    referenced_rule_ids: list[UUID] = Field(default_factory=list)


class AgentGovernanceProfileEvidenceBundleHintRead(BaseModel):
    available: bool
    export_path: str
    export_format: Literal["json"] = "json"
    access: Literal["allowed", "restricted"]
    contains_full_evidence: bool = False


class AgentGovernanceProfileRead(BaseModel):
    agent: AgentRead
    owner: AgentGovernanceProfileOwnerRead
    environment: Environment
    status: AgentStatus
    risk_level: RiskLevel
    recent_activity: AgentGovernanceProfileRecentActivityRead
    human_approvals: AgentGovernanceProfileHumanApprovalSummaryRead
    access_grants: list[AgentGovernanceProfileAccessGrantRead]
    policy_summary: AgentGovernanceProfilePolicySummaryRead
    evidence_bundle: AgentGovernanceProfileEvidenceBundleHintRead


EvidenceMetadataValue = str | int | float | bool | None
EvidenceMetadata = dict[str, EvidenceMetadataValue]
AgentActivitySeverity = Literal["info", "warning", "error"]


POLICY_CHECK_STEP_TARGET_SELECTORS = {
    PolicyCheckStepCheckType.ACCESS_GRANT_STATUS: {
        PolicyCheckStepTargetSelector.ACCESS_GRANTS,
    },
    PolicyCheckStepCheckType.DATA_USAGE_PROFILE_STATUS: {
        PolicyCheckStepTargetSelector.SOURCE_IDS,
    },
    PolicyCheckStepCheckType.SOURCE_STATUS: {
        PolicyCheckStepTargetSelector.SOURCE_IDS,
    },
    PolicyCheckStepCheckType.CAPABILITY_STATUS: {
        PolicyCheckStepTargetSelector.CAPABILITY_ID,
    },
    PolicyCheckStepCheckType.MODEL_ASSET_STATUS: {
        PolicyCheckStepTargetSelector.MODEL_ID,
    },
}


def validate_policy_check_step_target_selector(
    check_type: PolicyCheckStepCheckType,
    target_selector: PolicyCheckStepTargetSelector,
) -> None:
    supported_selectors = POLICY_CHECK_STEP_TARGET_SELECTORS[check_type]
    if target_selector not in supported_selectors:
        supported = ", ".join(
            sorted(selector.value for selector in supported_selectors)
        )
        raise ValueError(
            f"target_selector {target_selector.value!r} is not supported for "
            f"check_type {check_type.value!r}. Supported selectors: {supported}."
        )


def _validate_access_grant_target_reference(
    access_grant: AccessGrantCreate,
) -> AccessGrantCreate:
    inventory_target_types = {
        AccessGrantTargetType.CAPABILITY,
        AccessGrantTargetType.SOURCE,
        AccessGrantTargetType.MODEL_ASSET,
    }
    if (
        access_grant.target_type in inventory_target_types
        and access_grant.target_id is None
    ):
        raise ValueError("target_id is required for inventory access grant targets.")
    if access_grant.target_type is AccessGrantTargetType.EXTERNAL and not (
        access_grant.external_ref and access_grant.external_ref.strip()
    ):
        raise ValueError("external_ref is required for external access grant targets.")
    return access_grant


def _normalize_string_list(values: list[str]) -> list[str]:
    normalized_values: list[str] = []
    for raw_value in values:
        if not isinstance(raw_value, str) or not raw_value.strip():
            raise ValueError("List values must be non-empty strings.")
        normalized_values.append(raw_value.strip())

    return list(dict.fromkeys(normalized_values))


class EvidenceAuditLogRead(BaseModel):
    id: UUID
    event_type: str
    actor_type: str
    actor_id: str
    entity_type: str
    entity_id: str
    summary: str
    metadata: EvidenceMetadata
    created_at: datetime


class EvidenceAgentRunRead(BaseModel):
    id: UUID
    agent_id: UUID
    run_id: UUID
    correlation_id: str
    environment: Environment
    status: str
    started_at: datetime
    ended_at: datetime | None = None
    summary: str | None = None
    metadata: EvidenceMetadata
    created_at: datetime


class EvidenceTraceEventRead(BaseModel):
    id: UUID
    agent_id: UUID
    run_id: UUID
    external_event_id: str
    correlation_id: str
    event_type: str
    timestamp: datetime
    summary: str
    metadata: EvidenceMetadata
    created_at: datetime


class EvidencePolicyReferenceRead(BaseModel):
    id: UUID
    name: str
    status: PolicyStatus


class EvidencePolicyRuleReferenceRead(BaseModel):
    id: UUID
    policy_id: UUID
    name: str


class EvidencePolicyVersionReferenceRead(BaseModel):
    policy_version_id: UUID
    policy_id: UUID
    version_number: int
    status: PolicyVersionStatus
    activated_at: datetime | None = None
    change_summary: str | None = None


class EvidencePolicyDecisionRead(BaseModel):
    id: UUID
    agent_id: UUID | None = None
    policy_id: UUID | None = None
    policy_version_id: UUID | None = None
    rule_id: UUID | None = None
    trace_event_id: UUID | None = None
    decision: PolicyDecisionValue
    reason: str
    context_hash: str | None = None
    policy: EvidencePolicyReferenceRead | None = None
    rule: EvidencePolicyRuleReferenceRead | None = None
    policy_version: EvidencePolicyVersionReferenceRead | None = None
    created_at: datetime


class EvidenceHumanApprovalRead(BaseModel):
    id: UUID
    agent_id: UUID
    policy_decision_id: UUID | None = None
    status: HumanApprovalStatus
    requested_by_actor_type: ActorType
    requested_by_actor_id: str
    reviewed_by_actor_type: ActorType | None = None
    reviewed_by_actor_id: str | None = None
    reason: str | None = None
    decision_note: str | None = None
    created_at: datetime
    reviewed_at: datetime | None = None
    expires_at: datetime | None = None


class EvidenceAccessGrantRead(BaseModel):
    id: UUID
    name: str
    description: str | None = None
    grant_type: AccessGrantType
    subject_type: AccessGrantSubjectType
    subject_id: UUID
    target_type: AccessGrantTargetType
    target_id: UUID | None = None
    external_ref: str | None = None
    status: AccessGrantStatus
    granted_by_actor_type: ActorType
    granted_by_actor_id: str
    reason: str | None = None
    expires_at: datetime | None = None
    risk_level: RiskLevel
    metadata: EvidenceMetadata
    created_at: datetime
    updated_at: datetime


class EvidenceCapabilityReferenceRead(BaseModel):
    id: UUID
    name: str
    description: str | None = None
    capability_type: CapabilityType
    external_ref: str | None = None
    status: CapabilityStatus
    risk_level: RiskLevel
    metadata: EvidenceMetadata
    created_at: datetime
    updated_at: datetime


class EvidenceSourceReferenceRead(BaseModel):
    id: UUID
    name: str
    description: str | None = None
    source_type: DataSourceType
    external_ref: str | None = None
    owner_type: OwnerType
    owner_id: str
    owner_name: str
    owner_contact_email: str | None = None
    status: DataSourceStatus
    risk_level: RiskLevel
    metadata: EvidenceMetadata
    created_at: datetime
    updated_at: datetime


class EvidenceDataUsageProfileRead(BaseModel):
    id: UUID
    source_id: UUID
    data_classification: DataUsageClassification
    contains_personal_data: bool
    contains_sensitive_data: bool
    data_categories: list[str]
    legal_basis: str | None = None
    allowed_purposes: list[str]
    prohibited_purposes: list[str]
    allowed_processing: list[str]
    prohibited_processing: list[str]
    residency: str | None = None
    retention_policy: str | None = None
    data_owner: str | None = None
    review_status: DataUsageReviewStatus
    reviewed_by_actor_type: ActorType | None = None
    reviewed_by_actor_id: str | None = None
    reviewed_at: datetime | None = None
    review_expires_at: datetime | None = None
    dpia_required: bool
    dpia_reference: str | None = None
    metadata: EvidenceMetadata
    created_at: datetime
    updated_at: datetime


class EvidenceModelAssetReferenceRead(BaseModel):
    id: UUID
    name: str
    description: str | None = None
    model_type: ModelAssetType
    provider: ModelProvider
    model_ref: str | None = None
    version: str | None = None
    owner_type: OwnerType
    owner_id: str
    owner_name: str
    owner_contact_email: str | None = None
    status: ModelAssetStatus
    risk_level: RiskLevel
    metadata: EvidenceMetadata
    created_at: datetime
    updated_at: datetime


class EvidenceCheckResultRead(BaseModel):
    check_result_id: UUID
    check_tool_id: UUID
    check_tool_name: str | None = None
    check_tool_type: CheckToolType | None = None
    outcome: CheckResultOutcome
    confidence: CheckResultConfidence | None = None
    summary: str
    reason: str | None = None
    target_type: CheckResultTargetType
    target_id: UUID | None = None
    policy_decision_id: UUID | None = None
    policy_version_id: UUID | None = None
    policy_version: EvidencePolicyVersionReferenceRead | None = None
    trace_event_id: UUID | None = None
    run_id: UUID | None = None
    created_at: datetime
    metadata: EvidenceMetadata


class EvidenceBundleRead(BaseModel):
    agent: AgentRead
    audit_logs: list[EvidenceAuditLogRead]
    agent_runs: list[EvidenceAgentRunRead]
    trace_events: list[EvidenceTraceEventRead]
    policy_decisions: list[EvidencePolicyDecisionRead]
    human_approvals: list[EvidenceHumanApprovalRead]
    access_grants: list[EvidenceAccessGrantRead] = Field(default_factory=list)
    capability_references: list[EvidenceCapabilityReferenceRead] = Field(
        default_factory=list
    )
    source_references: list[EvidenceSourceReferenceRead] = Field(default_factory=list)
    data_usage_profiles: list[EvidenceDataUsageProfileRead] = Field(
        default_factory=list
    )
    model_asset_references: list[EvidenceModelAssetReferenceRead] = Field(
        default_factory=list
    )
    check_results: list[EvidenceCheckResultRead] = Field(default_factory=list)


class AgentActivityItemRead(BaseModel):
    id: UUID
    type: str
    timestamp: datetime
    title: str
    summary: str
    severity: AgentActivitySeverity
    trace_event_id: UUID | None = None
    policy_decision_id: UUID | None = None
    human_approval_id: UUID | None = None
    audit_log_id: UUID | None = None
    run_id: UUID | None = None
    related_ids: dict[str, UUID] = Field(default_factory=dict)
    metadata: EvidenceMetadata = Field(default_factory=dict)


class PolicyBase(BaseModel):
    name: str
    description: str | None = None
    status: PolicyStatus

    @field_validator("name")
    @classmethod
    def reject_blank_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Policy name must be non-empty.")
        return value


class PolicyCreate(PolicyBase):
    pass


class PolicyUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    description: str | None = None
    status: PolicyStatus | None = None

    @field_validator("name")
    @classmethod
    def reject_blank_name(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("Policy name must be non-empty.")
        return value

    @model_validator(mode="before")
    @classmethod
    def reject_null_for_required_fields(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        nullable_fields = {"description"}
        null_required_fields = sorted(
            field
            for field, value in data.items()
            if value is None and field not in nullable_fields
        )
        if null_required_fields:
            joined_fields = ", ".join(null_required_fields)
            raise ValueError(f"Required fields cannot be null: {joined_fields}")

        return data


class PolicyRead(PolicyBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime


class PolicyVersionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    change_summary: str

    @field_validator("change_summary")
    @classmethod
    def reject_blank_change_summary(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("PolicyVersion change_summary must be non-empty.")
        return value


class PolicyVersionDraftPolicySnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    description: str | None = None
    status: PolicyStatus

    @field_validator("name")
    @classmethod
    def reject_blank_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("PolicyVersion draft policy name must be non-empty.")
        return value


class PolicyVersionDraftRuleSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID | None = None
    name: str
    description: str | None = None
    condition: str

    @field_validator("name")
    @classmethod
    def reject_blank_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("PolicyVersion draft rule name must be non-empty.")
        return value

    @field_validator("condition")
    @classmethod
    def reject_invalid_condition(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("PolicyVersion draft rule condition must be non-empty.")
        return validate_policy_rule_condition(value)


class PolicyVersionDraftPayload(PolicyVersionCreate):
    policy_snapshot: PolicyVersionDraftPolicySnapshot | None = None
    rule_snapshots: list[PolicyVersionDraftRuleSnapshot] = Field(min_length=1)
    check_step_snapshots: list[dict[str, Any]] = Field(default_factory=list)


class PolicyVersionReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    review_note: str | None = None

    @field_validator("review_note")
    @classmethod
    def reject_blank_review_note(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("PolicyVersion review_note must be non-empty when set.")
        return value


class PolicyVersionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    policy_id: UUID
    source_version_id: UUID | None = None
    version_number: int
    status: PolicyVersionStatus
    change_summary: str
    policy_snapshot: dict[str, Any]
    rule_snapshots: list[dict[str, Any]]
    check_step_snapshots: list[dict[str, Any]]
    created_by_actor_type: ActorType
    created_by_actor_id: str
    review_requested_by_actor_type: ActorType | None = None
    review_requested_by_actor_id: str | None = None
    reviewed_by_actor_type: ActorType | None = None
    reviewed_by_actor_id: str | None = None
    review_note: str | None = None
    created_at: datetime
    updated_at: datetime
    submitted_at: datetime | None = None
    approved_at: datetime | None = None
    rejected_at: datetime | None = None
    activated_at: datetime | None = None
    superseded_at: datetime | None = None
    archived_at: datetime | None = None


class PolicyVersionReviewRequestCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_note: str | None = None

    @field_validator("request_note")
    @classmethod
    def reject_blank_request_note(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("PolicyVersion review request_note must be non-empty.")
        return value


class PolicyVersionReviewDecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision_note: str | None = None

    @field_validator("decision_note")
    @classmethod
    def reject_blank_decision_note(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("PolicyVersion review decision_note must be non-empty.")
        return value


class PolicyVersionReviewAssignmentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    assigned_reviewer_actor_type: ActorType
    assigned_reviewer_actor_id: str
    assigned_reviewer_name: str | None = None
    assignment_note: str | None = None

    @field_validator("assigned_reviewer_actor_id")
    @classmethod
    def reject_blank_assigned_reviewer_actor_id(cls, value: str) -> str:
        if not value.strip():
            raise ValueError(
                "PolicyVersion assigned_reviewer_actor_id must be non-empty."
            )
        return value

    @field_validator("assigned_reviewer_name", "assignment_note")
    @classmethod
    def reject_blank_optional_assignment_text(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("PolicyVersion review assignment text must be non-empty.")
        return value


class PolicyVersionReviewActivationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    replace_active: bool = False


class PolicyVersionReviewRequestRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    policy_version_id: UUID
    policy_id: UUID
    status: PolicyVersionReviewRequestStatus
    requested_by_actor_type: ActorType
    requested_by_actor_id: str
    reviewer_actor_type: ActorType | None = None
    reviewer_actor_id: str | None = None
    assigned_reviewer_actor_type: ActorType | None = None
    assigned_reviewer_actor_id: str | None = None
    assigned_reviewer_name: str | None = None
    assigned_at: datetime | None = None
    assigned_by_actor_type: ActorType | None = None
    assigned_by_actor_id: str | None = None
    request_note: str | None = None
    decision_note: str | None = None
    created_at: datetime
    decided_at: datetime | None = None
    policy_name: str | None = None
    policy_version_number: int | None = None


class PolicyVersionReviewStateRead(BaseModel):
    policy_version_id: UUID
    latest_review_request_id: UUID | None = None
    review_status: Literal[
        "not_submitted",
        "pending",
        "approved",
        "rejected",
        "canceled",
    ]
    requested_at: datetime | None = None
    decided_at: datetime | None = None
    reviewer_actor_id: str | None = None
    can_submit_review: bool
    message: str


class PolicyVersionDiffFieldValue(BaseModel):
    field: str
    value: Any = None


class PolicyVersionDiffChangedField(BaseModel):
    field: str
    baseline: Any = None
    reviewed: Any = None


class PolicyVersionDiffFieldChange(BaseModel):
    changed: bool
    baseline: Any = None
    reviewed: Any = None


class PolicyVersionPolicySnapshotChanges(BaseModel):
    name: PolicyVersionDiffFieldChange
    description: PolicyVersionDiffFieldChange
    status: PolicyVersionDiffFieldChange


class PolicyVersionRuleConditionChanges(BaseModel):
    added_fields: list[PolicyVersionDiffFieldValue] = Field(default_factory=list)
    removed_fields: list[PolicyVersionDiffFieldValue] = Field(default_factory=list)
    changed_fields: list[PolicyVersionDiffChangedField] = Field(default_factory=list)
    unchanged_fields_count: int = 0


class PolicyVersionCheckStepChanges(BaseModel):
    added_count: int = 0
    removed_count: int = 0
    changed_count: int = 0
    unchanged_count: int = 0
    changed_fields: list[str] = Field(default_factory=list)


class PolicyVersionReviewAuditReference(BaseModel):
    id: UUID
    event_type: str
    entity_type: str
    entity_id: str
    summary: str
    created_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)


class PolicyVersionReviewEvidenceRead(BaseModel):
    review_status: PolicyVersionReviewRequestStatus
    review_requested_at: datetime
    decided_at: datetime | None = None
    requested_by_actor_type: ActorType
    requested_by_actor_id: str
    reviewer_actor_type: ActorType | None = None
    reviewer_actor_id: str | None = None
    activation_audit_event: PolicyVersionReviewAuditReference | None = None
    superseded_audit_event: PolicyVersionReviewAuditReference | None = None
    activated_policy_version_id: UUID | None = None
    previous_active_policy_version_id: UUID | None = None


class PolicyVersionReviewDiffRead(BaseModel):
    review_request_id: UUID
    policy_id: UUID
    policy_version_id: UUID
    baseline_policy_version_id: UUID | None = None
    baseline_type: Literal["active_version", "live_fallback", "none"]
    baseline_summary: str
    reviewed_version_status: PolicyVersionStatus
    review_status: PolicyVersionReviewRequestStatus
    can_activate: bool
    activation_requires_replace: bool
    policy_snapshot_changes: PolicyVersionPolicySnapshotChanges
    rule_condition_changes: PolicyVersionRuleConditionChanges
    check_step_changes: PolicyVersionCheckStepChanges
    plain_language_summary: list[str] = Field(default_factory=list)
    runtime_effect_summary: list[str] = Field(default_factory=list)
    evidence: PolicyVersionReviewEvidenceRead


class PolicyRuleBase(BaseModel):
    policy_id: UUID
    name: str
    description: str | None = None
    condition: str

    @field_validator("name")
    @classmethod
    def reject_blank_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("PolicyRule name must be non-empty.")
        return value

    @field_validator("condition")
    @classmethod
    def reject_invalid_condition(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("PolicyRule condition must be non-empty.")
        return validate_policy_rule_condition(value)


class PolicyRuleCreate(PolicyRuleBase):
    pass


class PolicyRuleUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    policy_id: UUID | None = None
    name: str | None = None
    description: str | None = None
    condition: str | None = None

    @field_validator("name")
    @classmethod
    def reject_blank_name(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("PolicyRule name must be non-empty.")
        return value

    @field_validator("condition")
    @classmethod
    def reject_invalid_condition(cls, value: str | None) -> str | None:
        if value is not None:
            if not value.strip():
                raise ValueError("PolicyRule condition must be non-empty.")
            return validate_policy_rule_condition(value)
        return value

    @model_validator(mode="before")
    @classmethod
    def reject_null_for_required_fields(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        nullable_fields = {"description"}
        null_required_fields = sorted(
            field
            for field, value in data.items()
            if value is None and field not in nullable_fields
        )
        if null_required_fields:
            joined_fields = ", ".join(null_required_fields)
            raise ValueError(f"Required fields cannot be null: {joined_fields}")

        return data


class PolicyRuleRead(PolicyRuleBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime


class PolicyCheckStepBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    policy_rule_id: UUID
    check_tool_id: UUID | None = None
    check_type: PolicyCheckStepCheckType
    target_selector: PolicyCheckStepTargetSelector
    required: bool = True
    failure_behavior: PolicyCheckStepFailureBehavior
    min_confidence: float | None = Field(default=None, ge=0, le=1)
    status: PolicyCheckStepStatus
    evidence_retention: PolicyCheckStepEvidenceRetention
    metadata: SafeMetadata = Field(default_factory=dict)

    @field_validator("metadata")
    @classmethod
    def reject_unsafe_metadata(cls, value: SafeMetadata) -> SafeMetadata:
        return reject_unsafe_metadata_keys(value)

    @model_validator(mode="after")
    def validate_target_selector(self) -> Self:
        validate_policy_check_step_target_selector(
            self.check_type,
            self.target_selector,
        )
        return self


class PolicyCheckStepCreate(PolicyCheckStepBase):
    pass


class PolicyCheckStepUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    policy_rule_id: UUID | None = None
    check_tool_id: UUID | None = None
    check_type: PolicyCheckStepCheckType | None = None
    target_selector: PolicyCheckStepTargetSelector | None = None
    required: bool | None = None
    failure_behavior: PolicyCheckStepFailureBehavior | None = None
    min_confidence: float | None = Field(default=None, ge=0, le=1)
    status: PolicyCheckStepStatus | None = None
    evidence_retention: PolicyCheckStepEvidenceRetention | None = None
    metadata: SafeMetadata | None = None

    @field_validator("metadata")
    @classmethod
    def reject_unsafe_metadata(cls, value: SafeMetadata | None) -> SafeMetadata | None:
        if value is None:
            return None
        return reject_unsafe_metadata_keys(value)

    @model_validator(mode="before")
    @classmethod
    def reject_null_for_required_fields(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        nullable_fields = {"check_tool_id", "min_confidence"}
        null_required_fields = sorted(
            field
            for field, value in data.items()
            if value is None and field not in nullable_fields
        )
        if null_required_fields:
            joined_fields = ", ".join(null_required_fields)
            raise ValueError(f"Required fields cannot be null: {joined_fields}")

        return data

    @model_validator(mode="after")
    def validate_target_selector_when_complete(self) -> Self:
        if self.check_type is not None and self.target_selector is not None:
            validate_policy_check_step_target_selector(
                self.check_type,
                self.target_selector,
            )
        return self


class PolicyCheckStepRead(PolicyCheckStepBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    metadata: SafeMetadata = Field(default_factory=dict, validation_alias="metadata_")
    created_at: datetime
    updated_at: datetime

    @field_validator("metadata", mode="before")
    @classmethod
    def filter_metadata(cls, value: object) -> SafeMetadata:
        if isinstance(value, dict):
            return filter_safe_metadata(value)
        return {}


class PolicyDecisionBase(BaseModel):
    agent_id: UUID | None = None
    policy_id: UUID | None = None
    policy_version_id: UUID | None = None
    rule_id: UUID | None = None
    trace_event_id: UUID | None = None
    decision: PolicyDecisionValue
    reason: str
    context_hash: str | None = None


class PolicyDecisionCreate(PolicyDecisionBase):
    pass


class PolicyDecisionRead(PolicyDecisionBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime


class HumanApprovalBase(BaseModel):
    agent_id: UUID
    policy_decision_id: UUID | None = None
    status: HumanApprovalStatus
    requested_by_actor_type: ActorType
    requested_by_actor_id: str
    reviewed_by_actor_type: ActorType | None = None
    reviewed_by_actor_id: str | None = None
    reason: str | None = None
    decision_note: str | None = None
    reviewed_at: datetime | None = None
    expires_at: datetime | None = None


class HumanApprovalCreate(HumanApprovalBase):
    pass


class HumanApprovalRequest(BaseModel):
    agent_id: UUID
    policy_decision_id: UUID | None = None
    reason: str | None = None
    expires_at: datetime | None = None


class HumanApprovalDecisionRequest(BaseModel):
    reason: str | None = None
    decision_note: str | None = None


class HumanApprovalRead(HumanApprovalBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime


class ServiceActorRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    actor_id: str
    display_name: str
    description: str | None = None
    status: ServiceActorStatus
    created_at: datetime
    updated_at: datetime
    disabled_at: datetime | None = None


class ServiceActorApiKeyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    key_id: str
    status: ServiceActorApiKeyStatus
    created_at: datetime
    expires_at: datetime | None = None
    revoked_at: datetime | None = None
    last_used_at: datetime | None = None


class ServiceActorScopeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    service_actor_id: UUID
    scope: str
    created_at: datetime


class ServiceActorScopeRuleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    service_actor_id: UUID
    agent_ids: list[str]
    environments: list[str]
    runtime_modes: list[str]
    tool_names: list[str]
    created_at: datetime
    updated_at: datetime
