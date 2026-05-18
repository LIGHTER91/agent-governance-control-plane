from datetime import UTC, datetime
from hashlib import sha256
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from agent_governance_api.audit import append_audit_log
from agent_governance_api.config import RuntimeFailureDefault, Settings, get_settings
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
from agent_governance_api.policy_evaluator import (
    PolicyEvaluationResult,
    evaluate_policy,
)
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
POLICY_EVALUATION_FAILURE_ERRORS = (
    UnsupportedPolicyRuleConditionError,
    TypeError,
    ValueError,
)


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
            record_only_failure_response = (
                _runtime_record_only_response_for_trace_event(
                    payload,
                    trace_event=existing_event,
                )
            )
            if record_only_failure_response is not None:
                return record_only_failure_response
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

        human_approval = None
        record_only_failure_reason = None
        try:
            evaluation_result = _evaluate_runtime_policy(
                session,
                agent=agent,
                payload=payload,
            )
        except POLICY_EVALUATION_FAILURE_ERRORS:
            (
                policy_decision,
                human_approval,
                record_only_failure_reason,
            ) = _apply_runtime_failure_default(
                session,
                payload=payload,
                trace_event=trace_event,
                failure_default=settings.runtime_failure_default,
            )
        else:
            policy_decision = _persist_runtime_policy_decision(
                session,
                payload=payload,
                trace_event=trace_event,
                evaluation_result=evaluation_result,
            )
            if policy_decision.decision is PolicyDecisionValue.REQUIRE_HUMAN_REVIEW:
                human_approval = _create_human_approval_for_policy_decision(
                    session,
                    policy_decision,
                )

        session.commit()
        session.refresh(trace_event)
        if policy_decision is not None:
            session.refresh(policy_decision)
        if human_approval is not None:
            session.refresh(human_approval)
    except Exception:
        session.rollback()
        raise

    if policy_decision is None:
        return _runtime_record_only_failure_response(
            payload,
            trace_event=trace_event,
            reason=record_only_failure_reason,
        )

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


def _runtime_record_only_response_for_trace_event(
    payload: RuntimeToolCallDecisionRequest,
    *,
    trace_event: TraceEventRecord,
) -> RuntimeToolCallDecisionResponse | None:
    if trace_event.metadata_.get("runtime_failure_default") != (
        RuntimeFailureDefault.RECORD_ONLY.value
    ):
        return None
    if trace_event.metadata_.get("runtime_failure_category") != "policy_evaluation":
        return None

    return _runtime_record_only_failure_response(
        payload,
        trace_event=trace_event,
        reason=_runtime_failure_reason(RuntimeFailureDefault.RECORD_ONLY),
    )


def _runtime_record_only_failure_response(
    payload: RuntimeToolCallDecisionRequest,
    *,
    trace_event: TraceEventRecord,
    reason: str | None,
) -> RuntimeToolCallDecisionResponse:
    return RuntimeToolCallDecisionResponse(
        request_id=payload.request_id,
        agent_id=payload.agent_id,
        run_id=payload.run_id,
        tool_name=payload.tool_name,
        decision=PolicyDecisionValue.NOT_APPLICABLE,
        proceed=False,
        reason=reason or _runtime_failure_reason(RuntimeFailureDefault.RECORD_ONLY),
        trace_event_id=trace_event.id,
        policy_decision_id=None,
        human_approval_id=None,
    )


def _agent_run_status_for_mode(mode: RuntimeDecisionMode) -> str:
    if mode is RuntimeDecisionMode.ENFORCEMENT:
        return ENFORCED_RUN_STATUS
    return SIMULATED_RUN_STATUS


def _evaluate_runtime_policy(
    session: Session,
    *,
    agent: Agent,
    payload: RuntimeToolCallDecisionRequest,
) -> PolicyEvaluationResult:
    rules = load_active_policy_evaluation_rules(session)
    return evaluate_policy(
        agent_context={"agent_id": payload.agent_id},
        action_context={"tool_name": payload.tool_name},
        environment=agent.environment,
        risk_level=agent.risk_level,
        rules=rules,
    )


def _persist_runtime_policy_decision(
    session: Session,
    *,
    payload: RuntimeToolCallDecisionRequest,
    trace_event: TraceEventRecord,
    evaluation_result: PolicyEvaluationResult,
) -> PolicyDecision:
    return persist_policy_decision(
        session,
        agent_id=payload.agent_id,
        evaluation_result=evaluation_result,
        trace_event_id=trace_event.id,
        context_hash=_policy_context_hash(
            agent_id=payload.agent_id,
            run_id=payload.run_id,
            request_id=payload.request_id,
        ),
    )


def _apply_runtime_failure_default(
    session: Session,
    *,
    payload: RuntimeToolCallDecisionRequest,
    trace_event: TraceEventRecord,
    failure_default: RuntimeFailureDefault,
) -> tuple[PolicyDecision | None, HumanApproval | None, str | None]:
    effective_failure_default = failure_default
    if (
        failure_default is RuntimeFailureDefault.RECORD_ONLY
        and payload.mode is RuntimeDecisionMode.ENFORCEMENT
    ):
        effective_failure_default = RuntimeFailureDefault.FAIL_CLOSED_DENY

    _mark_trace_event_policy_evaluation_failure(
        trace_event,
        failure_default=effective_failure_default,
    )

    if effective_failure_default is RuntimeFailureDefault.RECORD_ONLY:
        session.flush()
        return None, None, _runtime_failure_reason(effective_failure_default)

    decision = {
        RuntimeFailureDefault.FAIL_CLOSED_DENY: PolicyDecisionValue.DENY,
        RuntimeFailureDefault.FAIL_CLOSED_HUMAN_REVIEW: (
            PolicyDecisionValue.REQUIRE_HUMAN_REVIEW
        ),
    }[effective_failure_default]
    policy_decision = _persist_runtime_policy_decision(
        session,
        payload=payload,
        trace_event=trace_event,
        evaluation_result=PolicyEvaluationResult(
            decision=decision,
            reason=_runtime_failure_reason(effective_failure_default),
            agent_id=str(payload.agent_id),
        ),
    )

    human_approval = None
    if policy_decision.decision is PolicyDecisionValue.REQUIRE_HUMAN_REVIEW:
        human_approval = _create_human_approval_for_policy_decision(
            session,
            policy_decision,
        )

    return policy_decision, human_approval, None


def _mark_trace_event_policy_evaluation_failure(
    trace_event: TraceEventRecord,
    *,
    failure_default: RuntimeFailureDefault,
) -> None:
    trace_event.metadata_ = {
        **trace_event.metadata_,
        "runtime_failure_category": "policy_evaluation",
        "runtime_failure_default": failure_default.value,
    }


def _runtime_failure_reason(failure_default: RuntimeFailureDefault) -> str:
    if failure_default is RuntimeFailureDefault.FAIL_CLOSED_HUMAN_REVIEW:
        return (
            "Policy evaluation failed; runtime failure policy "
            "fail_closed_human_review requested human review."
        )
    if failure_default is RuntimeFailureDefault.RECORD_ONLY:
        return (
            "Policy evaluation failed; runtime failure policy record_only recorded "
            "the failure in simulation mode."
        )
    return (
        "Policy evaluation failed; runtime failure policy fail_closed_deny selected "
        "deny."
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
