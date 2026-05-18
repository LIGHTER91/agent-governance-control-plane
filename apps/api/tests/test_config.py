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
