"""RMT-PROD P1 (E3) -- distinguishable evidence for a failed adapter execution.

Above-Core / operational. No ``app/core/**`` change.

**The gap.** ``AGENTS.md`` §11 requires these post-execution outcomes to be
*distinguishable in evidence*:

    blocked before execution | adapter invoked and failed | successful execution
    | verification failure | unknown or unavailable state

The Core covers four of the five. But when a governed execution reaches the
adapter and the adapter returns ``success=False``, the Core writes an **audit**
record and a **trace** record (both ``status="failed"``) and then *skips*
verification -- every caller gates ``verify_execution`` /
``verify_docker_execution`` on ``result.success``. So "adapter invoked and
failed" leaves **no verification record at all**, and it cannot be told apart
from "verification never ran" by looking at the verification store.
``verification_failure`` is not a substitute: it already means "the verifier
itself failed".

**The fix (this module).** For a governed outcome that *is* a real execution
attempt that did not succeed, write one ``VerificationResult`` into the existing
verification store with a distinct status string, correlated by
``execution_id``. Same store, same model, same boundary that
``app/homelab/verification.py`` already writes above-Core records to -- this
just adds the missing negative case.

**Strictly bounded.**
  * Fires only when ``outcome`` reached the execution engine and failed:
    ``status == "executed"`` and ``success is False`` and an ``execution_id``
    is present. Everything else -- ``manual_approval_required``,
    ``policy_denied``, ``no_authority``, ``authorization_not_created``,
    ``rejected``, ``no_remediation``, ``unsupported_operation``, ``error`` --
    is "blocked before execution", already distinguishable by its own status,
    and is left untouched.
  * Idempotent: if the verification store already has a record for the
    ``execution_id`` (e.g. an above-Core Docker verify already wrote
    ``state_mismatch`` / ``observation_unavailable`` for the same failed run),
    do nothing.
  * Fail-open: any error is logged and swallowed; recording evidence must
    never turn a handled execution failure into an unhandled one.
"""
import logging

from app.core.intelligence.verification.models import VerificationResult
from app.core.intelligence.verification.storage import verification_storage

logger = logging.getLogger("rmt.ops.execution_evidence")

# Distinct from the frozen ``VerificationStatus`` values
# (verified_success / state_mismatch / observation_unavailable /
# verification_failure). This is the §11 "adapter invoked and failed" case.
ADAPTER_EXECUTION_FAILED = "adapter_execution_failed"


def _is_failed_execution_attempt(outcome: dict) -> bool:
    return (
        isinstance(outcome, dict)
        and outcome.get("status") == "executed"
        and outcome.get("success") is False
        and bool(outcome.get("execution_id"))
    )


def record_failed_execution_evidence(
    outcome: dict,
    *,
    expected=None,
    source: str,
) -> VerificationResult | None:
    """Write a distinguishable verification record for an adapter that was
    invoked and failed (E3). Returns the record written, or ``None`` when
    nothing applied / was already recorded. Never raises.

    ``outcome`` is the governed-outcome dict returned by
    ``execute_governed_action`` / ``approve_held_action`` /
    ``continue_remediation`` / the agent adapter. ``expected`` is the
    ``ExpectedOutcome`` when the caller has it (``/execute``, agent), else
    ``None``. ``source`` is a short tag for the log line.
    """
    try:
        if not _is_failed_execution_attempt(outcome):
            return None

        execution_id = outcome["execution_id"]

        if verification_storage.get_by_execution_id(execution_id) is not None:
            # A verification record already exists for this run (an above-Core
            # observer got there first). Nothing to add.
            return None

        record = VerificationResult(
            execution_id=execution_id,
            status=ADAPTER_EXECUTION_FAILED,
            expected=expected,
            observed=None,
            reason=(
                outcome.get("message")
                or outcome.get("status_detail")
                or "Adapter invoked and returned failure"
            ),
        )
        verification_storage.save(record)
        logger.warning(
            "E3: adapter execution failed with no verification record "
            "(source=%s, execution_id=%s) -- recorded status=%s: %s",
            source,
            execution_id,
            ADAPTER_EXECUTION_FAILED,
            record.reason,
        )
        return record
    except Exception as exc:  # fail-open
        logger.warning(
            "E3 execution-evidence recording skipped (non-fatal): %r", exc
        )
        return None
