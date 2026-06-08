from fastapi.testclient import TestClient

from agent_governance_api.main import app


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
