#!/usr/bin/env python3
"""T0-1 -- one-shot migration of the six JSON evidence stores into the shared
SQLite database (``data/governance_evidence.db``), and its reverse.

Forward (default):
    for each ``app/core/intelligence/**/<name>.json`` that exists, insert every
    record into its table in insertion order, then rename the file to
    ``<name>.json.migrated``. Idempotent: a table that already holds rows is
    skipped unless ``--force`` (which clears the table first).

Reverse (``--reverse``):
    dump each table back to ``<name>.json`` in the exact prior on-disk format
    (a JSON list, ``indent=4``) -- byte-comparable to a pre-migration backup.

Run ONCE on the host, AFTER ``scripts/rmt-evidence-backup.sh`` (E5). Rollback =
``--reverse`` + revert the T0-1 commit; the JSON backend stays in the code for
exactly this.
"""
import argparse
import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]


def _stores(db: Path, base: Path | None = None):
    from app.core.intelligence.actions.approval_storage import (
        ApprovalHoldStorage,
        ApprovalRecordStorage,
    )
    from app.core.intelligence.actions.authorization_storage import (
        AuthorizationStorage,
    )
    from app.core.intelligence.execution.trace_storage import (
        ExecutionTraceStorage,
    )
    from app.core.intelligence.execution.storage import ExecutionAuditStorage
    from app.core.intelligence.verification.storage import VerificationStorage

    ci = base or (BACKEND / "app" / "core" / "intelligence")
    specs = [
        ("approval_holds", ci / "actions" / "approval_holds.json",
         ApprovalHoldStorage),
        ("approval_records", ci / "actions" / "approval_records.json",
         ApprovalRecordStorage),
        ("authorizations", ci / "actions" / "authorizations.json",
         AuthorizationStorage),
        ("traces", ci / "execution" / "traces.json", ExecutionTraceStorage),
        ("audit", ci / "execution" / "audit.json", ExecutionAuditStorage),
        ("verifications", ci / "verification" / "verifications.json",
         VerificationStorage),
    ]
    return [(name, path, cls(file_path=db)) for name, path, cls in specs]


def forward(db: Path, force: bool, base: Path | None = None) -> int:
    changed = 0
    for name, json_path, store in _stores(db, base):
        existing = store.get_all()
        if existing and not force:
            print(f"  {name}: {len(existing)} rows already -- skip "
                  f"(use --force to overwrite)")
            continue
        if not json_path.exists():
            print(f"  {name}: no {json_path.name} -- nothing to migrate")
            continue
        if existing and force:
            store._replace_records([])
        data = json.loads(json_path.read_text())
        for item in data:
            store.save(store._model.model_validate(item))
        json_path.rename(json_path.with_suffix(".json.migrated"))
        print(f"  {name}: migrated {len(data)} record(s); "
              f"{json_path.name} -> {json_path.name}.migrated")
        changed += 1
    return changed


def reverse(db: Path, base: Path | None = None) -> int:
    changed = 0
    for name, json_path, store in _stores(db, base):
        records = store.get_all()
        if not records:
            print(f"  {name}: table empty -- no {json_path.name} written")
            continue
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(
            json.dumps(
                [r.model_dump(mode="json") for r in records], indent=4
            )
        )
        print(f"  {name}: wrote {len(records)} record(s) -> {json_path.name}")
        changed += 1
    return changed


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--reverse", action="store_true",
                    help="dump SQLite tables back to JSON files")
    ap.add_argument("--force", action="store_true",
                    help="overwrite a non-empty table on a forward migration")
    ap.add_argument("--db",
                    default=str(BACKEND / "data" / "governance_evidence.db"),
                    help="path to governance_evidence.db")
    args = ap.parse_args()

    sys.path.insert(0, str(BACKEND))
    db = Path(args.db)
    print(f"evidence db: {db}")
    n = reverse(db) if args.reverse else forward(db, args.force)
    print(f"done -- {n} store(s) {'reversed' if args.reverse else 'migrated'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
