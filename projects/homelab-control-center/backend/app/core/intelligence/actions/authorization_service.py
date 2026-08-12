from app.core.intelligence.actions.authorization import (
    ExecutionAuthorization,
    AuthorizationStatus,
)

from app.core.intelligence.actions.approval_policy import (
    ApprovalMode,
)


def create_execution_authorization(
    action,
    approval_decision,
):
    """
    Convert an approved decision into an execution authorization.

    This function does not execute actions.
    It only creates permission to cross the execution boundary.
    """

    if approval_decision.mode != ApprovalMode.AUTO:
        return None

    if not approval_decision.approved:
        return None

    return ExecutionAuthorization(
        action_id=action.action_id,
        status=AuthorizationStatus.APPROVED,
        authorized_by="approval_policy",
        authorization_type="automatic",
        reason=approval_decision.reason,
    )
