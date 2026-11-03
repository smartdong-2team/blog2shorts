from fastapi.testclient import TestClient

from app import __version__
from app.core.config import Settings, get_settings
from app.main import app

client = TestClient(app)


def test_health_returns_ok() -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "app_env": get_settings().app_env, "version": __version__}


def test_health_uses_settings_dependency() -> None:
    app.dependency_overrides[get_settings] = lambda: Settings(_env_file=None, app_env="production")
    try:
        response = client.get("/api/v1/health")
    finally:
        app.dependency_overrides.clear()

    assert response.json()["app_env"] == "production"


def test_cors_allows_frontend_origin() -> None:
    response = client.get("/api/v1/health", headers={"Origin": "http://localhost:5173"})

    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_cors_rejects_unknown_origin() -> None:
    response = client.get("/api/v1/health", headers={"Origin": "https://evil.example.com"})

    assert "access-control-allow-origin" not in response.headers
