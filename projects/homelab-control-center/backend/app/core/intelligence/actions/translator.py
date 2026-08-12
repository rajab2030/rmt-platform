from app.core.intelligence.decision.models import (
    IntelligenceDecision,
)

from app.core.intelligence.actions.models import (
    ActionRequest,
    ActionType,
)


ACTION_MAPPING = {
    "restart_component": ActionType.RESTART_COMPONENT,
    "create_checkpoint": ActionType.CREATE_CHECKPOINT,
    "scale_down": ActionType.SCALE_DOWN,
    "isolate_component": ActionType.ISOLATE_COMPONENT,
}


def decision_to_action(
    decision: IntelligenceDecision,
):
    """
    Translate an intelligence decision into
    a controlled action request.

    Unknown decisions are rejected by returning None.
    """

    action_type = ACTION_MAPPING.get(
        decision.action
    )

    if not action_type:
        return None

    return ActionRequest(
        decision_id=f"decision-{decision.component}",
        component=decision.component,
        action_type=action_type,
        reason=decision.reason,
        confidence=decision.confidence,
    )
