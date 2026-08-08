from datetime import datetime, timezone

from app.core.intelligence.memory.models import MemoryRecord
from app.core.intelligence.schemas import HealthEvaluation


def health_evaluation_to_memory(
    evaluation: HealthEvaluation,
):
    return MemoryRecord(
        component=evaluation.component,
        event_type="health_evaluation",
        timestamp=datetime.now(timezone.utc),
        data={
            "status": evaluation.status.value,
            "reason": evaluation.reason.value,
            "confidence": evaluation.confidence,
            "impact": evaluation.impact.value,
            "message": evaluation.message,
            "evidence": evaluation.evidence,
            "recommendation": evaluation.recommendation,
        },
    )
