from fastapi import APIRouter

from app.core.observability.storage import (
    get_container_metrics,
)


router = APIRouter(
    prefix="/observability",
    tags=["Observability"],
)


def metric_to_dict(metric):

    return {
        "name": metric[0],
        "status": metric[1],
        "cpu_usage": metric[2],
        "memory_usage": metric[3],
        "health": metric[4],
        "timestamp": metric[5],
    }


@router.get("/history")
def observability_history():

    metrics = get_container_metrics()

    return [
        metric_to_dict(metric)
        for metric in metrics
    ]


@router.get("/latest")
def observability_latest():

    metrics = get_container_metrics(1)

    if metrics:
        return metric_to_dict(metrics[0])

    return None
