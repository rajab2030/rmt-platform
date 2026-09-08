"""RMT-PROD P1 (O3) -- the unauthenticated GET /health probe."""
import pytest
from fastapi.testclient import TestClient

import app.main as main_app
from app.homelab.operational_loop import operational_loop


@pytest.fixture
def client():
    with TestClient(main_app.app) as c:
        yield c


def test_health_is_open_and_ok(client):
    r = client.get("/health")  # no auth header
    assert r.status_code == 200
    body = r.json()
    assert body["status"] in ("ok", "degraded")
    assert set(body["loop"]) == {
        "enabled", "running", "cycle_count", "last_cycle_at",
        "last_cycle_error", "quarantined_components",
    }


def test_health_reports_degraded_on_cycle_error(client, monkeypatch):
    base = operational_loop.get_status()
    monkeypatch.setattr(
        operational_loop, "get_status",
        lambda: {**base, "last_cycle_error": "RuntimeError('x')", "components": {}},
    )
    body = client.get("/health").json()
    assert body["status"] == "degraded"
    assert body["loop"]["last_cycle_error"] == "RuntimeError('x')"


def test_health_reports_degraded_on_quarantine(client, monkeypatch):
    base = operational_loop.get_status()
    monkeypatch.setattr(
        operational_loop, "get_status",
        lambda: {
            **base,
            "last_cycle_error": None,
            "components": {"uptime-kuma": {"quarantined": True}},
        },
    )
    body = client.get("/health").json()
    assert body["status"] == "degraded"
    assert body["loop"]["quarantined_components"] == ["uptime-kuma"]
