# RMT Control Center — Deploy & Rollback Runbook

Operational runbook for the RMT backend service itself (not the homelab Docker
stack — that is `docs/recovery/RECOVERY_RUNBOOK.md`). Covers the
production-readiness **P0** posture: operator authentication (S1/S2-lite),
loopback bind + TLS reverse proxy (S4), atomic evidence writes (E1),
held-action alerting (O2).

Above-Core / operational. Does not change C01–C07.

---

## 0. What runs where

| Piece | Location |
|---|---|
| Service unit | `/etc/systemd/system/rmt-control-center.service` — canonical copy in git: `deploy/systemd/rmt-control-center.service` |
| Drop-ins | `/etc/systemd/system/rmt-control-center.service.d/*.conf` — canonical copies in `deploy/systemd/`, `auth.conf` included (it holds no secret itself — see below) |
| Code | `/home/rmt-lab/homelab/projects/homelab-control-center/backend` |
| venv | `…/backend/.venv` |
| Governance evidence | `…/backend/app/core/intelligence/**/*.json` |
| Intelligence memory | `…/backend/data/observability.db` |
| Reverse proxy | Caddy, config `projects/homelab-control-center/deploy/Caddyfile` |

Existing drop-ins: `cap04-loop.conf` (CAP-04 loop on), `cap05-agent.conf`
(agent 5A+5B on), `auth.conf` (S1 tokens), `bind-loopback.conf` (S4).
Add `hardening.conf` (D3) — see §5.1; optional `logging.conf` (O1 verbosity).
See `deploy/systemd/README.md` for the full drop-in inventory.

**Bare-host rebuild** (the machine is gone, not a code redeploy): follow
`docs/operations/RMT_PLATFORM_RECOVERY.md` (R3) — `backend/scripts/rmt-rebuild.sh`
drives venv → evidence restore → integrity check → suite → unit install → start.

---

## 1. First-time P0 cutover

### 1.1 Dependencies (D1)

```
cd /home/rmt-lab/homelab/projects/homelab-control-center/backend
.venv/bin/pip install -r requirements.txt        # pinned set
.venv/bin/python -m pytest -q                     # expect: all pass
```

### 1.2 Operator tokens (S1 / S2-lite)

T0-5 (2026-09-12): the token list is a systemd credential
(`LoadCredential=`), not an `Environment=` value — `systemctl show -p
Environment` exposes a unit's plain environment (drop-in secrets included)
to *any local user*, not just root; a credential file's path is exposed the
same way, but its content is not. See `docs/operations/SECRETS.md`.

```
cd /home/rmt-lab/homelab/projects/homelab-control-center
sudo install -d -m 0700 /etc/rmt
sudo install -m 0600 /dev/null /etc/rmt/operator_tokens.secret
echo "alice:$(openssl rand -hex 24),bob:$(openssl rand -hex 24)" \
  | sudo tee /etc/rmt/operator_tokens.secret >/dev/null
sudo install -m 0644 deploy/systemd/auth.conf.example \
  /etc/systemd/system/rmt-control-center.service.d/auth.conf
#   (optionally) sudoedit the drop-in to add RMT_NOTIFY_WEBHOOK_URL=…
sudo systemctl daemon-reload && sudo systemctl restart rmt-control-center.service
```

Distribute each operator their own token over a secure channel. The token is
sent as `Authorization: Bearer <token>` (or `X-API-Key: <token>`). Rotate by
overwriting `/etc/rmt/operator_tokens.secret` + `daemon-reload` + restart.

### 1.3 Loopback bind (S4)

```
sudo install -m 0644 deploy/systemd/bind-loopback.conf \
  /etc/systemd/system/rmt-control-center.service.d/bind-loopback.conf
```

### 1.4 Reverse proxy + TLS (S4)

```
# Debian/Ubuntu
sudo apt install -y caddy
sudo mkdir -p /var/log/caddy
sudo cp deploy/Caddyfile /etc/caddy/Caddyfile
# edit the site addresses to match your DNS / /etc/hosts
sudo systemctl restart caddy
# export Caddy's internal root CA and import it on operator machines:
sudo caddy trust      # local
# or copy: /var/lib/caddy/.local/share/caddy/pki/authorities/local/root.crt
```

### 1.5 Apply

```
sudo systemctl daemon-reload
sudo systemctl restart rmt-control-center.service
sleep 3
systemctl is-active rmt-control-center.service      # active
```

### 1.6 Verify

```
TOKEN=<an operator token>
# app is loopback only
curl -sS -m5 http://192.168.223.128:8000/ ; echo         # connection refused
# proxy serves TLS
curl -sS -m5 https://192.168.223.128/  ; echo            # 200 (CA trusted) 
# auth enforced
curl -sS -m5 -o /dev/null -w '%{http_code}\n' \
  -X POST https://192.168.223.128/homelab/loop/stop            # 401
curl -sS -m5 -o /dev/null -w '%{http_code}\n' \
  -H "Authorization: Bearer $TOKEN" \
  -X POST https://192.168.223.128/homelab/loop/stop            # 200
curl -sS -m5 -H "Authorization: Bearer $TOKEN" \
  https://192.168.223.128/agent/status | head -c 200 ; echo    # enabled:false…
```

If you stopped the loop to test, start it again:
`curl -H "Authorization: Bearer $TOKEN" -X POST https://…/homelab/loop/start`.

### 1.7 Restart-safety check (E1)

```
sudo systemctl kill -s KILL rmt-control-center.service   # hard kill
sudo systemctl start rmt-control-center.service
sleep 3
# no partial evidence, no leftover temp files
ls backend/app/core/intelligence/**/*.json.tmp 2>/dev/null   # nothing
python3 -c "import json,glob; [json.load(open(f)) for f in glob.glob('backend/app/core/intelligence/**/*.json', recursive=True)]; print('all evidence files parse')"
```

---

## 2. Routine redeploy (code change)

```
cd /home/rmt-lab/homelab
git pull                              # or check out the target commit
cd projects/homelab-control-center/backend
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m pytest -q         # gate: all pass
sudo systemctl restart rmt-control-center.service
sleep 3 && systemctl is-active rmt-control-center.service
# smoke
TOKEN=<token>
curl -s -H "Authorization: Bearer $TOKEN" https://192.168.223.128/agent/status | head -c 200; echo
curl -s https://192.168.223.128/homelab/loop/status | python3 -c "import sys,json;d=json.load(sys.stdin);print('loop',d['enabled'],d['running'],d['components'])"
```

---

## 3. Rollback

```
cd /home/rmt-lab/homelab
git log --oneline -5
git checkout <last-good-commit>       # e.g. the previous deploy tag/sha
cd projects/homelab-control-center/backend
.venv/bin/pip install -r requirements.txt
sudo systemctl restart rmt-control-center.service
sleep 3 && systemctl is-active rmt-control-center.service
```

Evidence stores are append-only and forward-compatible; a rollback does not
require restoring them. If a store was corrupted (should be impossible after
E1), restore the newest good copy from the homelab backup set
(`docs/recovery/RECOVERY_RUNBOOK.md`, once the RMT stores are added to it — item
E5) and restart.

Disable a single P0 drop-in without a full rollback:

```
sudo rm /etc/systemd/system/rmt-control-center.service.d/<name>.conf
sudo systemctl daemon-reload && sudo systemctl restart rmt-control-center.service
```

(`RMT_AUTH_ENABLED=false` in `auth.conf` is the fastest way to drop auth in an
emergency — leaves the surface open, so treat it as break-glass.)

---

## 4. Token rotation

```
sudoedit /etc/rmt/operator_tokens.secret
sudo systemctl restart rmt-control-center.service
```

(No `daemon-reload` needed — the unit still points at the same path via
`LoadCredential=`; only the file content changed.) Old tokens stop working
at the restart. Removing an operator = delete their `name:token` pair and
restart.

---

## 5. Hardening (D3) & log retention (O1)

### 5.1 Service sandboxing — `hardening.conf`

The unit runs as a non-root user but has no systemd confinement. The drop-in
`projects/homelab-control-center/deploy/systemd/hardening.conf` adds restart
backoff, resource ceilings (`MemoryMax=512M`, `CPUQuota=200%`, `TasksMax=128`),
`NoNewPrivileges`, `ProtectSystem=full`, `PrivateTmp`, the kernel-surface
protections, and `SystemCallFilter=@system-service`.
`systemd-analyze security` drops from **9.2 UNSAFE** to **4.1 OK**.

```
sudo install -m 0644 \
  projects/homelab-control-center/deploy/systemd/hardening.conf \
  /etc/systemd/system/rmt-control-center.service.d/hardening.conf
sudo systemctl daemon-reload && sudo systemctl restart rmt-control-center.service

# watch the FIRST restart
systemctl is-active rmt-control-center.service
curl -sk https://192.168.223.128/health | python3 -c "import sys,json;print(json.load(sys.stdin)['status'])"
journalctl -u rmt-control-center.service -n 50 --no-pager   # no EPERM / traceback
systemd-analyze security rmt-control-center.service         # ~4.1
```

Rollback: `sudo rm …/hardening.conf && sudo systemctl daemon-reload && sudo
systemctl restart rmt-control-center.service`.

**Deliberately deferred** (apply one at a time, `systemd-analyze security` +
`/health` after each): `ProtectSystem=strict` +
`ReadWritePaths=…/backend`; `ProcSubset=pid`; localhost-only
`IPAddressAllow`/`IPAddressDeny` once the notify sink is decided.
`ProtectHome` must stay `no` — evidence + `data/observability.db` live under
`/home`. `MemoryDenyWriteExecute` is not recommended for this stack.

### 5.2 Log retention — journald

The backend logs structured JSON to **stdout**; systemd routes it to
**journald**. Retention/rotation is journald's job — the app does not write or
rotate log files.

Bound the journal (host-wide or per-unit):

```
# host-wide, persistent journal cap
sudo mkdir -p /etc/systemd/journald.conf.d
printf '[Journal]\nSystemMaxUse=500M\nMaxRetentionSec=30day\n' \
  | sudo tee /etc/systemd/journald.conf.d/rmt.conf
sudo systemctl restart systemd-journald

# inspect just this service
journalctl -u rmt-control-center.service -f            # follow
journalctl -u rmt-control-center.service --since today
journalctl --vacuum-time=30d                           # one-off trim
```

Optional: raise verbosity with a drop-in
`/etc/systemd/system/rmt-control-center.service.d/logging.conf`
(`Environment=RMT_LOG_LEVEL=DEBUG`) — default is `INFO`, JSON on.

---

## 6. Known follow-ups (not in P0)

- **P0 status:** S1/S2-lite, E1, O2 live 2026-09-07; **E2** and **S4** closed
  2026-09-08. E2 = `app/ops/reconcile.py` runs in the startup lifespan and
  reconciles the approval hold store against the authoritative record store
  (no `app/core/**` change). S4 = Caddy `2.6.2` TLS reverse proxy installed +
  enabled (`/etc/caddy/Caddyfile` from `deploy/Caddyfile`, `tls internal`).
  **P0 is fully closed.**
- **S4 operator CA** — import the Caddy internal root CA on each operator
  workstation: `/var/lib/caddy/.local/share/caddy/pki/authorities/local/root.crt`
  (or `caddy trust` on that machine). Done on the RMT host itself.
- **E4 / E5 — DONE (2026-09-08).** E4: startup archival keeps the JSON stores
  bounded (`RMT_EVIDENCE_RETENTION_DAYS`, default 90). E5: dedicated
  backup/verify/restore for the RMT evidence + `observability.db` —
  `backend/scripts/rmt-evidence-backup.sh` / `rmt_evidence_verify.py` /
  `rmt-evidence-restore.sh`, runbook `docs/operations/RMT_EVIDENCE_RECOVERY.md`.
  **Wire the cron line** from that runbook.
- **O3 — DONE (2026-09-08).** `notify_ops` alerts on loop quarantine + cycle
  error (same webhook as O2); `GET /health` + `backend/scripts/rmt-heartbeat.sh`
  cover service-down. **Cron the heartbeat** with a monitor URL
  (`docs/operations/CONFIG.md` → O3 section).
- **O1 — DONE (2026-09-08).** Structured JSON logging to stdout/journald
  (`app/ops/logging_config.py`); `RMT_LOG_LEVEL` / `RMT_LOG_JSON`. **Set a
  journald cap** — see §5.2.
- **D3 — DONE (2026-09-08).** `deploy/systemd/hardening.conf` — sandboxing +
  resource ceilings + restart backoff (9.2 → 4.1 on `systemd-analyze
  security`). **Install it** — see §5.1.
- **R3 — DONE (2026-09-08).** Bare-host rebuild: the base unit + the four
  non-secret drop-ins are captured in `deploy/systemd/`;
  `backend/scripts/rmt-rebuild.sh` + `docs/operations/RMT_PLATFORM_RECOVERY.md`
  drive a cold start from repo + an E5 evidence backup. Scratch-dir drill
  passed; a from-cold VM rebuild is still recommended once.
- **P2 batch — DONE (2026-09-08).** All eight closed:
  - **S5** CORS from `RMT_CORS_ORIGINS` (+ scoped methods/headers) — set it in a
    drop-in to the deployed frontend origin (`CONFIG.md`).
  - **S6** secrets pattern — `docs/operations/SECRETS.md`.
  - **S7** rate limiting on `/execute` + `/agent/act*` (`RMT_RATELIMIT_*`).
  - **D4** `backend/scripts/rmt-watchdog.sh` — cron every 1–2 min
    (`RMT_WATCHDOG_NOTIFY_URL=…`); restarts on sustained-unreachable `/health`.
  - **D6** `/health` `runtime` block + startup mismatch WARNING;
    `docs/operations/PREREQUISITES.md`.
  - **O4** `GET /metrics` (Prometheus text, unauthenticated) — point a scraper
    at it, directly or via Caddy.
  - **V3** env-dependent routes now return 503 (not 500) when git/Docker is
    absent; both modes tested.
  - **V4** `backend/scripts/rmt-smoke.sh` — run after every restart / drop-in
    change (`RMT_SMOKE_TOKEN=…`; expects `runtime.resolved_adapter == docker`).
- See `docs/RMT_PRODUCTION_READINESS.md` for the full matrix (now all READY
  except the ACCEPTED `R4`).
- **Tier 1 batch T1-2/T1-3/T1-4 — DONE (2026-09-09).** Above-Core; a redeploy
  picks them up, all inert by default.
  - **T1-2** `RMT_HOMELAB_DEPENDENCIES` — set in a `deps.conf` drop-in only if a
    real inter-component edge exists (none today); activates T13 escalation
    without a code change (`CONFIG.md`).
  - **T1-3** `continue_remediation` above-Core Learn/verify now covers any
    component with a `ComponentContext` (not just `uptime-kuma`). No config.
  - **T1-4** `RMT_NOTIFY_FORMAT` (`generic`/`slack`/`ntfy`) shapes the existing
    notify webhook. New read-only `GET /ops/holds` +
    `backend/scripts/rmt-escalate.sh` — cron every 1–2 min alongside
    `rmt-watchdog.sh` (`RMT_ESCALATE_TOKEN=…`, `RMT_ESCALATE_WEBHOOK_URL=…`);
    one-time alert for a hold left unactioned or expired-unapproved.
- **B1 (strengthen Verify) — DONE (2026-09-10).** Above-Core; a redeploy picks
  it up, no new required env.
  - **B1a** every wired adapter/operation gets a real post-condition assertion
    through the frozen verifier; `RMT_VERIFY_OBSERVE_TIMEOUT_S` (default `5`,
    `0` = single-shot) — `CONFIG.md`.
  - **B1b** new read-only **`GET /ops/verifications`** (operator-authenticated;
    `?limit=` / `?effective_status=`) — per executed action, whether it was
    verified and if not why. `/metrics` gains
    `rmt_executed_actions_total{adapter,operation}` +
    `_verified_total` / `_unverified_total` / `_state_mismatch_total`. An
    executed action that could not be observed fires one low-severity
    `verification_inconclusive` line on the existing notify webhook. The
    effective-status index is in-memory, rebuilt from the durable evidence on
    startup.
