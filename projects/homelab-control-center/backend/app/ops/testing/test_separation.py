"""RMT-PROD P1 (S3) -- separation of duties for agent-originated approval holds.

``check_separation`` gates ``/approve`` and ``/homelab/approve``: for a hold an
agent proposal raised, the approver must differ from the grantor (and the
proposing agent id). Opt-in via ``RMT_AUTH_SEPARATION``; the check fails closed.
"""
import time

import pytest
from fastapi.testclient import TestClient

import app.ops.separation as sep
from app.ops.separation import (
    PROVENANCE_MAX_AGE_SECONDS,
    check_separation,
    get_hold_provenance,
    record_hold_provenance,
)


@pytest.fixture(autouse=True)
def _clean(monkeypatch):
    sep.reset()
    monkeypatch.delenv("RMT_AUTH_SEPARATION", raising=False)
    yield
    sep.reset()


def _record(approval_id="appr-1", granted_by="alice", agent_id="reference-agent"):
    record_hold_provenance(
        approval_id,
        grant_id="g-1",
        granted_by=granted_by,
        agent_id=agent_id,
    )


# --- record / retrieve ----------------------------------------------------


def test_record_and_get_roundtrip():
    _record()
    prov = get_hold_provenance("appr-1")
    assert prov.granted_by == "alice"
    assert prov.grant_id == "g-1"
    assert prov.agent_id == "reference-agent"


def test_record_ignores_empty_approval_id():
    record_hold_provenance("", grant_id="g", granted_by="a", agent_id="x")
    record_hold_provenance(None, grant_id="g", granted_by="a", agent_id="x")
    assert get_hold_provenance("") is None


def test_expired_provenance_is_dropped(monkeypatch):
    _record()
    # fast-forward past the max age
    prov = sep._provenance["appr-1"]
    prov.recorded_at = time.time() - PROVENANCE_MAX_AGE_SECONDS - 1
    assert get_hold_provenance("appr-1") is None
    assert "appr-1" not in sep._provenance  # pruned on read


def test_record_prunes_stale_entries():
    _record("old")
    sep._provenance["old"].recorded_at = time.time() - PROVENANCE_MAX_AGE_SECONDS - 1
    _record("new")
    assert "old" not in sep._provenance
    assert "new" in sep._provenance


# --- check_separation ---------------------------------------------------


def test_disabled_by_default_allows_anyone():
    _record(granted_by="alice")
    assert check_separation("appr-1", "alice") == (True, "separation_disabled")


def test_enabled_blocks_grantor(monkeypatch):
    monkeypatch.setenv("RMT_AUTH_SEPARATION", "true")
    _record(granted_by="alice")
    assert check_separation("appr-1", "alice") == (False, "approver_is_grantor")


def test_enabled_allows_a_different_operator(monkeypatch):
    monkeypatch.setenv("RMT_AUTH_SEPARATION", "true")
    _record(granted_by="alice")
    assert check_separation("appr-1", "bob") == (True, "ok")


def test_enabled_blocks_the_proposing_agent_id(monkeypatch):
    monkeypatch.setenv("RMT_AUTH_SEPARATION", "true")
    _record(granted_by="alice", agent_id="llm-agent")
    assert check_separation("appr-1", "llm-agent") == (
        False, "approver_is_proposer",
    )


def test_enabled_non_agent_hold_passes_through(monkeypatch):
    monkeypatch.setenv("RMT_AUTH_SEPARATION", "true")
    # no provenance recorded -> not an S3 concern (e.g. operator /execute hold)
    assert check_separation("operator-hold", "alice") == (
        True, "not_agent_originated",
    )


def test_check_fails_closed_on_internal_error(monkeypatch):
    monkeypatch.setenv("RMT_AUTH_SEPARATION", "true")
    monkeypatch.setattr(
        sep, "get_hold_provenance",
        lambda *_a, **_k: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    assert check_separation("appr-1", "alice") == (
        False, "separation_check_error",
    )


# --- HTTP: /approve + /homelab/approve enforce it ---------------------------

TOKENS = "alice:alice-secret,bob:bob-secret"
ALICE = {"Authorization": "Bearer alice-secret"}
BOB = {"Authorization": "Bearer bob-secret"}


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("RMT_AUTH_ENABLED", "true")
    monkeypatch.setenv("RMT_OPERATOR_TOKENS", TOKENS)
    monkeypatch.setenv("RMT_AUTH_SEPARATION", "true")
    import app.main as main_app

    with TestClient(main_app.app) as c:
        yield c


@pytest.mark.parametrize("path", ["/approve", "/homelab/approve"])
def test_route_blocks_grantor_with_403(client, path):
    # alice granted the agent authority behind this hold
    record_hold_provenance(
        "appr-x", grant_id="g", granted_by="alice", agent_id="reference-agent"
    )
    r = client.post(path, params={"approval_id": "appr-x"}, headers=ALICE)
    assert r.status_code == 403
    assert "approver_is_grantor" in r.text


@pytest.mark.parametrize("path", ["/approve", "/homelab/approve"])
def test_route_allows_a_different_operator(client, path):
    record_hold_provenance(
        "appr-y", grant_id="g", granted_by="alice", agent_id="reference-agent"
    )
    # bob != grantor -> S3 does not block (the Core then reports the hold state)
    r = client.post(path, params={"approval_id": "appr-y"}, headers=BOB)
    assert r.status_code != 403
