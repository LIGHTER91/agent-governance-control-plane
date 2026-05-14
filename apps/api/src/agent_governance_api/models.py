from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from agent_governance_api.database import Base


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
