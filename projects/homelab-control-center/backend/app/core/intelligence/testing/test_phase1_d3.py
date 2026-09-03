"""C04 Phase 2 (D3) - intelligence evidence / confidence / uncertainty semantics."""
from datetime import datetime, timezone, timedelta

from app.core.intelligence.observation.models import ComponentObservation
from app.core.intelligence.rules import (
    create_health_evaluation,
    STALE_THRESHOLD_SECONDS,
)
from app.core.intelligence.schemas import HealthStatus, HealthReason


def _obs(state="running", signals=None, age_seconds=5, health_meta="healthy"):
    signals = {"cpu_usage": 20.0, "memory_usage": 30.0} if signals is None else signals
    return ComponentObservation(
        component="svc",
        source="test",
        state=state,
        timestamp=datetime.now(timezone.utc) - timedelta(seconds=age_seconds),
        signals=signals,
        metadata={"health": health_meta},
    )


# --- 1) healthy, complete + fresh evidence -> high confidence, evidence-backed
def test_healthy_complete_fresh_is_high_confidence():
    ev = create_health_evaluation(_obs(signals={"cpu_usage": 20.0, "memory_usage": 30.0}))
    assert ev.status == HealthStatus.HEALTHY
    assert ev.reason == HealthReason.HEALTHY
    assert ev.confidence >= 90
    assert ev.evidence
    assert ev.freshness == "current"


# --- 2) healthy, partial evidence -> reduced confidence
def test_healthy_partial_evidence_reduces_confidence():
    full = create_health_evaluation(_obs(signals={"cpu_usage": 20.0, "memory_usage": 30.0}))
    partial = create_health_evaluation(_obs(signals={"cpu_usage": 20.0}))
    assert full.status == HealthStatus.HEALTHY
    assert partial.status == HealthStatus.HEALTHY
    assert partial.confidence < full.confidence


# --- 3) degraded/failed + evidence -> confidence reflects available evidence
def test_failure_confidence_reflects_available_evidence():
    no_signal = create_health_evaluation(_obs(state="stopped", signals={}))
    with_signal = create_health_evaluation(_obs(state="stopped", signals={"cpu_usage": 20.0}))
    assert no_signal.status == HealthStatus.CRITICAL
    assert with_signal.status == HealthStatus.CRITICAL
    # more evidence -> at least as much confidence, and basis present
    assert with_signal.confidence >= no_signal.confidence
    assert with_signal.confidence_basis
    assert with_signal.confidence > 0


# --- 4) stale -> freshness reflected and confidence reduced
def test_stale_confidence_reduced_and_freshness_reflected():
    fresh = create_health_evaluation(_obs(signals={"cpu_usage": 20.0, "memory_usage": 30.0}, age_seconds=5))
    stale = create_health_evaluation(
        _obs(signals={"cpu_usage": 20.0, "memory_usage": 30.0}, age_seconds=STALE_THRESHOLD_SECONDS + 1)
    )
    assert stale.status == HealthStatus.WARNING
    assert stale.reason == HealthReason.STALE_DATA
    assert stale.freshness == "stale"
    assert stale.confidence < fresh.confidence


# --- 5) missing/insufficient -> UNKNOWN + minimum/low confidence
def test_missing_unknown_minimum_confidence():
    ev = create_health_evaluation(None)
    assert ev.status == HealthStatus.UNKNOWN
    assert ev.confidence == 0
    assert ev.confidence_basis


def test_insufficient_evidence_unknown_low_confidence():
    ev = create_health_evaluation(_obs(signals={}))
    assert ev.status == HealthStatus.UNKNOWN
    assert ev.reason == HealthReason.INSUFFICIENT_EVIDENCE
    assert ev.confidence <= 20
    assert ev.confidence_basis


# --- 6) confidence_basis corresponds to actual evidence
def test_confidence_basis_tracks_evidence():
    full = create_health_evaluation(_obs(signals={"cpu_usage": 20.0, "memory_usage": 30.0}))
    assert "signals:2" in full.confidence_basis
    assert "fresh:current" in full.confidence_basis
    stale = create_health_evaluation(
        _obs(signals={"cpu_usage": 20.0, "memory_usage": 30.0}, age_seconds=STALE_THRESHOLD_SECONDS + 1)
    )
    assert "fresh:stale" in stale.confidence_basis


# --- 7) confidence cannot become high merely because a fixture looks healthy
def test_confidence_follows_evidence_not_fixture_label():
    # "healthy"-looking observation with no usable signals must not become
    # high-confidence or healthy just because metadata says healthy.
    ev = create_health_evaluation(_obs(signals={}, health_meta="healthy"))
    assert ev.status == HealthStatus.UNKNOWN
    assert ev.status != HealthStatus.HEALTHY
    assert ev.confidence <= 20
    assert ev.reason == HealthReason.INSUFFICIENT_EVIDENCE


# --- 8) UNKNOWN remains distinct from HEALTHY
def test_unknown_distinct_from_healthy():
    unknown = create_health_evaluation(_obs(state="unknown", signals={}))
    healthy = create_health_evaluation(_obs(state="running", signals={"cpu_usage": 20.0, "memory_usage": 30.0}))
    assert unknown.status == HealthStatus.UNKNOWN
    assert healthy.status == HealthStatus.HEALTHY
    assert unknown.status != healthy.status
    assert unknown.confidence < healthy.confidence
