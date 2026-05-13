from functools import lru_cache
from os import getenv

from pydantic import BaseModel, Field

DEFAULT_DATABASE_URL = (
    "postgresql+psycopg://postgres@127.0.0.1:5432/"
    "agent_governance_control_plane?connect_timeout=5"
)


class Settings(BaseModel):
    app_name: str = Field(default="Agent Governance Control Plane API")
    app_version: str = Field(default="0.1.0")
    environment: str = Field(default="development")
    log_level: str = Field(default="INFO")
    database_url: str = Field(default=DEFAULT_DATABASE_URL)


@lru_cache
def get_settings() -> Settings:
    return Settings(
        app_name=getenv("AGCP_APP_NAME", "Agent Governance Control Plane API"),
        app_version=getenv("AGCP_APP_VERSION", "0.1.0"),
        environment=getenv("AGCP_ENVIRONMENT", "development"),
        log_level=getenv("AGCP_LOG_LEVEL", "INFO"),
        database_url=getenv("AGCP_DATABASE_URL", DEFAULT_DATABASE_URL),
    )
