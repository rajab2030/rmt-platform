"""RMT-PROD P1 (E4) -- evidence-store retention / archival.

``archive_aged_evidence`` moves records older than the retention window out of
the live JSON stores into ``<name>.archive.jsonl`` (append-only), re-persists
the trimmed store atomically, and is strictly bounded + idempotent + fail-open.
"""
import json
from datetime import datetime, timedelta, timezone

import pytest

from app.core.intelligence.verification.models import VerificationResult
from app.core.intelligence.verification.storage import VerificationStorage
from app.ops.retention import (
    archive_aged_evidence,
    archive_store,
)


def _rec(execution_id, age_days=None, created_at="use_age"):
    kw = {"execution_id": execution_id, "status": "verified_success"}
    if created_at == "use_age" and age_days is not None:
        kw["created_at"] = datetime.now(timezone.utc) - timedelta(days=age_days)
    elif created_at != "use_age":
        kw["created_at"] = created_at
    return VerificationResult(**kw)


@pytest.fixture
def store(tmp_path):
    return VerificationStorage(file_path=tmp_path / "verifications.json")


def _archive_lines(store):
    p = store._file_path.with_name(store._file_path.stem + ".archive.jsonl")
    if not p.exists():
        return []
    return [json.loads(ln) for ln in p.read_text().splitlines() if ln.strip()]


def _cutoff(days):
    return datetime.now(timezone.utc) - timedelta(days=days)


def test_old_records_archived_new_kept(store):
    store.save(_rec("old-1", age_days=200))
    store.save(_rec("old-2", age_days=91))
    store.save(_rec("new-1", age_days=10))

    res = archive_store("verifications", store, _cutoff(90))

    assert res == {"store": "verifications", "archived": 2, "kept": 1}
    assert [r.execution_id for r in store.get_all()] == ["new-1"]
    assert {ln["execution_id"] for ln in _archive_lines(store)} == {"old-1", "old-2"}
    # durably: a fresh store from disk sees only the kept record
    reloaded = VerificationStorage(file_path=store._file_path).get_all()
    assert [r.execution_id for r in reloaded] == ["new-1"]


def test_nothing_old_writes_nothing(store, monkeypatch):
    store.save(_rec("new-1", age_days=1))
    calls = []
    monkeypatch.setattr(store, "_persist", lambda: calls.append(1))

    res = archive_store("verifications", store, _cutoff(90))

    assert res == {"store": "verifications", "archived": 0, "kept": 1}
    assert calls == []
    assert _archive_lines(store) == []


def test_missing_or_bad_created_at_is_kept(store):
    # force values past validation that a malformed archive/JSON could produce
    no_ts = _rec("no-ts")
    object.__setattr__(no_ts, "created_at", None)
    bad_ts = _rec("bad-ts")
    object.__setattr__(bad_ts, "created_at", "not-a-date")
    store._records.extend([no_ts, bad_ts])

    res = archive_store("verifications", store, _cutoff(1))

    assert res["archived"] == 0
    assert {x.execution_id for x in store.get_all()} == {"no-ts", "bad-ts"}


def test_archive_appends_across_runs(store):
    store.save(_rec("old-1", age_days=200))
    archive_store("verifications", store, _cutoff(90))
    store.save(_rec("old-2", age_days=200))
    archive_store("verifications", store, _cutoff(90))

    assert [ln["execution_id"] for ln in _archive_lines(store)] == ["old-1", "old-2"]


def test_idempotent_second_run_is_noop(store):
    store.save(_rec("old-1", age_days=200))
    store.save(_rec("new-1", age_days=1))
    first = archive_store("verifications", store, _cutoff(90))
    second = archive_store("verifications", store, _cutoff(90))

    assert first["archived"] == 1
    assert second == {"store": "verifications", "archived": 0, "kept": 1}
    assert len(_archive_lines(store)) == 1


def test_in_memory_store_is_skipped():
    mem = VerificationStorage(file_path=None)
    mem.save(_rec("x", age_days=999))
    res = archive_store("verifications", mem, _cutoff(90))
    assert res["skipped"] == "in_memory"
    assert len(mem.get_all()) == 1


def test_store_error_is_fail_open(store, monkeypatch):
    store.save(_rec("old-1", age_days=200))
    monkeypatch.setattr(
        store, "get_all",
        lambda: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    res = archive_store("verifications", store, _cutoff(90))
    assert res["archived"] == 0 and "error" in res


def test_archive_aged_evidence_disabled_when_days_le_zero(store):
    store.save(_rec("old-1", age_days=999))
    res = archive_aged_evidence(retention_days=0, stores=[("verifications", store)])
    assert res == {"retention_days": 0, "disabled": True, "archived_total": 0}
    assert len(store.get_all()) == 1


def test_archive_aged_evidence_rolls_up_multiple_stores(tmp_path):
    s1 = VerificationStorage(file_path=tmp_path / "a.json")
    s2 = VerificationStorage(file_path=tmp_path / "b.json")
    s1.save(_rec("a-old", age_days=200))
    s1.save(_rec("a-new", age_days=1))
    s2.save(_rec("b-old", age_days=200))

    res = archive_aged_evidence(
        retention_days=90, stores=[("a", s1), ("b", s2)]
    )

    assert res["archived_total"] == 2
    assert res["retention_days"] == 90
    assert {r["store"]: r["archived"] for r in res["stores"]} == {"a": 1, "b": 1}


def test_archive_aged_evidence_never_raises(monkeypatch):
    monkeypatch.setattr(
        "app.ops.retention._default_stores",
        lambda: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    res = archive_aged_evidence(retention_days=90)
    assert res["archived_total"] == 0 and "error" in res
