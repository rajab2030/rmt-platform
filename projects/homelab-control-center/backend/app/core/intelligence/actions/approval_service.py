from datetime import datetime, timedelta, timezone

from app.core.intelligence.actions.approval_policy import (
    evaluate_approval,
)

from app.core.intelligence.actions.approval import (
    ApprovalHold,
    ApprovalRecord,
    ApprovalStatus,
)

from app.core.intelligence.actions.approval_storage import (
    approval_hold_storage,
    approval_record_storage,
)

from app.core.intelligence.actions.authorization_service import (
    create_manual_authorization,
)

from app.core.intelligence.actions.authorization_storage import (
    execution_authorization_storage,
)

from app.core.intelligence.execution.translator import (
    translate_action_to_execution,
)

from app.core.intelligence.execution.engine import (
    execution_engine,
)

from app.core.intelligence.verification.service import (
    verify_execution,
)


# Window during which a manual-approval hold may be legitimately resolved.
APPROVAL_HOLD_TTL_SECONDS = 300


def _hold_expiry():
    return datetime.now(timezone.utc) + timedelta(
        seconds=APPROVAL_HOLD_TTL_SECONDS
    )


def process_approval(
    action,
    policy_result,
    simulation_result,
):
    """
    Run the approval workflow for an action.

    This layer coordinates approval decisions.
    It does not authorize execution and does not execute actions.
    """

    decision = evaluate_approval(
        action,
        policy_result,
        simulation_result,
    )

    return decision


def record_approval_decision(
    action,
    approval_decision,
    decision: str,
    approved_by: str,
    approval_id: str | None = None,
) -> ApprovalRecord:
    """
    Persist an ApprovalRecord for a governed approval decision.

    For manual holds the approval_id is the hold's id (so the continuation
    can update the same record); otherwise it is the decision's own id.
    """
    record = ApprovalRecord(
        approval_id=approval_id or approval_decision.approval_id,
        action_id=action.action_id,
        decision=decision,
        approved_by=approved_by,
        reason=approval_decision.reason,
    )

    approval_record_storage.save(record)

    return record


def hold_for_manual_approval(
    action,
    approval_decision,
    adapter_name: str,
    risk_level: str | None = None,
) -> ApprovalHold:
    """
    Place a governed action into a manual-approval hold state.

    The action and its destination adapter are preserved so a legitimate
    continuation can resume the lifecycle without re-fabricating policy,
    risk, or authorization.
    """
    hold = ApprovalHold(
        action_id=action.action_id,
        action=action,
        adapter_name=adapter_name,
        reason=approval_decision.reason,
        expires_at=_hold_expiry(),
        risk_level=risk_level,
    )

    approval_hold_storage.save(hold)

    return hold


def approve_held_action(
    approval_id: str,
    approved_by: str,
    approved: bool = True,
):
    """
    Resume a manually held action after a legitimate approval decision.

    The continuation reuses the previously governed action and adapter. It
    does not create a new unrelated action, does not skip policy/risk (they
    already ran), and does not manufacture authorization independently.

    Post-execution verification resolves a trusted internal observer from the
    execution request; it is never caller-controlled.

    Returns a dict with a 'status' field:
        - "approval_not_found"
        - "approval_already_resolved"
        - "rejected"
        - "executed"
    """
    hold = approval_hold_storage.get_by_id(approval_id)

    if hold is None:
        return {
            "status": "approval_not_found",
            "reason": f"No held approval with id '{approval_id}'",
        }

    if hold.status != ApprovalStatus.PENDING:
        return {
            "status": "approval_already_resolved",
            "reason": f"Approval already {hold.status.value}",
            "approval_id": approval_id,
        }

    if (
        hold.expires_at is not None
        and hold.expires_at < datetime.now(timezone.utc)
    ):
        hold.status = ApprovalStatus.REJECTED
        return {
            "status": "approval_expired",
            "reason": "Approval hold has expired",
            "approval_id": approval_id,
            "action_id": hold.action_id,
        }

    if not approved:
        hold.status = ApprovalStatus.REJECTED
        approval_record_storage.update(
            approval_id,
            decision="rejected",
            approved_by=approved_by,
        )
        return {
            "status": "rejected",
            "reason": "Approval rejected by approver",
            "approval_id": approval_id,
            "action_id": hold.action_id,
        }

    hold.status = ApprovalStatus.APPROVED
    hold.approved_by = approved_by

    approval_record_storage.update(
        approval_id,
        decision="approved",
        approved_by=approved_by,
    )

    authorization = create_manual_authorization(
        hold.action,
        approved_by=approved_by,
        reason=hold.reason,
        approval_id=approval_id,
    )

    execution_authorization_storage.save(authorization)

    execution_request = translate_action_to_execution(
        hold.action,
        authorization_id=authorization.authorization_id,
        risk_level=hold.risk_level,
    )

    result = execution_engine.execute(
        execution_request,
        adapter_name=hold.adapter_name,
    )

    verification_status = None
    verification_reason = ""
    if result.success:
        verification = verify_execution(
            result.execution_id,
            execution_request.expected_outcome,
            execution_request=execution_request,
        )
        verification_status = verification.status
        verification_reason = verification.reason

    return {
        "status": "executed",
        "execution_id": result.execution_id,
        "status_detail": result.status,
        "success": result.success,
        "message": result.message,
        "verification_status": verification_status,
        "verification_reason": verification_reason,
        "approval_id": approval_id,
        "action_id": hold.action_id,
    }
