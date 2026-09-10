"""G1 - Above-Core Homelab/Docker container-state observer tests.

Validates the trusted Docker observer and its integration with the existing
frozen verification boundary (verifier.verify + verification_storage).

The observer observes; the existing verification mechanism verifies. No real
Docker mutation is performed; docker functions are mocked.
"""
from datetime import datetime, timezone
from unittest.mock import Mock

import app.homelab.observer as observer_module
import app.core.intelligence.verification.storage as verification_storage_module
import app.core.intelligence.execution.engine as execution_engine_module
import app.core.intelligence.actions.service as actions_service_module
import app.core.intelligence.actions.approval_service as approval_service_module
import app.core.intelligence.verification.service as verification_service_module

from app.core.intelligence.verification.models import (
    ExpectedOutcome,
    ObservedState,
    VerificationStatus,
)
from app.core.intelligence.verification.storage import VerificationStorage
from app.core.intelligence.observation.models import ComponentObservation
from app.core.intelligence.rules import create_health_evaluation
from app.core.intelligence.decision.engine import make_decision
from app.core.intelligence.actions.authorization_storage import AuthorizationStorage
from app.core.intelligence.actions.approval_storage import (
    ApprovalHoldStorage,
    ApprovalRecordStorage,
)
from app.core.intelligence.execution.models import ExecutionResult
from app.core.intelligence.execution.storage import ExecutionAuditStorage
from app.core.intelligence.execution.trace_storage import ExecutionTraceStorage

from app.homelab.observer import observe_container_state
from app.ops.verification import verify_executed_action
from app.homelab.remediation import remediate_and_verify


def _expected(target="uptime-kuma", state="running"):
    return ExpectedOutcome(
        target=target,
        operation="restart",
        expected_state=state,
    )


def _mock_docker(monkeypatch, available=True, containers=None):
    monkeypatch.setattr(observer_module, "docker_available", lambda: available)
    monkeypatch.setattr(
        observer_module,
        "get_containers",
        lambda: containers if containers is not None else [],
    )


# ---------------------------------------------------------------------------
# Observer: read-only, produces ObservedState
# ---------------------------------------------------------------------------

def test_observer_returns_observed_state_for_running_container(monkeypatch):
    _mock_docker(
        monkeypatch,
        available=True,
        containers=[{"name": "uptime-kuma", "status": "running"}],
    )
    observed = observe_container_state("uptime-kuma")
    assert isinstance(observed, ObservedState)
    assert observed.target == "uptime-kuma"
    assert observed.state == "running"
    assert observed.source == "docker"


def test_observer_returns_none_when_docker_unavailable(monkeypatch):
    _mock_docker(monkeypatch, available=False)
    assert observe_container_state("uptime-kuma") is None


def test_observer_returns_absent_when_reachable_and_container_gone(monkeypatch):
    """B1a: docker reachable + listing succeeded but the target is not in it is
    a definite observation ("absent"), not an inability to observe."""
    _mock_docker(
        monkeypatch,
        available=True,
        containers=[{"name": "dozzle", "status": "running"}],
    )
    observed = observe_container_state("uptime-kuma")
    assert isinstance(observed, ObservedState)
    assert observed.state == "absent"
    assert observed.source == "docker"


def test_observer_returns_none_when_lookup_raises(monkeypatch):
    """None is reserved for "could not observe" -- here get_containers raises."""
    monkeypatch.setattr(observer_module, "docker_available", lambda: True)

    def _boom():
        raise RuntimeError("docker socket error")

    monkeypatch.setattr(observer_module, "get_containers", _boom)
    assert observe_container_state("uptime-kuma") is None


def test_observer_is_read_only_cannot_mutate(monkeypatch):
    """The observer must never invoke any Docker mutation."""
    _mock_docker(
        monkeypatch,
        available=True,
        containers=[{"name": "uptime-kuma", "status": "running"}],
    )
    # Mutation functions must never be called.
    for fn in ("start_container", "stop_container", "restart_container",
               "create_container", "remove_container"):
        m = Mock(side_effect=AssertionError(f"{fn} must not be called"))
        monkeypatch.setattr("app.docker_api." + fn, m)

    observe_container_state("uptime-kuma")

    # If any mutation had been called, the Mock would have raised.
    assert True


# ---------------------------------------------------------------------------
# Verification integration: existing verifier + storage
# ---------------------------------------------------------------------------

def test_verified_success_when_expected_state_reached(monkeypatch):
    _mock_docker(
        monkeypatch,
        available=True,
        containers=[{"name": "uptime-kuma", "status": "running"}],
    )
    store = VerificationStorage()
    monkeypatch.setattr(verification_storage_module, "verification_storage", store)

    result = verify_executed_action(
        "exec-1",
        adapter_name="docker",
        operation="restart",
        target="uptime-kuma",
        expected=_expected(),
    )
    assert result.status == VerificationStatus.VERIFIED_SUCCESS
    assert result.observed.state == "running"
    assert result.reason.startswith("[layer=above_core adapter=docker")
    # Persisted through the existing verification storage.
    assert len(store.get_all()) == 1
    assert store.get_all()[0].execution_id == "exec-1"


def test_state_mismatch_when_actual_state_differs(monkeypatch):
    _mock_docker(
        monkeypatch,
        available=True,
        containers=[{"name": "uptime-kuma", "status": "exited"}],
    )
    store = VerificationStorage()
    monkeypatch.setattr(verification_storage_module, "verification_storage", store)

    result = verify_executed_action(
        "exec-2",
        adapter_name="docker",
        operation="restart",
        target="uptime-kuma",
        expected=_expected(),
    )
    assert result.status == VerificationStatus.STATE_MISMATCH
    assert result.observed.state == "exited"


def test_observation_unavailable_when_docker_unavailable(monkeypatch):
    _mock_docker(monkeypatch, available=False)
    store = VerificationStorage()
    monkeypatch.setattr(verification_storage_module, "verification_storage", store)

    result = verify_executed_action(
        "exec-3",
        adapter_name="docker",
        operation="restart",
        target="uptime-kuma",
        expected=_expected(),
    )
    assert result.status == VerificationStatus.OBSERVATION_UNAVAILABLE
    assert result.observed is None


def test_remove_verified_success_against_absent(monkeypatch):
    """B1a: an absent expected state now has a distinct observed value, so a
    remove can reach verified_success."""
    _mock_docker(
        monkeypatch,
        available=True,
        containers=[{"name": "dozzle", "status": "running"}],
    )
    store = VerificationStorage()
    monkeypatch.setattr(verification_storage_module, "verification_storage", store)

    result = verify_executed_action(
        "exec-rm",
        adapter_name="docker",
        operation="remove",
        target="uptime-kuma",
    )
    assert result.status == VerificationStatus.VERIFIED_SUCCESS
    assert result.observed.state == "absent"


def test_unknown_adapter_operation_records_nothing(monkeypatch):
    """No registered observer -> observation_unavailable result, and no second
    record written (the Core already saved one)."""
    store = VerificationStorage()
    monkeypatch.setattr(verification_storage_module, "verification_storage", store)

    result = verify_executed_action(
        "exec-x",
        adapter_name="simulation",
        operation="restart",
        target="uptime-kuma",
    )
    assert result.status == VerificationStatus.OBSERVATION_UNAVAILABLE
    assert "no above-Core observer" in result.reason
    assert store.get_all() == []


# ---------------------------------------------------------------------------
# G2 intact: Decision -> ActionRequest -> Govern -> Authorize -> Execute -> Verify
# ---------------------------------------------------------------------------

def _setup_isolation(monkeypatch):
    """Wire governed pipeline + engine to isolated in-memory storage and a mock
    adapter (mirrors test_remediation)."""
    auth_storage = AuthorizationStorage()
    trace_storage = ExecutionTraceStorage()
    audit_storage = ExecutionAuditStorage()
    hold_storage = ApprovalHoldStorage()
    approval_record_storage = ApprovalRecordStorage()
    verification_storage = VerificationStorage()

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

    monkeypatch.setattr(
        actions_service_module, "execution_authorization_storage", auth_storage
    )
    monkeypatch.setattr(
        execution_engine_module, "execution_authorization_storage", auth_storage
    )
    monkeypatch.setattr(execution_engine_module, "execution_trace_storage", trace_storage)
    monkeypatch.setattr(execution_engine_module, "execution_audit_storage", audit_storage)
    monkeypatch.setattr(approval_service_module, "approval_hold_storage", hold_storage)
    monkeypatch.setattr(
        approval_service_module, "approval_record_storage", approval_record_storage
    )
    monkeypatch.setattr(
        approval_service_module, "execution_authorization_storage", auth_storage
    )
    # The governed path (execute_governed_action -> Core verify_execution) and
    # the above-Core verify_executed_action both write verification evidence;
    # patch the Core verification service storage AND the storage-module
    # singleton the above-Core layer dereferences (R10) so no real evidence db
    # is touched.
    monkeypatch.setattr(
        verification_service_module, "verification_storage", verification_storage
    )
    monkeypatch.setattr(
        verification_storage_module, "verification_storage", verification_storage
    )
    monkeypatch.setattr(execution_engine_module, "adapter_registry", adapter_registry)
    return {
        "auth": auth_storage,
        "trace": trace_storage,
        "audit": audit_storage,
        "hold": hold_storage,
        "verification": verification_storage,
        "adapter_registry": adapter_registry,
    }


def _critical_uptime_kuma(signals=None):
    return create_health_evaluation(
        ComponentObservation(
            component="uptime-kuma",
            source="docker",
            state="stopped",
            timestamp=datetime.now(timezone.utc),
            signals=signals or {},
            metadata={"health": "unhealthy"},
        )
    )


def test_remediate_and_verify_full_chain(monkeypatch):
    """G2 remains intact and now includes Docker verification: the governed
    restart executes and the existing verification boundary reports the actual
    post-restart Docker state."""
    from app.homelab import remediation as remediation_module

    stores = _setup_isolation(monkeypatch)
    # After the governed restart, the container is observed running.
    _mock_docker(
        monkeypatch,
        available=True,
        containers=[{"name": "uptime-kuma", "status": "running"}],
    )

    # A critical uptime-kuma WITH signals yields confidence 100; with the
    # Homelab policy set to auto-approve, the governed chain executes in one
    # call and the Docker verification runs end-to-end.
    evaluation = _critical_uptime_kuma(signals={"cpu_usage": 0.0, "memory_usage": 0.0})
    assert evaluation.confidence == 100
    decision = make_decision(evaluation)

    monkeypatch.setitem(
        remediation_module.REMEDIATION_POLICY["uptime-kuma"],
        "requires_approval",
        False,
    )

    result = remediate_and_verify(evaluation, decision, adapter_name="simulation")
    assert result["status"] == "executed"
    assert result.get("execution_id")
    # Docker verification ran through the existing verification boundary.
    assert result["docker_verification_status"] == "verified_success"

    # Full governed chain produced authorization + trace + audit + verification.
    assert len(stores["auth"].get_all()) >= 1
    assert len(stores["trace"].get_all()) >= 1
    assert len(stores["audit"].get_all()) >= 1
    assert len(stores["verification"].get_all()) >= 1
    stores["adapter_registry"].get.return_value.execute.assert_called_once()
