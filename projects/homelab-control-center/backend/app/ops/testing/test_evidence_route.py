"""RMT-CAP-09 -- GET /ops/evidence (read-only, operator-authenticated, opt-in).

Mirrors GET /ops/verifications: auth-gated, plus its own feature flag
(``RMT_OPS_EVIDENCE_ENABLED``, default off) since this route was found running
live before it had one -- disabled must mean disabled, byte for byte, with no
other code path able to reach ``evidence_chain()``.
"""
import pytest
from fastapi.testclient import TestClient

import app.main as main_app


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("RMT_AUTH_ENABLED", "true")
    monkeypatch.setenv("RMT_OPERATOR_TOKENS", "alice:tok-alice")
    with TestClient(main_app.app) as c:
        yield c


def _hdr():
    return {"Authorization": "Bearer tok-alice"}


def test_disabled_by_default_returns_503(client):
    r = client.get("/ops/evidence", params={"action_id": "a1"}, headers=_hdr())
    assert r.status_code == 503


def test_disabled_short_circuits_before_identifier_validation(client):
    # Authenticated, no identifier, flag still off (default): 503, not 422 --
    # the disabled check runs before the "need an identifier" check.
    r = client.get("/ops/evidence", headers=_hdr())
    assert r.status_code == 503


def test_enabled_requires_operator_auth(client, monkeypatch):
    monkeypatch.setenv("RMT_OPS_EVIDENCE_ENABLED", "true")
    r = client.get("/ops/evidence", params={"action_id": "a1"})
    assert r.status_code == 401


def test_enabled_requires_one_identifier(client, monkeypatch):
    monkeypatch.setenv("RMT_OPS_EVIDENCE_ENABLED", "true")
    r = client.get("/ops/evidence", headers=_hdr())
    assert r.status_code == 422


def test_enabled_resolves_and_writes_nothing(client, monkeypatch):
    monkeypatch.setenv("RMT_OPS_EVIDENCE_ENABLED", "true")
    r = client.get(
        "/ops/evidence", params={"action_id": "unknown-action"}, headers=_hdr()
    )
    assert r.status_code == 200
    body = r.json()
    assert body["resolved"]["action_id"] == "unknown-action"
    assert body["authorizations"] == []
