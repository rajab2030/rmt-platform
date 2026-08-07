from app.core.intelligence.observation.models import (
    ComponentObservation,
)

from app.core.intelligence.observation.adapters import (
    container_metric_to_observation,
)


def normalize_observation(data):

    if isinstance(data, ComponentObservation):
        return data

    return container_metric_to_observation(data)
