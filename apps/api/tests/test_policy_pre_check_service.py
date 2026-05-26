from collections.abc import Iterator
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from agent_governance_api.database import Base
from agent_governance_api.models import (
    CheckResult,
    CheckResultConfidence,
    CheckResultOutcome,
    CheckResultTargetType,
    CheckTool,
    CheckToolStatus,
    CheckToolType,
    OwnerType,
)
from agent_governance_api.policy_pre_checks import persist_check_result


@pytest.fixture()
def session() -> Iterator[Session]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )
    with session_factory() as db_session:
        yield db_session
    Base.metadata.drop_all(engine)
    engine.dispose()


def test_persist_check_result_creates_metadata_only_result(session: Session) -> None:
    check_tool = create_check_tool(session)
    agent_id = uuid4()
    target_id = uuid4()

    check_result = persist_check_result(
        session,
        check_tool_id=check_tool.id,
        agent_id=agent_id,
        target_type=CheckResultTargetType.DATA_USAGE_PROFILE,
        target_id=target_id,
        outcome=CheckResultOutcome.PASS,
        confidence=CheckResultConfidence.HIGH,
        summary="Data Usage Profile allows requested purpose.",
        reason="Purpose is listed in allowed_purposes.",
        metadata={"purpose": "customer_support_answering"},
    )

    stored = session.scalar(
        select(CheckResult).where(CheckResult.id == check_result.id)
    )
    assert stored is not None
    assert stored.check_tool_id == check_tool.id
    assert stored.check_tool.name == "data_usage_profile_checker"
    assert stored.agent_id == agent_id
    assert stored.target_id == target_id
    assert stored.outcome is CheckResultOutcome.PASS
    assert stored.confidence is CheckResultConfidence.HIGH
    assert stored.metadata_ == {"purpose": "customer_support_answering"}


def test_persist_check_result_does_not_commit_caller_transaction(
    session: Session,
) -> None:
    check_tool = create_check_tool(session)

    persist_check_result(
        session,
        check_tool_id=check_tool.id,
        target_type=CheckResultTargetType.SOURCE,
        outcome=CheckResultOutcome.UNKNOWN,
        summary="Source review status is unknown.",
        metadata={},
    )

    assert session.in_transaction()


def test_persist_check_result_rejects_blank_summary(session: Session) -> None:
    check_tool = create_check_tool(session)

    with pytest.raises(ValueError, match="non-empty"):
        persist_check_result(
            session,
            check_tool_id=check_tool.id,
            target_type=CheckResultTargetType.SOURCE,
            outcome=CheckResultOutcome.UNKNOWN,
            summary=" ",
        )


def test_persist_check_result_rejects_unsafe_metadata(session: Session) -> None:
    check_tool = create_check_tool(session)

    with pytest.raises(ValueError, match="unsafe key"):
        persist_check_result(
            session,
            check_tool_id=check_tool.id,
            target_type=CheckResultTargetType.SOURCE,
            outcome=CheckResultOutcome.UNKNOWN,
            summary="Source review status is unknown.",
            metadata={"raw_payload_ref": "do-not-store"},
        )


def test_persist_check_result_redacts_sensitive_assignments(
    session: Session,
) -> None:
    check_tool = create_check_tool(session)

    check_result = persist_check_result(
        session,
        check_tool_id=check_tool.id,
        target_type=CheckResultTargetType.EXTERNAL,
        outcome=CheckResultOutcome.ERROR,
        summary="Checker unavailable api_key=do-not-store",
        reason="authorization=Bearer do-not-store",
    )

    assert "do-not-store" not in check_result.summary
    assert "do-not-store" not in str(check_result.reason)
    assert "[REDACTED]" in check_result.summary
    assert "[REDACTED]" in str(check_result.reason)


def create_check_tool(session: Session) -> CheckTool:
    check_tool = CheckTool(
        id=uuid4(),
        name="data_usage_profile_checker",
        description="Checks declared Source usage metadata.",
        tool_type=CheckToolType.DATA_USAGE_PROFILE_CHECK,
        status=CheckToolStatus.ACTIVE,
        owner_type=OwnerType.TEAM,
        owner_id="team:governance",
        owner_name="Governance",
        metadata_={"source": "internal_metadata"},
    )
    session.add(check_tool)
    session.flush()
    assert isinstance(check_tool.id, UUID)
    return check_tool
