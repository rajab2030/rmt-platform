from app.core.observability.storage import (
    get_container_metrics,
)


def analyze_trend(component: str):

    metrics = get_container_metrics(20)

    filtered = [
        m
        for m in metrics
        if m[0] == component
    ]

    if len(filtered) < 2:
        return {
            "component": component,
            "trend": "unknown",
            "samples": len(filtered),
        }

    latest = filtered[0]
    previous = filtered[-1]

    cpu_change = latest[2] - previous[2]
    memory_change = latest[3] - previous[3]

    trend = "stable"

    if cpu_change > 0 or memory_change > 0:
        trend = "increasing"

    if cpu_change < 0 and memory_change < 0:
        trend = "decreasing"

    return {
        "component": component,
        "trend": trend,
        "cpu_change": cpu_change,
        "memory_change": memory_change,
        "samples": len(filtered),
    }
