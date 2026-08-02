"""Smoke tests — no database required. The health check tolerates a missing DB."""
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app


def test_counties_parse():
    assert "Dallas" in settings.counties
    assert settings.buybox_min_acres == 5
    assert settings.buybox_max_all_in == 5_000_000


def test_health_and_jobs_registered():
    with TestClient(app) as client:
        resp = client.get("/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert body["service"] == "realtydog"
        # All 7 scheduled jobs should register on startup.
        assert body["jobs"] == 7
