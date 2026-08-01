from datetime import datetime
from pydantic import BaseModel


class ContainerMetric(BaseModel):
    name: str
    status: str
    cpu_usage: float | None = None
    memory_usage: int | None = None
    health: str | None = None
    timestamp: datetime


class PlatformMetric(BaseModel):
    platform: str
    timestamp: datetime
    containers_running: int
    containers_unhealthy: int
