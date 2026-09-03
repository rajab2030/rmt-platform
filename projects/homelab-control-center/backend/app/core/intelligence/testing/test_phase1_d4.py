"""C04 Phase 3 (D4) - decision/recommendation semantics + non-executing boundary."""
import pytest

from app.core.intelligence.decision.models import IntelligenceDecision
from app.core.intelligence.decision.engine import make_decision
from app.core.intelligence.actions.translator import decision_to_action, ACTION_MAPPING
from app.core.intelligence.actions.models import ActionRequest, ActionStatus
from app.core.intelligence.verification.models import ExpectedOutcome
from app.core.intelligence.schemas import (
    HealthEvaluation,
    HealthStatus,
    HealthReason,
    HealthImpact,
)


def _ev(status, message="state", confidence=80, evidence=("e1", "e2")):
    return HealthEvaluation(
        component="svc",
        status=status,
        reason=(
            HealthReason.UNKNOWN_STATE
            if status == HealthStatus.UNKNOWN
            else HealthReason.HEALTHY
        ),
        evidence=list(evidence),
        confidence=confidence,
        impact=HealthImpact.LOW,
        message=message,
    )


# --- explicit state handling ------------------------------------------------

def test_healthy_is_advisory_continue_monitoring_not_actionable():
    d = make_decision(_ev(HealthStatus.HEALTHY))
    assert d.action == "continue_monitoring"
    assert d.priority == "low"
    assert decision_to_action(d) is None  # advisory, unmapped


def test_warning_is_advisory_monitor():
    d = make_decision(_ev(HealthStatus.WARNING))
    assert d.action == "monitor"
    assert decision_to_action(d) is None


def test_critical_is_existing_investigation_proposal():
    d = make_decision(_ev(HealthStatus.CRITICAL))
    assert d.action == "investigate_immediately"
    assert decision_to_action(d) is None


def test_unknown_does_not_become_continue_monitoring():
    d = make_decision(_ev(HealthStatus.UNKNOWN, message="ambiguous"))
    assert d.action != "continue_monitoring"
    assert d.action == "uncertain"
    assert d.priority == "medium"


def test_unknown_not_safe_or_executable():
    d = make_decision(_ev(HealthStatus.UNKNOWN))
    assert d.action == "uncertain"
    # unmapped -> no executable ActionRequest
    assert decision_to_action(d) is None


# --- advisory decisions remain unmapped/non-executable ----------------------

def test_advisory_decisions_not_in_action_mapping():
    for status, action in [
        (HealthStatus.HEALTHY, "continue_monitoring"),
        (HealthStatus.WARNING, "monitor"),
        (HealthStatus.CRITICAL, "investigate_immediately"),
        (HealthStatus.UNKNOWN, "uncertain"),
    ]:
        d = make_decision(_ev(status))
        assert d.action == action
        assert action not in ACTION_MAPPING
        assert decision_to_action(d) is None


# --- decision_to_action is pure: no execution / no authorization ------------

def test_decision_to_action_performs_no_execution(monkeypatch):
    from app.core.intelligence.execution.engine import execution_engine

    def fail(*a, **k):
        raise AssertionError("adapter/execution called")
    monkeypatch.setattr(execution_engine, "execute", fail)

    d = IntelligenceDecision(
        component="svc", priority="high", action="restart_component",
        reason="r", confidence=80, intended_outcome=None,
    )
    result = decision_to_action(d)  # must not raise
    assert isinstance(result, ActionRequest)
    assert not isinstance(result, dict)  # not a governed-execution result dict


def test_decision_to_action_does_not_mint_authorization():
    d = IntelligenceDecision(
        component="svc", priority="high", action="restart_component",
        reason="r", confidence=80, intended_outcome=None,
    )
    ar = decision_to_action(d)
    assert ar is not None
    assert isinstance(ar, ActionRequest)
    # action remains PENDING proposal; no authorization issued.
    assert ar.status == ActionStatus.PENDING
    assert not hasattr(ar, "authorization_id")
    assert not hasattr(ar, "authorization")


def test_decision_creation_cannot_authorize():
    d = make_decision(_ev(HealthStatus.CRITICAL))
    assert isinstance(d, IntelligenceDecision)
    assert not isinstance(d, ActionRequest)
    assert not hasattr(d, "authorization_id")
    assert not hasattr(d, "authorized_by")


def test_decision_creation_cannot_call_adapter(monkeypatch):
    from app.core.intelligence.execution.engine import execution_engine

    def fail(*a, **k):
        raise AssertionError("must never be invoked from decision layer")
    monkeypatch.setattr(execution_engine, "execute", fail)
    monkeypatch.setattr(
        "app.core.intelligence.actions.service.execute_governed_action", fail,
    )

    # make_decision must not reach any execution/adaptor surface.
    for status in (HealthStatus.HEALTHY, HealthStatus.WARNING,
                   HealthStatus.CRITICAL, HealthStatus.UNKNOWN):
        d = make_decision(_ev(status))
        assert isinstance(d, IntelligenceDecision)


# --- evidence preservation & intended outcome propagation -------------------

def test_decision_preserves_evidence_basis():
    ev = _ev(HealthStatus.CRITICAL, evidence=["high cpu", "not running"])
    d = make_decision(ev)
    assert d.evidence == ["high cpu", "not running"]
    assert d.confidence == ev.confidence
    assert d.reason == ev.message


def test_intended_outcome_propagates_to_expected_outcome():
    expected = ExpectedOutcome(target="svc", operation="restart", expected_state="running")
    d = IntelligenceDecision(
        component="svc", priority="high", action="restart_component",
        reason="r", confidence=80, intended_outcome=expected,
    )
    ar = decision_to_action(d)
    assert ar is not None
    assert ar.expected_outcome == expected  # carried as data only


def test_intended_outcome_none_by_default_and_for_advisory():
    d = make_decision(_ev(HealthStatus.CRITICAL))
    assert d.intended_outcome is None


# --- recommendations are separate/advisory ---------------------------------

def test_recommendation_separate_from_decision_execution():
    from app.core.intelligence.recommendations.engine import generate_recommendations
    recs = generate_recommendations(
        _ev(HealthStatus.CRITICAL),
        history={"recurring": True, "dominant_reason": "oom"},
    )
    assert isinstance(recs, list)
    assert all(isinstance(r, str) for r in recs)   # advisory strings only
    assert all(not isinstance(r, (ActionRequest, IntelligenceDecision)) for r in recs)


# --- execute_decision removal ------------------------------------------------

def test_execute_decision_no_longer_exists_in_service():
    import app.core.intelligence.service as svc
    assert not hasattr(svc, "execute_decision")
    # module still imports and exposes intelligence/decision functionality
    assert hasattr(svc, "calculate_platform_health")
    assert hasattr(svc, "make_decision")
