from app.core.intelligence.actions.models import (
    ActionRequest,
)

from app.core.intelligence.execution.models import (
    ExecutionRequest,
)


def translate_action_to_execution(
    action: ActionRequest,
    authorization_id: str,
    risk_level: str | None = None,
) -> ExecutionRequest:
    """
    Translate an approved action into an execution request.

    This layer does not authorize actions.
    It only converts intent into execution format.
    """

    return ExecutionRequest(
        authorization_id=authorization_id,
        action_id=action.action_id,
        target=action.component,
        operation=action.action_type.value,
        parameters=action.parameters,
        risk_level=risk_level,
        expected_outcome=action.expected_outcome,
    )
