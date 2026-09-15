"""
C03 validation: post-execution verification.

Proves the Execute -> Observe -> Verify -> Record control loop:
    - the four verification outcomes are distinguishable;
    - verification is connected to the governed execution path;
    - the expected outcome travels through authorization and execution and
      cannot be substituted;
    - verification evidence is correlated to the execution and durable.
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
from app.core.intelligence.actions.approval_storage import (
    ApprovalHoldStorage,
    ApprovalRecordStorage,
)
from app.core.intelligence.execution.models import (
    ExecutionRequest,
    ExecutionResult,
)
from app.core.intelligence.execution.storage import ExecutionAuditStorage
from app.core.intelligence.execution.trace_storage import ExecutionTraceStorage
from app.core.intelligence.verification.models import (
    VerificationResult,
    VerificationStatus,
    ExpectedOutcome,
    ObservedState,
)
from app.core.intelligence.verification.verifier import verifier
from app.core.intelligence.verification.storage import VerificationStorage
from app.core.intelligence.actions.binding import (
    CANONICALIZATION_VERSION,
    bind_execution_request,
)


def _make_action(
    action_type: ActionType,
    component: str = "test-container",
    confidence: int = 100,
    expected_state: str = "running",
) -> ActionRequest:
    return ActionRequest(
        decision_id="test-decision",
        component=component,
        action_type=action_type,
        reason="test",
        confidence=confidence,
        requires_approval=False,
        expected_outcome=ExpectedOutcome(
            target=component,
            operation=action_type.value,
            expected_state=expected_state,
        ),
    )


def _setup_isolation(monkeypatch):
    """
    Wire the governed pipeline, the execution engine, and the verification
    service to the same isolated in-memory storage and a mock adapter.
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
        isolated_verification_storage,
        adapter_registry,
    )


# ---------------------------------------------------------------------------
# 1-4. The four verification outcomes (verifier unit tests)
# ---------------------------------------------------------------------------

def test_verified_success():
    result = verifier.verify(
        "exec-1",
        ExpectedOutcome(target="c", operation="restart", expected_state="running"),
        ObservedState(target="c", state="running"),
    )
    assert result.status == VerificationStatus.VERIFIED_SUCCESS
    assert result.execution_id == "exec-1"


def test_state_mismatch():
    result = verifier.verify(
        "exec-1",
        ExpectedOutcome(target="c", operation="restart", expected_state="running"),
        ObservedState(target="c", state="stopped"),
    )
    assert result.status == VerificationStatus.STATE_MISMATCH


def test_observation_unavailable():
    result = verifier.verify(
        "exec-1",
        ExpectedOutcome(target="c", operation="restart", expected_state="running"),
        None,
    )
    assert result.status == VerificationStatus.OBSERVATION_UNAVAILABLE


def test_verification_failure_missing_expectation():
    result = verifier.verify("exec-1", None, ObservedState(target="c", state="running"))
    assert result.status == VerificationStatus.VERIFICATION_FAILURE


# ---------------------------------------------------------------------------
# 5. Execution/verification correlation
# ---------------------------------------------------------------------------

def test_verification_correlated_to_execution(monkeypatch):
    (
        auth_storage, trace_storage, audit_storage,
        verification_storage, adapter_registry,
    ) = _setup_isolation(monkeypatch)

    action = _make_action(ActionType.RESTART)

    result = actions_service_module.execute_governed_action(
        action, adapter_name="simulation"
    )

    assert result["status"] == "executed"
    # Generic (non-module) actions have no trusted observer: safe-failure.
    assert result["verification_status"] == VerificationStatus.OBSERVATION_UNAVAILABLE

    records = verification_storage.get_all()
    assert len(records) == 1
    assert records[0].execution_id == result["execution_id"]


# ---------------------------------------------------------------------------
# 6. Governed execution invokes verification
# ---------------------------------------------------------------------------

def test_governed_execution_invokes_verification(monkeypatch):
    (
        auth_storage, trace_storage, audit_storage,
        verification_storage, adapter_registry,
    ) = _setup_isolation(monkeypatch)

    action = _make_action(ActionType.RESTART)

    result = actions_service_module.execute_governed_action(
        action, adapter_name="simulation"
    )

    # Generic (non-module) actions have no trusted observer: safe-failure.
    assert result["verification_status"] == VerificationStatus.OBSERVATION_UNAVAILABLE
    assert len(verification_storage.get_all()) == 1


# ---------------------------------------------------------------------------
# 7 & 10. Expected-outcome authorization mismatch blocked before adapter
# ---------------------------------------------------------------------------

def test_expected_outcome_mismatch_blocked_before_adapter(monkeypatch):
    (
        auth_storage, trace_storage, audit_storage,
        verification_storage, adapter_registry,
    ) = _setup_isolation(monkeypatch)

    auth = ExecutionAuthorization(
        authorization_id="auth-1",
        action_id="action-1",
        status=AuthorizationStatus.APPROVED,
        target="web",
        operation="restart",
        expected_outcome=ExpectedOutcome(
            target="web", operation="restart", expected_state="running"
        ),
    )
    auth_storage.save(auth)

    request = ExecutionRequest(
        authorization_id="auth-1",
        action_id="action-1",
        target="web",
        operation="restart",
        expected_outcome=ExpectedOutcome(
            target="web", operation="restart", expected_state="stopped"
        ),
    )

    result = execution_engine_module.execution_engine.execute(request)

    assert result.status == "failed"
    assert "expected_outcome mismatch" in result.message
    adapter_registry.get.assert_not_called()


# ---------------------------------------------------------------------------
# 8. Manual approval continuation invokes verification
# ---------------------------------------------------------------------------

def test_manual_approval_continuation_invokes_verification(monkeypatch):
    (
        auth_storage, trace_storage, audit_storage,
        verification_storage, adapter_registry,
    ) = _setup_isolation(monkeypatch)

    # remove is high-risk -> held for manual approval
    action = _make_action(ActionType.REMOVE, expected_state="removed")
    held = actions_service_module.execute_governed_action(
        action, adapter_name="simulation"
    )
    assert held["status"] == "manual_approval_required"

    result = approval_service_module.approve_held_action(
        held["approval_id"], approved_by="operator", approved=True
    )

    assert result["status"] == "executed"
    # Generic (non-module) actions have no trusted observer: safe-failure.
    assert result["verification_status"] == VerificationStatus.OBSERVATION_UNAVAILABLE
    assert len(verification_storage.get_all()) == 1


# ---------------------------------------------------------------------------
# 9. Verification evidence is durable
# ---------------------------------------------------------------------------

def test_verification_evidence_durable(tmp_path):
    path = tmp_path / "verifications.json"
    store1 = VerificationStorage(file_path=path)
    store1.save(VerificationResult(
        execution_id="exec-1",
        status=VerificationStatus.VERIFIED_SUCCESS,
        expected=ExpectedOutcome(target="c", operation="restart", expected_state="running"),
        observed=ObservedState(target="c", state="running"),
    ))

    store2 = VerificationStorage(file_path=path)
    assert len(store2.get_all()) == 1
    rec = store2.get_by_execution_id("exec-1")
    assert rec is not None
    assert rec.status == VerificationStatus.VERIFIED_SUCCESS
    assert rec.expected.expected_state == "running"


# ---------------------------------------------------------------------------
# 11. Missing expectation is not confused with authorization failure
# ---------------------------------------------------------------------------

def test_missing_expectation_is_verification_limitation_not_auth_failure(monkeypatch):
    (
        auth_storage, trace_storage, audit_storage,
        verification_storage, adapter_registry,
    ) = _setup_isolation(monkeypatch)

    auth = ExecutionAuthorization(
        authorization_id="auth-1",
        action_id="action-1",
        status=AuthorizationStatus.APPROVED,
        target="web",
        operation="restart",
        expected_outcome=None,
    )

    request = ExecutionRequest(
        authorization_id="auth-1",
        action_id="action-1",
        target="web",
        operation="restart",
        expected_outcome=None,
        adapter_name="simulation",
        canonicalization_version=CANONICALIZATION_VERSION,
    )
    digest, _ = bind_execution_request(request, "simulation")
    request.instruction_digest = digest
    auth.adapter_name = "simulation"
    auth.canonicalization_version = CANONICALIZATION_VERSION
    auth.instruction_digest = digest
    auth_storage.save(auth)

    result = execution_engine_module.execution_engine.execute(request)

    # Not an authorization mismatch: execution proceeds to the adapter.
    assert "expected_outcome mismatch" not in result.message
    adapter_registry.get.assert_called_once()
