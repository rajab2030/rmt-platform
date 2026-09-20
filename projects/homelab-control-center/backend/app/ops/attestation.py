"""RMT-CAP-11 (P-C) -- signed, portable evidence-export bundles.

Above-Core / product surface. No ``app/core/**`` change; no write path; not on
the governed mutation path.

Wraps the existing, unmodified ``evidence_chain()`` (RMT-CAP-09) in a signed
envelope so a bundle can be taken out of the platform and verified **offline**
-- without trusting or re-querying the live service. Signing is HMAC-SHA256
over a canonical (deterministic key order) JSON serialization of the payload,
using stdlib only (``hashlib`` / ``hmac``); see the RMT-CAP-11 proposal §3a for
why an asymmetric/PKI scheme is out of scope for this slice.

Discipline mirrors ``evidence_chain()``: read-only and fail-open end-to-end --
an assembly failure still produces a signed "empty chain" bundle (itself a
verifiable, non-repudiable statement), never a 500.
"""
import hashlib
import hmac
import json
import logging
from datetime import datetime, timezone

from app.ops.evidence_chain import evidence_chain

logger = logging.getLogger("rmt.ops.attestation")

FORMAT_VERSION = 1
SIGNATURE_ALGORITHM = "HMAC-SHA256"


def canonicalize(payload: dict) -> bytes:
    """Deterministic byte serialization used for both signing and verifying.

    Sorted keys + compact separators so the same logical payload always
    produces the same bytes, on the signer and on an independent verifier.
    """
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )


def sign(payload_bytes: bytes, signing_key: str) -> str:
    """Hex-encoded HMAC-SHA256 digest of ``payload_bytes`` under ``signing_key``."""
    return hmac.new(
        signing_key.encode("utf-8"), payload_bytes, hashlib.sha256
    ).hexdigest()


def verify_signature(payload_bytes: bytes, signing_key: str, signature: str) -> bool:
    """Constant-time check that ``signature`` matches ``payload_bytes``."""
    expected = sign(payload_bytes, signing_key)
    return hmac.compare_digest(expected, signature)


def _build_payload(*, action_id, approval_id, execution_id) -> dict:
    """The unsigned envelope: format version, generation time, resolved
    identifiers, and the correlated Govern -> Verify chain. Never raises --
    ``evidence_chain()`` is already fail-open end-to-end."""
    chain = evidence_chain(
        action_id=action_id, approval_id=approval_id, execution_id=execution_id
    )
    return {
        "format_version": FORMAT_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "chain": chain,
    }


def export_bundle(
    *, action_id=None, approval_id=None, execution_id=None, signing_key: str
) -> dict:
    """Assemble and sign one evidence-export bundle.

    Returns the full envelope plus a ``signature`` block. Callers are
    responsible for checking ``signing_key`` truthiness before calling this
    (fail closed at the route, not here) -- an empty key still signs, so the
    503-on-missing-secret decision belongs one layer up where the operator
    surface is defined.
    """
    payload = _build_payload(
        action_id=action_id, approval_id=approval_id, execution_id=execution_id
    )
    payload_bytes = canonicalize(payload)
    return {
        **payload,
        "signature": {
            "algorithm": SIGNATURE_ALGORITHM,
            "value": sign(payload_bytes, signing_key),
        },
    }


def verify_bundle(bundle: dict, signing_key: str) -> bool:
    """Recompute the signature over the bundle's own payload fields and
    compare. Used by the offline verifier tool; also usable in tests.

    Returns ``False`` (never raises) for a malformed bundle -- missing
    ``signature``/``value``, or a payload that doesn't canonicalize -- so a
    tampered or corrupt bundle always reports as invalid rather than crashing
    the verifier.
    """
    try:
        signature_block = bundle.get("signature")
        if not isinstance(signature_block, dict):
            return False
        signature = signature_block.get("value")
        if not signature:
            return False
        payload = {k: v for k, v in bundle.items() if k != "signature"}
        payload_bytes = canonicalize(payload)
        return verify_signature(payload_bytes, signing_key, signature)
    except Exception:  # noqa: BLE001 -- verifier must never crash on bad input
        logger.warning("attestation.verify_bundle: malformed bundle")
        return False
