"""RMT-PROD P0 (E2 + E6) -- startup reconciliation / audit of the governance
evidence stores.

Above-Core / operational. No ``app/core/**`` change.

--------------------------------------------------------------------------------
E2 -- hold store correction (``reconcile_holds_against_records``)
--------------------------------------------------------------------------------
``approve_held_action`` flips ``hold.status`` on the in-memory ``ApprovalHold``
but persists only the approval **record** store, never the **hold** store. After
a process restart a hold that was approved / rejected days ago reloads from
``approval_holds.json`` as ``pending``. The approval **record** store *is*
reliably updated on resolution, so a terminal record decision
(``approved`` / ``rejected``) is authoritative.

CAP-04's operational loop already compensates read-side
(``_hold_is_still_actionable``). This module closes the same gap write-side,
once, at startup: it brings the hold store back into agreement with the
authoritative record store so a restart is faithful and any other consumer of
the hold store sees the true state.

**Strictly bounded.** Correct a ``pending`` hold only when an authoritative
*terminal record* contradicts it. A hold with no record, or a still-``pending``
record, is left exactly as is -- it never *invents* a resolution (e.g. it does
not reject merely-expired holds). Fail-open: any error is logged and swallowed.

--------------------------------------------------------------------------------
E6 -- authorization store integrity audit (``audit_authorizations``)
--------------------------------------------------------------------------------
The execution-authorization store is Core-owned and effectively append-only: an
``ExecutionAuthorization`` is created already in its final ``approved`` status
and the Core never mutates it afterwards (the execution engine only *reads* it
to gate the boundary). There is therefore no authoritative "true status" to
reconcile an authorization *to* -- so this half only **audits**. It walks the
authorization store and logs any record whose approval linkage is inconsistent
with the approval record / hold stores:

  * ``missing_record``        -- authorization references an approval id with no
                                approval record (orphan).
  * ``contradicts_rejection`` -- authorization exists but its approval record is
                                ``rejected`` (should be impossible: rejection
                                mints no authorization).
  * ``record_not_terminal``   -- authorization exists but its approval was never
                                finally decided (record ``pending`` /
                                ``manual_required``).
  * ``hold_still_pending``    -- the linked hold is still ``pending`` after the
                                E2 correction above ran.

It never writes -- deleting or rewriting Core evidence is out of scope; the
value is surfacing the divergence in the log so an operator can investigate.

``reconcile_governance_stores`` runs the E2 correction first, then the E6 audit
against the now-corrected holds. This is what ``app/main.py`` calls on startup.
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
    ``approval_record_storage`` (E2). Returns a summary dict
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
            approval_id = hold.approval_id

            fields = {"status": true_status}
            if getattr(hold, "approved_by", None) is None:
                fields["approved_by"] = getattr(record, "approved_by", None)

            # Persist just this correction through the store's own public
            # update() -- one SQLite UPDATE (T0-1), or an atomic JSON rewrite.
            hold_storage.update(approval_id, **fields)

            summary["reconciled"] += 1
            summary["ids"].append(approval_id)
            logger.info(
                "E2 reconcile: hold %s pending on disk but record says %s -- "
                "corrected to %s",
                approval_id,
                decision,
                true_status.value,
            )

        if summary["reconciled"]:
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


def audit_authorizations() -> dict:
    """Read-only startup integrity audit (E6) of ``execution_authorization_storage``
    against the approval record + hold stores.

    The authorization store is Core-owned and append-only, so this only *flags*
    inconsistent approval linkage -- it never writes. Returns
    ``{"checked": int, "divergences": int, "details": [ {...} ]}``.

    Never raises.
    """
    summary = {"checked": 0, "divergences": 0, "details": []}
    try:
        authz_storage = _approval_service.execution_authorization_storage
        record_storage = _approval_service.approval_record_storage
        hold_storage = _approval_service.approval_hold_storage

        authorizations = authz_storage.get_all()
        summary["checked"] = len(authorizations)

        for authz in authorizations:
            approval_id = getattr(authz, "approval_id", None)
            if not approval_id:
                # Not every authorization is approval-linked; nothing to check.
                continue

            record = record_storage.get_by_id(approval_id)
            decision = getattr(record, "decision", None) if record else None

            issue = None
            if record is None:
                issue = "missing_record"
            elif decision == "rejected":
                issue = "contradicts_rejection"
            elif decision not in _TERMINAL_DECISIONS:
                issue = "record_not_terminal"

            if issue is None:
                hold = hold_storage.get_by_id(approval_id)
                if (
                    hold is not None
                    and getattr(hold, "status", None) == ApprovalStatus.PENDING
                ):
                    issue = "hold_still_pending"

            if issue is None:
                continue

            detail = {
                "authorization_id": getattr(authz, "authorization_id", None),
                "approval_id": approval_id,
                "authorization_type": getattr(authz, "authorization_type", None),
                "issue": issue,
                "record_decision": decision,
            }
            summary["divergences"] += 1
            summary["details"].append(detail)
            logger.warning(
                "E6 authorization audit: authorization %s (approval %s, %s) -- "
                "%s (record decision=%r)",
                detail["authorization_id"],
                approval_id,
                detail["authorization_type"],
                issue,
                decision,
            )

        if summary["divergences"]:
            logger.warning(
                "E6 authorization audit: %d authorization(s) inconsistent with "
                "the approval record/hold stores (read-only; not modified): %s",
                summary["divergences"],
                ", ".join(
                    str(d["authorization_id"]) for d in summary["details"]
                ),
            )
        else:
            logger.debug(
                "E6 authorization audit: %d authorization(s) checked, all "
                "consistent",
                summary["checked"],
            )
    except Exception as exc:  # fail-open -- never block startup
        logger.warning(
            "E6 authorization audit skipped (non-fatal): %r", exc
        )

    return summary


def reconcile_governance_stores() -> dict:
    """Full startup governance-store reconciliation + audit (E2 + E6).

    Order matters: correct the hold store against the record store first (E2),
    then audit the authorization store against the now-corrected holds +
    records (E6). Returns ``{"holds": {...}, "authorizations": {...}}``.

    Never raises.
    """
    holds = reconcile_holds_against_records()
    authorizations = audit_authorizations()
    return {"holds": holds, "authorizations": authorizations}
