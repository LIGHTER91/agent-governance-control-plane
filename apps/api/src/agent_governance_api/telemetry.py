from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from agent_governance_api.metadata_safety import (
    SafeMetadata,
    reject_unsafe_metadata_keys,
)
from agent_governance_api.models import Environment, PolicyDecisionValue, TraceEventType


class AgentRun(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    agent_id: UUID
    correlation_id: str
    environment: Environment
    started_at: datetime
    ended_at: datetime | None = None
    status: str
    summary: str | None = None
    metadata: SafeMetadata = Field(default_factory=dict)

    @field_validator("correlation_id", "status")
    @classmethod
    def require_non_empty_text(cls, value: str) -> str:
        return _require_non_empty_text(value)

    @field_validator("metadata")
    @classmethod
    def reject_unsafe_metadata(cls, value: SafeMetadata) -> SafeMetadata:
        return reject_unsafe_metadata_keys(value)


class TraceEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    agent_id: UUID
    run_id: UUID
    external_event_id: str | None = None
    correlation_id: str
    event_type: TraceEventType
    timestamp: datetime
    summary: str
    metadata: SafeMetadata = Field(default_factory=dict)

    @field_validator("correlation_id", "summary")
    @classmethod
    def require_non_empty_text(cls, value: str) -> str:
        return _require_non_empty_text(value)

    @field_validator("external_event_id")
    @classmethod
    def require_non_empty_external_event_id(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _require_non_empty_text(value)

    @field_validator("metadata")
    @classmethod
    def reject_unsafe_metadata(cls, value: SafeMetadata) -> SafeMetadata:
        return reject_unsafe_metadata_keys(value)


class TraceEventIngestResponse(BaseModel):
    id: UUID
    agent_id: UUID
    run_id: UUID
    event_type: TraceEventType
    created_at: datetime
    policy_decision: "TraceEventPolicyDecisionResponse | None" = None
    human_approval_id: UUID | None = None


class TraceEventPolicyDecisionResponse(BaseModel):
    id: UUID
    trace_event_id: UUID | None = None
    decision: PolicyDecisionValue
    reason: str
    policy_id: UUID | None = None
    rule_id: UUID | None = None
    created_at: datetime


def _require_non_empty_text(value: str) -> str:
    if not value.strip():
        raise ValueError("Value must not be empty.")
    return value
