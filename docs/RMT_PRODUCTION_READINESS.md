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
- Governance evidence: six JSON files via `DurableStore`; intelligence memory in
  SQLite (`data/observability.db`).
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
| **S3** | Separation of duties | The same caller can `POST /agent/authority/grant` and then `POST /homelab/approve` the resulting hold. Identity is now *recorded* (S2); the rule is not yet *enforced*. | **GAP** | Enforce approver ≠ grantor / proposer for agent-originated holds (config-gated). Fast-follow behind an `RMT_AUTH_SEPARATION` toggle. | **P1** |
| **S4** | Transport security & network exposure | **DONE + LIVE (2026-09-08)** — `bind-loopback.conf` deployed (app listens `127.0.0.1:8000` only, verified unreachable off-loopback) **and** Caddy `2.6.2` TLS reverse proxy installed + enabled, `/etc/caddy/Caddyfile` from `deploy/Caddyfile`, `tls internal` CA trusted on the host. Verified on `192.168.223.128`: `https://` → 200 CA-validated, `http://` → 308 redirect, no-token `POST` → 401, open GET → 200, CAP-04 loop healthy through the proxy. | **READY** | Import the Caddy root CA on other operator machines (`/var/lib/caddy/.local/share/caddy/pki/authorities/local/root.crt`). | **P0** |
| **S5** | CORS configuration | `allow_origins` hardcoded to `http://192.168.235.128:5173` + `localhost:5173`, `allow_credentials=True`, `allow_methods/headers=["*"]`. | **PARTIAL** | Move origins to config; scope methods/headers to what the frontend needs. | **P2** |
| **S6** | Secrets management | Only a local Ollama endpoint today (no key). No secret store exists if a credentialed model / notifier / IdP is added. | **PARTIAL** | Adopt a secrets mechanism (env-file with restricted mode, or a vault) before introducing any credential. | **P2** |
| **S7** | Abuse / rate protection on expensive routes | `/agent/act/llm` (model call) and `/execute` (real mutation) have no throttle or concurrency cap beyond the agent single-use grant. | **GAP** | Add a simple per-principal rate limit / concurrency guard on `/agent/act*` and `/execute`. | **P2** |

### Group E — Evidence Durability & Integrity

The platform's core value is trustworthy governance evidence. The evidence
substrate is currently weaker than the governance logic on top of it.

| ID | Requirement | Current verified evidence | Status | Required action | Priority |
|---|---|---|---|---|---|
| **E1** | Atomic, concurrency-safe evidence writes | **DONE** — `DurableStore._persist` writes a sibling `.tmp`, `flush` + `os.fsync`, then `os.replace` (atomic on POSIX); `_load` discards stale `.tmp`. Byte-identical committed output; owner-authorized frozen-Core hardening deviation. `test_durable_store_atomic.py` (interrupted-write leaves prior file intact). | **READY** | — | **P0** |
| **E2** | Hold state persisted on resolution | **DONE (above-Core)** — owner chose reconciliation over a Core fix. `app/ops/reconcile.py::reconcile_holds_against_records`, run once in the `app/main.py` startup lifespan, brings the hold store back into agreement with the authoritative approval **record** store: a `pending` hold whose record shows a terminal decision (`approved`/`rejected`) is corrected in place and re-persisted via the store's atomic (E1) write path. Read-only where nothing diverges; fail-open (never blocks startup). Never invents a resolution. No `app/core/**` change. `app/ops/testing/test_reconcile.py` — 9 tests; full suite 263 passed. | **READY** | — | **P0** |
| **E3** | Failed-execution verification evidence | A failed adapter execution produces **no** verification record — not even `verification_failure` / `state_mismatch`. `AGENTS.md` §11 lists "adapter invoked and failed" as an outcome that should be distinguishable. (Recorded frozen-Core note.) | **GAP** | Emit a distinguishable verification/evidence record on adapter failure (Core fix on the freeze, or an above-Core wrapper on the execution result). | **P1** |
| **E4** | Retention / rotation / size management | The six JSON stores grow unbounded and are fully rewritten each save (O(n) per write). | **GAP** | Define a retention window + archival/rotation; this is also resolved by an E1 migration to SQLite. | **P1** |
| **E5** | Evidence backup & restore (RMT stores) | `docs/recovery/RECOVERY_RUNBOOK.md` + the `scripts/` backup engine cover the **Docker stack** (volumes, stack config). The RMT governance stores and `data/observability.db` are not in a documented backup/restore path. | **GAP** | Add the RMT evidence stores + SQLite DB to the backup engine and the recovery runbook, with a restore-integrity check. | **P1** |
| **E6** | Startup integrity / reconciliation | The hold ↔ record half is now reconciled on load (E2 fix, `app/ops/reconcile.py`): a divergence is corrected against the authoritative record store and logged (`WARNING`). The authorization store is not yet cross-checked. | **PARTIAL** | Extend the startup reconciliation to the authorization store. | **P2** |

### Group D — Deployment & Configuration

| ID | Requirement | Current verified evidence | Status | Required action | Priority |
|---|---|---|---|---|---|
| **D1** | Pinned, reproducible dependency set | **DONE** — `backend/requirements.txt` now pins every direct dep (+ `pytest`, `httpx2` as test-only); `backend/requirements.lock.txt` is the full 33-package transitive lock (`pip freeze`). | **READY** | Verify a clean venv builds from the lock in CI (V2). | **P1** |
| **D2** | Deploy + rollback runbook for the RMT service | **DONE** — `docs/operations/DEPLOY.md` (first-time P0 cutover, routine redeploy, rollback, token rotation, restart-safety check) + `docs/operations/CONFIG.md` (every `RMT_*` var — also closes **D5**). | **READY** | Exercise it on the next redeploy. | **P1** |
| **D3** | Service hardening | The unit has only `Restart=always` / `RestartSec=5`. No `MemoryMax`, `CPUQuota`, `NoNewPrivileges`, `ProtectSystem`, `ProtectHome`, `PrivateTmp`, restart backoff. | **GAP** | Add systemd sandboxing + resource limits; `StartLimitIntervalSec` / burst; run as the least-privileged user with only the Docker socket it needs. | **P1** |
| **D4** | Health/readiness probe acted upon | `/intelligence/health` returns 200 (D1 correction, C07). Nothing external watches it; `Restart=always` only restarts on process exit, not on unhealthy. | **PARTIAL** | Wire a watchdog (systemd `WatchdogSec` + `sd_notify`, or an external check) that restarts on sustained unhealthy. | **P2** |
| **D5** | Consolidated configuration reference | **DONE** — `docs/operations/CONFIG.md` lists every `RMT_*` var (auth, notify, CAP-04 loop, agent 5A/5B), default, effect, and which drop-in sets it, plus the expected live drop-in inventory. | **READY** | Keep in sync with `loop_config.py` changes. | **P2** |
| **D6** | Documented runtime prerequisites & environment parity | Behaviour depends on git presence and Docker-socket reachability (adapter resolves to `simulation` vs `docker`); this has bitten test runs before. | **PARTIAL** | Document required host capabilities; make adapter-mode explicit in `/agent/status` / a health field; fail loudly if a required capability is missing in production mode. | **P2** |

### Group O — Observability & Alerting

An unattended control plane that can hold actions for human approval must be
able to *tell a human*.

| ID | Requirement | Current verified evidence | Status | Required action | Priority |
|---|---|---|---|---|---|
| **O1** | Structured application logging + rotation | No logging framework in `app/main.py` or `app/core/**` (no `logging.getLogger`, loguru, structlog). Output is uvicorn's default to the journal. | **GAP** | Introduce structured logging (request id, action id, decision, principal) at the governed-lifecycle boundaries; ensure journald retention / rotation is set. | **P1** |
| **O2** | Alert on held remediation / agent proposal | **DONE + LIVE (log sink)** — `app/ops/notifications.py` `notify_held` (webhook via stdlib `urllib`, fail-open, per-key de-dupe) hooked at `/execute`, `/homelab/remediate`, the CAP-04 loop, and the agent adapter. Deployed with `RMT_NOTIFY_WEBHOOK_URL` **unset** → held actions log to the journal only. `test_notifications.py`. | **READY** *(routing to a real sink pending)* | Set `RMT_NOTIFY_WEBHOOK_URL` in `auth.conf` when a chat/email sink exists. | **P0** |
| **O3** | Alert on loop quarantine / cycle error / service down | `homelab_loop_quarantine` etc. are recorded to memory only; no outbound signal. | **GAP** | Notify on quarantine, `last_cycle_error`, and service-down (external heartbeat). | **P1** |
| **O4** | Platform self-metrics | No request-rate / error-rate / hold-queue-depth metrics for the RMT process. | **GAP** | Expose a metrics endpoint or periodic self-report (holds outstanding, cycles, error counts). | **P2** |

### Group V — Validation & Change Safety

| ID | Requirement | Current verified evidence | Status | Required action | Priority |
|---|---|---|---|---|---|
| **V1** | Automated end-to-end test on a realistic adapter | The 214-test suite mocks the execution adapter. The only true end-to-end proof (LLM → propose → approve → docker → verify) is the **manual** live exercises recorded in `HANDOFF.md`. | **PARTIAL** | Add an automated end-to-end test against a disposable real container (or a high-fidelity fake) covering fault → held → approve → execute → verify. | **P1** |
| **V2** | CI on every change | No `.github/workflows` (or other CI config) in the repo. | **GAP** | CI that runs the full suite (Core 122 + app 214) + a lint on every push; block merge on red. | **P1** |
| **V3** | Coverage of environment-dependent routes | `/platform/state` (git) and `/containers*` (docker socket) were validated only opportunistically; `test_http_entrypoints.py` had to be corrected once for adapter-mode drift. | **PARTIAL** | Add explicit tests for both adapter modes (git/docker present and absent). | **P2** |
| **V4** | Regression guard on live-config changes | Enabling a capability on live is a manual drop-in + restart + manual exercise. | **PARTIAL** | A post-deploy smoke script (assert route presence, flags, loop idle, suite green) run automatically after each restart. | **P2** |

### Group R — Resilience & Recovery

| ID | Requirement | Current verified evidence | Status | Required action | Priority |
|---|---|---|---|---|---|
| **R1** | Restart safety — state rebuilt correctly from disk | **Hard-kill restart test PASSED (2026-09-08).** `systemctl kill -s KILL` on the whole cgroup, then restart: all six durable evidence stores reloaded **byte-for-byte identical** (sha256 + record counts unchanged), no `.tmp` residue (E1), hold ↔ record stores in agreement / reconcile a clean no-op (E2), CAP-04 loop + auth + Caddy proxy all healthy on the new PID. Only the E6 authorization-store cross-check now remains. | **PARTIAL** | Close the E6 remainder (extend startup reconciliation to the authorization store). | **P1** |
| **R2** | Homelab stack disaster recovery | `docs/recovery/RECOVERY_RUNBOOK.md` + backup engine + `verify-recovery.sh` — a tested procedure with checksums and manifests. | **READY** | Keep exercised. | — |
| **R3** | RMT platform recovery procedure | No procedure to rebuild the RMT service itself (venv, unit, drop-ins, evidence stores, SQLite DB) on a fresh host. | **GAP** | A runbook + script to stand up the service from the repo + a restored evidence set. | **P1** |
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

*(Updated after the P0 batch, 2026-09-07.)*

| Group | READY | PARTIAL | GAP | ACCEPTED | N/A |
|---|---|---|---|---|---|
| S — Security & Access Control | 2 | 1 | 4 | 0 | 0 |
| E — Evidence Durability & Integrity | 1 | 0 | 5 | 0 | 0 |
| D — Deployment & Configuration | 3 | 1 | 2 | 0 | 0 |
| O — Observability & Alerting | 1 | 0 | 3 | 0 | 0 |
| V — Validation & Change Safety | 0 | 3 | 1 | 0 | 0 |
| R — Resilience & Recovery | 1 | 1 | 1 | 1 | 0 |
| G — Governance Process | 4 | 0 | 0 | 0 | 0 |
| **Total** | **12** | **6** | **16** | **1** | **0** |

### By priority

| Priority | Items | State |
|---|---|---|
| **P0** | S1 auth · S2-lite identity · E1 atomic writes · O2 alerting | **code-complete + LIVE & verified** (2026-09-07 12:36 UTC) |
| **P0** | S4 transport | **DONE + LIVE** (2026-09-08) — loopback bind + Caddy `2.6.2` TLS reverse proxy installed, enabled, verified on `192.168.223.128` |
| **P0** | E2 hold persistence | **DONE (above-Core reconciliation)** — `app/ops/reconcile.py`, wired into startup; live since the 2026-09-08 reboot (corrected the two stale holds `316257fc` / `79d6383a`); `test_reconcile.py` 9 tests, full suite 263 passed |

**P0 is fully closed (2026-09-08).** All six blocking items — S1, S2-lite, E1,
E2, O2, S4 — are live and verified. Next work is P1.
| **P1** | S3, E3, E4, E5, D3, O1, O3, V1, V2, R1, R3 | pending (D1, D2 done) |
| **P2** | S5, S6, S7, D4, D6, O4, V3, V4 | pending (D5 done; E6 now PARTIAL) |
| **ACCEPTED** | R4 (single-instance) | recorded |

---

## 5. Consolidated Remaining Work

Five coherent workstreams. Not milestone numbers; not mandatory sequence except
where noted.

**W1 — Access control.** S1 → S2 → S3 (+ S5, S7). Gated by the §2 threat-model
decision. Nothing else should be exposed until S1 + S4 are done.

**W2 — Evidence substrate.** E1 (atomic writes / SQLite migration) is the
keystone; it also resolves E4 and de-risks E6. **E2 is closed** by an above-Core
startup reconciliation (`app/ops/reconcile.py`) — the owner chose that over a
Core fix, so no freeze deviation; it also covers the hold↔record half of E6.
**E3** still touches the frozen Core (a failed adapter execution produces no
verification record) — a separate owner decision (Core fix vs above-Core
wrapper). E5 folds the RMT stores into the existing backup engine.

**W3 — Deployment reproducibility.** D1 (lock deps) → D2 (deploy/rollback
runbook) → D3 (unit hardening). Enables R3 (platform recovery).

**W4 — Operability.** O2 (P0, because the loop runs unattended) → O1 → O3 →
D4 → O4.

**W5 — Validation.** V2 (CI) → V1 (real e2e) → V3 → V4.

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
- **Reopening C01–C07 or adding a Core milestone.** E2 was closed above-Core
  (no Core touch). **E3** is now the only remaining item that would touch frozen
  Core, and only as an explicit, separately-authorized owner decision.
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

**CORE: COMPLETE & FROZEN. OPERATIONAL PRODUCTION-READINESS: P0 COMPLETE
(2026-09-08); P1 NEXT.**

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

**P0 is fully closed.** The P1/P2 items remain for a more robust posture but are
not individually blocking. Next: P1 — S3 enforcement, E3 (failed-execution
verification evidence — the lone remaining frozen-Core item), E4/E5, D3, O1/O3,
V1/V2, R1/R3.

---

*Above-Core operational assessment. Does not reopen or modify C01–C07. Does not
create a Core milestone. Status columns to be updated as items close.*

🤖 Generated with [Claude Code](https://claude.com/claude-code)
