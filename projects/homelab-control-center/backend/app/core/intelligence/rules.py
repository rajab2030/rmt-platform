from datetime import datetime, timezone

from app.core.intelligence.schemas import (
    HealthIssue,
    HealthStatus,
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


    # Docker health rule

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

    timestamp = metric.timestamp

    age = (
        now - timestamp.replace(tzinfo=timezone.utc)
    ).seconds


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
