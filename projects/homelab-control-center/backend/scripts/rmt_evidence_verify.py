#!/usr/bin/env python3
"""RMT-PROD P1 (E5) -- integrity check for an RMT evidence set.

Stdlib only (no venv, no pydantic) so it runs against a restored backup on a
bare host. Point it at either:

  * a live backend:  .../backend            (auto-finds data/ + app/core/intelligence)
  * a backup dir:    .../rmt-evidence/<ts>  (governance_evidence.db and/or stores/,
                                            archives/, observability.db)

Checks, in order:
  1. governance_evidence.db (T0-1): opens read-only; every one of the six
     evidence tables is present and countable
  1b. legacy: any residual ``*.json`` evidence store parses as a JSON list
  2. every ``*.archive.jsonl`` line parses as a JSON object (E4 archives)
  3. observability.db (if present) opens and intelligence_memory is queryable
  4. cross-store consistency (advisory, never fatal), read from the db when
     present else the JSON stores:
       - every authorization.approval_id resolves to an approval record
       - every terminal approval record's hold (if present) is not still 'pending'

Exit 0 = evidence set is structurally sound. Exit 1 = corruption (a table/store
or an archive line failed to parse, or a DB is unreadable). Cross-store
advisories print as WARN and do not change the exit code.
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

# governance_evidence.db tables (T0-1) and the JSON-store name each replaced
EVIDENCE_TABLES = {
    "traces": "traces.json",
    "audit": "audit.json",
    "verifications": "verifications.json",
    "authorizations": "authorizations.json",
    "approval_records": "approval_records.json",
    "approval_holds": "approval_holds.json",
}


def _resolve(root: Path):
    """Return (stores_dir_or_None, [archive_dirs], obs_db_or_None,
    gov_db_or_None)."""
    if (root / "stores").is_dir() or (root / "governance_evidence.db").exists():
        # backup layout
        stores = root / "stores" if (root / "stores").is_dir() else None
        archives = [root / "archives"] if (root / "archives").is_dir() else []
        obs = root / "observability.db"
        gov = root / "governance_evidence.db"
        return (stores, archives,
                obs if obs.exists() else None,
                gov if gov.exists() else None)
    ci = root / "app" / "core" / "intelligence"  # live backend layout
    data = root / "data"
    if ci.is_dir() or data.is_dir():
        obs = data / "observability.db"
        gov = data / "governance_evidence.db"
        return (ci if ci.is_dir() else None,
                [d for d in (ci, data) if d.is_dir()],
                obs if obs.exists() else None,
                gov if gov.exists() else None)
    # a bare directory of json files
    return root, [root], None, None


def _find(dirs, pattern: str):
    out = []
    for d in dirs or []:
        if d:
            out.extend(sorted(d.rglob(pattern)))
    return out


def _read_gov_db(gov_db: Path):
    """Return ({name.json: [records]}, fatal_int). Opens read-only; a missing
    table or unreadable payload is fatal."""
    stores, fatal = {}, 0
    try:
        con = sqlite3.connect(f"file:{gov_db}?mode=ro", uri=True)
    except Exception as e:
        print(f"FAIL  governance_evidence.db    cannot open: {e}")
        return stores, 1
    try:
        present = {
            r[0] for r in con.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        for table, json_name in EVIDENCE_TABLES.items():
            if table not in present:
                fatal = 1
                print(f"FAIL  governance_evidence.db    missing table {table!r}")
                continue
            try:
                rows = con.execute(
                    f'SELECT payload FROM "{table}" ORDER BY id'
                ).fetchall()
                recs = [json.loads(r[0]) for r in rows]
                stores[json_name] = recs
                print(f"OK    {table:26} {len(recs)} row(s)")
            except Exception as e:
                fatal = 1
                print(f"FAIL  {table:26} {e}")
    finally:
        con.close()
    return stores, fatal


def main(argv):
    root = Path(argv[1] if len(argv) > 1 else ".").resolve()
    if not root.exists():
        print(f"FAIL  path does not exist: {root}")
        return 1

    stores_dir, archive_dirs, obs_db, gov_db = _resolve(root)
    print(f"evidence root: {root}")
    fatal = 0
    checked_stores = {}

    # 1. governance_evidence.db (T0-1)
    if gov_db:
        db_stores, f = _read_gov_db(gov_db)
        checked_stores.update(db_stores)
        fatal |= f
    else:
        print("WARN  governance_evidence.db    not present "
              "(pre-T0-1 backup, or JSON stores only)")

    # 1b. residual / legacy JSON stores
    store_files = _find([stores_dir], "*.json")
    store_files = [f for f in store_files if f.name in STORE_NAMES] or store_files
    for f in store_files:
        try:
            data = json.loads(f.read_text())
            assert isinstance(data, list)
            checked_stores.setdefault(f.name, data)
            print(f"OK    {f.name:26} {len(data)} record(s) (JSON)")
        except Exception as e:
            fatal = 1
            print(f"FAIL  {f.name:26} {e}")
    if not gov_db and not store_files:
        fatal = 1
        print("FAIL  no governance_evidence.db and no JSON evidence stores")

    # 2. E4 archive lines
    for f in _find(archive_dirs, "*.archive.jsonl"):
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
    if obs_db:
        try:
            con = sqlite3.connect(f"file:{obs_db}?mode=ro", uri=True)
            n = con.execute(
                "SELECT count(*) FROM intelligence_memory"
            ).fetchone()[0]
            con.close()
            print(f"OK    observability.db          "
                  f"intelligence_memory: {n} row(s)")
        except Exception as e:
            fatal = 1
            print(f"FAIL  observability.db          {e}")
    else:
        print("WARN  observability.db          not present")

    # 4. cross-store advisories (never fatal)
    recs = {r.get("approval_id"): r
            for r in checked_stores.get("approval_records.json", [])}
    holds = {h.get("approval_id"): h
             for h in checked_stores.get("approval_holds.json", [])}
    for a in checked_stores.get("authorizations.json", []):
        aid = a.get("approval_id")
        if aid and aid not in recs:
            print(f"WARN  authorization {a.get('authorization_id','?')[:8]} -> "
                  f"no approval record ({aid[:8]})")
    for aid, r in recs.items():
        if r.get("decision") in ("approved", "rejected"):
            h = holds.get(aid)
            if h and h.get("status") == "pending":
                print(f"WARN  hold {aid[:8]} still 'pending' on disk but "
                      f"record is {r.get('decision')}")

    print("RESULT: " + ("FAIL (structural corruption)" if fatal else "OK"))
    return fatal


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
