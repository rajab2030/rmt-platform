import math

import pytest
from unittest.mock import Mock

import app.core.intelligence.actions.service as actions_service_module
import app.core.intelligence.execution.engine as engine_module
import app.core.intelligence.verification.service as verification_service_module

from app.core.intelligence.actions.assessment import (
    AssessmentError,
    AssessmentRegistry,
    resolve_assessment,
)
from app.core.intelligence.actions.binding import InvalidInstruction, bind_action
from app.core.intelligence.actions.models import ActionRequest, ActionType
from app.core.intelligence.actions.policy import ActionPolicyResult
from app.core.intelligence.actions.simulation import ActionSimulationResult
from app.core.intelligence.actions.authorization_storage import AuthorizationStorage
from app.core.intelligence.actions.approval_storage import ApprovalRecordStorage
from app.core.intelligence.execution.models import ExecutionResult
from app.core.intelligence.execution.storage import ExecutionAuditStorage
from app.core.intelligence.execution.trace_storage import ExecutionTraceStorage
from app.core.intelligence.verification.storage import VerificationStorage


class _Policy:
    evaluator_id = "test.policy"
    version = "1"

    def evaluate(self, action):
        return ActionPolicyResult(
            True,
            "test domain allows",
            True,
            evidence_references=("policy:test-record",),
        )


class _Risk:
    evaluator_id = "test.risk"
    version = "1"

    def evaluate(self, action):
        return ActionSimulationResult(
            action_id=action.action_id,
            component=action.component,
            action_type=action.action_type.value,
            expected_impact="Create one test-domain record",
            risk_level="medium",
            rollback_available=False,
            uncertainty="low",
            recovery_semantics="cancel with a separately governed operation",
            evidence_references=("risk:test-record",),
        )


def _action(**changes):
    values = {
        "action_id": "action-1",
        "decision_id": "decision-1",
        "governance_domain": "test.domain",
        "component": "record-1",
        "action_type": ActionType.CREATE,
        "reason": "test",
        "confidence": 100,
        "parameters": {"amount": "1500.00", "tags": ["a", "b"]},
    }
    values.update(changes)
    return ActionRequest(**values)


def _registry():
    registry = AssessmentRegistry()
    registry.register(
        domain="test.domain",
        policy=_Policy(),
        risk=_Risk(),
        operations={"create"},
        adapters={"test-adapter"},
    )
    return registry


def test_registered_domain_resolves_actual_domain_assessment():
    result = resolve_assessment(_action(), "test-adapter", registry=_registry())

    assert result.policy_result.allowed is True
    assert result.policy_result.requires_approval is True
    assert result.risk_result.expected_impact == "Create one test-domain record"
    assert result.risk_result.rollback_available is False
    assert result.policy_evaluator_id == "test.policy"
    assert result.risk_evaluator_id == "test.risk"
    assert len(result.instruction_digest) == 64


def test_unknown_domain_and_adapter_mismatch_fail_closed():
    with pytest.raises(AssessmentError, match="Unknown governance domain"):
        resolve_assessment(
            _action(governance_domain="unknown"),
            "test-adapter",
            registry=_registry(),
        )
    with pytest.raises(AssessmentError, match="not registered for the domain"):
        resolve_assessment(_action(), "wrong-adapter", registry=_registry())


def test_duplicate_registration_is_rejected():
    registry = _registry()
    with pytest.raises(AssessmentError, match="already registered"):
        registry.register(
            domain="test.domain",
            policy=_Policy(),
            risk=_Risk(),
            operations={"create"},
            adapters={"test-adapter"},
        )


def test_instruction_digest_is_deterministic_and_binds_every_effect_field():
    action = _action()
    digest, _ = bind_action(action, "test-adapter")
    same, _ = bind_action(
        _action(parameters={"tags": ["a", "b"], "amount": "1500.00"}),
        "test-adapter",
    )
    assert same == digest

    variants = [
        (_action(parameters={"amount": "1501.00", "tags": ["a", "b"]}), "test-adapter"),
        (_action(component="record-2"), "test-adapter"),
        (_action(decision_id="decision-2"), "test-adapter"),
        (_action(governance_domain="other.domain"), "test-adapter"),
        (action, "other-adapter"),
    ]
    assert all(bind_action(candidate, adapter)[0] != digest for candidate, adapter in variants)


def test_non_json_and_non_finite_parameters_fail_before_governance():
    with pytest.raises(InvalidInstruction):
        bind_action(_action(parameters={"bad": object()}), "test-adapter")
    with pytest.raises(InvalidInstruction):
        bind_action(_action(parameters={"bad": math.nan}), "test-adapter")


class _AutoPolicy(_Policy):
    def evaluate(self, action):
        return ActionPolicyResult(
            True,
            "test domain allows",
            False,
            evidence_references=("policy:test-record",),
        )


class _ReversibleRisk(_Risk):
    def evaluate(self, action):
        result = super().evaluate(action)
        result.rollback_available = True
        result.risk_level = "low"
        return result


def test_non_default_domain_reaches_adapter_only_through_full_governed_chain(monkeypatch):
    registry = AssessmentRegistry()
    registry.register(
        domain="test.domain",
        policy=_AutoPolicy(),
        risk=_ReversibleRisk(),
        operations={"create"},
        adapters={"test-adapter"},
    )
    monkeypatch.setattr(
        actions_service_module,
        "resolve_assessment",
        lambda action, adapter: resolve_assessment(
            action,
            adapter,
            registry=registry,
        ),
    )

    auth = AuthorizationStorage()
    trace = ExecutionTraceStorage()
    audit = ExecutionAuditStorage()
    approvals = ApprovalRecordStorage()
    verifications = VerificationStorage()
    adapter = Mock()
    adapter.supports.return_value = True
    adapter.execute.side_effect = lambda request: ExecutionResult(
        execution_id=request.execution_id,
        status="completed",
        success=True,
        message="test-domain record created",
    )
    adapters = Mock()
    adapters.get.return_value = adapter
    monkeypatch.setattr(actions_service_module, "execution_authorization_storage", auth)
    monkeypatch.setattr(engine_module, "execution_authorization_storage", auth)
    monkeypatch.setattr(engine_module, "execution_trace_storage", trace)
    monkeypatch.setattr(engine_module, "execution_audit_storage", audit)
    monkeypatch.setattr(engine_module, "adapter_registry", adapters)
    monkeypatch.setattr(verification_service_module, "verification_storage", verifications)
    monkeypatch.setattr(
        "app.core.intelligence.actions.approval_service.approval_record_storage",
        approvals,
    )

    result = actions_service_module.execute_governed_action(
        _action(requires_approval=False),
        adapter_name="test-adapter",
    )

    assert result["status"] == "executed"
    assert result["success"] is True
    adapter.execute.assert_called_once()
    assert len(auth.get_all()) == 1
    assert auth.get_all()[0].governance_domain == "test.domain"
    assert len(trace.get_all()) == 1
    assert trace.get_all()[0].policy_evaluator_id == "test.policy"
    assert len(audit.get_all()) == 1
    assert audit.get_all()[0].instruction_digest
