"""C07 HTTP transport evidence.

Validates the existing production-equivalent public routes at the FastAPI
transport layer, without requiring Docker, git, external services, or any
pre-existing durable evidence files.

EXCLUDED ROUTES (documented; NOT Core-required; NOT asserted as passing):
  * GET /platform/state             - requires the external `git` executable;
                                      absent git raises FileNotFoundError.
                                      Environment-limited, not a Core defect.
  * GET /containers                 - Docker daemon/socket integration (above-Core).
  * GET /containers/{name}/stats    - Docker daemon/socket integration (above-Core).

Isolation: the six durable evidence stores are swapped to in-memory instances for
the duration of each test (mirrors test_evolution.py::_setup_isolation), so the
real JSON stores (traces.json, audit.json, verifications.json, authorizations.json,
approval_records.json, approval_holds.json) are never written. Observability metric
sources and calculate_platform_health inputs are monkeypatched so tests are
deterministic and do not depend on the sqlite DB.
"""
from datetime import datetime, timezone, timedelta

import pytest
from fastapi.testclient import TestClient

from app.core.intelligence.actions.approval_storage import (
    ApprovalHoldStorage,
    ApprovalRecordStorage,
)
from app.core.intelligence.actions.authorization_storage import AuthorizationStorage
from app.core.intelligence.execution.storage import ExecutionAuditStorage
from app.core.intelligence.execution.trace_storage import ExecutionTraceStorage
from app.core.intelligence.verification.storage import VerificationStorage

# Modules whose module-level storage singletons the request path uses.
import app.core.intelligence.actions.service as actions_service_module
import app.core.intelligence.execution.engine as engine_module
import app.core.intelligence.actions.approval_service as approval_service_module
import app.core.intelligence.verification.service as verification_service_module


@pytest.fixture
def client():
    from fastapi.testclient import TestClient as _TC
    import app.main as main_app
    with _TC(main_app.app) as c:
        yield c


def _isolate_evidence_stores(monkeypatch):
    """Swap durable evidence stores to in-memory (mirrors test_evolution)."""
    auth_storage = AuthorizationStorage()
    trace_storage = ExecutionTraceStorage()
    audit_storage = ExecutionAuditStorage()
    hold_storage = ApprovalHoldStorage()
    approval_record_storage = ApprovalRecordStorage()
    verification_storage = VerificationStorage()

    monkeypatch.setattr(
        actions_service_module, "execution_authorization_storage", auth_storage
    )
    monkeypatch.setattr(engine_module, "execution_authorization_storage", auth_storage)
    monkeypatch.setattr(engine_module, "execution_trace_storage", trace_storage)
    monkeypatch.setattr(engine_module, "execution_audit_storage", audit_storage)
    monkeypatch.setattr(approval_service_module, "approval_hold_storage", hold_storage)
    monkeypatch.setattr(
        approval_service_module, "approval_record_storage", approval_record_storage
    )
    # Manual-approval continuation saves the authorization here
    # (approval_service.py:201); patch it so engine re-reads the SAME
    # in-memory store and no real authorizations.json is written.
    monkeypatch.setattr(
        approval_service_module, "execution_authorization_storage", auth_storage
    )
    monkeypatch.setattr(
        verification_service_module, "verification_storage", verification_storage
    )
    return {
        "auth": auth_storage,
        "trace": trace_storage,
        "audit": audit_storage,
        "hold": hold_storage,
        "approval_record": approval_record_storage,
        "verification": verification_storage,
    }


class _Metric:
    """Minimal container metric object used by normalize_observation."""

    def __init__(self, name="test-service", status="running", health="healthy",
                 cpu=50.0, memory=60.0):
        self.name = name
        self.status = status
        self.health = health
        self.cpu_usage = cpu
        self.memory_usage = memory
        self.timestamp = datetime.now(timezone.utc)


class TestReadOnlyCoreRoutes:
    def test_read_only_core_routes(self, client, monkeypatch):
        # Deterministic observability/monitor sources (no sqlite/DB dependency).
        monkeypatch.setattr(
            "app.core.observability.api.get_container_metrics",
            lambda limit=50: [],
        )
        import app.main as main_app
        monkeypatch.setattr(main_app, "get_history", lambda: [])

        r1 = client.get("/")
        assert r1.status_code == 200
        assert isinstance(r1.json(), dict)
        assert "name" in r1.json()

        r2 = client.get("/modules")
        assert r2.status_code == 200
        assert isinstance(r2.json(), list)

        r3 = client.get("/config")
        assert r3.status_code == 200
        body = r3.json()
        assert isinstance(body, dict)
        assert "platform_name" in body

        r4 = client.get("/monitor/history")
        assert r4.status_code == 200
        assert isinstance(r4.json(), list)

        r5 = client.get("/observability/history")
        assert r5.status_code == 200
        assert isinstance(r5.json(), list)

        r6 = client.get("/observability/latest")
        assert r6.status_code == 200
        # Empty source -> null is valid; a dict is also valid.
        assert r6.json() is None or isinstance(r6.json(), dict)


class TestIntelligenceHealth:
    def test_intelligence_health_exercises_deviation_path(self, client, monkeypatch):
        # One healthy running metric -> normalized ComponentObservation.signals.
        monkeypatch.setattr(
            "app.core.intelligence.service.get_current_container_metrics",
            lambda: [_Metric(name="test-service")],
        )
        # Populated history -> calculate_baseline returns samples>0 -> deviation
        # branch in calculate_platform_health is entered (D1-relevant path).
        monkeypatch.setattr(
            "app.core.intelligence.analysis.baseline.get_container_metrics",
            lambda limit=50: [
                (
                    "test-service",
                    "running",
                    30.0,
                    30.0,
                    "healthy",
                    datetime.now(timezone.utc) - timedelta(minutes=10),
                )
            ],
        )

        r = client.get("/intelligence/health")
        assert r.status_code == 200, r.text
        report = r.json()
        assert isinstance(report, dict)
        assert "score" in report
        assert "status" in report
        assert "analysis" in report
        # Deviation was actually computed (D1: ComponentObservation.signals ->
        # calculate_deviation -> analysis) without AttributeError.
        assert any(
            a.get("component") == "test-service" and a.get("deviation") is not None
            for a in report["analysis"]
        )


class TestExecute:
    def test_execute_low_risk_auto_allowed_records_evidence(self, client, monkeypatch):
        stores = _isolate_evidence_stores(monkeypatch)
        r = client.post("/execute", params={"operation": "start", "target": "web1"})
        body = r.json()
        assert r.status_code == 200
        assert body["status"] == "executed"
        assert body.get("execution_id")

        # Evidence recorded and correlated by execution_id.
        verif = stores["verification"].get_all()
        assert len(stores["auth"].get_all()) >= 1
        assert len(stores["trace"].get_all()) >= 1
        assert len(stores["audit"].get_all()) >= 1
        assert len(verif) >= 1
        assert verif[0].execution_id == body["execution_id"]

    def test_execute_high_risk_hold_blocked_no_execution(self, client, monkeypatch):
        stores = _isolate_evidence_stores(monkeypatch)
        r = client.post("/execute", params={"operation": "remove", "target": "db1"})
        body = r.json()
        assert r.status_code == 200
        assert body["status"] == "manual_approval_required"
        assert body.get("approval_id")
        # Adapter not invoked: no execution trace/audit/verification/authorization.
        assert len(stores["trace"].get_all()) == 0
        assert len(stores["audit"].get_all()) == 0
        assert len(stores["verification"].get_all()) == 0
        assert len(stores["auth"].get_all()) == 0
        # A hold was recorded.
        assert len(stores["hold"].get_all()) == 1

    def test_execute_unsupported_operation_blocked(self, client, monkeypatch):
        stores = _isolate_evidence_stores(monkeypatch)
        r = client.post("/execute", params={"operation": "bogus", "target": "x"})
        body = r.json()
        assert r.status_code == 200
        assert body["status"] == "unsupported_operation"
        # Nothing reached governance/execution; no evidence written.
        assert len(stores["trace"].get_all()) == 0
        assert len(stores["audit"].get_all()) == 0
        assert len(stores["verification"].get_all()) == 0
        assert len(stores["auth"].get_all()) == 0


class TestApprove:
    def _create_hold(self, client):
        r = client.post("/execute", params={"operation": "remove", "target": "db2"})
        body = r.json()
        assert body["status"] == "manual_approval_required"
        return body["approval_id"]

    def test_approve_valid_continuation_executes(self, client, monkeypatch):
        stores = _isolate_evidence_stores(monkeypatch)
        approval_id = self._create_hold(client)
        r = client.post(
            "/approve",
            params={"approval_id": approval_id, "approved_by": "operator"},
        )
        body = r.json()
        assert r.status_code == 200
        assert body["status"] == "executed"
        assert body.get("execution_id")
        # Continuation produced execution evidence.
        assert len(stores["trace"].get_all()) >= 1
        assert len(stores["audit"].get_all()) >= 1
        assert len(stores["verification"].get_all()) >= 1

    def test_approve_unknown_approval_not_found(self, client, monkeypatch):
        stores = _isolate_evidence_stores(monkeypatch)
        r = client.post(
            "/approve",
            params={"approval_id": "does-not-exist", "approved_by": "operator"},
        )
        body = r.json()
        assert r.status_code == 200
        assert body["status"] == "approval_not_found"
        assert len(stores["trace"].get_all()) == 0
