from enum import StrEnum
from functools import lru_cache
from json import JSONDecodeError, loads
from os import getenv

from pydantic import BaseModel, Field, field_validator

DEFAULT_DATABASE_URL = (
    "postgresql+psycopg://postgres@127.0.0.1:5432/"
    "agent_governance_control_plane?connect_timeout=5"
)
DEFAULT_CORS_ALLOWED_ORIGINS = (
    "http://localhost:3000",
    "http://127.0.0.1:3000",
)
DEFAULT_DEV_ACTOR_ID = "dev-placeholder"
SERVICE_ACTOR_API_KEY_HASH_PREFIX = "sha256:"
SERVICE_ACTOR_API_KEY_HASH_HEX_LENGTH = 64
SUPPORTED_DEV_ACTOR_ROLES = frozenset(
    {
        "auditor",
        "reviewer",
        "platform_admin",
    }
)
SUPPORTED_SERVICE_ACTOR_SCOPES = frozenset(
    {
        "agent:read",
        "evidence:read",
        "human_approval:read",
        "human_approval:review",
        "runtime:decision",
        "runtime:resume",
        "telemetry:write",
    }
)
SERVICE_ACTOR_FINE_GRAINED_WILDCARD = "*"
SUPPORTED_SERVICE_ACTOR_SCOPE_RULE_KEYS = frozenset(
    {
        "agent_ids",
        "environments",
        "runtime_modes",
        "tool_names",
    }
)
SUPPORTED_SERVICE_ACTOR_SCOPE_ENVIRONMENTS = frozenset(
    {
        "development",
        "staging",
        "production",
    }
)
SUPPORTED_SERVICE_ACTOR_RUNTIME_MODES = frozenset(
    {
        "simulation",
        "enforcement",
    }
)


class RuntimeFailureDefault(StrEnum):
    FAIL_CLOSED_DENY = "fail_closed_deny"
    FAIL_CLOSED_HUMAN_REVIEW = "fail_closed_human_review"
    RECORD_ONLY = "record_only"


class ServiceActorApiKey(BaseModel):
    actor_id: str
    key_hash: str


class ServiceActorScopes(BaseModel):
    actor_id: str
    scopes: tuple[str, ...]


class ServiceActorScopeRule(BaseModel):
    actor_id: str
    agent_ids: tuple[str, ...] = Field(default_factory=tuple)
    environments: tuple[str, ...] = Field(default_factory=tuple)
    runtime_modes: tuple[str, ...] = Field(default_factory=tuple)
    tool_names: tuple[str, ...] = Field(default_factory=tuple)


class Settings(BaseModel):
    app_name: str = Field(default="Agent Governance Control Plane API")
    app_version: str = Field(default="0.1.0")
    environment: str = Field(default="development")
    log_level: str = Field(default="INFO")
    database_url: str = Field(default=DEFAULT_DATABASE_URL)
    cors_allowed_origins: tuple[str, ...] = Field(default=DEFAULT_CORS_ALLOWED_ORIGINS)
    runtime_enforcement_enabled: bool = Field(default=False)
    runtime_metadata_pre_checks_enabled: bool = Field(default=False)
    runtime_failure_default: RuntimeFailureDefault = Field(
        default=RuntimeFailureDefault.FAIL_CLOSED_DENY
    )
    require_service_auth: bool = Field(default=False)
    service_actor_api_keys: tuple[ServiceActorApiKey, ...] = Field(
        default_factory=tuple
    )
    service_actor_scopes: tuple[ServiceActorScopes, ...] = Field(default_factory=tuple)
    service_actor_scope_rules: tuple[ServiceActorScopeRule, ...] = Field(
        default_factory=tuple
    )
    service_actor_registry_enabled: bool = Field(default=False)
    dev_actor_id: str = Field(default=DEFAULT_DEV_ACTOR_ID)
    dev_actor_roles: tuple[str, ...] = Field(default_factory=tuple)
    dev_actor_display_name: str | None = Field(default=None)

    @field_validator("dev_actor_roles")
    @classmethod
    def validate_dev_actor_roles(cls, roles: tuple[str, ...]) -> tuple[str, ...]:
        return _validate_dev_actor_roles("AGCP_DEV_ACTOR_ROLES", roles)


@lru_cache
def get_settings() -> Settings:
    return Settings(
        app_name=getenv("AGCP_APP_NAME", "Agent Governance Control Plane API"),
        app_version=getenv("AGCP_APP_VERSION", "0.1.0"),
        environment=getenv("AGCP_ENVIRONMENT", "development"),
        log_level=getenv("AGCP_LOG_LEVEL", "INFO"),
        database_url=getenv("AGCP_DATABASE_URL", DEFAULT_DATABASE_URL),
        cors_allowed_origins=_get_csv_env(
            "AGCP_CORS_ALLOWED_ORIGINS",
            default=DEFAULT_CORS_ALLOWED_ORIGINS,
        ),
        runtime_enforcement_enabled=_get_bool_env(
            "AGCP_RUNTIME_ENFORCEMENT_ENABLED",
            default=False,
        ),
        runtime_metadata_pre_checks_enabled=_get_bool_env(
            "AGCP_RUNTIME_METADATA_PRE_CHECKS_ENABLED",
            default=False,
        ),
        runtime_failure_default=_get_runtime_failure_default_env(
            "AGCP_RUNTIME_FAILURE_DEFAULT",
            default=RuntimeFailureDefault.FAIL_CLOSED_DENY,
        ),
        require_service_auth=_get_bool_env(
            "AGCP_REQUIRE_SERVICE_AUTH",
            default=False,
        ),
        service_actor_api_keys=_get_service_actor_api_keys_env(
            "AGCP_SERVICE_ACTOR_API_KEYS",
        ),
        service_actor_scopes=_get_service_actor_scopes_env(
            "AGCP_SERVICE_ACTOR_SCOPES",
        ),
        service_actor_scope_rules=_get_service_actor_scope_rules_env(
            "AGCP_SERVICE_ACTOR_SCOPE_RULES",
        ),
        service_actor_registry_enabled=_get_bool_env(
            "AGCP_SERVICE_ACTOR_REGISTRY_ENABLED",
            default=False,
        ),
        dev_actor_id=getenv("AGCP_DEV_ACTOR_ID", DEFAULT_DEV_ACTOR_ID).strip()
        or DEFAULT_DEV_ACTOR_ID,
        dev_actor_roles=_get_dev_actor_roles_env("AGCP_DEV_ACTOR_ROLES"),
        dev_actor_display_name=_get_optional_env("AGCP_DEV_ACTOR_DISPLAY_NAME"),
    )


def _get_csv_env(name: str, *, default: tuple[str, ...]) -> tuple[str, ...]:
    raw_value = getenv(name)
    if raw_value is None:
        return default

    values = tuple(
        dict.fromkeys(
            value.strip().rstrip("/") for value in raw_value.split(",") if value.strip()
        )
    )
    return values


def _get_optional_env(name: str) -> str | None:
    raw_value = getenv(name)
    if raw_value is None:
        return None

    value = raw_value.strip()
    return value or None


def _get_dev_actor_roles_env(name: str) -> tuple[str, ...]:
    raw_value = getenv(name)
    if raw_value is None or not raw_value.strip():
        return ()

    roles = tuple(
        dict.fromkeys(role.strip() for role in raw_value.split(",") if role.strip())
    )
    return _validate_dev_actor_roles(name, roles)


def _validate_dev_actor_roles(name: str, roles: tuple[str, ...]) -> tuple[str, ...]:
    unsupported_roles = sorted(
        role for role in roles if role not in SUPPORTED_DEV_ACTOR_ROLES
    )
    if unsupported_roles:
        supported_values = ", ".join(sorted(SUPPORTED_DEV_ACTOR_ROLES))
        unsupported_values = ", ".join(unsupported_roles)
        raise ValueError(
            f"{name} unsupported roles: {unsupported_values}. "
            f"Supported roles: {supported_values}."
        )

    return roles


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


def _get_service_actor_scopes_env(name: str) -> tuple[ServiceActorScopes, ...]:
    raw_value = getenv(name)
    if raw_value is None or not raw_value.strip():
        return ()

    entries: list[ServiceActorScopes] = []
    for raw_entry in raw_value.split(";"):
        entry = raw_entry.strip()
        if not entry:
            continue

        if "=" not in entry:
            raise ValueError(
                f"{name} entries must use service:<stable-id>=scope[,scope]."
            )

        actor_id, raw_scopes = (part.strip() for part in entry.split("=", 1))
        _validate_service_actor_id(name, actor_id)
        scopes = _validate_service_actor_scopes(name, raw_scopes)
        entries.append(ServiceActorScopes(actor_id=actor_id, scopes=scopes))

    return tuple(entries)


def _get_service_actor_scope_rules_env(
    name: str,
) -> tuple[ServiceActorScopeRule, ...]:
    raw_value = getenv(name)
    if raw_value is None or not raw_value.strip():
        return ()

    try:
        parsed_value = loads(raw_value)
    except JSONDecodeError as exc:
        raise ValueError(f"{name} must be a JSON object.") from exc

    if not isinstance(parsed_value, dict):
        raise ValueError(f"{name} must be a JSON object.")

    entries: list[ServiceActorScopeRule] = []
    for raw_actor_id, raw_rule in parsed_value.items():
        if not isinstance(raw_actor_id, str):
            raise ValueError(f"{name} actor ids must be strings.")
        actor_id = raw_actor_id.strip()
        _validate_service_actor_id(name, actor_id)

        if not isinstance(raw_rule, dict):
            raise ValueError(f"{name} entries must be JSON objects.")

        unsupported_keys = sorted(
            key
            for key in raw_rule
            if key not in SUPPORTED_SERVICE_ACTOR_SCOPE_RULE_KEYS
        )
        if unsupported_keys:
            unsupported_values = ", ".join(unsupported_keys)
            raise ValueError(f"{name} unsupported fields: {unsupported_values}.")

        agent_ids = _validate_service_actor_scope_rule_values(
            name,
            raw_rule.get("agent_ids"),
            field_name="agent_ids",
        )
        environments = _validate_service_actor_scope_rule_values(
            name,
            raw_rule.get("environments"),
            field_name="environments",
            supported_values=SUPPORTED_SERVICE_ACTOR_SCOPE_ENVIRONMENTS,
            normalize=True,
        )
        runtime_modes = _validate_service_actor_scope_rule_values(
            name,
            raw_rule.get("runtime_modes"),
            field_name="runtime_modes",
            supported_values=SUPPORTED_SERVICE_ACTOR_RUNTIME_MODES,
            normalize=True,
        )
        tool_names = _validate_service_actor_scope_rule_values(
            name,
            raw_rule.get("tool_names"),
            field_name="tool_names",
        )

        if not any((agent_ids, environments, runtime_modes, tool_names)):
            raise ValueError(
                f"{name} entries must include at least one fine-grained restriction."
            )

        entries.append(
            ServiceActorScopeRule(
                actor_id=actor_id,
                agent_ids=agent_ids,
                environments=environments,
                runtime_modes=runtime_modes,
                tool_names=tool_names,
            )
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


def _validate_service_actor_scopes(name: str, raw_scopes: str) -> tuple[str, ...]:
    scopes = tuple(
        dict.fromkeys(scope.strip() for scope in raw_scopes.split(",") if scope.strip())
    )
    if not scopes:
        raise ValueError(f"{name} entries must include at least one scope.")

    unsupported_scopes = sorted(
        scope for scope in scopes if scope not in SUPPORTED_SERVICE_ACTOR_SCOPES
    )
    if unsupported_scopes:
        supported_values = ", ".join(sorted(SUPPORTED_SERVICE_ACTOR_SCOPES))
        unsupported_values = ", ".join(unsupported_scopes)
        raise ValueError(
            f"{name} unsupported scopes: {unsupported_values}. "
            f"Supported scopes: {supported_values}."
        )

    return scopes


def _validate_service_actor_scope_rule_values(
    name: str,
    raw_values: object,
    *,
    field_name: str,
    supported_values: frozenset[str] | None = None,
    normalize: bool = False,
) -> tuple[str, ...]:
    if raw_values is None:
        return ()
    if not isinstance(raw_values, list):
        raise ValueError(f"{name}.{field_name} must be a list of strings.")

    values: list[str] = []
    for raw_value in raw_values:
        if not isinstance(raw_value, str) or not raw_value.strip():
            raise ValueError(f"{name}.{field_name} values must be non-empty strings.")

        value = raw_value.strip()
        if normalize:
            value = value.lower()

        if (
            supported_values is not None
            and value != SERVICE_ACTOR_FINE_GRAINED_WILDCARD
            and value not in supported_values
        ):
            supported = ", ".join(sorted(supported_values))
            raise ValueError(
                f"{name}.{field_name} unsupported value: {value}. "
                f"Supported values: {supported}, {SERVICE_ACTOR_FINE_GRAINED_WILDCARD}."
            )

        values.append(value)

    return tuple(dict.fromkeys(values))
