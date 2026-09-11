"""Above-Core Homelab remediation approval-continuation wiring (RMT-CAP-03).

Closes the Learn-stage gap for approval-continuation remediations.

When a Homelab remediation is held for manual approval,
``remediate_and_verify()`` records the *held* state
("manual_approval_required") as a learning record. The subsequent human
continuation goes through the frozen Core ``approve_held_action()``, which
executes and runs Core verification -- but nothing above-Core observes that
executed outcome, so:

  * no Learn/MemoryRecord is written for the executed outcome, and
  * the above-Core Docker verification (observer-fed) never runs.

``continue_remediation()`` wraps the frozen Core ``approve_held_action()``
(calling it unchanged), then, for a held action worth attributing, runs the
existing above-Core verification (resolved for whichever adapter/domain the
hold was actually destined for, not just Docker) and records the executed
outcome through the existing Core learning/memory capability -- correlated to
the run via ``approval_id`` and ``execution_id``.

T1-3: widened the attribution set from the CAP-04 ``REMEDIATION_POLICY``
component (``uptime-kuma``) to any component with a ``ComponentContext``.
Closed the recorded 5B-exercise finding: an agent-proposed remediation for
e.g. ``dozzle`` approved via ``POST /homelab/approve`` now gets the
executed-Learn closure and above-Core verification, not just the held-state
record.

**C3 follow-up (2026-09-11):** widened again to any **agent-originated**
hold (``decision_id`` prefix ``"agent-"``, set only by
``app/agent/adapter.py::propose_and_govern``), closing the gap the CAP-06
(C2) live exercise recorded: a git-domain hold approved through this same
route got no automatic verification because it has no ``ComponentContext``
(git tags aren't homelab components). Also fixed the adapter name used for
verification, previously hardcoded to ``"docker"`` regardless of domain --
now read from ``ApprovalHold.adapter_name`` (the frozen Core's own record of
"the adapter it was destined for"), the same fix already made to the
immediate-execution path in ``app/agent/adapter.py`` for C2. An unresolved
``(adapter_name, operation)`` pair still degrades gracefully to
``observation_unavailable`` (B1a's existing behaviour) rather than erroring.

Guarantees:
  * The frozen Core ``approve_held_action()`` is called, never modified.
  * No new authorization or execution path: this layer only reads the hold
    and records evidence AFTER the Core has executed.
  * Learning stays append-only / read-only: it records; it does not
    authorize or execute.
  * A held action that is neither a recognized homelab component nor an
    agent-originated proposal (e.g. the operator ``POST /execute`` flow) is
    continued by the Core exactly as before, with no extra Learn record and
    no verification -- unchanged from before this fix.
"""
import app.core.intelligence.actions.approval_service as _approval_service
from app.core.intelligence.actions.approval_service import approve_held_action
from app.core.intelligence.context.registry import get_component_context

from app.homelab.remediation import record_learning
from app.ops.verification import verify_executed_action


def continue_remediation(approval_id, approved_by, approved=True):
    """Continue a manually held remediation and close its Learn stage.

    Delegates the governed continuation to the frozen Core
    ``approve_held_action()``. When the continued action is a Homelab
    remediation that executed, runs the above-Core Docker verification and
    records the executed outcome as a learning record.

    Returns the Core outcome dict, augmented with
    ``docker_verification_status`` / ``docker_verification_reason`` when the
    above-Core Docker verification ran.
    """
    # Read-only: capture the held action BEFORE continuation so the component
    # and expected_outcome are retained even after the hold is resolved.
    # Resolve the hold storage through the Core module so runtime/test
    # substitution of that singleton is honoured (same pattern the Core uses).
    hold = _approval_service.approval_hold_storage.get_by_id(approval_id)

    result = approve_held_action(
        approval_id,
        approved_by=approved_by,
        approved=approved,
    )

    # Unknown / already-resolved continuation, or nothing to attribute.
    if hold is None:
        return result

    action = hold.action

    # Above-Core Learn/verify obligation applies to: any component with a
    # ComponentContext (T1-3, homelab), OR any agent-originated proposal
    # (C3 follow-up -- decision_id is only ever "agent-..." from
    # propose_and_govern, regardless of domain). A held action that is
    # neither -- the operator POST /execute -> hold flow -- passes through to
    # the Core continuation untouched: no extra Learn record, no verification.
    is_agent_originated = action.decision_id.startswith("agent-")
    if get_component_context(action.component) is None and not is_agent_originated:
        return result

    # Learn stage applies to a real executed continuation only. A rejected or
    # expired continuation produced no state change; the held-state learning
    # record already captured that the run was held.
    if (
        result.get("status") == "executed"
        and result.get("execution_id")
        and action.expected_outcome is not None
    ):
        # C3 follow-up: verify against the adapter the hold was actually
        # destined for (the frozen Core's own ApprovalHold.adapter_name),
        # not a hardcoded "docker" -- the same fix already made to the
        # immediate-execution path (app/agent/adapter.py, C2). An
        # unresolved (adapter, operation) pair degrades gracefully to
        # observation_unavailable (B1a), never an error.
        verification = verify_executed_action(
            result["execution_id"],
            adapter_name=hold.adapter_name,
            operation=action.action_type.value,
            target=action.component,
            expected=action.expected_outcome,
            action_id=action.action_id,
        )
        result["docker_verification_status"] = verification.status
        result["docker_verification_reason"] = verification.reason

        # Learn: record the executed continuation outcome through the existing
        # Core learning/memory capability (append-only, read-only). Tied to
        # the actual run via approval_id / execution_id.
        record_learning(
            action.component,
            result,
            confidence=action.confidence,
        )

    return result
