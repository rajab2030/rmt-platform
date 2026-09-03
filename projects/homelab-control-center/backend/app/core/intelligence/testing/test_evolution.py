"""
C06 validation: Controlled Platform Evolution.

Proves that a bounded module-registration change travels through the complete
governed lifecycle (Change Proposal -> Scope/Compatibility Assessment ->
Policy -> Risk -> Approval -> Authorization -> Controlled Execution ->
Post-change Verification -> Audit/Trace) using the existing Core machinery,
that out-of-scope / unsupported / unapproved changes are blocked before the
mutation boundary, and that read-only assessment is distinct from mutation.
"""
from unittest.mock import Mock

import pytest

import app.core.intelligence.execution.engine as execution_engine_module
import app.core.intelligence.actions.service as actions_service_module
import app.core.intelligence.actions.approval_service as approval_service_module
import app.core.intelligence.verification.service as verification_service_module
import app.core.evolution.service as evolution_service_module
import app.core.evolution.adapters.module_change as module_change_adapter_module

from app.core.intelligence.actions.models import ActionRequest
from app.core.intelligence.actions.authorization_storage import (
    AuthorizationStorage,
)
from app.core.intelligence.actions.approval_storage import (
    ApprovalHoldStorage,
    ApprovalRecordStorage,
)
from app.core.intelligence.execution.storage import ExecutionAuditStorage
from app.core.intelligence.execution.trace_storage import ExecutionTraceStorage
from app.core.intelligence.execution.adapters.registry import AdapterRegistry
from app.core.intelligence.verification.storage import VerificationStorage
from app.core.intelligence.verification.models import (
    ExpectedOutcome,
    ObservedState,
)
from app.core.module_registry.schema import Module, RuntimeInfo, HealthInfo
from app.core.evolution.models import (
    ChangeProposal,
    CompatibilityAssessment,
    ChangeResult,
)
from app.core.evolution.adapters.module_change import ModuleChangeAdapter


def _module(name="control-center", version="0.1.0"):
    return Module(
        module_id=f"{name}-id",
        name=name,
        description="",
        version=version,
        type="platform-service",
        status="active",
        runtime=RuntimeInfo(
            engine="docker",
            service=None,
            container=name,
            ports=[],
        ),
        dependencies=[],
        configuration={},
        health=HealthInfo(status="unknown"),
    )


def _proposal(
    target="new-service",
    operation="register_module",
    confidence=100,
    requires_approval=False,
):
    return ChangeProposal(
        scope=f"register {target}",
        target=target,
        operation=operation,
        version="0.1.0",
        reason="Add capability",
        confidence=confidence,
        requires_approval=requires_approval,
        expected_outcome=ExpectedOutcome(
            target=target,
            operation="register_module",
            expected_state="registered",
        ),
    )


def _setup_isolation(monkeypatch, module_store):
    """
    Wire the governed pipeline and the execution engine to the same isolated
    in-memory storage, a fresh adapter registry holding the real
    ModuleChangeAdapter, and an in-memory module registry.
    """
    isolated_authorization_storage = AuthorizationStorage()
    isolated_trace_storage = ExecutionTraceStorage()
    isolated_audit_storage = ExecutionAuditStorage()
    isolated_hold_storage = ApprovalHoldStorage()
    isolated_approval_record_storage = ApprovalRecordStorage()
    isolated_verification_storage = VerificationStorage()

    adapter = ModuleChangeAdapter()
    adapter_calls = []
    original_execute = adapter.execute

    def spy_execute(request):
        adapter_calls.append(request)
        return original_execute(request)

    adapter.execute = spy_execute

    adapter_registry = AdapterRegistry()
    adapter_registry.register("module_change", adapter)

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

    # In-memory module registry.
    monkeypatch.setattr(
        evolution_service_module,
        "get_modules",
        lambda: list(module_store),
    )
    # The trusted verification observer reads the same in-memory registry.
    monkeypatch.setattr(
        verification_service_module,
        "get_modules",
        lambda: list(module_store),
    )
    monkeypatch.setattr(
        module_change_adapter_module,
        "register_module",
        _make_register(module_store),
    )
    monkeypatch.setattr(
        module_change_adapter_module,
        "create_module",
        lambda name, version, module_type, runtime_engine="docker",
        container=None: _module(name, version),
    )

    return (
        isolated_authorization_storage,
        isolated_trace_storage,
        isolated_audit_storage,
        isolated_approval_record_storage,
        isolated_hold_storage,
        isolated_verification_storage,
        adapter_registry,
        adapter_calls,
    )


def _make_register(module_store):
    def register(module):
        for existing in module_store:
            if existing.module_id == module.module_id:
                raise ValueError(
                    f"Module {module.module_id} already exists."
                )
        module_store.append(module)
        return module
    return register


def test_positive_module_registration_full_lifecycle(monkeypatch):
    """
    P01. A representative approved module-registration change completes the
    full governed lifecycle and registers the module.
    """
    module_store = []
    (
        auth_storage,
        trace_storage,
        audit_storage,
        approval_record_storage,
        hold_storage,
        verification_storage,
        adapter_registry,
        adapter_calls,
    ) = _setup_isolation(monkeypatch, module_store)

    # Spy on the authoritative governed mutation boundary.
    boundary_calls = []
    original_boundary = evolution_service_module.execute_governed_action

    def spy_boundary(action, adapter_name="simulation"):
        boundary_calls.append(action)
        return original_boundary(
            action,
            adapter_name=adapter_name,
        )

    monkeypatch.setattr(
        evolution_service_module,
        "execute_governed_action",
        spy_boundary,
    )

    proposal = _proposal()

    result = evolution_service_module.evolution_service.execute_governed_change(
        proposal,
        adapter_name="module_change",
    )

    assert result.status == "executed"
    assert result.change_id == proposal.change_id
    assert result.execution_id is not None

    # Module registered through the adapter.
    assert len(module_store) == 1
    assert module_store[0].name == "new-service"

    # Authoritative boundary invoked exactly once with a governed ActionRequest.
    assert len(boundary_calls) == 1
    assert isinstance(boundary_calls[0], ActionRequest)
    assert boundary_calls[0].component == "new-service"

    # Adapter invoked exactly once.
    assert len(adapter_calls) == 1

    # Authorization created, bound to target/operation, change_id correlated.
    assert len(auth_storage.get_all()) == 1
    auth = auth_storage.get_all()[0]
    assert auth.decision_id == proposal.change_id
    assert auth.target == "new-service"
    assert auth.operation == "create"

    # Durable audit + trace evidence recorded.
    assert len(audit_storage.get_all()) == 1
    assert len(trace_storage.get_all()) == 1

    # Post-change verification correlated to execution; expected outcome from
    # the proposal (C03), not manufactured.
    assert len(verification_storage.get_all()) == 1
    verification = verification_storage.get_all()[0]
    assert verification.execution_id == result.execution_id
    assert verification.expected == proposal.expected_outcome
    assert verification.status == "verified_success"


def test_change_identity_correlation(monkeypatch):
    """
    C01. The same change_id remains traceable across proposal/result and the
    governed lifecycle evidence (authorization.decision_id).
    """
    module_store = []
    (
        auth_storage,
        trace_storage,
        audit_storage,
        approval_record_storage,
        hold_storage,
        verification_storage,
        adapter_registry,
        adapter_calls,
    ) = _setup_isolation(monkeypatch, module_store)

    proposal = _proposal()

    result = evolution_service_module.evolution_service.execute_governed_change(
        proposal,
        adapter_name="module_change",
    )

    assert result.status == "executed"
    assert result.change_id == proposal.change_id
    assert result.action_id is not None
    assert result.execution_id is not None

    # The change identity is carried into the authorization evidence.
    auth = auth_storage.get_all()[0]
    assert auth.decision_id == proposal.change_id

    # The audit/trace evidence is correlated to the same execution.
    audit = audit_storage.get_all()[0]
    trace = trace_storage.get_all()[0]
    assert audit.execution_id == result.execution_id
    assert trace.execution_id == result.execution_id


def test_negative_out_of_scope_change_blocked(monkeypatch):
    """
    N01. An out-of-scope change (target already registered) is blocked before
    execution. No authorization, no adapter, durable deny evidence.
    """
    module_store = [_module("control-center")]
    (
        auth_storage,
        trace_storage,
        audit_storage,
        approval_record_storage,
        hold_storage,
        verification_storage,
        adapter_registry,
        adapter_calls,
    ) = _setup_isolation(monkeypatch, module_store)

    proposal = _proposal(target="control-center")

    result = evolution_service_module.evolution_service.execute_governed_change(
        proposal,
        adapter_name="module_change",
    )

    assert result.status == "blocked"
    assert "already registered" in result.message

    # Mutation boundary never reached.
    assert len(auth_storage.get_all()) == 0
    assert len(adapter_calls) == 0
    assert len(audit_storage.get_all()) == 0
    assert len(trace_storage.get_all()) == 0

    # Durable deny evidence through the existing approval-record store.
    assert len(approval_record_storage.get_all()) == 1
    blocked = approval_record_storage.get_all()[0]
    assert blocked.decision == "rejected"
    assert blocked.approved_by == "evolution_boundary"


def test_negative_unsupported_operation_blocked(monkeypatch):
    """
    N02. An unsupported evolution operation is blocked before execution.
    """
    module_store = []
    (
        auth_storage,
        trace_storage,
        audit_storage,
        approval_record_storage,
        hold_storage,
        verification_storage,
        adapter_registry,
        adapter_calls,
    ) = _setup_isolation(monkeypatch, module_store)

    proposal = _proposal(operation="remove")

    result = evolution_service_module.evolution_service.execute_governed_change(
        proposal,
        adapter_name="module_change",
    )

    assert result.status == "blocked"
    assert "Unsupported" in result.message

    assert len(auth_storage.get_all()) == 0
    assert len(adapter_calls) == 0
    assert len(audit_storage.get_all()) == 0
    assert len(trace_storage.get_all()) == 0

    # Durable deny evidence.
    assert len(approval_record_storage.get_all()) == 1
    blocked = approval_record_storage.get_all()[0]
    assert blocked.decision == "rejected"
    assert blocked.approved_by == "evolution_boundary"


def test_negative_unapproved_change_does_not_reach_adapter(monkeypatch):
    """
    N03. A change requiring manual approval is held and never reaches
    authorization or the adapter.
    """
    module_store = []
    (
        auth_storage,
        trace_storage,
        audit_storage,
        approval_record_storage,
        hold_storage,
        verification_storage,
        adapter_registry,
        adapter_calls,
    ) = _setup_isolation(monkeypatch, module_store)

    proposal = _proposal(requires_approval=True)

    result = evolution_service_module.evolution_service.execute_governed_change(
        proposal,
        adapter_name="module_change",
    )

    assert result.status == "manual_approval_required"

    # No authorization, no adapter, no execution evidence.
    assert len(auth_storage.get_all()) == 0
    assert len(adapter_calls) == 0
    assert len(audit_storage.get_all()) == 0
    assert len(trace_storage.get_all()) == 0

    # Durable evidence: approval record (manual_required) + hold.
    assert len(approval_record_storage.get_all()) == 1
    assert len(hold_storage.get_all()) == 1


def test_read_only_assessment_does_not_mutate(monkeypatch):
    """
    R01. assess_change() is read-only: it creates no authorization, records no
    approval, executes nothing, invokes no adapter, and mutates no module
    state.
    """
    module_store = []
    (
        auth_storage,
        trace_storage,
        audit_storage,
        approval_record_storage,
        hold_storage,
        verification_storage,
        adapter_registry,
        adapter_calls,
    ) = _setup_isolation(monkeypatch, module_store)

    proposal = _proposal()

    assessment = evolution_service_module.evolution_service.assess_change(
        proposal,
    )

    assert isinstance(assessment, CompatibilityAssessment)
    assert assessment.compatible is True
    assert assessment.change_id == proposal.change_id

    # No mutation, no authorization, no approval, no audit/trace, no adapter.
    assert len(module_store) == 0
    assert len(auth_storage.get_all()) == 0
    assert len(approval_record_storage.get_all()) == 0
    assert len(audit_storage.get_all()) == 0
    assert len(trace_storage.get_all()) == 0
    assert len(adapter_calls) == 0


def test_production_adapter_registration(monkeypatch):
    """
    B1. The ModuleChangeAdapter is registered through the normal production
    bootstrap/registry path (no test-only adapter registration), and the
    representative evolution operation executes through it.
    """
    from app.core.intelligence.execution.adapters.bootstrap import (
        register_default_adapters,
    )
    from app.core.intelligence.execution.adapters.registry import (
        adapter_registry as real_registry,
    )

    # Populate the real production registry.
    register_default_adapters()
    assert real_registry.get("module_change") is not None
    assert isinstance(
        real_registry.get("module_change"),
        ModuleChangeAdapter,
    )

    # Isolate governed-path storages + module registry, but use the real
    # production adapter registry.
    module_store = []
    isolated_authorization_storage = AuthorizationStorage()
    isolated_trace_storage = ExecutionTraceStorage()
    isolated_audit_storage = ExecutionAuditStorage()
    isolated_hold_storage = ApprovalHoldStorage()
    isolated_approval_record_storage = ApprovalRecordStorage()
    isolated_verification_storage = VerificationStorage()

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
        real_registry,
    )

    monkeypatch.setattr(
        evolution_service_module,
        "get_modules",
        lambda: list(module_store),
    )
    monkeypatch.setattr(
        module_change_adapter_module,
        "register_module",
        _make_register(module_store),
    )
    monkeypatch.setattr(
        module_change_adapter_module,
        "create_module",
        lambda name, version, module_type, runtime_engine="docker",
        container=None: _module(name, version),
    )

    proposal = _proposal()
    result = evolution_service_module.evolution_service.execute_governed_change(
        proposal,
        adapter_name="module_change",
    )

    assert result.status == "executed"
    assert len(module_store) == 1
    assert module_store[0].name == "new-service"


def test_adapter_redirection_blocked(monkeypatch):
    """
    B2. A caller cannot redirect a module-registration evolution to Docker or
    any other adapter. The attempt is rejected before governance/execution.
    """
    module_store = []
    (
        auth_storage,
        trace_storage,
        audit_storage,
        approval_record_storage,
        hold_storage,
        verification_storage,
        adapter_registry,
        adapter_calls,
    ) = _setup_isolation(monkeypatch, module_store)

    proposal = _proposal()

    result = evolution_service_module.evolution_service.execute_governed_change(
        proposal,
        adapter_name="docker",
    )

    assert result.status == "blocked"
    assert "adapter" in result.message.lower()

    # No authorization, no adapter execution, no mutation, no execution evidence.
    assert len(auth_storage.get_all()) == 0
    assert len(adapter_calls) == 0
    assert len(module_store) == 0
    assert len(audit_storage.get_all()) == 0
    assert len(trace_storage.get_all()) == 0

    # Durable deny evidence.
    assert len(approval_record_storage.get_all()) == 1
    blocked = approval_record_storage.get_all()[0]
    assert blocked.decision == "rejected"
    assert blocked.approved_by == "evolution_boundary"


def test_default_verification_against_module_registry(monkeypatch):
    """
    B3. With observer omitted, the evolution service uses a default
    module-registry observer, and verification reaches verified_success based
    on actual observed registry state (not adapter success).
    """
    module_store = []
    (
        auth_storage,
        trace_storage,
        audit_storage,
        approval_record_storage,
        hold_storage,
        verification_storage,
        adapter_registry,
        adapter_calls,
    ) = _setup_isolation(monkeypatch, module_store)

    proposal = _proposal()

    # No observer provided: the default module-registry observer is used.
    result = evolution_service_module.evolution_service.execute_governed_change(
        proposal,
        adapter_name="module_change",
    )

    assert result.status == "executed"
    assert result.verification_status == "verified_success"

    assert len(verification_storage.get_all()) == 1
    verification = verification_storage.get_all()[0]
    assert verification.execution_id == result.execution_id
    assert verification.expected == proposal.expected_outcome
    assert verification.status == "verified_success"
    # Based on actual module-registry observation, not adapter success.
    assert verification.observed is not None
    assert verification.observed.state == "registered"
    assert verification.observed.source == "module_registry"


def test_b4_governed_api_rejects_caller_observer(monkeypatch):
    """
    B4. The governed public API no longer accepts a caller-supplied observer.
    A fabricated observer cannot be injected into the verification path.
    """
    module_store = []
    (
        auth_storage,
        trace_storage,
        audit_storage,
        approval_record_storage,
        hold_storage,
        verification_storage,
        adapter_registry,
        adapter_calls,
    ) = _setup_isolation(monkeypatch, module_store)

    proposal = _proposal()

    with pytest.raises(TypeError):
        evolution_service_module.evolution_service.execute_governed_change(
            proposal,
            adapter_name="module_change",
            observer=lambda: ObservedState(
                target="new-service",
                state="registered",
            ),
        )


def test_b4_adapter_success_alone_cannot_manufacture_verified_success(
    monkeypatch,
):
    """
    B4. Even when the adapter reports success, verification reflects actual
    module-registry state. If the module is not actually registered,
    verification is NOT verified_success.
    """
    module_store = []
    (
        auth_storage,
        trace_storage,
        audit_storage,
        approval_record_storage,
        hold_storage,
        verification_storage,
        adapter_registry,
        adapter_calls,
    ) = _setup_isolation(monkeypatch, module_store)

    # Adapter "succeeds" but never actually registers the module.
    monkeypatch.setattr(
        module_change_adapter_module,
        "register_module",
        lambda module: None,
    )

    proposal = _proposal()

    result = evolution_service_module.evolution_service.execute_governed_change(
        proposal,
        adapter_name="module_change",
    )

    assert result.status == "executed"
    assert result.verification_status != "verified_success"
    assert result.verification_status in (
        "state_mismatch",
        "observation_unavailable",
    )

    # The module is not actually in the registry.
    assert len(module_store) == 0
