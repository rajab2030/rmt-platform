"""
C01 validation: manual-approval continuation, authorization provenance,
and authorization expiry.
"""
from datetime import datetime, timedelta, timezone
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
from app.core.intelligence.actions.approval_storage import (
    ApprovalHoldStorage,
    ApprovalRecordStorage,
)
from app.core.intelligence.execution.models import ExecutionRequest, ExecutionResult
from app.core.intelligence.execution.storage import ExecutionAuditStorage
from app.core.intelligence.execution.trace_storage import ExecutionTraceStorage
from app.core.intelligence.verification.storage import VerificationStorage


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
        isolated_hold_storage,
        adapter_registry,
    )


def test_manual_approval_hold_then_legitimate_continuation_executes(
    monkeypatch,
):
    """
    P03. A high-risk action is held for manual approval, then a legitimate
    approval continuation resumes the lifecycle and reaches the adapter.
    """
    (
        auth_storage,
        trace_storage,
        audit_storage,
        hold_storage,
        adapter_registry,
    ) = _setup_isolation(monkeypatch)

    action = _make_action(ActionType.REMOVE)

    held = actions_service_module.execute_governed_action(
        action,
        adapter_name="simulation",
    )

    assert held["status"] == "manual_approval_required"
    approval_id = held["approval_id"]

    # No authorization yet, adapter not called.
    assert len(auth_storage.get_all()) == 0
    adapter_registry.get.assert_not_called()

    # Legitimate continuation.
    result = approval_service_module.approve_held_action(
        approval_id,
        approved_by="operator",
        approved=True,
    )

    assert result["status"] == "executed"
    assert result["success"] is True

    # Authorization was created from the held action with provenance.
    assert len(auth_storage.get_all()) == 1
    auth = auth_storage.get_all()[0]
    assert auth.action_id == action.action_id
    assert auth.decision_id == action.decision_id
    assert auth.approval_id == approval_id
    assert auth.authorization_type == "manual"

    # The resumed execution uses the original held action's target/operation
    # and governed risk, not caller-supplied values.
    assert auth.target == action.component
    assert auth.operation == action.action_type.value

    executed_request = (
        adapter_registry.get.return_value.execute.call_args[0][0]
    )
    assert executed_request.target == action.component
    assert executed_request.operation == action.action_type.value
    # REMOVE is governed as high risk; the continuation must carry it.
    assert executed_request.risk_level == "high"

    adapter_registry.get.assert_called_once()
    adapter_registry.get.return_value.execute.assert_called_once()


def test_changed_held_instruction_blocks_before_authorization_and_adapter(monkeypatch):
    auth_storage, _, _, hold_storage, adapter_registry = _setup_isolation(monkeypatch)
    action = _make_action(ActionType.REMOVE)
    action.parameters = {"amount": "1500.00"}
    held = actions_service_module.execute_governed_action(
        action,
        adapter_name="simulation",
    )
    hold = hold_storage.get_by_id(held["approval_id"])
    hold.action.parameters["amount"] = "9000.00"

    result = approval_service_module.approve_held_action(
        hold.approval_id,
        approved_by="operator",
        approved=True,
    )

    assert result["status"] == "assessment_invalid"
    assert auth_storage.get_all() == []
    adapter_registry.get.assert_not_called()


def test_governed_risk_propagated_into_execution_evidence(monkeypatch):
    """
    C. The governed risk from simulation is carried into execution and
    recorded in trace/audit, rather than re-derived by the execution-risk
    analyzer (which would classify restart_component as low).
    """
    (
        auth_storage,
        trace_storage,
        audit_storage,
        hold_storage,
        adapter_registry,
    ) = _setup_isolation(monkeypatch)

    action = _make_action(ActionType.RESTART_COMPONENT)

    result = actions_service_module.execute_governed_action(
        action,
        adapter_name="simulation",
    )

    assert result["status"] == "executed"

    # restart_component is governed as medium; the execution-risk analyzer
    # would have said low. Recording medium proves the carried risk is used.
    assert len(trace_storage.get_all()) == 1
    assert trace_storage.get_all()[0].risk_level == "medium"

    assert len(audit_storage.get_all()) == 1
    assert audit_storage.get_all()[0].risk_level == "medium"


def test_manual_approval_rejection_terminates_adapter_not_called(
    monkeypatch,
):
    """
    N02. A rejected manual approval terminates the path; adapter not called.
    """
    (
        auth_storage,
        trace_storage,
        audit_storage,
        hold_storage,
        adapter_registry,
    ) = _setup_isolation(monkeypatch)

    action = _make_action(ActionType.REMOVE)

    held = actions_service_module.execute_governed_action(
        action,
        adapter_name="simulation",
    )
    approval_id = held["approval_id"]

    result = approval_service_module.approve_held_action(
        approval_id,
        approved_by="operator",
        approved=False,
    )

    assert result["status"] == "rejected"

    assert len(auth_storage.get_all()) == 0
    adapter_registry.get.assert_not_called()


def test_approve_unknown_approval_id_not_found(monkeypatch):
    """
    A continuation for an unknown approval id is rejected.
    """
    (
        auth_storage,
        trace_storage,
        audit_storage,
        hold_storage,
        adapter_registry,
    ) = _setup_isolation(monkeypatch)

    result = approval_service_module.approve_held_action(
        "nonexistent-approval",
        approved_by="operator",
        approved=True,
    )

    assert result["status"] == "approval_not_found"
    adapter_registry.get.assert_not_called()


def test_auto_authorization_carries_provenance(monkeypatch):
    """
    An auto-approved authorization is bound to the governed action and
    approval (decision_id, approval_id) and carries an expiry window.
    """
    (
        auth_storage,
        trace_storage,
        audit_storage,
        hold_storage,
        adapter_registry,
    ) = _setup_isolation(monkeypatch)

    action = _make_action(ActionType.RESTART)

    result = actions_service_module.execute_governed_action(
        action,
        adapter_name="simulation",
    )

    assert result["status"] == "executed"

    auth = auth_storage.get_all()[0]
    assert auth.decision_id == action.decision_id
    assert auth.approval_id is not None
    assert auth.expires_at is not None
    assert auth.expires_at > datetime.now(timezone.utc)


def test_expired_authorization_blocked_adapter_not_called(monkeypatch):
    """
    N10. An expired authorization is blocked before the adapter.
    """
    (
        auth_storage,
        trace_storage,
        audit_storage,
        hold_storage,
        adapter_registry,
    ) = _setup_isolation(monkeypatch)

    expired = ExecutionAuthorization(
        authorization_id="auth-expired",
        action_id="action-restart",
        status=AuthorizationStatus.APPROVED,
        target="test-container",
        operation="restart",
        expires_at=datetime.now(timezone.utc) - timedelta(seconds=1),
    )
    auth_storage.save(expired)

    request = ExecutionRequest(
        execution_id="exec-expired",
        authorization_id="auth-expired",
        action_id="action-restart",
        target="test-container",
        operation="restart",
    )

    result = execution_engine_module.ExecutionEngine().execute(request)

    assert result.status == "failed"
    assert result.success is False
    assert result.message == "Authorization expired"

    adapter_registry.get.assert_not_called()


def test_approval_required_action_held_adapter_not_called(monkeypatch):
    """
    N03. An action that requires approval cannot execute without it.
    """
    (
        auth_storage,
        trace_storage,
        audit_storage,
        hold_storage,
        adapter_registry,
    ) = _setup_isolation(monkeypatch)

    action = _make_action(ActionType.RESTART)
    action.requires_approval = True

    result = actions_service_module.execute_governed_action(
        action,
        adapter_name="simulation",
    )

    assert result["status"] == "manual_approval_required"

    assert len(auth_storage.get_all()) == 0
    adapter_registry.get.assert_not_called()


def test_synthetic_authorization_does_not_grant_execution(monkeypatch):
    """
    N11. A caller-supplied authorization identifier is not sufficient; the
    authorization must correspond to a legitimate governed lifecycle state.
    """
    (
        auth_storage,
        trace_storage,
        audit_storage,
        hold_storage,
        adapter_registry,
    ) = _setup_isolation(monkeypatch)

    request = ExecutionRequest(
        execution_id="exec-synthetic",
        authorization_id="fabricated-auth-id",
        action_id="action-restart",
        target="test-container",
        operation="restart",
    )

    result = execution_engine_module.ExecutionEngine().execute(request)

    assert result.status == "failed"
    assert result.success is False
    assert result.message == "Authorization not found"

    adapter_registry.get.assert_not_called()


def test_governance_bypass_direct_engine_call_blocked(monkeypatch):
    """
    N12. A production mutation entrypoint that does not pass the governed
    lifecycle cannot invoke the adapter. Calling the engine directly with a
    fabricated authorization is blocked before the adapter.
    """
    (
        auth_storage,
        trace_storage,
        audit_storage,
        hold_storage,
        adapter_registry,
    ) = _setup_isolation(monkeypatch)

    request = ExecutionRequest(
        execution_id="exec-bypass",
        authorization_id="bypass-auth",
        action_id="action-any",
        target="any-target",
        operation="restart",
    )

    result = execution_engine_module.ExecutionEngine().execute(request)

    assert result.status == "failed"
    assert result.success is False

    adapter_registry.get.assert_not_called()


def test_expired_approval_hold_cannot_continue(monkeypatch):
    """
    An expired manual-approval hold cannot be continued.
    """
    from app.core.intelligence.actions.approval import (
        ApprovalHold,
    )

    (
        auth_storage,
        trace_storage,
        audit_storage,
        hold_storage,
        adapter_registry,
    ) = _setup_isolation(monkeypatch)

    action = _make_action(ActionType.REMOVE)

    expired_hold = ApprovalHold(
        action_id=action.action_id,
        action=action,
        adapter_name="simulation",
        reason="test",
        expires_at=datetime.now(timezone.utc) - timedelta(seconds=1),
    )
    hold_storage.save(expired_hold)

    result = approval_service_module.approve_held_action(
        expired_hold.approval_id,
        approved_by="operator",
        approved=True,
    )

    assert result["status"] == "approval_expired"

    assert len(auth_storage.get_all()) == 0
    adapter_registry.get.assert_not_called()
