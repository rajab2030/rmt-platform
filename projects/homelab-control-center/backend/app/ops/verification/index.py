"""B1b — effective-status index over post-execution verification evidence.

A read-only, in-memory projection keyed by ``execution_id``. It collapses the
two uncorrelated records B1a can leave for one execution (the frozen Core's
``observation_unavailable`` + the above-Core record) into one **effective
status**, and marks the Core record superseded where an above-Core assertion
exists.

Rebuilt from ``verification_storage`` + the execution audit store on startup
(**silent** — fires no notification, and marks every row it creates
``notified_inconclusive`` so history never re-alerts). Updated per call by
``verify_executed_action``.

**Not persisted.** Like ``app/ops/separation.py`` and ``app/agent/authority.py``
the state is short-lived by design: a restart rebuilds it. A durable SQLite
table is the recorded B1b non-goal (``docs/RMT_B1b_RECON.md`` RB-3).

``effective_status`` precedence (``docs/RMT_B1_PROPOSAL.md`` §2.3):
  1. an ``adapter_execution_failed`` record exists → ``adapter_execution_failed``
     (deferred to E3; ``verified`` False; **not** counted as ``unverified``);
  2. an above-Core record exists → its status;
  3. no above-Core record, adapter is ``module_change`` → the Core status
     (real there per R1);
  4. otherwise → ``unverified``.
"""
from __future__ import annotations

import logging
import re
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.core.intelligence.verification.models import VerificationStatus
from app.core.intelligence.verification import storage as _verification_storage_module
from app.core.intelligence.execution import storage as _audit_storage_module
from app.ops.execution_evidence import ADAPTER_EXECUTION_FAILED

logger = logging.getLogger("rmt.ops.verification.index")

# B1a writes this token as the prefix of an above-Core record's reason.
_ABOVE_CORE_RE = re.compile(r"^\[layer=above_core adapter=(?P<adapter>[^\s\]]+)")
_ABOVE_CORE_PREFIX = "[layer=above_core"

UNVERIFIED = "unverified"
MODULE_CHANGE_ADAPTER = "module_change"

_CORE_STATUSES = {
    VerificationStatus.VERIFIED_SUCCESS,
    VerificationStatus.STATE_MISMATCH,
    VerificationStatus.OBSERVATION_UNAVAILABLE,
    VerificationStatus.VERIFICATION_FAILURE,
}


@dataclass
class IndexRow:
    execution_id: str
    action_id: str | None = None
    adapter: str | None = None
    operation: str | None = None
    target: str | None = None
    core_status: str | None = None
    above_core_status: str | None = None
    effective_status: str = UNVERIFIED
    verified: bool = False
    notified_inconclusive: bool = False
    updated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def as_dict(self) -> dict:
        return {
            "execution_id": self.execution_id,
            "action_id": self.action_id,
            "adapter": self.adapter,
            "operation": self.operation,
            "target": self.target,
            "core_status": self.core_status,
            "above_core_status": self.above_core_status,
            "effective_status": self.effective_status,
            "verified": self.verified,
            "notified_inconclusive": self.notified_inconclusive,
            "updated_at": self.updated_at,
        }


_rows: dict[str, IndexRow] = {}
_lock = threading.Lock()


def _classify(core_status, above_core_status, adapter, has_adapter_failure):
    """Return ``(effective_status, verified)`` per the §2.3 precedence."""
    if has_adapter_failure:
        return ADAPTER_EXECUTION_FAILED, False
    if above_core_status is not None:
        return above_core_status, above_core_status == VerificationStatus.VERIFIED_SUCCESS
    if adapter == MODULE_CHANGE_ADAPTER and core_status is not None:
        return core_status, core_status == VerificationStatus.VERIFIED_SUCCESS
    return UNVERIFIED, False


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def record(
    execution_id: str,
    *,
    action_id: str | None,
    adapter: str | None,
    operation: str | None,
    target: str | None,
    core_status: str | None,
    above_core_status: str | None,
    has_adapter_failure: bool = False,
) -> IndexRow:
    """Upsert one row from the live ``verify_executed_action`` path. Preserves an
    existing row's ``notified_inconclusive`` flag."""
    with _lock:
        row = _rows.get(execution_id) or IndexRow(execution_id=execution_id)
        row.action_id = action_id or row.action_id
        row.adapter = adapter or row.adapter
        row.operation = operation or row.operation
        row.target = target or row.target
        if core_status is not None:
            row.core_status = core_status
        if above_core_status is not None:
            row.above_core_status = above_core_status
        row.effective_status, row.verified = _classify(
            row.core_status, row.above_core_status, row.adapter, has_adapter_failure
        )
        row.updated_at = _now()
        _rows[execution_id] = row
        return row


def mark_notified(execution_id: str) -> None:
    with _lock:
        row = _rows.get(execution_id)
        if row is not None:
            row.notified_inconclusive = True


def get(execution_id: str) -> IndexRow | None:
    return _rows.get(execution_id)


def view(limit: int = 50, effective_status: str | None = None) -> list[dict]:
    """Newest-first index rows, optionally filtered by ``effective_status``,
    capped at ``limit``. Never raises (``[]`` on error)."""
    try:
        rows = sorted(_rows.values(), key=lambda r: r.updated_at, reverse=True)
        if effective_status:
            rows = [r for r in rows if r.effective_status == effective_status]
        if limit and limit > 0:
            rows = rows[:limit]
        return [r.as_dict() for r in rows]
    except Exception as exc:  # read-only view -- never 500
        logger.warning("verification index view failed: %r", exc)
        return []


def snapshot() -> list[IndexRow]:
    return list(_rows.values())


def reset() -> None:
    """Test hook."""
    with _lock:
        _rows.clear()


def rebuild() -> dict:
    """Rebuild the index from the durable verification store + the execution
    audit store. **Silent**: marks every row it creates ``notified_inconclusive``
    so the first live pass never alerts on history. Never raises."""
    summary = {"rows": 0, "unverified": 0}
    try:
        records = _verification_storage_module.verification_storage.get_all()
    except Exception as exc:
        logger.warning(
            "verification index rebuild skipped (verification store): %r", exc
        )
        return summary

    audit_by_exec: dict[str, tuple] = {}
    try:
        for a in _audit_storage_module.execution_audit_storage.get_all():
            audit_by_exec.setdefault(
                a.execution_id,
                (getattr(a, "action_id", None), getattr(a, "adapter", None)),
            )
    except Exception as exc:
        logger.warning(
            "verification index rebuild: audit store read failed: %r", exc
        )

    grouped: dict[str, list] = {}
    for r in records:
        grouped.setdefault(r.execution_id, []).append(r)

    new_rows: dict[str, IndexRow] = {}
    for execution_id, group in grouped.items():
        core_status = above_core_status = adapter = operation = target = None
        has_adapter_failure = False

        for r in group:
            reason = r.reason or ""
            m = _ABOVE_CORE_RE.match(reason)
            if m:
                above_core_status = r.status
                adapter = adapter or m.group("adapter")
                if r.expected is not None:
                    operation = operation or (r.expected.operation or None)
                    target = target or (r.expected.target or None)
            elif r.status == ADAPTER_EXECUTION_FAILED:
                has_adapter_failure = True
            elif r.status in _CORE_STATUSES:
                core_status = r.status
                if r.expected is not None:
                    operation = operation or (r.expected.operation or None)
                    target = target or (r.expected.target or None)

        audit_action_id, audit_adapter = audit_by_exec.get(execution_id, (None, None))
        adapter = adapter or audit_adapter

        effective_status, verified = _classify(
            core_status, above_core_status, adapter, has_adapter_failure
        )
        new_rows[execution_id] = IndexRow(
            execution_id=execution_id,
            action_id=audit_action_id,
            adapter=adapter,
            operation=operation,
            target=target,
            core_status=core_status,
            above_core_status=above_core_status,
            effective_status=effective_status,
            verified=verified,
            notified_inconclusive=True,  # silent -- never re-alert on history
        )
        if effective_status == UNVERIFIED:
            summary["unverified"] += 1

    with _lock:
        _rows.clear()
        _rows.update(new_rows)

    summary["rows"] = len(new_rows)
    logger.info(
        "verification index rebuilt: %d row(s), %d unverified",
        summary["rows"],
        summary["unverified"],
    )
    return summary
