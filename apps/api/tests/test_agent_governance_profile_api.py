from collections.abc import Callable, Iterator
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, update
from sqlalchemy import event as sqlalchemy_event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from agent_governance_api.auth import ActorContext, get_current_actor
from agent_governance_api.database import Base, get_db_session
from agent_governance_api.main import app
from agent_governance_api.models import (
    AccessGrant,
    AccessGrantStatus,
    AccessGrantSubjectType,
    AccessGrantTargetType,
    AccessGrantType,
    ActorType,
    Agent,
    AgentRunRecord,
    AgentStatus,
    AuditLog,
    Capability,
    CapabilityStatus,
    CapabilityType,
    DataSource,
    DataSourceStatus,
    DataSourceType,
    Environment,
    HumanApproval,
    HumanApprovalStatus,
    ModelAsset,
    ModelAssetStatus,
    ModelAssetType,
    ModelProvider,
    OwnerType,
    Policy,
    PolicyDecision,
    PolicyDecisionValue,
    PolicyRule,
    PolicyStatus,
    RiskLevel,
    TraceEventRecord,
    TraceEventType,
)

SessionFactory = Callable[[], Session]


@pytest.fixture()
def api_client() -> Iterator[tuple[TestClient, SessionFactory]]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @sqlalchemy_event.listens_for(engine, "connect")
    def enable_foreign_keys(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    testing_session_factory = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )

    def override_get_db_session() -> Iterator[Session]:
        with testing_session_factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_get_db_session
    app.dependency_overrides[get_current_actor] = lambda: auditor_actor()
    try:
        with TestClient(app) as client:
            yield client, testing_session_factory
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_agent_governance_profile_unknown_agent_returns_404(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, _ = api_client

    response = client.get(f"/agents/{uuid4()}/governance-profile")

    assert response.status_code == 404
    assert response.json() == {"detail": "Agent not found."}


def test_agent_governance_profile_empty_agent(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)

    response = client.get(f"/agents/{agent_id}/governance-profile")

    assert response.status_code == 200
    profile = response.json()
    assert profile["agent"]["id"] == str(agent_id)
    assert profile["owner"] == {
        "owner_type": "team",
        "owner_id": "team:ai-platform",
        "owner_name": "AI Platform",
        "owner_contact_email": "owner@example.invalid",
    }
    assert profile["environment"] == "development"
    assert profile["status"] == "active"
    assert profile["risk_level"] == "medium"
    assert profile["recent_activity"] == {"limit": 5, "items": []}
    assert profile["human_approvals"] == {
        "total_count": 0,
        "by_status": {},
        "recent": [],
    }
    assert profile["access_grants"] == []
    assert profile["policy_summary"] == {
        "policy_decision_count": 0,
        "referenced_policy_ids": [],
        "referenced_rule_ids": [],
    }
    assert profile["evidence_bundle"] == {
        "available": True,
        "export_path": f"/agents/{agent_id}/evidence-bundle",
        "export_format": "json",
        "access": "allowed",
        "contains_full_evidence": False,
    }


def test_agent_governance_profile_includes_agent_access_grants_and_targets(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    other_agent_id = create_agent(session_factory, name="Other assistant")
    seeded = seed_inventory_targets_and_access_grants(
        session_factory,
        agent_id=agent_id,
        other_agent_id=other_agent_id,
    )

    response = client.get(f"/agents/{agent_id}/governance-profile")

    assert response.status_code == 200
    profile = response.json()
    access_grants = profile["access_grants"]
    assert [grant["name"] for grant in access_grants] == [
        "Model access",
        "Source access",
        "Capability access",
    ]
    assert "Other agent access" not in {grant["name"] for grant in access_grants}
    assert [grant["target_type"] for grant in access_grants] == [
        "model_asset",
        "source",
        "capability",
    ]
    target_by_type = {grant["target_type"]: grant["target"] for grant in access_grants}
    assert target_by_type["capability"]["id"] == str(seeded.capability_id)
    assert target_by_type["capability"]["name"] == "Send support email"
    assert target_by_type["capability"]["inventory_type"] == "tool"
    assert target_by_type["source"]["id"] == str(seeded.source_id)
    assert target_by_type["source"]["name"] == "Support knowledge base"
    assert target_by_type["model_asset"]["id"] == str(seeded.model_asset_id)
    assert target_by_type["model_asset"]["provider"] == "openai"


def test_agent_governance_profile_includes_recent_activity_summary(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    seeded = seed_activity_records(session_factory, agent_id)

    response = client.get(f"/agents/{agent_id}/governance-profile")

    assert response.status_code == 200
    recent_activity = response.json()["recent_activity"]
    assert recent_activity["limit"] == 5
    assert [item["type"] for item in recent_activity["items"]] == [
        "audit_log",
        "human_approval",
        "policy_decision",
        "trace_event",
    ]
    trace_item = next(
        item for item in recent_activity["items"] if item["type"] == "trace_event"
    )
    assert trace_item["trace_event_id"] == str(seeded.trace_event_id)
    assert trace_item["metadata"] == {"tool_name": "send_email"}


def test_agent_governance_profile_includes_human_approval_summary(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    seeded = seed_activity_records(session_factory, agent_id)

    response = client.get(f"/agents/{agent_id}/governance-profile")

    assert response.status_code == 200
    approvals = response.json()["human_approvals"]
    assert approvals["total_count"] == 1
    assert approvals["by_status"] == {"pending": 1}
    [recent_approval] = approvals["recent"]
    assert recent_approval["id"] == str(seeded.human_approval_id)
    assert recent_approval["policy_decision_id"] == str(seeded.policy_decision_id)
    assert recent_approval["status"] == "pending"


def test_agent_governance_profile_includes_policy_summary(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    seeded = seed_activity_records(session_factory, agent_id)

    response = client.get(f"/agents/{agent_id}/governance-profile")

    assert response.status_code == 200
    policy_summary = response.json()["policy_summary"]
    assert policy_summary == {
        "policy_decision_count": 1,
        "referenced_policy_ids": [str(seeded.policy_id)],
        "referenced_rule_ids": [str(seeded.rule_id)],
    }


def test_agent_governance_profile_does_not_include_evidence_bundle_contents(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    seed_activity_records(session_factory, agent_id)

    response = client.get(f"/agents/{agent_id}/governance-profile")

    assert response.status_code == 200
    profile = response.json()
    assert "audit_logs" not in profile
    assert "agent_runs" not in profile
    assert "trace_events" not in profile
    assert "policy_decisions" not in profile
    assert profile["evidence_bundle"]["contains_full_evidence"] is False


def test_agent_governance_profile_filters_unsafe_metadata(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(session_factory)
    seeded_targets = seed_inventory_targets_and_access_grants(
        session_factory,
        agent_id=agent_id,
        other_agent_id=create_agent(session_factory, name="Other assistant"),
    )
    seeded_activity = seed_activity_records(session_factory, agent_id)
    inject_unsafe_metadata(session_factory, seeded_targets, seeded_activity)

    response = client.get(f"/agents/{agent_id}/governance-profile")

    assert response.status_code == 200
    profile = response.json()
    grant = next(
        grant
        for grant in profile["access_grants"]
        if grant["name"] == "Capability access"
    )
    trace_item = next(
        item
        for item in profile["recent_activity"]["items"]
        if item["type"] == "trace_event"
    )
    audit_item = next(
        item
        for item in profile["recent_activity"]["items"]
        if item["type"] == "audit_log"
    )
    assert grant["metadata"] == {"review_status": "approved"}
    assert trace_item["metadata"] == {"tool_name": "send_email"}
    assert audit_item["metadata"] == {"safe_note": "kept"}
    body_text = response.text
    assert "do-not-export" not in body_text
    assert "raw_payload" not in body_text
    assert "authorization" not in body_text
    assert "token" not in body_text


class SeededTargets:
    def __init__(
        self,
        *,
        capability_id: UUID,
        source_id: UUID,
        model_asset_id: UUID,
        access_grant_id: UUID,
    ) -> None:
        self.capability_id = capability_id
        self.source_id = source_id
        self.model_asset_id = model_asset_id
        self.access_grant_id = access_grant_id


class SeededActivity:
    def __init__(
        self,
        *,
        policy_id: UUID,
        rule_id: UUID,
        run_id: UUID,
        trace_event_id: UUID,
        policy_decision_id: UUID,
        human_approval_id: UUID,
        audit_log_id: UUID,
    ) -> None:
        self.policy_id = policy_id
        self.rule_id = rule_id
        self.run_id = run_id
        self.trace_event_id = trace_event_id
        self.policy_decision_id = policy_decision_id
        self.human_approval_id = human_approval_id
        self.audit_log_id = audit_log_id


def auditor_actor() -> ActorContext:
    return ActorContext(
        actor_type=ActorType.USER,
        actor_id="user:auditor-1",
        roles=("auditor",),
    )


def create_agent(
    session_factory: SessionFactory,
    *,
    name: str = "Support assistant",
) -> UUID:
    now = datetime(2026, 1, 15, 12, 0, tzinfo=UTC)
    with session_factory() as session:
        agent = Agent(
            name=name,
            description="Routes support requests.",
            owner_type=OwnerType.TEAM,
            owner_id="team:ai-platform",
            owner_name="AI Platform",
            owner_contact_email="owner@example.invalid",
            environment=Environment.DEVELOPMENT,
            status=AgentStatus.ACTIVE,
            risk_level=RiskLevel.MEDIUM,
            framework="LangGraph",
            created_at=now,
            updated_at=now,
        )
        session.add(agent)
        session.commit()
        return agent.id


def seed_inventory_targets_and_access_grants(
    session_factory: SessionFactory,
    *,
    agent_id: UUID,
    other_agent_id: UUID,
) -> SeededTargets:
    base_time = datetime(2026, 1, 15, 12, 0, tzinfo=UTC)
    capability_id = uuid4()
    source_id = uuid4()
    model_asset_id = uuid4()
    access_grant_id = uuid4()
    with session_factory() as session:
        session.add_all(
            [
                Capability(
                    id=capability_id,
                    name="Send support email",
                    description="Send governed support email.",
                    capability_type=CapabilityType.TOOL,
                    external_ref="tool:send_email",
                    status=CapabilityStatus.ACTIVE,
                    risk_level=RiskLevel.MEDIUM,
                    metadata_={"domain": "support"},
                    created_at=base_time,
                    updated_at=base_time,
                ),
                DataSource(
                    id=source_id,
                    name="Support knowledge base",
                    description="Support runbooks.",
                    source_type=DataSourceType.KNOWLEDGE_BASE,
                    external_ref="kb:support",
                    owner_type=OwnerType.TEAM,
                    owner_id="team:support",
                    owner_name="Support",
                    owner_contact_email=None,
                    status=DataSourceStatus.ACTIVE,
                    risk_level=RiskLevel.MEDIUM,
                    metadata_={"domain": "support"},
                    created_at=base_time,
                    updated_at=base_time,
                ),
                ModelAsset(
                    id=model_asset_id,
                    name="Support chat model",
                    description="Hosted support model.",
                    model_type=ModelAssetType.LLM,
                    provider=ModelProvider.OPENAI,
                    model_ref="support-chat",
                    version="2026-01",
                    owner_type=OwnerType.TEAM,
                    owner_id="team:ai-platform",
                    owner_name="AI Platform",
                    owner_contact_email=None,
                    status=ModelAssetStatus.ACTIVE,
                    risk_level=RiskLevel.MEDIUM,
                    metadata_={"domain": "support"},
                    created_at=base_time,
                    updated_at=base_time,
                ),
            ]
        )
        session.add_all(
            [
                access_grant(
                    access_grant_id,
                    agent_id=agent_id,
                    name="Capability access",
                    grant_type=AccessGrantType.CAPABILITY,
                    target_type=AccessGrantTargetType.CAPABILITY,
                    target_id=capability_id,
                    created_at=base_time,
                ),
                access_grant(
                    uuid4(),
                    agent_id=agent_id,
                    name="Source access",
                    grant_type=AccessGrantType.SOURCE,
                    target_type=AccessGrantTargetType.SOURCE,
                    target_id=source_id,
                    created_at=base_time + timedelta(minutes=5),
                ),
                access_grant(
                    uuid4(),
                    agent_id=agent_id,
                    name="Model access",
                    grant_type=AccessGrantType.MODEL,
                    target_type=AccessGrantTargetType.MODEL_ASSET,
                    target_id=model_asset_id,
                    created_at=base_time + timedelta(minutes=10),
                ),
                access_grant(
                    uuid4(),
                    agent_id=other_agent_id,
                    name="Other agent access",
                    grant_type=AccessGrantType.CAPABILITY,
                    target_type=AccessGrantTargetType.CAPABILITY,
                    target_id=capability_id,
                    created_at=base_time + timedelta(minutes=15),
                ),
            ]
        )
        session.commit()

    return SeededTargets(
        capability_id=capability_id,
        source_id=source_id,
        model_asset_id=model_asset_id,
        access_grant_id=access_grant_id,
    )


def access_grant(
    grant_id: UUID,
    *,
    agent_id: UUID,
    name: str,
    grant_type: AccessGrantType,
    target_type: AccessGrantTargetType,
    target_id: UUID,
    created_at: datetime,
) -> AccessGrant:
    return AccessGrant(
        id=grant_id,
        name=name,
        description="Governed access grant.",
        grant_type=grant_type,
        subject_type=AccessGrantSubjectType.AGENT,
        subject_id=agent_id,
        target_type=target_type,
        target_id=target_id,
        external_ref=None,
        status=AccessGrantStatus.ACTIVE,
        granted_by_actor_type=ActorType.DEVELOPMENT,
        granted_by_actor_id="dev-placeholder",
        reason="Governance review completed.",
        expires_at=None,
        risk_level=RiskLevel.MEDIUM,
        metadata_={"review_status": "approved"},
        created_at=created_at,
        updated_at=created_at,
    )


def seed_activity_records(
    session_factory: SessionFactory,
    agent_id: UUID,
) -> SeededActivity:
    base_time = datetime(2026, 1, 15, 13, 0, tzinfo=UTC)
    policy_id = uuid4()
    rule_id = uuid4()
    run_id = uuid4()
    trace_event_id = uuid4()
    policy_decision_id = uuid4()
    human_approval_id = uuid4()
    audit_log_id = uuid4()
    with session_factory() as session:
        session.add(
            Policy(
                id=policy_id,
                name="Support email policy",
                description="Require review for support email.",
                status=PolicyStatus.ACTIVE,
                created_at=base_time,
                updated_at=base_time,
            )
        )
        session.flush()
        session.add(
            PolicyRule(
                id=rule_id,
                policy_id=policy_id,
                name="Require support email review",
                description=None,
                condition=(
                    '{"decision":"require_human_review",'
                    '"reason":"Email review required.",'
                    '"tool_name":"send_email"}'
                ),
                created_at=base_time,
                updated_at=base_time,
            )
        )
        session.flush()
        session.add(
            AgentRunRecord(
                agent_id=agent_id,
                run_id=run_id,
                correlation_id="corr-profile",
                environment=Environment.DEVELOPMENT,
                status="observed",
                started_at=base_time,
                summary="Observed profile test run.",
                metadata_={"source": "profile-test"},
                created_at=base_time,
            )
        )
        session.flush()
        session.add(
            TraceEventRecord(
                id=trace_event_id,
                agent_id=agent_id,
                run_id=run_id,
                external_event_id="event-profile",
                correlation_id="corr-profile",
                event_type=TraceEventType.TOOL_CALL_REQUESTED,
                timestamp=base_time + timedelta(seconds=1),
                summary="Tool call requested.",
                metadata_={"tool_name": "send_email"},
                created_at=base_time + timedelta(seconds=1),
            )
        )
        session.flush()
        session.add(
            PolicyDecision(
                id=policy_decision_id,
                agent_id=agent_id,
                policy_id=policy_id,
                rule_id=rule_id,
                trace_event_id=trace_event_id,
                decision=PolicyDecisionValue.REQUIRE_HUMAN_REVIEW,
                reason="Email review required.",
                context_hash="sha256:profile-test",
                created_at=base_time + timedelta(seconds=2),
            )
        )
        session.flush()
        session.add(
            HumanApproval(
                id=human_approval_id,
                agent_id=agent_id,
                policy_decision_id=policy_decision_id,
                status=HumanApprovalStatus.PENDING,
                requested_by_actor_type=ActorType.DEVELOPMENT,
                requested_by_actor_id="dev-placeholder",
                reason="Review required for email tool.",
                created_at=base_time + timedelta(seconds=3),
            )
        )
        session.add(
            AuditLog(
                id=audit_log_id,
                event_type="human_approval_requested",
                actor_type=ActorType.DEVELOPMENT,
                actor_id="dev-placeholder",
                entity_type="human_approval",
                entity_id=str(human_approval_id),
                summary="Human approval requested.",
                metadata_={
                    "agent_id": str(agent_id),
                    "human_approval_id": str(human_approval_id),
                    "policy_decision_id": str(policy_decision_id),
                    "safe_note": "kept",
                },
                created_at=base_time + timedelta(seconds=4),
            )
        )
        session.commit()

    return SeededActivity(
        policy_id=policy_id,
        rule_id=rule_id,
        run_id=run_id,
        trace_event_id=trace_event_id,
        policy_decision_id=policy_decision_id,
        human_approval_id=human_approval_id,
        audit_log_id=audit_log_id,
    )


def inject_unsafe_metadata(
    session_factory: SessionFactory,
    seeded_targets: SeededTargets,
    seeded_activity: SeededActivity,
) -> None:
    with session_factory() as session:
        session.execute(
            update(AccessGrant)
            .where(AccessGrant.id == seeded_targets.access_grant_id)
            .values(
                metadata_={
                    "review_status": "approved",
                    "token": "do-not-export",
                }
            )
        )
        session.execute(
            update(TraceEventRecord)
            .where(TraceEventRecord.id == seeded_activity.trace_event_id)
            .values(
                metadata_={
                    "tool_name": "send_email",
                    "raw_payload": "do-not-export",
                }
            )
        )
        session.execute(
            update(AuditLog)
            .where(AuditLog.id == seeded_activity.audit_log_id)
            .values(
                metadata_={
                    "safe_note": "kept",
                    "authorization": "do-not-export",
                }
            )
        )
        session.commit()
