from sqlalchemy.orm import Session

from agent_governance_api.database import (
    Base,
    create_database_engine,
    get_db_session,
)


def test_database_engine_uses_postgresql_psycopg_url() -> None:
    engine = create_database_engine(
        "postgresql+psycopg://db-user@localhost:5432/test_control_plane"
    )

    try:
        assert engine.url.get_backend_name() == "postgresql"
        assert engine.url.get_driver_name() == "psycopg"
    finally:
        engine.dispose()


def test_declarative_base_has_empty_metadata_for_baseline() -> None:
    assert Base.metadata.tables == {}


def test_db_session_dependency_yields_session_without_connecting() -> None:
    session_generator = get_db_session()
    session = next(session_generator)

    try:
        assert isinstance(session, Session)
    finally:
        session_generator.close()
