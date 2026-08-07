from datetime import datetime, timezone

from app.core.intelligence.observation.normalize import normalize_observation

from app.core.intelligence.schemas import (
    HealthIssue,
    HealthStatus,
    HealthEvaluation,
    HealthReason,
    HealthImpact,
)


def evaluate_container_health(metric, context=None):

    score = 100

    issues = []

    recommendations = []

    # Status rule

    if metric.status != "running":

        score -= 40

        issues.append(
            HealthIssue(
                component=metric.name,
                message="Container is not running",
                severity=HealthStatus.CRITICAL,
                role=context.role if context else None,
                criticality=context.criticality if context else None,
            )
        )

        recommendations.append(
            f"Restart {metric.name}"
        )

    # CPU rule

    if metric.cpu_usage > 90:

        score -= 20

        issues.append(
            HealthIssue(
                component=metric.name,
                message="High CPU usage",
                severity=HealthStatus.WARNING,
            )
        )

    elif metric.cpu_usage > 70:

        score -= 10

        issues.append(
            HealthIssue(
                component=metric.name,
                message="Elevated CPU usage",
                severity=HealthStatus.WARNING,
            )
        )

    # Memory rule

    if metric.memory_usage > 1024 * 1024 * 1024:

        score -= 20

        issues.append(
            HealthIssue(
                component=metric.name,
                message="High memory usage",
                severity=HealthStatus.WARNING,
            )
        )

    # Health rule

    if metric.health == "unhealthy":

        score -= 30

        issues.append(
            HealthIssue(
                component=metric.name,
                message="Docker health check failed",
                severity=HealthStatus.CRITICAL,
            )
        )

    # Freshness rule

    now = datetime.now(timezone.utc)

    age = (
        now - metric.timestamp.replace(
            tzinfo=timezone.utc
        )
    ).total_seconds()

    if age > 600:

        score -= 10

        issues.append(
            HealthIssue(
                component=metric.name,
                message="Metric data is old",
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

    if data is None:
        return create_no_metrics_evaluation()

    observation = normalize_observation(data)

    if observation.state != "running":

        return create_container_failure_evaluation(
            observation,
            context,
        )

    if is_metric_stale(observation):

        return create_stale_data_evaluation(
            observation,
            context,
        )

    return None


def create_no_metrics_evaluation():

    return HealthEvaluation(
        component="unknown",
        status=HealthStatus.WARNING,
        reason=HealthReason.NO_METRICS,
        evidence=[
            "No metric data received"
        ],
        confidence=80,
        impact=HealthImpact.MEDIUM,
        recommendation="Check metrics collector",
        message="No metrics available",
    )


def create_container_failure_evaluation(observation, context=None):

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
        confidence=95,
        impact=HealthImpact.MEDIUM,
        recommendation=f"Restart {observation.component}",
        message="Component unavailable",
    )


def is_metric_stale(observation):

    now = datetime.now(timezone.utc)

    age = (
        now - observation.timestamp.replace(
            tzinfo=timezone.utc
        )
    ).total_seconds()

    return age > 600


def create_stale_data_evaluation(observation, context=None):

    now = datetime.now(timezone.utc)

    age = (
        now - observation.timestamp.replace(
            tzinfo=timezone.utc
        )
    ).total_seconds()

    evidence = [
        f"Metric age: {age} seconds"
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
        confidence=90,
        impact=HealthImpact.MEDIUM,
        recommendation="Check metric collector freshness",
        message="Metric data is old",
    )
