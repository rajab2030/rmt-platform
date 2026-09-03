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


def generic_source_to_observation(source_data):
    """
    Provider-independent / non-Docker test observation producer (D1).

    Accepts simple provider-agnostic data and emits a normalised
    ComponentObservation. This is the representative non-Docker source used to
    prove that downstream intelligence consumes the normalised contract rather
    than Docker-specific data. No real external provider is added.
    """
    return ComponentObservation(
        component=source_data["component"],
        source=source_data.get("source", "test"),
        state=source_data["state"],
        timestamp=source_data["timestamp"],
        signals=source_data.get("signals", {}),
        metadata=source_data.get("metadata", {}),
    )
