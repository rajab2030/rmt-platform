from app.core.intelligence.observation.models import (
    ComponentObservation,
)


def container_metric_to_observation(metric):
    """
    Convert container-specific metric data
    into the generic intelligence observation model.
    """

    return ComponentObservation(
        component=metric.name,
        source="docker",
        state=metric.status,
        timestamp=metric.timestamp,
        signals={
            "cpu_usage": metric.cpu_usage,
            "memory_usage": metric.memory_usage,
        },
        metadata={
            "health": metric.health or "unknown",
        },
    )
