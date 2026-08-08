from collections import Counter

from app.core.intelligence.memory.query import (
    get_health_history,
)


def analyze_component_history(component: str):

    history = get_health_history(
        component
    )

    if not history:

        return {
            "component": component,
            "events": 0,
            "recurring": False,
        }


    statuses = Counter()
    reasons = Counter()


    for event in history:

        status = event.data.get(
            "status"
        )

        reason = event.data.get(
            "reason"
        )

        if status:
            statuses[status] += 1

        if reason:
            reasons[reason] += 1


    return {
        "component": component,
        "events": len(history),
        "warnings": statuses.get(
            "warning",
            0,
        ),
        "critical": statuses.get(
            "critical",
            0,
        ),
        "dominant_reason": (
            reasons.most_common(1)[0][0]
            if reasons
            else None
        ),
        "recurring": len(history) > 1,
    }
