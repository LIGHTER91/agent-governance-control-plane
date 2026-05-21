from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from agent_governance_api.models import (
    ActorType,
    AgentStatus,
    Environment,
    HumanApprovalStatus,
    OwnerType,
    PolicyDecisionValue,
    PolicyStatus,
    RiskLevel,
    ServiceActorApiKeyStatus,
    ServiceActorStatus,
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


EvidenceMetadataValue = str | int | float | bool | None
EvidenceMetadata = dict[str, EvidenceMetadataValue]
AgentActivitySeverity = Literal["info", "warning", "error"]


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


class EvidencePolicyDecisionRead(BaseModel):
    id: UUID
    agent_id: UUID | None = None
    policy_id: UUID | None = None
    rule_id: UUID | None = None
    trace_event_id: UUID | None = None
    decision: PolicyDecisionValue
    reason: str
    context_hash: str | None = None
    policy: EvidencePolicyReferenceRead | None = None
    rule: EvidencePolicyRuleReferenceRead | None = None
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


class EvidenceBundleRead(BaseModel):
    agent: AgentRead
    audit_logs: list[EvidenceAuditLogRead]
    agent_runs: list[EvidenceAgentRunRead]
    trace_events: list[EvidenceTraceEventRead]
    policy_decisions: list[EvidencePolicyDecisionRead]
    human_approvals: list[EvidenceHumanApprovalRead]


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

    id: UUID
    service_actor_id: UUID
    key_id: str
    hash_algorithm: str
    status: ServiceActorApiKeyStatus
    created_at: datetime
    activated_at: datetime | None = None
    retiring_at: datetime | None = None
    grace_expires_at: datetime | None = None
    expires_at: datetime | None = None
    revoked_at: datetime | None = None
    last_used_at: datetime | None = None
    last_used_endpoint: str | None = None
