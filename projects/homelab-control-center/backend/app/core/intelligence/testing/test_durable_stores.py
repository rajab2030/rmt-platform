"""
C02 validation: durable governance stores and approval-decision persistence.

Proves that authorization, approval/hold, audit, and trace records survive a
process restart (re-instantiation from disk), and that ApprovalRecords are
persisted for every approval decision in the governed lifecycle.
"""
from unittest.mock import Mock

import app.core.intelligence.execution.engine as execution_engine_module
import app.core.intelligence.actions.service as actions_service_module
import app.core.intelligence.actions.approval_service as approval_service_module
import app.core.intelligence.verification.service as verification_service_module

from app.core.intelligence.actions.models import (
    ActionRequest,
    ActionType,
)
from app.core.intelligence.actions.authorization import (
    ExecutionAuthorization,
    AuthorizationStatus,
)
from app.core.intelligence.actions.authorization_storage import (
    AuthorizationStorage,
)
from app.core.intelligence.actions.approval import (
    ApprovalHold,
)
from app.core.intelligence.actions.approval_storage import (
    ApprovalHoldStorage,
    ApprovalRecordStorage,
)
from app.core.intelligence.actions.approval_policy import (
    ApprovalDecision,
    ApprovalMode,
)
from app.core.intelligence.execution.audit import ExecutionAuditRecord
from app.core.intelligence.execution.trace import ExecutionTrace
from app.core.intelligence.execution.storage import ExecutionAuditStorage
from app.core.intelligence.execution.trace_storage import ExecutionTraceStorage
from app.core.intelligence.verification.storage import VerificationStorage
from app.core.intelligence.execution.models import ExecutionResult


def _make_action(
    action_type: ActionType,
    component: str = "test-container",
    confidence: int = 100,
) -> ActionRequest:
    return ActionRequest(
        decision_id="test-decision",
        component=component,
        action_type=action_type,
        reason="test",
        confidence=confidence,
        requires_approval=False,
    )


# ---------------------------------------------------------------------------
# A-D. Durability: save -> recreate storage instance (simulate restart) -> retrieve
# ---------------------------------------------------------------------------

def test_authorization_durability(tmp_path):
    path = tmp_path / "auth.json"
    store1 = AuthorizationStorage(file_path=path)
    store1.save(ExecutionAuthorization(
        authorization_id="auth-1",
        action_id="action-1",
        status=AuthorizationStatus.APPROVED,
        target="web",
        operation="restart",
    ))

    # Simulate process restart: new instance loads from disk.
    store2 = AuthorizationStorage(file_path=path)
    assert len(store2.get_all()) == 1
    auth = store2.get_by_id("auth-1")
    assert auth is not None
    assert auth.action_id == "action-1"
    assert auth.target == "web"
    assert auth.operation == "restart"


def test_approval_hold_durability(tmp_path):
    path = tmp_path / "holds.json"
    action = _make_action(ActionType.REMOVE)
    store1 = ApprovalHoldStorage(file_path=path)
    store1.save(ApprovalHold(
        action_id=action.action_id,
        action=action,
        adapter_name="simulation",
        reason="test",
    ))

    store2 = ApprovalHoldStorage(file_path=path)
    assert len(store2.get_all()) == 1
    hold = store2.get_by_id(store1.get_all()[0].approval_id)
    assert hold is not None
    assert hold.action_id == action.action_id
    # Nested ActionRequest survives serialization.
    assert hold.action.component == action.component
    assert hold.action.action_type == action.action_type


def test_audit_durability(tmp_path):
    path = tmp_path / "audit.json"
    store1 = ExecutionAuditStorage(file_path=path)
    store1.save(ExecutionAuditRecord(
        execution_id="exec-1",
        action_id="action-1",
        authorization_id="auth-1",
        adapter="simulation",
        status="completed",
        risk_level="medium",
    ))

    store2 = ExecutionAuditStorage(file_path=path)
    assert len(store2.get_all()) == 1
    rec = store2.get_all()[0]
    assert rec.execution_id == "exec-1"
    assert rec.risk_level == "medium"


def test_trace_durability(tmp_path):
    path = tmp_path / "traces.json"
    store1 = ExecutionTraceStorage(file_path=path)
    store1.save(ExecutionTrace(
        execution_id="exec-1",
        action_id="action-1",
        authorization_id="auth-1",
        policy_decision="allow",
        risk_level="medium",
        outcome="completed",
    ))

    store2 = ExecutionTraceStorage(file_path=path)
    assert len(store2.get_all()) == 1
    trace = store2.get_all()[0]
    assert trace.execution_id == "exec-1"
    assert trace.policy_decision == "allow"
    assert trace.risk_level == "medium"


# ---------------------------------------------------------------------------
# E. ApprovalRecord lifecycle
# ---------------------------------------------------------------------------

def _setup_isolation(monkeypatch):
    isolated_authorization_storage = AuthorizationStorage()
    isolated_trace_storage = ExecutionTraceStorage()
    isolated_audit_storage = ExecutionAuditStorage()
    isolated_hold_storage = ApprovalHoldStorage()
    isolated_approval_record_storage = ApprovalRecordStorage()
    isolated_verification_storage = VerificationStorage()

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
        approval_service_module, "approval_hold_storage", isolated_hold_storage
    )
    monkeypatch.setattr(
        approval_service_module,
        "approval_record_storage",
        isolated_approval_record_storage,
    )
    monkeypatch.setattr(
        approval_service_module,
        "execution_authorization_storage",
        isolated_authorization_storage,
    )
    monkeypatch.setattr(
        actions_service_module,
        "execution_authorization_storage",
        isolated_authorization_storage,
    )
    monkeypatch.setattr(
        execution_engine_module,
        "execution_authorization_storage",
        isolated_authorization_storage,
    )
    monkeypatch.setattr(
        execution_engine_module, "execution_trace_storage", isolated_trace_storage
    )
    monkeypatch.setattr(
        execution_engine_module, "execution_audit_storage", isolated_audit_storage
    )
    monkeypatch.setattr(
        verification_service_module,
        "verification_storage",
        isolated_verification_storage,
    )
    monkeypatch.setattr(
        execution_engine_module, "adapter_registry", adapter_registry
    )

    return (
        isolated_authorization_storage,
        isolated_trace_storage,
        isolated_audit_storage,
        isolated_hold_storage,
        isolated_approval_record_storage,
        adapter_registry,
    )


def test_automatic_approval_persists_approved_record(monkeypatch):
    (
        auth_storage, trace_storage, audit_storage,
        hold_storage, approval_record_storage, adapter_registry,
    ) = _setup_isolation(monkeypatch)

    action = _make_action(ActionType.RESTART)  # medium -> auto

    result = actions_service_module.execute_governed_action(
        action, adapter_name="simulation"
    )

    assert result["status"] == "executed"
    records = approval_record_storage.get_all()
    assert len(records) == 1
    assert records[0].decision == "approved"
    assert records[0].approved_by == "approval_policy"
    assert records[0].action_id == action.action_id


def test_manual_hold_persists_manual_required_record(monkeypatch):
    (
        auth_storage, trace_storage, audit_storage,
        hold_storage, approval_record_storage, adapter_registry,
    ) = _setup_isolation(monkeypatch)

    action = _make_action(ActionType.REMOVE)  # high -> manual

    result = actions_service_module.execute_governed_action(
        action, adapter_name="simulation"
    )

    assert result["status"] == "manual_approval_required"
    records = approval_record_storage.get_all()
    assert len(records) == 1
    assert records[0].decision == "manual_required"
    assert records[0].approved_by == ""
    # Keyed by the hold's approval_id so the continuation can update it.
    assert records[0].approval_id == result["approval_id"]


def test_manual_approval_updates_record_to_approved(monkeypatch):
    (
        auth_storage, trace_storage, audit_storage,
        hold_storage, approval_record_storage, adapter_registry,
    ) = _setup_isolation(monkeypatch)

    action = _make_action(ActionType.REMOVE)
    held = actions_service_module.execute_governed_action(
        action, adapter_name="simulation"
    )
    approval_id = held["approval_id"]

    result = approval_service_module.approve_held_action(
        approval_id, approved_by="operator", approved=True
    )

    assert result["status"] == "executed"
    records = approval_record_storage.get_all()
    assert len(records) == 1
    assert records[0].decision == "approved"
    assert records[0].approved_by == "operator"


def test_manual_rejection_updates_record_to_rejected(monkeypatch):
    (
        auth_storage, trace_storage, audit_storage,
        hold_storage, approval_record_storage, adapter_registry,
    ) = _setup_isolation(monkeypatch)

    action = _make_action(ActionType.REMOVE)
    held = actions_service_module.execute_governed_action(
        action, adapter_name="simulation"
    )
    approval_id = held["approval_id"]

    result = approval_service_module.approve_held_action(
        approval_id, approved_by="operator", approved=False
    )

    assert result["status"] == "rejected"
    records = approval_record_storage.get_all()
    assert len(records) == 1
    assert records[0].decision == "rejected"
    assert records[0].approved_by == "operator"


def test_approval_rejection_persists_rejected_record(monkeypatch):
    """
    The approval REJECT branch is not reachable via the current action set
    (no allowed action yields unknown risk), so this proves the persistence
    mechanism directly for a rejected decision.
    """
    (
        auth_storage, trace_storage, audit_storage,
        hold_storage, approval_record_storage, adapter_registry,
    ) = _setup_isolation(monkeypatch)

    action = _make_action(ActionType.RESTART)
    decision = ApprovalDecision(
        action_id=action.action_id,
        mode=ApprovalMode.REJECT,
        approved=False,
        reason="Simulation risk is unknown",
    )

    approval_service_module.record_approval_decision(
        action, decision, decision="rejected", approved_by="approval_policy"
    )

    records = approval_record_storage.get_all()
    assert len(records) == 1
    assert records[0].decision == "rejected"
    assert records[0].approved_by == "approval_policy"
    assert records[0].action_id == action.action_id
