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
import logging
import uuid

from app.core.intelligence.actions.models import ActionRequest
from app.core.intelligence.actions.service import execute_governed_action

from app.homelab.remediation import resolve_adapter_name, record_learning
from app.ops.verification import verify_executed_action
from app.ops.execution_evidence import record_failed_execution_evidence
from app.ops.logging_config import log_event
from app.ops.notifications import notify_held
from app.ops.separation import record_hold_provenance

from app.agent import loop_config
from app.agent.authority import authority_store
from app.agent.contract import AgentProposal, AgentOutcome
from app.agent.dependency_guard import escalate_for_dependency_cascade

logger = logging.getLogger("rmt.agent")

_ACCEPTED = {"executed", "manual_approval_required"}


def _log_outcome(outcome: AgentOutcome, *, operation: str, target: str) -> AgentOutcome:
    """O1: one structured line per agent proposal that reached the adapter."""
    log_event(
        logger,
        "agent_proposal_outcome",
        agent_id=outcome.proposal.identity.agent_id,
        operation=operation,
        target=target,
        decision=outcome.decision or None,
        governed_status=outcome.governed_status or None,
        approval_id=outcome.approval_id,
        execution_id=outcome.execution_id,
        escalated=outcome.escalated or None,
        verification_status=outcome.verification_status,
    )
    return outcome


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
        return _log_outcome(
            AgentOutcome(
                proposal=proposal, decision="no_authority", detail=why
            ),
            operation=operation,
            target=target,
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
        return _log_outcome(
            AgentOutcome(
                proposal=proposal,
                decision="error",
                escalated=escalate,
                detail=repr(exc),
            ),
            operation=operation,
            target=target,
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
        # S3: remember who is behind this agent-raised hold so the approver
        # can be required to differ from the grantor / proposer.
        _grant = authority_store.get(proposal.grant_id)
        record_hold_provenance(
            outcome.approval_id,
            grant_id=proposal.grant_id,
            granted_by=_grant.granted_by if _grant else None,
            agent_id=proposal.identity.agent_id,
        )
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
        return _log_outcome(outcome, operation=operation, target=target)

    if status == "executed":
        outcome.decision = "allow"
        outcome.execution_id = result.get("execution_id")
        if result.get("success") and action.expected_outcome is not None:
            verification = verify_executed_action(
                result["execution_id"],
                adapter_name="docker",
                operation=operation,
                target=target,
                expected=action.expected_outcome,
                action_id=action.action_id,
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
        return _log_outcome(outcome, operation=operation, target=target)

    # policy_denied / authorization_not_created / rejected / unknown --
    # rejected before anything happened; grant left intact.
    outcome.decision = (
        "deny"
        if status in ("policy_denied", "authorization_not_created")
        else "rejected"
    )
    return _log_outcome(outcome, operation=operation, target=target)
