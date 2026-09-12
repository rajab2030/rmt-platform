# RMT — Metrics & Dashboards

`GET /metrics` (unauthenticated) exposes RMT's own operational state in
Prometheus text format (`text/plain; version=0.0.4`). It is a **read-only**
derivation from the operational-loop status object and the durable evidence
stores — no new evidence category, no write path, no `app/core/**` code.
Source: `backend/app/ops/metrics.py`.

Every section is independently wrapped: a broken store increments
`rmt_metrics_scrape_errors_total` and is skipped rather than failing the
whole scrape. `rmt_up 1` is always present while the process is serving.

## Metric reference

| Metric | Type | Labels | Meaning |
|---|---|---|---|
| `rmt_up` | gauge | — | `1` while the process is serving `/metrics`. |
| `rmt_loop_enabled` | gauge | — | Whether the CAP-04 operational loop is enabled. |
| `rmt_loop_running` | gauge | — | Whether the loop is currently running. |
| `rmt_loop_cycles_total` | counter | — | Loop cycles completed. |
| `rmt_loop_cycle_error` | gauge | — | `1` if the last loop cycle raised. |
| `rmt_loop_quarantined_components` | gauge | — | Components currently quarantined by the loop. |
| `rmt_approval_holds` | gauge | `status` | Approval holds on disk, by status (`pending`/`approved`/`rejected`) — the manual-approval queue depth. |
| `rmt_approval_records_total` | counter | `decision` | Approval decisions recorded, cumulative. |
| `rmt_approval_latency_seconds_sum` / `_count` | counter | `decision` | Sum/count of `record.created_at − hold.created_at` for every decision that resolved an actual manual hold (an auto-approval never held, so it contributes to neither). |
| `rmt_verifications_total` | counter | `status` | Post-execution verification outcomes. |
| `rmt_executions_total` | counter | `adapter` | Governed executions that reached an adapter. |
| `rmt_authorizations_total` | counter | — | Execution authorizations issued. |
| `rmt_executed_actions_total` / `_verified_total` / `_unverified_total` / `_state_mismatch_total` | counter | `adapter`, `operation` | Effective-status verification index: one row per execution, so an executed action is counted once even where the Core and above-Core each leave a record. |
| `rmt_agent_enabled` | gauge | — | Whether the agent surface (CAP-05) is enabled. |
| `rmt_agent_active_grants` | gauge | — | Active (unconsumed, unexpired) authority grants. |
| `rmt_metrics_scrape_errors_total` | counter | — | Store-read failures during this scrape; the corresponding section was skipped. |

## Derived signals (PromQL, computed by the scraper — not server-side)

RMT exposes counters and timestamps; rates and averages are queries over
them, not fields RMT computes itself — the correct Prometheus shape, and it
keeps `/metrics` a stateless read on every scrape.

- **Decisions per minute:**
  `rate(rmt_approval_records_total[5m]) * 60`
- **Average approval latency (seconds), by decision:**
  `rate(rmt_approval_latency_seconds_sum[5m]) / rate(rmt_approval_latency_seconds_count[5m])`
- **Held-queue depth right now:**
  `rmt_approval_holds{status="pending"}`
- **Verification failure rate:**
  `rate(rmt_verifications_total{status=~"state_mismatch|observation_unavailable|adapter_execution_failed"}[5m])`
- **Scrape health:**
  `rmt_metrics_scrape_errors_total` — alert on any increase; it means a
  store was unreadable during a scrape, not that the platform mis-executed
  anything.

## Alerting

Metric-threshold alerting on a Prometheus/Alertmanager stack is not set up
by this platform — that's operator infrastructure, pointed at `:8000/metrics`
(or via Caddy). RMT's own alerting is out-of-band and already live:

- **Held actions / agent proposals** — `notify_held` (O2,
  `backend/app/ops/notifications.py`) fires a webhook per new hold; set
  `RMT_NOTIFY_WEBHOOK_URL` to route it to a real channel.
- **Loop quarantine / cycle error / service down** — `notify_ops` (O3, same
  module) plus `GET /health` + `backend/scripts/rmt-heartbeat.sh` (a cron
  dead-man's-switch).

See `docs/operations/CONFIG.md` for every `RMT_NOTIFY_*` / `RMT_HEARTBEAT_*`
variable.

## Scraping

Point a Prometheus server (or any scraper) at `GET /metrics` — no
authentication, matching a scraper/heartbeat use case. Example
`scrape_configs` entry:

```yaml
- job_name: rmt
  metrics_path: /metrics
  static_configs:
    - targets: ["localhost:8000"]
```
