"""RMT-CAP-09 -- read-only evidence-chain correlation for the governed console.

Above-Core / product surface (roadmap P-B). No ``app/core/**`` change; no write
path; not on the governed mutation path.

``evidence_chain()`` resolves a single identifier (``action_id`` / ``approval_id``
/ ``execution_id``) against the shared durable evidence stores and returns the
full **Govern -> Verify** chain for that action: authorization -> approval
record (decision) -> hold (if held) -> execution audit -> decision trace ->
verification, plus S3 provenance where present.

Discipline mirrors ``held_holds.py`` / ``ops/verifications``: strictly read-only
and **fail-open end-to-end** -- any store read error *or* any assembly error
degrades to an empty/partial chain, never a 500.
"""
import logging

from app.core.intelligence.actions.approval_storage import (
    approval_hold_storage,
    approval_record_storage,
)
from app.core.intelligence.actions.authorization_storage import (
    execution_authorization_storage,
)
from app.core.intelligence.execution.storage import execution_audit_storage
from app.core.intelligence.execution.trace_storage import execution_trace_storage
from app.core.intelligence.verification.storage import verification_storage
from app.ops.separation import get_hold_provenance

logger = logging.getLogger("rmt.ops.evidence")


def _empty_shape(action_id, approval_id, execution_id):
    return {
        "resolved": {
            "action_id": action_id,
            "approval_id": approval_id,
            "execution_id": execution_id,
        },
        "authorizations": [],
        "approvals": [],
        "holds": [],
        "audit": [],
        "traces": [],
        "verifications": [],
        "provenance": {},
    }


def _dump(rec):
    """Serialise a Pydantic record to a JSON-serialisable dict; safe on None."""
    if rec is None:
        return None
    dump = getattr(rec, "model_dump", None)
    if dump is not None:
        try:
            return dump(mode="json")
        except Exception:  # noqa: BLE001 -- best effort
            return {k: str(v) for k, v in rec.__dict__.items()}
    # dataclass / plain object fallback
    try:
        return {k: str(v) for k, v in rec.__dict__.items()}
    except Exception:  # noqa: BLE001
        return str(rec)


def _safe(fn, section):
    """Run a store read; any error -> [] and a log line (fail-open)."""
    try:
        return list(fn())
    except Exception as exc:  # noqa: BLE001 -- read-only view, never 500
        logger.warning("evidence_chain: %s read failed: %r", section, exc)
        return []


def _matches(rec, action_id, approval_id, execution_id):
    if action_id and getattr(rec, "action_id", None) == action_id:
        return True
    if approval_id and getattr(rec, "approval_id", None) == approval_id:
        return True
    if execution_id and getattr(rec, "execution_id", None) == execution_id:
        return True
    return False


def _assemble(action_id, approval_id, execution_id):
    """Correlate across the durable stores. Callers guarantee try/except."""
    # Pull everything first (fail-open per store).
    authz = _safe(lambda: execution_authorization_storage.get_all(), "authorizations")
    records = _safe(lambda: approval_record_storage.get_all(), "approval_records")
    holds = _safe(lambda: approval_hold_storage.get_all(), "approval_holds")
    audit = _safe(lambda: execution_audit_storage.get_all(), "audit")
    traces = _safe(lambda: execution_trace_storage.get_all(), "traces")
    verif = _safe(lambda: verification_storage.get_all(), "verifications")

    # Resolve the action_id from the directly-requested identifier when missing.
    resolved_action = action_id
    if not resolved_action and approval_id:
        for r in (*records, *holds, *authz):
            if getattr(r, "approval_id", None) == approval_id:
                resolved_action = getattr(r, "action_id", None) or resolved_action
                if resolved_action:
                    break
    if not resolved_action and execution_id:
        for r in (*audit, *traces):
            if getattr(r, "execution_id", None) == execution_id:
                resolved_action = getattr(r, "action_id", None) or resolved_action
                if resolved_action:
                    break

    def mat(rec):
        return _matches(rec, resolved_action, approval_id, execution_id)

    a_matches = [r for r in authz if mat(r)]
    rec_matches = [r for r in records if mat(r)]
    hold_matches = [h for h in holds if mat(h)]
    audit_matches = [a for a in audit if mat(a)]
    trace_matches = [t for t in traces if mat(t)]

    # Verification is keyed by execution_id only. An action/approval-based
    # lookup resolves its execution_ids from the audit records that matched.
    exec_ids = {
        a.execution_id for a in audit_matches if getattr(a, "execution_id", None)
    }
    if execution_id:
        exec_ids.add(execution_id)
    if execution_id:
        vermatch = [v for v in verif if v.execution_id == execution_id]
        if not vermatch:
            vermatch = [v for v in verif if v.execution_id in exec_ids]
    else:
        vermatch = [v for v in verif if v.execution_id in exec_ids]

    # S3 provenance, best-effort (in-memory store; may be empty post-restart).
    provenance = {}
    for h in hold_matches:
        prov = get_hold_provenance(getattr(h, "approval_id", None))
        if prov is not None:
            provenance[getattr(h, "approval_id", None)] = _dump(prov)

    return {
        "resolved": {
            "action_id": resolved_action,
            "approval_id": approval_id,
            "execution_id": execution_id,
        },
        "authorizations": [_dump(r) for r in a_matches],
        "approvals": [_dump(r) for r in rec_matches],
        "holds": [_dump(r) for r in hold_matches],
        "audit": [_dump(r) for r in audit_matches],
        "traces": [_dump(r) for r in trace_matches],
        "verifications": [_dump(r) for r in vermatch],
        "provenance": provenance,
    }


def evidence_chain(*, action_id=None, approval_id=None, execution_id=None):
    """Assemble the Govern -> Verify evidence chain for one governed action.

    At least one identifier must be given. Read-only and **fail-open end-to-end**
    (never 500s): if the assembly itself fails for any unexpected reason, the
    caller still gets a 200 with the empty chain shape rather than a 500.
    """
    ids = (action_id, approval_id, execution_id)
    if not any(ids):
        return _empty_shape(action_id, approval_id, execution_id)
    try:
        return _assemble(action_id, approval_id, execution_id)
    except Exception:  # noqa: BLE001 -- whole call is fail-open
        logger.exception("evidence_chain: unexpected assembly failure")
        return _empty_shape(action_id, approval_id, execution_id)
