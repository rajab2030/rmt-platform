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

    action_type = action.action_type.value

    if action_type == "restart_component":

        return ActionSimulationResult(
            action_id=action.action_id,
            component=action.component,
            action_type=action_type,
            expected_impact="Temporary component restart",
            risk_level="medium",
            rollback_available=True,
        )

    if action_type in {"start", "stop"}:

        return ActionSimulationResult(
            action_id=action.action_id,
            component=action.component,
            action_type=action_type,
            expected_impact="Temporary container operation",
            risk_level="low",
            rollback_available=True,
        )

    if action_type == "restart":

        return ActionSimulationResult(
            action_id=action.action_id,
            component=action.component,
            action_type=action_type,
            expected_impact="Restart container",
            risk_level="medium",
            rollback_available=True,
        )

    if action_type == "create":

        return ActionSimulationResult(
            action_id=action.action_id,
            component=action.component,
            action_type=action_type,
            expected_impact="Create new container",
            risk_level="medium",
            rollback_available=True,
        )

    if action_type == "remove":

        return ActionSimulationResult(
            action_id=action.action_id,
            component=action.component,
            action_type=action_type,
            expected_impact="Remove container",
            risk_level="high",
            rollback_available=False,
        )

    return ActionSimulationResult(
        action_id=action.action_id,
        component=action.component,
        action_type=action_type,
        expected_impact="Unknown action impact",
        risk_level="unknown",
        rollback_available=False,
    )
