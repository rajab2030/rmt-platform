"""RMT-CAP-05 (5A) -- ``propose_and_govern``: route an agent proposal through
the frozen Core's single governed boundary.

Flow:
  1. disabled gate (``AGENT_ENABLED``)
  2. authority check (capability != authority; grant scoped + live)
  3. T13 dependency-cascade escalation (may force ``requires_approval=True``)
  4. translate ``AgentProposal`` -> ``ActionRequest``
  5. ``execute_governed_action(...)`` -- the Core boundary, unchanged
  6. on ``executed``: above-Core Docker verification + Learn record
     on ``manual_approval_required``: Learn record; **never** auto-continued
  7. consume the grant iff the proposal was accepted (executed / held)

No new mutation path. No ``app/core/**`` change. The agent never calls an
adapter directly, never mints authorization, never continues a hold.
"""
import uuid

from app.core.intelligence.actions.models import ActionRequest
from app.core.intelligence.actions.service import execute_governed_action

from app.homelab.remediation import resolve_adapter_name, record_learning
from app.homelab.verification import verify_docker_execution
from app.ops.execution_evidence import record_failed_execution_evidence
from app.ops.notifications import notify_held

from app.agent import loop_config
from app.agent.authority import authority_store
from app.agent.contract import AgentProposal, AgentOutcome
from app.agent.dependency_guard import escalate_for_dependency_cascade


_ACCEPTED = {"executed", "manual_approval_required"}


def _default_requires_approval() -> bool:
    return loop_config.AGENT_DEFAULT_REQUIRES_APPROVAL


def propose_and_govern(proposal: AgentProposal) -> AgentOutcome:
    if not loop_config.AGENT_ENABLED:
        return AgentOutcome(
            proposal=proposal,
            decision="disabled",
            detail="agent surface disabled (RMT_AGENT_ENABLED)",
        )

    operation = proposal.intent.mechanism.value
    target = proposal.intent.target

    ok, why = authority_store.check(proposal.grant_id, operation, target)
    if not ok:
        return AgentOutcome(
            proposal=proposal, decision="no_authority", detail=why
        )

    escalate, esc_reason = escalate_for_dependency_cascade(target, operation)
    requires_approval = escalate or _default_requires_approval()

    action = ActionRequest(
        decision_id=f"agent-{proposal.identity.agent_id}-{uuid.uuid4().hex[:8]}",
        component=target,
        action_type=proposal.intent.mechanism,
        reason=proposal.intent.reason or proposal.intent.goal,
        confidence=proposal.intent.confidence,
        requires_approval=requires_approval,
        expected_outcome=proposal.to_expected_outcome(),
    )

    try:
        result = execute_governed_action(
            action, adapter_name=resolve_adapter_name()
        )
    except Exception as exc:  # defensive: the surface must not 500
        return AgentOutcome(
            proposal=proposal,
            decision="error",
            escalated=escalate,
            detail=repr(exc),
        )

    status = str(result.get("status", "unknown"))
    outcome = AgentOutcome(
        proposal=proposal,
        decision="",
        governed_status=status,
        escalated=escalate,
        detail=esc_reason or result.get("reason", "") or "",
    )

    if status in _ACCEPTED:
        authority_store.consume(proposal.grant_id)

    if status == "manual_approval_required":
        outcome.decision = "escalated_hold" if escalate else "hold"
        outcome.approval_id = result.get("approval_id")
        record_learning(
            target, result, confidence=proposal.intent.confidence
        )
        outcome.learn_recorded = True
        # O2: an agent-proposed action is awaiting human approval.
        notify_held(
            kind="agent_proposal",
            component=target,
            approval_id=result.get("approval_id"),
            detail=esc_reason or result.get("reason", "") or "",
            source="agent_adapter",
        )
        return outcome

    if status == "executed":
        outcome.decision = "allow"
        outcome.execution_id = result.get("execution_id")
        if result.get("success") and action.expected_outcome is not None:
            verification = verify_docker_execution(
                result["execution_id"], action.expected_outcome, target
            )
            result["docker_verification_status"] = verification.status
            result["docker_verification_reason"] = verification.reason
            outcome.verification_status = verification.status
        elif not result.get("success"):
            # E3: adapter invoked and failed -> distinguishable evidence.
            failed = record_failed_execution_evidence(
                result,
                expected=action.expected_outcome,
                source="agent_adapter",
            )
            if failed is not None:
                result["docker_verification_status"] = failed.status
                outcome.verification_status = failed.status
        record_learning(
            target, result, confidence=proposal.intent.confidence
        )
        outcome.learn_recorded = True
        return outcome

    # policy_denied / authorization_not_created / rejected / unknown --
    # rejected before anything happened; grant left intact.
    outcome.decision = (
        "deny"
        if status in ("policy_denied", "authorization_not_created")
        else "rejected"
    )
    return outcome
