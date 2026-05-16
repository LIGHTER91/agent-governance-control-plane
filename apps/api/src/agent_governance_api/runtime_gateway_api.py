from datetime import UTC, datetime
from hashlib import sha256
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from agent_governance_api.audit import append_audit_log
from agent_governance_api.config import Settings, get_settings
from agent_governance_api.database import get_db_session
from agent_governance_api.models import (
    ActorType,
    Agent,
    AgentRunRecord,
    HumanApproval,
    HumanApprovalStatus,
    PolicyDecision,
    PolicyDecisionValue,
    TraceEventRecord,
    TraceEventType,
)
from agent_governance_api.openapi_examples import RUNTIME_TOOL_CALL_DECISION_OPENAPI
from agent_governance_api.policy_decision_service import persist_policy_decision
from agent_governance_api.policy_evaluator import evaluate_policy
from agent_governance_api.policy_rule_adapter import (
    UnsupportedPolicyRuleConditionError,
    load_active_policy_evaluation_rules,
)
from agent_governance_api.runtime_gateway import (
    RuntimeDecisionMode,
    RuntimeToolCallDecisionRequest,
    RuntimeToolCallDecisionResponse,
)

router = APIRouter(prefix="/runtime", tags=["runtime"])

SIMULATED_RUN_STATUS = "simulated"
ENFORCED_RUN_STATUS = "enforced"
DEVELOPMENT_ACTOR_TYPE = ActorType.DEVELOPMENT
DEVELOPMENT_ACTOR_ID = "dev-placeholder"


@router.post(
    "/tool-calls/decision",
    response_model=RuntimeToolCallDecisionResponse,
    status_code=status.HTTP_201_CREATED,
    openapi_extra=RUNTIME_TOOL_CALL_DECISION_OPENAPI,
)
def decide_runtime_tool_call(
    payload: RuntimeToolCallDecisionRequest,
    response: Response,
    session: Session = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> RuntimeToolCallDecisionResponse:
    if payload.mode is RuntimeDecisionMode.TELEMETRY:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=(
                "Runtime Gateway telemetry mode is not implemented for this "
                "endpoint yet. Use POST /telemetry/events for telemetry ingestion."
            ),
        )

    if (
        payload.mode is RuntimeDecisionMode.ENFORCEMENT
        and not settings.runtime_enforcement_enabled
    ):
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=(
                "Runtime Gateway enforcement mode is disabled. Set "
                "AGCP_RUNTIME_ENFORCEMENT_ENABLED=true to enable it."
            ),
        )

    agent = session.get(Agent, payload.agent_id)
    if agent is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found.",
        )

    existing_event = _runtime_trace_event_for_request(session, payload)
    if existing_event is not None:
        response.status_code = status.HTTP_200_OK
        policy_decision = _policy_decision_for_trace_event(session, existing_event)
        if policy_decision is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Runtime decision records are incomplete for this request.",
            )
        human_approval = _human_approval_for_policy_decision(session, policy_decision)
        return _runtime_decision_response(
            payload,
            trace_event=existing_event,
            policy_decision=policy_decision,
            human_approval=human_approval,
        )

    try:
        now = datetime.now(UTC)
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
                status=_agent_run_status_for_mode(payload.mode),
                started_at=now,
                summary=f"Auto-created from runtime {payload.mode.value} request.",
                metadata_={},
                created_at=now,
            )
            session.add(run)
            session.flush()

        trace_event = TraceEventRecord(
            agent_id=payload.agent_id,
            run_id=payload.run_id,
            external_event_id=payload.request_id,
            correlation_id=payload.correlation_id,
            event_type=TraceEventType.TOOL_CALL_REQUESTED,
            timestamp=now,
            summary=payload.action_summary,
            metadata_=_trace_event_metadata(payload),
            created_at=now,
        )
        session.add(trace_event)
        session.flush()

        policy_decision = _evaluate_and_persist_policy_decision(
            session,
            agent=agent,
            payload=payload,
            trace_event=trace_event,
        )

        human_approval = None
        if policy_decision.decision is PolicyDecisionValue.REQUIRE_HUMAN_REVIEW:
            human_approval = _create_human_approval_for_policy_decision(
                session,
                policy_decision,
            )

        session.commit()
        session.refresh(trace_event)
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

    return _runtime_decision_response(
        payload,
        trace_event=trace_event,
        policy_decision=policy_decision,
        human_approval=human_approval,
    )


def _runtime_trace_event_for_request(
    session: Session,
    payload: RuntimeToolCallDecisionRequest,
) -> TraceEventRecord | None:
    return session.scalar(
        select(TraceEventRecord).where(
            TraceEventRecord.agent_id == payload.agent_id,
            TraceEventRecord.run_id == payload.run_id,
            TraceEventRecord.external_event_id == payload.request_id,
        )
    )


def _runtime_decision_response(
    payload: RuntimeToolCallDecisionRequest,
    *,
    trace_event: TraceEventRecord,
    policy_decision: PolicyDecision,
    human_approval: HumanApproval | None,
) -> RuntimeToolCallDecisionResponse:
    decision = policy_decision.decision
    return RuntimeToolCallDecisionResponse(
        request_id=payload.request_id,
        agent_id=payload.agent_id,
        run_id=payload.run_id,
        tool_name=payload.tool_name,
        decision=decision,
        proceed=decision is PolicyDecisionValue.ALLOW,
        reason=policy_decision.reason,
        trace_event_id=trace_event.id,
        policy_decision_id=policy_decision.id,
        human_approval_id=human_approval.id if human_approval is not None else None,
    )


def _agent_run_status_for_mode(mode: RuntimeDecisionMode) -> str:
    if mode is RuntimeDecisionMode.ENFORCEMENT:
        return ENFORCED_RUN_STATUS
    return SIMULATED_RUN_STATUS


def _evaluate_and_persist_policy_decision(
    session: Session,
    *,
    agent: Agent,
    payload: RuntimeToolCallDecisionRequest,
    trace_event: TraceEventRecord,
) -> PolicyDecision:
    rules = load_active_policy_evaluation_rules(session)
    result = evaluate_policy(
        agent_context={"agent_id": payload.agent_id},
        action_context={"tool_name": payload.tool_name},
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
            request_id=payload.request_id,
        ),
    )


def _policy_decision_for_trace_event(
    session: Session,
    trace_event: TraceEventRecord,
) -> PolicyDecision | None:
    return session.scalar(
        select(PolicyDecision)
        .where(PolicyDecision.trace_event_id == trace_event.id)
        .order_by(PolicyDecision.created_at.desc(), PolicyDecision.id.desc())
    )


def _create_human_approval_for_policy_decision(
    session: Session,
    policy_decision: PolicyDecision,
) -> HumanApproval:
    if policy_decision.agent_id is None:
        raise ValueError("HumanApproval requires a PolicyDecision linked to an Agent.")

    approval = HumanApproval(
        agent_id=policy_decision.agent_id,
        policy_decision_id=policy_decision.id,
        status=HumanApprovalStatus.PENDING,
        requested_by_actor_type=DEVELOPMENT_ACTOR_TYPE,
        requested_by_actor_id=DEVELOPMENT_ACTOR_ID,
        reason=policy_decision.reason,
        created_at=datetime.now(UTC),
    )
    session.add(approval)
    session.flush()

    append_audit_log(
        session,
        event_type="human_approval_requested",
        actor_type=DEVELOPMENT_ACTOR_TYPE,
        actor_id=DEVELOPMENT_ACTOR_ID,
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
    policy_decision: PolicyDecision,
) -> HumanApproval | None:
    return session.scalar(
        select(HumanApproval)
        .where(HumanApproval.policy_decision_id == policy_decision.id)
        .order_by(HumanApproval.created_at.desc(), HumanApproval.id.desc())
    )


def _trace_event_metadata(
    payload: RuntimeToolCallDecisionRequest,
) -> dict[str, str | int | float | bool | None]:
    return {**payload.metadata, "tool_name": payload.tool_name}


def _policy_context_hash(
    *,
    agent_id: UUID,
    run_id: UUID,
    request_id: str,
) -> str:
    context = f"{agent_id}:{run_id}:{request_id}".encode()
    return f"sha256:{sha256(context).hexdigest()}"
