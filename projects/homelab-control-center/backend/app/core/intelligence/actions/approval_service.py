from app.core.intelligence.actions.approval_policy import (
    evaluate_approval,
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
