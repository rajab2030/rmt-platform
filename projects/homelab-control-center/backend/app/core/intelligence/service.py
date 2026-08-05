from app.core.observability.service import (
    get_recent_container_metrics,
)

from app.core.intelligence.rules import (
    evaluate_container_health,
)

from app.core.intelligence.schemas import (
    HealthReport,
    HealthStatus,
)


def calculate_platform_health():

    metrics = get_recent_container_metrics()


    if not metrics:

        return HealthReport(
            platform="RMT",
            score=0,
            status=HealthStatus.UNKNOWN,
            issues=[],
            recommendations=[
                "No observability metrics available"
            ],
        )


    total_score = 0

    issues = []

    recommendations = []


    for metric in metrics:

        result = evaluate_container_health(
            metric
        )

        total_score += result["score"]

        issues.extend(
            result["issues"]
        )

        recommendations.extend(
            result["recommendations"]
        )


    score = int(
        total_score / len(metrics)
    )


    if score >= 85:

        status = HealthStatus.HEALTHY

    elif score >= 60:

        status = HealthStatus.WARNING

    else:

        status = HealthStatus.CRITICAL


    return HealthReport(
        platform="RMT",
        score=score,
        status=status,
        issues=issues,
        recommendations=recommendations,
    )
