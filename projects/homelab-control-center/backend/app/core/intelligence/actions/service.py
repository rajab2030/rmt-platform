from app.core.intelligence.actions.models import (
    ActionRequest,
)

from app.core.intelligence.actions.policy import (
    evaluate_action_policy,
)

from app.core.intelligence.actions.simulation import (
    simulate_action,
)

from app.core.intelligence.actions.approval_service import (
    process_approval,
    hold_for_manual_approval,
    record_approval_decision,
)

from app.core.intelligence.actions.approval_policy import (
    ApprovalMode,
)

from app.core.intelligence.actions.authorization_service import (
    create_execution_authorization,
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


def execute_governed_action(
    action: ActionRequest,
    adapter_name: str = "simulation",
):
    """
    Run an action through the single authoritative governed lifecycle:

        Action -> Policy -> Risk(Simulation) -> Approval -> Authorization
        -> Execution Translation -> ExecutionEngine

    This is the only path by which a Core-scope production mutation may
    reach an execution adapter. It does not fabricate authorization; the
    authorization is created only from a legitimate approval result.

    Post-execution verification resolves a trusted internal observer from the
    execution request; it is never caller-controlled.

    Returns a dict with a 'status' field discriminating outcomes:
        - "policy_denied"
        - "rejected"
        - "manual_approval_required"
        - "authorization_not_created"
        - "executed"
    """
    policy_result = evaluate_action_policy(action)
    if not policy_result.allowed:
        return {
            "status": "policy_denied",
            "reason": policy_result.reason,
            "requires_approval": policy_result.requires_approval,
            "action_id": action.action_id,
        }

    simulation_result = simulate_action(action)
    approval_decision = process_approval(
        action,
        policy_result,
        simulation_result,
    )

    if approval_decision.mode == ApprovalMode.REJECT:
        record_approval_decision(
            action,
            approval_decision,
            decision="rejected",
            approved_by="approval_policy",
        )
        return {
            "status": "rejected",
            "reason": approval_decision.reason,
            "action_id": action.action_id,
        }

    if approval_decision.mode == ApprovalMode.MANUAL:
        hold = hold_for_manual_approval(
            action,
            approval_decision,
            adapter_name=adapter_name,
            risk_level=simulation_result.risk_level,
        )
        record_approval_decision(
            action,
            approval_decision,
            decision="manual_required",
            approved_by="",
            approval_id=hold.approval_id,
        )
        return {
            "status": "manual_approval_required",
            "reason": approval_decision.reason,
            "action_id": action.action_id,
            "approval_id": hold.approval_id,
        }

    record_approval_decision(
        action,
        approval_decision,
        decision="approved",
        approved_by="approval_policy",
    )

    authorization = create_execution_authorization(
        action,
        approval_decision,
    )
    if authorization is None:
        return {
            "status": "authorization_not_created",
            "reason": "Approval was not auto-approved",
            "action_id": action.action_id,
        }

    execution_authorization_storage.save(authorization)

    execution_request = translate_action_to_execution(
        action,
        authorization_id=authorization.authorization_id,
        risk_level=simulation_result.risk_level,
    )

    result = execution_engine.execute(
        execution_request,
        adapter_name=adapter_name,
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
    }
