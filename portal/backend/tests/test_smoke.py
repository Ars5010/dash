from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


def test_health_no_db() -> None:
    with TestClient(app) as client:
        r = client.get("/api/health")
        assert r.status_code == 200
        assert r.json().get("ok") is True


def test_extension_example_ping() -> None:
    with TestClient(app) as client:
        r = client.get("/api/v1/ext/example/ping")
        assert r.status_code == 200
        data = r.json()
        assert data.get("module") == "example"
        assert data.get("ok") == "true"
