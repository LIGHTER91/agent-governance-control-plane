from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, model_validator

from agent_governance_api.models import (
    AgentStatus,
    Environment,
    OwnerType,
    PolicyDecisionValue,
    PolicyStatus,
    RiskLevel,
)


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


class PolicyBase(BaseModel):
    name: str
    description: str | None = None
    status: PolicyStatus


class PolicyCreate(PolicyBase):
    pass


class PolicyRead(PolicyBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime


class PolicyRuleBase(BaseModel):
    policy_id: UUID
    name: str
    description: str | None = None
    condition: str


class PolicyRuleCreate(PolicyRuleBase):
    pass


class PolicyRuleRead(PolicyRuleBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime


class PolicyDecisionBase(BaseModel):
    agent_id: UUID | None = None
    policy_id: UUID | None = None
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
