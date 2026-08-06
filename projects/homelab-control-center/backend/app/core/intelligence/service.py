from app.core.observability.service import (
    get_current_container_metrics,
)

from app.core.intelligence.context.service import (
    enrich_component,
)

from app.core.intelligence.rules import (
    evaluate_container_health,
    create_health_evaluation,
)

from app.core.intelligence.schemas import (
    HealthReport,
    HealthStatus,
)



def calculate_platform_health():

    metrics = get_current_container_metrics()


    if not metrics:

        return HealthReport(
            platform="RMT",
            score=0,
            status=HealthStatus.UNKNOWN,
            issues=[],
            evaluations=[],
            recommendations=[
                "No observability metrics available"
            ],
        )


    total_score = 0

    issues = []

    evaluations = []

    recommendations = []


    for metric in metrics:


        context_result = enrich_component(
            metric
        )


        context = context_result["context"]


        result = evaluate_container_health(
            metric,
            context
        )


        evaluation = create_health_evaluation(
            metric,
            context
        )


        if evaluation:

            evaluations.append(
                evaluation
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
        evaluations=evaluations,
        recommendations=recommendations,
    )
