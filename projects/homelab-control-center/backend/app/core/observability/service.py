
from app.core.observability.storage import save_container_metric

from datetime import datetime

from app.core.observability.schemas import (
    ContainerMetric,
    PlatformMetric,
)


container_metrics: list[ContainerMetric] = []

platform_metrics: list[PlatformMetric] = []


def record_container_metric(
    metric: ContainerMetric
):
    container_metrics.append(metric)

    container_metrics.append(metric)

    save_container_metric(metric)


def record_platform_metric(
    metric: PlatformMetric
):
    platform_metrics.append(metric)


def get_latest_container_metrics():

    return container_metrics[-1:]


def get_latest_platform_metric():

    if platform_metrics:
        return platform_metrics[-1]

    return None
