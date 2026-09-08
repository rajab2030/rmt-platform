# RMT Control Center — Configuration Reference

Every `RMT_*` environment variable the backend reads, its default, effect, and
which systemd drop-in sets it. Above-Core / operational (production-readiness
item **D5**).

Drop-ins live in `/etc/systemd/system/rmt-control-center.service.d/`. After any
change: `sudo systemctl daemon-reload && sudo systemctl restart
rmt-control-center.service`.

---

## Operator authentication — `app/ops/ops_config.py` (P0: S1 / S2-lite, P1: S3)

| Variable | Default | Effect | Set by |
|---|---|---|---|
| `RMT_AUTH_ENABLED` | `true` | Master switch. `false` is a **local-dev only** escape hatch — leaves every mutating route open. | `auth.conf` |
| `RMT_OPERATOR_TOKENS` | *(empty)* | `name:token` pairs, comma-separated. **With auth enabled and this empty, the app refuses to start.** The matched `name` is recorded as `authorized_by` / `approved_by` / `granted_by` in the evidence. | `auth.conf` |
| `RMT_AUTH_SEPARATION` | `false` | **S3.** When `true`, `/approve` and `/homelab/approve` return **403** if the operator continuing an *agent-originated* hold is the one who granted the agent's authority (or is the proposing agent id). Non-agent holds are unaffected. Fails closed. With one operator, agent-hold approvals need a second identity — enable only when you have one. | `auth.conf` |
| `RMT_CORS_ORIGINS` | `http://localhost:5173` | **S5.** Comma-separated list of browser origins allowed to call the API. Default is the local Vite dev origin only (the old hardcoded `192.168.235.128` is gone). Set to the deployed frontend origin(s). Methods are scoped to `GET, POST` and headers to `Authorization, X-API-Key, Content-Type, X-Request-ID` (no longer `*`). | `auth.conf` or a `cors.conf` drop-in |

## Notifications — `app/ops/ops_config.py` (P0: O2 held actions · P1: O3 ops alerts)

| Variable | Default | Effect | Set by |
|---|---|---|---|
| `RMT_NOTIFY_WEBHOOK_URL` | *(empty)* | When set, both `manual_approval_required` (O2) **and** ops alerts (O3: `loop_quarantine`, `loop_cycle_error`) are POSTed as JSON here (fail-open). Unset → logged only. | `auth.conf` |
| `RMT_NOTIFY_TIMEOUT_SECONDS` | `5` | Webhook POST timeout. | `auth.conf` |
| `RMT_NOTIFY_MIN_INTERVAL_SECONDS` | `60` | Per-key de-dupe window (O2: `(kind, component, approval_id)`; O3: `(kind, key)`) — stops re-alerting every cycle. | `auth.conf` |

## Application logging — `app/ops/ops_config.py` (P1: O1 structured logging)

| Variable | Default | Effect | Set by |
|---|---|---|---|
| `RMT_LOG_LEVEL` | `INFO` | Level for the `rmt` logger tree (`rmt.http`, `rmt.homelab.loop`, `rmt.agent`, `rmt.ops.*`). | `logging.conf` drop-in (optional) |
| `RMT_LOG_JSON` | `true` | `true` → one JSON object per line on stdout → journald (`request_id`, `event`, `principal`, `action_id`/`execution_id`/`approval_id`, `governed_status`, `duration_ms`). `false` → plain text (local dev). | `logging.conf` drop-in (optional) |

Every governed HTTP mutation (`/execute`, `/approve`, `/homelab/remediate`,
`/homelab/approve`), every CAP-04 loop remediation, loop quarantine / cycle
error, and every agent proposal that reaches the adapter emits one structured
line, correlated by the same ids the durable evidence uses. Each request also
gets one `http_request` line and an `X-Request-ID` response header (an inbound
`X-Request-ID` is honoured). Nothing is read from `app/core/**`; Core-internal
steps are not logged here.

**Log retention / rotation** is journald's job, not the app's — see
`DEPLOY.md` §5 (`journalctl --vacuum` or a `journald.conf` `SystemMaxUse=`).

### O3 service-down heartbeat — `backend/scripts/rmt-heartbeat.sh` (not read by the app)

| Variable | Default | Effect | Set by |
|---|---|---|---|
| `RMT_HEARTBEAT_URL` | *(required)* | Cron pings this only while `GET /health` returns 200 — an inverted dead-man's switch. If the service is down the ping stops and the external monitor alerts. | crontab line |
| `RMT_HEALTH_URL` | `http://127.0.0.1:8000/health` | Local probe the heartbeat script checks. | crontab line |

## CAP-04 continuous operational loop — `app/homelab/loop_config.py`

| Variable | Default | Effect | Set by |
|---|---|---|---|
| `RMT_HOMELAB_LOOP_ENABLED` | `false` | Start the supervised loop at boot. | `cap04-loop.conf` (**=true on live**) |
| `RMT_HOMELAB_LOOP_INTERVAL_SECONDS` | `120` | Cycle cadence. | — |
| `RMT_HOMELAB_LOOP_FLAP_WINDOW_SECONDS` | `900` | Flap-guard window. | — |
| `RMT_HOMELAB_LOOP_MAX_ATTEMPTS_PER_WINDOW` | `3` | Held/failed attempts in the window before quarantine. | — |
| `RMT_HOMELAB_LOOP_COOLDOWN_SECONDS` | `300` | Per-component cooldown after an attempt. | — |
| `RMT_HOMELAB_LOOP_RECOVERY_HEALTHY_STREAK` | `2` | Healthy observations needed to auto-clear quarantine. | — |
| `RMT_HOMELAB_LOOP_HISTORY_CAP` | `50` | In-memory cycle-history length. | — |

*(Exact names as read by `loop_config.py`; verify there before overriding.)*

## Agent surface 5A + 5B — `app/agent/loop_config.py`

| Variable | Default | Effect | Set by |
|---|---|---|---|
| `RMT_AGENT_ENABLED` | `false` | Enable the governed agent surface (`/agent/act`). | `cap05-agent.conf` (**=true on live**) |
| `RMT_AGENT_GRANT_TTL_SECONDS` | `300` | Authority-grant lifetime (also single-use). | — |
| `RMT_AGENT_DEFAULT_REQUIRES_APPROVAL` | `true` | Every state-changing agent action is human-approval-gated. | — |
| `RMT_AGENT_DEPENDENCY_ESCALATION` | `true` | T13: force approval when an allowed op reaches a restricted effect via a known dependency. | — |
| `RMT_AGENT_LLM_ENABLED` | `false` | Enable `/agent/act/llm` (LLM turns a goal into a proposal). | `cap05-agent.conf` (**=true on live**) |
| `RMT_AGENT_LLM_MODEL` | `deepseek-v4-flash:cloud` | Ollama model. | — |
| `RMT_AGENT_LLM_HOST` | `http://127.0.0.1:11434` | Ollama endpoint. | — |
| `RMT_AGENT_LLM_TIMEOUT_SECONDS` | `60` | LLM call timeout. | — |
| `RMT_AGENT_LLM_MAX_TOKENS` | `400` | `num_predict`. | — |
| `RMT_AGENT_LLM_TEMPERATURE` | `0.1` | Sampling temperature. | — |

## Runtime engine — `config/config.yaml` (not env)

`runtime.engine: docker` — the execution adapter. Resolves to `simulation` when
the Docker adapter is not registered. See `RMT_CONTEXT.md` §13.

**D6:** the resolved mode is visible at runtime — `GET /health` carries a
`runtime` block (`configured_engine`, `resolved_adapter`, `docker_available`,
`git_available`, `adapter_degraded`, `notes`), and a configured/resolved
mismatch is logged as a `WARNING` at startup. Full host-capability list:
`docs/operations/PREREQUISITES.md`.

---

## Live drop-in inventory (expected after P0)

```
/etc/systemd/system/rmt-control-center.service.d/
├── auth.conf            # S1/S2-lite/O2  (mode 0600, root)
├── bind-loopback.conf   # S4
├── cap04-loop.conf      # RMT_HOMELAB_LOOP_ENABLED=true
└── cap05-agent.conf     # RMT_AGENT_ENABLED=true, RMT_AGENT_LLM_ENABLED=true
```
