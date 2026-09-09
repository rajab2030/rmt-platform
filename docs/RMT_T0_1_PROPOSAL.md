# RMT — T0-1 Evidence Substrate: JSON → SQLite — Proposal

**Status:** APPROVED 2026-09-09 — **Option A authorized** by the owner: the
bounded internal change to `app/core/intelligence/durable_store.py` (persistence
mechanism only; method signatures, return types, pydantic models, and all
governance logic unchanged) plus the additive `ApprovalHoldStorage.update()`
are authorized on the same footing as the E1 atomic-write hardening. No C08. No
reopening of C01–C07. Implementation proceeds per §9.
**Classification:** above-Core substrate; one owner-authorized bounded edit
under `app/core/` (§2, Option A).

Governing refs: `docs/RMT_ABOVE_CORE_ROADMAP.md` §5 (T0-1) + §9, `AGENTS.md`
§§8–11, `STEWARD.md` §4, `docs/RMT_PRODUCTION_READINESS.md` §5 (W2),
`docs/operations/RMT_EVIDENCE_RECOVERY.md` (E5).

---

## 0. Recon findings (verified against the repository, 2026-09-09)

| # | Finding |
|---|---|
| R1 | **`app/core/intelligence/durable_store.py`** — `DurableStore` is a JSON-file store. `save()` appends to an in-memory `self._records` list **and rewrites the entire file** (atomic `.tmp` + `fsync` + `os.replace`, the authorized E1 hardening). Cost is **O(n) per append**; file grows unbounded. Public surface: `__init__(file_path=None, model=…)`, `save(record)`, `get_all()`. `file_path=None` ⇒ pure in-memory (every isolated test instance relies on this). |
| R2 | **Six on-disk singletons**, all `Path(__file__).parent / "*.json"` (beside the code, **git-ignored**): `approval_holds.json`, `approval_records.json`, `authorizations.json` (`app/core/intelligence/actions/`), `traces.json`, `audit.json` (`app/core/intelligence/execution/`), `verifications.json` (`app/core/intelligence/verification/`). Live sizes today ≈ 7–56 KB each. |
| R3 | **Per-subclass API beyond the base:** `ApprovalHoldStorage.get_by_id`, `ApprovalRecordStorage.get_by_id` **+ `.update(approval_id, **fields)`**, `AuthorizationStorage.get_by_id`, `VerificationStorage.get_by_execution_id`. `get_by_*` return the **first** match in insertion order. `update()` is the only mutation path — `model_copy(update=…)` then re-persist. |
| R4 | **Two above-Core modules reach into `DurableStore` internals:** `app/ops/retention.py` (E4) uses `store._file_path`, sets `store._records = keep`, calls `store._persist()`; `app/ops/reconcile.py` (E2) mutates `hold.status` on objects from `get_all()` then calls `hold_storage._persist()` (the hold store has no public `update()`). Any backend swap must keep these working — they are in scope for this change. |
| R5 | **Retention (E4)** already exists and is wired into startup (`archive_aged_evidence()` in `app/main.py` lifespan, after `reconcile_governance_stores()`): records older than `RMT_EVIDENCE_RETENTION_DAYS` (default 90; `<=0` disables) move to an append-only `<name>.archive.jsonl` beside the store. **Reconciliation (E2) + authorization audit (E6)** also already exist (`app/ops/reconcile.py`). T0-1's job is to make E4 a bounded `DELETE`, make E2's write a real per-row update, and let E6 run inside one transaction — not to invent these. |
| R6 | **Contract tests:** `test_durable_store_atomic.py` (4: round-trip **asserts the JSON file shape**, interrupted-write leaves prior file intact, stale `.tmp` discarded, `file_path=None` in-memory); `test_durable_stores.py` (durability via re-instantiation from `tmp_path`, + approval-record persistence). `test_retention.py`, `test_reconcile.py`. Full backend suite: **389 passed** (353 `test_` functions; `scripts/ci.sh`). |
| R7 | **E5 backup** (`backend/scripts/rmt-evidence-backup.sh`) copies `app/core/intelligence/**/*.json` + `*.archive.jsonl` + a `VACUUM INTO` snapshot of `data/observability.db`. It must learn the new DB file (§6). |

---

## 1. Objective & Definition of Done (from the roadmap)

Replace the six file-backed JSON stores with a **single SQLite-backed store**
behind the **unchanged `DurableStore` + subclass interface**: O(1) appends,
bounded file growth, transactional reconciliation.

**DoD:**
1. All backend tests green against SQLite (`scripts/ci.sh`), including a
   rewritten `test_durable_store_atomic.py` and new SQLite-backend tests.
2. One-shot migration of existing JSON records into SQLite; **reversible**
   (a documented dump-back-to-JSON path).
3. Retention/rotation closes **E4** as a bounded `DELETE` (+ unchanged
   `.archive.jsonl`).
4. Startup integrity check across hold ↔ record ↔ authorization runs in **one
   transaction** — finishes **E6**.
5. A hard-kill restart test: kill mid-write, restart, evidence intact and the
   three stores mutually consistent.

---

## 2. The freeze-boundary decision (owner call)

T0-1 edits **`app/core/intelligence/durable_store.py`** — a file under
`app/core/`. The roadmap classes it "above-Core substrate, interface
unchanged," citing the precedent that this class **already** took an
owner-authorized internal change (E1 atomic writes) with **no** API / format /
behaviour change for any caller. T0-1 asks for the same kind of change: swap the
persistence mechanism, keep the interface.

**What this proposal will and will not touch in Core:**
- **Will:** the *body* of `DurableStore._load` / `_persist` / `__init__`
  (persistence mechanism), and **additively** a public
  `ApprovalHoldStorage.update()` mirroring the existing
  `ApprovalRecordStorage.update()`.
- **Will not:** the `DurableStore` / subclass method **signatures** and return
  types; the pydantic record models; the governed lifecycle; any
  policy / risk / approval / authorization / verification logic; the meaning of
  any stored field.

**Options:**
- **A — authorize the bounded internal change** (recommended): treat it as E1
  did — a substrate hardening with an explicit, recorded authorization in this
  doc and `HANDOFF.md`. Cleanest; matches the roadmap's own classification.
- **B — above-Core indirection:** leave `durable_store.py` untouched; add a
  SQLite backend in `app/ops/` and reassign the six module singletons at
  startup. Avoids the Core edit but adds a boot-time monkeypatch layer and two
  code paths to keep in sync; the singletons are still *defined* in
  `app/core/`, so the seam is awkward. Not recommended.
- **C — accept-and-record, do nothing:** keep JSON; document O(n) growth as an
  accepted limitation. Defers every Tier 2 domain that needs evidence volume.

**This proposal assumes Option A** for the rest of the design. If the owner
prefers B or C, §§3–7 change accordingly.

---

## 3. Design (Option A)

### 3.1 Backend abstraction
`DurableStore.__init__` gains an internal branch on the path it is given:
- **`file_path` ends `.db` (or a new `sqlite_path=` kwarg):** SQLite backend.
- **`file_path` is a `.json` path:** the current JSON backend, unchanged
  (kept during migration + as the dump-back target).
- **`file_path is None`:** **unchanged** pure in-memory list. Every isolated
  test instance keeps byte-identical behaviour; this is deliberate risk
  reduction.

The six singletons switch to one shared DB file
**`data/governance_evidence.db`** (under the already-git-ignored `data/`),
one table per record type:

```
CREATE TABLE <store> (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    key        TEXT,           -- approval_id / authorization_id / execution_id, NULL if none
    created_at TEXT,           -- record.created_at when present (for E4)
    payload    TEXT NOT NULL   -- json.dumps(record.model_dump(mode="json"))
);
CREATE INDEX <store>_key_idx        ON <store>(key);
CREATE INDEX <store>_created_at_idx ON <store>(created_at);
```

Stored `payload` is **exactly** today's per-record JSON — the "on-the-wire
record schema" the DoD preserves. No column-per-field normalisation.

### 3.2 Operation mapping
| API | SQLite |
|---|---|
| `save(r)` | one `INSERT` — **O(1)**, one transaction |
| `get_all()` | `SELECT payload FROM <store> ORDER BY id` → `model_validate(json.loads(p))` |
| `get_by_id(k)` / `get_by_execution_id(k)` | `SELECT payload … WHERE key=? ORDER BY id LIMIT 1` (first-match, as today) |
| `ApprovalRecordStorage.update(id, **f)` | read row → `model_copy(update=f)` → `UPDATE … WHERE id=?` |
| `ApprovalHoldStorage.update(id, **f)` | **new**, same shape — replaces `reconcile.py`'s `_persist()` poke |

`get_all()` still returns the full list — semantics preserved. (Streaming /
pagination is explicitly **out of scope**; it is a later item once a Tier 2
domain needs it.)

### 3.3 Atomicity / durability
SQLite in WAL mode gives per-`INSERT`/`UPDATE` atomic commit and crash
recovery natively — the E1 guarantee ("a reader never sees a partial write; an
interrupted write leaves the last good state intact") is now the database's,
not a `.tmp`+`os.replace` dance. `test_durable_store_atomic.py` is rewritten to
assert it against SQLite (kill mid-transaction → last commit intact; no
torn read).

---

## 4. Scope / boundary / files

**Core (Option A authorization):**
- `app/core/intelligence/durable_store.py` — backend swap (body only).
- `app/core/intelligence/actions/approval_storage.py` — add
  `ApprovalHoldStorage.update()`; point the two singletons at the DB.
- `app/core/intelligence/actions/authorization_storage.py`,
  `app/core/intelligence/execution/trace_storage.py`,
  `app/core/intelligence/execution/storage.py`,
  `app/core/intelligence/verification/storage.py` — point each singleton at the
  shared DB file (one-line change each).

**Above-Core:**
- `app/ops/retention.py` — archive via `DELETE FROM <store> WHERE id IN (…)`
  after the unchanged `.archive.jsonl` append; drop the `_records = keep`
  reassignment.
- `app/ops/reconcile.py` — E2 calls the new `ApprovalHoldStorage.update()`;
  E6 audit wrapped in one read transaction.
- `app/main.py` — create/migrate the DB in `lifespan()` (next to the SQLite
  init added for the CI fix).
- `backend/scripts/rmt-evidence-*` + `docs/operations/RMT_EVIDENCE_RECOVERY.md`
  — back up / restore / verify `governance_evidence.db` (§6).
- `backend/scripts/rmt-migrate-evidence.py` (new) — one-shot JSON → SQLite,
  and `--reverse` for dump-back.

**Tests:** rewrite `test_durable_store_atomic.py`; new
`test_durable_store_sqlite.py` (backend contract: O(1) insert, first-match
`get_by_id`, `update`, crash-consistency); extend `test_retention.py` /
`test_reconcile.py` for the DB path; a `test_migrate_evidence.py`.

**Not touched:** every method signature/return type; the pydantic models; the
governed lifecycle and all governance logic; `data/observability.db`
(`container_metrics` / `intelligence_memory` stay where they are).

---

## 5. Migration & reversibility

- `rmt-migrate-evidence.py` reads each live `*.json`, inserts every record into
  its table (preserving order → `id` order), and renames the JSON to
  `*.json.migrated`. Idempotent (skips a table that already has rows unless
  `--force`).
- `--reverse` writes each table back out to `*.json` in the exact current
  format (list, `indent=4`) and is byte-comparable to a pre-migration backup.
- Run once, by the owner, on the live host after an E5 backup. Documented in
  `RMT_EVIDENCE_RECOVERY.md`.
- Rollback = `--reverse` + revert the commit; the JSON backend stays in the
  code for exactly this reason.

---

## 6. E4 / E5 / E6 impact

- **E4 (retention):** archive path unchanged (`.archive.jsonl`); the trim
  becomes a bounded `DELETE`. Closes E4's "O(n) rewrite" note for good.
- **E5 (backup):** `rmt-evidence-backup.sh` swaps the six-JSON copy for a
  `VACUUM INTO` of `governance_evidence.db` (hot-safe, same as it already does
  for `observability.db`); `rmt_evidence_verify.py` checks row counts per
  table. `.archive.jsonl` files still captured.
- **E6 (integrity):** `audit_authorizations()` runs against the DB inside one
  transaction — a consistent snapshot of holds + records + authorizations
  instead of three independent file reads. Finishes E6.

---

## 7. Validation plan

1. `scripts/ci.sh` green (throwaway venv, ruff, full suite) — the CI gate.
2. New `test_durable_store_sqlite.py`: `save` is one INSERT (row count / no
   full-table rewrite); `get_by_id` first-match order; `update` in place;
   `file_path=None` still in-memory; WAL crash-consistency (kill a child
   mid-transaction, reopen, assert last commit present and no torn row).
3. `test_migrate_evidence.py`: JSON → SQLite → `--reverse` round-trips
   byte-for-byte against a captured sample.
4. Manual hard-kill drill on a scratch instance: `kill -9` during a governed
   action, restart, `reconcile_governance_stores()` reports consistent,
   evidence chain reconstructs.
5. Diff review: no signature/model/logic changes; Core diff confined to the
   files in §4.

---

## 8. Risks

| Risk | Mitigation |
|---|---|
| A behaviour change sneaks in via the backend swap | `file_path=None` path left as-is; `payload` is verbatim `model_dump`; contract tests assert first-match order + `update` semantics. |
| Concurrency: the collector task + a request writing at once | One connection per store, WAL, short `BUSY_TIMEOUT`; the governed path is already single-writer in practice. Documented, tested with a concurrent-append test. |
| Migration data loss | Mandatory E5 backup first; JSON renamed not deleted; `--reverse` proven in CI. |
| E5 restore of an old JSON-era backup after the swap | `rmt-evidence-restore.sh` detects format and runs `rmt-migrate-evidence.py` on the way in. |
| Scope creep into query/streaming API | Explicit non-goal (§9). |

---

## 9. Sequencing & non-goals

**Sequence:** (1) SQLite backend + `file_path` branch + contract tests;
(2) point the six singletons at the DB, `lifespan()` create/migrate;
(3) `retention.py` / `reconcile.py` to the DB path; (4) migration script +
reverse; (5) E5 script + recovery doc; (6) `HANDOFF.md` note,
`RMT_PRODUCTION_READINESS.md` W2 + `RMT_ABOVE_CORE_ROADMAP.md` ticks;
(7) `scripts/ci.sh` green, push, CI green.

**Non-goals:** a query / filter / pagination API; streaming `get_all()`;
moving `container_metrics` / `intelligence_memory`; any change to the JSON
record schema; ORM / migration framework (hand-rolled `CREATE TABLE IF NOT
EXISTS` + a tiny migration script, matching the existing
`observability/storage.py` style); multi-process writers.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

https://claude.ai/code/session_01P5af6Eq9D3zWrztvPegANU
