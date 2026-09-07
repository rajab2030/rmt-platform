# RMT Control Center — Configuration Reference

Every `RMT_*` environment variable the backend reads, its default, effect, and
which systemd drop-in sets it. Above-Core / operational (production-readiness
item **D5**).

Drop-ins live in `/etc/systemd/system/rmt-control-center.service.d/`. After any
change: `sudo systemctl daemon-reload && sudo systemctl restart
rmt-control-center.service`.

---

## Operator authentication — `app/ops/ops_config.py` (P0: S1 / S2-lite)

| Variable | Default | Effect | Set by |
|---|---|---|---|
| `RMT_AUTH_ENABLED` | `true` | Master switch. `false` is a **local-dev only** escape hatch — leaves every mutating route open. | `auth.conf` |
| `RMT_OPERATOR_TOKENS` | *(empty)* | `name:token` pairs, comma-separated. **With auth enabled and this empty, the app refuses to start.** The matched `name` is recorded as `authorized_by` / `approved_by` / `granted_by` in the evidence. | `auth.conf` |

## Held-action notifications — `app/ops/ops_config.py` (P0: O2)

| Variable | Default | Effect | Set by |
|---|---|---|---|
| `RMT_NOTIFY_WEBHOOK_URL` | *(empty)* | When set, a `manual_approval_required` outcome is POSTed as JSON here (5 s, fail-open). Unset → logged only. | `auth.conf` |
| `RMT_NOTIFY_TIMEOUT_SECONDS` | `5` | Webhook POST timeout. | `auth.conf` |
| `RMT_NOTIFY_MIN_INTERVAL_SECONDS` | `60` | Per `(kind, component, approval_id)` de-dupe window — stops the loop re-alerting the same hold every cycle. | `auth.conf` |

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

---

## Live drop-in inventory (expected after P0)

```
/etc/systemd/system/rmt-control-center.service.d/
├── auth.conf            # S1/S2-lite/O2  (mode 0600, root)
├── bind-loopback.conf   # S4
├── cap04-loop.conf      # RMT_HOMELAB_LOOP_ENABLED=true
└── cap05-agent.conf     # RMT_AGENT_ENABLED=true, RMT_AGENT_LLM_ENABLED=true
```
