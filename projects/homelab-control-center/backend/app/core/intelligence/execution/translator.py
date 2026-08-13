from app.core.intelligence.actions.models import (
    ActionRequest,
)

from app.core.intelligence.execution.models import (
    ExecutionRequest,
)


def translate_action_to_execution(
    action: ActionRequest,
) -> ExecutionRequest:
    """
    Translate an approved action into an execution request.

    This layer does not authorize actions.
    It only converts intent into execution format.
    """

    return ExecutionRequest(
        authorization_id=action.decision_id,
        action_id=action.action_id,
        target=action.component,
        operation=action.action_type.value,
    )
