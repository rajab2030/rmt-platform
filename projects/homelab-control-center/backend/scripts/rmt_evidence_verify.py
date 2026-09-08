#!/usr/bin/env python3
"""RMT-PROD P1 (E5) -- integrity check for an RMT evidence set.

Stdlib only (no venv, no pydantic) so it runs against a restored backup on a
bare host. Point it at either:

  * a live backend:  .../backend            (auto-finds app/core/intelligence + data)
  * a backup dir:    .../rmt-evidence/<ts>  (expects stores/ archives/ observability.db)

Checks, in order:
  1. every *.json evidence store parses as a JSON list
  2. every *.archive.jsonl line parses as a JSON object (E4 archives)
  3. observability.db (if present) opens and intelligence_memory is queryable
  4. cross-store consistency (advisory, never fatal):
       - every authorization.approval_id resolves to an approval record
       - every terminal approval record's hold (if present) is not still 'pending'

Exit 0 = evidence set is structurally sound. Exit 1 = corruption (a store or an
archive line failed to parse, or the DB is unreadable). Cross-store advisories
print as WARN and do not change the exit code.
"""
import json
import sqlite3
import sys
from pathlib import Path

STORE_NAMES = [
    "traces.json",
    "audit.json",
    "verifications.json",
    "authorizations.json",
    "approval_records.json",
    "approval_holds.json",
]


def _resolve(root: Path):
    """Return (stores_dir_or_None, archives_dir_or_None, db_path_or_None)."""
    if (root / "stores").is_dir():  # backup layout
        return (
            root / "stores",
            root / "archives" if (root / "archives").is_dir() else None,
            root / "observability.db" if (root / "observability.db").exists() else None,
        )
    ci = root / "app" / "core" / "intelligence"  # live backend layout
    if ci.is_dir():
        db = root / "data" / "observability.db"
        return ci, ci, db if db.exists() else None
    # a bare directory of json files
    return root, root, None


def _find(dirp: Path, pattern: str):
    return sorted(dirp.rglob(pattern)) if dirp else []


def main(argv):
    root = Path(argv[1] if len(argv) > 1 else ".").resolve()
    if not root.exists():
        print(f"FAIL  path does not exist: {root}")
        return 1

    stores_dir, archives_dir, db_path = _resolve(root)
    print(f"evidence root: {root}")
    fatal = 0
    checked_stores = {}

    # 1. JSON stores
    store_files = _find(stores_dir, "*.json")
    store_files = [f for f in store_files if f.name in STORE_NAMES] or store_files
    for f in store_files:
        try:
            data = json.loads(f.read_text())
            assert isinstance(data, list)
            checked_stores[f.name] = data
            print(f"OK    {f.name:26} {len(data)} record(s)")
        except Exception as e:
            fatal = 1
            print(f"FAIL  {f.name:26} {e}")
    for name in STORE_NAMES:
        if name not in {f.name for f in store_files}:
            print(f"WARN  {name:26} not present")

    # 2. E4 archive lines
    for f in _find(archives_dir, "*.archive.jsonl"):
        bad = 0
        for i, line in enumerate(f.read_text().splitlines(), 1):
            if not line.strip():
                continue
            try:
                json.loads(line)
            except Exception as e:
                bad += 1
                fatal = 1
                print(f"FAIL  {f.name}:{i} {e}")
        if not bad:
            n = sum(1 for ln in f.read_text().splitlines() if ln.strip())
            print(f"OK    {f.name:26} {n} archived line(s)")

    # 3. observability.db
    if db_path:
        try:
            con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
            n = con.execute("SELECT count(*) FROM intelligence_memory").fetchone()[0]
            con.close()
            print(f"OK    observability.db          intelligence_memory: {n} row(s)")
        except Exception as e:
            fatal = 1
            print(f"FAIL  observability.db          {e}")
    else:
        print("WARN  observability.db          not present")

    # 4. cross-store advisories (never fatal)
    recs = {r.get("approval_id"): r for r in checked_stores.get("approval_records.json", [])}
    holds = {h.get("approval_id"): h for h in checked_stores.get("approval_holds.json", [])}
    for a in checked_stores.get("authorizations.json", []):
        aid = a.get("approval_id")
        if aid and aid not in recs:
            print(f"WARN  authorization {a.get('authorization_id','?')[:8]} -> no approval record ({aid[:8]})")
    for aid, r in recs.items():
        if r.get("decision") in ("approved", "rejected"):
            h = holds.get(aid)
            if h and h.get("status") == "pending":
                print(f"WARN  hold {aid[:8]} still 'pending' on disk but record is {r.get('decision')}")

    print("RESULT: " + ("FAIL (structural corruption)" if fatal else "OK"))
    return fatal


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
