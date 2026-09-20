"""RMT-CAP-11 (P-C) -- signed evidence-export bundle assembly and verification.

Mirrors ``test_evidence_chain.py``'s isolation discipline: the underlying
``evidence_chain()`` stores are wired to in-memory instances so no test
touches the real ``data/governance_evidence.db``. These tests exercise the
signing/verification layer itself (canonicalization, tamper detection,
fail-open shape); route-level (auth/flag) behavior is in
``test_attestation_route.py``.
"""
import pytest

import app.ops.evidence_chain as evidence_chain
from app.ops import attestation
from app.core.intelligence.actions.authorization import ExecutionAuthorization
from app.core.intelligence.actions.authorization_storage import AuthorizationStorage


@pytest.fixture
def stores(monkeypatch):
    authz = AuthorizationStorage()
    authz.save(
        ExecutionAuthorization(
            action_id="a-1",
            approval_id="ap-1",
            authorized_by="grantor",
            status="authorized",
        )
    )
    monkeypatch.setattr(evidence_chain, "execution_authorization_storage", authz)
    return {"authz": authz}


SIGNING_KEY = "test-signing-key-do-not-use-in-prod"


def test_export_bundle_is_signed_and_verifies(stores):
    bundle = attestation.export_bundle(action_id="a-1", signing_key=SIGNING_KEY)
    assert bundle["format_version"] == attestation.FORMAT_VERSION
    assert bundle["chain"]["resolved"]["action_id"] == "a-1"
    assert bundle["signature"]["algorithm"] == "HMAC-SHA256"
    assert attestation.verify_bundle(bundle, SIGNING_KEY) is True


def test_unknown_identifier_still_produces_a_verifiable_bundle(stores):
    bundle = attestation.export_bundle(
        action_id="does-not-exist", signing_key=SIGNING_KEY
    )
    assert bundle["chain"]["authorizations"] == []
    assert attestation.verify_bundle(bundle, SIGNING_KEY) is True


def test_wrong_key_fails_verification(stores):
    bundle = attestation.export_bundle(action_id="a-1", signing_key=SIGNING_KEY)
    assert attestation.verify_bundle(bundle, "wrong-key") is False


def test_tampered_chain_fails_verification(stores):
    bundle = attestation.export_bundle(action_id="a-1", signing_key=SIGNING_KEY)
    bundle["chain"]["authorizations"][0]["authorized_by"] = "attacker"
    assert attestation.verify_bundle(bundle, SIGNING_KEY) is False


def test_tampered_timestamp_fails_verification(stores):
    bundle = attestation.export_bundle(action_id="a-1", signing_key=SIGNING_KEY)
    bundle["generated_at"] = "2000-01-01T00:00:00+00:00"
    assert attestation.verify_bundle(bundle, SIGNING_KEY) is False


def test_tampered_signature_fails_verification(stores):
    bundle = attestation.export_bundle(action_id="a-1", signing_key=SIGNING_KEY)
    bundle["signature"]["value"] = "0" * 64
    assert attestation.verify_bundle(bundle, SIGNING_KEY) is False


def test_missing_signature_block_is_invalid_not_a_crash():
    assert attestation.verify_bundle({"format_version": 1}, SIGNING_KEY) is False


def test_non_dict_bundle_is_invalid_not_a_crash():
    assert attestation.verify_bundle("not-a-bundle", SIGNING_KEY) is False  # type: ignore[arg-type]


def test_canonicalize_is_key_order_independent():
    a = attestation.canonicalize({"x": 1, "y": 2})
    b = attestation.canonicalize({"y": 2, "x": 1})
    assert a == b


def test_export_bundle_read_only(stores):
    before = len(stores["authz"].get_all())
    attestation.export_bundle(action_id="a-1", signing_key=SIGNING_KEY)
    assert len(stores["authz"].get_all()) == before
