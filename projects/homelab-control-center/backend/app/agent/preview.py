"""RMT-CAP-07 (C3) -- ``preview_proposal``: resolve a proposal to its
concrete ``ActionRequest`` + predicted governed outcome, with zero durable
writes.

An operator (or the agent's own calling code) sees exactly what a proposal
will do before it is actually submitted -- not a heuristic guess, but the
real frozen policy/risk/approval evaluation. ``execute_governed_action``
already calls ``evaluate_action_policy`` -> ``simulate_action`` ->
``process_approval`` *before* anything is written to storage (policy result,
simulation, approval decision are all pure); this reuses exactly those three
frozen functions and stops there.

No grant consumed, no hold, no authorization, no trace/audit/verification/
Learn record, no adapter invoked. Never calls ``execute_governed_action``.
"""
from app.core.intelligence.actions.assessment import AssessmentError, resolve_assessment
from app.core.intelligence.actions.approval_service import process_approval

from app.agent import loop_config
from app.agent.adapter import resolve_proposal, _resolve_adapter_name
from app.agent.contract import AgentProposal


def preview_proposal(proposal: AgentProposal) -> dict:
    if not loop_config.AGENT_ENABLED:
        return {"decision": "disabled", "detail": "agent surface disabled (RMT_AGENT_ENABLED)"}

    if not proposal.intent.goal or not proposal.intent.target:
        return {"decision": "no_proposal", "detail": "empty goal or target -- nothing to preview"}

    resolution = resolve_proposal(proposal)
    action = resolution.action

    try:
        assessment = resolve_assessment(
            action,
            _resolve_adapter_name(proposal.identity.operational_context),
        )
    except AssessmentError as exc:
        return {"decision": "assessment_failed", "detail": str(exc)}
    policy_result = assessment.policy_result
    simulation_result = assessment.risk_result
    approval_decision = process_approval(action, policy_result, simulation_result)

    return {
        "decision": "preview",
        "action": {
            "component": action.component,
            "action_type": action.action_type.value,
            "reason": action.reason,
            "confidence": action.confidence,
            "requires_approval": action.requires_approval,
            "expected_outcome": (
                action.expected_outcome.model_dump()
                if action.expected_outcome is not None
                else None
            ),
        },
        "authority": {
            "ok": resolution.auth_ok,
            "detail": resolution.auth_reason,
        },
        "escalation": {
            "escalated": resolution.escalate,
            "detail": resolution.esc_reason,
        },
        "predicted": {
            "policy_allowed": policy_result.allowed,
            "policy_reason": policy_result.reason,
            "risk_level": simulation_result.risk_level,
            "approval_mode": approval_decision.mode.value,
            "approval_reason": approval_decision.reason,
        },
    }
