"""RMT-PROD P2 (S5) -- CORS origins from config; methods/headers scoped."""
import importlib
import os

import pytest
from fastapi.testclient import TestClient

from app.ops import ops_config


def _client():
    import app.main as main_app
    importlib.reload(main_app)          # re-evaluate add_middleware with the env in place
    return TestClient(main_app.app), main_app


@pytest.fixture(autouse=True)
def _restore_main():
    yield
    os.environ.pop("RMT_CORS_ORIGINS", None)
    import app.main as main_app
    importlib.reload(main_app)          # leave app.main as the rest of the suite expects


def test_default_origin_is_local_dev_only(monkeypatch):
    monkeypatch.delenv("RMT_CORS_ORIGINS", raising=False)
    assert ops_config.cors_origins() == ["http://localhost:5173"]
    # the stale 192.168.235.128 default is gone
    assert not any("192.168.235.128" in o for o in ops_config.cors_origins())


def test_origins_come_from_env(monkeypatch):
    monkeypatch.setenv(
        "RMT_CORS_ORIGINS",
        "https://rmt.homelab.lan, https://ops.homelab.lan ",
    )
    assert ops_config.cors_origins() == [
        "https://rmt.homelab.lan",
        "https://ops.homelab.lan",
    ]


def test_configured_origin_is_reflected_and_unknown_is_not(monkeypatch):
    monkeypatch.setenv("RMT_CORS_ORIGINS", "https://ui.homelab.lan")
    client, _ = _client()

    ok = client.get("/health", headers={"Origin": "https://ui.homelab.lan"})
    assert ok.headers.get("access-control-allow-origin") == "https://ui.homelab.lan"

    bad = client.get("/health", headers={"Origin": "https://evil.example"})
    assert bad.headers.get("access-control-allow-origin") is None


def test_preflight_rejects_unscoped_method_and_header(monkeypatch):
    monkeypatch.setenv("RMT_CORS_ORIGINS", "https://ui.homelab.lan")
    client, _ = _client()

    allowed = client.options(
        "/execute",
        headers={
            "Origin": "https://ui.homelab.lan",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization",
        },
    )
    assert allowed.headers.get("access-control-allow-origin") == "https://ui.homelab.lan"

    denied = client.options(
        "/execute",
        headers={
            "Origin": "https://ui.homelab.lan",
            "Access-Control-Request-Method": "DELETE",
        },
    )
    # Starlette returns 400 for a disallowed preflight method
    assert denied.status_code == 400
