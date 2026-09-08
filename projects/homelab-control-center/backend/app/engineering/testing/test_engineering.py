"""RMT-CAP-02 focused tests (above-Core, read-only, no Docker).

Verifies component resolution, impact, engineering-change risk (explicit
deterministic rule), recommendation, evidence traceability, and the
read-only guarantee.
"""
import app.engineering.service as service
from app.engineering.models import (
    ResolutionStatus,
    EngineeringChangeAssessment,
)


class _Ctx:
    """Minimal component-context stand-in with a criticality attribute."""

    def __init__(self, criticality):
        self.criticality = criticality


class _V:
    """Minimal governed-outcome view stand-in."""

    def __init__(self, component="uptime-kuma", verification_status="verified_success"):
        self.component = component
        self.verification_status = verification_status


class _F:
    """Minimal prior-failure stand-in."""


# ---------------------------------------------------------------------------
# Component resolution (exact/unique only)
# ---------------------------------------------------------------------------
def test_resolve_by_module_id():
    status, entity = service.resolve_component("control-center")
    assert status == ResolutionStatus.RESOLVED
    assert entity == "control-center"


def test_resolve_by_container_name():
    status, entity = service.resolve_component("rmt-ai-assistant")
    assert status == ResolutionStatus.RESOLVED
    assert entity == "rmt-ai-assistant-e04095"


def test_resolve_by_context_name():
    status, entity = service.resolve_component("uptime-kuma")
    assert status == ResolutionStatus.RESOLVED
    assert entity == "uptime-kuma"


def test_resolve_unknown_component():
    status, entity = service.resolve_component("does-not-exist")
    assert status == ResolutionStatus.UNKNOWN_COMPONENT
    assert entity is None


def test_resolve_ambiguous_component(monkeypatch):
    # Two distinct entities both match "foo": module_id "foo" and a different
    # module whose container is "foo".
    class _M:
        def __init__(self, module_id, container):
            self.module_id = module_id
            self.runtime = type("R", (), {"container": container})()

    monkeypatch.setattr(
        service,
        "get_modules",
        lambda: [_M("foo", "foo"), _M("bar", "foo")],
    )
    status, entity = service.resolve_component("foo")
    assert status == ResolutionStatus.AMBIGUOUS_COMPONENT
    assert entity is None


# ---------------------------------------------------------------------------
# Impact analysis
# ---------------------------------------------------------------------------
def test_impact_direct_dependent(monkeypatch):
    class _M:
        def __init__(self, module_id, deps, container=None):
            self.module_id = module_id
            self.dependencies = deps
            self.runtime = type("R", (), {"container": container or module_id})()

    monkeypatch.setattr(
        service,
        "get_modules",
        lambda: [_M("web", ["db"]), _M("db", [])],
    )
    monkeypatch.setattr(service, "get_governed_outcomes", lambda: [])
    monkeypatch.setattr(service, "get_previous_failures", lambda c: [])

    affected = service.compute_impact("db", "db")
    rels = {a.component: a.relationship for a in affected}
    assert "web" in rels
    assert "dependent" in rels["web"]


def test_impact_governed_evidence_related(monkeypatch):
    monkeypatch.setattr(service, "get_governed_outcomes", lambda: [_V()])
    monkeypatch.setattr(service, "get_previous_failures", lambda c: [])

    affected = service.compute_impact("uptime-kuma", "uptime-kuma")
    assert any(
        a.component == "uptime-kuma" and "evidence_related" in a.relationship
        for a in affected
    )


# ---------------------------------------------------------------------------
# Engineering-change risk (explicit deterministic rule)
# ---------------------------------------------------------------------------
def test_risk_high_when_governance_and_failures(monkeypatch):
    monkeypatch.setattr(service, "get_governed_outcomes", lambda: [_V()])
    monkeypatch.setattr(service, "get_previous_failures", lambda c: [_F(), _F()])
    monkeypatch.setattr(service, "get_component_context", lambda c: _Ctx("medium"))

    affected = service.compute_impact("uptime-kuma", "uptime-kuma")
    risk = service.compute_risk("uptime-kuma", "uptime-kuma", affected)
    assert risk.classification == "high"
    assert any("governance_boundary" in e for e in risk.explanation)
    assert any("historical_failures" in e for e in risk.explanation)


def test_risk_medium_when_unknown_dependency(monkeypatch):
    # Empty registered dependencies -> unknown_dependency factor -> medium.
    monkeypatch.setattr(service, "get_governed_outcomes", lambda: [])
    monkeypatch.setattr(service, "get_previous_failures", lambda c: [])
    monkeypatch.setattr(service, "get_component_context", lambda c: None)

    affected = service.compute_impact("control-center", "control-center")
    risk = service.compute_risk("control-center", "control-center", affected)
    assert risk.classification == "medium"
    assert any(f.name == "unknown_dependency" and f.value == "True" for f in risk.factors)


def test_risk_factors_are_evidence_backed(monkeypatch):
    monkeypatch.setattr(service, "get_governed_outcomes", lambda: [])
    monkeypatch.setattr(service, "get_previous_failures", lambda c: [])
    monkeypatch.setattr(service, "get_component_context", lambda c: None)

    affected = service.compute_impact("control-center", "control-center")
    risk = service.compute_risk("control-center", "control-center", affected)
    names = {f.name for f in risk.factors}
    assert names == {
        "dependency_fan_out",
        "governance_boundary",
        "historical_failures",
        "verification_coverage",
        "unknown_dependency",
        "criticality",
    }
    assert all(f.evidence_source for f in risk.factors)


# ---------------------------------------------------------------------------
# Recommendation + evidence traceability
# ---------------------------------------------------------------------------
def test_recommendation_and_evidence_traceable(monkeypatch):
    monkeypatch.setattr(service, "get_governed_outcomes", lambda: [_V()])
    monkeypatch.setattr(service, "get_previous_failures", lambda c: [_F()])
    monkeypatch.setattr(service, "get_component_context", lambda c: _Ctx("medium"))

    result = service.assess_engineering_change("uptime-kuma", "update")
    assert isinstance(result, EngineeringChangeAssessment)
    assert result.resolution == ResolutionStatus.RESOLVED
    assert result.risk.classification == "high"
    assert result.recommendation is not None
    assert result.recommendation.text
    # Every material conclusion is traceable.
    assert result.evidence
    assert any(e.claim.startswith("Engineering-change risk") for e in result.evidence)
    assert any(e.claim.startswith("Recommendation") for e in result.evidence)


def test_unknown_component_result(monkeypatch):
    monkeypatch.setattr(service, "get_modules", lambda: [])
    monkeypatch.setattr(service, "get_component_context", lambda c: None)
    result = service.assess_engineering_change("nope", "restart")
    assert result.resolution == ResolutionStatus.UNKNOWN_COMPONENT
    assert result.risk is None


# ---------------------------------------------------------------------------
# Read-only guarantee
# ---------------------------------------------------------------------------
def test_read_only_no_store_write(monkeypatch):
    # Any store save/write must never be called by the assessment.
    def boom(*a, **k):
        raise AssertionError("CAP-02 must not write to any store")

    import app.core.intelligence.execution.storage as exec_storage
    import app.core.intelligence.execution.trace_storage as trace_storage
    import app.core.intelligence.verification.storage as verif
    import app.core.intelligence.actions.approval_storage as appr
    import app.core.intelligence.actions.authorization_storage as authz

    monkeypatch.setattr(exec_storage.execution_audit_storage, "save", boom)
    monkeypatch.setattr(trace_storage.execution_trace_storage, "save", boom)
    monkeypatch.setattr(verif.verification_storage, "save", boom)
    monkeypatch.setattr(appr.approval_record_storage, "save", boom)
    monkeypatch.setattr(authz.execution_authorization_storage, "save", boom)

    # Runs to completion without touching any write path.
    result = service.assess_engineering_change("control-center", "update")
    assert result.resolution == ResolutionStatus.RESOLVED


# ---------------------------------------------------------------------------
# Demonstration (deterministic, derived from the rule, not hardcoded)
# ---------------------------------------------------------------------------
def test_demonstration_derives_risk_from_rule(monkeypatch):
    """Reproducible demo: proposed change to uptime-kuma with seeded evidence.

    The risk classification is DERIVED by the deterministic rule from the
    seeded factors, and the contributing evidence is exposed.
    """
    monkeypatch.setattr(service, "get_governed_outcomes", lambda: [_V()])
    monkeypatch.setattr(service, "get_previous_failures", lambda c: [_F()])
    monkeypatch.setattr(service, "get_component_context", lambda c: _Ctx("medium"))

    result = service.assess_engineering_change("uptime-kuma", "update")

    # Derived, not hardcoded: classification follows from the factors.
    assert result.risk.classification in {"low", "medium", "high"}
    assert result.risk.classification == "high"  # governance + failures rule
    # Contributing evidence exposed.
    factor_names = {f.name for f in result.risk.factors}
    assert "governance_boundary" in factor_names
    assert "historical_failures" in factor_names
    assert result.risk.explanation
    assert result.evidence
