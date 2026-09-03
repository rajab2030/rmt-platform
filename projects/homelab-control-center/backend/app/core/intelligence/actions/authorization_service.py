from datetime import datetime, timedelta, timezone

from app.core.intelligence.actions.authorization import (
    ExecutionAuthorization,
    AuthorizationStatus,
)

from app.core.intelligence.actions.approval_policy import (
    ApprovalMode,
)


# Authorization validity window. C01 enforces expiry; durability is C02.
AUTHORIZATION_TTL_SECONDS = 300


def _expiry():
    return datetime.now(timezone.utc) + timedelta(
        seconds=AUTHORIZATION_TTL_SECONDS
    )


def create_execution_authorization(
    action,
    approval_decision,
):
    """
    Convert an approved decision into an execution authorization.

    This function does not execute actions.
    It only creates permission to cross the execution boundary.

    The authorization is bound to the governed action and approval, and
    carries provenance (decision_id, approval_id) plus an expiry window.
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
        decision_id=action.decision_id,
        approval_id=approval_decision.approval_id,
        reason=approval_decision.reason,
        target=action.component,
        operation=action.action_type.value,
        expected_outcome=action.expected_outcome,
        expires_at=_expiry(),
    )


def create_manual_authorization(
    action,
    approved_by: str,
    reason: str = "",
    approval_id: str | None = None,
):
    """
    Create an authorization from a legitimately granted manual approval.

    This is the only way a manually held action may resume. It is created
    from the previously governed action and the human approval result, not
    from a caller-supplied identifier.
    """

    return ExecutionAuthorization(
        action_id=action.action_id,
        status=AuthorizationStatus.APPROVED,
        authorized_by=approved_by,
        authorization_type="manual",
        decision_id=action.decision_id,
        approval_id=approval_id,
        reason=reason,
        target=action.component,
        operation=action.action_type.value,
        expected_outcome=action.expected_outcome,
        expires_at=_expiry(),
    )
