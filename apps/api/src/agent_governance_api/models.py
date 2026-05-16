from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    DateTime,
    Enum,
    ForeignKey,
    ForeignKeyConstraint,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

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
    TOOL_CALL_ALLOWED = "tool_call_allowed"
    TOOL_CALL_DENIED = "tool_call_denied"
    HUMAN_REVIEW_REQUESTED = "human_review_requested"
    ERROR = "error"


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
