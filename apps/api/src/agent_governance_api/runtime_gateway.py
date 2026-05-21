from datetime import datetime
from enum import StrEnum
from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from agent_governance_api.metadata_safety import (
    SafeMetadata,
    reject_unsafe_metadata_keys,
)
from agent_governance_api.models import HumanApprovalStatus, PolicyDecisionValue


class RuntimeDecisionMode(StrEnum):
    TELEMETRY = "telemetry"
    SIMULATION = "simulation"
    ENFORCEMENT = "enforcement"


class RuntimeToolCallActivityType(StrEnum):
    TOOL_CALL_DECISION = "tool_call_decision"
    TOOL_CALL_RESUME = "tool_call_resume"


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


class RuntimeToolCallResumeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    resume_id: str
    original_request_id: str
    agent_id: UUID
    run_id: UUID
    tool_name: str
    human_approval_id: UUID
    policy_decision_id: UUID
    action_ref: str
    correlation_id: str
    metadata: SafeMetadata = Field(default_factory=dict)

    @field_validator(
        "resume_id",
        "original_request_id",
        "tool_name",
        "action_ref",
        "correlation_id",
    )
    @classmethod
    def require_non_empty_text(cls, value: str) -> str:
        return _require_non_empty_text(value)

    @field_validator("metadata")
    @classmethod
    def reject_unsafe_metadata(cls, value: SafeMetadata) -> SafeMetadata:
        return reject_unsafe_metadata_keys(value)


class RuntimeToolCallResumeResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    resume_id: str
    original_request_id: str
    agent_id: UUID
    run_id: UUID
    tool_name: str
    decision: PolicyDecisionValue
    proceed: bool
    reason: str
    human_approval_status: HumanApprovalStatus
    trace_event_id: UUID | None = None
    policy_decision_id: UUID
    human_approval_id: UUID

    @field_validator("resume_id", "original_request_id", "tool_name", "reason")
    @classmethod
    def require_non_empty_text(cls, value: str) -> str:
        return _require_non_empty_text(value)

    @model_validator(mode="after")
    def require_consistent_resume_proceed_value(self) -> Self:
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

        if (
            self.proceed
            and self.human_approval_status is not HumanApprovalStatus.APPROVED
        ):
            raise ValueError(
                "Resume proceed=true requires human_approval_status='approved'."
            )

        return self


class RuntimeToolCallActivityItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    type: RuntimeToolCallActivityType
    agent_id: UUID
    run_id: UUID
    request_id: str | None = None
    timestamp: datetime
    tool_name: str | None = None
    mode: RuntimeDecisionMode | None = None
    decision: PolicyDecisionValue | None = None
    proceed: bool | None = None
    reason: str | None = None
    trace_event_id: UUID
    policy_decision_id: UUID | None = None
    human_approval_id: UUID | None = None
    related_ids: dict[str, str] = Field(default_factory=dict)

    @field_validator("request_id", "tool_name", "reason")
    @classmethod
    def require_optional_non_empty_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _require_non_empty_text(value)


def _require_non_empty_text(value: str) -> str:
    if not value.strip():
        raise ValueError("Value must not be empty.")
    return value
