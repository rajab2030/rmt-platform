# RMT Evidence — Backup & Recovery Runbook

RMT-PROD **P1 / E5**. Backup and restore for the RMT **governance evidence** —
the durable record of every governed action (who authorised it, was it verified,
what did the platform learn). This is separate from the homelab Docker-stack
recovery (`docs/recovery/RECOVERY_RUNBOOK.md`), which does not cover these files.

Above-Core / operational. No `app/core/**` dependency.

---

## 0. What is covered

| Artifact | Path | Why |
|---|---|---|
| 6 durable evidence stores | `backend/data/governance_evidence.db` (one table each — **T0-1**; was six `*.json` under `app/core/intelligence/**`) | authorization / approval / hold / audit / trace / verification chain |
| E4 retention archives | `backend/data/*.archive.jsonl` (one per table) | records aged out of the live stores (full history = archive + live) |
| Intelligence memory | `backend/data/observability.db` → `intelligence_memory` | the Learn stage |
| Manifest + checksums | in each backup dir | provenance + tamper-evidence |

**Not** covered here: `container_metrics` in `observability.db` (transient
telemetry — captured incidentally, not relied on), the code (git), the systemd
drop-ins (`docs/operations/DEPLOY.md` §3 covers those).

Scripts (`backend/scripts/`):

| Script | Role | Needs venv? |
|---|---|---|
| `rmt-evidence-backup.sh` | make a timestamped, checksummed backup | no |
| `rmt_evidence_verify.py` | structural + cross-store integrity check (the six `governance_evidence.db` tables, any residual JSON, the archives, `observability.db`) | **no** (stdlib only) |
| `rmt-evidence-restore.sh` | restore from a backup, with guards | no (but calls `rmt-migrate-evidence.py` for a **pre-T0-1** backup, which needs the venv) |
| `rmt-migrate-evidence.py` | one-shot JSON → `governance_evidence.db` (`--reverse` to go back) — run once on the T0-1 cutover | **yes** |

---

## 1. Back up (safe while the service runs)

```bash
cd /home/rmt-lab/homelab/projects/homelab-control-center/backend
./scripts/rmt-evidence-backup.sh
```

Writes `~/homelab/backups/rmt-evidence/<UTC timestamp>/`:

```
governance_evidence.db  VACUUM INTO snapshot of the six evidence tables (T0-1)
stores/                 residual *.json / *.json.migrated (pre-cutover hosts only)
archives/               *.archive.jsonl  (only if E4 has archived anything)
observability.db        VACUUM INTO snapshot (hot-safe, not a torn copy)
manifest.txt            git commit, host, date, per-table + per-store counts
checksum.sha256         sha256 of every file above
```

The backup is read-only against the live tree — no need to stop the service.
Override the destination root with `RMT_BACKUP_ROOT=/path`.

### Schedule it

Add to the operator's crontab (adjust the hour):

```cron
17 3 * * *  /home/rmt-lab/homelab/projects/homelab-control-center/backend/scripts/rmt-evidence-backup.sh >> /home/rmt-lab/homelab/backups/rmt-evidence/backup.log 2>&1
```

Prune old backups with whatever policy the homelab backup set already uses
(these dirs are small — the JSON stores are KB-scale; `observability.db` is a
few MB).

---

## 2. Verify a backup (or the live tree)

```bash
python3 scripts/rmt_evidence_verify.py ~/homelab/backups/rmt-evidence/<timestamp>
python3 scripts/rmt_evidence_verify.py .        # the live backend
```

- **Exit 0 / `RESULT: OK`** — `governance_evidence.db` opens read-only and all
  six evidence tables are countable, any residual JSON store parses as a list,
  every archive line parses, `observability.db` opens and `intelligence_memory`
  is queryable.
- **Exit 1 / `RESULT: FAIL`** — structural corruption (a table missing /
  unreadable, a store or archive line failed to parse, or a DB is unreadable).
  Do **not** restore from this set.
- **`WARN` lines** — cross-store advisories (an authorization with no approval
  record; a hold still `pending` on disk whose record is terminal). These are
  informational, never fatal — the startup reconcile (E2/E6) handles the hold
  case on the next boot. One known-benign orphan (`14be2cb0` /
  `3df558e8`, a 2026-09-02 test artifact) will show until it is pruned.

---

## 3. Restore

Restore replaces the live evidence with a backup. **The service must be
stopped** — a running process holds the stores in memory and would re-persist
the old state over the restore on its next write.

```bash
sudo systemctl stop rmt-control-center.service

cd /home/rmt-lab/homelab/projects/homelab-control-center/backend
./scripts/rmt-evidence-restore.sh ~/homelab/backups/rmt-evidence/<timestamp>

sudo systemctl start rmt-control-center.service
```

The script:

1. verifies `checksum.sha256` (aborts on any mismatch);
2. runs `rmt_evidence_verify.py` on the backup (aborts on structural failure);
3. refuses to proceed if `rmt-control-center.service` is active (`--force` as a
   2nd arg overrides — only when restoring into a copy you control);
4. moves each current live file aside to `<name>.pre-restore.<timestamp>`, then
   restores:
   - **T0-1+ backup** (`governance_evidence.db` present): copies it to
     `backend/data/governance_evidence.db` (with any `-wal` / `-shm` moved aside);
   - **pre-T0-1 backup** (`stores/*.json` only): restores the JSON files to
     `app/core/intelligence/**`, then runs
     `.venv/bin/python scripts/rmt-migrate-evidence.py --force` to load them into
     `governance_evidence.db` (warns to run it by hand if there is no venv);
   - archives → `backend/data/`, `observability.db` → `backend/data/`;
5. re-runs `rmt_evidence_verify.py` against the now-live tree.

After starting the service, confirm:

```bash
curl -s http://127.0.0.1:8000/ -o /dev/null -w '%{http_code}\n'          # 200
journalctl -u rmt-control-center.service -b | grep -iE 'reconcile|E4 retention'
```

Once you have confirmed the service is healthy on the restored evidence, remove
the `*.pre-restore.*` files.

### Restore drill

At least once, prove the round trip end to end: `rmt-evidence-backup.sh` → copy
the backend tree to a scratch dir → `rmt-evidence-restore.sh <backup> --force`
against the copy → `rmt_evidence_verify.py` the copy → start a throwaway
instance on `:8001` and hit `/`. Record the result in
`docs/RMT_CAPABILITIES_EVIDENCE.md`.

---

## 4. Relationship to other recovery paths

| Concern | Runbook |
|---|---|
| Homelab Docker stack (volumes, compose, images) | `docs/recovery/RECOVERY_RUNBOOK.md` |
| RMT service itself (venv, unit, drop-ins) | `docs/operations/DEPLOY.md` (§2 redeploy, §3 rollback); full bare-host rebuild is **R3** — `docs/operations/RMT_PLATFORM_RECOVERY.md` + `backend/scripts/rmt-rebuild.sh` (consumes an E5 backup for the evidence half) |
| RMT governance evidence (this doc) | E5 |

The homelab unified backup (`scripts/homelab-backup.sh`) already copies the
whole `projects/` tree, so it *incidentally* captures the JSON stores — but not
a hot-safe DB snapshot, no evidence-specific checksums, and no integrity check.
E5 is the dedicated, verifiable path; run both.
