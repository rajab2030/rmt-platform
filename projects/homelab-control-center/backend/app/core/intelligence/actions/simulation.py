from app.core.intelligence.actions.models import (
    ActionRequest,
)


class ActionSimulationResult:
    def __init__(
        self,
        action_id: str,
        component: str,
        action_type: str,
        expected_impact: str,
        risk_level: str,
        rollback_available: bool,
    ):
        self.action_id = action_id
        self.component = component
        self.action_type = action_type
        self.expected_impact = expected_impact
        self.risk_level = risk_level
        self.rollback_available = rollback_available


def simulate_action(
    action: ActionRequest,
):
    """
    Estimate the impact of an action.

    This does not execute anything.
    """

    if action.action_type.value == "restart_component":

        return ActionSimulationResult(
            action_id=action.action_id,
            component=action.component,
            action_type=action.action_type.value,
            expected_impact="Temporary component restart",
            risk_level="medium",
            rollback_available=True,
        )

    return ActionSimulationResult(
        action_id=action.action_id,
        component=action.component,
        action_type=action.action_type.value,
        expected_impact="Unknown action impact",
        risk_level="unknown",
        rollback_available=False,
    )
