"""RMT-PROD P0 (E1) -- DurableStore writes are atomic and crash-tolerant.

Behaviour-preserving hardening: committed file contents are unchanged; the
only difference is that a partial write can never be observed or committed.
"""
import json

import pytest
from pydantic import BaseModel

from app.core.intelligence import durable_store
from app.core.intelligence.durable_store import DurableStore


class _Rec(BaseModel):
    n: int
    label: str


def _new(path):
    return DurableStore(file_path=path, model=_Rec)


def test_round_trip_and_file_shape(tmp_path):
    p = tmp_path / "recs.json"
    s = _new(p)
    s.save(_Rec(n=1, label="a"))
    s.save(_Rec(n=2, label="b"))

    # identical on-disk shape to a plain json.dump(..., indent=4)
    on_disk = json.loads(p.read_text())
    assert on_disk == [{"n": 1, "label": "a"}, {"n": 2, "label": "b"}]
    assert p.read_text() == json.dumps(on_disk, indent=4)

    # a fresh store reloads it
    assert [(r.n, r.label) for r in _new(p).get_all()] == [(1, "a"), (2, "b")]

    # no leftover temp file after a clean write
    assert not (tmp_path / "recs.json.tmp").exists()


def test_interrupted_write_leaves_previous_file_intact(tmp_path, monkeypatch):
    p = tmp_path / "recs.json"
    s = _new(p)
    s.save(_Rec(n=1, label="committed"))
    good = p.read_text()

    # next persist blows up mid-serialization
    def boom(*a, **k):
        raise RuntimeError("disk full")

    monkeypatch.setattr(durable_store.json, "dump", boom)
    with pytest.raises(RuntimeError):
        s.save(_Rec(n=2, label="lost"))

    # the committed file is untouched (os.replace never ran)
    assert p.read_text() == good
    assert json.loads(p.read_text()) == [{"n": 1, "label": "committed"}]


def test_stale_tmp_is_discarded_on_load(tmp_path):
    p = tmp_path / "recs.json"
    _new(p).save(_Rec(n=7, label="real"))
    # simulate residue from a killed process
    (tmp_path / "recs.json.tmp").write_text('[{"n": 999, "label": "partial"}')

    s = _new(p)
    assert [(r.n, r.label) for r in s.get_all()] == [(7, "real")]
    assert not (tmp_path / "recs.json.tmp").exists()


def test_no_path_is_in_memory_only(tmp_path):
    s = DurableStore(model=_Rec)
    s.save(_Rec(n=1, label="x"))
    assert len(s.get_all()) == 1  # no file, no error
