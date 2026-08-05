from app.core.intelligence.schemas import MetricBaseline
from app.core.observability.storage import get_container_metrics


def calculate_baseline(component: str) -> MetricBaseline:

    metrics = get_container_metrics(50)

    filtered = [
        m for m in metrics
        if m[0] == component
    ]

    if not filtered:
        return MetricBaseline(
            component=component,
            avg_cpu=0,
            avg_memory=0,
            samples=0,
        )

    avg_cpu = sum(
        m[2] for m in filtered
    ) / len(filtered)

    avg_memory = sum(
        m[3] for m in filtered
    ) / len(filtered)

    return MetricBaseline(
        component=component,
        avg_cpu=avg_cpu,
        avg_memory=avg_memory,
        samples=len(filtered),
    )
