# RMT Platform Recovery Runbook

RMT-PROD **P1 / R3**. The tested procedure to rebuild the **RMT control-center
service itself** — venv, systemd unit + drop-ins, governance evidence stores,
`observability.db` — on a fresh host, from the repository plus a restored
evidence set.

Above-Core / operational. No `app/core/**` dependency; does not reopen or modify
C01–C07.

---

## 0. Where this sits among the recovery paths

| Concern | Runbook |
|---|---|
| Homelab Docker stack (volumes, compose, images) | `docs/recovery/RECOVERY_RUNBOOK.md` |
| RMT **governance evidence** (the 6 JSON stores + `observability.db`) | `docs/operations/RMT_EVIDENCE_RECOVERY.md` (E5) |
| RMT **service** — bare-host rebuild | **this doc (R3)** |
| RMT service — routine redeploy / rollback / token rotation | `docs/operations/DEPLOY.md` |

R3 = "the machine is gone; stand the service back up." It **consumes** E5 (for
the evidence) and reuses DEPLOY.md §1 (for the P0/D3 install steps) rather than
duplicating them.

---

## 1. What you need

1. **The repository** at the canonical path:
   `/home/rmt-lab/homelab` → `projects/homelab-control-center/`.
   The systemd unit and every drop-in hard-code
   `/home/rmt-lab/homelab/projects/homelab-control-center/backend`; rebuild there.
2. **An evidence backup** made by `backend/scripts/rmt-evidence-backup.sh`
   (`~/homelab/backups/rmt-evidence/<UTC timestamp>/`, or wherever it is
   archived). The newest one that passes `rmt_evidence_verify.py`.
3. **Host prerequisites** (`docs/operations/CONFIG.md` §prereqs and
   `deploy/systemd/hardening.conf` notes):
   - Python **3.12**, `git`, `sqlite3`, `rsync`, `curl`
   - a `rmt-lab` user; membership of the `docker` group (else the execution
     adapter falls back to `simulation`)
   - `systemd`; `caddy` ≥ 2.6 for the S4 TLS entry point
4. **The operator tokens** (S1) — from your secret store, *not* from git.
5. **The Caddy root CA** if you want the existing operator workstations to keep
   trusting the endpoint without re-import (otherwise a fresh `tls internal` CA
   is generated and must be re-trusted).

---

## 2. Rebuild — the fast path

`backend/scripts/rmt-rebuild.sh` orchestrates the whole sequence.

```bash
# 0. restore the repo to /home/rmt-lab/homelab (git clone / backup extract)

# 1. put an evidence backup on the box, e.g.
#    ~/homelab/backups/rmt-evidence/2026-09-08T21-54-28Z/

cd /home/rmt-lab/homelab/projects/homelab-control-center/backend
./scripts/rmt-rebuild.sh --evidence ~/homelab/backups/rmt-evidence/<timestamp>
```

The script runs, in order:

| # | Step | Detail |
|---|---|---|
| 1 | prerequisites | python 3.12 / git / sqlite3 / rsync / docker group / systemd / caddy — hard-fails on a missing core tool, `WARN`s on the soft ones |
| 2 | venv | `.venv` built **strictly from `requirements.lock.txt`** (same reproducible install the V2 CI gate uses) |
| 3 | evidence restore | calls `scripts/rmt-evidence-restore.sh <backup>` — checksum → integrity → refuses if the service is live → moves the current stores to `*.pre-restore.*` → copies the backup in → re-verifies |
| 4 | integrity check | `scripts/rmt_evidence_verify.py <backend>` against the now-live tree; **aborts the rebuild on structural failure** |
| 5 | test suite | `PYTHONPATH=. pytest -q` (skip with `--skip-suite`) |
| 6 | systemd bring-up | installs `deploy/systemd/rmt-control-center.service` + the four non-secret drop-ins (`cap04-loop`, `cap05-agent`, `bind-loopback`, `hardening`), `daemon-reload`, then **pauses** and prints the manual secret/CA checklist before `systemctl enable --now` and a `/health` poll |

### The manual steps the script will not do (secrets / CA)

Printed by the script at step 6; do them before you let it start the service:

1. **`auth.conf`** (S1 / S2-lite) — `DEPLOY.md` §1.2. The app **refuses to
   start** with auth enabled and no tokens, so this is mandatory.
2. **Caddy TLS proxy** (S4) — `DEPLOY.md` §1.4. Import the root CA on operator
   machines (or `caddy trust`).
3. **journald cap** (O1) — `DEPLOY.md` §5.2.
4. **cron** — `rmt-evidence-backup.sh` (RMT_EVIDENCE_RECOVERY.md §1) and
   `rmt-heartbeat.sh` (CONFIG.md → O3).

### Options

```
--repo DIR         repo root (default /home/rmt-lab/homelab)
--drill DIR        DRILL MODE (see §4) — no live changes
--port N           drill instance port (default 8001)
--skip-systemd     stop after step 5 (venv + evidence + suite only)
--skip-suite       skip step 5
--yes              don't prompt before overwriting the live evidence tree
```

---

## 3. Rebuild — the manual path (if the script can't run)

1. `python3.12 -m venv backend/.venv && backend/.venv/bin/pip install -r backend/requirements.lock.txt`
2. `sudo systemctl stop rmt-control-center.service` (if it somehow exists)
3. `backend/scripts/rmt-evidence-restore.sh <backup>`
4. `python3 backend/scripts/rmt_evidence_verify.py backend` → must print `RESULT: OK`
5. `cd backend && PYTHONPATH=. .venv/bin/pytest -q` → all pass
6. `sudo install -m 0644 deploy/systemd/rmt-control-center.service /etc/systemd/system/`
7. `sudo mkdir -p /etc/systemd/system/rmt-control-center.service.d` and
   `install -m 0644` each of `cap04-loop.conf cap05-agent.conf bind-loopback.conf hardening.conf`
8. `auth.conf` — `DEPLOY.md` §1.2 (mode `0600`, real tokens)
9. `sudo systemctl daemon-reload && sudo systemctl enable --now rmt-control-center.service`
10. `curl -s http://127.0.0.1:8000/health` → `{"status":"ok",…}`
11. Caddy (`DEPLOY.md` §1.4), journald cap (§5.2), cron jobs

---

## 4. Recovery drill

Prove the sequence without touching the live host: `--drill` rsyncs the project
into a scratch dir, runs steps 2–5 there, and starts a throwaway instance on a
spare port with auth disabled — no systemd, no change to the real service or its
evidence.

```bash
cd /home/rmt-lab/homelab/projects/homelab-control-center/backend
./scripts/rmt-evidence-backup.sh                       # fresh backup
./scripts/rmt-rebuild.sh \
  --evidence ~/homelab/backups/rmt-evidence/<timestamp> \
  --drill /tmp/rmt-r3-drill --port 8011
# expect: DRILL PASSED + a /health JSON body with "status": "ok"
rm -rf /tmp/rmt-r3-drill
```

Record each drill (date, commit, evidence set, result) in
`docs/RMT_CAPABILITIES_EVIDENCE.md`.

**Still recommended at least once:** a genuine from-cold rebuild on a fresh VM
(no `--drill`) to exercise the systemd + Caddy + cron steps end to end. The
drill covers everything up to and including a live-serving process; it does not
exercise the unit-install / proxy / CA path.

---

## 5. Post-rebuild verification

```bash
TOKEN=<an operator token>
curl -s http://127.0.0.1:8000/health | python3 -m json.tool            # status ok
systemctl is-active rmt-control-center.service                         # active
journalctl -u rmt-control-center.service -b | grep -iE 'reconcile|retention|E6'
curl -s http://127.0.0.1:8000/homelab/loop/status                     # enabled true, running true
curl -s -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8000/agent/status | head -c 200
curl -sk https://<host>/ -o /dev/null -w '%{http_code}\n'             # 200 via Caddy
curl -sk -o /dev/null -w '%{http_code}\n' -X POST https://<host>/homelab/loop/stop   # 401 (no token)
```

The startup reconcile (E2/E6) runs automatically and logs its result; a clean
rebuild shows a no-op reconcile and every evidence store parsing. Remove the
`*.pre-restore.*` files once the service is confirmed healthy on the restored
evidence.
