from datetime import UTC, datetime
from hashlib import sha256
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from agent_governance_api.audit import append_audit_log
from agent_governance_api.auth import (
    SCOPE_TELEMETRY_WRITE,
    ActorContext,
    get_current_integration_actor,
    require_scope,
    require_service_actor_fine_grained_scope,
)
from agent_governance_api.database import get_db_session
from agent_governance_api.models import (
    Agent,
    AgentRunRecord,
    HumanApproval,
    HumanApprovalStatus,
    PolicyDecision,
    PolicyDecisionValue,
    TraceEventRecord,
    TraceEventType,
)
from agent_governance_api.openapi_examples import TELEMETRY_EVENT_OPENAPI
from agent_governance_api.policy_decision_service import persist_policy_decision
from agent_governance_api.policy_evaluator import evaluate_policy
from agent_governance_api.policy_rule_adapter import (
    UnsupportedPolicyRuleConditionError,
    load_active_policy_evaluation_rules,
)
from agent_governance_api.telemetry import (
    TraceEvent,
    TraceEventIngestResponse,
    TraceEventPolicyDecisionResponse,
)

router = APIRouter(prefix="/telemetry", tags=["telemetry"])

AUTO_CREATED_RUN_STATUS = "observed"


@router.post(
    "/events",
    response_model=TraceEventIngestResponse,
    status_code=status.HTTP_201_CREATED,
    openapi_extra=TELEMETRY_EVENT_OPENAPI,
)
def ingest_trace_event(
    payload: TraceEvent,
    response: Response,
    session: Session = Depends(get_db_session),
    actor: ActorContext = Depends(get_current_integration_actor),
) -> TraceEventIngestResponse:
    require_scope(actor, SCOPE_TELEMETRY_WRITE)

    agent = session.get(Agent, payload.agent_id)
    if agent is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found.",
        )

    external_event_id = payload.external_event_id or str(payload.id)
    tool_name = _tool_name(payload)
    require_service_actor_fine_grained_scope(
        actor,
        agent_id=payload.agent_id,
        environment=agent.environment,
        tool_name=tool_name,
        session=session,
    )
    existing_event = session.scalar(
        select(TraceEventRecord).where(
            TraceEventRecord.agent_id == payload.agent_id,
            TraceEventRecord.run_id == payload.run_id,
            TraceEventRecord.external_event_id == external_event_id,
        )
    )
    if existing_event is not None:
        response.status_code = status.HTTP_200_OK
        policy_decision = _policy_decision_for_trace_event(
            session,
            existing_event,
            external_event_id=external_event_id,
        )
        human_approval = _human_approval_for_policy_decision(
            session,
            policy_decision,
        )
        return _trace_event_response(existing_event, policy_decision, human_approval)

    try:
        run = session.scalar(
            select(AgentRunRecord).where(
                AgentRunRecord.agent_id == payload.agent_id,
                AgentRunRecord.run_id == payload.run_id,
            )
        )
        if run is None:
            run = AgentRunRecord(
                agent_id=payload.agent_id,
                run_id=payload.run_id,
                correlation_id=payload.correlation_id,
                environment=agent.environment,
                status=AUTO_CREATED_RUN_STATUS,
                started_at=payload.timestamp,
                summary="Auto-created from telemetry event.",
                metadata_={},
            )
            session.add(run)
            session.flush()

        trace_event = TraceEventRecord(
            id=payload.id,
            agent_id=payload.agent_id,
            run_id=payload.run_id,
            external_event_id=external_event_id,
            correlation_id=payload.correlation_id,
            event_type=payload.event_type,
            timestamp=payload.timestamp,
            summary=payload.summary,
            metadata_=payload.metadata,
            created_at=datetime.now(UTC),
        )
        session.add(trace_event)
        session.flush()

        policy_decision = None
        human_approval = None
        if _is_tool_call_requested(payload.event_type):
            policy_decision = _evaluate_and_persist_policy_decision(
                session,
                agent=agent,
                payload=payload,
                trace_event=trace_event,
                tool_name=tool_name,
                external_event_id=external_event_id,
            )
            if policy_decision.decision is PolicyDecisionValue.REQUIRE_HUMAN_REVIEW:
                human_approval = _create_human_approval_for_policy_decision(
                    session,
                    policy_decision,
                    actor=actor,
                )

        session.commit()
        session.refresh(trace_event)
        if policy_decision is not None:
            session.refresh(policy_decision)
        if human_approval is not None:
            session.refresh(human_approval)
    except UnsupportedPolicyRuleConditionError as exc:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    except Exception:
        session.rollback()
        raise

    return _trace_event_response(trace_event, policy_decision, human_approval)


def _trace_event_response(
    trace_event: TraceEventRecord,
    policy_decision: PolicyDecision | None,
    human_approval: HumanApproval | None,
) -> TraceEventIngestResponse:
    return TraceEventIngestResponse(
        id=trace_event.id,
        agent_id=trace_event.agent_id,
        run_id=trace_event.run_id,
        event_type=trace_event.event_type,
        created_at=trace_event.created_at,
        policy_decision=_policy_decision_response(policy_decision),
        human_approval_id=human_approval.id if human_approval is not None else None,
    )


def _evaluate_and_persist_policy_decision(
    session: Session,
    *,
    agent: Agent,
    payload: TraceEvent,
    trace_event: TraceEventRecord,
    tool_name: str | None,
    external_event_id: str,
) -> PolicyDecision:
    rules = load_active_policy_evaluation_rules(session)
    result = evaluate_policy(
        agent_context={"agent_id": payload.agent_id},
        action_context={"tool_name": tool_name},
        environment=agent.environment,
        risk_level=agent.risk_level,
        rules=rules,
    )
    return persist_policy_decision(
        session,
        agent_id=payload.agent_id,
        evaluation_result=result,
        trace_event_id=trace_event.id,
        context_hash=_policy_context_hash(
            agent_id=payload.agent_id,
            run_id=payload.run_id,
            external_event_id=external_event_id,
        ),
    )


def _policy_decision_for_trace_event(
    session: Session,
    trace_event: TraceEventRecord,
    *,
    external_event_id: str,
) -> PolicyDecision | None:
    if not _is_tool_call_requested(trace_event.event_type):
        return None

    policy_decision = session.scalar(
        select(PolicyDecision)
        .where(PolicyDecision.trace_event_id == trace_event.id)
        .order_by(PolicyDecision.created_at.desc(), PolicyDecision.id.desc())
    )
    if policy_decision is not None:
        return policy_decision

    context_hash = _policy_context_hash(
        agent_id=trace_event.agent_id,
        run_id=trace_event.run_id,
        external_event_id=external_event_id,
    )
    return session.scalar(
        select(PolicyDecision)
        .where(
            PolicyDecision.agent_id == trace_event.agent_id,
            PolicyDecision.context_hash == context_hash,
        )
        .order_by(PolicyDecision.created_at.desc(), PolicyDecision.id.desc())
    )


def _policy_decision_response(
    policy_decision: PolicyDecision | None,
) -> TraceEventPolicyDecisionResponse | None:
    if policy_decision is None:
        return None
    return TraceEventPolicyDecisionResponse(
        id=policy_decision.id,
        trace_event_id=policy_decision.trace_event_id,
        decision=policy_decision.decision,
        reason=policy_decision.reason,
        policy_id=policy_decision.policy_id,
        policy_version_id=policy_decision.policy_version_id,
        rule_id=policy_decision.rule_id,
        created_at=policy_decision.created_at,
    )


def _create_human_approval_for_policy_decision(
    session: Session,
    policy_decision: PolicyDecision,
    *,
    actor: ActorContext,
) -> HumanApproval:
    if policy_decision.agent_id is None:
        raise ValueError("HumanApproval requires a PolicyDecision linked to an Agent.")

    approval = HumanApproval(
        agent_id=policy_decision.agent_id,
        policy_decision_id=policy_decision.id,
        status=HumanApprovalStatus.PENDING,
        requested_by_actor_type=actor.actor_type,
        requested_by_actor_id=actor.actor_id,
        reason=policy_decision.reason,
        created_at=datetime.now(UTC),
    )
    session.add(approval)
    session.flush()

    append_audit_log(
        session,
        event_type="human_approval_requested",
        actor_type=actor.actor_type,
        actor_id=actor.actor_id,
        entity_type="human_approval",
        entity_id=str(approval.id),
        summary="Human approval requested.",
        metadata={
            "agent_id": str(approval.agent_id),
            "status": approval.status.value,
            "policy_decision_id": str(policy_decision.id),
        },
    )

    return approval


def _human_approval_for_policy_decision(
    session: Session,
    policy_decision: PolicyDecision | None,
) -> HumanApproval | None:
    if policy_decision is None:
        return None

    return session.scalar(
        select(HumanApproval)
        .where(HumanApproval.policy_decision_id == policy_decision.id)
        .order_by(HumanApproval.created_at.desc(), HumanApproval.id.desc())
    )


def _tool_name(payload: TraceEvent) -> str | None:
    if not _is_tool_call_requested(payload.event_type):
        return None

    tool_name = payload.metadata.get("tool_name")
    if not isinstance(tool_name, str) or not tool_name.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="metadata.tool_name is required for tool_call_requested events.",
        )
    return tool_name


def _is_tool_call_requested(event_type: TraceEventType | str) -> bool:
    return TraceEventType(event_type) is TraceEventType.TOOL_CALL_REQUESTED


def _policy_context_hash(
    *,
    agent_id: UUID,
    run_id: UUID,
    external_event_id: str,
) -> str:
    context = f"{agent_id}:{run_id}:{external_event_id}".encode()
    return f"sha256:{sha256(context).hexdigest()}"
