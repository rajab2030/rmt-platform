"""RMT-PROD P2 (D6) -- runtime capability reporting + startup mismatch WARNING."""
import logging

import pytest
from fastapi.testclient import TestClient

import app.main as main_app
from app.ops import runtime_info


@pytest.fixture
def client():
    with TestClient(main_app.app) as c:
        yield c


def test_runtime_status_shape():
    s = runtime_info.runtime_status()
    assert set(s) == {
        "configured_engine", "resolved_adapter", "docker_available",
        "git_available", "adapter_degraded", "notes",
    }
    assert isinstance(s["notes"], list)
    assert s["adapter_degraded"] == bool(s["notes"])


def test_health_carries_runtime_block(client):
    body = client.get("/health").json()
    assert "runtime" in body
    assert body["runtime"]["resolved_adapter"] in ("docker", "simulation", "module_change")
    # advisory only: an adapter mismatch must not flip /health status
    assert body["status"] in ("ok", "degraded")


def test_degraded_when_configured_engine_unavailable(monkeypatch):
    monkeypatch.setattr(runtime_info, "resolved_adapter", lambda: "simulation")

    class _S:
        class runtime:
            engine = "docker"

    monkeypatch.setattr(runtime_info, "load_settings", lambda: _S)
    monkeypatch.setattr(runtime_info, "docker_available", lambda: False)

    s = runtime_info.runtime_status()
    assert s["adapter_degraded"] is True
    assert any("docker" in n and "simulation" in n for n in s["notes"])


def test_warn_on_capability_mismatch_logs(monkeypatch, caplog):
    monkeypatch.setattr(
        runtime_info, "runtime_status",
        lambda: {"notes": ["configured engine 'docker' unavailable -- running 'simulation'"]},
    )
    logger = logging.getLogger("rmt.test")
    with caplog.at_level(logging.WARNING, logger="rmt.test"):
        runtime_info.warn_on_capability_mismatch(logger)
    assert "capability mismatch" in caplog.text


def test_warn_never_raises(monkeypatch):
    def _boom():
        raise RuntimeError("settings unreadable")

    monkeypatch.setattr(runtime_info, "runtime_status", _boom)
    assert runtime_info.warn_on_capability_mismatch(logging.getLogger("rmt.test")) == {}
