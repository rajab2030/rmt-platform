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
| `RMT_OPERATOR_TOKENS` | *(empty)* | `name:token` pairs, comma-separated. **With auth enabled and this empty, the app refuses to start.** The matched `name` is recorded as `authorized_by` / `approved_by` / `granted_by` in the evidence. **T0-5 (2026-09-12):** on a systemd deployment this is a `LoadCredential=RMT_OPERATOR_TOKENS:/etc/rmt-control-center/operator_tokens.secret` in `auth.conf`, not an `Environment=` value — `systemctl show -p Environment` exposes plain env vars to any local user, `LoadCredential=` doesn't. The env var remains a fallback for local dev/tests. | `/etc/rmt-control-center/operator_tokens.secret` (via `auth.conf`) |
| `RMT_AUTH_SEPARATION` | `false` | **S3.** When `true`, `/approve` and `/homelab/approve` return **403** if the operator continuing an *agent-originated* hold is the one who granted the agent's authority (or is the proposing agent id). Non-agent holds are unaffected. Fails closed. With one operator, agent-hold approvals need a second identity — enable only when you have one. | `auth.conf` |
| `RMT_CORS_ORIGINS` | `http://localhost:5173` | **S5.** Comma-separated list of browser origins allowed to call the API. Default is the local Vite dev origin only (the old hardcoded `192.168.235.128` is gone). Set to the deployed frontend origin(s). Methods are scoped to `GET, POST` and headers to `Authorization, X-API-Key, Content-Type, X-Request-ID` (no longer `*`). | `auth.conf` or a `cors.conf` drop-in |
| `RMT_RATELIMIT_ENABLED` | `true` | **S7.** Per-principal fixed-window rate limiting on the expensive routes. `false` disables it. | `auth.conf` |
| `RMT_RATELIMIT_EXECUTE_PER_MINUTE` | `30` | **S7.** Max `POST /execute` calls per operator per 60s → **429** + `Retry-After`. | `auth.conf` |
| `RMT_RATELIMIT_AGENT_PER_MINUTE` | `20` | **S7.** Max `POST /agent/act`, `/agent/act/llm`, `/agent/authority/grant` per operator per 60s → **429**. Read-only agent routes are not limited. | `auth.conf` |

## Notifications — `app/ops/ops_config.py` (P0: O2 held actions · P1: O3 ops alerts)

| Variable | Default | Effect | Set by |
|---|---|---|---|
| `RMT_NOTIFY_WEBHOOK_URL` | *(empty)* | When set, both `manual_approval_required` (O2) **and** ops alerts (O3: `loop_quarantine`, `loop_cycle_error`) are POSTed as JSON here (fail-open). Unset → logged only. | `auth.conf` |
| `RMT_NOTIFY_TIMEOUT_SECONDS` | `5` | Webhook POST timeout. | `auth.conf` |
| `RMT_NOTIFY_MIN_INTERVAL_SECONDS` | `60` | Per-key de-dupe window (O2: `(kind, component, approval_id)`; O3: `(kind, key)`) — stops re-alerting every cycle. | `auth.conf` |
| `RMT_NOTIFY_FORMAT` | `generic` | **T1-4.** Payload shaping for `RMT_NOTIFY_WEBHOOK_URL`: `generic` (today's JSON, unchanged) · `slack` (`{"text": …}`, Slack/Mattermost incoming-webhook) · `ntfy` (plain body + `Title`/`Priority`/`Tags` headers). Unknown value → `generic`. | `auth.conf` |

### T1-4 held-action escalation — `backend/scripts/rmt-escalate.sh` (not read by the app)

The Core approval-hold TTL is 300 s: a hold nobody approves just expires. This
cron/timer script reads the read-only `GET /ops/holds` and POSTs a **one-time**
alert to a second channel for any hold that is still `actionable` past a
threshold, or that `expired` while never approved. Each `approval_id` escalates
once (state file).

| Variable | Default | Effect |
|---|---|---|
| `RMT_ESCALATE_HOLDS_URL` | `http://127.0.0.1:8000/ops/holds` | Read-only holds view. |
| `RMT_ESCALATE_TOKEN` | *(required when auth is on)* | Operator token for that route (`Authorization: Bearer`). |
| `RMT_ESCALATE_WEBHOOK_URL` | *(optional)* | Second-channel webhook (JSON POST). Unset → log only, still one-shot. |
| `RMT_ESCALATE_AFTER_SECONDS` | `180` | Age at which a still-open hold escalates. Must be `< 300` (Core TTL); the script warns otherwise. |
| `RMT_ESCALATE_STATE` | `/run/rmt-escalate` (fallback `/tmp`) | State dir for the escalated-id list. |

## Above-Core verification — `app/ops/verification/service.py` (B1a)

| Variable | Default | Effect | Set by |
|---|---|---|---|
| `RMT_VERIFY_OBSERVE_TIMEOUT_S` | `5` | **B1a.** Seconds the above-Core post-execution observer keeps re-observing (~0.5 s interval) while the expected state has not yet been seen — a settling allowance for the beat a container spends `created` / `restarting` right after a `restart` / `start`. Returns as soon as the expected state is observed. `0` = single-shot (no poll). Adds at most this much to a `POST /execute` response on a genuine `state_mismatch`. | drop-in (optional) |

Applies to `POST /execute`, the homelab remediation / approval-continuation
paths, and the governed agent path: each resolves a read-only Docker observer
for the `(adapter, operation)` and feeds it to the **frozen** verifier +
verification store. Where no observer is registered (e.g. the `simulation`
adapter) nothing new is written and the Core's `observation_unavailable` stands.

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

### D4 health watchdog — `backend/scripts/rmt-watchdog.sh` (not read by the app)

| Variable | Default | Effect | Set by |
|---|---|---|---|
| `RMT_WATCHDOG_HEALTH_URL` | `http://127.0.0.1:8000/health` | Probe the watchdog polls. | crontab / timer |
| `RMT_WATCHDOG_FAILS_BEFORE_RESTART` | `3` | Consecutive **unreachable** polls before `systemctl restart`. | crontab / timer |
| `RMT_WATCHDOG_RESTART_ON_DEGRADED` | `false` | Also count sustained `status: degraded` toward a restart (off by default — a restart doesn't clear a quarantine). | crontab / timer |
| `RMT_WATCHDOG_NOTIFY_URL` | *(optional)* | Webhook for the watchdog's own alerts (JSON POST). | crontab / timer |
| `RMT_WATCHDOG_SERVICE` | `rmt-control-center.service` | Unit to restart. | crontab / timer |

### V4 post-deploy smoke — `backend/scripts/rmt-smoke.sh` (not read by the app)

| Variable | Default | Effect |
|---|---|---|
| `RMT_SMOKE_BASE_URL` | `http://127.0.0.1:8000` | Target. |
| `RMT_SMOKE_TOKEN` | *(optional)* | Operator token — enables the authed check. |
| `RMT_SMOKE_EXPECT_ADAPTER` | `docker` | Asserted against `/health` `runtime.resolved_adapter` (+ `adapter_degraded == false`). |
| `RMT_SMOKE_EXPECT_LOOP` | `any` | `running` \| `stopped` \| `any`. |

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

## Homelab dependency edges — `app/ops/ops_config.py` (T1-2)

| Variable | Default | Effect | Set by |
|---|---|---|---|
| `RMT_HOMELAB_DEPENDENCIES` | *(empty)* | **T1-2.** Operator-declared inter-component dependency edges, `"web:db,cache;api:db"` (`;`-separated `component:dep1,dep2` groups). Unioned into the static all-independent homelab map (`app/homelab/dependencies.py`). A declared edge **activates T13**: an *allowed*-class op (`start`/`create`) on a depended-upon component is forced to human approval. The static map stays all-independent; `GET /agent/status.dependency_map.sources` shows `static` vs `env`. Malformed groups are skipped. | a `deps.conf` drop-in |

The real homelab has **no** inter-container edges (portainer / dozzle /
uptime-kuma each need only dockerd), so this is unset in production. It exists so
a genuine edge can be declared without a code change + redeploy.

## Evidence substrate — `app/core/intelligence/durable_store.py` (T0-1)

| Variable | Default | Effect | Set by |
|---|---|---|---|
| `RMT_EVIDENCE_DB` | `data/governance_evidence.db` | **T0-1.** Path to the shared SQLite database holding the six governance-evidence stores (approval holds/records, authorizations, traces, audit, verifications). Was six JSON files under `app/core/intelligence/**`. `save()` is now one `INSERT`; the file no longer grows by rewrite; crash-atomic via WAL. Tests point this at a throwaway file. | rarely set — a drop-in only if `data/` moves off the working dir |
| `RMT_EVIDENCE_RETENTION_DAYS` | `90` | **E4.** On startup, evidence rows whose `created_at` is older than this are moved from the live DB into an append-only `<table>.archive.jsonl` beside it (`data/`). `<= 0` disables. Archived rows are never deleted — E5 backup captures them. | `auth.conf` or a drop-in |

**Migration:** on a host with pre-T0-1 JSON stores, run
`python3 backend/scripts/rmt-migrate-evidence.py` **once**, after
`backend/scripts/rmt-evidence-backup.sh`. It inserts every JSON record into the
DB (order preserved) and renames each file to `<name>.json.migrated`.
`--reverse` dumps the tables back to JSON in the exact prior format. See
`docs/operations/RMT_EVIDENCE_RECOVERY.md`.

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
├── auth.conf            # S1/S2-lite/O2  (mode 0644 — holds no secret, T0-5)
├── bind-loopback.conf   # S4
├── cap04-loop.conf      # RMT_HOMELAB_LOOP_ENABLED=true
└── cap05-agent.conf     # RMT_AGENT_ENABLED=true, RMT_AGENT_LLM_ENABLED=true

/etc/rmt-control-center/
└── operator_tokens.secret   # the actual token list (mode 0600, root) — T0-5
```
