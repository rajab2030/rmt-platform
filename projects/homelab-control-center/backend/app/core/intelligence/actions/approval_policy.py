from enum import Enum

from app.core.intelligence.actions.models import (
    ActionRequest,
)


class ApprovalMode(str, Enum):
    AUTO = "auto"
    MANUAL = "manual"
    REJECT = "reject"


class ApprovalDecision:
    def __init__(
        self,
        action_id: str,
        mode: ApprovalMode,
        approved: bool,
        reason: str,
    ):
        self.action_id = action_id
        self.mode = mode
        self.approved = approved
        self.reason = reason


def evaluate_approval(
    action: ActionRequest,
    policy_result,
    simulation_result,
):
    """
    Determine whether an action can proceed automatically,
    requires human approval, or must be rejected.

    This function does not create authorization and does not execute.
    """

    if not policy_result.allowed:
        return ApprovalDecision(
            action_id=action.action_id,
            mode=ApprovalMode.REJECT,
            approved=False,
            reason=policy_result.reason,
        )

    risk_level = getattr(
        simulation_result,
        "risk_level",
        "unknown",
    )

    rollback_available = getattr(
        simulation_result,
        "rollback_available",
        False,
    )

    if risk_level == "unknown":
        return ApprovalDecision(
            action_id=action.action_id,
            mode=ApprovalMode.REJECT,
            approved=False,
            reason="Simulation risk is unknown",
        )

    if risk_level in {"high", "critical"}:
        return ApprovalDecision(
            action_id=action.action_id,
            mode=ApprovalMode.MANUAL,
            approved=False,
            reason="High-risk action requires human approval",
        )

    if action.confidence < 90:
        return ApprovalDecision(
            action_id=action.action_id,
            mode=ApprovalMode.MANUAL,
            approved=False,
            reason="Confidence below automatic approval threshold",
        )

    if action.requires_approval:
        return ApprovalDecision(
            action_id=action.action_id,
            mode=ApprovalMode.MANUAL,
            approved=False,
            reason="Action explicitly requires approval",
        )

    if not rollback_available:
        return ApprovalDecision(
            action_id=action.action_id,
            mode=ApprovalMode.MANUAL,
            approved=False,
            reason="Rollback is not available",
        )

    if risk_level == "low":
        return ApprovalDecision(
            action_id=action.action_id,
            mode=ApprovalMode.AUTO,
            approved=True,
            reason="Action meets automatic approval criteria",
        )

    return ApprovalDecision(
        action_id=action.action_id,
        mode=ApprovalMode.MANUAL,
        approved=False,
        reason="Action requires human approval",
    )
