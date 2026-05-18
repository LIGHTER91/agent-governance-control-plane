from enum import StrEnum
from functools import lru_cache
from os import getenv

from pydantic import BaseModel, Field

DEFAULT_DATABASE_URL = (
    "postgresql+psycopg://postgres@127.0.0.1:5432/"
    "agent_governance_control_plane?connect_timeout=5"
)


class RuntimeFailureDefault(StrEnum):
    FAIL_CLOSED_DENY = "fail_closed_deny"
    FAIL_CLOSED_HUMAN_REVIEW = "fail_closed_human_review"
    RECORD_ONLY = "record_only"


class Settings(BaseModel):
    app_name: str = Field(default="Agent Governance Control Plane API")
    app_version: str = Field(default="0.1.0")
    environment: str = Field(default="development")
    log_level: str = Field(default="INFO")
    database_url: str = Field(default=DEFAULT_DATABASE_URL)
    runtime_enforcement_enabled: bool = Field(default=False)
    runtime_failure_default: RuntimeFailureDefault = Field(
        default=RuntimeFailureDefault.FAIL_CLOSED_DENY
    )


@lru_cache
def get_settings() -> Settings:
    return Settings(
        app_name=getenv("AGCP_APP_NAME", "Agent Governance Control Plane API"),
        app_version=getenv("AGCP_APP_VERSION", "0.1.0"),
        environment=getenv("AGCP_ENVIRONMENT", "development"),
        log_level=getenv("AGCP_LOG_LEVEL", "INFO"),
        database_url=getenv("AGCP_DATABASE_URL", DEFAULT_DATABASE_URL),
        runtime_enforcement_enabled=_get_bool_env(
            "AGCP_RUNTIME_ENFORCEMENT_ENABLED",
            default=False,
        ),
        runtime_failure_default=_get_runtime_failure_default_env(
            "AGCP_RUNTIME_FAILURE_DEFAULT",
            default=RuntimeFailureDefault.FAIL_CLOSED_DENY,
        ),
    )


def _get_bool_env(name: str, *, default: bool) -> bool:
    raw_value = getenv(name)
    if raw_value is None:
        return default

    normalized_value = raw_value.strip().lower()
    if normalized_value in {"1", "true", "yes", "on"}:
        return True
    if normalized_value in {"0", "false", "no", "off"}:
        return False

    raise ValueError(f"{name} must be one of: 1, true, yes, on, 0, false, no, off.")


def _get_runtime_failure_default_env(
    name: str,
    *,
    default: RuntimeFailureDefault,
) -> RuntimeFailureDefault:
    raw_value = getenv(name)
    if raw_value is None:
        return default

    normalized_value = raw_value.strip().lower()
    try:
        return RuntimeFailureDefault(normalized_value)
    except ValueError as exc:
        supported_values = ", ".join(item.value for item in RuntimeFailureDefault)
        raise ValueError(f"{name} must be one of: {supported_values}.") from exc
