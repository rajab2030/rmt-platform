from app.core.intelligence.decision.models import (
    IntelligenceDecision,
)

from app.core.intelligence.schemas import (
    HealthEvaluation,
    HealthStatus,
)


def make_decision(
    evaluation: HealthEvaluation,
    analysis=None,
    context=None,
):
    if evaluation.status == HealthStatus.CRITICAL:

        return IntelligenceDecision(
            component=evaluation.component,
            priority="high",
            action="investigate_immediately",
            reason=evaluation.message,
            confidence=evaluation.confidence,
        )

    if evaluation.status == HealthStatus.WARNING:

        if analysis and analysis.history.get("recurring"):

            return IntelligenceDecision(
                component=evaluation.component,
                priority="high",
                action="investigate_recurring_issue",
                reason=(
                    f"Recurring issue: "
                    f"{analysis.history.get('dominant_reason')}"
                ),
                confidence=evaluation.confidence,
            )

        return IntelligenceDecision(
            component=evaluation.component,
            priority="medium",
            action="monitor",
            reason=evaluation.message,
            confidence=evaluation.confidence,
        )

    return IntelligenceDecision(
        component=evaluation.component,
        priority="low",
        action="continue_monitoring",
        reason="Component is healthy",
        confidence=evaluation.confidence,
    )
