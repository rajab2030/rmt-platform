from app.core.intelligence.actions.models import (
    ActionRequest,
)

from app.core.intelligence.actions.policy import (
    evaluate_action_policy,
)


def process_action(
    action: ActionRequest,
    context=None,
):
    """
    Process an action request through policy validation.

    This layer does not execute actions.
    It only validates whether the requested action
    is acceptable according to platform policy.
    """

    policy_result = evaluate_action_policy(
        action,
        context,
    )

    return {
        "action_id": action.action_id,
        "component": action.component,
        "action_type": action.action_type,
        "allowed": policy_result.allowed,
        "reason": policy_result.reason,
        "requires_approval": policy_result.requires_approval,
    }
