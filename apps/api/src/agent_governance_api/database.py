from collections.abc import Generator

from sqlalchemy import MetaData, create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from agent_governance_api.config import get_settings


class Base(DeclarativeBase):
    metadata = MetaData()


def create_database_engine(database_url: str | None = None) -> Engine:
    return create_engine(
        database_url or get_settings().database_url,
        pool_pre_ping=True,
    )


engine = create_database_engine()
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


def get_db_session() -> Generator[Session, None, None]:
    with SessionLocal() as session:
        yield session
