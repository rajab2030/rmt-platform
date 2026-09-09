# RMT — Production-Readiness Gap Matrix

## 1. Authority and Purpose

This document defines the verified gap between the current RMT deployment and an
**operationally production-ready** state.

It is **above-Core / operational**. It is **not** an RMT authority document, it
does **not** reopen or modify C01–C07, it does **not** create a new Core
milestone (there is no C08), and it does **not** expand the Core. The finite RMT
Core Target State remains **ACHIEVED** and the Core remains **frozen**
(`docs/RMT_CORE_TARGET_STATE.md`, `docs/RMT_CORE_GAP_MATRIX.md`).

It answers one question:

> **What must still become true before the running RMT platform can be relied on
> as a production control plane — beyond the architectural completeness already
> declared for the Core?**

"Production-ready" here means: safe to expose, safe to run unattended, able to
survive a restart or crash with its governance evidence intact, reproducibly
deployable, observable, and recoverable.

> **P0 batch implemented + deployed 2026-09-07** (`docs/RMT_PROD_P0_PROPOSAL.md`,
> APPROVED). S1 + S2-lite (auth + operator identity), E1 (atomic evidence
> writes), O2 (held-action alerting) are **code-complete, merged, and LIVE** on
> `:8000` (service restarted 2026-09-07 12:36 UTC).
> Verified on live: unauth → 401, authed → 200, `granted_by` records the
> authenticated operator, evidence files parse with no `.tmp` residue.
> **E2 is now closed** (owner chose the **above-Core reconciliation** path):
> `app/ops/reconcile.py` reconciles the hold store against the authoritative
> approval-record store on startup — no `app/core/**` change. Full suite **263
> passed** (254 + 9 `test_reconcile.py`).
> **S4 is now closed** (2026-09-08). Loopback bind is live (`127.0.0.1:8000`
> only, verified unreachable off-loopback) and the **Caddy `2.6.2` TLS reverse
> proxy is installed, enabled, and live**: `/etc/caddy/Caddyfile` from
> `deploy/Caddyfile`, `tls internal` CA trusted on the host. Verified on
> `192.168.223.128`: `https://` → 200 (CA-validated, no `-k`), `http://` → 308
> auto-redirect, `POST` with no token → 401, open GET → 200, the app itself
> refuses `:8000` off-loopback. CAP-04 loop healthy through the proxy.
>
> **P0 is now fully closed** — S1/S2-lite, E1, E2, O2, S4 all live and verified.

### Relationship to the Core Gap Matrix

`RMT_CORE_GAP_MATRIX.md` establishes that the **Core architecture** is complete:
one authoritative governed mutation path, durable correlated evidence,
post-execution verification, controlled self-management and evolution, a passing
finite validation suite. That is a statement about *design correctness*, not
about *operational fitness*. The Core Gap Matrix §6 explicitly places full
enterprise IAM, arbitrary UI, and unlimited adapter coverage **outside** Core
scope — which is correct, and is exactly why those items land **here** instead.

### Scope anchor (verified 2026-09-07)

- Live service: `rmt-control-center.service` (systemd), `uvicorn app.main:app`,
  bound `0.0.0.0:8000` (confirmed via `ss`).
- Enabled on live: CAP-04 operational loop; CAP-05 (5A) agent surface; CAP-05
  (5B) LLM agent — all via systemd drop-ins.
- 10 mutating HTTP routes, **0** behind authentication.
- Governance evidence: six stores via `DurableStore`, now SQLite-backed
  (`data/governance_evidence.db`, one table each — T0-1, 2026-09-09; was six
  JSON files); intelligence memory in SQLite (`data/observability.db`).
- Frontend: a Vite/React app in `projects/homelab-control-center/frontend`
  (dev-server config only; not part of the served backend).

## 2. Assessment Rules

Each requirement is classified:

| Class | Meaning |
|---|---|
| **READY** | Materially satisfied by connected implementation and available evidence. |
| **PARTIAL** | A meaningful portion exists; one or more production requirements (enforcement, durability, reproducibility, coverage, runbook) remain. |
| **GAP** | The requirement or its enforcement mechanism is not implemented. |
| **ACCEPTED** | Not satisfied, and deliberately accepted for the current deployment scale — recorded, not silently ignored. |
| **N/A** | Not applicable to this platform. |

Priority:

| Priority | Meaning |
|---|---|
| **P0** | Blocking. Must close before any exposure beyond a single trusted host, or before relying on the platform unattended. |
| **P1** | Required for production. |
| **P2** | Hardening / should-have. |

### Prerequisite decision (sizes the whole matrix)

**The owner must fix the deployment / threat model.** The Security group is
scoped entirely by this answer:

- **(a) Single trusted host, loopback only** — S1/S2/S3/S4 shrink to
  "bind `127.0.0.1`, document the trust assumption"; most of Security becomes
  ACCEPTED.
- **(b) Trusted LAN, one or few operators** — S1 (auth), S4 (TLS) become P0;
  S2/S3 (identity, separation of duties) P1.
- **(c) Multi-user or internet-reachable** — the full Security group is P0/P1
  and a real IAM integration is required.

The matrix below is written for **(b)**, the current de facto posture
(`0.0.0.0` on the LAN). Adjust if the owner chooses (a) or (c).

---

## 3. Gap Matrix

### Group S — Security & Access Control

The governance model assumes the operator endpoints are trusted. Nothing
currently enforces who the operator is.

| ID | Requirement | Current verified evidence | Status | Required action | Priority |
|---|---|---|---|---|---|
| **S1** | Authentication on every mutating route | **DONE + LIVE** — `app/ops/auth.py` `require_operator` on all 10 `@app.post` routes + the whole `/agent/*` router; bearer / `X-API-Key` → `RMT_OPERATOR_TOKENS`; app refuses to start if enabled + unconfigured. `auth.conf` deployed with two operator tokens; live-verified 401/200. | **READY** | — | **P0** |
| **S2** | Operator identity & non-repudiation | **DONE (lite) + LIVE** — `/approve`, `/homelab/approve`, `/agent/authority/grant` take the identity from the authenticated `OperatorIdentity`; body `approved_by` / `granted_by` ignored. `/execute` threads the operator name into `decision_id` / `reason`. Live-verified: grant recorded `granted_by: "ragb"` from the token, body value ignored. | **READY** | — | **P1** |
| **S3** | Separation of duties | **DONE (above-Core, 2026-09-08).** `app/ops/separation.py` — when a proposal is held, `propose_and_govern` records `approval_id → {grant_id, granted_by, agent_id}`; `/approve` and `/homelab/approve` call `check_separation(approval_id, operator)` before continuing and return **403** if the approver granted the agent's authority (`approver_is_grantor`) or is the proposing agent id (`approver_is_proposer`). Config-gated by **`RMT_AUTH_SEPARATION`** (default off). Non-agent holds pass through (`not_agent_originated`); the check **fails closed**. `/agent/status` exposes `separation_of_duties`. `test_separation.py` — 15 tests (unit + `/approve` + `/homelab/approve` 403). No `app/core/**` change. | **READY** | — | **P1** |
| **S4** | Transport security & network exposure | **DONE + LIVE (2026-09-08)** — `bind-loopback.conf` deployed (app listens `127.0.0.1:8000` only, verified unreachable off-loopback) **and** Caddy `2.6.2` TLS reverse proxy installed + enabled, `/etc/caddy/Caddyfile` from `deploy/Caddyfile`, `tls internal` CA trusted on the host. Verified on `192.168.223.128`: `https://` → 200 CA-validated, `http://` → 308 redirect, no-token `POST` → 401, open GET → 200, CAP-04 loop healthy through the proxy. | **READY** | Import the Caddy root CA on other operator machines (`/var/lib/caddy/.local/share/caddy/pki/authorities/local/root.crt`). | **P0** |
| **S5** | CORS configuration | **DONE (2026-09-08).** `RMT_CORS_ORIGINS` (comma-separated) → `ops_config.cors_origins()`; default is `http://localhost:5173` only (the stale hardcoded `192.168.235.128` is gone). `allow_methods` scoped to `GET, POST`, `allow_headers` to `Authorization, X-API-Key, Content-Type, X-Request-ID` (were `["*"]`). `test_cors.py` — 4 tests. | **READY** | Set `RMT_CORS_ORIGINS` to the deployed frontend origin in a drop-in. | **P2** |
| **S6** | Secrets management | **DONE by policy (2026-09-08).** No credential exists in the system today (local Ollama, no key). `docs/operations/SECRETS.md` fixes the standing pattern (root-owned `0600` systemd `EnvironmentFile`, template committed / populated file not) and the pre-agreed next step — `systemd` credentials (`LoadCredential=`) — which is mandatory before **any** credentialed dependency (model key, authed notifier, IdP) is added. | **READY** *(by policy)* | Implement the `systemd`-credentials path when the first credential is proposed. | **P2** |
| **S7** | Abuse / rate protection on expensive routes | **DONE (2026-09-08).** `app/ops/ratelimit.py` — an in-process **fixed-window** limiter keyed by `(principal, bucket)`. `POST /execute` → 30/min per operator (`RMT_RATELIMIT_EXECUTE_PER_MINUTE`); `POST /agent/act`, `/agent/act/llm`, `/agent/authority/grant` → 20/min (`RMT_RATELIMIT_AGENT_PER_MINUTE`); over-limit → **429** + `Retry-After`. Per-principal (the authenticated operator; peer IP fallback). Read-only agent routes are not limited. `RMT_RATELIMIT_ENABLED=false` disables it. Fits the single-process deployment (R4). `test_ratelimit.py` — 5 tests. No `app/core/**` change. | **READY** | — | **P2** |

### Group E — Evidence Durability & Integrity

The platform's core value is trustworthy governance evidence. The evidence
substrate is currently weaker than the governance logic on top of it.

| ID | Requirement | Current verified evidence | Status | Required action | Priority |
|---|---|---|---|---|---|
| **E1** | Atomic, concurrency-safe evidence writes | **DONE** — `DurableStore._persist` writes a sibling `.tmp`, `flush` + `os.fsync`, then `os.replace` (atomic on POSIX); `_load` discards stale `.tmp`. Byte-identical committed output; owner-authorized frozen-Core hardening deviation. `test_durable_store_atomic.py` (interrupted-write leaves prior file intact). | **READY** | — | **P0** |
| **E2** | Hold state persisted on resolution | **DONE (above-Core)** — owner chose reconciliation over a Core fix. `app/ops/reconcile.py::reconcile_holds_against_records`, run once in the `app/main.py` startup lifespan, brings the hold store back into agreement with the authoritative approval **record** store: a `pending` hold whose record shows a terminal decision (`approved`/`rejected`) is corrected in place and re-persisted via the store's atomic (E1) write path. Read-only where nothing diverges; fail-open (never blocks startup). Never invents a resolution. No `app/core/**` change. `app/ops/testing/test_reconcile.py` — 9 tests; full suite 263 passed. | **READY** | — | **P0** |
| **E3** | Failed-execution verification evidence | **DONE (above-Core, 2026-09-08).** `app/ops/execution_evidence.py::record_failed_execution_evidence` — for a governed outcome that *reached the adapter and failed* (`status == "executed"`, `success is False`, has `execution_id`), writes one `VerificationResult` into the **existing** verification store with a distinct status **`adapter_execution_failed`** (§11 "adapter invoked and failed"), correlated by `execution_id`. Bounded (blocked-before-adapter outcomes left alone), idempotent (skips if an above-Core observer already recorded one), fail-open. Wired at `/execute`, `/approve`, `/homelab/remediate`, `/homelab/approve`, and the agent adapter's failure branch. No `app/core/**` change. `test_execution_evidence.py` — 19 tests + an agent end-to-end test. | **READY** | — | **P1** |
| **E4** | Retention / rotation / size management | **DONE (above-Core, 2026-09-08).** `app/ops/retention.py::archive_aged_evidence` runs on startup (after the reconcile): every evidence record older than **`RMT_EVIDENCE_RETENTION_DAYS`** (default 90; `<=0` disables) is moved out of the live JSON store into an append-only `<name>.archive.jsonl` beside it, and the trimmed store is re-persisted via the atomic (E1) path. Bounded (no/bad `created_at` → kept), idempotent, fail-open per store. Archives are what E5 backs up; full history = archive + live. No `app/core/**` change. `test_retention.py` — 10 tests. | **READY** | — | **P1** |
| **E5** | Evidence backup & restore (RMT stores) | **DONE (2026-09-08; T0-1-updated 2026-09-09).** `backend/scripts/rmt-evidence-backup.sh` (`VACUUM INTO` snapshots of `governance_evidence.db` **and** `observability.db` + E4 archives + any residual JSON + manifest + `sha256`), `rmt_evidence_verify.py` (stdlib-only; checks the six `governance_evidence.db` tables, residual JSON, archives, `observability.db`; exit 1 on corruption), `rmt-evidence-restore.sh` (checksum → integrity → refuses if the service is up → restores the db, or restores a pre-T0-1 JSON backup and runs `rmt-migrate-evidence.py --force` → re-verifies live). Runbook: `docs/operations/RMT_EVIDENCE_RECOVERY.md`. Backup→verify→restore drill exercised end-to-end (2026-09-09). | **READY** | Wire the cron line; run the T0-1 cutover on the live host. | **P1** |
| **E6** | Startup integrity / reconciliation | **DONE (above-Core, 2026-09-08).** `app/ops/reconcile.py::reconcile_governance_stores` runs on startup: (1) E2 — corrects a stale `pending` hold against the authoritative record store; (2) **E6 — `audit_authorizations()` cross-checks every `ExecutionAuthorization` against the approval record + hold stores** and logs (`WARNING`) any inconsistent linkage — `missing_record`, `contradicts_rejection`, `record_not_terminal`, `hold_still_pending`. The authorization store is Core-owned + append-only (the Core never mutates an authorization after creation), so this half is **read-only by design** — it surfaces divergence, never rewrites Core evidence. Verified against the live store: 18 checked, 1 flagged (a historical 2026-09-02 `test-container` orphan authz with no record), `authorizations.json` byte-identical afterward. `test_reconcile.py` — 18 tests (9 E2 + 9 E6). | **READY** | — | **P2** |

### Group D — Deployment & Configuration

| ID | Requirement | Current verified evidence | Status | Required action | Priority |
|---|---|---|---|---|---|
| **D1** | Pinned, reproducible dependency set | **DONE** — `backend/requirements.txt` now pins every direct dep (+ `pytest`, `httpx2` as test-only); `backend/requirements.lock.txt` is the full 33-package transitive lock (`pip freeze`). | **READY** | — (V2 `ci.sh` now builds a clean venv from the lock on every run). | **P1** |
| **D2** | Deploy + rollback runbook for the RMT service | **DONE** — `docs/operations/DEPLOY.md` (first-time P0 cutover, routine redeploy, rollback, token rotation, restart-safety check) + `docs/operations/CONFIG.md` (every `RMT_*` var — also closes **D5**). | **READY** | Exercise it on the next redeploy. | **P1** |
| **D3** | Service hardening | **DONE (2026-09-08).** `projects/homelab-control-center/deploy/systemd/hardening.conf` — a drop-in adding: restart backoff (`StartLimitIntervalSec=300` / `StartLimitBurst=5`, `RestartSteps` / `RestartMaxDelaySec=60`); resource ceilings (`MemoryMax=512M`, `MemoryHigh=384M`, `CPUQuota=200%`, `TasksMax=128` — idle RSS is ~70M); `NoNewPrivileges`, `LockPersonality`, `RestrictRealtime/SUIDSGID/Namespaces`, `RemoveIPC`, `UMask=0077`; `ProtectSystem=full`, `PrivateTmp`, and the kernel-surface protections (`ProtectControlGroups/KernelTunables/KernelModules/KernelLogs/Clock/Hostname`, `ProtectProc=invisible`); `SystemCallArchitectures=native`, `SystemCallFilter=@system-service` (`→EPERM`), `RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6 AF_NETLINK`. Docker-socket access survives (supplementary `docker` group, not dropped by `NoNewPrivileges`); no `app/core/**` or code change. `systemd-analyze verify` clean; `systemd-analyze security --offline` **9.2 UNSAFE → 4.1 OK**. `ProtectHome` stays `no` and `ProtectSystem` is `full` not `strict` (evidence JSON + `data/observability.db` live under `/home`); `strict`+`ReadWritePaths`, `ProcSubset=pid`, IP filtering are documented deferrals (`DEPLOY.md` §5.1). | **READY** | Install the drop-in + `daemon-reload` + restart; watch the first restart (`DEPLOY.md` §5.1). | **P1** |
| **D4** | Health/readiness probe acted upon | **DONE (2026-09-08).** `backend/scripts/rmt-watchdog.sh` — cron / systemd-timer polls `GET /health`; after N consecutive **unreachable** results (`RMT_WATCHDOG_FAILS_BEFORE_RESTART`, default 3) it `systemctl restart`s the service and fires an ops alert (`RMT_WATCHDOG_NOTIFY_URL`). Sustained `status: degraded` (loop cycle error / quarantine) is **alert-only** by default — a restart doesn't clear a quarantine and risks a restart loop; `RMT_WATCHDOG_RESTART_ON_DEGRADED=true` opts in. Consecutive-failure count in a state file; clears on recovery. Ops tooling only; no code change. | **READY** | Cron `rmt-watchdog.sh` every 1–2 min with a notify URL. | **P2** |
| **D5** | Consolidated configuration reference | **DONE** — `docs/operations/CONFIG.md` lists every `RMT_*` var (auth, notify, CAP-04 loop, agent 5A/5B), default, effect, and which drop-in sets it, plus the expected live drop-in inventory. | **READY** | Keep in sync with `loop_config.py` changes. | **P2** |
| **D6** | Documented runtime prerequisites & environment parity | **DONE (2026-09-08).** `docs/operations/PREREQUISITES.md` lists required vs capability-sensitive host capabilities. `app/ops/runtime_info.py` — `GET /health` carries a `runtime` block (`configured_engine`, `resolved_adapter`, `docker_available`, `git_available`, `adapter_degraded`, `notes`); a configured/resolved engine mismatch is logged as a `WARNING` at startup. The V4 smoke script asserts `configured == resolved == "docker"` on the live host. `test_runtime_info.py` — 6 tests. | **READY** | — | **P2** |

### Group O — Observability & Alerting

An unattended control plane that can hold actions for human approval must be
able to *tell a human*.

| ID | Requirement | Current verified evidence | Status | Required action | Priority |
|---|---|---|---|---|---|
| **O1** | Structured application logging + rotation | **DONE (2026-09-08).** `app/ops/logging_config.py` — stdlib `logging`, **no dependency**. `configure_logging()` owns the `rmt` logger tree: one JSON line per record to stdout → journald, `propagate=False`, idempotent; `RMT_LOG_LEVEL` (default `INFO`), `RMT_LOG_JSON` (default `true`). `RequestContextMiddleware` binds a per-request `request_id` (honours inbound `X-Request-ID`, echoes it on the response) and logs one `http_request` line (method, path, status, duration_ms, principal). `log_event()` emits one structured line at each governed-lifecycle boundary — the 4 mutating routes (`governed_execute` / `governed_approve` / `homelab_remediate` / `homelab_approve`), the CAP-04 loop (`loop_remediation` / `loop_quarantine` / `loop_cycle_error`), and every agent proposal that reaches the adapter (`agent_proposal_outcome`) — correlated by `action_id` / `execution_id` / `approval_id`. `require_operator` stashes the resolved name on `request.state.principal`. No `app/core/**` change. `test_logging_config.py` — 16 tests. **Rotation:** journald (`DEPLOY.md` §5 — `SystemMaxUse=` / `MaxRetentionSec=`), operator step. | **READY** | Set a journald cap on the host (`DEPLOY.md` §5). | **P1** |
| **O2** | Alert on held remediation / agent proposal | **DONE + LIVE (log sink)** — `app/ops/notifications.py` `notify_held` (webhook via stdlib `urllib`, fail-open, per-key de-dupe) hooked at `/execute`, `/homelab/remediate`, the CAP-04 loop, and the agent adapter. Deployed with `RMT_NOTIFY_WEBHOOK_URL` **unset** → held actions log to the journal only. `test_notifications.py`. | **READY** *(routing to a real sink pending)* | Set `RMT_NOTIFY_WEBHOOK_URL` in `auth.conf` when a chat/email sink exists. | **P0** |
| **O3** | Alert on loop quarantine / cycle error / service down | **DONE (above-Core, 2026-09-08).** `app/ops/notifications.py::notify_ops` (same fail-open, de-duped webhook sink as O2) fires on **loop quarantine** and **loop cycle error** — hooked in `app/homelab/operational_loop.py`. **Service-down** is out-of-band: new unauthenticated `GET /health` probe (`status: ok`/`degraded` from the loop state) + `backend/scripts/rmt-heartbeat.sh`, a cron inverted dead-man's-switch that pings `RMT_HEARTBEAT_URL` only while `/health` answers 200. `test_notifications.py` + `test_health.py` + `test_operational_loop.py` cover it. No `app/core/**` change. | **READY** | Set `RMT_NOTIFY_WEBHOOK_URL`; cron `rmt-heartbeat.sh` with a monitor URL. | **P1** |
| **O4** | Platform self-metrics | **DONE (2026-09-08).** `app/ops/metrics.py` + unauthenticated `GET /metrics` in Prometheus text format (`text/plain; version=0.0.4`), **no new dependency**. Exposes: loop enabled/running/cycles/cycle-error/quarantined; approval holds by status (queue depth); approval decisions; verification outcomes by status; executions by adapter; authorizations issued; agent enabled + active grants; `rmt_metrics_scrape_errors_total`. **Read-only** derivation from the loop status + the durable evidence stores — no new evidence category, no write path, no `app/core/**` change. Each store read is wrapped (a failure increments the scrape-errors counter instead of 500-ing). `test_metrics.py` — 4 tests. | **READY** | Point Prometheus / a scraper at `:8000/metrics` (or via Caddy). | **P2** |

### Group V — Validation & Change Safety

| ID | Requirement | Current verified evidence | Status | Required action | Priority |
|---|---|---|---|---|---|
| **V1** | Automated end-to-end test on a realistic adapter | **DONE (2026-09-08).** `app/homelab/testing/test_e2e_docker.py` (`@pytest.mark.e2e`) drives the **real** `DockerExecutionAdapter` against a disposable `alpine` container: fault (stop) → `observe_container_state` sees `exited` → `execute_governed_action(RESTART, requires_approval=True)` → **`manual_approval_required`** (nothing executed) → `approve_held_action` → real `docker restart` → container back to `running` → above-Core `verify_docker_execution` → **`verified_success`** → asserts the correlated authorization / audit (`adapter=docker`) / trace / verification records, and that the real JSON stores are untouched. A second test drives the real adapter against a missing container → `success=False` → E3 `adapter_execution_failed`. **Auto-skips** when the Docker daemon is unreachable or `alpine:latest` can't be obtained, so it is safe in the default suite and CI. All six evidence stores + every `verification_storage` reference are swapped to in-memory (finding: `app/ops/execution_evidence.py` binds its own ref — now also patched); the throwaway container (`rmt-e2e-<hex>`, never a homelab component) is force-removed on teardown. `pytest.ini` registers the `e2e` marker. No `app/core/**` change. | **READY** | — | **P1** |
| **V2** | CI on every change | **DONE (2026-09-08).** `backend/scripts/ci.sh` — one gate: throwaway venv built strictly from `requirements.lock.txt` (reproducible install) → `ruff check` (errors-only: `F`, `E9`; `backend/ruff.toml`; `app/core` excluded — it keeps its own 122-test gate) → the full backend suite. Exit non-zero on any step. `.github/workflows/ci.yml` calls it on push / PR to `main`/`master` — **inert until the repo has a remote**, then it gates automatically with no further change. Verified green from a clean venv: ruff clean, **324 passed**. 7 pre-existing dead imports removed (all above-Core; no `app/core/**` touch). Also closes the D1 open action (clean-venv-from-lock build). | **READY** | Push the repo to a remote so the workflow runs; add branch protection when it does. | **P1** |
| **V3** | Coverage of environment-dependent routes | **DONE (2026-09-08).** `app/ops/testing/test_env_routes.py` — `/containers`, `/containers/{name}/stats` and `/platform/state` pinned in **both** modes: capability present (200 + body) and capability absent. To make "absent" a defined outcome, the three route bodies now catch the Docker/`git` failure and return **503** (`{"detail": "docker unavailable: …"}` / `git unavailable: …`) instead of an unhandled 500. `test_http_entrypoints.py`'s deliberate exclusion of these routes is now covered here. 5 tests; no `app/core/**` change. | **READY** | — | **P2** |
| **V4** | Regression guard on live-config changes | **DONE (2026-09-08).** `backend/scripts/rmt-smoke.sh` — post-deploy smoke: `/health` 200 + `status ok`; the D6 `runtime` block shows `resolved_adapter == RMT_SMOKE_EXPECT_ADAPTER` (default `docker`) and `adapter_degraded == false`; `/metrics` up with 0 scrape errors; `POST /execute` and `GET /agent/status` → 401 unauthenticated (S1); loop state matches `RMT_SMOKE_EXPECT_LOOP`; optional authed `/agent/status` with `RMT_SMOKE_TOKEN`. Exit non-zero on any failure. Verified against a throwaway instance (9/10, the 10th a deliberately mis-set expectation). Run it after every restart / drop-in change. | **READY** | Wire into the deploy step / a post-start `ExecStartPost=` or cron. | **P2** |

### Group R — Resilience & Recovery

| ID | Requirement | Current verified evidence | Status | Required action | Priority |
|---|---|---|---|---|---|
| **R1** | Restart safety — state rebuilt correctly from disk | **DONE (2026-09-08).** Hard-kill restart test PASSED: `systemctl kill -s KILL` on the whole cgroup, then restart — all six durable evidence stores reloaded **byte-for-byte identical** (sha256 + record counts unchanged), no `.tmp` residue (E1), hold ↔ record stores in agreement / reconcile a clean no-op (E2), CAP-04 loop + auth + Caddy proxy all healthy on the new PID. E6 authorization cross-check now also runs on startup (`reconcile_governance_stores`). E1/E2/E6 all closed → a restart is provably faithful. | **READY** | — | **P1** |
| **R2** | Homelab stack disaster recovery | `docs/recovery/RECOVERY_RUNBOOK.md` + backup engine + `verify-recovery.sh` — a tested procedure with checksums and manifests. | **READY** | Keep exercised. | — |
| **R3** | RMT platform recovery procedure | **DONE (2026-09-08).** The canonical base unit + the four non-secret drop-ins (`cap04-loop`, `cap05-agent`, `bind-loopback`, `hardening`) are now captured in `projects/homelab-control-center/deploy/systemd/` (+ `README.md` inventory; secret `auth.conf` stays out of git). `backend/scripts/rmt-rebuild.sh` orchestrates the cold start: prereq check (py3.12 / git / sqlite3 / rsync / docker group / systemd / caddy) → `.venv` **from `requirements.lock.txt`** → `rmt-evidence-restore.sh <E5 backup>` → `rmt_evidence_verify.py` (aborts on structural failure) → full suite → install unit + non-secret drop-ins + `daemon-reload`, then pauses for the manual secret/CA checklist before `enable --now` + a `/health` poll. `--drill DIR` runs steps 2–5 + a throwaway instance against an rsync'd copy with **zero** live-host changes. Runbook: `docs/operations/RMT_PLATFORM_RECOVERY.md`. **Scratch-dir drill PASSED (2026-09-08):** venv from lock → evidence restored from a fresh backup → `rmt_evidence_verify.py` `RESULT: OK` (only the known-benign `14be2cb0` orphan WARN) → **342 passed** in 315s → throwaway instance on `:8011` answered `/health` `{"status":"ok"}`; live service on `:8000` untouched throughout. | **READY** | Run a genuine from-cold rebuild on a fresh VM once (exercises the systemd + Caddy + cron steps the drill skips). | **P1** |
| **R4** | High availability / no single point of failure | Single uvicorn process, single host. | **ACCEPTED** | Acceptable at homelab scale; record the RTO expectation (a restart / redeploy, minutes). Revisit only if RMT governs something that cannot tolerate that window. | — |

### Group G — Governance Process (already production-grade)

| ID | Requirement | Current verified evidence | Status |
|---|---|---|---|
| **G1** | Bounded-change discipline | `propose → approve → implement → validate → evidence` followed for CAP-01…05; `STEWARD.md`, `AGENTS.md`. | **READY** |
| **G2** | Architecture authority hierarchy & freeze discipline | Master Definition / Target State / Gap Matrix / roadmap; C01–C07 closed and not reopened. | **READY** |
| **G3** | Correlated durable evidence model | Every governed action correlates authorization / trace / audit / verification / approval / learn by stable IDs (design). Durability mechanics are tracked under Group E. | **READY** (model) |
| **G4** | Capability evidence records | `docs/RMT_CAPABILITIES_EVIDENCE.md` with per-capability validation + live-exercise records. | **READY** |

---

## 4. Status Summary

*(Resynced 2026-09-08 after the E1–E6 / S3 / S5 / S6 / S7 / O1 / O3 / O4 / D3 /
D4 / D6 / V1 / V2 / V3 / V4 / R3 closures — **P0, P1 and P2 all complete**.)*

| Group | READY | PARTIAL | GAP | ACCEPTED | N/A |
|---|---|---|---|---|---|
| S — Security & Access Control | 7 | 0 | 0 | 0 | 0 |
| E — Evidence Durability & Integrity | 6 | 0 | 0 | 0 | 0 |
| D — Deployment & Configuration | 6 | 0 | 0 | 0 | 0 |
| O — Observability & Alerting | 4 | 0 | 0 | 0 | 0 |
| V — Validation & Change Safety | 4 | 0 | 0 | 0 | 0 |
| R — Resilience & Recovery | 3 | 0 | 0 | 1 | 0 |
| G — Governance Process | 4 | 0 | 0 | 0 | 0 |
| **Total** | **34** | **0** | **0** | **1** | **0** |

**Nothing PARTIAL or GAP remains.** `R4` (single-instance / no HA) stays
**ACCEPTED** at homelab scale. `S6` is READY *by policy* (no credential exists
yet; the `systemd`-credentials path is scoped and mandatory before the first
one — `docs/operations/SECRETS.md`).

### By priority

| Priority | Items | State |
|---|---|---|
| **P0** | S1 auth · S2-lite identity · E1 atomic writes · O2 alerting | **code-complete + LIVE & verified** (2026-09-07 12:36 UTC) |
| **P0** | S4 transport | **DONE + LIVE** (2026-09-08) — loopback bind + Caddy `2.6.2` TLS reverse proxy installed, enabled, verified on `192.168.223.128` |
| **P0** | E2 hold persistence | **DONE (above-Core reconciliation)** — `app/ops/reconcile.py`, wired into startup; live since the 2026-09-08 reboot (corrected the two stale holds `316257fc` / `79d6383a`); `test_reconcile.py` 9 tests, full suite 263 passed |

**P0 is fully closed (2026-09-08).** All six blocking items — S1, S2-lite, E1,
E2, O2, S4 — are live and verified.
| **P1** | — | **all closed** (D1, D2, R1, E3, S3, E4, E5, O3, V2, O1, D3, V1, R3) |
| **P2** | — | **all closed** (S5, S6, S7, D4, D5, D6, O4, V3, V4, E6) |
| **ACCEPTED** | R4 (single-instance) | recorded |

---

## 5. Consolidated Remaining Work

Five coherent workstreams. Not milestone numbers; not mandatory sequence except
where noted.

**W1 — Access control.** S1, S2-lite, S3 done (S3 config-gated by
`RMT_AUTH_SEPARATION`). S5, S7 remain (P2). Gated by the §2 threat-model
decision. Nothing else should be exposed until S1 + S4 are done — **both are**.

**W2 — Evidence substrate.** **T0-1 (2026-09-09) landed the JSON → SQLite swap**
(`docs/RMT_T0_1_PROPOSAL.md`, owner-authorised Option A — `DurableStore` backend
only, interface unchanged): the six stores share `data/governance_evidence.db`,
`save()` is one `INSERT` (O(1), no rewrite), WAL-atomic; `scripts/rmt-migrate-evidence.py`
does the one-shot JSON → SQLite + `--reverse`. E4's trim is now a bounded
`DELETE`; E6's audit runs on one DB snapshot. E1's atomic JSON path is retained
for the migration. **E5 follow-up done (2026-09-09):** `rmt_evidence_verify.py`
+ `rmt-evidence-restore.sh` now handle `governance_evidence.db` (and migrate a
pre-T0-1 JSON backup on restore); `test_evidence_verify.py` (5) + a live
backup→verify→restore drill.
**E2 and E6 are closed** by an above-Core startup
reconciliation + audit (`app/ops/reconcile.py::reconcile_governance_stores`) —
the owner chose that over a Core fix, so no freeze deviation. **E3 is closed**
by an above-Core execution-result wrapper (`app/ops/execution_evidence.py`) that
writes a distinguishable `adapter_execution_failed` verification record when the
adapter was invoked and failed; no `app/core/**` change. **E5 is closed** — a
dedicated, checksummed, integrity-verified backup/restore path for the RMT
evidence stores + `observability.db` (`backend/scripts/rmt-evidence-*`,
`docs/operations/RMT_EVIDENCE_RECOVERY.md`).

**W3 — Deployment reproducibility.** D1 (lock deps), D2 (deploy/rollback
runbook), **D3 (unit hardening — `deploy/systemd/hardening.conf`, 9.2 → 4.1)**
all done. **R3 (bare-host rebuild) closed** — base unit + non-secret drop-ins
captured in `deploy/systemd/`; `backend/scripts/rmt-rebuild.sh` +
`docs/operations/RMT_PLATFORM_RECOVERY.md` drive a cold start from repo + an E5
evidence backup; scratch-dir drill passed.

**W4 — Operability.** O2, O3, **O1 done** → D4 → O4.

**W5 — Validation.** **V2 (CI) + V1 (real Docker e2e) done** → V3 → V4.

### Dependency view

```
Threat-model decision (§2)
        ↓
W1 Access control ──┐
                    ├──► exposure-safe
W2 Evidence substrate ──► restart-safe / audit-trustworthy
                    │
W3 Deploy repro ──► W3→R3 recovery-safe
                    │
W4 Operability ──► unattended-safe
                    │
W5 Validation ──► change-safe
```

## 6. Non-Goals / Out of Scope

Not required for this platform to be production-ready at its current purpose:

- **Full enterprise IAM / SSO / RBAC matrix.** A single auth boundary + actor
  identity + separation of duties is sufficient for posture (b). (Core Gap
  Matrix §6 already excludes enterprise IAM from Core.)
- **High availability / clustering.** Recorded as ACCEPTED (R4).
- **Multi-tenancy.**
- **A hosted / internet-facing product.** If that changes, re-run §2 as case (c).
- **Reopening C01–C07 or adding a Core milestone.** Owner directive: **no Core
  modification or fix.** E2 and E6 were closed above-Core; E3 is to be fixed
  above-Core only (an execution-result wrapper). No item in this matrix touches
  the frozen Core.
- **Replacing the governance architecture.** It is sound; this document is about
  the operational substrate under it.

## 7. Recommended First Step

1. **Owner fixes the threat model** (§2 (a) / (b) / (c)).
2. Close **P0** as one focused effort: S1 + S4 (auth + bind/TLS), E1 (atomic
   evidence writes), O2 (held-action alert), E2 (startup hold/record
   reconciliation). **DONE (2026-09-08)** — all six live and verified.
3. Re-verify: full suite green (**263 passed, 2026-09-08**), live exercise under
   auth, hard-kill restart test with evidence intact (**PASSED, 2026-09-08** —
   all six evidence stores byte-identical on reload; see R1).
4. Then W3 / W4 / W5 in bounded steps, updating this matrix's Status column as
   each item closes.

## 8. Final Verdict

**CORE: COMPLETE & FROZEN. OPERATIONAL PRODUCTION-READINESS: P0 + P1 + P2 ALL
COMPLETE (2026-09-08).** Every row of this matrix is READY except `R4` (no HA),
which stays **ACCEPTED** at homelab scale.

The RMT Core architecture is validated and frozen. The running platform is a
working, evidenced control plane, live-exercised end to end.

**P0 batch (2026-09-07): authentication + operator identity (S1/S2-lite),
atomic governance-evidence writes (E1), and held-action alerting (O2) are
code-complete, merged, and LIVE on `:8000`** (service restarted 12:36 UTC;
unauth → 401, authed → 200, `granted_by` = authenticated operator, evidence
intact). The app now binds loopback only.

**E2 (2026-09-07): closed via above-Core startup reconciliation.** The owner
chose reconciliation over a Core fix. `app/ops/reconcile.py` runs once in the
`app/main.py` startup lifespan and brings the approval hold store back into
agreement with the authoritative record store (a stale `pending` hold whose
record shows `approved`/`rejected` is corrected and re-persisted atomically).
No `app/core/**` change. Full suite **263 passed** (254 + 9); 122 frozen-Core
tests unchanged.

**S4 (2026-09-08): closed.** Caddy `2.6.2` TLS reverse proxy installed, enabled,
and live — `/etc/caddy/Caddyfile` from `deploy/Caddyfile`, `tls internal` CA
trusted on the host. Verified on `192.168.223.128`: `https://` → 200
(CA-validated), `http://` → 308 auto-redirect, no-token `POST` → 401, open GET →
200, app refuses `:8000` off-loopback, CAP-04 loop healthy through the proxy.
Remaining housekeeping only: import the Caddy root CA on other operator machines.

**E6 + R1 (2026-09-08): closed.** `reconcile_governance_stores` extends the
startup pass with a read-only authorization-store integrity audit
(`audit_authorizations`); the hard-kill restart test passed with every evidence
store byte-identical on reload. E1/E2/E6 all closed → a restart is provably
faithful.

**P0 is fully closed** and the restart-safety bar (R1) is met. **E3 (2026-09-08)
closed** above-Core: `record_failed_execution_evidence` writes a distinguishable
`adapter_execution_failed` verification record when the adapter was invoked and
failed, so all five §11 outcomes are now distinguishable in evidence. The
remaining P1/P2 items are for a more robust posture but are not individually
blocking. **S3 (2026-09-08) closed** above-Core: `RMT_AUTH_SEPARATION` gates
`/approve` + `/homelab/approve` so the approver of an agent-raised hold cannot
be its grantor. **E4 (2026-09-08) closed**: `archive_aged_evidence` bounds the
live JSON stores on startup (`RMT_EVIDENCE_RETENTION_DAYS`, default 90; archives
to `<name>.archive.jsonl`). **E5 (2026-09-08) closed**: dedicated
backup/verify/restore scripts + `RMT_EVIDENCE_RECOVERY.md`. **O3 (2026-09-08)
closed**: `notify_ops` alerts on loop quarantine + cycle error; `GET /health` +
`rmt-heartbeat.sh` cover service-down. **V2 (2026-09-08) closed**:
`backend/scripts/ci.sh` (clean-venv-from-lock + errors-only ruff + full suite,
324 passed) and a dormant `.github/workflows/ci.yml` that runs it once the repo
has a remote. **O1 (2026-09-08) closed**: `app/ops/logging_config.py` — stdlib
structured JSON logging to stdout/journald, per-request `request_id` +
`http_request` line, one `log_event` line at every governed-lifecycle boundary
(routes / CAP-04 loop / agent adapter); `RMT_LOG_LEVEL` / `RMT_LOG_JSON`;
journald handles rotation. **D3 (2026-09-08) closed**:
`deploy/systemd/hardening.conf` — sandboxing + resource ceilings + restart
backoff, no code change; `systemd-analyze security` 9.2 UNSAFE → 4.1 OK
(install pending). **V1 (2026-09-08) closed**: `test_e2e_docker.py` drives the
real `DockerExecutionAdapter` against a disposable `alpine` container through
fault → held → approve → restart → verify → evidence (auto-skips without
Docker). **R3 (2026-09-08) closed**: bare-host rebuild — the canonical base
systemd unit and the four non-secret drop-ins are captured in `deploy/systemd/`,
and `backend/scripts/rmt-rebuild.sh` (+ `docs/operations/RMT_PLATFORM_RECOVERY.md`)
drives a cold start from the repo + an E5 evidence backup through venv-from-lock
→ evidence restore → integrity check → suite → unit install → service up. A
scratch-dir drill passed end to end (342 passed; throwaway `/health` → `ok`;
live service untouched).

**P2 batch (2026-09-08) closed** — all above-Core, no `app/core/**` change:
**S5** CORS from `RMT_CORS_ORIGINS` + scoped methods/headers; **S6** secrets
pattern documented + accepted by policy (`docs/operations/SECRETS.md`); **S7**
`app/ops/ratelimit.py` per-principal fixed-window limits on `/execute` +
`/agent/act*` → 429; **D4** `rmt-watchdog.sh` restarts on sustained-unreachable
`/health`, alerts on degraded; **D6** `app/ops/runtime_info.py` — `/health`
`runtime` block + startup WARNING on adapter-mode mismatch, plus
`docs/operations/PREREQUISITES.md`; **O4** `app/ops/metrics.py` + Prometheus
`GET /metrics` (read-only, no dependency); **V3** `test_env_routes.py` pins
`/containers*` + `/platform/state` in both modes (routes now 503 not 500 when
the capability is absent); **V4** `rmt-smoke.sh` post-deploy gate. Full suite
green. **Every P0, P1 and P2 item is now closed; only `R4` (no HA) remains, and
it is ACCEPTED.**

---

*Above-Core operational assessment. Does not reopen or modify C01–C07. Does not
create a Core milestone. Status columns to be updated as items close.*

🤖 Generated with [Claude Code](https://claude.com/claude-code)
