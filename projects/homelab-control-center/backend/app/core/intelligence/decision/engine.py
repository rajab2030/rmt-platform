from app.core.intelligence.decision.models import (
    IntelligenceDecision,
)

from app.core.intelligence.schemas import (
    HealthEvaluation,
    HealthStatus,
)


def _decision(
    evaluation,
    priority,
    action,
    reason,
    intended_outcome=None,
):
    """Build an advisory IntelligenceDecision PROPOSAL."""
    return IntelligenceDecision(
        component=evaluation.component,
        priority=priority,
        action=action,
        reason=reason,
        confidence=evaluation.confidence,
        intended_outcome=intended_outcome,
        evidence=list(evaluation.evidence or []),
    )


def make_decision(
    evaluation: HealthEvaluation,
    analysis=None,
    context=None,
):
    """Produce an advisory IntelligenceDecision PROPOSAL.

    IntelligenceDecision is a proposal only: it cannot authorize, execute, call
    an adapter, or mint authorization. All C01/C02/C03 enforcement remains in
    the governed execution path (execute_governed_action), which is not invoked
    here.
    """

    # CRITICAL / failed: existing explicit investigation proposal.
    if evaluation.status == HealthStatus.CRITICAL:

        return _decision(
            evaluation,
            priority="high",
            action="investigate_immediately",
            reason=evaluation.message,
        )

    # WARNING / degraded: existing advisory monitoring/investigation proposal.
    if evaluation.status == HealthStatus.WARNING:

        if analysis and analysis.history.get("recurring"):

            reason = (
                "Recurring issue: "
                f"{analysis.history.get('dominant_reason')}"
            )

            return _decision(
                evaluation,
                priority="high",
                action="investigate_recurring_issue",
                reason=reason,
            )

        return _decision(
            evaluation,
            priority="medium",
            action="monitor",
            reason=evaluation.message,
        )

    # UNKNOWN: MUST NOT fall through to continue_monitoring. Emit an explicit
    # unresolved/uncertain advisory decision, distinct from healthy/safe.
    if evaluation.status == HealthStatus.UNKNOWN:

        return _decision(
            evaluation,
            priority="medium",
            action="uncertain",
            reason=evaluation.message or "State is unresolved",
        )

    # HEALTHY (only remaining status): advisory continue-monitoring proposal.
    return _decision(
        evaluation,
        priority="low",
        action="continue_monitoring",
        reason="Component is healthy",
    )
