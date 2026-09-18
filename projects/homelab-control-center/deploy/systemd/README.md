# RMT Control Center — deploy artifacts

Everything needed to stand the RMT backend service up on a host. Above-Core /
operational; no `app/core/**` dependency.

## systemd unit + drop-ins

The service is one **base unit** plus **drop-in overrides**. systemd merges the
base unit with every `*.conf` in `rmt-control-center.service.d/`, in filename
order, `[Section]` by `[Section]`. An empty `ExecStart=` clears the base value
before a replacement.

| File | Item | In git? | Purpose |
|---|---|---|---|
| `rmt-control-center.service` | R3 | ✅ | base unit — user, workdir, `ExecStart` (127.0.0.1:8000, one worker), `Restart=always` |
| `cap04-loop.conf` | CAP-04 | ✅ | `RMT_HOMELAB_LOOP_ENABLED=true` |
| `cap05-agent.conf` | CAP-05 | ✅ | `RMT_AGENT_ENABLED` / `RMT_AGENT_LLM_ENABLED=true` |
| `bind-loopback.conf` | S4 | ✅ | rebinds `ExecStart` to `127.0.0.1:8000` (Caddy is the only LAN listener) |
| `hardening.conf` | D3 | ✅ | sandboxing + resource ceilings + restart backoff (`systemd-analyze security` 9.2 → 4.1) |
| `auth.conf` | S1/S2-lite/O2 | ✅ (T0-5, 2026-09-12) | `RMT_AUTH_ENABLED=true`, `LoadCredential=RMT_OPERATOR_TOKENS:/etc/rmt-control-center/operator_tokens.secret`, and optional `RMT_NOTIFY_WEBHOOK_URL`. Holds **no secret itself** — install verbatim from `auth.conf.example`. The actual token list lives at `/etc/rmt-control-center/operator_tokens.secret` (mode `0600`, root-owned, outside git entirely — not even a template, created fresh per deployment; see `docs/operations/SECRETS.md`). Rationale: `systemctl show -p Environment` exposes a unit's plain environment to any local user, not just root — `LoadCredential=` doesn't. |
| `logging.conf` | O1 | ❌ optional | `RMT_LOG_LEVEL=DEBUG` etc. — only if raising verbosity from the `INFO` default |

**Expected live drop-in inventory:** `cap04-loop.conf`, `cap05-agent.conf`,
`auth.conf`, `bind-loopback.conf`, `hardening.conf`. `docs/operations/CONFIG.md`
lists every `RMT_*` variable and which drop-in sets it.

Keep exactly one backend process/worker. The HTTP approval serialization control
is process-local; multiple workers or overlapping backend instances sharing the
evidence database are unsupported. Both the base unit and loopback override pin
`--workers 1`. See `docs/RMT_SECURITY_REMEDIATION.md` for validation and deployment
status; editing these files does not update an installed unit.

## Reverse proxy

`Caddyfile` — the Caddy `2.6.2` TLS reverse proxy config. Goes to
`/etc/caddy/Caddyfile`. `tls internal`; export the root CA and trust it on each
operator workstation (`caddy trust`, or copy
`/var/lib/caddy/.local/share/caddy/pki/authorities/local/root.crt`).

## Rebuilding on a fresh host

`../../backend/scripts/rmt-rebuild.sh` orchestrates the whole cold start (venv
from the lockfile → evidence restore → integrity check → suite → unit install →
service up). Runbook: `docs/operations/RMT_PLATFORM_RECOVERY.md` (R3).
