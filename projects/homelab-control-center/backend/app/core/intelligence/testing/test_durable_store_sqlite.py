"""T0-1 -- DurableStore SQLite backend contract.

Selected by a ``.db`` file path. ``save()`` is one INSERT (no whole-file
rewrite); ``get_by_*`` keep first-match order; ``update()`` is in place;
``file_path=None`` is still pure in-memory; a killed process mid-write leaves
the last committed rows intact and never a torn record; E4 retention's
``_replace_records`` maps to DELETE + re-insert; the per-table archive path
does not collide across the six shared-DB stores.
"""
import os
import signal
import subprocess
import sys
import time

import pytest
from pydantic import BaseModel

from app.core.intelligence.durable_store import DurableStore
from app.core.intelligence.verification.models import VerificationResult
from app.core.intelligence.verification.storage import VerificationStorage
from app.core.intelligence.actions.approval_storage import ApprovalRecordStorage
from app.core.intelligence.actions.approval import ApprovalRecord


class _Rec(BaseModel):
    n: int
    label: str


class _Store(DurableStore):
    _table = "recs"
    _key_field = "label"

    def __init__(self, file_path=None):
        super().__init__(file_path=file_path, model=_Rec)


def _db(tmp_path):
    return tmp_path / "governance_evidence.db"


def test_save_is_a_single_insert_not_a_rewrite(tmp_path):
    s = _Store(_db(tmp_path))
    for i in range(200):
        s.save(_Rec(n=i, label=f"r{i}"))

    rows = s._conn.execute('SELECT COUNT(*) FROM "recs"').fetchone()[0]
    assert rows == 200
    # payload column is exactly the JSON object the JSON backend would write
    one = s._conn.execute(
        'SELECT payload FROM "recs" WHERE key = ?', ("r7",)
    ).fetchone()[0]
    assert one == '{"n": 7, "label": "r7"}'


def test_reload_from_disk_preserves_order(tmp_path):
    s = _Store(_db(tmp_path))
    s.save(_Rec(n=1, label="a"))
    s.save(_Rec(n=2, label="b"))
    s.save(_Rec(n=3, label="c"))

    reloaded = _Store(_db(tmp_path))
    assert [(r.n, r.label) for r in reloaded.get_all()] == [
        (1, "a"), (2, "b"), (3, "c")
    ]


def test_get_by_id_first_match_and_update_in_place(tmp_path):
    s = ApprovalRecordStorage(file_path=_db(tmp_path))
    s.save(ApprovalRecord(
        approval_id="p1", action_id="a1",
        decision="manual_required", approved_by="",
    ))
    s.save(ApprovalRecord(
        approval_id="p2", action_id="a2",
        decision="manual_required", approved_by="",
    ))

    s.update("p1", decision="approved", approved_by="ops")

    assert s.get_by_id("p1").decision == "approved"
    assert s.get_by_id("p1").approved_by == "ops"
    assert s.get_by_id("p2").decision == "manual_required"
    # durable: a fresh store from the same db sees the update, no dup row
    fresh = ApprovalRecordStorage(file_path=_db(tmp_path))
    assert fresh.get_by_id("p1").decision == "approved"
    assert len(fresh.get_all()) == 2


def test_no_path_is_in_memory_only_no_db_file(tmp_path):
    monkey_cwd = tmp_path
    old = os.getcwd()
    os.chdir(monkey_cwd)
    try:
        s = VerificationStorage(file_path=None)
        s.save(VerificationResult(execution_id="x", status="verified_success"))
        assert len(s.get_all()) == 1
        assert not any(p.suffix == ".db" for p in tmp_path.iterdir())
    finally:
        os.chdir(old)


def test_retention_replace_records_maps_to_delete_and_reinsert(tmp_path):
    s = _Store(_db(tmp_path))
    for i in range(5):
        s.save(_Rec(n=i, label=f"r{i}"))

    s._replace_records([r for r in s.get_all() if r.n >= 3])

    assert [r.n for r in s.get_all()] == [3, 4]
    rows = s._conn.execute(
        'SELECT key FROM "recs" ORDER BY id'
    ).fetchall()
    assert [r[0] for r in rows] == ["r3", "r4"]
    assert _Store(_db(tmp_path)).get_all()[0].n == 3


def test_archive_path_is_per_table_not_per_db_file(tmp_path):
    a = VerificationStorage(file_path=_db(tmp_path))
    b = ApprovalRecordStorage(file_path=_db(tmp_path))
    assert a._archive_path().name == "verifications.archive.jsonl"
    assert b._archive_path().name == "approval_records.archive.jsonl"
    assert a._archive_path() != b._archive_path()


_CHILD = """
import sys, time
sys.path.insert(0, {backend!r})
from app.core.intelligence.durable_store import DurableStore
from pydantic import BaseModel
class R(BaseModel):
    n: int
    label: str
class S(DurableStore):
    _table = "recs"
    _key_field = "label"
    def __init__(self, p): super().__init__(file_path=p, model=R)
s = S({db!r})
for i in range(500):
    s.save(R(n=i, label="r%d" % i))
    time.sleep(0.005)
"""


def test_killed_mid_write_leaves_committed_rows_intact(tmp_path):
    backend = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")
    )
    db = str(_db(tmp_path))
    code = _CHILD.format(backend=backend, db=db)
    proc = subprocess.Popen([sys.executable, "-c", code])
    time.sleep(0.6)
    proc.send_signal(signal.SIGKILL)
    proc.wait()

    s = _Store(tmp_path / "governance_evidence.db")
    recs = s.get_all()
    # some rows committed, not all; every one is a whole, valid record; the
    # committed rows are a prefix 0..k with no gap and no torn payload
    assert 0 < len(recs) < 500
    assert [r.n for r in recs] == list(range(len(recs)))


def test_concurrent_appends_from_threads_all_land(tmp_path):
    import threading

    s = _Store(_db(tmp_path))

    def worker(base):
        for i in range(50):
            s.save(_Rec(n=base + i, label=f"r{base + i}"))

    threads = [threading.Thread(target=worker, args=(b,)) for b in (0, 100, 200)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(s.get_all()) == 150
    assert _Store(_db(tmp_path))._conn.execute(
        'SELECT COUNT(*) FROM "recs"'
    ).fetchone()[0] == 150
