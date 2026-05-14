from sqlalchemy.orm import Session

from agent_governance_api.database import (
    Base,
    create_database_engine,
    get_db_session,
)
from agent_governance_api.models import Agent


def test_database_engine_uses_postgresql_psycopg_url() -> None:
    engine = create_database_engine(
        "postgresql+psycopg://db-user@localhost:5432/test_control_plane"
    )

    try:
        assert engine.url.get_backend_name() == "postgresql"
        assert engine.url.get_driver_name() == "psycopg"
    finally:
        engine.dispose()


def test_declarative_base_includes_agent_table() -> None:
    assert Agent.__tablename__ in Base.metadata.tables


def test_db_session_dependency_yields_session_without_connecting() -> None:
    session_generator = get_db_session()
    session = next(session_generator)

    try:
        assert isinstance(session, Session)
    finally:
        session_generator.close()
