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
| Service unit | `/etc/systemd/system/rmt-control-center.service` |
| Drop-ins | `/etc/systemd/system/rmt-control-center.service.d/*.conf` |
| Code | `/home/rmt-lab/homelab/projects/homelab-control-center/backend` |
| venv | `…/backend/.venv` |
| Governance evidence | `…/backend/app/core/intelligence/**/*.json` |
| Intelligence memory | `…/backend/data/observability.db` |
| Reverse proxy | Caddy, config `projects/homelab-control-center/deploy/Caddyfile` |

Existing drop-ins: `cap04-loop.conf` (CAP-04 loop on), `cap05-agent.conf`
(agent 5A+5B on). This runbook adds `auth.conf` and `bind-loopback.conf`.

---

## 1. First-time P0 cutover

### 1.1 Dependencies (D1)

```
cd /home/rmt-lab/homelab/projects/homelab-control-center/backend
.venv/bin/pip install -r requirements.txt        # pinned set
.venv/bin/python -m pytest -q                     # expect: all pass
```

### 1.2 Operator tokens (S1 / S2-lite)

```
cd /home/rmt-lab/homelab/projects/homelab-control-center
sudo install -m 0600 deploy/systemd/auth.conf.example \
  /etc/systemd/system/rmt-control-center.service.d/auth.conf
# generate real tokens
openssl rand -hex 24    # once per operator
sudoedit /etc/systemd/system/rmt-control-center.service.d/auth.conf
#   RMT_OPERATOR_TOKENS=alice:<tok1>,bob:<tok2>
#   (optionally) RMT_NOTIFY_WEBHOOK_URL=…
```

Distribute each operator their own token over a secure channel. The token is
sent as `Authorization: Bearer <token>` (or `X-API-Key: <token>`).

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
sudoedit /etc/systemd/system/rmt-control-center.service.d/auth.conf
sudo systemctl daemon-reload && sudo systemctl restart rmt-control-center.service
```

Old tokens stop working at the restart. Removing an operator = delete their
`name:token` pair and restart.

---

## 5. Known follow-ups (not in P0)

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
- **S5** — CORS origin list in `app/main.py` is hardcoded (and currently points
  at a stale `192.168.235.128`); move to config.
- **D3** — systemd sandboxing / resource limits on the unit.
- See `docs/RMT_PRODUCTION_READINESS.md` for the full matrix.
