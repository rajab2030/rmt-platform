"""RMT-CAP-03 - Above-Core Homelab approval-continuation Learn-stage tests.

Validates that continuing a manually held Homelab remediation via
``continue_remediation()`` (the wiring behind ``POST /homelab/approve``):

  * calls the frozen Core ``approve_held_action()`` unchanged;
  * runs the existing above-Core Docker verification for the executed
    continuation;
  * records the *executed* outcome through the existing Core learning/memory
    capability, correlated by approval_id / execution_id;
  * does NOT add a Learn record or Docker verification for a non-Homelab
    held action, or for a rejected / unknown continuation.

Run-safe: the execution adapter and the Docker observer are mocked, and all
evidence + memory stores are isolated in-memory, so no real container is
mutated and no durable JSON / SQLite file is touched.
"""
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

import app.core.intelligence.execution.engine as execution_engine_module
import app.core.intelligence.actions.service as actions_service_module
import app.core.intelligence.actions.approval_service as approval_service_module
import app.core.intelligence.verification.service as verification_service_module
import app.core.intelligence.memory.service as memory_service_module
import app.homelab.verification as homelab_verification_module
import app.homelab.observer as observer_module

from app.core.intelligence.observation.models import ComponentObservation
from app.core.intelligence.rules import create_health_evaluation
from app.core.intelligence.decision.engine import make_decision
from app.core.intelligence.actions.models import ActionRequest, ActionType
from app.core.intelligence.actions.approval import ApprovalHold, ApprovalStatus
from app.core.intelligence.actions.authorization_storage import AuthorizationStorage
from app.core.intelligence.actions.approval_storage import (
    ApprovalHoldStorage,
    ApprovalRecordStorage,
)
from app.core.intelligence.execution.models import ExecutionResult
from app.core.intelligence.execution.storage import ExecutionAuditStorage
from app.core.intelligence.execution.trace_storage import ExecutionTraceStorage
from app.core.intelligence.verification.models import (
    ExpectedOutcome,
    VerificationStatus,
)
from app.core.intelligence.verification.storage import VerificationStorage

from app.homelab.remediation import remediate_and_verify
from app.homelab.continuation import continue_remediation


# ---------------------------------------------------------------------------
# Isolation helpers
# ---------------------------------------------------------------------------

def _setup_isolation(monkeypatch):
    """Wire the governed pipeline, engine, verification and learning to
    isolated in-memory storage and a mock adapter (mirrors
    test_remediation._setup_isolation plus memory isolation)."""
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
    monkeypatch.setattr(
        execution_engine_module, "execution_trace_storage", trace_storage
    )
    monkeypatch.setattr(
        execution_engine_module, "execution_audit_storage", audit_storage
    )
    monkeypatch.setattr(
        approval_service_module, "approval_hold_storage", hold_storage
    )
    monkeypatch.setattr(
        approval_service_module, "approval_record_storage", approval_record_storage
    )
    # The manual-approval continuation saves its authorization here; patch it
    # so the engine re-reads the SAME in-memory store.
    monkeypatch.setattr(
        approval_service_module, "execution_authorization_storage", auth_storage
    )
    # Core verification storage (verify_execution inside approve_held_action).
    monkeypatch.setattr(
        verification_service_module, "verification_storage", verification_storage
    )
    # Above-Core Docker verification storage (verify_docker_execution).
    monkeypatch.setattr(
        homelab_verification_module, "verification_storage", verification_storage
    )
    monkeypatch.setattr(
        execution_engine_module, "adapter_registry", adapter_registry
    )

    # Learn stage: isolate the Core memory/learning store in-memory.
    memory_records = []
    monkeypatch.setattr(
        memory_service_module,
        "save_memory",
        lambda record: memory_records.append(record) or record,
    )

    return {
        "auth": auth_storage,
        "trace": trace_storage,
        "audit": audit_storage,
        "hold": hold_storage,
        "approval_record": approval_record_storage,
        "verification": verification_storage,
        "adapter_registry": adapter_registry,
        "memory": memory_records,
    }


def _mock_docker_observer(monkeypatch, post_status="running"):
    """Make the above-Core Docker observer report a deterministic post-state."""
    monkeypatch.setattr(observer_module, "docker_available", lambda: True)
    monkeypatch.setattr(
        observer_module,
        "get_containers",
        lambda: [{"name": "uptime-kuma", "status": post_status}],
    )


def _critical_uptime_kuma():
    """Critical uptime-kuma with signals -> confidence 100 (auto-approvable
    were it not for the explicit requires_approval on the Homelab policy)."""
    return create_health_evaluation(
        ComponentObservation(
            component="uptime-kuma",
            source="docker",
            state="stopped",
            timestamp=datetime.now(timezone.utc),
            signals={"cpu_usage": 0.0, "memory_usage": 0.0},
            metadata={"health": "unhealthy"},
        )
    )


def _hold_a_homelab_remediation(monkeypatch):
    """Drive a real remediation to a manual-approval hold and return its
    approval_id. Uses remediate_and_verify so the held-state Learn record is
    produced exactly as in the real flow."""
    evaluation = _critical_uptime_kuma()
    decision = make_decision(evaluation)
    held = remediate_and_verify(evaluation, decision, adapter_name="simulation")
    assert held["status"] == "manual_approval_required"
    assert held["approval_id"]
    return held["approval_id"]


# ---------------------------------------------------------------------------
# Executed continuation: Learn stage is closed
# ---------------------------------------------------------------------------

def test_continuation_records_executed_outcome_as_learning(monkeypatch):
    stores = _setup_isolation(monkeypatch)
    _mock_docker_observer(monkeypatch, post_status="running")

    approval_id = _hold_a_homelab_remediation(monkeypatch)

    # Before continuation: only the held-state Learn record exists.
    assert [r.data.get("status") for r in stores["memory"]] == [
        "manual_approval_required"
    ]

    result = continue_remediation(approval_id, approved_by="operator")

    # Frozen Core continuation executed.
    assert result["status"] == "executed"
    assert result["execution_id"]
    assert result["approval_id"] == approval_id

    # Above-Core Docker verification ran and is reported.
    assert result["docker_verification_status"] == VerificationStatus.VERIFIED_SUCCESS
    assert "docker_verification_reason" in result

    # Learn stage closed: the executed outcome is now recorded, tied to the
    # run via execution_id / approval_id, carrying the verification status.
    executed = [r for r in stores["memory"] if r.data.get("status") == "executed"]
    assert len(executed) == 1
    rec = executed[0]
    assert rec.event_type == "remediation"
    assert rec.component == "uptime-kuma"
    assert rec.data["execution_id"] == result["execution_id"]
    assert rec.data["approval_id"] == approval_id
    assert rec.data["docker_verification_status"] == VerificationStatus.VERIFIED_SUCCESS

    # Docker verification evidence persisted and correlated by execution_id.
    verifs = stores["verification"].get_all()
    assert any(v.execution_id == result["execution_id"] for v in verifs)


def test_continuation_learn_record_preserves_state_mismatch(monkeypatch):
    """allowed != verified: if the container did not reach the expected state,
    the executed Learn record must carry state_mismatch, not success."""
    stores = _setup_isolation(monkeypatch)
    _mock_docker_observer(monkeypatch, post_status="exited")

    approval_id = _hold_a_homelab_remediation(monkeypatch)
    result = continue_remediation(approval_id, approved_by="operator")

    assert result["status"] == "executed"
    assert result["docker_verification_status"] == VerificationStatus.STATE_MISMATCH

    executed = [r for r in stores["memory"] if r.data.get("status") == "executed"]
    assert len(executed) == 1
    assert (
        executed[0].data["docker_verification_status"]
        == VerificationStatus.STATE_MISMATCH
    )


# ---------------------------------------------------------------------------
# Non-Homelab held action: continued by the Core, no extra Learn / verify
# ---------------------------------------------------------------------------

def test_non_homelab_held_action_gets_no_learn_or_docker_verification(monkeypatch):
    stores = _setup_isolation(monkeypatch)
    _mock_docker_observer(monkeypatch, post_status="running")

    # A held action whose component is NOT in the Homelab remediation policy
    # (e.g. the operator POST /execute flow), placed directly into the
    # isolated hold store.
    action = ActionRequest(
        decision_id="operator-request-restart",
        component="some-other-service",
        action_type=ActionType.RESTART,
        reason="operator requested restart",
        confidence=100,
        requires_approval=True,
        expected_outcome=ExpectedOutcome(
            target="some-other-service",
            operation="restart",
            expected_state="running",
        ),
    )
    hold = ApprovalHold(
        action_id=action.action_id,
        action=action,
        adapter_name="simulation",
        reason="operator hold",
        status=ApprovalStatus.PENDING,
        expires_at=datetime.now(timezone.utc) + timedelta(seconds=300),
        risk_level="medium",
    )
    stores["hold"].save(hold)

    result = continue_remediation(hold.approval_id, approved_by="operator")

    # Core continuation still executes it, exactly as generic POST /approve.
    assert result["status"] == "executed"
    # No above-Core augmentation for a non-Homelab action.
    assert "docker_verification_status" not in result
    # No Learn record written by this wiring.
    assert stores["memory"] == []


# ---------------------------------------------------------------------------
# Rejected / unknown continuation: nothing added
# ---------------------------------------------------------------------------

def test_rejected_continuation_records_no_executed_learning(monkeypatch):
    stores = _setup_isolation(monkeypatch)
    _mock_docker_observer(monkeypatch, post_status="running")

    approval_id = _hold_a_homelab_remediation(monkeypatch)
    result = continue_remediation(
        approval_id, approved_by="operator", approved=False
    )

    assert result["status"] == "rejected"
    # Only the original held-state record remains; no executed record.
    assert all(r.data.get("status") != "executed" for r in stores["memory"])
    assert "docker_verification_status" not in result


def test_unknown_approval_id_returns_core_result_unchanged(monkeypatch):
    stores = _setup_isolation(monkeypatch)

    result = continue_remediation("does-not-exist", approved_by="operator")

    assert result["status"] == "approval_not_found"
    assert stores["memory"] == []
