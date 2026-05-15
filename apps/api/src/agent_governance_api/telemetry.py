from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from agent_governance_api.models import Environment

TelemetryMetadataValue = str | int | float | bool | None
TelemetryMetadata = dict[str, TelemetryMetadataValue]

UNSAFE_METADATA_KEY_PARTS = (
    "api_key",
    "authorization",
    "credential",
    "password",
    "raw_payload",
    "raw_prompt",
    "secret",
    "token",
)


class TraceEventType(StrEnum):
    MODEL_CALL_STARTED = "model_call_started"
    MODEL_CALL_COMPLETED = "model_call_completed"
    TOOL_CALL_REQUESTED = "tool_call_requested"
    TOOL_CALL_ALLOWED = "tool_call_allowed"
    TOOL_CALL_DENIED = "tool_call_denied"
    HUMAN_REVIEW_REQUESTED = "human_review_requested"
    ERROR = "error"


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
    metadata: TelemetryMetadata = Field(default_factory=dict)

    @field_validator("correlation_id", "status")
    @classmethod
    def require_non_empty_text(cls, value: str) -> str:
        return _require_non_empty_text(value)

    @field_validator("metadata")
    @classmethod
    def reject_unsafe_metadata(cls, value: TelemetryMetadata) -> TelemetryMetadata:
        return _reject_unsafe_metadata(value)


class TraceEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    agent_id: UUID
    run_id: UUID
    correlation_id: str
    event_type: TraceEventType
    timestamp: datetime
    summary: str
    metadata: TelemetryMetadata = Field(default_factory=dict)

    @field_validator("correlation_id", "summary")
    @classmethod
    def require_non_empty_text(cls, value: str) -> str:
        return _require_non_empty_text(value)

    @field_validator("metadata")
    @classmethod
    def reject_unsafe_metadata(cls, value: TelemetryMetadata) -> TelemetryMetadata:
        return _reject_unsafe_metadata(value)


def _require_non_empty_text(value: str) -> str:
    if not value.strip():
        raise ValueError("Value must not be empty.")
    return value


def _reject_unsafe_metadata(value: TelemetryMetadata) -> TelemetryMetadata:
    unsafe_keys = [
        key
        for key in value
        if any(part in key.lower() for part in UNSAFE_METADATA_KEY_PARTS)
    ]
    if unsafe_keys:
        raise ValueError("Telemetry metadata contains unsafe key names.")
    return value
