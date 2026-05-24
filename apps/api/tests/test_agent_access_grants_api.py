from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

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
    AgentStatus,
    Environment,
    OwnerType,
    RiskLevel,
)

SessionFactory = Callable[[], Session]


@pytest.fixture()
def api_client() -> Iterator[tuple[TestClient, SessionFactory]]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
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
    try:
        with TestClient(app) as client:
            yield client, testing_session_factory
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_list_agent_access_grants_returns_inventory_targets_newest_first(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = uuid4()
    other_agent_id = uuid4()
    seed_agent(session_factory, agent_id, name="Support assistant")
    seed_agent(session_factory, other_agent_id, name="Risk assistant")
    seed_access_grant(
        session_factory,
        agent_id=agent_id,
        name="Capability grant",
        grant_type=AccessGrantType.CAPABILITY,
        target_type=AccessGrantTargetType.CAPABILITY,
        created_at=datetime(2026, 1, 15, 12, 0, tzinfo=UTC),
    )
    seed_access_grant(
        session_factory,
        agent_id=agent_id,
        name="Source grant",
        grant_type=AccessGrantType.SOURCE,
        target_type=AccessGrantTargetType.SOURCE,
        created_at=datetime(2026, 1, 15, 12, 5, tzinfo=UTC),
    )
    seed_access_grant(
        session_factory,
        agent_id=agent_id,
        name="Model grant",
        grant_type=AccessGrantType.MODEL,
        target_type=AccessGrantTargetType.MODEL_ASSET,
        created_at=datetime(2026, 1, 15, 12, 10, tzinfo=UTC),
    )
    seed_access_grant(
        session_factory,
        agent_id=other_agent_id,
        name="Other agent grant",
        grant_type=AccessGrantType.CAPABILITY,
        target_type=AccessGrantTargetType.CAPABILITY,
        created_at=datetime(2026, 1, 15, 12, 15, tzinfo=UTC),
    )

    response = client.get(f"/agents/{agent_id}/access-grants")

    assert response.status_code == 200
    body = response.json()
    assert [grant["name"] for grant in body] == [
        "Model grant",
        "Source grant",
        "Capability grant",
    ]
    assert [grant["target_type"] for grant in body] == [
        "model_asset",
        "source",
        "capability",
    ]
    assert {grant["subject_id"] for grant in body} == {str(agent_id)}
    assert "Other agent grant" not in {grant["name"] for grant in body}


def test_list_agent_access_grants_filters_by_status(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = uuid4()
    seed_agent(session_factory, agent_id)
    seed_access_grant(
        session_factory,
        agent_id=agent_id,
        name="Active grant",
        grant_type=AccessGrantType.CAPABILITY,
        target_type=AccessGrantTargetType.CAPABILITY,
        status=AccessGrantStatus.ACTIVE,
    )
    seed_access_grant(
        session_factory,
        agent_id=agent_id,
        name="Suspended grant",
        grant_type=AccessGrantType.SOURCE,
        target_type=AccessGrantTargetType.SOURCE,
        status=AccessGrantStatus.SUSPENDED,
    )

    response = client.get(f"/agents/{agent_id}/access-grants?status=active")

    assert response.status_code == 200
    assert [grant["name"] for grant in response.json()] == ["Active grant"]


def test_list_agent_access_grants_filters_by_target_type(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = uuid4()
    seed_agent(session_factory, agent_id)
    seed_access_grant(
        session_factory,
        agent_id=agent_id,
        name="Capability grant",
        grant_type=AccessGrantType.CAPABILITY,
        target_type=AccessGrantTargetType.CAPABILITY,
    )
    seed_access_grant(
        session_factory,
        agent_id=agent_id,
        name="Source grant",
        grant_type=AccessGrantType.SOURCE,
        target_type=AccessGrantTargetType.SOURCE,
    )

    response = client.get(f"/agents/{agent_id}/access-grants?target_type=source")

    assert response.status_code == 200
    body = response.json()
    assert [grant["name"] for grant in body] == ["Source grant"]
    assert {grant["target_type"] for grant in body} == {"source"}


def test_list_agent_access_grants_unknown_agent_returns_404_without_grants(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    missing_agent_id = uuid4()
    seed_access_grant(
        session_factory,
        agent_id=missing_agent_id,
        name="Grant for missing agent id",
        grant_type=AccessGrantType.CAPABILITY,
        target_type=AccessGrantTargetType.CAPABILITY,
    )

    response = client.get(f"/agents/{missing_agent_id}/access-grants")

    assert response.status_code == 404
    assert response.json() == {"detail": "Agent not found."}
    assert "Grant for missing agent id" not in response.text


def seed_agent(
    session_factory: SessionFactory,
    agent_id: UUID,
    *,
    name: str = "Support assistant",
) -> None:
    now = datetime(2026, 1, 15, 12, 0, tzinfo=UTC)
    with session_factory() as session:
        session.add(
            Agent(
                id=agent_id,
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
        )
        session.commit()


def seed_access_grant(
    session_factory: SessionFactory,
    *,
    agent_id: UUID,
    name: str,
    grant_type: AccessGrantType,
    target_type: AccessGrantTargetType,
    status: AccessGrantStatus = AccessGrantStatus.ACTIVE,
    created_at: datetime | None = None,
) -> None:
    now = created_at or datetime(2026, 1, 15, 12, 0, tzinfo=UTC)
    with session_factory() as session:
        session.add(
            AccessGrant(
                id=uuid4(),
                name=name,
                description="Governed access grant for API test.",
                grant_type=grant_type,
                subject_type=AccessGrantSubjectType.AGENT,
                subject_id=agent_id,
                target_type=target_type,
                target_id=uuid4(),
                external_ref=None,
                status=status,
                granted_by_actor_type=ActorType.DEVELOPMENT,
                granted_by_actor_id="dev-placeholder",
                reason="Governance review completed.",
                expires_at=None,
                risk_level=RiskLevel.MEDIUM,
                metadata_={"review_status": "approved"},
                created_at=now,
                updated_at=now,
            )
        )
        session.commit()
