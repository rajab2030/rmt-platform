from unittest.mock import Mock

import app.core.intelligence.execution.engine as execution_engine_module

from app.core.intelligence.actions.authorization import (
    ExecutionAuthorization,
    AuthorizationStatus,
)
from app.core.intelligence.actions.authorization_storage import (
    AuthorizationStorage,
)
from app.core.intelligence.execution.models import ExecutionRequest, ExecutionResult
from app.core.intelligence.execution.policy import PolicyDecision
from app.core.intelligence.execution.risk import ExecutionRisk
from app.core.intelligence.execution.storage import ExecutionAuditStorage
from app.core.intelligence.execution.trace_storage import ExecutionTraceStorage
from app.core.intelligence.actions.binding import (
    CANONICALIZATION_VERSION,
    bind_execution_request,
)


def _make_auth(
    authorization_id: str,
    status: str,
    action_id: str,
    target: str,
    operation: str,
) -> ExecutionAuthorization:
    return ExecutionAuthorization(
        authorization_id=authorization_id,
        status=status,
        action_id=action_id,
        target=target,
        operation=operation,
        authorized_by="test",
        authorization_type="test",
    )


def _setup_isolation(monkeypatch):
    isolated_authorization_storage = AuthorizationStorage()
    isolated_trace_storage = ExecutionTraceStorage()
    isolated_audit_storage_obj = ExecutionAuditStorage()
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
        isolated_audit_storage_obj,
    )
    monkeypatch.setattr(
        execution_engine_module,
        "adapter_registry",
        adapter_registry,
    )

    return (
        isolated_authorization_storage,
        isolated_trace_storage,
        isolated_audit_storage_obj,
        adapter_registry,
    )


def _bind(auth, request, adapter_name="simulation"):
    request.adapter_name = adapter_name
    request.canonicalization_version = CANONICALIZATION_VERSION
    digest, _ = bind_execution_request(request, adapter_name)
    request.instruction_digest = digest
    auth.adapter_name = adapter_name
    auth.canonicalization_version = CANONICALIZATION_VERSION
    auth.instruction_digest = digest

def test_valid_approved_authorization_proceeds_to_simulation_adapter(
    monkeypatch,
):
    """
    A. Valid APPROVED authorization -> simulation execution succeeds.
    Proves that a valid authorization reaches the existing risk/policy/adapter path.
    """
    (
        auth_storage,
        trace_storage,
        audit_storage,
        adapter_registry,
    ) = _setup_isolation(monkeypatch)

    auth = _make_auth(
        authorization_id="auth-valid",
        status=AuthorizationStatus.APPROVED,
        action_id="action-restart",
        target="test-container",
        operation="restart",
    )
    request = ExecutionRequest(
        execution_id="exec-valid",
        authorization_id="auth-valid",
        action_id="action-restart",
        target="test-container",
        operation="restart",
    )
    _bind(auth, request)
    auth_storage.save(auth)

    result = execution_engine_module.ExecutionEngine().execute(request)

    traces = trace_storage.get_all()
    audits = audit_storage.get_all()

    assert result.status == "completed"
    assert result.success is True

    adapter_registry.get.assert_called_once()

    assert len(traces) == 1
    trace = traces[0]
    assert trace.execution_id == request.execution_id
    assert trace.action_id == request.action_id
    assert trace.authorization_id == request.authorization_id
    assert trace.policy_decision == PolicyDecision.ALLOW.value
    assert trace.risk_level == ExecutionRisk.MEDIUM.value
    assert trace.outcome == "completed"

    assert len(audits) == 1


def test_missing_authorization_blocked_adapter_not_called(
    monkeypatch,
):
    """
    B. Missing authorization -> blocked, adapter not called.
    """
    (
        auth_storage,
        trace_storage,
        audit_storage,
        adapter_registry,
    ) = _setup_isolation(monkeypatch)

    request = ExecutionRequest(
        execution_id="exec-missing",
        authorization_id="nonexistent-auth",
        action_id="action-any",
        target="target-any",
        operation="restart",
    )

    result = execution_engine_module.ExecutionEngine().execute(request)

    traces = trace_storage.get_all()
    audits = audit_storage.get_all()

    assert result.status == "failed"
    assert result.success is False
    assert result.message == "Authorization not found"

    adapter_registry.get.assert_not_called()

    assert len(traces) == 1
    trace = traces[0]
    assert trace.execution_id == request.execution_id
    assert trace.action_id == request.action_id
    assert trace.authorization_id == request.authorization_id
    assert trace.policy_decision == "not_evaluated"
    assert trace.risk_level == "not_evaluated"
    assert trace.outcome == "blocked"
    assert trace.reason == "Authorization not found"

    assert len(audits) == 0


def test_non_approved_authorization_blocked_adapter_not_called(
    monkeypatch,
):
    """
    C. Non-approved authorization -> blocked, adapter not called.
    """
    (
        auth_storage,
        trace_storage,
        audit_storage,
        adapter_registry,
    ) = _setup_isolation(monkeypatch)

    auth = _make_auth(
        authorization_id="auth-pending",
        status=AuthorizationStatus.PENDING,
        action_id="action-any",
        target="target-any",
        operation="restart",
    )
    auth_storage.save(auth)

    request = ExecutionRequest(
        execution_id="exec-pending",
        authorization_id="auth-pending",
        action_id="action-any",
        target="target-any",
        operation="restart",
    )

    result = execution_engine_module.ExecutionEngine().execute(request)

    traces = trace_storage.get_all()

    assert result.status == "failed"
    assert result.success is False
    assert result.message == "Authorization not approved"

    adapter_registry.get.assert_not_called()

    assert len(traces) == 1
    trace = traces[0]
    assert trace.outcome == "blocked"
    assert trace.policy_decision == "not_evaluated"
    assert trace.risk_level == "not_evaluated"
    assert trace.reason == "Authorization not approved"


def test_wrong_action_id_blocked_adapter_not_called(
    monkeypatch,
):
    """
    D. Wrong action_id -> blocked, adapter not called.
    """
    (
        auth_storage,
        trace_storage,
        audit_storage,
        adapter_registry,
    ) = _setup_isolation(monkeypatch)

    auth = _make_auth(
        authorization_id="auth-wrong-action",
        status=AuthorizationStatus.APPROVED,
        action_id="wrong-action-id",
        target="test-container",
        operation="restart",
    )
    auth_storage.save(auth)

    request = ExecutionRequest(
        execution_id="exec-wrong-action",
        authorization_id="auth-wrong-action",
        action_id="correct-action-id",
        target="test-container",
        operation="restart",
    )

    result = execution_engine_module.ExecutionEngine().execute(request)

    traces = trace_storage.get_all()

    assert result.status == "failed"
    assert result.success is False
    assert result.message == "Authorization action_id mismatch"

    adapter_registry.get.assert_not_called()

    assert len(traces) == 1
    trace = traces[0]
    assert trace.outcome == "blocked"
    assert trace.policy_decision == "not_evaluated"
    assert trace.risk_level == "not_evaluated"
    assert trace.reason == "Authorization action_id mismatch"


def test_wrong_target_blocked_adapter_not_called(
    monkeypatch,
):
    """
    E. Wrong target -> blocked, adapter not called.
    """
    (
        auth_storage,
        trace_storage,
        audit_storage,
        adapter_registry,
    ) = _setup_isolation(monkeypatch)

    auth = _make_auth(
        authorization_id="auth-wrong-target",
        status=AuthorizationStatus.APPROVED,
        action_id="action-any",
        target="wrong-target",
        operation="restart",
    )
    auth_storage.save(auth)

    request = ExecutionRequest(
        execution_id="exec-wrong-target",
        authorization_id="auth-wrong-target",
        action_id="action-any",
        target="correct-target",
        operation="restart",
    )

    result = execution_engine_module.ExecutionEngine().execute(request)

    traces = trace_storage.get_all()

    assert result.status == "failed"
    assert result.success is False
    assert result.message == "Authorization target mismatch"

    adapter_registry.get.assert_not_called()

    assert len(traces) == 1
    trace = traces[0]
    assert trace.outcome == "blocked"
    assert trace.policy_decision == "not_evaluated"
    assert trace.risk_level == "not_evaluated"
    assert trace.reason == "Authorization target mismatch"


def test_wrong_operation_blocked_adapter_not_called(
    monkeypatch,
):
    """
    F. Wrong operation -> blocked, adapter not called.
    """
    (
        auth_storage,
        trace_storage,
        audit_storage,
        adapter_registry,
    ) = _setup_isolation(monkeypatch)

    auth = _make_auth(
        authorization_id="auth-wrong-op",
        status=AuthorizationStatus.APPROVED,
        action_id="action-any",
        target="test-container",
        operation="restart",
    )
    auth_storage.save(auth)

    request = ExecutionRequest(
        execution_id="exec-wrong-op",
        authorization_id="auth-wrong-op",
        action_id="action-any",
        target="test-container",
        operation="wipe",
    )

    result = execution_engine_module.ExecutionEngine().execute(request)

    traces = trace_storage.get_all()

    assert result.status == "failed"
    assert result.success is False
    assert result.message == "Authorization operation mismatch"

    adapter_registry.get.assert_not_called()

    assert len(traces) == 1
    trace = traces[0]
    assert trace.outcome == "blocked"
    assert trace.policy_decision == "not_evaluated"
    assert trace.risk_level == "not_evaluated"
    assert trace.reason == "Authorization operation mismatch"


def test_valid_authorization_wipe_execution_policy_deny(
    monkeypatch,
):
    """
    G. Valid authorization + wipe -> execution policy DENY still blocks.
    Proves that authorization verification passes but existing policy denial
    remains enforced, and the trace correctly records policy="deny".
    """
    (
        auth_storage,
        trace_storage,
        audit_storage,
        adapter_registry,
    ) = _setup_isolation(monkeypatch)

    auth = _make_auth(
        authorization_id="auth-wipe",
        status=AuthorizationStatus.APPROVED,
        action_id="action-wipe",
        target="test-container",
        operation="wipe",
    )
    request = ExecutionRequest(
        execution_id="exec-wipe",
        authorization_id="auth-wipe",
        action_id="action-wipe",
        target="test-container",
        operation="wipe",
    )
    _bind(auth, request)
    auth_storage.save(auth)

    result = execution_engine_module.ExecutionEngine().execute(request)

    traces = trace_storage.get_all()

    assert result.status == "failed"
    assert result.success is False
    assert result.message == "Execution blocked by policy: deny"

    adapter_registry.get.assert_not_called()

    assert len(traces) == 1
    trace = traces[0]
    assert trace.execution_id == request.execution_id
    assert trace.action_id == request.action_id
    assert trace.authorization_id == request.authorization_id
    assert trace.policy_decision == PolicyDecision.DENY.value
    assert trace.risk_level == ExecutionRisk.HIGH.value
    assert trace.outcome == "blocked"
    assert trace.reason == "Execution blocked by policy: deny"


def test_valid_authorization_restart_simulation_audit_trace_produced(
    monkeypatch,
):
    """
    H. Valid authorization + restart -> simulation adapter executes
    and audit + trace are produced.
    """
    (
        auth_storage,
        trace_storage,
        audit_storage,
        adapter_registry,
    ) = _setup_isolation(monkeypatch)

    auth = _make_auth(
        authorization_id="auth-restart",
        status=AuthorizationStatus.APPROVED,
        action_id="action-restart",
        target="test-container",
        operation="restart",
    )
    request = ExecutionRequest(
        execution_id="exec-restart",
        authorization_id="auth-restart",
        action_id="action-restart",
        target="test-container",
        operation="restart",
    )
    _bind(auth, request)
    auth_storage.save(auth)

    result = execution_engine_module.ExecutionEngine().execute(request)

    traces = trace_storage.get_all()
    audits = audit_storage.get_all()

    assert result.status == "completed"
    assert result.success is True

    adapter_registry.get.assert_called_once()

    assert len(traces) == 1
    trace = traces[0]
    assert trace.execution_id == result.execution_id
    assert trace.action_id == request.action_id
    assert trace.authorization_id == request.authorization_id
    assert trace.policy_decision == PolicyDecision.ALLOW.value
    assert trace.risk_level == ExecutionRisk.MEDIUM.value
    assert trace.outcome == "completed"

    assert len(audits) == 1
    audit = audits[0]
    assert audit.execution_id == result.execution_id
    assert audit.action_id == request.action_id
    assert audit.authorization_id == request.authorization_id
    assert audit.adapter == "simulation"
    assert audit.status == "completed"


def test_changed_parameters_after_authorization_block_before_adapter(monkeypatch):
    auth_storage, trace_storage, _, adapter_registry = _setup_isolation(monkeypatch)
    auth = _make_auth(
        authorization_id="auth-bound-parameters",
        status=AuthorizationStatus.APPROVED,
        action_id="action-bound-parameters",
        target="test-container",
        operation="restart",
    )
    request = ExecutionRequest(
        authorization_id=auth.authorization_id,
        action_id=auth.action_id,
        target=auth.target,
        operation=auth.operation,
        parameters={"amount": "1500.00"},
    )
    _bind(auth, request)
    auth_storage.save(auth)

    request.parameters["amount"] = "9000.00"
    result = execution_engine_module.ExecutionEngine().execute(request)

    assert result.success is False
    assert result.message == "Execution instruction binding mismatch"
    adapter_registry.get.assert_not_called()
    assert trace_storage.get_all()[0].outcome == "blocked"


def test_changed_adapter_after_authorization_block_before_lookup(monkeypatch):
    auth_storage, _, _, adapter_registry = _setup_isolation(monkeypatch)
    auth = _make_auth(
        authorization_id="auth-bound-adapter",
        status=AuthorizationStatus.APPROVED,
        action_id="action-bound-adapter",
        target="test-container",
        operation="restart",
    )
    request = ExecutionRequest(
        authorization_id=auth.authorization_id,
        action_id=auth.action_id,
        target=auth.target,
        operation=auth.operation,
    )
    _bind(auth, request, adapter_name="simulation")
    auth_storage.save(auth)

    result = execution_engine_module.ExecutionEngine().execute(
        request,
        adapter_name="docker",
    )

    assert result.success is False
    assert result.message == "Authorization instruction or adapter binding mismatch"
    adapter_registry.get.assert_not_called()
