from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, model_validator

from agent_governance_api.models import AgentStatus, Environment, OwnerType, RiskLevel


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
