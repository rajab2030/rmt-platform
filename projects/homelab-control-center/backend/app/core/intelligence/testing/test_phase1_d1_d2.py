"""C04 Phase 1 (D1/D2) contract tests.

D1 - provider-independent observation boundary.
D2 - freshness / stale / unknown foundation.
"""
from datetime import datetime, timezone, timedelta

from app.core.intelligence.observation.models import ComponentObservation
from app.core.intelligence.observation.service import observe_test_source
from app.core.intelligence.observation.normalize import normalize_observation
from app.core.intelligence.observation.adapters import generic_source_to_observation

from app.core.intelligence.rules import (
    create_health_evaluation,
    freshness_for_age,
    STALE_THRESHOLD_SECONDS,
)

from app.core.intelligence.schemas import HealthStatus, HealthReason


# ---------------------------------------------------------------------------
# D1 - provider-independent observation boundary
# ---------------------------------------------------------------------------

def test_non_docker_test_source_enters_normalized_boundary():
    """A non-Docker/test producer yields a normalized ComponentObservation."""
    data = {
        "component": "test-service",
        "state": "running",
        "timestamp": datetime.now(timezone.utc),
        "signals": {"cpu_usage": 20.0, "memory_usage": 30.0},
        "metadata": {"health": "healthy"},
    }
    observation = observe_test_source(data)
    assert isinstance(observation, ComponentObservation)
    assert observation.source == "test"
    assert observation.state == "running"


def test_normalize_passes_non_docker_observation_through():
    """normalize_observation accepts a ComponentObservation unchanged, proving
    downstream consumes the normalized contract, not Docker-specific data."""
    observation = generic_source_to_observation(
        {
            "component": "test-service",
            "state": "running",
            "timestamp": datetime.now(timezone.utc),
            "signals": {"cpu_usage": 20.0},
            "metadata": {},
        }
    )
    normalized = normalize_observation(observation)
    assert normalized is observation or normalized == observation
    assert normalized.source == "test"
    assert normalized.component == "test-service"


def test_healthy_evaluation_from_non_docker_source():
    """A non-Docker healthy observation produces a HEALTHY HealthEvaluation."""
    data = {
        "component": "test-service",
        "state": "running",
        "timestamp": datetime.now(timezone.utc),
        "signals": {"cpu_usage": 20.0, "memory_usage": 30.0},
    }
    evaluation = create_health_evaluation(generic_source_to_observation(data))
    assert evaluation is not None
    assert evaluation.status == HealthStatus.HEALTHY
    assert evaluation.reason == HealthReason.HEALTHY
    assert evaluation.evidence


# ---------------------------------------------------------------------------
# D2 - healthy evaluation (was returning None)
# ---------------------------------------------------------------------------

def test_healthy_observation_returns_health_evaluation_not_none():
    evaluation = create_health_evaluation(
        _base_observation(fresh=True))
    assert evaluation is not None
    assert evaluation.status == HealthStatus.HEALTHY
    assert evaluation.reason == HealthReason.HEALTHY
    # inspectable evidence + freshness metadata
    assert evaluation.evidence
    assert evaluation.age_seconds is not None
    assert evaluation.freshness == "current"
    assert evaluation.confidence > 0
    assert evaluation.confidence_basis


def test_fresh_observation_semantics():
    """fresh = age <= stale threshold; label reflects closeness to now."""
    assert freshness_for_age(5) == "current"
    assert freshness_for_age(120) == "fresh"  # > fresh, <= stale
    assert freshness_for_age(STALE_THRESHOLD_SECONDS + 1) == "stale"

    # a component ~2 minutes old is still 'fresh' (not stale) and evaluates
    # as HEALTHY with freshness metadata preserved.
    evaluation = create_health_evaluation(
        _base_observation(fresh=False, age_seconds=120))
    assert evaluation.status == HealthStatus.HEALTHY
    assert evaluation.freshness == "fresh"


def test_stale_observation():
    evaluation = create_health_evaluation(
        _base_observation(fresh=False, age_seconds=3600))
    assert evaluation.status == HealthStatus.WARNING
    assert evaluation.reason == HealthReason.STALE_DATA
    assert evaluation.freshness == "stale"
    assert evaluation.age_seconds is not None


def test_freshness_threshold_constant_is_single_source():
    """600 default preserved and no longer duplicated as a literal in rules."""
    assert STALE_THRESHOLD_SECONDS == 600.0


# ---------------------------------------------------------------------------
# D2 - UNKNOWN handling
# ---------------------------------------------------------------------------

def test_missing_observation_is_unknown_not_healthy_or_safe():
    evaluation = create_health_evaluation(None)
    assert evaluation.status == HealthStatus.UNKNOWN
    assert evaluation.reason == HealthReason.MISSING_OBSERVATION
    assert evaluation.confidence == 0


def test_malformed_observation_is_unknown():
    evaluation = create_health_evaluation("not-an-observation")
    assert evaluation.status == HealthStatus.UNKNOWN
    assert evaluation.reason == HealthReason.MALFORMED_OBSERVATION
    assert evaluation.confidence == 0


def test_malformed_missing_component_is_unknown():
    evaluation = create_health_evaluation(
        generic_source_to_observation(
            {
                "component": "",
                "state": "running",
                "timestamp": datetime.now(timezone.utc),
                "signals": {},
            }
        )
    )
    assert evaluation.status == HealthStatus.UNKNOWN
    assert evaluation.reason == HealthReason.MALFORMED_OBSERVATION


def test_unknown_component_state_is_unknown():
    observation = ComponentObservation(
        component="test-service",
        source="test",
        state="unknown",
        timestamp=datetime.now(timezone.utc),
        signals={},
    )
    evaluation = create_health_evaluation(observation)
    assert evaluation.status == HealthStatus.UNKNOWN
    assert evaluation.reason == HealthReason.UNKNOWN_STATE
    assert evaluation.confidence < 50


def test_insufficient_evidence_is_unknown():
    observation = ComponentObservation(
        component="test-service",
        source="test",
        state="running",
        timestamp=datetime.now(timezone.utc),
        signals={},
    )
    evaluation = create_health_evaluation(observation)
    assert evaluation.status == HealthStatus.UNKNOWN
    assert evaluation.reason == HealthReason.INSUFFICIENT_EVIDENCE
    assert evaluation.confidence < 50


def test_unknown_is_distinct_from_healthy():
    unknown = create_health_evaluation(
        ComponentObservation(
            component="test-service",
            source="test",
            state="unknown",
            timestamp=datetime.now(timezone.utc),
            signals={},
        )
    )
    assert unknown.status != HealthStatus.HEALTHY
    assert unknown.status == HealthStatus.UNKNOWN


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _base_observation(fresh=True, age_seconds=5):
    age = 0 if fresh else age_seconds
    return ComponentObservation(
        component="test-service",
        source="test",
        state="running",
        timestamp=datetime.now(timezone.utc) - timedelta(seconds=age),
        signals={"cpu_usage": 20.0, "memory_usage": 30.0},
        metadata={"health": "healthy"},
    )


def test_unknown_does_not_contribute_as_healthy(monkeypatch):
    """UNKNOWN must not inflate the platform health score (service level)."""
    from app.core.intelligence.service import calculate_platform_health

    class _UnknownMetric:
        name = "test-service"
        status = "unknown"
        health = "unknown"
        cpu_usage = 0.0
        memory_usage = 0.0
        timestamp = datetime.now(timezone.utc)

    monkeypatch.setattr(
        "app.core.intelligence.service.get_current_container_metrics",
        lambda: [_UnknownMetric()],
    )

    report = calculate_platform_health()

    # The unknown-state observation must not be judged healthy.
    assert report.score < 85
    assert report.status != HealthStatus.HEALTHY
    assert any(e.status == HealthStatus.UNKNOWN for e in report.evaluations)

def test_deviation_branch_uses_signals_contract(monkeypatch):
    """D1 regression.

    calculate_platform_health() must compute deviation from the canonical
    signals contract, not stale cpu_usage/memory_usage attributes. A populated
    baseline forces the deviation branch (service.py: calculate_deviation),
    which previously raised AttributeError on the generic ComponentObservation.
    """
    from app.core.intelligence.service import calculate_platform_health

    class _HealthyMetric:
        name = "test-service"
        status = "running"
        health = "healthy"
        cpu_usage = 50.0
        memory_usage = 60.0
        timestamp = datetime.now(timezone.utc)

    # Current observation flows through normalize_observation -> signals.
    monkeypatch.setattr(
        "app.core.intelligence.service.get_current_container_metrics",
        lambda: [_HealthyMetric()],
    )

    # Populated historical metrics for "test-service" make baseline.samples
    # truthy, so service.calculate_platform_health enters the deviation branch.
    monkeypatch.setattr(
        "app.core.intelligence.analysis.baseline.get_container_metrics",
        lambda limit=50: [
            (
                "test-service",
                "running",
                30.0,
                30.0,
                "healthy",
                datetime.now(timezone.utc) - timedelta(minutes=10),
            )
        ],
    )

    # Must not raise AttributeError despite baseline.samples being populated.
    report = calculate_platform_health()

    assert report is not None
    assert any(
        e.component == "test-service" for e in report.evaluations
    )
    # Deviation is actually calculated and preserved in the analysis output.
    analysis = next(
        (a for a in report.analysis if a.component == "test-service"),
        None,
    )
    assert analysis is not None
    assert analysis.deviation is not None
    assert analysis.deviation.cpu_deviation is not None
    assert analysis.deviation.memory_deviation is not None
