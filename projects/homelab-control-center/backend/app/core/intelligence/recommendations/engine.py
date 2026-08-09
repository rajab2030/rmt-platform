from app.core.intelligence.schemas import (
    HealthStatus,
)


def generate_recommendations(
    evaluation,
    history=None,
    context=None,
):

    recommendations = []


    if evaluation.status == HealthStatus.CRITICAL:

        recommendations.append(
            f"Investigate {evaluation.component} immediately"
        )


    elif evaluation.status == HealthStatus.WARNING:

        recommendations.append(
            f"Monitor {evaluation.component}"
        )


    if history:

        if history.get("recurring"):

            reason = history.get(
                "dominant_reason"
            )

            if reason:

                recommendations.append(
                    f"Recurring issue detected: {reason}"
                )


    if context:

        if context.criticality == "high":

            recommendations.append(
                "Prioritize because component criticality is high"
            )


    return recommendations
