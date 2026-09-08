"""RMT-PROD P0 (E2) -- startup reconciliation of the approval hold store.

Above-Core / operational. No ``app/core/**`` change.

**The gap (E2, recorded frozen-Core note).**
``approve_held_action`` flips ``hold.status`` on the in-memory ``ApprovalHold``
but persists only the approval **record** store, never the **hold** store. After
a process restart a hold that was approved / rejected days ago reloads from
``approval_holds.json`` as ``pending``. The approval **record** store *is*
reliably updated on resolution, so a terminal record decision
(``approved`` / ``rejected``) is authoritative.

CAP-04's operational loop already compensates read-side
(``_hold_is_still_actionable``): it cross-checks the record store before letting
a stale ``pending`` hold block a new remediation. This module closes the same
gap write-side, once, at startup: it brings the hold store back into agreement
with the authoritative record store so a restart is faithful and any other
consumer of the hold store sees the true state.

**Strictly bounded.**
  * Read the hold store and, per hold, the matching record. Correct a hold
    only when an authoritative *terminal record* contradicts a ``pending``
    hold. Nothing else is touched.
  * A hold with no record, or a still-``pending`` record, is left exactly as
    is -- reconciliation never *invents* a resolution (e.g. it does not
    reject merely-expired holds; that stays a read-side / Core concern).
  * Fail-open: any error is logged and swallowed; reconciliation must never
    stop the app from starting.

This also covers the hold<->record half of E6 (startup integrity check).
"""
import logging

import app.core.intelligence.actions.approval_service as _approval_service
from app.core.intelligence.actions.approval import ApprovalStatus

logger = logging.getLogger("rmt.ops.reconcile")

_TERMINAL_DECISIONS = {"approved", "rejected"}

_DECISION_TO_STATUS = {
    "approved": ApprovalStatus.APPROVED,
    "rejected": ApprovalStatus.REJECTED,
}


def reconcile_holds_against_records() -> dict:
    """Bring ``approval_hold_storage`` into agreement with the authoritative
    ``approval_record_storage``. Returns a summary dict
    ``{"checked": int, "reconciled": int, "ids": [approval_id, ...]}``.

    Never raises.
    """
    summary = {"checked": 0, "reconciled": 0, "ids": []}
    try:
        hold_storage = _approval_service.approval_hold_storage
        record_storage = _approval_service.approval_record_storage

        holds = hold_storage.get_all()
        summary["checked"] = len(holds)

        for hold in holds:
            if getattr(hold, "status", None) != ApprovalStatus.PENDING:
                continue

            record = record_storage.get_by_id(hold.approval_id)
            decision = getattr(record, "decision", None) if record else None
            if decision not in _TERMINAL_DECISIONS:
                continue

            true_status = _DECISION_TO_STATUS[decision]
            hold.status = true_status
            if getattr(hold, "approved_by", None) is None:
                hold.approved_by = getattr(record, "approved_by", None)

            summary["reconciled"] += 1
            summary["ids"].append(hold.approval_id)
            logger.info(
                "E2 reconcile: hold %s pending on disk but record says %s -- "
                "corrected to %s",
                hold.approval_id,
                decision,
                true_status.value,
            )

        if summary["reconciled"]:
            # Persist the corrected in-memory records through the store's own
            # (atomic, E1) write path. The hold store exposes no public
            # update(); this is the same mechanism ApprovalRecordStorage.update
            # uses, invoked here on the shared in-process singleton.
            hold_storage._persist()
            logger.warning(
                "E2 reconcile: corrected %d stale approval hold(s) on startup: "
                "%s",
                summary["reconciled"],
                ", ".join(summary["ids"]),
            )
        else:
            logger.debug(
                "E2 reconcile: %d hold(s) checked, none stale", summary["checked"]
            )
    except Exception as exc:  # fail-open -- never block startup
        logger.warning("E2 reconcile skipped (non-fatal): %r", exc)

    return summary
