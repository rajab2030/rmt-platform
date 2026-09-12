# RMT — T0-3: Close the remaining observability gap (approval latency + a dashboards note) — Proposal

**Status:** APPROVED 2026-09-12 (owner approved via explicit selection after
recon; per the roadmap's own process rule, a proposal precedes code — this
is that record).
**Classification:** Above-Core / operational. No `app/core/**` change. No C08.
No reopening of C01–C07.

Governing refs: `docs/RMT_ABOVE_CORE_ROADMAP.md` §4 T0-3,
`docs/RMT_PRODUCTION_READINESS.md` Group O (O1/O3/O4), `AGENTS.md`,
`STEWARD.md`.

---

## 0. Recon findings

| # | Finding |
|---|---|
| 1 | T0-3's objective ("structured logs + a metrics endpoint... decisions/min, holds open, approvals latency, verification outcomes, adapter failures") is **already substantially shipped**, dated 2026-09-08, under different item codes: **O1** structured JSON logging (`backend/app/ops/logging_config.py`), **O3** quarantine/cycle-error/service-down alerting (`backend/app/ops/notifications.py::notify_ops` + `GET /health` + `rmt-heartbeat.sh`), **O4** Prometheus `GET /metrics` (`backend/app/ops/metrics.py`) — all read-only derivation from existing evidence stores, no new dependency. `docs/RMT_ABOVE_CORE_ROADMAP.md` did not cross-reference this; corrected 2026-09-12 (doc-only, no code change) in the same edit that produced this proposal. |
| 2 | Of the objective's five signals, `/metrics` already covers **holds open** (`rmt_approval_holds{status=...}`), **verification outcomes** (`rmt_verifications_total`, `rmt_executed_actions_*`), and **adapter failures** (`rmt_executed_actions_unverified_total` / `state_mismatch`; E3's `adapter_execution_failed` lands in `verification_storage`, already counted). |
| 3 | **decisions/min** — `rmt_approval_records_total{decision=...}` (`backend/app/ops/metrics.py:83-85`) is a cumulative counter, which is the *correct* Prometheus shape for a rate signal — a rate is a scraper-side `rate()` query over a counter, not a server-computed field. Nothing is missing in code; what's missing is the query, which belongs in a dashboards note (finding 5). |
| 4 | **approval latency** — genuinely missing. `ApprovalHold.created_at` (`backend/app/core/intelligence/actions/approval.py:56-58`) and `ApprovalRecord.created_at` (`approval.py:35-37`) both exist; for a manual-approval hold, `record_approval_decision` reuses the hold's `approval_id` for the record (`backend/app/core/intelligence/actions/approval_service.py:74-90`, docstring: "the approval_id is the hold's id"), so the two rows are joinable by `approval_id` — but nothing computes `record.created_at - hold.created_at` anywhere in the codebase today. |
| 5 | **"a minimal dashboards note"** — named in the original T0-3 scope, never written. `docs/operations/` holds `AGENT_API.md`, `CONFIG.md`, `CI.md`, `DEPLOY.md`, `PREREQUISITES.md`, `RMT_EVIDENCE_RECOVERY.md`, `RMT_PLATFORM_RECOVERY.md`, `SECRETS.md`, `baseline.md` — no metrics/dashboards doc. |
| 6 | Test convention for `app/ops/metrics.py` (`backend/app/ops/testing/test_metrics.py`): a `TestClient(main_app.app)` hits the real `/metrics` route end-to-end, then `monkeypatch.setattr(metrics.<store>, "get_all", lambda: [...])` injects fake rows for assertions, plus a `_boom()` monkeypatch to prove fail-open (scrape-error counter increments, `rmt_up` still present). No on-disk fixtures. |

## 1. Objective

Close the two real gaps found in recon (findings 4–5) with the smallest
addition consistent with the existing `/metrics` module's design — no new
dependency, same fail-open-per-signal pattern, same read-only-derivation
boundary. Do **not** re-implement decisions/min as a server-side rate
(finding 3) — that would add a sliding-window state machine to a stateless
scrape handler for a value Prometheus's own `rate()` already computes
correctly from the existing counter.

## 2. In scope

1. **`rmt_approval_latency_seconds_sum` / `rmt_approval_latency_seconds_count`**
   in `backend/app/ops/metrics.py` — a minimal (no-quantile) Prometheus
   summary. For every `ApprovalRecord` whose `approval_id` matches an
   `ApprovalHold` in `approval_hold_storage` (i.e. every decision that
   resolved an actual manual hold, not an auto-approval that never held),
   compute `(record.created_at - hold.created_at).total_seconds()`; sum and
   count them. Labelled by `decision` (`approved`/`rejected`) so a rejected
   hold's latency doesn't dilute an approved one's. Wrapped in the same
   `try/except → errors += 1` pattern as every other section of
   `render_prometheus()` — a broken store degrades this one signal, not the
   scrape.
2. **`docs/operations/METRICS.md`** — the minimal dashboards note the
   original scope named: every `rmt_*` metric with its meaning, the PromQL
   for decisions/min (`rate(rmt_approval_records_total[5m]) * 60`) and
   average approval latency
   (`rate(rmt_approval_latency_seconds_sum[5m]) / rate(rmt_approval_latency_seconds_count[5m])`),
   and the two existing alert conditions already live in O2/O3
   (`RMT_NOTIFY_WEBHOOK_URL` held-action / quarantine alerts) referenced
   rather than duplicated. Linked from `README.md` alongside `AGENT_API.md`.

## 3. Explicitly OUT of scope

- No server-computed decisions/min rate (finding 3 — PromQL already covers
  it; would be a needless stateful addition to a stateless handler).
- No histogram buckets for latency — sum+count is sufficient for an average
  at homelab scale; a real percentile view is a P-B (evidence console)
  concern, not this item.
- No actual Grafana/Prometheus deployment or scrape-config file — the note
  documents the queries; standing up a scraper is an operator action already
  covered by O4's "Required action" (`docs/RMT_PRODUCTION_READINESS.md`).
- No change to `logging_config.py` or `notifications.py` — O1/O3 are done as
  shipped.

## 4. Boundary

- `backend/app/ops/metrics.py` + `backend/app/ops/testing/test_metrics.py` +
  `docs/operations/METRICS.md` + a `README.md` link. No `app/core/**` change.
- Read-only: only `.get_all()` calls against stores already read by this
  module (`approval_hold_storage`, `approval_record_storage`); no new store,
  no new evidence category, no write path.
- No test opens the real evidence DB (existing `test_metrics.py` pattern —
  monkeypatched `get_all`, never a real file).

## 5. Done when

- `/metrics` exposes `rmt_approval_latency_seconds_sum` and
  `rmt_approval_latency_seconds_count`, labelled by `decision`; a broken
  store degrades only this signal (scrape-error counter increments, `rmt_up`
  still 1).
- `docs/operations/METRICS.md` exists, is linked from `README.md`, and lists
  every metric currently in `render_prometheus()` (not just the new two).
- Full backend suite green (baseline 522 + new tests); `ruff check .` clean;
  no `app/core/**` diff.

## 6. Tests

- `test_render_computes_approval_latency` — monkeypatch
  `approval_hold_storage.get_all` / `approval_record_storage.get_all` with a
  hold/record pair sharing an `approval_id` and a known `created_at` delta;
  assert the `_sum`/`_count` lines match.
- `test_latency_excludes_records_without_a_matching_hold` — a record whose
  `approval_id` has no corresponding hold (auto-approval path) contributes
  to neither `_sum` nor `_count`.
- `test_latency_survives_a_broken_store` — same `_boom()` pattern as the
  existing fail-open test, targeted at the new section.
- Regression: existing `test_metrics.py` cases unchanged.

## 7. Validation plan

- New tests pass; full suite stays green.
- `ruff check .` clean; `import app.main` clean.
- Manual: `curl localhost:8000/metrics` on the live instance after deploy,
  confirm the two new lines are present and well-formed.

---

*Above-Core operational item. Does not reopen or modify C01–C07. Does not
create a Core milestone. Not authorized until the owner approves this
proposal.*

🤖 Generated with [Claude Code](https://claude.com/claude-code)
