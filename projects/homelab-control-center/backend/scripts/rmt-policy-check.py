#!/usr/bin/env python3
"""RMT-CAP-14 (P-A) -- check a homelab remediation policy file before a restart.

Runs exactly the validator the backend runs at startup
(``app/homelab/policy_config.py``) without starting the service. An invalid
file would stop the backend from starting (proposal decision D1), so run this
on every edit, before ``systemctl restart``.

Unlike ``rmt-attestation-verify.py`` this is not stdlib-only: the rules read the
component-context registry and the dependency map from the application
package, so run it with the backend venv:

    .venv/bin/python scripts/rmt-policy-check.py /etc/rmt-platform/remediation_policy.toml

The dependency rule uses ``RMT_HOMELAB_DEPENDENCIES`` from *this* shell's
environment. If the live unit sets it, pass the same value:

    RMT_HOMELAB_DEPENDENCIES='web:db' .venv/bin/python scripts/rmt-policy-check.py FILE

Exit 0 + "VALID"   -- the backend would load this policy.
Exit 1 + "INVALID" -- one line per rule violation; the backend would refuse
                      to start with this file.
"""
import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.homelab.policy_config import PolicyConfigError, load_policy_file  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("policy_file")
    args = parser.parse_args(argv)
    logging.disable(logging.CRITICAL)

    try:
        policy, source = load_policy_file(args.policy_file)
    except PolicyConfigError as exc:
        print(f"INVALID {exc.path}")
        for err in exc.errors:
            print(f"  - {err}")
        return 1

    print(f"VALID {source.path}")
    print(f"  sha256: {source.sha256}")
    if not policy:
        print("  WARNING: no components -- the operational loop will never remediate")
    for name, entry in policy.items():
        triggers = ",".join(sorted(s.value for s in entry["remediate_on"]))
        print(
            f"  - {name}: {entry['action_type'].value} on {triggers} "
            f"-> expect {entry['expected_state']} (approval required)"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
