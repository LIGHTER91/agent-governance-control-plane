from fastapi.testclient import TestClient

from agent_governance_api.auth import ActorContext, get_current_actor
from agent_governance_api.main import app
from agent_governance_api.models import ActorType


def test_health_returns_ok() -> None:
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "Agent Governance Control Plane API",
        "environment": "development",
    }


def test_local_web_origin_can_preflight_backend_requests() -> None:
    client = TestClient(app)

    response = client.options(
        "/agents",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert "GET" in response.headers["access-control-allow-methods"]


def test_me_returns_local_development_actor_without_secrets() -> None:
    client = TestClient(app)

    response = client.get("/me")

    assert response.status_code == 200
    assert response.json() == {
        "actor_type": "development",
        "actor_id": "dev-placeholder",
        "roles": [],
        "display_name": None,
        "environment": "development",
        "dev_mode_caveat": (
            "Local development actor fallback; this is not enterprise auth."
        ),
    }
    assert "api_key" not in response.json()
    assert "token" not in response.json()
    assert "credential" not in response.json()


def test_me_returns_overridden_actor_roles() -> None:
    client = TestClient(app)
    app.dependency_overrides[get_current_actor] = lambda: ActorContext(
        actor_type=ActorType.USER,
        actor_id="user:reviewer-1",
        roles=("reviewer", "auditor"),
    )

    try:
        response = client.get("/me")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "actor_type": "user",
        "actor_id": "user:reviewer-1",
        "roles": ["reviewer", "auditor"],
        "display_name": None,
        "environment": "development",
        "dev_mode_caveat": None,
    }
