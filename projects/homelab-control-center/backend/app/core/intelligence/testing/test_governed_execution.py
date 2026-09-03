"""
C01 validation: the governed execution boundary.

Proves that the single authoritative governed lifecycle
(Action -> Policy -> Risk -> Approval -> Authorization -> Execution)
is the only path by which an action reaches an execution adapter, and
that blocked paths never invoke the adapter.
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
from app.core.intelligence.actions.authorization_storage import (
    AuthorizationStorage,
)
from app.core.intelligence.actions.approval_storage import (
    ApprovalHoldStorage,
    ApprovalRecordStorage,
)
from app.core.intelligence.execution.models import ExecutionResult
from app.core.intelligence.execution.storage import ExecutionAuditStorage
from app.core.intelligence.execution.trace_storage import ExecutionTraceStorage
from app.core.intelligence.verification.storage import VerificationStorage


def _make_action(
    action_type: ActionType,
    component: str = "test-container",
    confidence: int = 100,
    requires_approval: bool = False,
) -> ActionRequest:
    return ActionRequest(
        decision_id="test-decision",
        component=component,
        action_type=action_type,
        reason="test",
        confidence=confidence,
        requires_approval=requires_approval,
    )


def _setup_isolation(monkeypatch):
    """
    Wire the governed pipeline and the execution engine to the same
    isolated in-memory storage and a mock adapter, so we can observe
    whether the adapter is invoked.
    """
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

    # The governed pipeline saves authorization here...
    monkeypatch.setattr(
        actions_service_module,
        "execution_authorization_storage",
        isolated_authorization_storage,
    )
    # ...and the engine reads authorization from here. Same instance.
    monkeypatch.setattr(
        execution_engine_module,
        "execution_authorization_storage",
        isolated_authorization_storage,
    )
    monkeypatch.setattr(
        execution_engine_module,
        "execution_trace_storage",
        isolated_trace_storage,
    )
    monkeypatch.setattr(
        execution_engine_module,
        "execution_audit_storage",
        isolated_audit_storage,
    )
    monkeypatch.setattr(
        approval_service_module,
        "approval_hold_storage",
        isolated_hold_storage,
    )
    monkeypatch.setattr(
        approval_service_module,
        "approval_record_storage",
        isolated_approval_record_storage,
    )
    monkeypatch.setattr(
        verification_service_module,
        "verification_storage",
        isolated_verification_storage,
    )
    monkeypatch.setattr(
        execution_engine_module,
        "adapter_registry",
        adapter_registry,
    )

    return (
        isolated_authorization_storage,
        isolated_trace_storage,
        isolated_audit_storage,
        adapter_registry,
    )


def test_low_risk_action_auto_approves_and_executes(monkeypatch):
    """
    P01. A low-risk governed action (restart) auto-approves, creates a
    legitimate authorization, and reaches the adapter.
    """
    (
        auth_storage,
        trace_storage,
        audit_storage,
        adapter_registry,
    ) = _setup_isolation(monkeypatch)

    action = _make_action(ActionType.RESTART)

    result = actions_service_module.execute_governed_action(
        action,
        adapter_name="simulation",
    )

    assert result["status"] == "executed"
    assert result["success"] is True

    # Authorization was created through the governed lifecycle.
    assert len(auth_storage.get_all()) == 1
    auth = auth_storage.get_all()[0]
    assert auth.action_id == action.action_id
    assert auth.target == action.component
    assert auth.operation == action.action_type.value

    # Adapter was invoked exactly once.
    adapter_registry.get.assert_called_once()
    adapter_registry.get.return_value.execute.assert_called_once()


def test_high_risk_remove_held_for_manual_approval_adapter_not_called(
    monkeypatch,
):
    """
    N04. A high-risk action (remove) is held for manual approval.
    No authorization is created and the adapter is never invoked.
    """
    (
        auth_storage,
        trace_storage,
        audit_storage,
        adapter_registry,
    ) = _setup_isolation(monkeypatch)

    action = _make_action(ActionType.REMOVE)

    result = actions_service_module.execute_governed_action(
        action,
        adapter_name="simulation",
    )

    assert result["status"] == "manual_approval_required"

    # No authorization was created.
    assert len(auth_storage.get_all()) == 0

    # Adapter was never invoked.
    adapter_registry.get.assert_not_called()


def test_policy_denied_action_adapter_not_called(monkeypatch):
    """
    N01. A policy-denied action never reaches the adapter.
    """
    (
        auth_storage,
        trace_storage,
        audit_storage,
        adapter_registry,
    ) = _setup_isolation(monkeypatch)

    # Low confidence -> action policy denies.
    action = _make_action(ActionType.RESTART, confidence=50)

    result = actions_service_module.execute_governed_action(
        action,
        adapter_name="simulation",
    )

    assert result["status"] == "policy_denied"

    assert len(auth_storage.get_all()) == 0
    adapter_registry.get.assert_not_called()


def test_unsupported_action_type_policy_denied_adapter_not_called(
    monkeypatch,
):
    """
    N01. An action type not allowed by policy is denied before the adapter.
    """
    (
        auth_storage,
        trace_storage,
        audit_storage,
        adapter_registry,
    ) = _setup_isolation(monkeypatch)

    # create_checkpoint is not in ALLOWED_ACTION_TYPES.
    action = _make_action(ActionType.CREATE_CHECKPOINT)

    result = actions_service_module.execute_governed_action(
        action,
        adapter_name="simulation",
    )

    assert result["status"] == "policy_denied"

    assert len(auth_storage.get_all()) == 0
    adapter_registry.get.assert_not_called()
