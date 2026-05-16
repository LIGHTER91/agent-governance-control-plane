from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from agent_governance_api.audit import append_audit_log
from agent_governance_api.database import get_db_session
from agent_governance_api.models import (
    ActorType,
    Agent,
    HumanApproval,
    HumanApprovalStatus,
    PolicyDecision,
)
from agent_governance_api.schemas import (
    HumanApprovalDecisionRequest,
    HumanApprovalRead,
    HumanApprovalRequest,
)

router = APIRouter(tags=["human-approvals"])

DEVELOPMENT_ACTOR_TYPE = ActorType.DEVELOPMENT
DEVELOPMENT_ACTOR_ID = "dev-placeholder"


@router.post(
    "/human-approvals",
    response_model=HumanApprovalRead,
    status_code=status.HTTP_201_CREATED,
)
def create_human_approval(
    payload: HumanApprovalRequest,
    session: Session = Depends(get_db_session),
) -> HumanApproval:
    _get_agent_or_404(session, payload.agent_id)
    if payload.policy_decision_id is not None:
        policy_decision = _get_policy_decision_or_404(
            session,
            payload.policy_decision_id,
        )
        _ensure_policy_decision_belongs_to_agent(policy_decision, payload.agent_id)

    approval = HumanApproval(
        agent_id=payload.agent_id,
        policy_decision_id=payload.policy_decision_id,
        status=HumanApprovalStatus.PENDING,
        requested_by_actor_type=DEVELOPMENT_ACTOR_TYPE,
        requested_by_actor_id=DEVELOPMENT_ACTOR_ID,
        reason=payload.reason,
        expires_at=payload.expires_at,
        created_at=datetime.now(UTC),
    )
    session.add(approval)
    session.flush()
    _append_human_approval_audit_log(
        session,
        approval,
        event_type="human_approval_requested",
        summary="Human approval requested.",
    )
    session.commit()
    session.refresh(approval)

    return approval


@router.get("/human-approvals/{approval_id}", response_model=HumanApprovalRead)
def get_human_approval(
    approval_id: UUID,
    session: Session = Depends(get_db_session),
) -> HumanApproval:
    return _get_human_approval_or_404(session, approval_id)


@router.get(
    "/agents/{agent_id}/human-approvals",
    response_model=list[HumanApprovalRead],
)
def list_agent_human_approvals(
    agent_id: UUID,
    session: Session = Depends(get_db_session),
) -> list[HumanApproval]:
    _get_agent_or_404(session, agent_id)
    statement = (
        select(HumanApproval)
        .where(HumanApproval.agent_id == agent_id)
        .order_by(HumanApproval.created_at, HumanApproval.id)
    )
    return list(session.scalars(statement).all())


@router.post(
    "/human-approvals/{approval_id}/approve",
    response_model=HumanApprovalRead,
)
def approve_human_approval(
    approval_id: UUID,
    payload: HumanApprovalDecisionRequest | None = None,
    session: Session = Depends(get_db_session),
) -> HumanApproval:
    approval = _get_human_approval_or_404(session, approval_id)
    _ensure_pending(approval)

    now = datetime.now(UTC)
    approval.status = HumanApprovalStatus.APPROVED
    approval.reviewed_by_actor_type = DEVELOPMENT_ACTOR_TYPE
    approval.reviewed_by_actor_id = DEVELOPMENT_ACTOR_ID
    approval.reviewed_at = now
    if payload is not None:
        approval.reason = payload.reason or approval.reason
        approval.decision_note = payload.decision_note

    _append_human_approval_audit_log(
        session,
        approval,
        event_type="human_approval_approved",
        summary="Human approval approved.",
    )
    session.commit()
    session.refresh(approval)

    return approval


@router.post(
    "/human-approvals/{approval_id}/reject",
    response_model=HumanApprovalRead,
)
def reject_human_approval(
    approval_id: UUID,
    payload: HumanApprovalDecisionRequest | None = None,
    session: Session = Depends(get_db_session),
) -> HumanApproval:
    approval = _get_human_approval_or_404(session, approval_id)
    _ensure_pending(approval)

    now = datetime.now(UTC)
    approval.status = HumanApprovalStatus.REJECTED
    approval.reviewed_by_actor_type = DEVELOPMENT_ACTOR_TYPE
    approval.reviewed_by_actor_id = DEVELOPMENT_ACTOR_ID
    approval.reviewed_at = now
    if payload is not None:
        approval.reason = payload.reason or approval.reason
        approval.decision_note = payload.decision_note

    _append_human_approval_audit_log(
        session,
        approval,
        event_type="human_approval_rejected",
        summary="Human approval rejected.",
    )
    session.commit()
    session.refresh(approval)

    return approval


@router.post(
    "/human-approvals/{approval_id}/cancel",
    response_model=HumanApprovalRead,
)
def cancel_human_approval(
    approval_id: UUID,
    session: Session = Depends(get_db_session),
) -> HumanApproval:
    approval = _get_human_approval_or_404(session, approval_id)
    _ensure_pending(approval)

    approval.status = HumanApprovalStatus.CANCELLED
    _append_human_approval_audit_log(
        session,
        approval,
        event_type="human_approval_cancelled",
        summary="Human approval cancelled.",
    )
    session.commit()
    session.refresh(approval)

    return approval


def _get_agent_or_404(session: Session, agent_id: UUID) -> Agent:
    agent = session.get(Agent, agent_id)
    if agent is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found.",
        )
    return agent


def _get_policy_decision_or_404(
    session: Session,
    policy_decision_id: UUID,
) -> PolicyDecision:
    policy_decision = session.get(PolicyDecision, policy_decision_id)
    if policy_decision is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Policy decision not found.",
        )
    return policy_decision


def _ensure_policy_decision_belongs_to_agent(
    policy_decision: PolicyDecision,
    agent_id: UUID,
) -> None:
    if policy_decision.agent_id != agent_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Policy decision does not belong to the requested agent.",
        )


def _get_human_approval_or_404(
    session: Session,
    approval_id: UUID,
) -> HumanApproval:
    approval = session.get(HumanApproval, approval_id)
    if approval is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Human approval not found.",
        )
    return approval


def _ensure_pending(approval: HumanApproval) -> None:
    if approval.status is not HumanApprovalStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only pending human approvals can transition.",
        )


def _append_human_approval_audit_log(
    session: Session,
    approval: HumanApproval,
    *,
    event_type: str,
    summary: str,
) -> None:
    metadata = {
        "agent_id": str(approval.agent_id),
        "status": approval.status.value,
    }
    if approval.policy_decision_id is not None:
        metadata["policy_decision_id"] = str(approval.policy_decision_id)

    append_audit_log(
        session,
        event_type=event_type,
        actor_type=DEVELOPMENT_ACTOR_TYPE,
        actor_id=DEVELOPMENT_ACTOR_ID,
        entity_type="human_approval",
        entity_id=str(approval.id),
        summary=summary,
        metadata=metadata,
    )
