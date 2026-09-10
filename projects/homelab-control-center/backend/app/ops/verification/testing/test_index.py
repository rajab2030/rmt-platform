"""B1b -- effective-status verification index.

Covers the rebuild precedence (all four branches of proposal section 2.3),
that rebuild is silent + marks history already-notified, the live `record`
upsert, and the `view` filter / limit / ordering.
"""
import app.core.intelligence.verification.storage as verification_storage_module
import app.core.intelligence.execution.storage as audit_storage_module
from app.core.intelligence.verification.models import (
    ExpectedOutcome,
    VerificationResult,
    VerificationStatus,
)
from app.core.intelligence.verification.storage import VerificationStorage
from app.core.intelligence.execution.storage import ExecutionAuditStorage
from app.core.intelligence.execution.audit import ExecutionAuditRecord

from app.ops.verification import index
from app.ops.execution_evidence import ADAPTER_EXECUTION_FAILED


def _vr(execution_id, status, *, reason="", operation="restart", target="svc"):
    return VerificationResult(
        execution_id=execution_id,
        status=status,
        expected=ExpectedOutcome(
            target=target, operation=operation, expected_state="running"
        ),
        reason=reason,
        observed=None,
    )


def _above_core(execution_id, status, adapter="docker", **kw):
    return _vr(
        execution_id,
        status,
        reason=f"[layer=above_core adapter={adapter} supersedes=observation_unavailable] ok",
        **kw,
    )


def _seed(monkeypatch, records, audit=None):
    store = VerificationStorage(file_path=None)
    for r in records:
        store.save(r)
    monkeypatch.setattr(verification_storage_module, "verification_storage", store)

    aud = ExecutionAuditStorage(file_path=None)
    for a in audit or []:
        aud.save(a)
    monkeypatch.setattr(audit_storage_module, "execution_audit_storage", aud)
    return store


# --- rebuild precedence --------------------------------------------------

def test_rebuild_above_core_verified_success_supersedes_core(monkeypatch):
    _seed(
        monkeypatch,
        [
            _vr("e1", VerificationStatus.OBSERVATION_UNAVAILABLE),  # Core
            _above_core("e1", VerificationStatus.VERIFIED_SUCCESS),
        ],
    )
    index.rebuild()
    row = index.get("e1")
    assert row.effective_status == "verified_success"
    assert row.verified is True
    assert row.core_status == "observation_unavailable"
    assert row.above_core_status == "verified_success"


def test_rebuild_above_core_state_mismatch(monkeypatch):
    _seed(
        monkeypatch,
        [
            _vr("e2", VerificationStatus.OBSERVATION_UNAVAILABLE),
            _above_core("e2", VerificationStatus.STATE_MISMATCH),
        ],
    )
    index.rebuild()
    row = index.get("e2")
    assert row.effective_status == "state_mismatch"
    assert row.verified is False


def test_rebuild_adapter_failure_wins_over_above_core(monkeypatch):
    _seed(
        monkeypatch,
        [
            _above_core("e3", VerificationStatus.STATE_MISMATCH),
            _vr("e3", ADAPTER_EXECUTION_FAILED),  # E3 record
        ],
    )
    index.rebuild()
    row = index.get("e3")
    assert row.effective_status == ADAPTER_EXECUTION_FAILED
    assert row.verified is False


def test_rebuild_module_change_uses_core_status(monkeypatch):
    _seed(
        monkeypatch,
        [_vr("e4", VerificationStatus.VERIFIED_SUCCESS, operation="create")],
        audit=[
            ExecutionAuditRecord(
                execution_id="e4", action_id="a4",
                authorization_id="z4", adapter="module_change", status="completed",
            )
        ],
    )
    index.rebuild()
    row = index.get("e4")
    assert row.adapter == "module_change"
    assert row.effective_status == "verified_success"
    assert row.verified is True
    assert row.action_id == "a4"


def test_rebuild_bare_core_observation_unavailable_is_unverified(monkeypatch):
    _seed(
        monkeypatch,
        [_vr("e5", VerificationStatus.OBSERVATION_UNAVAILABLE)],
        audit=[
            ExecutionAuditRecord(
                execution_id="e5", action_id="a5",
                authorization_id="z5", adapter="docker", status="completed",
            )
        ],
    )
    index.rebuild()
    row = index.get("e5")
    assert row.effective_status == "unverified"
    assert row.verified is False
    assert row.adapter == "docker"


def test_rebuild_is_silent_and_marks_history_notified(monkeypatch):
    _seed(monkeypatch, [_vr("e6", VerificationStatus.OBSERVATION_UNAVAILABLE)])
    summary = index.rebuild()
    assert summary["rows"] == 1 and summary["unverified"] == 1
    assert index.get("e6").notified_inconclusive is True


# --- live record + view -----------------------------------------------

def test_record_upsert_and_reclassify(monkeypatch):
    _seed(monkeypatch, [])
    index.record(
        "e7", action_id="a7", adapter="docker", operation="restart",
        target="svc", core_status="observation_unavailable", above_core_status=None,
    )
    assert index.get("e7").effective_status == "unverified"
    index.record(
        "e7", action_id="a7", adapter="docker", operation="restart",
        target="svc", core_status="observation_unavailable",
        above_core_status="verified_success",
    )
    row = index.get("e7")
    assert row.effective_status == "verified_success" and row.verified is True


def test_record_preserves_notified_flag(monkeypatch):
    _seed(monkeypatch, [])
    index.record(
        "e8", action_id=None, adapter="simulation", operation="restart",
        target="svc", core_status="observation_unavailable", above_core_status=None,
    )
    index.mark_notified("e8")
    index.record(
        "e8", action_id=None, adapter="simulation", operation="restart",
        target="svc", core_status="observation_unavailable", above_core_status=None,
    )
    assert index.get("e8").notified_inconclusive is True


def test_view_filter_limit_and_order(monkeypatch):
    import time

    _seed(monkeypatch, [])
    for i in range(5):
        index.record(
            f"e{i}", action_id=None, adapter="docker", operation="restart",
            target="svc", core_status="observation_unavailable",
            above_core_status="verified_success" if i % 2 else None,
        )
        time.sleep(0.002)  # distinct updated_at for a deterministic newest-first order
    all_rows = index.view(limit=50)
    assert [r["execution_id"] for r in all_rows] == ["e4", "e3", "e2", "e1", "e0"]
    assert index.view(limit=2) == all_rows[:2]
    unverified = index.view(effective_status="unverified")
    assert {r["execution_id"] for r in unverified} == {"e0", "e2", "e4"}


def test_view_never_raises(monkeypatch):
    monkeypatch.setattr(index, "_rows", "not-a-dict")
    assert index.view() == []
