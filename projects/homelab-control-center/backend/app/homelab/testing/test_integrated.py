"""Integrated run-safe validation of the complete Homelab capability.

Exercises the production-equivalent HTTP entrypoint (POST /homelab/remediate)
through the full chain:

  Understand -> Decide -> ActionRequest -> Govern -> Authorize -> Execute
  -> Verify -> Evidence

Run-safe: the Docker execution adapter and the Docker observer are mocked, so
no real container is mutated. Evidence stores are isolated in-memory, so no
real durable evidence file is touched.
"""
from datetime import datetime, timezone
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

import app.core.intelligence.execution.engine as execution_engine_module
import app.core.intelligence.actions.service as actions_service_module
import app.core.intelligence.actions.approval_service as approval_service_module
import app.core.intelligence.verification.service as verification_service_module
import app.core.intelligence.memory.service as memory_service_module
import app.homelab.verification as homelab_verification_module
import app.homelab.observer as observer_module
import app.homelab.remediation as remediation_module

from app.core.intelligence.actions.authorization_storage import AuthorizationStorage
from app.core.intelligence.actions.approval_storage import (
    ApprovalHoldStorage,
    ApprovalRecordStorage,
)
from app.core.intelligence.execution.models import ExecutionResult
from app.core.intelligence.execution.storage import ExecutionAuditStorage
from app.core.intelligence.execution.trace_storage import ExecutionTraceStorage
from app.core.intelligence.verification.storage import VerificationStorage


class _Metric:
    def __init__(self, name, status, health, cpu=0.0, memory=0.0):
        self.name = name
        self.status = status
        self.health = health
        self.cpu_usage = cpu
        self.memory_usage = memory
        self.timestamp = datetime.now(timezone.utc)


@pytest.fixture
def client():
    import app.main as main_app
    with TestClient(main_app.app) as c:
        yield c


def _isolate_evidence_stores(monkeypatch):
    auth = AuthorizationStorage()
    trace = ExecutionTraceStorage()
    audit = ExecutionAuditStorage()
    hold = ApprovalHoldStorage()
    approval_record = ApprovalRecordStorage()
    verification = VerificationStorage()

    monkeypatch.setattr(actions_service_module, "execution_authorization_storage", auth)
    monkeypatch.setattr(execution_engine_module, "execution_authorization_storage", auth)
    monkeypatch.setattr(execution_engine_module, "execution_trace_storage", trace)
    monkeypatch.setattr(execution_engine_module, "execution_audit_storage", audit)
    monkeypatch.setattr(approval_service_module, "approval_hold_storage", hold)
    monkeypatch.setattr(approval_service_module, "approval_record_storage", approval_record)
    monkeypatch.setattr(approval_service_module, "execution_authorization_storage", auth)
    monkeypatch.setattr(verification_service_module, "verification_storage", verification)
    monkeypatch.setattr(homelab_verification_module, "verification_storage", verification)

    # Learn stage: isolate the Core memory/learning store in-memory so no real
    # intelligence_memory table is written and assertions are deterministic.
    memory_records = []
    monkeypatch.setattr(
        memory_service_module,
        "save_memory",
        lambda record: memory_records.append(record) or record,
    )

    return {
        "auth": auth,
        "trace": trace,
        "audit": audit,
        "hold": hold,
        "approval_record": approval_record,
        "verification": verification,
        "memory": memory_records,
    }


def _mock_docker(monkeypatch, metric, post_status="running"):
    """Mock the Docker execution adapter and the Docker observer."""
    adapter = Mock()
    adapter.supports.return_value = True
    adapter.execute.side_effect = lambda request: ExecutionResult(
        execution_id=request.execution_id,
        status="completed",
        success=True,
        message="Simulation execution completed",
    )
    adapter_registry = Mock()
    adapter_registry.get.return_value = adapter
    monkeypatch.setattr(execution_engine_module, "adapter_registry", adapter_registry)
    monkeypatch.setattr(remediation_module, "resolve_adapter_name", lambda: "docker")

    monkeypatch.setattr(observer_module, "docker_available", lambda: True)
    monkeypatch.setattr(
        observer_module,
        "get_containers",
        lambda: [{"name": metric.name, "status": post_status}],
    )
    return adapter_registry


def _mock_observation(monkeypatch, metric):
    monkeypatch.setattr(
        "app.core.observability.service.get_current_container_metrics",
        lambda: [metric],
    )


# ---------------------------------------------------------------------------
# Remediation path: approval enforced (no execution, no mutation)
# ---------------------------------------------------------------------------

def test_remediation_approval_enforced_no_mutation(client, monkeypatch):
    stores = _isolate_evidence_stores(monkeypatch)
    metric = _Metric("uptime-kuma", "stopped", "unhealthy")
    _mock_observation(monkeypatch, metric)
    _mock_docker(monkeypatch, metric)

    r = client.post("/homelab/remediate", params={"component": "uptime-kuma"})
    assert r.status_code == 200
    body = r.json()
    # requires_approval=True -> held for manual approval; adapter not invoked.
    assert body["status"] == "manual_approval_required"
    assert body.get("approval_id")

    # No execution evidence; no authorization; adapter never invoked.
    assert len(stores["trace"].get_all()) == 0
    assert len(stores["audit"].get_all()) == 0
    assert len(stores["auth"].get_all()) == 0
    assert len(stores["hold"].get_all()) == 1

    # Learn: the remediation attempt (held for approval) is recorded, tied to
    # the actual run via approval_id.
    learn = stores["memory"]
    assert any(
        r.event_type == "remediation"
        and r.data.get("approval_id") == body["approval_id"]
        and r.data.get("status") == "manual_approval_required"
        for r in learn
    )


# ---------------------------------------------------------------------------
# Full chain with Docker verification (auto-approve, mocked)
# ---------------------------------------------------------------------------

def test_full_chain_execute_and_verify(client, monkeypatch):
    stores = _isolate_evidence_stores(monkeypatch)
    metric = _Metric("uptime-kuma", "stopped", "unhealthy")
    _mock_observation(monkeypatch, metric)
    adapter_registry = _mock_docker(monkeypatch, metric, post_status="running")
    # Auto-approve so the governed chain executes in one call.
    monkeypatch.setitem(
        remediation_module.REMEDIATION_POLICY["uptime-kuma"],
        "requires_approval",
        False,
    )

    r = client.post("/homelab/remediate", params={"component": "uptime-kuma"})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "executed"
    assert body.get("execution_id")
    # G1 Docker verification through the existing verification boundary.
    assert body["docker_verification_status"] == "verified_success"

    # Evidence correlated by execution_id.
    assert len(stores["auth"].get_all()) >= 1
    assert len(stores["trace"].get_all()) >= 1
    assert len(stores["audit"].get_all()) >= 1
    assert len(stores["verification"].get_all()) >= 1
    verif = stores["verification"].get_all()
    assert any(v.execution_id == body["execution_id"] for v in verif)
    adapter_registry.get.return_value.execute.assert_called_once()

    # Learn: the remediation outcome is recorded, tied to the actual run via
    # execution_id, and carries the verification status.
    learn = stores["memory"]
    assert any(
        r.event_type == "remediation"
        and r.data.get("execution_id") == body["execution_id"]
        and r.data.get("status") == "executed"
        and r.data.get("docker_verification_status") == "verified_success"
        for r in learn
    )


# ---------------------------------------------------------------------------
# Healthy path: no remediation, no mutation
# ---------------------------------------------------------------------------

def test_healthy_path_no_remediation(client, monkeypatch):
    stores = _isolate_evidence_stores(monkeypatch)
    metric = _Metric("uptime-kuma", "running", "healthy", cpu=20.0, memory=30.0)
    _mock_observation(monkeypatch, metric)
    _mock_docker(monkeypatch, metric)

    r = client.post("/homelab/remediate", params={"component": "uptime-kuma"})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "no_remediation"

    # No governance/execution evidence written.
    assert len(stores["trace"].get_all()) == 0
    assert len(stores["audit"].get_all()) == 0
    assert len(stores["auth"].get_all()) == 0
    assert len(stores["verification"].get_all()) == 0

    # No remediation run -> no Learn record.
    assert len(stores["memory"]) == 0
