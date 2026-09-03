from app.core.intelligence.observation.adapters import (
    container_metric_to_observation,
    generic_source_to_observation,
)


def observe_container(metric):
    """
    Convert container-specific metrics
    into the generic observation model.
    """

    return container_metric_to_observation(metric)


def observe_test_source(source_data):
    """
    Convert a provider-independent (non-Docker/test) metric
    into the generic observation model.

    This is the representative non-Docker producer entering the same
    normalised ComponentObservation boundary as production observations (D1).
    """

    return generic_source_to_observation(source_data)
