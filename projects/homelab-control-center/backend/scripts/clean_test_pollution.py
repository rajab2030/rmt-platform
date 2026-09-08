"""One-off: remove `test_auth.py` `/execute?target=x` pollution from the Core
evidence stores.

Background. Before 2026-09-08, `app/ops/testing/test_auth.py` had no store
isolation: its "accepts valid token" cases POST `/execute?target=x` with a real
token, which reached the real Docker adapter (available on this host), 404'd on
the non-existent container `x`, and wrote a `failed` trace + audit record (and,
after E3, an `adapter_execution_failed` verification record) into the real JSON
stores. `test_auth.py` now isolates those stores; this script removes the
records already written.

**Run only while the service is stopped** -- otherwise the running process holds
these stores in memory and its next `save()` re-persists the pollution:

    sudo systemctl stop rmt-control-center.service
    .venv/bin/python scripts/clean_test_pollution.py            # dry run
    .venv/bin/python scripts/clean_test_pollution.py --apply
    sudo systemctl start rmt-control-center.service

A record is pollution iff its reason/message contains
`No such container: x` (the bogus test target). Real operations never target a
container literally named `x`.
"""
import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
STORES = [
    BACKEND / "app/core/intelligence/execution/traces.json",
    BACKEND / "app/core/intelligence/execution/audit.json",
    BACKEND / "app/core/intelligence/verification/verifications.json",
]
MARKER = 'No such container: x'


def is_pollution(record: dict) -> bool:
    return MARKER in json.dumps(record)


def main() -> int:
    apply = "--apply" in sys.argv[1:]
    total = 0
    for path in STORES:
        if not path.exists():
            continue
        records = json.loads(path.read_text())
        keep = [r for r in records if not is_pollution(r)]
        removed = len(records) - len(keep)
        total += removed
        print(f"{path.name}: {len(records)} -> {len(keep)}  (-{removed})")
        if apply and removed:
            path.write_text(json.dumps(keep, indent=4))
    print(f"\n{'REMOVED' if apply else 'WOULD REMOVE'} {total} polluted record(s).")
    if not apply:
        print("Re-run with --apply (service stopped) to write the changes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
