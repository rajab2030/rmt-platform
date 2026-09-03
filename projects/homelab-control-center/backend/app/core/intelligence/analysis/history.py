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


def analyze_governed_outcomes(component: str | None = None):
    """
    L1 - summarize governed lifecycle evidence as analysis INFO ONLY.

    Consumes the read-only governed-history boundary. This function never
    authorizes, executes, or mutates governance state; it only reports what
    governed outcomes have been observed.

    Kept distinct from analyze_component_history() so observation/evaluation
    history and governed lifecycle history remain distinguishable.
    """
    from app.core.intelligence.analysis.governed_history import (
        get_governed_outcomes,
    )

    outcomes = get_governed_outcomes(component=component)

    blocked = [o for o in outcomes if o.outcome == "blocked"]
    completed = [o for o in outcomes if o.outcome == "completed"]

    verification_counts = {}
    for o in outcomes:
        if o.verification_status:
            verification_counts[o.verification_status] = (
                verification_counts.get(o.verification_status, 0) + 1
            )

    return {
        "component": component,
        "total_governed_outcomes": len(outcomes),
        "blocked": len(blocked),
        "completed": len(completed),
        "verification_counts": verification_counts,
        "outcomes": [
            {
                "action_id": o.action_id,
                "execution_id": o.execution_id,
                "component": o.component,
                "operation": o.operation,
                "outcome": o.outcome,
                "execution_status": o.execution_status,
                "verification_status": o.verification_status,
                "sources": o.sources,
            }
            for o in outcomes
        ],
    }
