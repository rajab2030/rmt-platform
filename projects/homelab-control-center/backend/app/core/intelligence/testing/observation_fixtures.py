from datetime import datetime, timezone

from app.core.intelligence.observation.models import (
    ComponentObservation,
)


def healthy_observation():
    return ComponentObservation(
        component="test-service",
        source="test",
        state="running",
        timestamp=datetime.now(timezone.utc),
        signals={
            "cpu_usage": 20,
            "memory_usage": 30,
        },
        metadata={
            "health": "healthy",
        },
    )


def stopped_observation():
    return ComponentObservation(
        component="test-service",
        source="test",
        state="stopped",
        timestamp=datetime.now(timezone.utc),
        signals={},
        metadata={},
    )
