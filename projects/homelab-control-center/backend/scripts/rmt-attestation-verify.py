#!/usr/bin/env python3
"""RMT-CAP-11 (P-C) -- offline verification for a signed evidence-export bundle.

Stdlib only (no venv, no FastAPI/pydantic, no network call, no running
service) so it runs standalone -- including in an external auditor's own
tooling -- against a bundle produced by ``GET /ops/evidence/export``.

The signature/canonicalization logic here is intentionally a small, direct
duplication of ``app/ops/attestation.py`` (same pattern ``rmt_evidence_verify.py``
uses for the evidence-store schema) rather than an import, so this script has
zero dependency on the application package or its virtualenv.

Usage:
    rmt-attestation-verify.py <bundle.json> --key-file <path>
    rmt-attestation-verify.py <bundle.json> --key <secret>
    RMT_ATTESTATION_SIGNING_KEY=<secret> rmt-attestation-verify.py <bundle.json>

Exit 0 + "VALID"     -- signature matches the bundle's own payload.
Exit 1 + "INVALID"   -- signature does not match (tampered, wrong key, or a
                        genuinely corrupt bundle).
Exit 2 + "MALFORMED" -- not parseable JSON, or missing required fields; a
                        distinct outcome from a bad signature, never a
                        traceback.
"""
import argparse
import hashlib
import hmac
import json
import os
import sys


def canonicalize(payload: dict) -> bytes:
    """Must match app/ops/attestation.py::canonicalize() exactly."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )


def verify(bundle: dict, signing_key: str) -> bool:
    signature_block = bundle.get("signature")
    if not isinstance(signature_block, dict):
        return False
    signature = signature_block.get("value")
    if not signature:
        return False
    payload = {k: v for k, v in bundle.items() if k != "signature"}
    payload_bytes = canonicalize(payload)
    expected = hmac.new(
        signing_key.encode("utf-8"), payload_bytes, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


def _resolve_key(args) -> str | None:
    if args.key:
        return args.key
    if args.key_file:
        try:
            with open(args.key_file) as f:
                return f.read().strip() or None
        except OSError as exc:
            print(f"MALFORMED: could not read key file: {exc}", file=sys.stderr)
            return None
    env_key = os.environ.get("RMT_ATTESTATION_SIGNING_KEY", "").strip()
    return env_key or None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", help="path to the evidence-export bundle JSON")
    key_group = parser.add_mutually_exclusive_group()
    key_group.add_argument("--key", help="the HMAC signing secret")
    key_group.add_argument("--key-file", help="path to a file containing the secret")
    args = parser.parse_args()

    signing_key = _resolve_key(args)
    if not signing_key:
        print(
            "MALFORMED: no signing key given (--key / --key-file / "
            "RMT_ATTESTATION_SIGNING_KEY)",
            file=sys.stderr,
        )
        return 2

    try:
        with open(args.bundle) as f:
            bundle = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"MALFORMED: {exc}", file=sys.stderr)
        return 2

    if not isinstance(bundle, dict) or "format_version" not in bundle:
        print("MALFORMED: not a recognizable evidence-export bundle", file=sys.stderr)
        return 2

    if verify(bundle, signing_key):
        print("VALID")
        return 0

    print("INVALID")
    return 1


if __name__ == "__main__":
    sys.exit(main())
