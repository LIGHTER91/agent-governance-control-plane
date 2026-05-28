from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    ForeignKeyConstraint,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from agent_governance_api.config import (
    SERVICE_ACTOR_API_KEY_HASH_HEX_LENGTH,
    SERVICE_ACTOR_API_KEY_HASH_PREFIX,
    SERVICE_ACTOR_FINE_GRAINED_WILDCARD,
    SUPPORTED_SERVICE_ACTOR_RUNTIME_MODES,
    SUPPORTED_SERVICE_ACTOR_SCOPE_ENVIRONMENTS,
    SUPPORTED_SERVICE_ACTOR_SCOPES,
)
from agent_governance_api.database import Base
from agent_governance_api.metadata_safety import (
    SafeMetadata,
    reject_unsafe_metadata_keys,
)


def enum_values(enum_class: type[StrEnum]) -> list[str]:
    return [item.value for item in enum_class]


class Environment(StrEnum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class AgentStatus(StrEnum):
    DRAFT = "draft"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    RETIRED = "retired"


class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class CapabilityType(StrEnum):
    TOOL = "tool"
    API = "api"
    INTEGRATION = "integration"
    WORKFLOW_ACTION = "workflow_action"
    OTHER = "other"


class CapabilityStatus(StrEnum):
    ACTIVE = "active"
    DISABLED = "disabled"
    RETIRED = "retired"


class DataSourceType(StrEnum):
    KNOWLEDGE_BASE = "knowledge_base"
    DATABASE = "database"
    DOCUMENT_STORE = "document_store"
    API = "api"
    BUCKET = "bucket"
    FILESYSTEM = "filesystem"
    OTHER = "other"


class DataSourceStatus(StrEnum):
    ACTIVE = "active"
    DISABLED = "disabled"
    RETIRED = "retired"


class DataUsageClassification(StrEnum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


class DataUsageReviewStatus(StrEnum):
    DRAFT = "draft"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    NEEDS_REVIEW = "needs_review"


class ModelAssetType(StrEnum):
    LLM = "llm"
    EMBEDDING = "embedding"
    RERANKER = "reranker"
    CLASSIFIER = "classifier"
    VISION = "vision"
    AUDIO = "audio"
    OTHER = "other"


class ModelProvider(StrEnum):
    OPENAI = "openai"
    MISTRAL = "mistral"
    ANTHROPIC = "anthropic"
    LOCAL = "local"
    AZURE = "azure"
    AWS = "aws"
    GCP = "gcp"
    OTHER = "other"


class ModelAssetStatus(StrEnum):
    ACTIVE = "active"
    DISABLED = "disabled"
    RETIRED = "retired"


class AccessGrantType(StrEnum):
    CAPABILITY = "capability"
    SOURCE = "source"
    MODEL = "model"
    PERMISSION = "permission"
    OTHER = "other"


class AccessGrantSubjectType(StrEnum):
    AGENT = "agent"


class AccessGrantTargetType(StrEnum):
    CAPABILITY = "capability"
    SOURCE = "source"
    MODEL_ASSET = "model_asset"
    EXTERNAL = "external"
    OTHER = "other"


class AccessGrantStatus(StrEnum):
    PENDING_REVIEW = "pending_review"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    REVOKED = "revoked"
    EXPIRED = "expired"


class CheckToolType(StrEnum):
    METADATA_LOOKUP = "metadata_lookup"
    ACCESS_GRANT_CHECK = "access_grant_check"
    DATA_USAGE_PROFILE_CHECK = "data_usage_profile_check"
    SOURCE_STATUS_CHECK = "source_status_check"
    MODEL_STATUS_CHECK = "model_status_check"
    CAPABILITY_STATUS_CHECK = "capability_status_check"


class CheckToolStatus(StrEnum):
    ACTIVE = "active"
    DISABLED = "disabled"
    RETIRED = "retired"


class CheckResultTargetType(StrEnum):
    SOURCE = "source"
    CAPABILITY = "capability"
    MODEL_ASSET = "model_asset"
    ACCESS_GRANT = "access_grant"
    DATA_USAGE_PROFILE = "data_usage_profile"
    EXTERNAL = "external"


class CheckResultOutcome(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    UNKNOWN = "unknown"
    ERROR = "error"
    NOT_APPLICABLE = "not_applicable"


class CheckResultConfidence(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNKNOWN = "unknown"


class PolicyCheckStepCheckType(StrEnum):
    ACCESS_GRANT_STATUS = "access_grant_status"
    DATA_USAGE_PROFILE_STATUS = "data_usage_profile_status"
    SOURCE_STATUS = "source_status"
    CAPABILITY_STATUS = "capability_status"
    MODEL_ASSET_STATUS = "model_asset_status"


class PolicyCheckStepTargetSelector(StrEnum):
    AGENT = "agent"
    SOURCE_IDS = "source_ids"
    MODEL_ID = "model_id"
    CAPABILITY_ID = "capability_id"
    ACCESS_GRANTS = "access_grants"


class PolicyCheckStepFailureBehavior(StrEnum):
    RECORD_ONLY = "record_only"
    REQUIRE_HUMAN_REVIEW = "require_human_review"
    FAIL_CLOSED = "fail_closed"
    IGNORE_IF_UNAVAILABLE = "ignore_if_unavailable"


class PolicyCheckStepStatus(StrEnum):
    ACTIVE = "active"
    DISABLED = "disabled"
    RETIRED = "retired"


class PolicyCheckStepEvidenceRetention(StrEnum):
    DECISION_ONLY = "decision_only"
    EVIDENCE_BUNDLE = "evidence_bundle"
    NONE = "none"


class OwnerType(StrEnum):
    USER = "user"
    TEAM = "team"
    SERVICE = "service"
    ORGANIZATION_UNIT = "organization_unit"


class ActorType(StrEnum):
    SYSTEM = "system"
    USER = "user"
    SERVICE = "service"
    DEVELOPMENT = "development"


class ServiceActorStatus(StrEnum):
    ACTIVE = "active"
    DISABLED = "disabled"


class ServiceActorApiKeyStatus(StrEnum):
    ACTIVE = "active"
    RETIRING = "retiring"
    REVOKED = "revoked"
    EXPIRED = "expired"


class PolicyStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    DISABLED = "disabled"
    ARCHIVED = "archived"


class PolicyDecisionValue(StrEnum):
    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_HUMAN_REVIEW = "require_human_review"
    NOT_APPLICABLE = "not_applicable"


class TraceEventType(StrEnum):
    MODEL_CALL_STARTED = "model_call_started"
    MODEL_CALL_COMPLETED = "model_call_completed"
    TOOL_CALL_REQUESTED = "tool_call_requested"
    TOOL_CALL_RESUME_REQUESTED = "tool_call_resume_requested"
    TOOL_CALL_ALLOWED = "tool_call_allowed"
    TOOL_CALL_DENIED = "tool_call_denied"
    HUMAN_REVIEW_REQUESTED = "human_review_requested"
    ERROR = "error"


class HumanApprovalStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


def validate_service_actor_id(value: str) -> str:
    if not value.startswith("service:") or value == "service:":
        raise ValueError("Service actor IDs must use service:<stable-id>.")
    return value


def validate_service_actor_key_hash(value: str) -> str:
    normalized_value = value.lower()
    if not normalized_value.startswith(SERVICE_ACTOR_API_KEY_HASH_PREFIX):
        raise ValueError("Service actor API key hashes must use sha256:<digest>.")

    digest = normalized_value.removeprefix(SERVICE_ACTOR_API_KEY_HASH_PREFIX)
    if len(digest) != SERVICE_ACTOR_API_KEY_HASH_HEX_LENGTH or any(
        char not in "0123456789abcdef" for char in digest
    ):
        raise ValueError("Service actor API key hashes must use sha256:<64 hex chars>.")

    return normalized_value


def validate_service_actor_key_id(value: str) -> str:
    normalized_value = value.strip()
    if not normalized_value:
        raise ValueError("Service actor API key IDs must be non-empty.")
    if normalized_value.startswith(SERVICE_ACTOR_API_KEY_HASH_PREFIX):
        raise ValueError("Service actor API key IDs must not be key hashes.")
    return normalized_value


def validate_service_actor_scope(value: str) -> str:
    normalized_value = value.strip()
    if normalized_value not in SUPPORTED_SERVICE_ACTOR_SCOPES:
        supported_scopes = ", ".join(sorted(SUPPORTED_SERVICE_ACTOR_SCOPES))
        raise ValueError(f"Service actor scope must be one of: {supported_scopes}.")
    return normalized_value


def validate_service_actor_scope_rule_values(
    values: object,
    *,
    field_name: str,
    supported_values: frozenset[str] | None = None,
    normalize: bool = False,
) -> list[str]:
    if values is None:
        return []
    if not isinstance(values, list | tuple):
        raise ValueError(f"{field_name} must be a list of strings.")

    normalized_values: list[str] = []
    for raw_value in values:
        if not isinstance(raw_value, str) or not raw_value.strip():
            raise ValueError(f"{field_name} values must be non-empty strings.")

        value = raw_value.strip()
        if normalize:
            value = value.lower()

        if (
            supported_values is not None
            and value != SERVICE_ACTOR_FINE_GRAINED_WILDCARD
            and value not in supported_values
        ):
            supported = ", ".join(sorted(supported_values))
            raise ValueError(
                f"{field_name} unsupported value: {value}. "
                f"Supported values: {supported}, {SERVICE_ACTOR_FINE_GRAINED_WILDCARD}."
            )

        normalized_values.append(value)

    return list(dict.fromkeys(normalized_values))


def validate_data_usage_string_list(
    values: object,
    *,
    field_name: str,
) -> list[str]:
    if values is None:
        return []
    if not isinstance(values, list | tuple):
        raise ValueError(f"{field_name} must be a list of strings.")

    normalized_values: list[str] = []
    for raw_value in values:
        if not isinstance(raw_value, str) or not raw_value.strip():
            raise ValueError(f"{field_name} values must be non-empty strings.")
        normalized_values.append(raw_value.strip())

    return list(dict.fromkeys(normalized_values))


class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    owner_type: Mapped[OwnerType] = mapped_column(
        Enum(
            OwnerType,
            values_callable=enum_values,
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            name="agent_owner_type",
        ),
        nullable=False,
    )
    owner_id: Mapped[str] = mapped_column(String(255), nullable=False)
    owner_name: Mapped[str] = mapped_column(String(255), nullable=False)
    owner_contact_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    environment: Mapped[Environment] = mapped_column(
        Enum(
            Environment,
            values_callable=enum_values,
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            name="agent_environment",
        ),
        nullable=False,
    )
    status: Mapped[AgentStatus] = mapped_column(
        Enum(
            AgentStatus,
            values_callable=enum_values,
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            name="agent_status",
        ),
        nullable=False,
    )
    risk_level: Mapped[RiskLevel] = mapped_column(
        Enum(
            RiskLevel,
            values_callable=enum_values,
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            name="agent_risk_level",
        ),
        nullable=False,
    )
    framework: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class Capability(Base):
    __tablename__ = "capabilities"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    capability_type: Mapped[CapabilityType] = mapped_column(
        Enum(
            CapabilityType,
            values_callable=enum_values,
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            name="capability_type",
        ),
        nullable=False,
    )
    external_ref: Mapped[str | None] = mapped_column(String(512), nullable=True)
    status: Mapped[CapabilityStatus] = mapped_column(
        Enum(
            CapabilityStatus,
            values_callable=enum_values,
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            name="capability_status",
        ),
        nullable=False,
    )
    risk_level: Mapped[RiskLevel] = mapped_column(
        Enum(
            RiskLevel,
            values_callable=enum_values,
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            name="capability_risk_level",
        ),
        nullable=False,
    )
    metadata_: Mapped[SafeMetadata] = mapped_column(
        "metadata",
        JSON,
        nullable=False,
        default=dict,
        server_default=text("'{}'"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default=text("CURRENT_TIMESTAMP"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        server_default=text("CURRENT_TIMESTAMP"),
    )

    @validates("metadata_")
    def validate_metadata(self, _key: str, value: SafeMetadata) -> SafeMetadata:
        return reject_unsafe_metadata_keys(value)


class DataSource(Base):
    __tablename__ = "sources"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_type: Mapped[DataSourceType] = mapped_column(
        Enum(
            DataSourceType,
            values_callable=enum_values,
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            name="source_type",
        ),
        nullable=False,
    )
    external_ref: Mapped[str | None] = mapped_column(String(512), nullable=True)
    owner_type: Mapped[OwnerType] = mapped_column(
        Enum(
            OwnerType,
            values_callable=enum_values,
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            name="source_owner_type",
        ),
        nullable=False,
    )
    owner_id: Mapped[str] = mapped_column(String(255), nullable=False)
    owner_name: Mapped[str] = mapped_column(String(255), nullable=False)
    owner_contact_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    status: Mapped[DataSourceStatus] = mapped_column(
        Enum(
            DataSourceStatus,
            values_callable=enum_values,
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            name="source_status",
        ),
        nullable=False,
    )
    risk_level: Mapped[RiskLevel] = mapped_column(
        Enum(
            RiskLevel,
            values_callable=enum_values,
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            name="source_risk_level",
        ),
        nullable=False,
    )
    metadata_: Mapped[SafeMetadata] = mapped_column(
        "metadata",
        JSON,
        nullable=False,
        default=dict,
        server_default=text("'{}'"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default=text("CURRENT_TIMESTAMP"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        server_default=text("CURRENT_TIMESTAMP"),
    )
    usage_profile: Mapped["DataUsageProfile | None"] = relationship(
        back_populates="source",
        uselist=False,
    )

    @validates("metadata_")
    def validate_metadata(self, _key: str, value: SafeMetadata) -> SafeMetadata:
        return reject_unsafe_metadata_keys(value)


class DataUsageProfile(Base):
    __tablename__ = "data_usage_profiles"
    __table_args__ = (
        UniqueConstraint("source_id", name="uq_data_usage_profiles_source_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    source_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("sources.id"),
        nullable=False,
    )
    data_classification: Mapped[DataUsageClassification] = mapped_column(
        Enum(
            DataUsageClassification,
            values_callable=enum_values,
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            name="data_usage_classification",
        ),
        nullable=False,
    )
    contains_personal_data: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )
    contains_sensitive_data: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )
    data_categories: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
        server_default=text("'[]'"),
    )
    legal_basis: Mapped[str | None] = mapped_column(Text, nullable=True)
    allowed_purposes: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
        server_default=text("'[]'"),
    )
    prohibited_purposes: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
        server_default=text("'[]'"),
    )
    allowed_processing: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
        server_default=text("'[]'"),
    )
    prohibited_processing: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
        server_default=text("'[]'"),
    )
    residency: Mapped[str | None] = mapped_column(String(255), nullable=True)
    retention_policy: Mapped[str | None] = mapped_column(String(255), nullable=True)
    data_owner: Mapped[str | None] = mapped_column(String(255), nullable=True)
    review_status: Mapped[DataUsageReviewStatus] = mapped_column(
        Enum(
            DataUsageReviewStatus,
            values_callable=enum_values,
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            name="data_usage_review_status",
        ),
        nullable=False,
    )
    reviewed_by_actor_type: Mapped[ActorType | None] = mapped_column(
        Enum(
            ActorType,
            values_callable=enum_values,
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            name="data_usage_profile_reviewed_actor_type",
        ),
        nullable=True,
    )
    reviewed_by_actor_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    review_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    dpia_required: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )
    dpia_reference: Mapped[str | None] = mapped_column(String(512), nullable=True)
    metadata_: Mapped[SafeMetadata] = mapped_column(
        "metadata",
        JSON,
        nullable=False,
        default=dict,
        server_default=text("'{}'"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default=text("CURRENT_TIMESTAMP"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        server_default=text("CURRENT_TIMESTAMP"),
    )
    source: Mapped[DataSource] = relationship(back_populates="usage_profile")

    @validates(
        "data_categories",
        "allowed_purposes",
        "prohibited_purposes",
        "allowed_processing",
        "prohibited_processing",
    )
    def validate_string_list(self, key: str, value: object) -> list[str]:
        return validate_data_usage_string_list(value, field_name=key)

    @validates("metadata_")
    def validate_metadata(self, _key: str, value: SafeMetadata) -> SafeMetadata:
        return reject_unsafe_metadata_keys(value)


class ModelAsset(Base):
    __tablename__ = "model_assets"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    model_type: Mapped[ModelAssetType] = mapped_column(
        Enum(
            ModelAssetType,
            values_callable=enum_values,
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            name="model_asset_type",
        ),
        nullable=False,
    )
    provider: Mapped[ModelProvider] = mapped_column(
        Enum(
            ModelProvider,
            values_callable=enum_values,
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            name="model_asset_provider",
        ),
        nullable=False,
    )
    model_ref: Mapped[str | None] = mapped_column(String(512), nullable=True)
    version: Mapped[str | None] = mapped_column(String(255), nullable=True)
    owner_type: Mapped[OwnerType] = mapped_column(
        Enum(
            OwnerType,
            values_callable=enum_values,
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            name="model_asset_owner_type",
        ),
        nullable=False,
    )
    owner_id: Mapped[str] = mapped_column(String(255), nullable=False)
    owner_name: Mapped[str] = mapped_column(String(255), nullable=False)
    owner_contact_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    status: Mapped[ModelAssetStatus] = mapped_column(
        Enum(
            ModelAssetStatus,
            values_callable=enum_values,
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            name="model_asset_status",
        ),
        nullable=False,
    )
    risk_level: Mapped[RiskLevel] = mapped_column(
        Enum(
            RiskLevel,
            values_callable=enum_values,
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            name="model_asset_risk_level",
        ),
        nullable=False,
    )
    metadata_: Mapped[SafeMetadata] = mapped_column(
        "metadata",
        JSON,
        nullable=False,
        default=dict,
        server_default=text("'{}'"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default=text("CURRENT_TIMESTAMP"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        server_default=text("CURRENT_TIMESTAMP"),
    )

    @validates("metadata_")
    def validate_metadata(self, _key: str, value: SafeMetadata) -> SafeMetadata:
        return reject_unsafe_metadata_keys(value)


class AccessGrant(Base):
    __tablename__ = "access_grants"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    grant_type: Mapped[AccessGrantType] = mapped_column(
        Enum(
            AccessGrantType,
            values_callable=enum_values,
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            name="access_grant_type",
        ),
        nullable=False,
    )
    subject_type: Mapped[AccessGrantSubjectType] = mapped_column(
        Enum(
            AccessGrantSubjectType,
            values_callable=enum_values,
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            name="access_grant_subject_type",
        ),
        nullable=False,
    )
    subject_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    target_type: Mapped[AccessGrantTargetType] = mapped_column(
        Enum(
            AccessGrantTargetType,
            values_callable=enum_values,
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            name="access_grant_target_type",
        ),
        nullable=False,
    )
    target_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    external_ref: Mapped[str | None] = mapped_column(String(512), nullable=True)
    status: Mapped[AccessGrantStatus] = mapped_column(
        Enum(
            AccessGrantStatus,
            values_callable=enum_values,
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            name="access_grant_status",
        ),
        nullable=False,
    )
    granted_by_actor_type: Mapped[ActorType] = mapped_column(
        Enum(
            ActorType,
            values_callable=enum_values,
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            name="access_grant_granted_by_actor_type",
        ),
        nullable=False,
    )
    granted_by_actor_id: Mapped[str] = mapped_column(String(255), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    risk_level: Mapped[RiskLevel] = mapped_column(
        Enum(
            RiskLevel,
            values_callable=enum_values,
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            name="access_grant_risk_level",
        ),
        nullable=False,
    )
    metadata_: Mapped[SafeMetadata] = mapped_column(
        "metadata",
        JSON,
        nullable=False,
        default=dict,
        server_default=text("'{}'"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default=text("CURRENT_TIMESTAMP"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        server_default=text("CURRENT_TIMESTAMP"),
    )

    @validates("metadata_")
    def validate_metadata(self, _key: str, value: SafeMetadata) -> SafeMetadata:
        return reject_unsafe_metadata_keys(value)


class CheckTool(Base):
    __tablename__ = "check_tools"
    __table_args__ = (UniqueConstraint("name", name="uq_check_tools_name"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    tool_type: Mapped[CheckToolType] = mapped_column(
        Enum(
            CheckToolType,
            values_callable=enum_values,
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            name="check_tool_type",
        ),
        nullable=False,
    )
    status: Mapped[CheckToolStatus] = mapped_column(
        Enum(
            CheckToolStatus,
            values_callable=enum_values,
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            name="check_tool_status",
        ),
        nullable=False,
    )
    owner_type: Mapped[OwnerType] = mapped_column(
        Enum(
            OwnerType,
            values_callable=enum_values,
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            name="check_tool_owner_type",
        ),
        nullable=False,
    )
    owner_id: Mapped[str] = mapped_column(String(255), nullable=False)
    owner_name: Mapped[str] = mapped_column(String(255), nullable=False)
    metadata_: Mapped[SafeMetadata] = mapped_column(
        "metadata",
        JSON,
        nullable=False,
        default=dict,
        server_default=text("'{}'"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default=text("CURRENT_TIMESTAMP"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        server_default=text("CURRENT_TIMESTAMP"),
    )
    results: Mapped[list["CheckResult"]] = relationship(back_populates="check_tool")
    check_steps: Mapped[list["PolicyCheckStep"]] = relationship(
        back_populates="check_tool"
    )

    @validates("metadata_")
    def validate_metadata(self, _key: str, value: SafeMetadata) -> SafeMetadata:
        return reject_unsafe_metadata_keys(value)


class CheckResult(Base):
    __tablename__ = "check_results"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    check_tool_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("check_tools.id"),
        nullable=False,
    )
    agent_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("agents.id"),
        nullable=True,
    )
    run_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    trace_event_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("trace_events.id"),
        nullable=True,
    )
    policy_decision_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("policy_decisions.id"),
        nullable=True,
    )
    target_type: Mapped[CheckResultTargetType] = mapped_column(
        Enum(
            CheckResultTargetType,
            values_callable=enum_values,
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            name="check_result_target_type",
        ),
        nullable=False,
    )
    target_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    outcome: Mapped[CheckResultOutcome] = mapped_column(
        Enum(
            CheckResultOutcome,
            values_callable=enum_values,
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            name="check_result_outcome",
        ),
        nullable=False,
    )
    confidence: Mapped[CheckResultConfidence | None] = mapped_column(
        Enum(
            CheckResultConfidence,
            values_callable=enum_values,
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            name="check_result_confidence",
        ),
        nullable=True,
    )
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_: Mapped[SafeMetadata] = mapped_column(
        "metadata",
        JSON,
        nullable=False,
        default=dict,
        server_default=text("'{}'"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default=text("CURRENT_TIMESTAMP"),
    )
    check_tool: Mapped[CheckTool] = relationship(back_populates="results")

    @validates("metadata_")
    def validate_metadata(self, _key: str, value: SafeMetadata) -> SafeMetadata:
        return reject_unsafe_metadata_keys(value)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    event_type: Mapped[str] = mapped_column(String(255), nullable=False)
    actor_type: Mapped[ActorType] = mapped_column(
        Enum(
            ActorType,
            values_callable=enum_values,
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            name="audit_actor_type",
        ),
        nullable=False,
    )
    actor_id: Mapped[str] = mapped_column(String(255), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(255), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_: Mapped[dict[str, object]] = mapped_column(
        "metadata",
        JSON,
        nullable=False,
        default=dict,
        server_default=text("'{}'"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default=text("CURRENT_TIMESTAMP"),
    )


class ServiceActor(Base):
    __tablename__ = "service_actors"
    __table_args__ = (UniqueConstraint("actor_id", name="uq_service_actors_actor_id"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    actor_id: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[ServiceActorStatus] = mapped_column(
        Enum(
            ServiceActorStatus,
            values_callable=enum_values,
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            name="service_actor_status",
        ),
        nullable=False,
        default=ServiceActorStatus.ACTIVE,
        server_default=ServiceActorStatus.ACTIVE.value,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default=text("CURRENT_TIMESTAMP"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        server_default=text("CURRENT_TIMESTAMP"),
    )
    disabled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    api_keys: Mapped[list["ServiceActorApiKey"]] = relationship(
        back_populates="service_actor",
    )
    scopes: Mapped[list["ServiceActorScope"]] = relationship(
        back_populates="service_actor",
    )
    scope_rules: Mapped[list["ServiceActorScopeRule"]] = relationship(
        back_populates="service_actor",
    )

    @validates("actor_id")
    def validate_actor_id(self, _key: str, value: str) -> str:
        return validate_service_actor_id(value)


class ServiceActorApiKey(Base):
    __tablename__ = "service_actor_api_keys"
    __table_args__ = (
        UniqueConstraint("key_id", name="uq_service_actor_api_keys_key_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    service_actor_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("service_actors.id"),
        nullable=False,
    )
    key_id: Mapped[str] = mapped_column(String(255), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    hash_algorithm: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="sha256",
        server_default="sha256",
    )
    status: Mapped[ServiceActorApiKeyStatus] = mapped_column(
        Enum(
            ServiceActorApiKeyStatus,
            values_callable=enum_values,
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            name="service_actor_api_key_status",
        ),
        nullable=False,
        default=ServiceActorApiKeyStatus.ACTIVE,
        server_default=ServiceActorApiKeyStatus.ACTIVE.value,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default=text("CURRENT_TIMESTAMP"),
    )
    activated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    retiring_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    grace_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_used_endpoint: Mapped[str | None] = mapped_column(String(255), nullable=True)
    service_actor: Mapped[ServiceActor] = relationship(back_populates="api_keys")

    @validates("key_id")
    def validate_key_id(self, _key: str, value: str) -> str:
        return validate_service_actor_key_id(value)

    @validates("key_hash")
    def validate_key_hash(self, _key: str, value: str) -> str:
        return validate_service_actor_key_hash(value)


class ServiceActorScope(Base):
    __tablename__ = "service_actor_scopes"
    __table_args__ = (
        UniqueConstraint(
            "service_actor_id",
            "scope",
            name="uq_service_actor_scopes_actor_scope",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    service_actor_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("service_actors.id"),
        nullable=False,
    )
    scope: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default=text("CURRENT_TIMESTAMP"),
    )
    service_actor: Mapped[ServiceActor] = relationship(back_populates="scopes")

    @validates("scope")
    def validate_scope(self, _key: str, value: str) -> str:
        return validate_service_actor_scope(value)


class ServiceActorScopeRule(Base):
    __tablename__ = "service_actor_scope_rules"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    service_actor_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("service_actors.id"),
        nullable=False,
    )
    agent_ids: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
        server_default=text("'[]'"),
    )
    environments: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
        server_default=text("'[]'"),
    )
    runtime_modes: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
        server_default=text("'[]'"),
    )
    tool_names: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
        server_default=text("'[]'"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default=text("CURRENT_TIMESTAMP"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        server_default=text("CURRENT_TIMESTAMP"),
    )
    service_actor: Mapped[ServiceActor] = relationship(back_populates="scope_rules")

    @validates("agent_ids")
    def validate_agent_ids(self, _key: str, value: object) -> list[str]:
        return validate_service_actor_scope_rule_values(
            value,
            field_name="agent_ids",
        )

    @validates("environments")
    def validate_environments(self, _key: str, value: object) -> list[str]:
        return validate_service_actor_scope_rule_values(
            value,
            field_name="environments",
            supported_values=SUPPORTED_SERVICE_ACTOR_SCOPE_ENVIRONMENTS,
            normalize=True,
        )

    @validates("runtime_modes")
    def validate_runtime_modes(self, _key: str, value: object) -> list[str]:
        return validate_service_actor_scope_rule_values(
            value,
            field_name="runtime_modes",
            supported_values=SUPPORTED_SERVICE_ACTOR_RUNTIME_MODES,
            normalize=True,
        )

    @validates("tool_names")
    def validate_tool_names(self, _key: str, value: object) -> list[str]:
        return validate_service_actor_scope_rule_values(
            value,
            field_name="tool_names",
        )


class Policy(Base):
    __tablename__ = "policies"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[PolicyStatus] = mapped_column(
        Enum(
            PolicyStatus,
            values_callable=enum_values,
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            name="policy_status",
        ),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default=text("CURRENT_TIMESTAMP"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        server_default=text("CURRENT_TIMESTAMP"),
    )


class PolicyRule(Base):
    __tablename__ = "policy_rules"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    policy_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("policies.id"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    condition: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default=text("CURRENT_TIMESTAMP"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        server_default=text("CURRENT_TIMESTAMP"),
    )
    check_steps: Mapped[list["PolicyCheckStep"]] = relationship(
        back_populates="policy_rule"
    )


class PolicyCheckStep(Base):
    __tablename__ = "policy_check_steps"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    policy_rule_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("policy_rules.id"),
        nullable=False,
    )
    check_tool_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("check_tools.id"),
        nullable=True,
    )
    check_type: Mapped[PolicyCheckStepCheckType] = mapped_column(
        Enum(
            PolicyCheckStepCheckType,
            values_callable=enum_values,
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            name="policy_check_step_type",
        ),
        nullable=False,
    )
    target_selector: Mapped[PolicyCheckStepTargetSelector] = mapped_column(
        Enum(
            PolicyCheckStepTargetSelector,
            values_callable=enum_values,
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            name="policy_check_step_target_selector",
        ),
        nullable=False,
    )
    required: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )
    failure_behavior: Mapped[PolicyCheckStepFailureBehavior] = mapped_column(
        Enum(
            PolicyCheckStepFailureBehavior,
            values_callable=enum_values,
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            name="policy_check_step_failure_behavior",
        ),
        nullable=False,
    )
    min_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[PolicyCheckStepStatus] = mapped_column(
        Enum(
            PolicyCheckStepStatus,
            values_callable=enum_values,
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            name="policy_check_step_status",
        ),
        nullable=False,
    )
    evidence_retention: Mapped[PolicyCheckStepEvidenceRetention] = mapped_column(
        Enum(
            PolicyCheckStepEvidenceRetention,
            values_callable=enum_values,
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            name="policy_check_step_evidence_retention",
        ),
        nullable=False,
    )
    metadata_: Mapped[SafeMetadata] = mapped_column(
        "metadata",
        JSON,
        nullable=False,
        default=dict,
        server_default=text("'{}'"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default=text("CURRENT_TIMESTAMP"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        server_default=text("CURRENT_TIMESTAMP"),
    )
    policy_rule: Mapped[PolicyRule] = relationship(back_populates="check_steps")
    check_tool: Mapped[CheckTool | None] = relationship(back_populates="check_steps")

    @validates("metadata_")
    def validate_metadata(self, _key: str, value: SafeMetadata) -> SafeMetadata:
        return reject_unsafe_metadata_keys(value)


class PolicyDecision(Base):
    __tablename__ = "policy_decisions"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    agent_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("agents.id"),
        nullable=True,
    )
    policy_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("policies.id"),
        nullable=True,
    )
    rule_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("policy_rules.id"),
        nullable=True,
    )
    trace_event_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("trace_events.id"),
        nullable=True,
    )
    decision: Mapped[PolicyDecisionValue] = mapped_column(
        Enum(
            PolicyDecisionValue,
            values_callable=enum_values,
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            name="policy_decision_value",
        ),
        nullable=False,
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    context_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default=text("CURRENT_TIMESTAMP"),
    )
    trace_event: Mapped["TraceEventRecord | None"] = relationship(
        back_populates="policy_decisions",
    )


class HumanApproval(Base):
    __tablename__ = "human_approvals"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    agent_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("agents.id"),
        nullable=False,
    )
    policy_decision_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("policy_decisions.id"),
        nullable=True,
    )
    status: Mapped[HumanApprovalStatus] = mapped_column(
        Enum(
            HumanApprovalStatus,
            values_callable=enum_values,
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            name="human_approval_status",
        ),
        nullable=False,
    )
    requested_by_actor_type: Mapped[ActorType] = mapped_column(
        Enum(
            ActorType,
            values_callable=enum_values,
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            name="human_approval_requested_actor_type",
        ),
        nullable=False,
    )
    requested_by_actor_id: Mapped[str] = mapped_column(String(255), nullable=False)
    reviewed_by_actor_type: Mapped[ActorType | None] = mapped_column(
        Enum(
            ActorType,
            values_callable=enum_values,
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            name="human_approval_reviewed_actor_type",
        ),
        nullable=True,
    )
    reviewed_by_actor_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    decision_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default=text("CURRENT_TIMESTAMP"),
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )


class AgentRunRecord(Base):
    __tablename__ = "agent_runs"
    __table_args__ = (
        UniqueConstraint("agent_id", "run_id", name="uq_agent_runs_agent_run"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    agent_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("agents.id"),
        nullable=False,
    )
    run_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    correlation_id: Mapped[str] = mapped_column(String(255), nullable=False)
    environment: Mapped[Environment] = mapped_column(
        Enum(
            Environment,
            values_callable=enum_values,
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            name="agent_run_environment",
        ),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_: Mapped[SafeMetadata] = mapped_column(
        "metadata",
        JSON,
        nullable=False,
        default=dict,
        server_default=text("'{}'"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default=text("CURRENT_TIMESTAMP"),
    )

    @validates("metadata_")
    def validate_metadata(self, _key: str, value: SafeMetadata) -> SafeMetadata:
        return reject_unsafe_metadata_keys(value)


class TraceEventRecord(Base):
    __tablename__ = "trace_events"
    __table_args__ = (
        ForeignKeyConstraint(
            ["agent_id", "run_id"],
            ["agent_runs.agent_id", "agent_runs.run_id"],
            name="fk_trace_events_agent_run",
        ),
        UniqueConstraint(
            "agent_id",
            "run_id",
            "external_event_id",
            name="uq_trace_events_external_event_per_run",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    agent_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("agents.id"),
        nullable=False,
    )
    run_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    external_event_id: Mapped[str] = mapped_column(String(255), nullable=False)
    correlation_id: Mapped[str] = mapped_column(String(255), nullable=False)
    event_type: Mapped[TraceEventType] = mapped_column(
        Enum(
            TraceEventType,
            values_callable=enum_values,
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            name="trace_event_type",
        ),
        nullable=False,
    )
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_: Mapped[SafeMetadata] = mapped_column(
        "metadata",
        JSON,
        nullable=False,
        default=dict,
        server_default=text("'{}'"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default=text("CURRENT_TIMESTAMP"),
    )
    policy_decisions: Mapped[list["PolicyDecision"]] = relationship(
        back_populates="trace_event",
    )

    @validates("metadata_")
    def validate_metadata(self, _key: str, value: SafeMetadata) -> SafeMetadata:
        return reject_unsafe_metadata_keys(value)
