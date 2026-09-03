from datetime import datetime, timezone

from app.core.intelligence.observation.normalize import (
    normalize_observation,
)

from app.core.intelligence.schemas import (
    HealthIssue,
    HealthStatus,
    HealthEvaluation,
    HealthReason,
    HealthImpact,
)

# Freshness thresholds (D2). The semantics are fixed in the Core contract; the
# numeric values are configuration defaults. 600s preserves prior behavior and
# is defined once so it is not duplicated across callers.
FRESH_MAX_SECONDS = 60.0
STALE_THRESHOLD_SECONDS = 600.0


def observation_age(observation):
    """Age of an observation in seconds since its recorded timestamp."""
    return (
        datetime.now(timezone.utc)
        - observation.timestamp.replace(tzinfo=timezone.utc)
    ).total_seconds()


def freshness_for_age(age):
    """Agreed freshness semantics.

    - current: age <= FRESH_MAX_SECONDS
    - fresh:   age <= STALE_THRESHOLD_SECONDS
    - stale:   age > STALE_THRESHOLD_SECONDS
    """
    if age <= FRESH_MAX_SECONDS:
        return "current"
    if age <= STALE_THRESHOLD_SECONDS:
        return "fresh"
    return "stale"


def _derive_confidence(observation, age):
    """Deterministic confidence (0-100) derived from actual evidence (D3).

    Confidence is never an arbitrary fixed value; it is a sum of evidence
    components that also appear in confidence_basis so the value is reviewable:
      - state resolvability, up to 40 (explicit running/stopped);
      - signal presence, up to 40 (scaled by count, baseline of 2 signals);
      - freshness, up to 30 (current 30 / fresh 20 / stale 10).
    Capped at 100.
    """
    confidence = 0
    basis = []

    state = (observation.state or "").strip().lower()
    if state in ("running", "stopped"):
        confidence += 40
        basis.append("state:" + state)
    elif state:
        confidence += 10
        basis.append("state:(unresolved)")
    else:
        basis.append("state:(none)")

    signal_count = len(observation.signals or {})
    confidence += min(signal_count, 2) * 20
    basis.append("signals:" + str(signal_count))

    if age is None:
        basis.append("age:(none)")
    elif age <= FRESH_MAX_SECONDS:
        confidence += 30
        basis.append("fresh:current")
    elif age <= STALE_THRESHOLD_SECONDS:
        confidence += 20
        basis.append("fresh:fresh")
    else:
        confidence += 10
        basis.append("fresh:stale")

    return min(confidence, 100), ", ".join(basis)


def evaluate_observation_health(observation, context=None):

    score = 100

    issues = []

    recommendations = []

    cpu_usage = observation.signals.get(
        "cpu_usage",
        0,
    )

    memory_usage = observation.signals.get(
        "memory_usage",
        0,
    )

    health = observation.metadata.get(
        "health",
        "unknown",
    )

    # State rule

    if observation.state != "running":

        score -= 40

        issues.append(
            HealthIssue(
                component=observation.component,
                message="Component is not running",
                severity=HealthStatus.CRITICAL,
                role=context.role if context else None,
                criticality=context.criticality if context else None,
            )
        )

        recommendations.append(
            f"Restart {observation.component}"
        )


    # CPU rule

    if cpu_usage > 90:

        score -= 20

        issues.append(
            HealthIssue(
                component=observation.component,
                message="High CPU usage",
                severity=HealthStatus.WARNING,
            )
        )

    elif cpu_usage > 70:

        score -= 10

        issues.append(
            HealthIssue(
                component=observation.component,
                message="Elevated CPU usage",
                severity=HealthStatus.WARNING,
            )
        )


    # Memory rule

    if memory_usage > 1024 * 1024 * 1024:

        score -= 20

        issues.append(
            HealthIssue(
                component=observation.component,
                message="High memory usage",
                severity=HealthStatus.WARNING,
            )
        )


    # Health rule

    if health == "unhealthy":

        score -= 30

        issues.append(
            HealthIssue(
                component=observation.component,
                message="Component health check failed",
                severity=HealthStatus.CRITICAL,
            )
        )


    # Freshness rule

    age = observation_age(observation)

    if age > STALE_THRESHOLD_SECONDS:

        score -= 10

        issues.append(
            HealthIssue(
                component=observation.component,
                message="Observation data is old",
                severity=HealthStatus.WARNING,
                role=context.role if context else None,
                criticality=context.criticality if context else None,
            )
        )


    # Final status

    if score >= 85:

        status = HealthStatus.HEALTHY

    elif score >= 60:

        status = HealthStatus.WARNING

    else:

        status = HealthStatus.CRITICAL


    return {
        "score": max(score, 0),
        "status": status,
        "issues": issues,
        "recommendations": recommendations,
    }


def create_health_evaluation(data, context=None):
    """Return a HealthEvaluation for every resolvable input state.

    Never returns None. Explicitly handles (D2):
    - missing observation
    - malformed observation
    - unknown component state
    - insufficient evidence
    - stale data
    - component/container failure (non-running)
    - healthy/running
    """

    if data is None:
        return create_missing_observation_evaluation()

    try:
        observation = normalize_observation(data)
    except Exception:
        return create_malformed_observation_evaluation()

    if not observation.component:
        return create_malformed_observation_evaluation()

    state = (observation.state or "").strip().lower()

    if state in ("", "unknown"):
        return create_unknown_state_evaluation(observation, context)

    if state != "running":
        return create_container_failure_evaluation(observation, context)

    if is_metric_stale(observation):
        return create_stale_data_evaluation(observation, context)

    if not observation.signals:
        return create_insufficient_evidence_evaluation(observation, context)

    return create_healthy_evaluation(observation, context)


def create_missing_observation_evaluation():

    return HealthEvaluation(
        component="unknown",
        status=HealthStatus.UNKNOWN,
        reason=HealthReason.MISSING_OBSERVATION,
        evidence=[
            "No observation data received"
        ],
        confidence=0,
        freshness="unknown",
        confidence_basis="no observation",
        impact=HealthImpact.MEDIUM,
        recommendation="Verify the observation source is producing data",
        message="Observation missing",
    )


def create_malformed_observation_evaluation():

    return HealthEvaluation(
        component="unknown",
        status=HealthStatus.UNKNOWN,
        reason=HealthReason.MALFORMED_OBSERVATION,
        evidence=[
            "Observation could not be normalized"
        ],
        confidence=0,
        freshness="unknown",
        confidence_basis="malformed/unnormalizable observation",
        impact=HealthImpact.MEDIUM,
        recommendation="Check the observation payload/source contract",
        message="Observation malformed",
    )


def create_unknown_state_evaluation(observation, context=None):

    age = observation_age(observation)

    evidence = [
        f"State '{observation.state}' is not resolvable",
        f"Observation age: {age:.1f} seconds",
    ]

    if context:

        evidence.append(
            f"Role: {context.role}"
        )

        evidence.append(
            f"Criticality: {context.criticality}"
        )

    return HealthEvaluation(
        component=observation.component,
        status=HealthStatus.UNKNOWN,
        reason=HealthReason.UNKNOWN_STATE,
        evidence=evidence,
        confidence=10,
        age_seconds=round(age, 1),
        freshness=freshness_for_age(age),
        confidence_basis="unresolved state; low evidence",
        impact=HealthImpact.MEDIUM,
        recommendation="Determine the component state before acting",
        message="Component state unknown",
    )


def create_insufficient_evidence_evaluation(observation, context=None):

    age = observation_age(observation)

    evidence = [
        "Component reports running but no signals were provided",
        f"Observation age: {age:.1f} seconds",
    ]

    if context:

        evidence.append(
            f"Role: {context.role}"
        )

        evidence.append(
            f"Criticality: {context.criticality}"
        )

    return HealthEvaluation(
        component=observation.component,
        status=HealthStatus.UNKNOWN,
        reason=HealthReason.INSUFFICIENT_EVIDENCE,
        evidence=evidence,
        confidence=20,
        age_seconds=round(age, 1),
        freshness=freshness_for_age(age),
        confidence_basis="state only; no signals",
        impact=HealthImpact.MEDIUM,
        recommendation="Collect signals for the component before judging health",
        message="Insufficient evidence to judge component health",
    )


def create_healthy_evaluation(observation, context=None):

    age = observation_age(observation)

    confidence, basis = _derive_confidence(observation, age)

    evidence = [
        "Component is running",
        f"Observation age: {age:.1f} seconds",
        f"Signals: {', '.join(sorted(observation.signals.keys()))}",
    ]

    if context:

        evidence.append(
            f"Role: {context.role}"
        )

        evidence.append(
            f"Criticality: {context.criticality}"
        )

    return HealthEvaluation(
        component=observation.component,
        status=HealthStatus.HEALTHY,
        reason=HealthReason.HEALTHY,
        evidence=evidence,
        confidence=confidence,
        age_seconds=round(age, 1),
        freshness=freshness_for_age(age),
        confidence_basis=basis,
        impact=HealthImpact.LOW,
        recommendation=None,
        message="Component is healthy",
    )


def create_container_failure_evaluation(observation, context=None):

    age = observation_age(observation)

    confidence, basis = _derive_confidence(observation, age)

    evidence = [
        "Component is not running"
    ]

    if context:

        evidence.append(
            f"Role: {context.role}"
        )

        evidence.append(
            f"Criticality: {context.criticality}"
        )

    return HealthEvaluation(
        component=observation.component,
        status=HealthStatus.CRITICAL,
        reason=HealthReason.COLLECTOR_FAILURE,
        evidence=evidence,
        confidence=confidence,
        age_seconds=round(age, 1),
        freshness=freshness_for_age(age),
        confidence_basis=basis,
        impact=HealthImpact.MEDIUM,
        recommendation=f"Restart {observation.component}",
        message="Component unavailable",
    )


def is_metric_stale(observation):

    age = observation_age(observation)

    return age > STALE_THRESHOLD_SECONDS


def create_stale_data_evaluation(observation, context=None):

    age = observation_age(observation)

    confidence, basis = _derive_confidence(observation, age)

    evidence = [
        f"Metric age: {age:.1f} seconds"
    ]

    if context:

        evidence.append(
            f"Role: {context.role}"
        )

        evidence.append(
            f"Criticality: {context.criticality}"
        )

    return HealthEvaluation(
        component=observation.component,
        status=HealthStatus.WARNING,
        reason=HealthReason.STALE_DATA,
        evidence=evidence,
        confidence=confidence,
        age_seconds=round(age, 1),
        freshness=freshness_for_age(age),
        confidence_basis=basis,
        impact=HealthImpact.MEDIUM,
        recommendation="Check metric collector freshness",
        message="Metric data is old",
    )
