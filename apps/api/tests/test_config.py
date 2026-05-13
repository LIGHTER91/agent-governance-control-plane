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
