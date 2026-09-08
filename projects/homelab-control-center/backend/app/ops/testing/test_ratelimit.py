"""RMT-PROD P2 (S7) -- per-principal rate limiting on /execute and /agent/*."""
import pytest
from fastapi.testclient import TestClient

import app.main as main_app
from app.ops import ops_config, ratelimit


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("RMT_AUTH_ENABLED", "true")
    monkeypatch.setenv("RMT_OPERATOR_TOKENS", "alice:tok-alice,bob:tok-bob")
    ratelimit.reset()
    with TestClient(main_app.app) as c:
        yield c
    ratelimit.reset()


def _hdr(who="alice"):
    return {"Authorization": f"Bearer tok-{who}"}


def test_execute_429s_after_the_limit(client, monkeypatch):
    monkeypatch.setattr(ops_config, "ratelimit_execute_per_min", lambda: 3)

    codes = [
        client.post("/execute", params={"operation": "restart", "target": "x"},
                    headers=_hdr()).status_code
        for _ in range(5)
    ]
    assert codes[:3] == [c for c in codes[:3] if c != 429]  # first 3 not limited
    assert codes[3] == 429 and codes[4] == 429
    r = client.post("/execute", params={"operation": "restart", "target": "x"}, headers=_hdr())
    assert r.status_code == 429
    assert int(r.headers["Retry-After"]) >= 1


def test_limit_is_per_principal(client, monkeypatch):
    monkeypatch.setattr(ops_config, "ratelimit_execute_per_min", lambda: 2)
    for _ in range(3):
        client.post("/execute", params={"operation": "restart", "target": "x"}, headers=_hdr("alice"))
    assert client.post("/execute", params={"operation": "restart", "target": "x"},
                       headers=_hdr("alice")).status_code == 429
    # bob has his own bucket
    assert client.post("/execute", params={"operation": "restart", "target": "x"},
                       headers=_hdr("bob")).status_code != 429


def test_agent_grant_is_rate_limited(client, monkeypatch):
    monkeypatch.setattr(ops_config, "ratelimit_agent_per_min", lambda: 2)
    body = {"operation": "restart", "target": "x", "ttl_seconds": 60}
    seen = [client.post("/agent/authority/grant", json=body, headers=_hdr()).status_code
            for _ in range(4)]
    assert seen[-1] == 429


def test_disabled_switch_bypasses(client, monkeypatch):
    monkeypatch.setattr(ops_config, "ratelimit_enabled", lambda: False)
    monkeypatch.setattr(ops_config, "ratelimit_execute_per_min", lambda: 1)
    codes = [
        client.post("/execute", params={"operation": "restart", "target": "x"},
                    headers=_hdr()).status_code
        for _ in range(5)
    ]
    assert 429 not in codes


def test_read_routes_are_not_limited(client, monkeypatch):
    monkeypatch.setattr(ops_config, "ratelimit_agent_per_min", lambda: 1)
    for _ in range(5):
        assert client.get("/agent/status", headers=_hdr()).status_code == 200
