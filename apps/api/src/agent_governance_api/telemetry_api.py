from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from agent_governance_api.database import get_db_session
from agent_governance_api.models import Agent, AgentRunRecord, TraceEventRecord
from agent_governance_api.telemetry import TraceEvent, TraceEventIngestResponse

router = APIRouter(prefix="/telemetry", tags=["telemetry"])

AUTO_CREATED_RUN_STATUS = "observed"


@router.post(
    "/events",
    response_model=TraceEventIngestResponse,
    status_code=status.HTTP_201_CREATED,
)
def ingest_trace_event(
    payload: TraceEvent,
    response: Response,
    session: Session = Depends(get_db_session),
) -> TraceEventIngestResponse:
    agent = session.get(Agent, payload.agent_id)
    if agent is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found.",
        )

    external_event_id = payload.external_event_id or str(payload.id)
    existing_event = session.scalar(
        select(TraceEventRecord).where(
            TraceEventRecord.agent_id == payload.agent_id,
            TraceEventRecord.run_id == payload.run_id,
            TraceEventRecord.external_event_id == external_event_id,
        )
    )
    if existing_event is not None:
        response.status_code = status.HTTP_200_OK
        return _trace_event_response(existing_event)

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
    session.commit()
    session.refresh(trace_event)

    return _trace_event_response(trace_event)


def _trace_event_response(trace_event: TraceEventRecord) -> TraceEventIngestResponse:
    return TraceEventIngestResponse(
        id=trace_event.id,
        agent_id=trace_event.agent_id,
        run_id=trace_event.run_id,
        event_type=trace_event.event_type,
        created_at=trace_event.created_at,
    )
