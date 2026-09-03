"""
C05 validation: Controlled Platform Self-Management.

Proves that a bounded self-management operation travels through the complete
governed lifecycle (Understand -> Decide -> Govern -> Authorize -> Execute ->
Verify -> Audit) using the existing Core machinery, that out-of-bound
operations are blocked before the mutation boundary, and that read-only
observation is distinct from mutation authority.
"""
from unittest.mock import Mock

import app.core.intelligence.execution.engine as execution_engine_module
import app.core.intelligence.actions.service as actions_service_module
import app.core.intelligence.actions.approval_service as approval_service_module
import app.core.intelligence.verification.service as verification_service_module
import app.core.self_management.service as self_management_module

from app.core.intelligence.decision.models import IntelligenceDecision
from app.core.intelligence.actions.models import ActionRequest
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
from app.core.intelligence.verification.models import ExpectedOutcome
from app.core.module_registry.schema import Module, RuntimeInfo, HealthInfo
from app.core.configuration.public import PublicConfiguration
from app.core.self_management.models import SelfManagementState


def _registered_module(container="control-center"):
    return Module(
        module_id="control-center",
        name="RMT Platform Control Center",
        description="Platform management console",
        version="0.1.0",
        type="platform-service",
        status="active",
        runtime=RuntimeInfo(
            engine="docker",
            service="fastapi-react",
            container=container,
            ports=[8000],
        ),
        dependencies=[],
        configuration={},
        health=HealthInfo(status="healthy"),
    )


def _decision(
    component="control-center",
    action="restart_component",
    confidence=100,
):
    return IntelligenceDecision(
        component=component,
        priority="high",
        action=action,
        reason="Bounded self-management restart",
        confidence=confidence,
        intended_outcome=ExpectedOutcome(
            target=component,
            operation="restart",
            expected_state="running",
        ),
    )


def _setup_isolation(monkeypatch):
    """
    Wire the governed pipeline and the execution engine to the same isolated
    in-memory storage and a mock adapter, so we can observe whether the
    adapter is invoked and whether evidence is recorded.
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
        isolated_approval_record_storage,
        isolated_verification_storage,
        adapter_registry,
    )


def test_positive_self_management_full_lifecycle(monkeypatch):
    """
    P01. A bounded self-management restart of a permitted platform component
    travels through the complete governed lifecycle and executes through the
    existing authoritative boundary.
    """
    (
        auth_storage,
        trace_storage,
        audit_storage,
        approval_record_storage,
        verification_storage,
        adapter_registry,
    ) = _setup_isolation(monkeypatch)

    monkeypatch.setattr(
        self_management_module,
        "get_modules",
        lambda: [_registered_module()],
    )

    # Spy on the existing decision->action translator to prove the decision
    # stage is genuinely involved (no second decision engine).
    calls = []
    original_translate = self_management_module.decision_to_action

    def spy_translate(decision):
        calls.append(decision)
        return original_translate(decision)

    monkeypatch.setattr(
        self_management_module,
        "decision_to_action",
        spy_translate,
    )

    decision = _decision()

    result = self_management_module.self_management_service.execute_self_management_decision(
        decision,
        adapter_name="simulation",
    )

    assert result["status"] == "executed"
    assert result["success"] is True

    # 1. Decision stage genuinely involved: the existing translator was called
    #    with the IntelligenceDecision.
    assert len(calls) == 1
    assert isinstance(calls[0], IntelligenceDecision)
    assert calls[0].action == "restart_component"

    # 2. Authorization created through the governed lifecycle.
    assert len(auth_storage.get_all()) == 1
    auth = auth_storage.get_all()[0]
    assert auth.target == "control-center"
    assert auth.operation == "restart_component"

    # 3. Controlled execution: adapter invoked exactly once.
    adapter_registry.get.assert_called_once()
    adapter_registry.get.return_value.execute.assert_called_once()

    # 4. Durable audit + trace evidence recorded.
    assert len(audit_storage.get_all()) == 1
    assert len(trace_storage.get_all()) == 1

    # 5. Post-execution verification recorded, correlated to execution, using
    #    the decision's explicit expected outcome (C03), not manufactured.
    assert len(verification_storage.get_all()) == 1
    verification = verification_storage.get_all()[0]
    assert verification.execution_id == result["execution_id"]
    assert verification.expected == decision.intended_outcome


def test_self_management_routes_through_existing_governed_boundary(monkeypatch):
    """
    P02. The self-management layer routes through the existing authoritative
    governed mutation boundary (execute_governed_action), not a new one.
    """
    (
        auth_storage,
        trace_storage,
        audit_storage,
        approval_record_storage,
        verification_storage,
        adapter_registry,
    ) = _setup_isolation(monkeypatch)

    monkeypatch.setattr(
        self_management_module,
        "get_modules",
        lambda: [_registered_module()],
    )

    calls = []
    original = self_management_module.execute_governed_action

    def spy(action, adapter_name="simulation"):
        calls.append(action)
        return original(action, adapter_name=adapter_name)

    monkeypatch.setattr(
        self_management_module,
        "execute_governed_action",
        spy,
    )

    decision = _decision()

    result = self_management_module.self_management_service.execute_self_management_decision(
        decision,
        adapter_name="simulation",
    )

    assert result["status"] == "executed"
    assert len(calls) == 1
    assert isinstance(calls[0], ActionRequest)
    assert calls[0].component == "control-center"
    assert calls[0].action_type.value == "restart_component"
    # The decision's intended outcome is carried as the action's expected
    # outcome (C03), not manufactured inside verification.
    assert calls[0].expected_outcome == decision.intended_outcome


def test_negative_out_of_bound_target_blocked(monkeypatch):
    """
    N01. An out-of-bound target is rejected by the self-management boundary.
    The mutation boundary is never reached: no authorization, no execution,
    no adapter invocation. Blocked/deny evidence remains available through the
    existing approval-record evidence mechanism.
    """
    (
        auth_storage,
        trace_storage,
        audit_storage,
        approval_record_storage,
        verification_storage,
        adapter_registry,
    ) = _setup_isolation(monkeypatch)

    monkeypatch.setattr(
        self_management_module,
        "get_modules",
        lambda: [_registered_module()],
    )

    decision = _decision(component="not-a-registered-component")

    result = self_management_module.self_management_service.execute_self_management_decision(
        decision,
        adapter_name="simulation",
    )

    assert result["status"] == "blocked"
    assert "not a permitted" in result["reason"]

    # Mutation boundary never reached.
    assert len(auth_storage.get_all()) == 0
    adapter_registry.get.assert_not_called()
    adapter_registry.get.return_value.execute.assert_not_called()

    # No execution evidence (audit/trace) was produced.
    assert len(audit_storage.get_all()) == 0
    assert len(trace_storage.get_all()) == 0

    # Blocked/deny evidence remains available through the existing
    # approval-record evidence mechanism.
    assert len(approval_record_storage.get_all()) == 1
    blocked = approval_record_storage.get_all()[0]
    assert blocked.decision == "rejected"
    assert blocked.approved_by == "self_management_boundary"


def test_negative_unsupported_operation_blocked(monkeypatch):
    """
    N02. An operation outside the bounded self-management set is rejected
    before any action is created or executed.
    """
    (
        auth_storage,
        trace_storage,
        audit_storage,
        approval_record_storage,
        verification_storage,
        adapter_registry,
    ) = _setup_isolation(monkeypatch)

    monkeypatch.setattr(
        self_management_module,
        "get_modules",
        lambda: [_registered_module()],
    )

    decision = _decision(action="remove")

    result = self_management_module.self_management_service.execute_self_management_decision(
        decision,
        adapter_name="simulation",
    )

    assert result["status"] == "blocked"
    assert "not supported" in result["reason"]

    assert len(auth_storage.get_all()) == 0
    adapter_registry.get.assert_not_called()
    adapter_registry.get.return_value.execute.assert_not_called()
    assert len(audit_storage.get_all()) == 0
    assert len(trace_storage.get_all()) == 0


def test_read_only_observation_does_not_mutate(monkeypatch):
    """
    R01. Read-only platform state observation (identity/version, capability,
    configuration) is distinct from mutation authority: it creates no
    authorization, records no approval, and executes nothing.
    """
    (
        auth_storage,
        trace_storage,
        audit_storage,
        approval_record_storage,
        verification_storage,
        adapter_registry,
    ) = _setup_isolation(monkeypatch)

    monkeypatch.setattr(
        self_management_module,
        "get_modules",
        lambda: [_registered_module()],
    )
    monkeypatch.setattr(
        self_management_module,
        "load_settings",
        lambda: None,
    )
    monkeypatch.setattr(
        self_management_module,
        "create_public_config",
        lambda settings: PublicConfiguration(
            platform_name="RMT Platform",
            platform_version="0.3",
            environment="homelab",
            api_host="0.0.0.0",
            api_port=8000,
            runtime_engine="docker",
        ),
    )

    state = self_management_module.self_management_service.observe_platform_state()

    assert isinstance(state, SelfManagementState)
    assert state.identity.platform == "RMT Platform"
    assert state.identity.version == "0.3"
    assert len(state.capabilities) == 1
    assert state.capabilities[0].runtime.container == "control-center"
    assert state.configuration.platform_name == "RMT Platform"

    # Observing state created no authorization, recorded no approval, executed
    # nothing, and did not invoke any adapter.
    assert len(auth_storage.get_all()) == 0
    assert len(approval_record_storage.get_all()) == 0
    assert len(audit_storage.get_all()) == 0
    assert len(trace_storage.get_all()) == 0
    adapter_registry.get.assert_not_called()
    adapter_registry.get.return_value.execute.assert_not_called()
