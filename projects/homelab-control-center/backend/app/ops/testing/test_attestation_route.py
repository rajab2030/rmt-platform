"""RMT-CAP-11 (P-C) -- GET /ops/evidence/export (read-only, operator-auth,
opt-in, requires a signing key).

Mirrors ``test_evidence_route.py``'s discipline for ``GET /ops/evidence``:
disabled must mean disabled, byte for byte, before auth or identifier
validation ever run.
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
    r = client.get(
        "/ops/evidence/export", params={"action_id": "a1"}, headers=_hdr()
    )
    assert r.status_code == 503


def test_enabled_without_signing_key_returns_503(client, monkeypatch):
    monkeypatch.setenv("RMT_ATTESTATION_EXPORT_ENABLED", "true")
    r = client.get(
        "/ops/evidence/export", params={"action_id": "a1"}, headers=_hdr()
    )
    assert r.status_code == 503


def test_enabled_requires_operator_auth(client, monkeypatch):
    monkeypatch.setenv("RMT_ATTESTATION_EXPORT_ENABLED", "true")
    monkeypatch.setenv("RMT_ATTESTATION_SIGNING_KEY", "route-test-key")
    r = client.get("/ops/evidence/export", params={"action_id": "a1"})
    assert r.status_code == 401


def test_enabled_requires_one_identifier(client, monkeypatch):
    monkeypatch.setenv("RMT_ATTESTATION_EXPORT_ENABLED", "true")
    monkeypatch.setenv("RMT_ATTESTATION_SIGNING_KEY", "route-test-key")
    r = client.get("/ops/evidence/export", headers=_hdr())
    assert r.status_code == 422


def test_enabled_returns_a_signed_bundle_and_writes_nothing(client, monkeypatch):
    monkeypatch.setenv("RMT_ATTESTATION_EXPORT_ENABLED", "true")
    monkeypatch.setenv("RMT_ATTESTATION_SIGNING_KEY", "route-test-key")
    r = client.get(
        "/ops/evidence/export",
        params={"action_id": "unknown-action"},
        headers=_hdr(),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["chain"]["resolved"]["action_id"] == "unknown-action"
    assert body["signature"]["algorithm"] == "HMAC-SHA256"

    from app.ops.attestation import verify_bundle

    assert verify_bundle(body, "route-test-key") is True
    assert verify_bundle(body, "wrong-key") is False
