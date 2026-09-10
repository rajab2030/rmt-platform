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
(calling it unchanged), then, for a held action whose component carries a
``ComponentContext``, runs the existing above-Core Docker verification and
records the executed outcome through the existing Core learning/memory
capability -- correlated to the run via ``approval_id`` and ``execution_id``.

T1-3: the attribution set is any component with a ``ComponentContext``
(``app/core/intelligence/context/registry.py``), not only the CAP-04
``REMEDIATION_POLICY`` component (``uptime-kuma``). This closes the recorded
5B-exercise finding: an agent-proposed remediation for e.g. ``dozzle``
approved via ``POST /homelab/approve`` now gets the executed-Learn closure and
the above-Core Docker verification, not just the held-state record.

Guarantees:
  * The frozen Core ``approve_held_action()`` is called, never modified.
  * No new authorization or execution path: this layer only reads the hold
    and records evidence AFTER the Core has executed.
  * Learning stays append-only / read-only: it records; it does not
    authorize or execute.
  * A held action whose component has no ``ComponentContext`` (e.g. the
    operator ``POST /execute`` flow) is continued by the Core exactly as
    before, with no extra Learn record and no Docker verification.
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

    # Any component with a ComponentContext carries an above-Core Learn/verify
    # obligation (T1-3, widened from the CAP-04 REMEDIATION_POLICY set). A held
    # action whose component has no ComponentContext -- the operator
    # POST /execute -> hold flow -- passes through to the Core continuation
    # untouched: no extra Learn record, no Docker verification.
    if get_component_context(action.component) is None:
        return result

    # Learn stage applies to a real executed continuation only. A rejected or
    # expired continuation produced no state change; the held-state learning
    # record already captured that the run was held.
    if (
        result.get("status") == "executed"
        and result.get("execution_id")
        and action.expected_outcome is not None
    ):
        verification = verify_executed_action(
            result["execution_id"],
            adapter_name="docker",
            operation=action.action_type.value,
            target=action.component,
            expected=action.expected_outcome,
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
