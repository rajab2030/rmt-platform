"""G2 - Above-Core Homelab decision -> remediation wiring tests.

Validates the decision-to-action connection WITHOUT any real Docker mutation:

  * Healthy path: healthy evaluation -> continue_monitoring -> no ActionRequest
  * Remediation path: controlled unhealthy fixture -> remediation decision
    -> restart ActionRequest -> governed action path (policy/risk/approval/
    authorization/execution/verification via the governed boundary).

The governed pipeline and execution engine are wired to isolated in-memory
storage and a mock adapter, so no real Docker mutation and no durable JSON
evidence files are touched.
"""
from datetime import datetime, timezone
from unittest.mock import Mock

import app.core.intelligence.execution.engine as execution_engine_module
import app.core.intelligence.actions.service as actions_service_module
import app.core.intelligence.actions.approval_service as approval_service_module
import app.core.intelligence.verification.service as verification_service_module

from app.core.intelligence.observation.models import ComponentObservation
from app.core.intelligence.rules import create_health_evaluation
from app.core.intelligence.decision.engine import make_decision
from app.core.intelligence.schemas import HealthStatus
from app.core.intelligence.actions.models import ActionType
from app.core.intelligence.actions.authorization_storage import AuthorizationStorage
from app.core.intelligence.actions.approval_storage import (
    ApprovalHoldStorage,
    ApprovalRecordStorage,
)
from app.core.intelligence.execution.models import ExecutionResult
from app.core.intelligence.execution.storage import ExecutionAuditStorage
from app.core.intelligence.execution.trace_storage import ExecutionTraceStorage
from app.core.intelligence.verification.storage import VerificationStorage

from app.homelab.remediation import (
    build_remediation_action,
    remediate,
)


def _observation(component, state, signals=None, health="healthy"):
    return ComponentObservation(
        component=component,
        source="docker",
        state=state,
        timestamp=datetime.now(timezone.utc),
        signals=signals or {},
        metadata={"health": health},
    )


def _healthy_uptime_kuma():
    return create_health_evaluation(
        _observation(
            "uptime-kuma",
            "running",
            {"cpu_usage": 20.0, "memory_usage": 30.0},
            "healthy",
        )
    )


def _critical_uptime_kuma():
    return create_health_evaluation(
        _observation("uptime-kuma", "stopped", {}, "unhealthy")
    )


def _healthy_portainer():
    return create_health_evaluation(
        _observation(
            "portainer",
            "running",
            {"cpu_usage": 15.0, "memory_usage": 25.0},
            "healthy",
        )
    )


def _critical_portainer():
    return create_health_evaluation(
        _observation("portainer", "stopped", {}, "unhealthy")
    )


def _setup_isolation(monkeypatch):
    """Wire the governed pipeline + engine to isolated in-memory storage and a
    mock adapter (mirrors test_governed_execution, plus the manual-approval
    authorization storage reference)."""
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
    # Manual-approval continuation saves the authorization here; patch it so the
    # engine re-reads the SAME in-memory store.
    monkeypatch.setattr(
        approval_service_module, "execution_authorization_storage", auth_storage
    )
    monkeypatch.setattr(
        verification_service_module, "verification_storage", verification_storage
    )
    monkeypatch.setattr(execution_engine_module, "adapter_registry", adapter_registry)

    return {
        "auth": auth_storage,
        "trace": trace_storage,
        "audit": audit_storage,
        "hold": hold_storage,
        "approval_record": approval_record_storage,
        "verification": verification_storage,
        "adapter_registry": adapter_registry,
    }


# ---------------------------------------------------------------------------
# Healthy path: no remediation
# ---------------------------------------------------------------------------

def test_healthy_uptime_kuma_produces_no_remediation_action():
    evaluation = _healthy_uptime_kuma()
    assert evaluation.status == HealthStatus.HEALTHY

    decision = make_decision(evaluation)
    assert decision.action == "continue_monitoring"

    action = build_remediation_action(evaluation, decision)
    assert action is None

    result = remediate(evaluation, decision)
    assert result["status"] == "no_remediation"


def test_non_remediable_target_produces_no_action():
    # dozzle is not in the Homelab remediation policy, even when critical.
    evaluation = create_health_evaluation(
        _observation("dozzle", "stopped", {}, "unhealthy")
    )
    assert evaluation.status == HealthStatus.CRITICAL
    assert build_remediation_action(evaluation) is None


# ---------------------------------------------------------------------------
# T1-1: second policy component (portainer) -- same shape as uptime-kuma,
# proving the loop/policy generalize past a single hardcoded component.
# ---------------------------------------------------------------------------

def test_healthy_portainer_produces_no_remediation_action():
    evaluation = _healthy_portainer()
    assert evaluation.status == HealthStatus.HEALTHY

    decision = make_decision(evaluation)
    assert decision.action == "continue_monitoring"

    action = build_remediation_action(evaluation, decision)
    assert action is None

    result = remediate(evaluation, decision)
    assert result["status"] == "no_remediation"


def test_critical_portainer_builds_restart_action_with_evaluation_confidence():
    evaluation = _critical_portainer()
    assert evaluation.status == HealthStatus.CRITICAL

    decision = make_decision(evaluation)
    assert decision.action == "investigate_immediately"

    action = build_remediation_action(evaluation, decision)
    assert action is not None
    assert action.component == "portainer"
    assert action.action_type == ActionType.RESTART
    assert action.confidence == evaluation.confidence
    assert action.requires_approval is True
    assert action.expected_outcome is not None
    assert action.expected_outcome.target == "portainer"
    assert action.expected_outcome.expected_state == "running"


def test_portainer_remediation_reaches_governed_boundary_and_continues(monkeypatch):
    """Same governed-chain proof as uptime-kuma, for the second policy
    component: policy/risk/approval/authorization/execution/verification all
    run through the governed boundary, not a bypass."""
    stores = _setup_isolation(monkeypatch)
    evaluation = _critical_portainer()
    decision = make_decision(evaluation)

    result = remediate(evaluation, decision, adapter_name="simulation")
    assert result["status"] == "manual_approval_required"
    approval_id = result["approval_id"]
    assert approval_id

    assert len(stores["trace"].get_all()) == 0
    assert len(stores["audit"].get_all()) == 0
    assert len(stores["auth"].get_all()) == 0
    assert len(stores["hold"].get_all()) == 1

    from app.core.intelligence.actions.approval_service import approve_held_action
    cont = approve_held_action(approval_id, approved_by="operator")
    assert cont["status"] == "executed"
    assert cont.get("execution_id")

    assert len(stores["auth"].get_all()) >= 1
    assert len(stores["trace"].get_all()) >= 1
    assert len(stores["audit"].get_all()) >= 1
    assert len(stores["verification"].get_all()) >= 1
    stores["adapter_registry"].get.assert_called()
    stores["adapter_registry"].get.return_value.execute.assert_called_once()


# ---------------------------------------------------------------------------
# Remediation path: governed action
# ---------------------------------------------------------------------------

def test_critical_uptime_kuma_builds_restart_action_with_evaluation_confidence():
    evaluation = _critical_uptime_kuma()
    assert evaluation.status == HealthStatus.CRITICAL

    decision = make_decision(evaluation)
    assert decision.action == "investigate_immediately"

    action = build_remediation_action(evaluation, decision)
    assert action is not None
    assert action.component == "uptime-kuma"
    assert action.action_type == ActionType.RESTART
    # Confidence provenance: originates from the actual evaluation, not fabricated.
    assert action.confidence == evaluation.confidence
    assert action.requires_approval is True
    # Explicit expected outcome carried into the governed chain.
    assert action.expected_outcome is not None
    assert action.expected_outcome.target == "uptime-kuma"
    assert action.expected_outcome.expected_state == "running"


def test_remediation_reaches_governed_boundary_and_continues(monkeypatch):
    """The remediation ActionRequest enters execute_governed_action and the
    full governed chain (policy/risk/approval/authorization/execution/
    verification) runs through the governed boundary, not a bypass."""
    stores = _setup_isolation(monkeypatch)
    evaluation = _critical_uptime_kuma()
    decision = make_decision(evaluation)

    result = remediate(evaluation, decision, adapter_name="simulation")
    # requires_approval=True -> manual hold (governed, not a bypass).
    assert result["status"] == "manual_approval_required"
    approval_id = result["approval_id"]
    assert approval_id

    # Held before the adapter: no execution evidence yet.
    assert len(stores["trace"].get_all()) == 0
    assert len(stores["audit"].get_all()) == 0
    assert len(stores["auth"].get_all()) == 0
    assert len(stores["hold"].get_all()) == 1

    # Legitimate approval continuation -> authorization + execution + verification.
    from app.core.intelligence.actions.approval_service import approve_held_action
    cont = approve_held_action(approval_id, approved_by="operator")
    assert cont["status"] == "executed"
    assert cont.get("execution_id")

    assert len(stores["auth"].get_all()) >= 1
    assert len(stores["trace"].get_all()) >= 1
    assert len(stores["audit"].get_all()) >= 1
    assert len(stores["verification"].get_all()) >= 1
    # Adapter invoked through the governed engine exactly once.
    stores["adapter_registry"].get.assert_called()
    stores["adapter_registry"].get.return_value.execute.assert_called_once()


def test_low_confidence_remediation_is_policy_denied(monkeypatch):
    """A critical evaluation with confidence below the action threshold is
    denied by policy before any adapter invocation (governance enforced)."""
    stores = _setup_isolation(monkeypatch)
    # state "exited" -> unresolved state -> low confidence critical.
    evaluation = create_health_evaluation(
        _observation("uptime-kuma", "exited", {}, "unhealthy")
    )
    assert evaluation.status == HealthStatus.CRITICAL
    assert evaluation.confidence < 70

    result = remediate(evaluation, adapter_name="simulation")
    assert result["status"] == "policy_denied"

    # No execution evidence; adapter never invoked.
    assert len(stores["trace"].get_all()) == 0
    assert len(stores["audit"].get_all()) == 0
    assert len(stores["auth"].get_all()) == 0
    stores["adapter_registry"].get.assert_not_called()
