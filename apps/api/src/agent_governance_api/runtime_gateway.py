from enum import StrEnum
from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from agent_governance_api.metadata_safety import (
    SafeMetadata,
    reject_unsafe_metadata_keys,
)
from agent_governance_api.models import PolicyDecisionValue


class RuntimeDecisionMode(StrEnum):
    TELEMETRY = "telemetry"
    SIMULATION = "simulation"
    ENFORCEMENT = "enforcement"


class RuntimeToolCallDecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: str
    agent_id: UUID
    run_id: UUID
    correlation_id: str
    tool_name: str
    action_summary: str
    metadata: SafeMetadata = Field(default_factory=dict)
    mode: RuntimeDecisionMode

    @field_validator("request_id", "correlation_id", "tool_name", "action_summary")
    @classmethod
    def require_non_empty_text(cls, value: str) -> str:
        return _require_non_empty_text(value)

    @field_validator("metadata")
    @classmethod
    def reject_unsafe_metadata(cls, value: SafeMetadata) -> SafeMetadata:
        return reject_unsafe_metadata_keys(value)


class RuntimeToolCallDecisionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: str
    agent_id: UUID
    run_id: UUID
    tool_name: str
    decision: PolicyDecisionValue
    proceed: bool
    reason: str
    trace_event_id: UUID | None = None
    policy_decision_id: UUID | None = None
    human_approval_id: UUID | None = None

    @field_validator("request_id", "tool_name", "reason")
    @classmethod
    def require_non_empty_text(cls, value: str) -> str:
        return _require_non_empty_text(value)

    @model_validator(mode="after")
    def require_consistent_proceed_value(self) -> Self:
        expected_proceed = {
            PolicyDecisionValue.ALLOW: True,
            PolicyDecisionValue.DENY: False,
            PolicyDecisionValue.REQUIRE_HUMAN_REVIEW: False,
            PolicyDecisionValue.NOT_APPLICABLE: False,
        }[self.decision]

        if self.proceed != expected_proceed:
            raise ValueError(
                f"Decision {self.decision.value!r} requires proceed={expected_proceed}."
            )

        return self


def _require_non_empty_text(value: str) -> str:
    if not value.strip():
        raise ValueError("Value must not be empty.")
    return value
