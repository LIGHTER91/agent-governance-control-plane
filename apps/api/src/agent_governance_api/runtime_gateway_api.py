from datetime import UTC, datetime
from hashlib import sha256
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from agent_governance_api.audit import append_audit_log
from agent_governance_api.auth import (
    ROLE_AUDITOR,
    ROLE_PLATFORM_ADMIN,
    ROLE_REVIEWER,
    SCOPE_RUNTIME_DECISION,
    SCOPE_RUNTIME_RESUME,
    ActorContext,
    get_current_actor,
    get_current_integration_actor,
    require_role,
    require_scope,
    require_service_actor_fine_grained_scope,
)
from agent_governance_api.config import RuntimeFailureDefault, Settings, get_settings
from agent_governance_api.database import get_db_session
from agent_governance_api.models import (
    ActorType,
    Agent,
    AgentRunRecord,
    CheckResult,
    HumanApproval,
    HumanApprovalStatus,
    PolicyDecision,
    PolicyDecisionValue,
    TraceEventRecord,
    TraceEventType,
)
from agent_governance_api.openapi_examples import (
    RUNTIME_TOOL_CALL_ACTIVITY_OPENAPI,
    RUNTIME_TOOL_CALL_DECISION_OPENAPI,
    RUNTIME_TOOL_CALL_RESUME_OPENAPI,
)
from agent_governance_api.policy_decision_service import persist_policy_decision
from agent_governance_api.policy_evaluator import (
    PolicyEvaluationResult,
    evaluate_policy,
)
from agent_governance_api.policy_rule_adapter import (
    UnsupportedPolicyRuleConditionError,
    load_active_policy_evaluation_rules,
)
from agent_governance_api.runtime_activity import build_runtime_tool_call_activity
from agent_governance_api.runtime_gateway import (
    RuntimeDecisionMode,
    RuntimeToolCallActivityItem,
    RuntimeToolCallDecisionRequest,
    RuntimeToolCallDecisionResponse,
    RuntimeToolCallResumeRequest,
    RuntimeToolCallResumeResponse,
)
from agent_governance_api.runtime_inventory_context import (
    ResolvedRuntimeInventoryContext,
    resolve_runtime_inventory_context,
)
from agent_governance_api.runtime_metadata_pre_checks import (
    run_runtime_metadata_pre_checks,
)

router = APIRouter(prefix="/runtime", tags=["runtime"])

SIMULATED_RUN_STATUS = "simulated"
ENFORCED_RUN_STATUS = "enforced"
RESUME_CHECKED_RUN_STATUS = "resume_checked"
RESUME_FINE_GRAINED_RUNTIME_MODE = "enforcement"
POLICY_EVALUATION_FAILURE_ERRORS = (
    UnsupportedPolicyRuleConditionError,
    TypeError,
    ValueError,
)


@router.get(
    "/tool-calls/activity",
    response_model=list[RuntimeToolCallActivityItem],
    openapi_extra=RUNTIME_TOOL_CALL_ACTIVITY_OPENAPI,
)
def list_runtime_tool_call_activity(
    session: Session = Depends(get_db_session),
    actor: ActorContext = Depends(get_current_actor),
) -> list[RuntimeToolCallActivityItem]:
    """Return Runtime Gateway tool-call activity sorted newest first."""

    _require_runtime_activity_reader(actor)
    return build_runtime_tool_call_activity(session)


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
    actor: ActorContext = Depends(get_current_integration_actor),
) -> RuntimeToolCallDecisionResponse:
    require_scope(actor, SCOPE_RUNTIME_DECISION)

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
    require_service_actor_fine_grained_scope(
        actor,
        agent_id=payload.agent_id,
        environment=agent.environment,
        runtime_mode=payload.mode,
        tool_name=payload.tool_name,
        settings=settings,
        session=session,
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

        inventory_context = resolve_runtime_inventory_context(
            session,
            agent_id=agent.id,
            payload=payload,
        )
        trace_event = TraceEventRecord(
            agent_id=payload.agent_id,
            run_id=payload.run_id,
            external_event_id=payload.request_id,
            correlation_id=payload.correlation_id,
            event_type=TraceEventType.TOOL_CALL_REQUESTED,
            timestamp=now,
            summary=payload.action_summary,
            metadata_=_trace_event_metadata(
                payload,
                inventory_context=inventory_context,
            ),
            created_at=now,
        )
        session.add(trace_event)
        session.flush()

        human_approval = None
        evaluation_result: PolicyEvaluationResult | None = None
        pre_check_results: list[CheckResult] = []
        record_only_failure_reason = None
        try:
            if settings.runtime_metadata_pre_checks_enabled:
                candidate_evaluation_result = _evaluate_runtime_policy(
                    session,
                    agent=agent,
                    payload=payload,
                    inventory_context=inventory_context,
                    ignore_check_result_conditions=True,
                )
                pre_check_results = run_runtime_metadata_pre_checks(
                    session,
                    payload=payload,
                    trace_event=trace_event,
                    policy_decision_id=None,
                    policy_rule_ids=candidate_evaluation_result.matched_rule_ids,
                )

            evaluation_result = _evaluate_runtime_policy(
                session,
                agent=agent,
                payload=payload,
                inventory_context=inventory_context,
                check_results=pre_check_results,
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
                actor=actor,
            )
            if policy_decision is not None:
                for check_result in pre_check_results:
                    check_result.policy_decision_id = policy_decision.id
        else:
            policy_decision = _persist_runtime_policy_decision(
                session,
                payload=payload,
                trace_event=trace_event,
                evaluation_result=evaluation_result,
            )
            for check_result in pre_check_results:
                check_result.policy_decision_id = policy_decision.id
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


@router.post(
    "/tool-calls/resume",
    response_model=RuntimeToolCallResumeResponse,
    status_code=status.HTTP_201_CREATED,
    openapi_extra=RUNTIME_TOOL_CALL_RESUME_OPENAPI,
)
def resume_runtime_tool_call(
    payload: RuntimeToolCallResumeRequest,
    response: Response,
    session: Session = Depends(get_db_session),
    actor: ActorContext = Depends(get_current_integration_actor),
) -> RuntimeToolCallResumeResponse:
    require_scope(actor, SCOPE_RUNTIME_RESUME)

    agent = session.get(Agent, payload.agent_id)
    if agent is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found.",
        )
    require_service_actor_fine_grained_scope(
        actor,
        agent_id=payload.agent_id,
        environment=agent.environment,
        runtime_mode=RESUME_FINE_GRAINED_RUNTIME_MODE,
        tool_name=payload.tool_name,
        session=session,
    )

    approval = _human_approval_or_404(session, payload.human_approval_id)
    policy_decision = _policy_decision_or_404(session, payload.policy_decision_id)
    _ensure_resume_chain_matches_request(
        session,
        payload=payload,
        approval=approval,
        policy_decision=policy_decision,
    )

    existing_event = _runtime_trace_event_for_resume(session, payload)
    if existing_event is not None:
        response.status_code = status.HTTP_200_OK
        return _runtime_resume_response_for_trace_event(existing_event)

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
                status=RESUME_CHECKED_RUN_STATUS,
                started_at=now,
                summary="Auto-created from runtime resume request.",
                metadata_={},
                created_at=now,
            )
            session.add(run)
            session.flush()

        decision = _resume_decision_for_approval_status(approval.status)
        proceed = decision is PolicyDecisionValue.ALLOW
        reason = _resume_reason_for_approval_status(approval.status)
        trace_event = TraceEventRecord(
            agent_id=payload.agent_id,
            run_id=payload.run_id,
            external_event_id=payload.resume_id,
            correlation_id=payload.correlation_id,
            event_type=TraceEventType.TOOL_CALL_RESUME_REQUESTED,
            timestamp=now,
            summary="Runtime tool call resume checked.",
            metadata_=_resume_trace_event_metadata(
                payload,
                decision=decision,
                proceed=proceed,
                reason=reason,
                approval=approval,
            ),
            created_at=now,
        )
        session.add(trace_event)
        session.flush()

        _append_runtime_resume_audit_log(
            session,
            payload=payload,
            trace_event=trace_event,
            decision=decision,
            proceed=proceed,
            reason=reason,
            approval=approval,
            actor=actor,
        )

        session.commit()
        session.refresh(trace_event)
    except Exception:
        session.rollback()
        raise

    return RuntimeToolCallResumeResponse(
        resume_id=payload.resume_id,
        original_request_id=payload.original_request_id,
        agent_id=payload.agent_id,
        run_id=payload.run_id,
        tool_name=payload.tool_name,
        decision=decision,
        proceed=proceed,
        reason=reason,
        human_approval_status=approval.status,
        trace_event_id=trace_event.id,
        policy_decision_id=policy_decision.id,
        human_approval_id=approval.id,
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


def _runtime_trace_event_for_resume(
    session: Session,
    payload: RuntimeToolCallResumeRequest,
) -> TraceEventRecord | None:
    trace_event = session.scalar(
        select(TraceEventRecord).where(
            TraceEventRecord.agent_id == payload.agent_id,
            TraceEventRecord.run_id == payload.run_id,
            TraceEventRecord.external_event_id == payload.resume_id,
        )
    )
    if trace_event is None:
        return None
    if trace_event.event_type is not TraceEventType.TOOL_CALL_RESUME_REQUESTED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Resume id conflicts with an existing trace event.",
        )
    return trace_event


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


def _runtime_resume_response_for_trace_event(
    trace_event: TraceEventRecord,
) -> RuntimeToolCallResumeResponse:
    metadata = trace_event.metadata_
    try:
        return RuntimeToolCallResumeResponse(
            resume_id=trace_event.external_event_id,
            original_request_id=str(metadata["original_request_id"]),
            agent_id=trace_event.agent_id,
            run_id=trace_event.run_id,
            tool_name=str(metadata["tool_name"]),
            decision=PolicyDecisionValue(str(metadata["resume_decision"])),
            proceed=_metadata_bool(metadata["proceed"]),
            reason=str(metadata["resume_reason"]),
            human_approval_status=HumanApprovalStatus(
                str(metadata["human_approval_status"])
            ),
            trace_event_id=trace_event.id,
            policy_decision_id=UUID(str(metadata["policy_decision_id"])),
            human_approval_id=UUID(str(metadata["human_approval_id"])),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Runtime resume records are incomplete for this request.",
        ) from exc


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


def _human_approval_or_404(
    session: Session,
    human_approval_id: UUID,
) -> HumanApproval:
    approval = session.get(HumanApproval, human_approval_id)
    if approval is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Human approval not found.",
        )
    return approval


def _policy_decision_or_404(
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


def _ensure_resume_chain_matches_request(
    session: Session,
    *,
    payload: RuntimeToolCallResumeRequest,
    approval: HumanApproval,
    policy_decision: PolicyDecision,
) -> None:
    if approval.agent_id != payload.agent_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Human approval does not belong to the requested agent.",
        )
    if policy_decision.agent_id != payload.agent_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Policy decision does not belong to the requested agent.",
        )
    if approval.policy_decision_id != payload.policy_decision_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Human approval is not linked to the requested policy decision.",
        )

    if policy_decision.trace_event_id is None:
        return

    original_trace_event = session.get(TraceEventRecord, policy_decision.trace_event_id)
    if original_trace_event is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Original trace event for policy decision was not found.",
        )
    if original_trace_event.agent_id != payload.agent_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Original trace event does not belong to the requested agent.",
        )
    if original_trace_event.run_id != payload.run_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Original trace event does not belong to the requested run.",
        )
    if original_trace_event.external_event_id != payload.original_request_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Original request id does not match the original trace event.",
        )

    original_tool_name = original_trace_event.metadata_.get("tool_name")
    if isinstance(original_tool_name, str) and original_tool_name != payload.tool_name:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Tool name does not match the original trace event.",
        )


def _resume_decision_for_approval_status(
    approval_status: HumanApprovalStatus,
) -> PolicyDecisionValue:
    if approval_status is HumanApprovalStatus.APPROVED:
        return PolicyDecisionValue.ALLOW
    if approval_status is HumanApprovalStatus.PENDING:
        return PolicyDecisionValue.REQUIRE_HUMAN_REVIEW
    return PolicyDecisionValue.DENY


def _resume_reason_for_approval_status(approval_status: HumanApprovalStatus) -> str:
    if approval_status is HumanApprovalStatus.APPROVED:
        return "Human approval is approved and the resume context matches."
    if approval_status is HumanApprovalStatus.PENDING:
        return "Human approval is still pending."
    if approval_status is HumanApprovalStatus.REJECTED:
        return "Human approval was rejected."
    if approval_status is HumanApprovalStatus.CANCELLED:
        return "Human approval was cancelled."
    return "Human approval is expired."


def _resume_trace_event_metadata(
    payload: RuntimeToolCallResumeRequest,
    *,
    decision: PolicyDecisionValue,
    proceed: bool,
    reason: str,
    approval: HumanApproval,
) -> dict[str, str | int | float | bool | None]:
    return {
        **payload.metadata,
        "tool_name": payload.tool_name,
        "action_ref": payload.action_ref,
        "original_request_id": payload.original_request_id,
        "human_approval_id": str(payload.human_approval_id),
        "policy_decision_id": str(payload.policy_decision_id),
        "resume_decision": decision.value,
        "proceed": proceed,
        "resume_reason": reason,
        "human_approval_status": approval.status.value,
    }


def _append_runtime_resume_audit_log(
    session: Session,
    *,
    payload: RuntimeToolCallResumeRequest,
    trace_event: TraceEventRecord,
    decision: PolicyDecisionValue,
    proceed: bool,
    reason: str,
    approval: HumanApproval,
    actor: ActorContext,
) -> None:
    append_audit_log(
        session,
        event_type="runtime_tool_call_resume_checked",
        actor_type=actor.actor_type,
        actor_id=actor.actor_id,
        entity_type="agent",
        entity_id=str(payload.agent_id),
        summary="Runtime tool call resume checked.",
        metadata={
            "agent_id": str(payload.agent_id),
            "run_id": str(payload.run_id),
            "resume_id": payload.resume_id,
            "original_request_id": payload.original_request_id,
            "tool_name": payload.tool_name,
            "action_ref": payload.action_ref,
            "human_approval_id": str(payload.human_approval_id),
            "policy_decision_id": str(payload.policy_decision_id),
            "trace_event_id": str(trace_event.id),
            "decision": decision.value,
            "proceed": proceed,
            "reason": reason,
            "human_approval_status": approval.status.value,
        },
    )


def _metadata_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    raise ValueError("Expected boolean metadata value.")


def _evaluate_runtime_policy(
    session: Session,
    *,
    agent: Agent,
    payload: RuntimeToolCallDecisionRequest,
    inventory_context: ResolvedRuntimeInventoryContext,
    check_results: list[CheckResult] | None = None,
    ignore_check_result_conditions: bool = False,
) -> PolicyEvaluationResult:
    rules = load_active_policy_evaluation_rules(session)
    return evaluate_policy(
        agent_context={"agent_id": payload.agent_id},
        action_context=_runtime_policy_action_context(
            payload,
            inventory_context=inventory_context,
            check_results=check_results or [],
        ),
        environment=agent.environment,
        risk_level=agent.risk_level,
        rules=rules,
        ignore_check_result_conditions=ignore_check_result_conditions,
    )


def _runtime_policy_action_context(
    payload: RuntimeToolCallDecisionRequest,
    *,
    inventory_context: ResolvedRuntimeInventoryContext,
    check_results: list[CheckResult],
) -> dict[str, object]:
    context: dict[str, object] = {
        "tool_name": payload.tool_name,
    }
    if payload.action_type is not None:
        context["action_type"] = payload.action_type
    if payload.capability_id is not None:
        context["capability_id"] = payload.capability_id
    if payload.source_ids:
        context["source_ids"] = tuple(payload.source_ids)
    if payload.model_id is not None:
        context["model_id"] = payload.model_id
    if payload.purpose is not None:
        context["purpose"] = payload.purpose
    if payload.data_classification is not None:
        context["data_classification"] = payload.data_classification
        context["declared_data_classification"] = payload.data_classification
    if payload.contains_personal_data is not None:
        context["contains_personal_data"] = payload.contains_personal_data
    if payload.contains_sensitive_data is not None:
        context["contains_sensitive_data"] = payload.contains_sensitive_data
    if check_results:
        context["check_results"] = [
            _check_result_policy_context(check_result) for check_result in check_results
        ]
    context.update(inventory_context.policy_context)
    return context


def _check_result_policy_context(
    check_result: CheckResult,
) -> dict[str, str]:
    context = {
        "check_outcome": check_result.outcome.value,
        "check_target_type": check_result.target_type.value,
        "check_tool_id": str(check_result.check_tool_id),
    }
    if check_result.target_id is not None:
        context["check_target_id"] = str(check_result.target_id)
    if check_result.confidence is not None:
        context["check_confidence"] = check_result.confidence.value

    metadata = check_result.metadata_ or {}
    check_type = metadata.get("policy_check_step_check_type")
    if not isinstance(check_type, str):
        check_type = metadata.get("check_type")
    if isinstance(check_type, str):
        context["check_type"] = check_type
    return context


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
    actor: ActorContext,
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
            actor=actor,
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
    policy_decision: PolicyDecision,
) -> HumanApproval | None:
    return session.scalar(
        select(HumanApproval)
        .where(HumanApproval.policy_decision_id == policy_decision.id)
        .order_by(HumanApproval.created_at.desc(), HumanApproval.id.desc())
    )


def _trace_event_metadata(
    payload: RuntimeToolCallDecisionRequest,
    *,
    inventory_context: ResolvedRuntimeInventoryContext,
) -> dict[str, str | int | float | bool | None]:
    metadata: dict[str, str | int | float | bool | None] = {
        **payload.metadata,
        "tool_name": payload.tool_name,
    }
    metadata.update(_runtime_context_metadata(payload))
    metadata.update(inventory_context.trace_metadata)
    return metadata


def _runtime_context_metadata(
    payload: RuntimeToolCallDecisionRequest,
) -> dict[str, str | int | float | bool | None]:
    metadata: dict[str, str | int | float | bool | None] = {}
    if payload.action_type is not None:
        metadata["action_type"] = payload.action_type
    if payload.capability_id is not None:
        metadata["capability_id"] = str(payload.capability_id)
    if payload.source_ids:
        metadata["source_ids"] = ",".join(
            str(source_id) for source_id in payload.source_ids
        )
    if payload.model_id is not None:
        metadata["model_id"] = str(payload.model_id)
    if payload.purpose is not None:
        metadata["purpose"] = payload.purpose
    if payload.data_classification is not None:
        metadata["data_classification"] = payload.data_classification.value
    if payload.contains_personal_data is not None:
        metadata["contains_personal_data"] = payload.contains_personal_data
    if payload.contains_sensitive_data is not None:
        metadata["contains_sensitive_data"] = payload.contains_sensitive_data
    return metadata


def _require_runtime_activity_reader(actor: ActorContext) -> None:
    if actor.actor_type is ActorType.SERVICE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Service actors cannot view Runtime activity.",
        )

    require_role(actor, (ROLE_REVIEWER, ROLE_AUDITOR, ROLE_PLATFORM_ADMIN))


def _policy_context_hash(
    *,
    agent_id: UUID,
    run_id: UUID,
    request_id: str,
) -> str:
    context = f"{agent_id}:{run_id}:{request_id}".encode()
    return f"sha256:{sha256(context).hexdigest()}"
