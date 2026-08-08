from app.core.observability.service import (
    get_current_container_metrics,
)

from app.core.intelligence.context.service import (
    enrich_component,
)

from app.core.intelligence.observation.normalize import (
    normalize_observation,
)

from app.core.intelligence.rules import (
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

    evaluations = []

    recommendations = []


    for metric in metrics:

        observation = normalize_observation(
            metric
        )


        context_result = enrich_component(
            observation
        )

        context = context_result["context"]


        evaluation = create_health_evaluation(
            observation,
            context,
        )


        if evaluation:

            evaluations.append(
                evaluation
            )


            if evaluation.status == HealthStatus.CRITICAL:
                total_score += 40

            elif evaluation.status == HealthStatus.WARNING:
                total_score += 70

            else:
                total_score += 100


            if evaluation.recommendation:

                recommendations.append(
                    evaluation.recommendation
                )

        else:

            total_score += 100


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
        issues=[],
        evaluations=evaluations,
        recommendations=recommendations,
    )
