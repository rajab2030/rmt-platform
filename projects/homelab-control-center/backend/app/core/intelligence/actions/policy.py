from app.core.intelligence.actions.models import (
    ActionRequest,
)


class ActionPolicyResult:

    def __init__(
        self,
        allowed: bool,
        reason: str,
        requires_approval: bool,
        evidence_references: tuple[str, ...] = (),
    ):
        self.allowed = allowed
        self.reason = reason
        self.requires_approval = requires_approval
        self.evidence_references = evidence_references


ALLOWED_ACTION_TYPES = {
    "restart_component",
    "start",
    "stop",
    "restart",
    "create",
    "remove",
}


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

    if action.action_type.value in ALLOWED_ACTION_TYPES:

        return ActionPolicyResult(
            allowed=True,
            reason="Action type allowed by policy",
            requires_approval=action.requires_approval,
        )

    return ActionPolicyResult(
        allowed=False,
        reason="Action type not approved by policy",
        requires_approval=True,
    )
