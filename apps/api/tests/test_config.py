from agent_governance_api.config import get_settings


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


def test_runtime_enforcement_can_be_enabled_from_environment(monkeypatch) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("AGCP_RUNTIME_ENFORCEMENT_ENABLED", "true")

    try:
        settings = get_settings()

        assert settings.runtime_enforcement_enabled is True
    finally:
        get_settings.cache_clear()
