from enum import StrEnum
from functools import lru_cache
from os import getenv

from pydantic import BaseModel, Field

DEFAULT_DATABASE_URL = (
    "postgresql+psycopg://postgres@127.0.0.1:5432/"
    "agent_governance_control_plane?connect_timeout=5"
)
SERVICE_ACTOR_API_KEY_HASH_PREFIX = "sha256:"
SERVICE_ACTOR_API_KEY_HASH_HEX_LENGTH = 64


class RuntimeFailureDefault(StrEnum):
    FAIL_CLOSED_DENY = "fail_closed_deny"
    FAIL_CLOSED_HUMAN_REVIEW = "fail_closed_human_review"
    RECORD_ONLY = "record_only"


class ServiceActorApiKey(BaseModel):
    actor_id: str
    key_hash: str


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
    service_actor_api_keys: tuple[ServiceActorApiKey, ...] = Field(
        default_factory=tuple
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
        service_actor_api_keys=_get_service_actor_api_keys_env(
            "AGCP_SERVICE_ACTOR_API_KEYS",
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


def _get_service_actor_api_keys_env(name: str) -> tuple[ServiceActorApiKey, ...]:
    raw_value = getenv(name)
    if raw_value is None or not raw_value.strip():
        return ()

    entries: list[ServiceActorApiKey] = []
    for raw_entry in raw_value.split(","):
        entry = raw_entry.strip()
        if not entry:
            continue

        if "=" not in entry:
            raise ValueError(
                f"{name} entries must use service:<stable-id>=sha256:<digest>."
            )

        actor_id, key_hash = (part.strip() for part in entry.split("=", 1))
        _validate_service_actor_id(name, actor_id)
        normalized_key_hash = _validate_service_actor_key_hash(name, key_hash)
        entries.append(
            ServiceActorApiKey(actor_id=actor_id, key_hash=normalized_key_hash)
        )

    return tuple(entries)


def _validate_service_actor_id(name: str, actor_id: str) -> None:
    if not actor_id.startswith("service:") or actor_id == "service:":
        raise ValueError(f"{name} actor ids must use service:<stable-id>.")


def _validate_service_actor_key_hash(name: str, key_hash: str) -> str:
    normalized_key_hash = key_hash.lower()
    if not normalized_key_hash.startswith(SERVICE_ACTOR_API_KEY_HASH_PREFIX):
        raise ValueError(f"{name} key hashes must use sha256:<digest>.")

    digest = normalized_key_hash.removeprefix(SERVICE_ACTOR_API_KEY_HASH_PREFIX)
    if len(digest) != SERVICE_ACTOR_API_KEY_HASH_HEX_LENGTH or any(
        char not in "0123456789abcdef" for char in digest
    ):
        raise ValueError(f"{name} key hashes must use sha256:<64 hex chars>.")

    return normalized_key_hash
