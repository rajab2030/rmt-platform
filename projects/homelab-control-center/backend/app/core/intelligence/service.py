from app.core.intelligence.decision.engine import (
    make_decision,
)

from app.core.intelligence.analysis.anomaly import (
    calculate_deviation,
)

from app.core.intelligence.analysis.baseline import (
    calculate_baseline,
)

from app.core.intelligence.analysis.trends import (
    analyze_trend,
)

from app.core.intelligence.analysis.history import (
    analyze_component_history,
)

from app.core.intelligence.schemas import (
    IntelligenceAnalysis,
    HealthReport,
    HealthStatus,
)

from app.core.intelligence.memory import (
    health_evaluation_to_memory,
    remember,
)

from app.core.intelligence.recommendations.engine import (
    generate_recommendations,
)

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
            analysis=[],
            decisions=[],
        )

    total_score = 0

    evaluations = []
    recommendations = []
    analysis_results = []
    decisions = []

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

        if not evaluation:
            total_score += 100
            continue

        evaluations.append(
            evaluation
        )

        memory_record = health_evaluation_to_memory(
            evaluation
        )

        remember(
            memory_record
        )

        history = analyze_component_history(
            evaluation.component
        )

        baseline = calculate_baseline(
            evaluation.component
        )

        trend = analyze_trend(
            evaluation.component
        )

        deviation = None

        if baseline and baseline.samples:

            deviation = calculate_deviation(
                component=evaluation.component,
                current_cpu=observation.cpu_usage,
                current_memory=observation.memory_usage,
                baseline_cpu=baseline.avg_cpu,
                baseline_memory=baseline.avg_memory,
            )

        analysis = IntelligenceAnalysis(
            component=evaluation.component,
            deviation=deviation,
            trend=trend or {},
            history=history or {},
        )

        analysis_results.append(
            analysis
        )

        decision_result = make_decision(
            evaluation,
            analysis,
            context,
        )

        if decision_result:

            decisions.append(
                decision_result
            )

        generated = generate_recommendations(
            evaluation,
            history,
            context,
        ) or []

        recommendations.extend(
            generated
        )

        if evaluation.status == HealthStatus.CRITICAL:
            total_score += 40

        elif evaluation.status == HealthStatus.WARNING:
            total_score += 70

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
        analysis=analysis_results,
        decisions=decisions,
    )
