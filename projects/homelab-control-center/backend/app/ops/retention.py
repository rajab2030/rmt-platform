"""RMT-PROD P1 (E4) -- evidence-store retention / archival.

Above-Core / operational. No ``app/core/**`` change.

The six governance-evidence JSON stores grow unbounded and ``DurableStore``
rewrites the whole file on every save (O(n)). E4 bounds the live files: on
startup, every record older than ``RMT_EVIDENCE_RETENTION_DAYS`` is moved out of
the live store into an append-only archive file beside it, and the trimmed store
is re-persisted through its own atomic (E1) write path.

**Archived evidence is not deleted.** It goes to ``<name>.archive.jsonl`` (one
JSON object per line, append-only) next to the live store -- which is what E5's
backup engine captures for long-term retention. A full history is
``cat <name>.archive.jsonl`` + the live ``<name>.json``.

**Strictly bounded.**
  * Only records whose ``created_at`` parses and is strictly older than the
    cutoff are moved. No / blank / unparseable ``created_at`` -> kept (never
    archived on a guess).
  * Runs AFTER ``reconcile_governance_stores()`` so a stale hold is corrected
    before it can be archived.
  * Fail-open per store and overall -- an error on one store is logged and
    skipped; the app always starts.
  * Idempotent -- a run with nothing older than the cutoff writes nothing.
  * ``RMT_EVIDENCE_RETENTION_DAYS <= 0`` disables archival entirely.

Default window 90 days: long enough that an operator or auditor working a
recent incident still finds everything in the live store; the archive holds the
rest.
"""
import json
import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.ops import ops_config

logger = logging.getLogger("rmt.ops.retention")


def _default_stores():
    """The six live evidence-store singletons as ``(name, storage)`` pairs.

    Approval stores are resolved through the ``approval_service`` module so
    runtime / test substitution of those singletons is honoured (same pattern
    as ``app/ops/reconcile.py``)."""
    import app.core.intelligence.actions.approval_service as _asvc
    from app.core.intelligence.execution.trace_storage import (
        execution_trace_storage,
    )
    from app.core.intelligence.execution.storage import execution_audit_storage
    from app.core.intelligence.verification.storage import verification_storage
    from app.core.intelligence.actions.authorization_storage import (
        execution_authorization_storage,
    )

    return [
        ("traces", execution_trace_storage),
        ("audit", execution_audit_storage),
        ("verifications", verification_storage),
        ("authorizations", execution_authorization_storage),
        ("approval_records", _asvc.approval_record_storage),
        ("approval_holds", _asvc.approval_hold_storage),
    ]


def _archive_path(store) -> Path:
    p = store._file_path
    return p.with_name(p.stem + ".archive.jsonl")


def _older_than(created_at, cutoff: datetime) -> bool:
    if created_at is None:
        return False
    if isinstance(created_at, str):
        try:
            created_at = datetime.fromisoformat(
                created_at.replace("Z", "+00:00")
            )
        except ValueError:
            return False
    if not isinstance(created_at, datetime):
        return False
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    return created_at < cutoff


def archive_store(name: str, store, cutoff: datetime) -> dict:
    """Move records older than ``cutoff`` from ``store`` into its
    ``.archive.jsonl``. Returns ``{"store", "archived", "kept"}``. Never raises.
    """
    try:
        if getattr(store, "_file_path", None) is None:
            return {"store": name, "archived": 0, "kept": 0, "skipped": "in_memory"}

        keep, archive = [], []
        for r in store.get_all():
            (archive if _older_than(getattr(r, "created_at", None), cutoff)
             else keep).append(r)

        if not archive:
            return {"store": name, "archived": 0, "kept": len(keep)}

        archive_path = _archive_path(store)
        with open(archive_path, "a") as f:
            for r in archive:
                f.write(json.dumps(r.model_dump(mode="json")) + "\n")
            f.flush()
            os.fsync(f.fileno())

        store._records = keep
        store._persist()  # atomic (E1) write path

        logger.warning(
            "E4 retention: archived %d record(s) from %s (kept %d) -> %s",
            len(archive), name, len(keep), archive_path.name,
        )
        return {"store": name, "archived": len(archive), "kept": len(keep)}
    except Exception as exc:  # fail-open per store
        logger.warning("E4 retention: %s skipped (non-fatal): %r", name, exc)
        return {"store": name, "archived": 0, "kept": -1, "error": repr(exc)}


def archive_aged_evidence(retention_days: int | None = None, stores=None) -> dict:
    """Archive every evidence record older than the retention window. Returns a
    summary dict. Never raises."""
    try:
        days = (
            retention_days
            if retention_days is not None
            else ops_config.evidence_retention_days()
        )
        if days <= 0:
            logger.debug("E4 retention: disabled (RMT_EVIDENCE_RETENTION_DAYS<=0)")
            return {"retention_days": days, "disabled": True, "archived_total": 0}

        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        pairs = stores if stores is not None else _default_stores()
        results = [archive_store(n, s, cutoff) for n, s in pairs]
        total = sum(r["archived"] for r in results)

        if total:
            logger.warning(
                "E4 retention: archived %d aged evidence record(s) across %d "
                "store(s) (older than %d days)",
                total,
                sum(1 for r in results if r["archived"]),
                days,
            )
        else:
            logger.debug(
                "E4 retention: %d store(s) checked, nothing older than %d days",
                len(results), days,
            )
        return {
            "retention_days": days,
            "cutoff": cutoff.isoformat(),
            "archived_total": total,
            "stores": results,
        }
    except Exception as exc:  # fail-open overall
        logger.warning("E4 retention skipped (non-fatal): %r", exc)
        return {"archived_total": 0, "error": repr(exc)}
