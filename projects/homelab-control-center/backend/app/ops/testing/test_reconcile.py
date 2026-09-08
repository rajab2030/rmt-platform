"""RMT-PROD P0 (E2) -- startup hold/record reconciliation.

The Core resolves a manual-approval hold in the approval *record* store but not
the *hold* store, so after a restart a resolved hold reloads as ``pending``.
``reconcile_holds_against_records`` corrects that once at startup, using the
record store as the source of truth, and is strictly bounded + fail-open.
"""
import pytest

import app.core.intelligence.actions.approval_service as approval_service
from app.core.intelligence.actions.approval import (
    ApprovalHold,
    ApprovalRecord,
    ApprovalStatus,
)
from app.core.intelligence.actions.approval_storage import (
    ApprovalHoldStorage,
    ApprovalRecordStorage,
)
from app.core.intelligence.actions.models import ActionRequest, ActionType
from app.ops.reconcile import reconcile_holds_against_records


def _action(component="uptime-kuma"):
    return ActionRequest(
        decision_id="d-1",
        component=component,
        action_type=ActionType.RESTART_COMPONENT,
        reason="test",
    )


def _hold(approval_id, status=ApprovalStatus.PENDING, approved_by=None):
    return ApprovalHold(
        approval_id=approval_id,
        action_id="a-1",
        action=_action(),
        adapter_name="simulation",
        reason="held",
        status=status,
        approved_by=approved_by,
    )


def _record(approval_id, decision, approved_by="ragb"):
    return ApprovalRecord(
        approval_id=approval_id,
        action_id="a-1",
        decision=decision,
        approved_by=approved_by,
    )


@pytest.fixture
def stores(tmp_path, monkeypatch):
    """Isolated, file-backed hold + record stores wired into approval_service."""
    hold_path = tmp_path / "approval_holds.json"
    record_path = tmp_path / "approval_records.json"
    hold_storage = ApprovalHoldStorage(file_path=hold_path)
    record_storage = ApprovalRecordStorage(file_path=record_path)
    monkeypatch.setattr(
        approval_service, "approval_hold_storage", hold_storage
    )
    monkeypatch.setattr(
        approval_service, "approval_record_storage", record_storage
    )
    return hold_storage, record_storage, hold_path


def _reload(path):
    return ApprovalHoldStorage(file_path=path).get_all()


@pytest.mark.parametrize(
    "decision, expected",
    [
        ("approved", ApprovalStatus.APPROVED),
        ("rejected", ApprovalStatus.REJECTED),
    ],
)
def test_stale_pending_hold_is_corrected_and_persisted(
    stores, decision, expected
):
    hold_storage, record_storage, hold_path = stores
    hold_storage.save(_hold("h1"))
    record_storage.save(_record("h1", decision, approved_by="ops2"))

    summary = reconcile_holds_against_records()

    assert summary == {"checked": 1, "reconciled": 1, "ids": ["h1"]}
    # in memory
    assert hold_storage.get_by_id("h1").status is expected
    assert hold_storage.get_by_id("h1").approved_by == "ops2"
    # durably: a fresh store loaded from disk sees the corrected state
    reloaded = _reload(hold_path)
    assert reloaded[0].status is expected
    assert reloaded[0].approved_by == "ops2"


def test_hold_with_no_record_is_left_untouched(stores):
    hold_storage, _record_storage, hold_path = stores
    hold_storage.save(_hold("h1"))

    summary = reconcile_holds_against_records()

    assert summary["reconciled"] == 0
    assert hold_storage.get_by_id("h1").status is ApprovalStatus.PENDING
    assert _reload(hold_path)[0].status is ApprovalStatus.PENDING


def test_non_terminal_record_is_left_untouched(stores):
    hold_storage, record_storage, _p = stores
    hold_storage.save(_hold("h1"))
    record_storage.save(_record("h1", "pending"))

    summary = reconcile_holds_against_records()

    assert summary["reconciled"] == 0
    assert hold_storage.get_by_id("h1").status is ApprovalStatus.PENDING


def test_already_resolved_hold_is_not_recounted(stores):
    hold_storage, record_storage, _p = stores
    hold_storage.save(_hold("h1", status=ApprovalStatus.APPROVED))
    record_storage.save(_record("h1", "approved"))

    summary = reconcile_holds_against_records()

    assert summary == {"checked": 1, "reconciled": 0, "ids": []}


def test_existing_approved_by_is_preserved(stores):
    hold_storage, record_storage, _p = stores
    hold_storage.save(_hold("h1", approved_by="original"))
    record_storage.save(_record("h1", "approved", approved_by="someone-else"))

    reconcile_holds_against_records()

    assert hold_storage.get_by_id("h1").approved_by == "original"


def test_mixed_batch_only_stale_ones_corrected(stores):
    hold_storage, record_storage, hold_path = stores
    hold_storage.save(_hold("stale"))
    hold_storage.save(_hold("live"))
    hold_storage.save(_hold("done", status=ApprovalStatus.REJECTED))
    record_storage.save(_record("stale", "approved"))
    # "live" has no record; "done" already resolved

    summary = reconcile_holds_against_records()

    assert summary["checked"] == 3
    assert summary["reconciled"] == 1
    assert summary["ids"] == ["stale"]
    by_id = {h.approval_id: h for h in _reload(hold_path)}
    assert by_id["stale"].status is ApprovalStatus.APPROVED
    assert by_id["live"].status is ApprovalStatus.PENDING
    assert by_id["done"].status is ApprovalStatus.REJECTED


def test_no_disk_write_when_nothing_is_stale(stores, monkeypatch):
    hold_storage, record_storage, _p = stores
    hold_storage.save(_hold("h1"))
    record_storage.save(_record("h1", "pending"))

    calls = []
    monkeypatch.setattr(
        hold_storage, "_persist", lambda: calls.append(1)
    )
    reconcile_holds_against_records()
    assert calls == []


def test_fail_open_on_storage_error(stores, monkeypatch):
    hold_storage, _record_storage, _p = stores
    monkeypatch.setattr(
        hold_storage, "get_all", lambda: (_ for _ in ()).throw(RuntimeError("boom"))
    )
    # must not raise
    summary = reconcile_holds_against_records()
    assert summary["reconciled"] == 0
