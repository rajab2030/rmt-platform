from enum import Enum
from pydantic import BaseModel
from typing import List


class HealthStatus(str, Enum):

    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"



class HealthIssue(BaseModel):

    component: str
    message: str
    severity: HealthStatus

    role: str | None = None
    criticality: str | None = None



class HealthReason(str, Enum):

    NEW_COMPONENT = "new_component"
    NO_METRICS = "no_metrics"
    STALE_DATA = "stale_data"
    BASELINE_NOT_READY = "baseline_not_ready"
    COLLECTOR_FAILURE = "collector_failure"
    CONFIGURATION_MISSING = "configuration_missing"



class HealthImpact(str, Enum):

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"



class HealthEvaluation(BaseModel):

    component: str

    status: HealthStatus

    reason: HealthReason

    evidence: List[str] = []

    confidence: int = 0

    impact: HealthImpact = HealthImpact.LOW

    recommendation: str | None = None
    message: str



class HealthReport(BaseModel):

    platform: str
    score: int
    status: HealthStatus

    issues: List[HealthIssue] = []
    evaluations: List[HealthEvaluation] = []
    recommendations: List[str] = []



class MetricBaseline(BaseModel):

    component: str

    avg_cpu: float
    avg_memory: float

    samples: int



class MetricDeviation(BaseModel):

    component: str

    cpu_deviation: float
    memory_deviation: float

    risk: HealthStatus
