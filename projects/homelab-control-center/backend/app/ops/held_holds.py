"""RMT T1-4 -- read-only view of open (PENDING) approval holds.

Above-Core / operational. No ``app/core/**`` change; no write path.

``open_holds_view()`` walks the durable approval **hold** store and, for every
hold still ``PENDING``, reports enough for the external escalation script
(``backend/scripts/rmt-escalate.sh``) to decide whether a human missed it:

  * ``age_seconds`` / ``created_at`` / ``expires_at``
  * ``expired``          -- past the Core ``APPROVAL_HOLD_TTL_SECONDS`` (300 s);
                            such a hold can no longer be continued
  * ``record_decision`` / ``record_terminal`` -- the authoritative approval
                            **record** already resolved it (approved/rejected)
                            even though the hold store still reads ``pending``
                            (the recorded frozen-Core hold-persistence gap)
  * ``actionable``       -- ``not expired and not record_terminal``: a real
                            open decision still waiting on a human
  * ``kind`` / ``granted_by`` / ``agent_id`` -- S3 provenance when the hold was
                            raised by an agent proposal

Escalation policy (an age threshold, a second channel) lives entirely in the
script, matching the D4 / O3 external-check pattern. This function only reads
and classifies; it never raises (``[]`` on any error).
"""
import logging
from datetime import datetime, timezone

import app.core.intelligence.actions.approval_service as _approval_service
from app.core.intelligence.actions.approval import ApprovalStatus
from app.ops.separation import get_hold_provenance

logger = logging.getLogger("rmt.ops.holds")

_TERMINAL_DECISIONS = {"approved", "rejected"}


def _aware(dt):
    if dt is None:
        return None
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt


def _iso(dt):
    return dt.isoformat() if dt is not None else None


def open_holds_view() -> list[dict]:
    """Classified snapshot of every PENDING approval hold. Never raises."""
    try:
        holds = _approval_service.approval_hold_storage.get_all()
    except Exception as exc:  # fail-open -- read-only view, never 500
        logger.warning("open_holds_view: hold store read failed: %r", exc)
        return []

    now = datetime.now(timezone.utc)
    out: list[dict] = []

    for hold in holds:
        try:
            if getattr(hold, "status", None) != ApprovalStatus.PENDING:
                continue

            created = _aware(getattr(hold, "created_at", None))
            expires = _aware(getattr(hold, "expires_at", None))

            record = None
            try:
                record = _approval_service.approval_record_storage.get_by_id(
                    hold.approval_id
                )
            except Exception:  # noqa: BLE001 -- record store is advisory here
                record = None
            decision = getattr(record, "decision", None) if record else None
            record_terminal = decision in _TERMINAL_DECISIONS

            expired = expires is not None and now > expires
            actionable = not expired and not record_terminal

            action = getattr(hold, "action", None)
            prov = get_hold_provenance(hold.approval_id)

            out.append(
                {
                    "approval_id": hold.approval_id,
                    "component": getattr(action, "component", None),
                    "action_type": getattr(
                        getattr(action, "action_type", None), "value", None
                    ),
                    "created_at": _iso(created),
                    "expires_at": _iso(expires),
                    "age_seconds": (
                        (now - created).total_seconds()
                        if created is not None
                        else None
                    ),
                    "expired": expired,
                    "record_decision": decision,
                    "record_terminal": record_terminal,
                    "actionable": actionable,
                    "kind": "agent_proposal" if prov else "held_action",
                    "granted_by": getattr(prov, "granted_by", None),
                    "agent_id": getattr(prov, "agent_id", None),
                }
            )
        except Exception as exc:  # one bad hold must not sink the view
            logger.warning("open_holds_view: skipping a hold: %r", exc)

    return out
