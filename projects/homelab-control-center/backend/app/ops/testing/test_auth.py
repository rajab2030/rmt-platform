"""RMT-PROD P0 (S1 + S2-lite) -- operator authentication boundary.

These are the only tests that run with ``RMT_AUTH_ENABLED=true``. The shared
``conftest.py`` defaults every other suite to auth-off.
"""
import pytest
from fastapi.testclient import TestClient

from app.ops import ops_config
from app.ops.auth import OperatorIdentity, resolve_operator, auth_misconfigured


TOKENS = "alice:alice-secret-1,bob:bob-secret-2"
GOOD = {"Authorization": "Bearer alice-secret-1"}


@pytest.fixture
def auth_env(monkeypatch):
    monkeypatch.setenv("RMT_AUTH_ENABLED", "true")
    monkeypatch.setenv("RMT_OPERATOR_TOKENS", TOKENS)
    yield


@pytest.fixture
def client(auth_env):
    import app.main as main_app

    with TestClient(main_app.app) as c:
        yield c


# --- unit: resolve_operator -------------------------------------------------


def test_resolve_disabled_returns_local_dev(monkeypatch):
    monkeypatch.setenv("RMT_AUTH_ENABLED", "false")
    assert resolve_operator() == OperatorIdentity(name="local-dev")


def test_resolve_bearer_and_apikey(auth_env):
    assert resolve_operator(authorization="Bearer alice-secret-1").name == "alice"
    assert resolve_operator(x_api_key="bob-secret-2").name == "bob"


def test_resolve_missing_is_401(auth_env):
    with pytest.raises(Exception) as ei:
        resolve_operator()
    assert getattr(ei.value, "status_code", None) == 401


def test_resolve_bad_token_is_401(auth_env):
    with pytest.raises(Exception) as ei:
        resolve_operator(authorization="Bearer nope")
    assert getattr(ei.value, "status_code", None) == 401


def test_misconfigured_detected(monkeypatch):
    monkeypatch.setenv("RMT_AUTH_ENABLED", "true")
    monkeypatch.setenv("RMT_OPERATOR_TOKENS", "")
    assert auth_misconfigured() is True
    monkeypatch.setenv("RMT_OPERATOR_TOKENS", TOKENS)
    assert auth_misconfigured() is False


def test_token_parsing_tolerant(monkeypatch):
    monkeypatch.setenv(
        "RMT_OPERATOR_TOKENS", " alice:s1 , malformed , :nokey, name: , bob:s2 "
    )
    assert ops_config.operator_tokens() == {"s1": "alice", "s2": "bob"}


# --- HTTP: every mutating route rejects the unauthenticated caller ---------

MUTATING = [
    ("post", "/execute", {"params": {"operation": "restart", "target": "x"}}),
    ("post", "/approve", {"params": {"approval_id": "x"}}),
    ("post", "/homelab/remediate", {"params": {"component": "x"}}),
    ("post", "/homelab/approve", {"params": {"approval_id": "x"}}),
    ("post", "/homelab/loop/start", {}),
    ("post", "/homelab/loop/stop", {}),
    ("post", "/homelab/loop/clear", {"params": {"component": "x"}}),
    ("post", "/agent/authority/grant",
     {"json": {"operation": "restart", "target": "x"}}),
    ("post", "/agent/act",
     {"json": {"agent_id": "a", "goal": "g", "target": "x",
               "mechanism": "restart"}}),
    ("post", "/agent/act/llm", {"json": {"goal": "g"}}),
]


@pytest.mark.parametrize("method,path,kw", MUTATING, ids=[m[1] for m in MUTATING])
def test_mutating_route_requires_auth(client, method, path, kw):
    r = getattr(client, method)(path, **kw)
    assert r.status_code == 401, (path, r.status_code, r.text)


@pytest.mark.parametrize("method,path,kw", MUTATING, ids=[m[1] for m in MUTATING])
def test_mutating_route_accepts_valid_token(client, method, path, kw):
    r = getattr(client, method)(path, headers=GOOD, **kw)
    # Business outcome varies; the point is auth did not reject it.
    assert r.status_code != 401, (path, r.status_code, r.text)


def test_bad_token_still_401(client):
    r = client.post(
        "/execute",
        params={"operation": "restart", "target": "x"},
        headers={"Authorization": "Bearer wrong"},
    )
    assert r.status_code == 401


def test_apikey_header_accepted(client):
    r = client.post(
        "/homelab/remediate",
        params={"component": "x"},
        headers={"X-API-Key": "bob-secret-2"},
    )
    assert r.status_code != 401


def test_readonly_routes_stay_open(client):
    # No auth header -- read-only endpoints are unaffected by S1.
    assert client.get("/").status_code == 200
    assert client.get("/monitor/history").status_code == 200
    assert client.get("/homelab/loop/status").status_code == 200


def test_agent_status_is_behind_auth(client):
    assert client.get("/agent/status").status_code == 401
    assert client.get("/agent/status", headers=GOOD).status_code == 200


def test_startup_refuses_without_tokens(monkeypatch):
    monkeypatch.setenv("RMT_AUTH_ENABLED", "true")
    monkeypatch.setenv("RMT_OPERATOR_TOKENS", "")
    import app.main as main_app

    with pytest.raises(RuntimeError, match="RMT_OPERATOR_TOKENS"):
        with TestClient(main_app.app):
            pass


def test_authenticated_identity_reaches_grant(client):
    r = client.post(
        "/agent/authority/grant",
        headers=GOOD,
        json={"operation": "restart", "target": "uptime-kuma",
              "granted_by": "SHOULD-BE-IGNORED"},
    )
    assert r.status_code == 200
    assert r.json()["granted_by"] == "alice"
