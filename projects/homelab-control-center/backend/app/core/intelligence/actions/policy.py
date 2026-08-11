from app.core.intelligence.actions.models import (
    ActionRequest,
)


class ActionPolicyResult:

    def __init__(
        self,
        allowed: bool,
        reason: str,
        requires_approval: bool,
    ):
        self.allowed = allowed
        self.reason = reason
        self.requires_approval = requires_approval


def evaluate_action_policy(
    action: ActionRequest,
    context=None,
):

    criticality = None

    if isinstance(context, dict):
        criticality = context.get(
            "criticality"
        )
    else:
        criticality = getattr(
            context,
            "criticality",
            None,
        )

    if action.confidence < 70:

        return ActionPolicyResult(
            allowed=False,
            reason="Confidence below action threshold",
            requires_approval=True,
        )

    if criticality == "critical":

        return ActionPolicyResult(
            allowed=True,
            reason="Critical component requires approval",
            requires_approval=True,
        )

    if action.action_type.value == "restart_component":

        return ActionPolicyResult(
            allowed=True,
            reason="Restart action allowed",
            requires_approval=action.requires_approval,
        )

    return ActionPolicyResult(
        allowed=False,
        reason="Action type not approved by policy",
        requires_approval=True,
    )
