# RMT — Project Context (Stable Project Brain)

> **Purpose:** This is the stable bootstrap/context document for the RMT project.
> A new technical session reads this FIRST, then `HANDOFF.md` (fine-grained
> session history), then the governing documents, and verifies consequential
> claims against the repository.
>
> `RMT_CONTEXT.md` = stable project brain / bootstrap context.
> `HANDOFF.md` = fine-grained session history / continuation context.

---

## 1. RMT identity and purpose

RMT is a general-purpose intelligent control, execution, and governance
platform. The Core is domain-agnostic: it governs services, applications,
systems, and AI agents without embedding the rules of any particular domain.

The Core is a **finite** capability set. It is not an indefinitely expanding
architecture.

## 2. Core lifecycle

**Understand → Decide → Govern → Authorize → Execute → Verify → Learn**

The single authoritative governed mutation path is:

`execute_governed_action` → `execution_engine.execute` → adapter

## 3. Core/domain boundary

- **Core:** generic platform capability (observation, intelligence, decision,
  governance, risk, approval, authorization, controlled execution, adapter
  boundary, verification, audit/trace, learning/history, self-management,
  controlled evolution, platform validation).
- **Above-Core / domain:** Banking Risk Management, Budget Control, AI Agent
  Governance, IT/Cloud Operations, concrete Docker/provider adapters, products,
  integrations, applications, UI.
- A useful capability is **not** automatically a Core requirement.

## 4. Finite Core Target-State principle

The Target State is a **completion boundary**, not an implementation plan.
The Core is complete when one governed lifecycle is real, connected, enforced,
observable, verifiable, and evidenced. A class/module/isolated test is not
completion evidence by itself.

## 5. Governing documents and their authority

| Document | Role |
|---|---|
| `docs/RMT_MASTER_DEFINITION.md` | Top authority — defines RMT and Core/domain boundary |
| `docs/RMT_CORE_TARGET_STATE.md` | Top authority — finite Core Target State and completion criteria |
| `docs/RMT_CORE_GAP_MATRIX.md` | Verified gaps vs Target State (status record) |
| `docs/RMT_CORE_REMAINING_ROADMAP.md` | Finite implementation roadmap and milestone status |
| `AGENTS.md` | Agent operating contract (authority hierarchy, rules) |
| `RMT_CONTEXT.md` / `HANDOFF.md` | Coordination/continuation (not architecture authority) |

Governing documents take precedence over assumptions. Repository evidence takes
precedence over conversation memory.

## 6. Major established architectural decisions

- **Single governed mutation boundary:** `execute_governed_action` is the only
  Core-scope production mutation path; no equivalent unmanaged path remains.
- **Policy relationship:** action policy is the authoritative governance gate;
  execution policy is a deny-only final safety check.
- **Risk relationship:** governance risk is authoritative for approval;
  execution risk is a final independent assessment, consistent and traceable.
- **Durable evidence:** authorization, approval/hold, approval-record, audit,
  trace, and verification are durable via JSON `DurableStore`, correlated by
  stable identifiers.
- **Verification authority:** post-execution verification uses a trusted
  internal observer resolved from the execution request; it is never
  caller-controlled (B3/B4). Adapter success alone cannot manufacture
  `verified_success`.
- **Evolution & self-management:** validated through the governed service
  boundary (`execute_governed_change`, `execute_self_management_decision`).
  No HTTP evolution route is required.
- **Adapters are executors only:** they do not authorize, approve, override
  policy, redefine risk, or manufacture governance evidence.

## 7. Architectural boundaries and anti-bypass principles

- No second mutation boundary.
- No direct execution without a valid, bound authorization.
- Authorization is created at a single site inside the governed chain.
- Approval continuation stays within the governed path.
- Adapter selection/redirection is constrained (e.g., evolution is bound to the
  `module_change` adapter).
- Learning/history is read-only and cannot invoke execution, mint
  authorization, or mutate governance state.
- Blocked/denied/unknown paths never reach an adapter.

## 8. Completed milestones and status

| Milestone | Capability | Status |
|---|---|---|
| RMT-C01 | Governed Execution Boundary | CLOSED |
| RMT-C02 | Durable Governance Evidence | CLOSED |
| RMT-C03 | Post-Execution Verification | CLOSED |
| RMT-C04 | Generalized Understand → Decide Completion | CLOSED |
| RMT-C05 | Controlled Platform Self-Management | CLOSED |
| RMT-C06 | Controlled Platform Evolution | CLOSED |
| RMT-C07 | Platform Validation and Freeze | CLOSED — Platform Freeze |

Closed milestones must not be reopened without evidence.

## 9. Current milestone / status

**C01–C07: CLOSED.** **RMT Core Target State: ACHIEVED.** **RMT Core Platform
Freeze: REACHED** (freeze commit `46a4441` — "RMT Core Platform Freeze"). Core
validation: **122 tests passed**; no reachable production-equivalent governance
bypass; no remaining required Core capability. There is intentionally **no C08**.
The RMT Core is now considered frozen.

## 10. Current verified implementation state

- Full intelligence testing suite: **122 passed** (verified).
- C07 HTTP validation artifact exists:
  `app/core/intelligence/testing/test_http_entrypoints.py` (7 tests).
- D1 production correction applied (`app/core/intelligence/service.py`:
  `calculate_platform_health` reads `observation.signals.get("cpu_usage", 0)` /
  `.get("memory_usage", 0)`), with a focused regression test
  (`test_deviation_branch_uses_signals_contract`).
- `GET /intelligence/health` returns HTTP 200.
- G2 Core-boundary review: **PASS** (no genuine Core implementation gap after D1).
- Durable evidence stores are clean under the committed HTTP artifact.

## 11. Current remaining work

- No remaining Core work. The finite Core Target State is validated and the RMT
  Core is frozen.
- The next phase is **not Core development** and must not reopen C01–C07.
- Any Core change requires evidence that the finite Target State or an existing
  Core contract is insufficient.

## 12. Current immediate next action

**Above-Core capabilities (completed):**
- **RMT-CAP-01 — Homelab Operations (Learn closure):** COMPLETED & VERIFIED.
  Closed the missing Learn stage in the Homelab operational loop; full lifecycle
  `Understand → Decide → Govern → Authorize → Execute → Verify → Learn`.
- **RMT-CAP-02 — Engineering Change-Impact & Risk Analysis:** COMPLETED &
  VERIFIED. Read-only, deterministic, evidence-backed engineering analysis
  (component resolution, impact, engineering-change risk, recommendation).
  See `docs/RMT_CAPABILITIES_EVIDENCE.md`.
- **RMT-CAP-03 — Homelab Remediation Approval-Continuation Learn Closure:**
  COMPLETED & VERIFIED. The executed outcome of an approval-continuation
  remediation is now recorded as a learning record with above-Core Docker
  verification (`app/homelab/continuation.py`, `POST /homelab/approve`).
- **RMT-CAP-04 — Continuous Homelab Operational Loop:** COMPLETED & VERIFIED
  (2026-09-07). Runs the existing single-shot Homelab governed lifecycle on a
  cadence under supervision — cadence + guardrails only, no new mutation path.
  `app/homelab/operational_loop.py` + `loop_config.py`; routes
  `GET/POST /homelab/loop/{status,start,stop,clear}`. Ships disabled;
  **ENABLED on the live server 2026-09-07** via systemd drop-in
  `rmt-control-center.service.d/cap04-loop.conf`
  (`RMT_HOMELAB_LOOP_ENABLED=true`). Guardrails: approval retained (holds never
  auto-continued), flap-guard/quarantine, cooldown, duplicate-hold guard
  (read-only hold + record store query → `awaiting_approval`; a hold blocks only
  while still-actionable — not terminally recorded, not past its TTL),
  single-flight, fail-safe. Diff confined to `app/homelab/**` + `app/main.py`;
  no `app/core/**` change. Validation: 17 focused + 38 Homelab + 122 Core + 177
  full, all passed. **Live-demonstrated on the real homelab 2026-09-07**
  (owner-authorized; isolated instance; fault-inject → held → approve → governed
  restart → Docker `verified_success` → loop stood down; PASS). See
  `docs/RMT_CAP_04_PROPOSAL.md`, `docs/RMT_CAPABILITIES_EVIDENCE.md`, and the
  `HANDOFF.md` session notes.

**MCR/T13 disposition — RECORDED 2026-09-07** (`docs/RMT_T13_DISPOSITION.md`):
ACCEPT (with constraint) + BOUND + DEFER. T13 is a policy-completeness gap in the
MCR-EXP-3 simulation, not a live defect in RMT Core or CAP-01..04. CAP-04 may be
*enabled* only inside its safe-enablement envelope (every `REMEDIATION_POLICY`
entry independent + `requires_approval=True`; guard test
`test_remediation_policy_within_cap04_safe_envelope`). The full
dependency-cascade escalation fix is delivered by **CAP-05 (5A)** and the
disposition is **CLOSED** (2026-09-07): `app/agent/dependency_guard.py` is live,
wired to the above-Core homelab dependency map `app/homelab/dependencies.py`
(recorded all-independent) unioned with the Core context. No edges today → no
escalation; adding any edge escalates the matching allowed op automatically.

- **RMT-CAP-05 (5A) — Governed Agent Surface:** COMPLETED & VERIFIED
  (2026-09-07). MCR child-contract surface (`app/agent/`): an agent *proposes* a
  consequential homelab op → `AgentProposal` → `execute_governed_action` (same
  single boundary). Single-use, time-limited, scoped authority grants
  (capability ≠ authority); T13 dependency-cascade escalation; deterministic
  reference agent; routes `POST /agent/{authority/grant,act}` + read-only
  `GET /agent/{status,authority}`. Ships disabled (`RMT_AGENT_ENABLED`);
  **ENABLED on the live server 2026-09-07** (see the 5B bullet + §Next action).
  Diff confined to `app/agent/**` + `app/main.py`; no `app/core/**` change; no
  new mutation path; held proposals never auto-continued. 20 focused + 122 Core
  (unchanged) + 197 full, all passed.
- **RMT-CAP-05 (5B) — LLM-Backed Agent Adapter:** COMPLETED & VERIFIED
  (2026-09-07). A local LLM (`deepseek-v4-flash:cloud` via Ollama) turns a
  natural-language goal into a structured `AgentProposal` that runs the
  identical 5A path (authority → T13 → governance → human approval). The LLM
  only proposes — no execution/tools/authority/continuation. Fail-closed parse
  + allow-list validation; `POST /agent/act/llm`; disabled by default
  (`RMT_AGENT_LLM_ENABLED`). Diff confined to `app/agent/**`; no `app/core/**`
  change; no autonomous loop. 17 focused + 37 agent + 122 Core (unchanged) +
  214 full, all passed. See `docs/RMT_CAP_05B_PROPOSAL.md`.
  **5A + 5B ENABLED on the live server 2026-09-07** — systemd drop-in
  `rmt-control-center.service.d/cap05-agent.conf`
  (`RMT_AGENT_ENABLED=true` + `RMT_AGENT_LLM_ENABLED=true`); `GET /agent/status`
  → `enabled: true`, `llm.enabled: true`, `active_grants: 0`. The surface is
  request-driven only (no background task) — inert until an operator both issues
  a grant and approves the resulting hold; every proposal is human-approval
  gated; T13 active but a no-op (no dependency edges). **Controlled LLM exercise
  on live :8000 (target `dozzle`) — PASS**: no-grant → `no_authority`;
  do-nothing goal → `no_proposal`; fault-inject → grant → LLM proposes → held →
  approve → governed `docker` start (exec `37ab18bf…`, authorization
  `decision_id agent-llm-agent-…`); replay → `grant_consumed`; scope mismatch
  held. One **finding** recorded (not a defect): `continue_remediation`
  (`/homelab/approve`) runs the above-Core Docker verify + executed-Learn
  closure only for `REMEDIATION_POLICY` components (`uptime-kuma` only), so the
  `dozzle` run got the held-state Learn record but not `verified_success`. See
  `docs/RMT_CAPABILITIES_EVIDENCE.md` §CAP-05 + the `HANDOFF.md` session note.

**Next action:** the next above-Core capability is to be selected by the owner
from the candidate directions. **Full menu: `docs/RMT_ABOVE_CORE_ROADMAP.md`**
(2026-09-07) — the fit profile (what RMT governs effectively), plus Tier 0
operational-readiness completion, Tier 1 homelab depth, Tier 2 new domains on
the frozen Core (AI Agent Governance Gateway, Cloud/IaC Ops, Kubernetes Ops,
Financial/Approval Control, Data & ML Ops), Tier 3 platform surface, and the
lone Core-change candidate (E3), each scoped Objective/Boundary/DoD. Nothing
there is authorized until the owner selects it and an approved per-capability
proposal exists. A **production-readiness gap matrix** exists
(`docs/RMT_PRODUCTION_READINESS.md`, 2026-09-07): above-Core / operational, does
not reopen C01–C07. Threat model set to **(b) trusted LAN, few operators**.
**P0 batch implemented + DEPLOYED 2026-09-07** (`docs/RMT_PROD_P0_PROPOSAL.md`,
APPROVED; commit `c4f63a3`): **S1** operator auth + **S2-lite** identity (new
`app/ops/`, `require_operator` on all mutating routes + `/agent/*`;
`RMT_OPERATOR_TOKENS`; authenticated name now lands in the evidence), **E1**
atomic evidence writes (owner-authorized frozen-Core hardening of
`durable_store._persist`), **O2** held-action webhook alerting (log sink).
**D1** deps pinned + lock; **D2/D5** `docs/operations/DEPLOY.md` + `CONFIG.md`.
Validation: **254 tests pass** (214 + 40); Core intelligence 126 (122 unchanged
+ 4). **Live on :8000 since 12:36 UTC** — `auth.conf` (tokens `ragb`/`ops2`,
`sudo cat` to read) + `bind-loopback.conf` deployed; verified: unauth → 401,
authed → 200, `granted_by` = operator, app on `127.0.0.1:8000` only, evidence
intact, CAP-04 loop + agent still healthy. **E2 CLOSED 2026-09-07** — owner
chose **above-Core reconciliation** over a Core fix: new `app/ops/reconcile.py`
(`reconcile_holds_against_records`), called in the `app/main.py` startup
lifespan, corrects any `pending` hold whose approval **record** is terminal
against the authoritative record store and re-persists atomically; fail-open,
never invents a resolution, no `app/core/**` change. Full suite **263 passed**
(254 + 9 `test_reconcile.py`). Committed 2026-09-08 (`b485365`). **E2 is live** — the
2026-09-08 host reboot auto-started the service from the working tree; the
startup reconcile ran and corrected the two stale holds (`316257fc` →
`approved`, `79d6383a` → `rejected`), leaving the genuinely-unresolved
`54f685f6` (`manual_required` record) untouched; re-run now is a no-op.
**S4 CLOSED 2026-09-08** — Caddy `2.6.2` TLS reverse proxy installed + enabled;
`/etc/caddy/Caddyfile` from `deploy/Caddyfile`, `tls internal` CA trusted on the
host. Verified on `192.168.223.128`: `https://` → 200 CA-validated, `http://` →
308 redirect, no-token `POST` → 401, open GET → 200, app refuses `:8000`
off-loopback, CAP-04 loop healthy through the proxy. Remaining: import the Caddy
root CA on other operator machines.
**P0 IS FULLY CLOSED (2026-09-08)** — S1, S2-lite, E1, E2, O2, S4 all live and
verified. **E6 + R1 also closed 2026-09-08:** `reconcile.py` extended to
`reconcile_governance_stores` (E2 hold correction **+** `audit_authorizations`,
a read-only startup integrity audit of the execution-authorization store against
holds/records — logs `missing_record` / `contradicts_rejection` /
`record_not_terminal` / `hold_still_pending`, never writes; the authz store is
Core-owned append-only so read-only by design). `test_reconcile.py` now 18 tests
(9 E2 + 9 E6). Hard-kill restart test PASSED — all six evidence stores
byte-identical on reload. E1/E2/E6 all closed → restart provably faithful.
**E3 also closed 2026-09-08** (above-Core, no Core change): new
`app/ops/execution_evidence.py::record_failed_execution_evidence` — when the
adapter was invoked and returned `success=False` (which produced no verification
record — callers gate `verify_*` on `result.success`), writes one
`VerificationResult` to the existing store with a distinct status
`adapter_execution_failed`, correlated by `execution_id`; bounded
(blocked-before-adapter outcomes untouched), idempotent, fail-open. Wired at
`/execute`, `/approve`, `/homelab/remediate`, `/homelab/approve` and the agent
adapter's failure branch. `test_execution_evidence.py` 19 tests + 1 agent
end-to-end. All five `AGENTS.md` §11 outcomes now distinguishable in evidence.
**S3 also closed 2026-09-08** (above-Core, config-gated by `RMT_AUTH_SEPARATION`,
default off): new `app/ops/separation.py` — `propose_and_govern` records
`approval_id → {grant_id, granted_by, agent_id}` on a hold; `/approve` +
`/homelab/approve` call `check_separation()` first and return **403** if the
approver granted the agent's authority (`approver_is_grantor`) or is the
proposing agent (`approver_is_proposer`); non-agent holds pass through; the
check fails **closed**. `GET /agent/status` exposes `separation_of_duties`.
`test_separation.py` 14 tests. Also fixed a pre-existing `test_auth.py`
isolation gap that was polluting the Core evidence stores; 22 stray `target: x`
records cleaned from traces/audit/verifications via
`scripts/clean_test_pollution.py`.
**E4 + E5 also closed 2026-09-08:** E4 = `app/ops/retention.py::archive_aged_evidence`
runs on startup (after the reconcile) — evidence older than
`RMT_EVIDENCE_RETENTION_DAYS` (default 90; `<=0` disables) moves to an
append-only `<name>.archive.jsonl` beside the store; bounded, idempotent,
fail-open; `test_retention.py` 10 tests. E5 = `backend/scripts/rmt-evidence-{backup,restore}.sh`
+ `rmt_evidence_verify.py` (stdlib-only structural + cross-store integrity check)
+ `docs/operations/RMT_EVIDENCE_RECOVERY.md`; backup is `VACUUM INTO` hot-safe +
`sha256`, restore refuses while the service is up. **Full app suite 316 passed**
(306 + 10). D4 proposal revised to rev-2 (`7dab721`) — S3/E3 recorded done,
`ActionType` blocker + dual-approval scoped, sequencing = hold D4 until E4/E5
close (now done). **O3 also closed 2026-09-08:** `notify_ops` (same webhook
sink as O2) alerts on CAP-04 loop quarantine + cycle error; new unauthenticated
`GET /health` (`ok`/`degraded`) + `backend/scripts/rmt-heartbeat.sh` (cron
inverted dead-man's switch) cover service-down. `test_health.py` +
`test_notifications.py`/`test_operational_loop.py` extensions. **V2 also closed
2026-09-08:** `backend/scripts/ci.sh` (throwaway venv from `requirements.lock.txt`
+ errors-only `ruff` [`backend/ruff.toml`, `app/core` excluded] + full suite,
**324 passed**); `.github/workflows/ci.yml` calls it — dormant until the repo
has a remote. 7 above-Core dead imports removed; no `app/core/**` change. Closes
D1's clean-venv-from-lock action. **O1 also closed 2026-09-08:**
`app/ops/logging_config.py` -- stdlib structured JSON logging to stdout/journald
(no dependency), per-request `request_id` + one `http_request` line, and a
`log_event` line at every governed-lifecycle boundary (4 mutating routes, the
CAP-04 loop, the agent adapter), correlated by action/execution/approval id.
`RMT_LOG_LEVEL` / `RMT_LOG_JSON`; rotation is journald's job (`DEPLOY.md` §5).
`test_logging_config.py` 16 tests; no `app/core/**` change. **D3 also closed
2026-09-08:** `projects/homelab-control-center/deploy/systemd/hardening.conf` --
a systemd drop-in (sandboxing + `MemoryMax=512M`/`CPUQuota`/`TasksMax` ceilings
+ restart backoff), **no code change**; `systemd-analyze security` 9.2 UNSAFE ->
4.1 OK (verified offline). Install is an operator step (`DEPLOY.md` §5.1).
`RMT_PRODUCTION_READINESS.md` §4 summary table resynced (24 READY / 7 PARTIAL /
3 GAP). Next: **P1** (V1, R3). Monitoring / exercise calls now require a token
header.
**Owner directive 2026-09-08: no Core modification or fix** — recorded
frozen-Core gaps get an above-Core mitigation or an explicit accept-and-record,
never a freeze deviation. CAP-04, CAP-05 (5A) and CAP-05 (5B) are all enabled on
the live server (2026-09-07); the CAP-04 loop is idle at `no_remediation` and
the agent surface sits at `0` grants. Do not begin implementation of a new
capability until the owner selects and authorizes it. Do not reopen C01–C07; do
not invent a new Core milestone (no C08).

## 13. Environment limitations vs genuine implementation gaps

- **Shell-dependent tooling.** Git and Docker availability depend on which shell
  the session runs in. A prior session ran inside an Ollama Snap confinement
  where the Docker socket returned `PermissionError(13)` and git was unavailable;
  in that context the RMT FastAPI backend (a normal host process) was the way to
  reach Docker. As of 2026-09-06 the working shell has **git functional** (HEAD =
  freeze commit `46a4441`) and **Docker reachable** (`docker_available()` → True;
  `get_containers()` → `portainer, dozzle, uptime-kuma`). Verify in the current
  shell rather than assuming either state.
- Docker is an above-Core adapter concern regardless of reachability; the Core
  must not hard-depend on it.
- **`httpx2` is installed** (test dependency) — HTTP route tests are possible.
- **Adapter selection is environment-sensitive:** `config/config.yaml` sets
  `runtime.engine: docker`, and `_resolve_adapter_name()` returns `"docker"` only
  when the Docker adapter is registered (i.e. `docker_available()` is True),
  otherwise the safe `simulation` adapter. Tests that exercise an executed path
  must mock the execution adapter rather than depend on ambient Docker (see the
  C07 `test_http_entrypoints.py` correction, 2026-09-06).
- Environment limitations must **not** automatically be classified as
  implementation defects.

## 14. Deferred issues — disposition recorded

- **`module_registry.register_module()`** — an **internal governed primitive**, not
  a bypass and not a missing Core requirement. Disposition recorded at C07 closure.
- **`execution/service.py::execute_action()`** — **unreachable dead-code
  housekeeping**, no C07 impact.
- Committed HTTP-route test evidence (existing public routes only) — recorded.
- **C07 freeze deviation #1 (COMPLETED, verified):** `platform_state` provider
  extraction removed the Core's direct `app.docker_api` dependency via a generic
  `PlatformStateProvider` protocol; Docker implementation moved outside Core
  (`app/docker_provider.py`). `/platform/state` contract preserved; 122 tests
  green. Adapter-decoupling #2–#18 remain DEFERRED under the owner REDUCE-SCOPE
  decision (see `docs/RMT_CORE_ADAPTER_DECOUPING.md`).
- G2 Core-boundary review record — recorded (PASS).
- **Frozen-Core note (recorded 2026-09-07, not fixed):**
  `approve_held_action` (`app/core/intelligence/actions/approval_service.py`)
  sets `hold.status = APPROVED/REJECTED` on the in-memory object but only
  persists the approval **record** store, never the approval **hold** store —
  so a resolved hold can read `pending` on disk after a process restart. The
  **record** store is authoritative on resolution. Surfaced by CAP-04's
  duplicate-hold guard, which now cross-checks the record store + hold TTL.
  Core is frozen; owner consideration only.
- **Frozen-Core note (recorded earlier, not fixed):** a *failed* adapter
  execution produces no verification evidence (AGENTS.md §11 lists it as a
  distinguishable outcome). Owner consideration only.

## 15. Rules for distinguishing FACT / DECISION / PROPOSAL / UNKNOWN

- **FACT:** established by repository/evidence (code, tests, recorded results).
- **DECISION:** a recorded architectural/scope decision (e.g., no HTTP evolution
  route; deny-only execution policy).
- **PROPOSAL:** a suggested change not yet accepted.
- **UNKNOWN:** not yet established by evidence; state it as unverified.
- Never silently convert assumptions into facts.

## 16. Rules for evaluating proposed Core changes

A proposed change may enter the remaining Core roadmap only if it closes a
verified gap against `RMT_CORE_TARGET_STATE.md`. Otherwise it is classified as
**ABOVE-CORE / DOMAIN**, **FUTURE**, or **NOT REQUIRED**. There is no C08; after
C07 the Core is complete or frozen.

## 17. Working / coordination method with the user

1. Read-only reconnaissance and contract review.
2. Verify claims against the repository and governing documents.
3. Propose the smallest bounded change; get explicit approval.
4. Implement; add tests; run the suite; report evidence.
5. Report files changed, results, deviations, and any conflicts.

## 18. Bootstrap instructions for a new technical session

1. Read `RMT_CONTEXT.md` first.
2. Read `HANDOFF.md` second.
3. Read `STEWARD.md` (session opener) and follow it.
4. Read the relevant governing documents.
5. Verify consequential claims against the repository.
6. Do NOT ask the user to reconstruct project status if the documents already
   establish it.
7. Do NOT ask "where are we?" or "what is next?" as the default.
8. State the verified understanding briefly.
9. Continue from the established next action.
10. If evidence conflicts with context, identify the conflict and resolve it
    using the governing documents/repository evidence.
11. Never silently convert assumptions into facts.

---

## Final boundary statements

- **Do not invent another Core milestone after C07.** C07 is the final finite
  Core validation/freeze stage. There is intentionally **no C08**.
- **Platform Freeze** occurs only after the Target State has been validated.
- Future work after Core Freeze is primarily above-Core/domain/product/
  integration/adapter/application work.
- The next phase is **not Core development** and must not reopen C01–C07. The
  next objective is the **First Real RMT Capability — Homelab Operations**: use
  the frozen Core as the intelligent control plane for the real homelab.
- Closed milestones must not be reopened without evidence.
- A useful capability is not automatically a Core requirement.
- Environment limitations must not automatically be classified as
  implementation defects.
- Repository evidence takes precedence over conversation memory.
- Governing documents take precedence over assumptions.
