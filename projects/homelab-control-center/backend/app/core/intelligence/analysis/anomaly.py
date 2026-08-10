from app.core.intelligence.schemas import (
    MetricDeviation,
    HealthStatus,
)


def calculate_deviation(
    component: str,
    current_cpu: float,
    current_memory: float,
    baseline_cpu: float,
    baseline_memory: float,
) -> MetricDeviation:

    cpu_deviation = 0

    memory_deviation = 0

    if baseline_cpu:
        cpu_deviation = (
            (current_cpu - baseline_cpu)
            / baseline_cpu
        )

    if baseline_memory:
        memory_deviation = (
            (current_memory - baseline_memory)
            / baseline_memory
        )

    risk = HealthStatus.HEALTHY

    if (
        cpu_deviation > 0.5
        or memory_deviation > 0.5
    ):
        risk = HealthStatus.WARNING

    if (
        cpu_deviation > 1.0
        or memory_deviation > 1.0
    ):
        risk = HealthStatus.CRITICAL

    return MetricDeviation(
        component=component,
        cpu_deviation=cpu_deviation,
        memory_deviation=memory_deviation,
        risk=risk,
    )
