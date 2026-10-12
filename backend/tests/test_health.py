import pytest


def test_health_returns_exact_json(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["content-type"] == "application/json"


@pytest.mark.parametrize("origin", ["http://127.0.0.1:5173", "http://localhost:5173"])
def test_cors_allows_configured_local_origins(client, origin):
    response = client.get("/api/health", headers={"Origin": origin})
    assert response.headers["access-control-allow-origin"] == origin


@pytest.mark.parametrize("origin", ["https://example.com", "http://localhost:5174", "null"])
def test_cors_does_not_allow_other_origins(client, origin):
    response = client.get("/api/health", headers={"Origin": origin})
    assert "access-control-allow-origin" not in response.headers


def test_cors_preflight(client):
    response = client.options("/api/health", headers={
        "Origin": "http://127.0.0.1:5173",
        "Access-Control-Request-Method": "GET",
        "Access-Control-Request-Headers": "Accept",
    })
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:5173"


def test_cors_rejects_unconfigured_preflight(client):
    response = client.options("/api/health", headers={
        "Origin": "https://example.com",
        "Access-Control-Request-Method": "GET",
    })
    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers
