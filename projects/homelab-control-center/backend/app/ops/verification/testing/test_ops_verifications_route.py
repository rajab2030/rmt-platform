"""B1b -- GET /ops/verifications (read-only, operator-authenticated).

Mirrors GET /ops/holds: auth-gated, derives from the in-memory effective-status
index, [] on error.
"""
import pytest
from fastapi.testclient import TestClient

import app.main as main_app
from app.ops.verification import index


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("RMT_AUTH_ENABLED", "true")
    monkeypatch.setenv("RMT_OPERATOR_TOKENS", "alice:tok-alice")
    with TestClient(main_app.app) as c:
        # The lifespan rebuild populates the index from the session-shared
        # throwaway evidence db; clear it so each test controls the rows.
        index.reset()
        yield c


def _hdr():
    return {"Authorization": "Bearer tok-alice"}


def _seed_rows():
    index.record(
        "v1", action_id="a1", adapter="docker", operation="restart",
        target="svc", core_status="observation_unavailable",
        above_core_status="verified_success",
    )
    index.record(
        "v2", action_id="a2", adapter="simulation", operation="restart",
        target="svc", core_status="observation_unavailable", above_core_status=None,
    )


def test_requires_operator_auth(client):
    assert client.get("/ops/verifications").status_code == 401


def test_returns_index_rows(client):
    _seed_rows()
    r = client.get("/ops/verifications", headers=_hdr())
    assert r.status_code == 200
    rows = r.json()["verifications"]
    assert {row["execution_id"] for row in rows} == {"v1", "v2"}


def test_effective_status_filter(client):
    _seed_rows()
    rows = client.get(
        "/ops/verifications", params={"effective_status": "unverified"}, headers=_hdr()
    ).json()["verifications"]
    assert [row["execution_id"] for row in rows] == ["v2"]


def test_limit_caps_results(client):
    _seed_rows()
    rows = client.get(
        "/ops/verifications", params={"limit": 1}, headers=_hdr()
    ).json()["verifications"]
    assert len(rows) == 1


def test_empty_index_returns_empty_list(client):
    r = client.get("/ops/verifications", headers=_hdr())
    assert r.status_code == 200
    assert r.json()["verifications"] == []
