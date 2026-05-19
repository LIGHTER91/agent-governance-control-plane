from hashlib import sha256

import pytest

from agent_governance_api.config import RuntimeFailureDefault, get_settings


def test_database_url_comes_from_environment(monkeypatch) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv(
        "AGCP_DATABASE_URL",
        "postgresql+psycopg://db-user@localhost:5432/test_control_plane",
    )

    try:
        settings = get_settings()

        assert (
            settings.database_url
            == "postgresql+psycopg://db-user@localhost:5432/test_control_plane"
        )
    finally:
        get_settings.cache_clear()


def test_runtime_enforcement_is_disabled_by_default(monkeypatch) -> None:
    get_settings.cache_clear()
    monkeypatch.delenv("AGCP_RUNTIME_ENFORCEMENT_ENABLED", raising=False)

    try:
        settings = get_settings()

        assert settings.runtime_enforcement_enabled is False
    finally:
        get_settings.cache_clear()


def test_require_service_auth_is_disabled_by_default(monkeypatch) -> None:
    get_settings.cache_clear()
    monkeypatch.delenv("AGCP_REQUIRE_SERVICE_AUTH", raising=False)

    try:
        settings = get_settings()

        assert settings.require_service_auth is False
    finally:
        get_settings.cache_clear()


def test_runtime_failure_default_is_fail_closed_deny_by_default(monkeypatch) -> None:
    get_settings.cache_clear()
    monkeypatch.delenv("AGCP_RUNTIME_FAILURE_DEFAULT", raising=False)

    try:
        settings = get_settings()

        assert (
            settings.runtime_failure_default is RuntimeFailureDefault.FAIL_CLOSED_DENY
        )
    finally:
        get_settings.cache_clear()


def test_runtime_enforcement_can_be_enabled_from_environment(monkeypatch) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("AGCP_RUNTIME_ENFORCEMENT_ENABLED", "true")

    try:
        settings = get_settings()

        assert settings.runtime_enforcement_enabled is True
    finally:
        get_settings.cache_clear()


def test_require_service_auth_can_be_enabled_from_environment(monkeypatch) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("AGCP_REQUIRE_SERVICE_AUTH", "true")

    try:
        settings = get_settings()

        assert settings.require_service_auth is True
    finally:
        get_settings.cache_clear()


@pytest.mark.parametrize(
    ("env_value", "expected"),
    [
        ("fail_closed_deny", RuntimeFailureDefault.FAIL_CLOSED_DENY),
        (
            "fail_closed_human_review",
            RuntimeFailureDefault.FAIL_CLOSED_HUMAN_REVIEW,
        ),
        ("record_only", RuntimeFailureDefault.RECORD_ONLY),
    ],
)
def test_valid_runtime_failure_default_values_are_accepted(
    monkeypatch,
    env_value: str,
    expected: RuntimeFailureDefault,
) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("AGCP_RUNTIME_FAILURE_DEFAULT", env_value)

    try:
        settings = get_settings()

        assert settings.runtime_failure_default is expected
    finally:
        get_settings.cache_clear()


@pytest.mark.parametrize("env_value", ["invalid", "fail_open_allow"])
def test_invalid_runtime_failure_default_values_are_rejected(
    monkeypatch,
    env_value: str,
) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("AGCP_RUNTIME_FAILURE_DEFAULT", env_value)

    try:
        with pytest.raises(
            ValueError,
            match=(
                "AGCP_RUNTIME_FAILURE_DEFAULT must be one of: "
                "fail_closed_deny, fail_closed_human_review, record_only."
            ),
        ):
            get_settings()
    finally:
        get_settings.cache_clear()


def test_service_actor_api_keys_are_empty_by_default(monkeypatch) -> None:
    get_settings.cache_clear()
    monkeypatch.delenv("AGCP_SERVICE_ACTOR_API_KEYS", raising=False)

    try:
        settings = get_settings()

        assert settings.service_actor_api_keys == ()
    finally:
        get_settings.cache_clear()


def test_service_actor_scopes_are_empty_by_default(monkeypatch) -> None:
    get_settings.cache_clear()
    monkeypatch.delenv("AGCP_SERVICE_ACTOR_SCOPES", raising=False)

    try:
        settings = get_settings()

        assert settings.service_actor_scopes == ()
    finally:
        get_settings.cache_clear()


def test_service_actor_api_keys_are_loaded_from_hashed_config(monkeypatch) -> None:
    get_settings.cache_clear()
    key_hash = sha256(b"local-test-service-key").hexdigest()
    monkeypatch.setenv(
        "AGCP_SERVICE_ACTOR_API_KEYS",
        f"service:runtime-test=sha256:{key_hash}",
    )

    try:
        settings = get_settings()

        [configured_key] = settings.service_actor_api_keys
        assert configured_key.actor_id == "service:runtime-test"
        assert configured_key.key_hash == f"sha256:{key_hash}"
    finally:
        get_settings.cache_clear()


def test_service_actor_scopes_are_loaded_from_config(monkeypatch) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv(
        "AGCP_SERVICE_ACTOR_SCOPES",
        (
            "service:runtime-test=runtime:decision,runtime:resume;"
            "service:telemetry-test=telemetry:write"
        ),
    )

    try:
        settings = get_settings()

        runtime_scopes, telemetry_scopes = settings.service_actor_scopes
        assert runtime_scopes.actor_id == "service:runtime-test"
        assert runtime_scopes.scopes == ("runtime:decision", "runtime:resume")
        assert telemetry_scopes.actor_id == "service:telemetry-test"
        assert telemetry_scopes.scopes == ("telemetry:write",)
    finally:
        get_settings.cache_clear()


@pytest.mark.parametrize(
    "env_value",
    [
        "runtime-test=telemetry:write",
        "service:runtime-test=",
        "service:runtime-test=policy:write",
    ],
)
def test_invalid_service_actor_scopes_config_is_rejected(
    monkeypatch,
    env_value: str,
) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("AGCP_SERVICE_ACTOR_SCOPES", env_value)

    try:
        with pytest.raises(ValueError, match="AGCP_SERVICE_ACTOR_SCOPES"):
            get_settings()
    finally:
        get_settings.cache_clear()


@pytest.mark.parametrize(
    "env_value",
    [
        "runtime-test=sha256:"
        "0000000000000000000000000000000000000000000000000000000000000000",
        "service:runtime-test=local-test-service-key",
        "service:runtime-test=sha256:not-hex",
    ],
)
def test_invalid_service_actor_api_key_config_is_rejected(
    monkeypatch,
    env_value: str,
) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("AGCP_SERVICE_ACTOR_API_KEYS", env_value)

    try:
        with pytest.raises(ValueError, match="AGCP_SERVICE_ACTOR_API_KEYS"):
            get_settings()
    finally:
        get_settings.cache_clear()
