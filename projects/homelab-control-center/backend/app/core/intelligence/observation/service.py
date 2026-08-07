from app.core.intelligence.observation.adapters import (
    container_metric_to_observation,
)


def observe_container(metric):
    """
    Convert container-specific metrics
    into the generic observation model.
    """

    return container_metric_to_observation(metric)
