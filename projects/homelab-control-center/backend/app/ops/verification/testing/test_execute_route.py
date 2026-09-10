"""B1a -- POST /execute carries an above_core_verification_status for an
executed operator action, from the above-Core observer layer.

The governed pipeline is stubbed (this is not a governance test); the point is
that main.execute wires verify_executed_action and surfaces its status.
"""
import pytest
from fastapi.testclient import TestClient

import app.main as main_app
import app.homelab.observer as observer_module
import app.core.intelligence.verification.storage as verification_storage_module
from app.core.intelligence.verification.storage import VerificationStorage


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(
        verification_storage_module,
        "verification_storage",
        VerificationStorage(file_path=None),
    )
    with TestClient(main_app.app) as c:
        yield c


def _stub_governed(monkeypatch, *, status="executed", success=True):
    def fake(action, adapter_name=None):
        return {
            "status": status,
            "success": success,
            "execution_id": "exec-route-1",
            "action_id": "act-1",
        }

    monkeypatch.setattr(main_app, "execute_governed_action", fake)
    monkeypatch.setattr(main_app, "_resolve_adapter_name", lambda: "docker")


def test_execute_surfaces_above_core_verified_success(client, monkeypatch):
    _stub_governed(monkeypatch)
    monkeypatch.setattr(observer_module, "docker_available", lambda: True)
    monkeypatch.setattr(
        observer_module, "get_containers",
        lambda: [{"name": "svc", "status": "running"}],
    )

    r = client.post("/execute", params={"operation": "restart", "target": "svc"})
    assert r.status_code == 200
    body = r.json()
    assert body["above_core_verification_status"] == "verified_success"


def test_execute_above_core_state_mismatch_is_surfaced(client, monkeypatch):
    _stub_governed(monkeypatch)
    monkeypatch.setattr(observer_module, "docker_available", lambda: True)
    monkeypatch.setattr(
        observer_module, "get_containers",
        lambda: [{"name": "svc", "status": "exited"}],
    )

    r = client.post("/execute", params={"operation": "restart", "target": "svc"})
    assert r.json()["above_core_verification_status"] == "state_mismatch"


def test_execute_no_observer_leaves_no_above_core_record(client, monkeypatch):
    _stub_governed(monkeypatch)
    monkeypatch.setattr(main_app, "_resolve_adapter_name", lambda: "simulation")

    r = client.post("/execute", params={"operation": "restart", "target": "svc"})
    body = r.json()
    # simulation -> no registered observer -> observation_unavailable, nothing saved
    assert body["above_core_verification_status"] == "observation_unavailable"
    assert verification_storage_module.verification_storage.get_all() == []


def test_execute_failed_adapter_gets_no_above_core_verification(client, monkeypatch):
    _stub_governed(monkeypatch, success=False)
    monkeypatch.setattr(observer_module, "docker_available", lambda: True)
    monkeypatch.setattr(
        observer_module, "get_containers",
        lambda: [{"name": "svc", "status": "running"}],
    )

    r = client.post("/execute", params={"operation": "restart", "target": "svc"})
    assert "above_core_verification_status" not in r.json()
