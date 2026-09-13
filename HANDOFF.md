# RMT — Session Handoff

> **Read order for a new session:**
> 1. `RMT_CONTEXT.md` — stable project brain / bootstrap context (identity,
>    lifecycle, boundary, decisions, milestone status, next action).
> 2. `HANDOFF.md` — fine-grained session history / continuation context
>    (this file: latest session, work performed, evidence, discoveries,
>    files changed, unresolved items, immediate next action).
> 3. The relevant governing documents (`docs/RMT_MASTER_DEFINITION.md`,
>    `docs/RMT_CORE_TARGET_STATE.md`, `docs/RMT_CORE_GAP_MATRIX.md`,
>    `docs/RMT_CORE_REMAINING_ROADMAP.md`, `AGENTS.md`).

## How to resume

Start the next session with the resume prompt below (see "Resume prompt").
Read `RMT_CONTEXT.md` first, then this file.

## Current state

- **C01 — Governed Execution Boundary: CLOSED**
- **C02 — Durable Governance Evidence: CLOSED**
- **C03 — Post-Execution Verification: CLOSED**
- **C04 — Generalized Understand → Decide Completion: CLOSED**
- **C05 — Controlled Platform Self-Management: CLOSED**
- **C06 — Controlled Platform Evolution: CLOSED**
  - Direct `register_module()` remains explicitly deferred to C07 (not a C06
    defect).
- **C07 — Platform Validation and Freeze: CLOSED** — RMT Core **Platform Freeze**
  declared (freeze commit `46a4441` — "RMT Core Platform Freeze"). Finite
  platform-validation suite passes (122 tests); G2 Core-boundary review passed;
  no reachable governance bypass; no remaining required Core capability.

## Latest session (C07 Phases 4–6)



Work performed and evidence:

- **Phase 4 — Finite validation executed.**
  - Baseline full suite: **114 passed**.
  - Installed `httpx2` (test-only dependency) so FastAPI `TestClient` works.
  - HTTP validation of existing routes: `POST /execute` (allowed/hold/
    unsupported), `POST /approve` (continuation/not-found), read-only GET routes.
  - **Found D1 defect:** `GET /intelligence/health` → 500
    `AttributeError: 'ComponentObservation' object has no attribute 'cpu_usage'`
    (`app/core/intelligence/service.py` `calculate_platform_health` read stale
    attributes instead of `observation.signals`).
  - Environment-limited routes (not Core defects): `/platform/state` (git
    absent), `/containers*` (docker socket denied; above-Core).
- **Phase 5 — D1 analysis + authorized minimal fix.**
  - Confirmed stale-consumer root cause; canonical contract is
    `ComponentObservation.signals`.
  - Applied minimal fix in `app/core/intelligence/service.py`:
    `current_cpu=observation.signals.get("cpu_usage", 0)` /
    `current_memory=observation.signals.get("memory_usage", 0)`.
  - Added focused regression test
    `test_deviation_branch_uses_signals_contract` in
    `app/core/intelligence/testing/test_phase1_d1_d2.py`.
  - `GET /intelligence/health` now HTTP 200.
- **Phase 5 — G2 Final Core-Boundary Review: PASS.**
  - No genuine Core implementation gap after D1; only evidence packaging
    remains. Environment limitations are not Core blockers.
- **Phase 6 — Evidence packaging.**
  - Created `app/core/intelligence/testing/test_http_entrypoints.py` (7 HTTP
    transport tests, existing public routes only, isolated in-memory stores).
  - Full suite now **122 passed** (115 + 7).
  - **Discovery:** the approval-continuation path saves its manual authorization
    via `approval_service.execution_authorization_storage`
    (`approval_service.py:201`), an additional module-level storage reference
    that the existing `test_evolution._setup_isolation` helper does not patch.
    The new HTTP test patches it. (Latent isolation gap in the existing helper —
    test-housekeeping note, not a Core defect.)
  - Evidence-store pollution check: all six durable JSON stores unchanged by the
    committed HTTP artifact. During interim debugging, 4 manual-authorization
    records were written to `authorizations.json`; these were identified and
    removed, restoring the file to its prior 4-record state.

## Current next milestone / action

**C01–C07: CLOSED.** **RMT Core Target State: ACHIEVED.** **RMT Core Platform
Freeze: REACHED** (freeze commit `46a4441`). There is no C08.

**Operational production-readiness (`docs/RMT_PRODUCTION_READINESS.md`): P0 + P1
+ P2 ALL COMPLETE (2026-09-08).** Every row of the matrix is **READY** except
`R4` (no HA), which stays **ACCEPTED** at homelab scale.
- **P1** (D1, D2, R1, E3, S3, E4, E5, O3, V2, O1, D3, V1, **R3**) — R3 was the
  last: bare-host rebuild (`deploy/systemd/` unit+drop-ins,
  `backend/scripts/rmt-rebuild.sh`, `docs/operations/RMT_PLATFORM_RECOVERY.md`),
  scratch-dir drill passed. Recommended once: a real from-cold VM rebuild.
- **P2** (S5, S6, S7, D4, D6, O4, V3, V4) — all closed above-Core, no
  `app/core/**` change, full suite **365 passed**. See the two session notes at
  the end of this file.

**Immediate next action:** the next phase is **not Core development** and must not
reopen C01–C07. The **First Real RMT Capability — Homelab Operations** is now
realized: the frozen RMT Core acts as the intelligent control plane for the real
homelab through the full governed lifecycle
**Understand → Decide → Govern → Authorize → Execute → Verify → Learn**.

**RMT-CAP-04 — Continuous Homelab Operational Loop: COMPLETED & VERIFIED
(2026-09-07).** The single-shot Homelab lifecycle now runs on a supervised,
periodic cadence (disabled by default; opt-in via env var or
`POST /homelab/loop/start`). Implementation confined to `app/homelab/**` +
`app/main.py`; no `app/core/**` change; no C08; C01–C07 remain closed/frozen.
Validation: 17 focused tests; Homelab suite 38 passed; Core suite 122 passed;
full app suite 177 passed. T13 disposition recorded
(`docs/RMT_T13_DISPOSITION.md`). See `docs/RMT_CAPABILITIES_EVIDENCE.md` §CAP-04.

**Next:** the next above-Core capability is to be selected by the owner from the
candidate directions (engineering intelligence expansion, frontend
governed-evidence/productization, real Docker demonstration, AI Agent
Governance). Do not begin implementation until the owner selects and authorizes
it. Do not reopen C01–C07; do not invent a new Core milestone (no C08).

## Important boundary

- **C07 is CLOSED and the RMT Core is frozen.** No new Core milestone (no C08).
- **Disposition of deferred items (recorded):**
  - `module_registry.register_module()` — an **internal governed primitive**, not
    a bypass and not a missing Core requirement.
  - `execution/service.py::execute_action()` — **unreachable dead-code
    housekeeping**, no C07 impact.
- No HTTP evolution route is required; evolution is validated at the governed
  service boundary.
- Environment limitations (git absent, docker socket denied) are preserved and
  are not Core defects; `/containers*` remain above-Core.

## Validation command

```bash
cd /home/rmt-lab/homelab/projects/homelab-control-center/backend
source .venv/bin/activate
PYTHONPATH=. pytest app/core/intelligence/testing -q
```

## Expected currently validated result

- Full suite: **122 passed** (verified).
- C07 HTTP artifact: `test_http_entrypoints.py` — 7 passed.
- D1 regression: `test_deviation_branch_uses_signals_contract` — passed.

## Architectural principles (preserve)

- Understand -> Decide -> Govern -> Authorize -> Execute -> Verify -> Learn
- Single governed mutation boundary
- Learning remains read-only
- No speculative Core expansion
- No changes to protected authority documents without explicit approval

## Resume prompt

> RMT Core is post-freeze. C01–C07 are closed; RMT Core Target State ACHIEVED;
> Platform Freeze REACHED (freeze commit `46a4441`); there is no C08. Read
> `RMT_CONTEXT.md` first, then `HANDOFF.md`, then the governing documents. Full
> suite is 122 passed; D1 resolved; G2 passed. register_module() is an internal
> governed primitive; execute_action() is unreachable dead-code housekeeping.
> The next phase is NOT Core development and must not reopen C01–C07. Next
> objective: First Real RMT Capability — Homelab Operations (use the frozen Core
> as the intelligent control plane for the real homelab). Do not start
> implementation yet. Start with read-only reconnaissance and contract review.
> Do not modify files or run system/git commands without explicit approval.

## Key files

- `RMT_CONTEXT.md` — stable project brain / bootstrap context (read first).
- `AGENTS.md` — governing contract; read first (authority hierarchy, rules).
- `docs/RMT_MASTER_DEFINITION.md`, `docs/RMT_CORE_TARGET_STATE.md` — top authority.
- `docs/RMT_CORE_GAP_MATRIX.md`, `docs/RMT_CORE_REMAINING_ROADMAP.md` — gaps + roadmap.
- Backend: `projects/homelab-control-center/backend`.

## Environment caveats

- **Git is NOT installed** on this system — `git status`/`git log`/`git tag`
  will not work. The user handles git separately. This is a tooling limitation,
  not a new RMT milestone.
- **Docker is NOT accessible** here (permission denied on the socket) — live
  docker execution and `/containers*` routes require docker; tests use mocks.
  Docker is an above-Core adapter concern.
- **`httpx2` IS installed** (test dependency) — FastAPI `TestClient` HTTP route
  tests work.
- **`~` expands incorrectly** in this shell — use explicit paths
  (`/home/rmt-lab/homelab/...`).

## Working pattern that worked well

1. Read the milestone contract + authority docs.
2. Read-only integrated verification against the contract.
3. Get explicit approval before implementing.
4. Implement the bounded change; add tests; run the suite.
5. Report files changed, summary, test result, deviations.


---

## Session note — C07 freeze deviation #1 (platform_state provider extraction)

**Completed and verified (2026-09-04).** Owner approved a narrowly scoped C07
freeze deviation: remove the concrete Docker dependency from
`app/core/platform_state/service.py` via a generic provider protocol.

- New: `app/core/platform_state/provider.py` (`PlatformStateProvider` protocol).
- Modified: `app/core/platform_state/service.py` (no longer imports
  `app.docker_api`; `get_platform_state(provider)` consumes the protocol).
- New (outside Core): `app/docker_provider.py` (`DockerPlatformStateProvider`).
- Modified: `app/main.py` (composition root injects the Docker provider).
- New test: `app/core/platform_state/testing/test_platform_state_provider.py` (3 passed).

Dependency direction: `Core service -> protocol <- Docker implementation`.
`/platform/state` JSON contract preserved exactly. Full C07 suite: **122 passed**
(no regressions). No out-of-scope area touched; no new milestone; C01–C07 remain
closed.

**Deferred (owner REDUCE-SCOPE decision):** #2–#18 of the adapter-decoupling
work item remain deferred. Do not automatically proceed to #2; reassess the
remaining findings against the frozen Target State before any further
authorization. See `docs/RMT_CORE_ADAPTER_DECOUPING.md` §9.

---

## Session note — RMT-CAP-02 (Engineering Change-Impact & Risk Analysis)

**Completed and verified (2026-09-04).** Above-Core capability, read-only,
deterministic, evidence-backed.

- New `app/engineering/` package: `models.py`, `repo_index.py`, `service.py`,
  `api.py`, `testing/test_engineering.py`.
- Modified: `app/main.py` (registered read-only `GET /engineering/change-impact`
  router; additive only).
- Reuses frozen Core read-only primitives only (`get_modules`,
  `get_governed_outcomes`, `get_previous_failures`, `get_component_context`).
- **Validation:** 14 focused tests passed; full app suite **155 passed**
  (141 baseline + 14 new). `app.main` imports cleanly.
- **Core integrity:** C01–C07 untouched; no frozen Core file modified; governed
  execution semantics untouched; read-only guarantee verified.
- **Semantic clarification:** `unknown_dependency=True` = incomplete/
  unestablished dependency knowledge (empty/unpopulated `dependencies`), NOT a
  discovered actual unknown dependency.
- **Evidence index:** see `docs/RMT_CAPABILITIES_EVIDENCE.md`.

**Next:** next above-Core capability to be selected by the owner. No C08; no
Core changes.

---

## Session note — First live homelab operation (fault-injection validation)

**Date:** 2026-09-04. This is an OPERATIONAL event + findings, not a code change.

### Environment finding (important for future sessions)
- The **TA/RMT command shell runs inside the Ollama Snap confinement** (`SNAP_NAME=ollama`,
  v0.32.14; `Seccomp:2`, `CapEff=0`). It **cannot connect to the Docker socket**
  (`connect()` → `PermissionError(13)`) even though host socket permissions
  (`/var/run/docker.sock` = root:docker 660) and group membership are correct.
- **Workaround that works:** the RMT **FastAPI backend runs as a normal host process**
  (separate from the Snap sandbox) at `http://127.0.0.1:8000` and **has Docker access**.
  Drive RMT via its HTTP API, not via the Snap shell's Python/docker.
- Docker daemon IS running; Docker CLI not installed (not required by RMT).

### First live governed operation — RESULT: PASS (with one Learn observation)
Full lifecycle: Understand → Decide → Risk → Policy → Approval → Authorization →
Execute → Verify → Audit/Evidence → Learn.
1. **Fault injection:** governed `POST /execute?operation=stop&target=uptime-kuma`
   (execution `4e1c86ff…`) → uptime-kuma `exited`. portainer/dozzle untouched.
2. **Observation:** RMT health → uptime-kuma **CRITICAL** (collector_failure, conf 80).
3. **Remediation:** `POST /homelab/remediate?component=uptime-kuma` →
   **`manual_approval_required`** (action `9fda6452…`, approval `316257fc…`). Held; no mutation.
4. **Approval:** `POST /approve` (approval `316257fc…`) → **executed** via Docker adapter:
   execution `666f42af…`, status completed, success true.
5. **Verify:** RMT verification → `observation_unavailable` (fail-safe, not fabricated).
   Live post-state independently confirmed: uptime-kuma **running**.
6. **Audit/evidence:** audit `666f42af…` (completed); trace `9fda6452…` (allow, medium);
   authorization `9fda6452…` (approved, uptime-kuma); approval record (approved);
   verification `666f42af…` (observation_unavailable). All correlated by IDs.
7. **Learn:** learning record written: `remediation | manual_approval_required |
   approval_id 316257fc…`.

### Finding — Learn-stage gap (evidence-backed, above-Core)
`_record_learning()` runs in `remediat_and_verify()` BEFORE the approval
continuation. When the action is continued via `POST /approve`, the **executed
outcome** (execution `666f42af…`) is **NOT** written as a learning record — only
the held (`manual_approval_required`) state is recorded. The executed outcome is
not captured in the Learn stage for approval-continuation remediations.

### Current state
- Full test suite: **155 passed** (unchanged; no code changed this session).
- C01–C07 remain closed/frozen; CAP-01, CAP-02 complete; no C08.
- **Next possible follow-up (owner decision):** whether to close the Learn-stage
  gap so approval-continuation remediation outcomes are recorded as learning.
  Above-Core scope; no Core change required. Do not implement without approval.

---

## Session note — RMT-CAP-03 (approval-continuation Learn closure) + C07 artifact fix

**Date:** 2026-09-06. Above-Core capability + one owner-approved C07 test-artifact
correction. C01–C07 remain closed/frozen; no C08; no frozen Core code modified.

### Environment facts (updated — this shell is NOT the Snap-confined shell)
- **Git works here** (`git log`/`status`/`stash` all functional). HEAD = freeze
  commit `46a4441`. Working tree carries the prior uncommitted above-Core work
  (platform_state provider extraction, `app/engineering/`, `app/homelab/`, CAP
  docs) plus this session's CAP-03 changes.
- **Docker IS reachable here** — `docker_available()` returns True;
  `get_containers()` → `['portainer','dozzle','uptime-kuma']`. This differs from
  the 2026-09-04 note (Snap confinement, socket `PermissionError(13)`). The
  standing "Docker/Git not accessible" caveats are shell-specific, not universal.
- A `STEWARD.md` session-opener file is present at repo root (not created by this
  session).
- **MCR = Master Control Room** (owner-confirmed 2026-09-06). A supervisory
  *architectural pattern*: one supervisor governs the consequential actions of
  many independent, internally-autonomous "child" systems (apps, infra, AI
  agents, other platforms) via a single authoritative consequential-mutation
  boundary. It is a lens on RMT's existing role, **not** a new subsystem or
  milestone; subordinate to RMT's governing architecture.
- Two above-Core MCR docs in `docs/` (v0.1, not RMT authority docs):
  - `MCR_ARCHITECTURAL_PRINCIPLE.md` — the principle (intent / what & why).
  - `MCR_SUPERVISORY_CONTRACT.md` — the compliance spec (C1–C10, fail-closed,
    replay, evidence standard). The two cross-reference each other.
- The MCR experiments (`experiments/mcr/`, `mcr2/`, `mcr3/`), dated 2026-09-06:
  `MCR-EXP-3` = 14/14 adversarial tests, no boundary bypass (Claim A + B for the
  tested tool surface; Claim C not claimed), one recorded **T13 policy-level
  finding** — effect-based governance at the mutation boundary does not catch a
  restricted effect reached indirectly via an *allowed* dependency operation.
  Boundary integrity ≠ policy completeness. **T13 disposition recorded
  2026-09-07** (`docs/RMT_T13_DISPOSITION.md`): ACCEPT (with constraint) + BOUND
  + DEFER. Not a live defect in Core or CAP-01..04. CAP-04 may be enabled only
  inside its *safe-enablement envelope* (every `REMEDIATION_POLICY` entry
  independent + `requires_approval=True`, guard test
  `test_remediation_policy_within_cap04_safe_envelope`); the full
  dependency-cascade escalation fix is assigned to CAP-05.

### RMT-CAP-03 — COMPLETED & VERIFIED
Closes the Learn-stage gap identified in the 2026-09-04 fault-injection note: the
**executed** outcome of an **approval-continuation** remediation is now recorded
as a learning record, with above-Core Docker verification.

- **New** `app/homelab/continuation.py` — `continue_remediation(approval_id,
  approved_by, approved=True)`: calls frozen Core `approve_held_action()`
  unchanged, then for an executed Homelab remediation runs
  `verify_docker_execution(...)` and `record_learning(...)`, correlated by
  `approval_id` / `execution_id`. Non-Homelab holds pass through unchanged.
- **Modified** `app/homelab/remediation.py` — `_record_learning` → `record_learning`
  (shared) + comments; no behavior change.
- **Modified** `app/main.py` — new route `POST /homelab/approve`. Generic
  `POST /approve` untouched.
- **New** `app/homelab/testing/test_continuation.py` — 5 run-safe tests.
- **Validation:** 5 focused passed; Homelab suite **21 passed** (16 + 5); C07/Core
  intelligence suite **122 passed**; full app suite **160 passed** (155 + 5).
- **Core integrity:** diff confined to `app/homelab/**` + `app/main.py`; no new
  authorization/execution path; learning append-only / read-only.

### C07 test-artifact correction (owner-approved, option 1)
`app/core/intelligence/testing/test_http_entrypoints.py` had **2 failures**
(`TestExecute::test_execute_low_risk_auto_allowed_records_evidence`,
`TestApprove::test_approve_valid_continuation_executes`) — reproducible at pure
`46a4441`, **not** caused by CAP-03. Root cause: the artifact did not mock the
execution adapter and implicitly assumed `docker_available()` is False (safe
`simulation` fallback). Docker being reachable in this shell made
`_resolve_adapter_name()` pick the real Docker adapter, which failed on
non-existent containers `web1`/`db2`; verification is skipped when
`result.success` is False (frozen-Core behavior), so the verification store was
empty. **Fix:** mock the execution adapter registry in that file's
`_isolate_evidence_stores` (mirrors `test_integrated.py`); diff confined to the
one test file (+24/−1); no Core code touched. Core intelligence suite restored to
**122 passed**.

Secondary observation (frozen-Core design note, not fixed, out of scope): a
*failed* adapter execution produces **no** verification evidence at all — not
even `verification_failure` / `state_mismatch`. AGENTS.md §11 lists
"adapter invoked and failed" as an outcome that should be distinguishable in
evidence. Recorded for owner consideration only.

### Next
- **CAP-04 — Continuous Homelab Operational Loop: COMPLETED & VERIFIED
  (2026-09-07).** See the session note below and
  `docs/RMT_CAPABILITIES_EVIDENCE.md` §CAP-04.
- Owner disposition still pending on: the MCR/T13 dependency-cascade policy
  finding (open above-Core work item); whether the MCR pattern informs a future
  above-Core capability (e.g. AI Agent Governance — governing a reasoning agent
  as an MCR "child"). MCR docs are recorded in `docs/` but are **not** RMT
  authority documents and do not change C01–C07.

---

## Session note — RMT-CAP-04 (Continuous Homelab Operational Loop)

**Date:** 2026-09-07. Above-Core capability. C01–C07 remain closed/frozen; no
C08; **no `app/core/**` file modified**. Owner-approved scope:
`docs/RMT_CAP_04_PROPOSAL.md`.

### Housekeeping (start of session)
- Removed two stale untracked files: `_validate_docker_adapter.py` (superseded
  one-off Docker-adapter validation script — the adapter is committed in freeze
  commit `46a4441`) and a 6-line empty root `package-lock.json` (accidental
  `npm` run; no root `package.json`).

### CAP-04 — COMPLETED & VERIFIED
Runs the existing single-shot Homelab governed lifecycle on a cadence, under
supervision. **Cadence + guardrails only — no new mutation path.**

- **New** `app/homelab/operational_loop.py` — `HomelabOperationalLoop`
  (singleton `operational_loop`). Each cycle iterates `REMEDIATION_POLICY`
  components → calls the existing `remediate_component(component)` → classifies
  the governed outcome → updates per-component loop state → appends a bounded
  cycle record. Guardrails: **approval retained** (`manual_approval_required`
  recorded, never continued — `continue_remediation` not imported here);
  **flap guard** → quarantine after N held/failed attempts in a window (then
  read-only recovery checks only, via `observe_container_state`, until a healthy
  streak or a manual clear); **cooldown** after every attempt;
  **duplicate-hold guard** (read-only query of the approval hold store; a
  `pending` hold for the component → `awaiting_approval`, no second hold, no
  flap count); **single-flight**
  (`_cycle_in_progress` guard); **fail-safe** (per-component + per-cycle
  `try/except`; the task never raises into the app). State transitions recorded
  append-only via the existing Core memory capability (`remember` +
  `MemoryRecord`) with distinct `event_type`s (`homelab_loop_quarantine`,
  `homelab_loop_recovery`, `homelab_loop_quarantine_cleared`) — kept out of the
  remediation-outcome record stream.
- **New** `app/homelab/loop_config.py` — env-overridable constants read
  dynamically each cycle. `LOOP_ENABLED` default **False** (opt-in). Interval
  120s; flap window 900s / threshold 3; cooldown 300s; recovery streak 2;
  history cap 50. No `app/core/configuration/**` change.
- **Modified** `app/main.py` (+52) — `lifespan` starts the loop task only when
  `LOOP_ENABLED`, stops it on shutdown; new routes
  `GET /homelab/loop/status` (read-only), `POST /homelab/loop/start`,
  `POST /homelab/loop/stop`, `POST /homelab/loop/clear?component=`
  (`start`/`stop` are `async def` so they run on the event loop).
- **New** `app/homelab/testing/test_operational_loop.py` — 15 run-safe tests
  (11 loop behaviour + 3 duplicate-hold guard + 1 T13 safe-envelope guard;
  `remediate_component`, `observe_container_state`, `remember` and the approval
  hold store mocked/isolated; asyncio task never started).

### Validation
- New focused: **15 passed** (11 loop + 3 duplicate-hold guard + 1 T13 envelope
  guard).
- Full Homelab suite: **36 passed** (21 baseline + 15).
- Full C07/Core intelligence suite: **122 passed** (unchanged — frozen Core
  intact).
- Full app suite: **175 passed** (160 baseline + 15).
- `import app.main` clean; loop confirmed **disabled by default**.

### Core integrity
Diff confined to `app/homelab/**` + `app/main.py` (+52). No second mutation
boundary — routes through `execute_governed_action` via the existing entrypoint
only. Approval enforcement unchanged. Learning append-only / read-only.

### Deviations from the approved proposal
- State-transition Learn records use `remember()` + `MemoryRecord` **directly**
  with a distinct `event_type`, rather than `record_learning()` (which is
  remediation-specific and hardcodes `event_type="remediation"`). Still the
  Core memory boundary, still append-only. Minor, keeps loop-transition records
  distinct from remediation-outcome records.

### Open / next
- **T13 disposition — RECORDED 2026-09-07** (`docs/RMT_T13_DISPOSITION.md`):
  ACCEPT (with constraint) + BOUND + DEFER. CAP-04 as shipped is inside the
  *safe-enablement envelope* (one independent RESTART-only, approval-gated
  component), enforced by `test_remediation_policy_within_cap04_safe_envelope`.
  Full dependency-cascade escalation fix assigned to CAP-05. Enabling CAP-04
  within the envelope no longer waits on a separate T13 decision.
- Enabling in the real homelab: **DONE 2026-09-07** — `RMT_HOMELAB_LOOP_ENABLED=true`
  via systemd drop-in; live demonstration performed the same day (see notes
  below). Redeployed 2026-09-07 with the guard hardening; live loop then idle at `no_remediation`.
- **Recorded frozen-Core notes** (Core is frozen; owner consideration only):
  - a *failed* adapter execution produces no verification evidence
    (AGENTS.md §11 lists it as a distinguishable outcome);
  - `approve_held_action` flips `hold.status` in memory but does not reliably
    persist the approval **hold** store — a resolved hold can read `pending` on
    disk after a restart. The approval **record** store is the reliable source
    of truth; CAP-04's guard now uses it (see the enablement session note).

---

## Session note — CAP-04 first live demonstration (real homelab)

**Date:** 2026-09-07. OPERATIONAL EVENT + evidence, not a code change. Owner
authorized ("go run it").

### Method
The systemd-managed backend (`rmt-control-center.service`, PID 1261, :8000) is
pre-CAP-04 and could not be restarted from this shell (no sudo). Ran an
**isolated second instance** of the same tree on **:8001** (my process, loop
initially OFF, demo cadence `RMT_HOMELAB_LOOP_INTERVAL_SECONDS=20` /
`LOOP_COOLDOWN_SECONDS=30`). The :8000 service was left untouched and stayed
`active` throughout. Same code, same real Docker adapter, same real containers,
same durable evidence stores.

### Sequence (all on `uptime-kuma` only; portainer/dozzle untouched)
1. **Pre-state:** `uptime-kuma` running/healthy.
2. **Fault injection:** governed `POST /execute?operation=stop&target=uptime-kuma`
   (:8001) → execution `9db08379…` completed → container `exited` / `unhealthy`.
3. **`POST /homelab/loop/start`** → loop `enabled=true, running=true`.
4. **Cycle 1** (09:23:37): health eval CRITICAL (collector_failure, conf 80) →
   remediation **`manual_approval_required`** — held, no mutation
   (approval `5c7085a5…`).
5. **Cycle 2**: `skipped_cooldown` (flap guard working).
6. **Cycle 3** (09:24:17): still-stale observation → a second held remediation
   (approval `79d6383a…`); `attempts_in_window=2`, still not quarantined.
7. **`POST /homelab/approve`** (CAP-03 endpoint) for `5c7085a5…`,
   `approved_by=demo-operator-2026-09-07` → **executed** via the `docker`
   adapter: execution `40b3dce9…`, success true, "restart on uptime-kuma".
   Core verifier `observation_unavailable` (fail-safe); above-Core Docker
   verifier **`verified_success`** ("Observed state matches expected outcome").
8. **Cycle 5** (09:25:00): observation refreshed → **`no_remediation`**;
   `attempts_in_window=0`, `consecutive_failures=0`, `healthy_streak=1` — loop
   stood down on its own.
9. **`POST /homelab/loop/stop`**; rejected the cycle-3 orphan hold
   `79d6383a…` (`approved=false`); killed the :8001 instance.
10. **Final:** `uptime-kuma` running/healthy (restarted 09:24:09);
    portainer/dozzle running; :8000 service `active`.

### Evidence bundle (all correlated by `action_id 17d573aa…` /
`execution_id 40b3dce9…` / `approval_id 5c7085a5…`)
- **approval_record** `5c7085a5…` → approved by `demo-operator-2026-09-07`.
- **authorization** `e99c43a1…` → type `manual`, single-use, `expires_at`
  09:29:09, target uptime-kuma / restart / expected_state running.
- **trace** `635ddc2e…` → policy `allow`, risk `medium`, outcome `completed`.
- **audit** → adapter `docker`, status `completed`, risk `medium`.
- **verification** → `observation_unavailable` (Core) + **`verified_success`**
  (above-Core Docker observer; observed `running` == expected `running`).
- **Learn** (`intelligence_memory`, ids 275–278): `health_evaluation` CRITICAL →
  `remediation manual_approval_required` (held) → **`remediation executed`**
  with `docker_verification_status=verified_success` (the CAP-03 Learn-closure,
  demonstrated live) → `remediation manual_approval_required` for the rejected
  cycle-3 hold.

### Result
**PASS.** The supervised loop ran the full lifecycle
`Understand → Decide → Govern → Authorize → Execute → Verify → Learn` on a
cadence against the real homelab. Approval was retained (loop never
auto-continued a hold); flap-guard cooldown fired; the loop stood down once the
system recovered. No `portainer`/`dozzle` impact; systemd service unaffected;
no code change.

### Observations (recorded, not defects)
- With a fast demo cadence the loop raised a **second** held remediation
  (cycle 3) before the 60 s metric collector reflected the approved restart.
  Bounded by cooldown; would have quarantined after 3. **RESOLVED 2026-09-07**
  by the *duplicate-hold guard* refinement (`operational_loop.py`
  `_pending_hold_for`): a read-only query of the approval hold store; if a
  `pending` hold already exists for the component the loop returns
  `awaiting_approval` — no second hold, no flap count, no spurious quarantine.
  3 new run-safe tests; full app suite **175 passed**.
- Core verifier returned `observation_unavailable` while the above-Core Docker
  verifier returned `verified_success` — same split as the 2026-09-04 run;
  expected (the Core observer is not the Docker observer).

---

## Session note — CAP-04 duplicate-hold guard refinement

**Date:** 2026-09-07. Above-Core; owner-authorized ("implement the refinement
with the store query"). Follows the live-demo observation above.

- **Modified** `app/homelab/operational_loop.py` — added `_pending_hold_for()`
  (read-only query of `_approval_service.approval_hold_storage.get_all()`,
  resolved through the Core module so runtime/test substitution is honoured —
  same pattern as `continuation.py`). In `_process_component`, before the
  cooldown / remediate path: if a `pending` `ApprovalHold` exists for the
  component, return the new benign outcome **`awaiting_approval`** — no
  `remediate_component` call, no new hold, no cooldown, no `attempt_times`
  entry, no streak change. Cycling resumes automatically once the hold is
  approved / rejected / expired or the component recovers.
- **Modified** `app/homelab/testing/test_operational_loop.py` — autouse
  `isolate_hold_store` fixture (empty in-memory `ApprovalHoldStorage`) so no
  test sees real pending holds; 3 new tests (suppresses new remediation; never
  quarantines while awaiting approval; cycling resumes after the hold is
  resolved).
- **No `app/core/**` change; no new mutation path** — the guard only *reads*
  the hold store. Diff confined to `app/homelab/**`.
- **Validation:** 15 focused (12 + 3); Homelab **36 passed**; Core intelligence
  **122 passed** (unchanged); full app **175 passed**.

---

## Session note — CAP-04 enabled on the live server + duplicate-hold guard hardening

**Date:** 2026-09-07. Owner-authorized ("close the CAP-04 (loop on for
uptime-kuma) before we start 5A").

### Enablement
- Added systemd drop-in
  `/etc/systemd/system/rmt-control-center.service.d/cap04-loop.conf`
  (`Environment=RMT_HOMELAB_LOOP_ENABLED=true`); `daemon-reload` + restart.
  `GET /homelab/loop/status` → `enabled: true, running: true` on live :8000.
  Disable = delete that file + `daemon-reload` + restart.

### Finding surfaced by enablement — frozen-Core hold-persistence gap
On the first live cycle the loop reported `awaiting_approval` keyed on hold
`316257fc…` — a **2026-09-04** uptime-kuma restart hold that was **approved and
executed that day**. Root cause (verified): `approve_held_action`
(`app/core/intelligence/actions/approval_service.py`) sets
`hold.status = APPROVED/REJECTED` on the in-memory object but **only persists
the approval RECORD store** (`approval_record_storage.update(...)`), never the
**hold store**. The hold's status reaches disk only if some *later*
`approval_hold_storage.save(new_hold)` in the same process flushes the list.
After a process restart the hold reloads as `pending`. Result on disk today:
`316257fc` hold=`pending` / record=`approved`; `79d6383a` hold=`pending` /
record=`rejected`; the genuinely-unresolved `54f685f6` (db1) record=
`manual_required`. **Recorded frozen-Core note — not fixed here** (Core is
frozen; the RECORD store is the reliable source of truth).

### Above-Core hardening (this session)
- `operational_loop.py` — new `_hold_is_still_actionable(hold, now)`. A PENDING
  hold blocks a new remediation only if **(a)** the approval **record** store
  has no terminal decision (`approved`/`rejected`) for it, **and** **(b)** its
  `expires_at` (Core `APPROVAL_HOLD_TTL_SECONDS = 300`) has not passed — a
  lapsed hold cannot be continued by the Core anyway. `_pending_hold_for` now
  uses it. Still read-only; still no `app/core/**` change.
- `test_operational_loop.py` — autouse fixture now also isolates
  `approval_record_storage`; `_pending_hold` sets a real `expires_at`; 2 new
  tests (resolved-but-still-`pending`-on-disk hold does not block; expired hold
  does not block).
- **Validation:** 17 focused (15 + 2); Homelab **38 passed**; Core intelligence
  **122 passed** (unchanged); full app **177 passed**.
- **Not touched:** the stale on-disk holds (`316257fc`, `79d6383a`). Re-rejecting
  `316257fc` via the API would overwrite its historical `approved` record — so
  they are left as-is; the hardened guard reads them correctly (both resolved +
  expired → ignored).

### Redeploy required
The live :8000 service is running the pre-hardening code (loop enabled but
blocked by `316257fc`). A restart picks up the guard fix; the loop then sits at
`no_remediation` against the healthy homelab.

---

## Session note — RMT-CAP-05 (5A) Governed Agent Surface

**Date:** 2026-09-07. Above-Core. Owner: "approve 5A now" (5B — the LLM agent —
explicitly held as a separate later decision). C01–C07 remain closed/frozen; no
C08; no `app/core/**` change.

### Delivered — new `app/agent/` package
- `contract.py` — MCR child surface as dataclasses: `AgentIdentity`,
  `AgentIntent` (goal kept distinct from mechanism), `AgentProposal`,
  `AgentOutcome`.
- `authority.py` — `AuthorityStore` (in-memory). Grants are operation+target
  scoped, time-limited (`AGENT_GRANT_TTL_SECONDS`, default 300s), **single-use**
  (consumed only when a proposal is accepted into the pipeline — `executed` or
  `manual_approval_required`; not on a pre-boundary deny). Capability ≠
  authority.
- `dependency_guard.py` — **T13 closure**. `escalate_for_dependency_cascade`:
  an allowed-class op (`start`/`create`) whose target has a dependent component
  (`ComponentContext.dependencies`) → forces `requires_approval=True`. Every
  dependency list is empty today → no-op; wired + tested so a widened envelope
  is safe by construction.
- `adapter.py` — `propose_and_govern(proposal)`: disabled gate → authority
  check → T13 escalation → `ActionRequest` → `execute_governed_action(...)` →
  `executed`: above-Core Docker verify + `record_learning`;
  `manual_approval_required`: `record_learning`, **never** auto-continued.
  Boundary exceptions contained (`decision="error"`, grant left intact).
- `reference_agent.py` — deterministic: `HealthEvaluation` CRITICAL → RESTART
  `AgentProposal`; else `None`.
- `api.py` — `POST /agent/authority/grant` (operator issues a grant — **added
  beyond the proposal's route list**, needed to make the surface usable),
  `POST /agent/act`, read-only `GET /agent/status` + `GET /agent/authority`.
- `app/main.py` — register `agent_router` (additive only).

### Validation
- 13 focused (`app/agent/testing/test_agent_governance.py`) — disabled gate;
  allowed→execute→verify→learn; held→recorded→not continued; policy_denied→
  grant intact; no grant / consumed / expired / scope-mismatch → `no_authority`;
  T13 escalation forces approval (seeded dependency edge); T13 no-op with real
  empty deps; status/authority endpoints read-only; boundary exception
  contained; reference agent proposes only on CRITICAL.
- Core intelligence **122** (unchanged); Homelab **38** (unchanged); full app
  **190 passed** (177 + 13). `import app.main` clean; `RMT_AGENT_ENABLED=False`
  by default.

### Core integrity
Diff confined to `app/agent/**` + `app/main.py`. No `app/core/**` change; no
second mutation boundary (proposal → `ActionRequest` → `execute_governed_action`
only); approval enforcement unchanged; held proposals never auto-continued;
learning append-only / read-only. Disabled by default; request-driven (no
background task).

### Open / deferred
- **5B** (LLM-backed agent adapter) — separate owner decision; nothing built.
- Populating `ComponentContext.dependencies` (makes the T13 guard load-bearing)
  — a separate explicit change.
- Not deployed to the live server (this is a new package; a redeploy would pick
  it up, still disabled by default).

### CAP-05 (5A) — deployed to live + controlled exercise (2026-09-07)

**Deploy:** `sudo systemctl restart rmt-control-center.service` (owner). Live
:8000 now carries the `/agent/*` routes; `GET /agent/status` → `enabled: false`
(agent OFF, as intended). CAP-04 loop unaffected (still enabled, `no_remediation`).

**Exercise:** owner-authorized ("1 then 2 later 5B"). Temp instance on :8001 with
`RMT_AGENT_ENABLED=true` (live :8000 left OFF). Live CAP-04 loop paused for the
window (`POST /homelab/loop/stop`) then resumed. Sequence:

1. `POST /agent/act` with **no grant** → `decision: no_authority`,
   `detail: no_grant`; governed boundary never reached.
2. `POST /agent/authority/grant` {restart, uptime-kuma, exercise-operator} →
   grant `c93a42edc87c` (5-min TTL, single-use).
3. `POST /agent/act` {reference-agent, restore uptime-kuma, restart, conf 80,
   grant} → `decision: hold`, `governed_status: manual_approval_required`,
   `approval_id 0c774a8d…`, `learn_recorded: true`, `escalated: false`. No
   execution.
4. `POST /agent/act` **replay same grant** → `no_authority` /
   `grant_consumed` (single-use enforced).
5. `POST /homelab/approve` (`approved_by=cap05-exercise-operator`) → **executed**
   via the `docker` adapter: execution `e3f3de2d…`, action `cba279ae…`,
   Core verify `observation_unavailable` (fail-safe) + above-Core Docker verify
   **`verified_success`**.

**Evidence bundle** (all correlated by `action cba279ae…` / `exec e3f3de2d…` /
`approval 0c774a8d…`):
- authorization `c4095d71…` — type `manual`, `authorized_by cap05-exercise-operator`,
  **`decision_id agent-reference-agent-3afbb8fe`** (proves agent-surface origin),
  target uptime-kuma/restart, expected_state running, 5-min TTL.
- trace `49e25830…` — policy `allow`, risk `medium`, outcome `completed`.
- audit — adapter `docker`, `completed`, risk `medium`.
- verification — `observation_unavailable` (Core) + **`verified_success`** (above-Core).
- Learn (`intelligence_memory` ids 309, 310) — `manual_approval_required` (held)
  → **`executed`** with `docker_verification_status=verified_success`.

**Result:** PASS. Agent-proposed → authority-checked → held for human approval →
approved → governed docker restart → verified → learned. Single-use authority
and capability≠authority both enforced. `uptime-kuma` healthy after; no
portainer/dozzle impact; systemd service unaffected.

**Restore:** live CAP-04 loop resumed (`no_remediation`, not quarantined); temp
:8001 killed; live agent surface confirmed `enabled: false`, 0 grants.

### CAP-05 — T13 completion (2026-09-07)

**Owner:** "complete the T13 implementation and then 5B".

The 5A escalation rule (`app/agent/dependency_guard.py`) existed but had no
dependency data (all `ComponentContext.dependencies` empty, and that file is
frozen Core). Completed above-Core, no Core edit:

- **New** `app/homelab/dependencies.py` — `HOMELAB_DEPENDENCIES`, the
  authoritative above-Core homelab dependency map. All three services recorded
  **independent** (`[]`): portainer / dozzle / uptime-kuma each need only the
  Docker daemon, not one another. Explicit `[]` = "established: independent"
  (vs the Core default "not established").
- **Modified** `app/agent/dependency_guard.py` — `_dependents_of` now unions the
  above-Core map with the frozen Core `ComponentContext.dependencies`; added
  `dependency_view()` for read-only status.
- **Modified** `app/agent/api.py` — `GET /agent/status` now includes
  `dependency_map` (resolved sources).
- **New** `app/agent/testing/test_dependency_guard.py` — 7 tests: real map → no
  escalation; seeded homelab edge → escalation; seeded Core edge → escalation
  (union); restricted op → not escalated; global disable; end-to-end through
  `propose_and_govern`.
- **Docs** — `docs/RMT_T13_DISPOSITION.md` verdict moved to
  **ACCEPT + BOUND + CLOSED**; §3c rewritten from DEFER to the implemented fix.

**Behaviour:** no edges recorded → the guard escalates nothing today. It is
**live**: add any edge to either source (`"web": ["db"]`) and `start db`
escalates to human approval automatically. The CAP-04 §3b envelope guard test
stays as defence in depth.

**Validation:** 20 agent focused (13 + 7) + 122 Core (unchanged) + 38 Homelab
(unchanged) + **197 full**, all passed. No `app/core/**` change; diff confined
to `app/agent/**`, `app/homelab/dependencies.py`. Not yet deployed to live (new
files; a redeploy would pick them up, agent still OFF).

### CAP-05 (5B) — LLM-backed agent adapter (2026-09-07)

**Owner:** approved the scope (`docs/RMT_CAP_05B_PROPOSAL.md`). Above-Core; no
`app/core/**` change; disabled by default (`RMT_AGENT_LLM_ENABLED`).

- **New** `app/agent/llm_client.py` — stdlib `urllib` Ollama client (the
  `experiments/mcr3/atlas.py` pattern; no new dependency).
- **New** `app/agent/llm_agent.py` — `LlmAgent.propose(goal, observations,
  grant_id)`. Strict single-JSON parse + **fail-closed** validation: `target` ∈
  known homelab components, `mechanism` ∈ `ActionType`, `confidence` int 0-100;
  anything else → `LlmProposalError` with reason `no_proposal` /
  `invalid_proposal` / `llm_parse_error` / `llm_error`. Never a partial/guessed
  proposal. `agent_id="llm-agent"`.
- **Modified** `app/agent/loop_config.py` — `AGENT_LLM_ENABLED` (False),
  `AGENT_LLM_MODEL` (`deepseek-v4-flash:cloud`), host/timeout/tokens/temp.
- **Modified** `app/agent/api.py` — `POST /agent/act/llm` {goal, grant_id};
  disabled → `llm_disabled` (no model call); valid proposal →
  `propose_and_govern(...)` (the 5A path, unchanged). `GET /agent/status` gains
  a read-only `llm` block.
- **New** `app/agent/testing/test_llm_agent.py` — 17 cases (model always mocked).

**The LLM only proposes.** No execution, no tool calls, no authority, no
continuation. Every LLM proposal still runs 5A: authority (scoped/single-use) →
T13 escalation → governance → **human approval**. Layered defence: structural
attacks rejected by the allow-list validation before an `ActionRequest` exists;
a structurally-valid but semantically-wrong proposal (the prompt-injection
shape) is caught by human approval — tested.

**Out of scope (per the proposal):** no autonomous LLM loop (one goal → at most
one proposal); no lowering of `AGENT_DEFAULT_REQUIRES_APPROVAL`; not wired into
the CAP-04 loop; not enabled on live.

**Validation:** 17 focused + agent suite **37** (20 + 17) + Core **122**
(unchanged) + Homelab **38** (unchanged) + full app **214** (197 + 17). `import
app.main` clean; both agent flags OFF by default.

**Not deployed to live** — new files; a redeploy would pick them up, both the
5A surface and 5B still OFF.

### Next candidates (owner to select)
> **Full scoped menu: `docs/RMT_ABOVE_CORE_ROADMAP.md`** (2026-09-07) — fit
> profile + Tier 0 operational-readiness, Tier 1 homelab depth, Tier 2 new
> domains on the frozen Core, Tier 3 platform surface, and the E3 Core-change
> candidate; each item scoped Objective / Boundary / DoD. The bullets below are
> the original shortlist, now folded into that document.
- ~~Enable 5A and/or 5B on the live server + a controlled LLM exercise.~~
  **DONE 2026-09-07** — see the session note below.
- Populate real `HOMELAB_DEPENDENCIES` edges if/when any exist (activates T13
  for real).
- Frontend governed-evidence view; engineering-intelligence expansion.
- Notifications for held remediations / proposals (currently only visible via
  `GET /homelab/loop/status` and the approval list).
- **New (from the 5B live exercise):** decide whether `continue_remediation`
  (`/homelab/approve`) should run the above-Core Docker verify + executed-Learn
  closure for any component with a `ComponentContext`, not only for
  `REMEDIATION_POLICY` components (today: `uptime-kuma` only). Scoped-by-design
  today; recorded as a finding, not a defect.

---

## Session note — CAP-05 (5A + 5B) enabled on the live server + controlled LLM exercise

**Date:** 2026-09-07. Owner selected candidate 1 ("enable 5A / 5B on live + a
controlled LLM exercise"); chose "both 5A + 5B on live now" and exercise target
`dozzle`. Above-Core; **no code change** — systemd enablement + an operational
exercise + docs only. C01–C07 remain closed/frozen; no C08.

### Enablement (live :8000)
- New drop-in `/etc/systemd/system/rmt-control-center.service.d/cap05-agent.conf`:
  `Environment=RMT_AGENT_ENABLED=true` + `Environment=RMT_AGENT_LLM_ENABLED=true`.
  `sudo systemctl daemon-reload && sudo systemctl restart` (owner ran it; no
  non-interactive sudo in this shell).
- `GET /agent/status` on live → `enabled: true`, `llm.enabled: true`
  (`deepseek-v4-flash:cloud` @ `127.0.0.1:11434`), `active_grants: 0`,
  `dependency_escalation: true` (no edges → no-op).
- The agent surface has **no background task** — request-driven only; inert
  until an operator issues a grant *and* approves the resulting hold.
- CAP-04 loop unaffected (still enabled; `no_remediation`; not quarantined).
- Disable = delete `cap05-agent.conf` + `daemon-reload` + `restart`.

### Controlled LLM exercise — live :8000, target `dozzle`
`dozzle` is **not** in the CAP-04 `REMEDIATION_POLICY` (`["uptime-kuma"]`), so
the loop neither reacts nor needs pausing. `portainer` / `uptime-kuma` untouched
throughout.

1. `POST /agent/act/llm` **no grant** → `no_authority` / `no_grant`. The LLM
   produced a valid `dozzle` proposal; blocked before the governed boundary.
2. `POST /agent/act/llm`, healthy state + "only act if something is broken"
   goal → `no_proposal` — fail-closed; the model declined.
3. Governed fault-injection `POST /execute?operation=stop&target=dozzle` →
   execution `24b5d25f…` → `dozzle` `exited`.
4. `POST /agent/authority/grant` {`restart`, `dozzle`,
   `cap05-llm-exercise-operator`} → grant `0720df95…`. `POST /agent/act/llm`
   with it → `no_authority` / **`grant_scope_mismatch`**: the model proposed
   `start` (stopped container), not `restart`. Model mechanism choice is
   nondeterministic call-to-call; the grant is operation-scoped and held.
5. `POST /agent/authority/grant` {`start`, `dozzle`, …} → grant `6c596894…`.
   `POST /agent/act/llm` → **`decision: hold`**,
   `governed_status: manual_approval_required`, `approval_id c7b3e598…`,
   `escalated: false`, `learn_recorded: true`, `agent_id: llm-agent`,
   `mechanism: start`, `confidence: 95`. No execution.
6. `POST /agent/act/llm` **replay the same grant** → `no_authority` /
   **`grant_consumed`** (single-use enforced).
7. `POST /homelab/approve?approval_id=c7b3e598…&approved_by=cap05-llm-exercise-operator`
   → **`executed`** via the `docker` adapter: execution `37ab18bf…`, action
   `becbf4d0…`, "start on dozzle" success. Core verifier
   `observation_unavailable` (fail-safe).
8. `dozzle` `running` (restarted 11:26:29). Stray `restart` grant `0720df95…`
   self-expired at its TTL → `active_grants: 0`. CAP-04 loop `no_remediation`.

### Evidence bundle
Correlated by action `becbf4d0-32a2-4f0b-b4ff-29356940071f` / execution
`37ab18bf-4aa5-4174-a07c-6cfcb6fc5cd8` / approval
`c7b3e598-88e8-4d20-9b51-ed382395c8b4`:

- **authorization** `33eed7bb…` — type `manual`,
  `authorized_by cap05-llm-exercise-operator`,
  **`decision_id = agent-llm-agent-3c15347d`** (proves LLM-agent-surface
  origin), single-use, 5-min TTL, status `approved`.
- **trace** `455c8db4…` — policy `allow`, risk `low`, outcome `completed`.
- **audit** — adapter `docker`, `completed`, risk `low`.
- **verification** `94235f26…` — `observation_unavailable` (Core fail-safe).
- **approval_record** `c7b3e598…` — `decision approved`,
  `approved_by cap05-llm-exercise-operator`. (The **hold** store reads
  `pending` on disk — the known frozen-Core hold-persistence note; the record
  store is authoritative.)
- **Learn** (`intelligence_memory` id 336) — `dozzle / remediation`
  `manual_approval_required`, `approval_id c7b3e598…`, `confidence 95` — the
  held-state record, written by the agent adapter.

### Finding — recorded, not a defect
The above-Core CAP-03 Learn-closure (executed-outcome Learn record + above-Core
Docker-observer **`verified_success`** verification) **did not run** for this
exercise: `continue_remediation` (`/homelab/approve`) early-returns for any
component `not in REMEDIATION_POLICY`, and that policy holds only `uptime-kuma`
(the CAP-04 safe envelope). So an agent proposal approved via `/homelab/approve`
gets the full above-Core Learn/verify closure **only when its target is in
`REMEDIATION_POLICY`** — it did for `uptime-kuma` (the 5A exercise, same day,
`verified_success`); it was skipped for `dozzle`. The governed Core lifecycle,
durable evidence, scoped/single-use authority, and the held-state Learn record
all ran correctly. Owner consideration: widen the `continue_remediation`
attribution beyond `REMEDIATION_POLICY` (e.g. any component with a
`ComponentContext`), or accept it as scoped-by-design.

### Result
**PASS.** On the live server with both agent flags enabled:
`deepseek-v4-flash:cloud` → structured `AgentProposal` → scoped single-use
authority → T13 (no-op) → governance → **human approval** → governed `docker`
execution → Core verification → correlated durable evidence. Structural
allow-list validation, grant scope, single-use, and capability ≠ authority all
enforced against the live LLM path. No `portainer` / `uptime-kuma` impact;
systemd service and CAP-04 loop unaffected. No code changed; C01–C07 frozen.

---

## Session note — Production-readiness gap matrix + P0 batch (S1/S2-lite/E1/O2)

**Date:** 2026-09-07. Above-Core / operational. C01–C07 remain closed/frozen;
no C08. **One frozen-Core file touched (E1)** — owner-authorized,
behaviour-preserving.

### Assessment
- New `docs/RMT_PRODUCTION_READINESS.md` — operational gap matrix (37 criteria,
  7 groups). Blocking set (P0): S1 auth, S2 identity, S4 transport, E1 atomic
  evidence writes, E2 hold persistence, O2 held-action alerting.
- Owner decisions: threat model **(b) trusted LAN, few operators**; work the P0
  set together; authorize the E1 frozen-Core hardening; S4 = reverse proxy +
  loopback bind; agent read-only routes behind auth; keep an
  `RMT_AUTH_ENABLED=false` local-dev escape hatch.
- Proposal `docs/RMT_PROD_P0_PROPOSAL.md` — APPROVED, then implemented (see its
  §10 for the file-level record).

### Implemented (code-complete, merged)
- **S1 + S2-lite** — new `app/ops/{ops_config,auth,notifications}.py`.
  `require_operator` (bearer / `X-API-Key` → `RMT_OPERATOR_TOKENS` = `name:token`
  pairs) on all 10 `@app.post` routes + the `/agent/*` router. App refuses to
  start with auth on and no tokens. `/approve`, `/homelab/approve`,
  `/agent/authority/grant` now take the identity from the authenticated
  operator (body `approved_by`/`granted_by` ignored); `/execute` threads the
  operator name into `decision_id`/`reason`. Evidence `authorized_by` /
  `approved_by` is now trustworthy.
- **E1** — `app/core/intelligence/durable_store.py::_persist` writes `*.tmp` →
  `flush`/`os.fsync` → `os.replace` (atomic); `_load` discards stale `*.tmp`.
  Byte-identical committed output, no API/behaviour change.
- **O2** — `notify_held` (stdlib `urllib` webhook, fail-open, per-hold de-dupe;
  logs only when `RMT_NOTIFY_WEBHOOK_URL` unset) hooked at `/execute`,
  `/homelab/remediate`, the CAP-04 loop, and the agent adapter.
- **D1** — `requirements.txt` pinned; `requirements.lock.txt` (33-pkg freeze).
- **D2 / D5** — `docs/operations/DEPLOY.md`, `docs/operations/CONFIG.md`.
- **S4 artifacts** — `deploy/Caddyfile`, `deploy/systemd/bind-loopback.conf`,
  `deploy/systemd/auth.conf.example`. **Live cutover is an operator step.**
- `conftest.py` (backend root) defaults the suite to `RMT_AUTH_ENABLED=false`;
  `app/ops/testing/test_auth.py` opts back in.

### Validation
Full suite **254 passed** (214 + 40 new: 25 auth incl. per-route 401/accept, 4
notifications, 4 atomic-store, + auth unit). Core intelligence **126** (122
unchanged + 4). `import app.main` clean. Commit **`c4f63a3`**.

### Deployed to live 2026-09-07 12:36 UTC
Owner ran the `DEPLOY.md` §1 steps. Drop-ins installed:
`/etc/systemd/system/rmt-control-center.service.d/auth.conf` (mode 0600, two
operator tokens `ragb` / `ops2`) and `bind-loopback.conf`. `daemon-reload` +
`restart`; service `active` on the new code.

**Verified on live :8000:**
- `POST /homelab/loop/stop` no token → **401**; with `Authorization: Bearer
  <token>` → **200**; `GET /` → 200 (open routes unaffected).
- `POST /agent/authority/grant` with body `granted_by:"IGNORED"` → recorded
  **`granted_by:"ragb"`** (authenticated operator; body value ignored) — S2-lite.
- App listens **`127.0.0.1:8000` only**; `192.168.223.128:8000` refused — S4
  loopback bind live.
- 6 governance-evidence files parse, **no `.tmp` residue** — E1.
- CAP-04 loop + agent 5A/5B still enabled and healthy on the new code.

Token values are **not in the repo** — `sudo cat
/etc/systemd/system/rmt-control-center.service.d/auth.conf`. Monitoring /
exercise calls now need a token header.

### Open / next (deferred to the next session)
- **S4 Caddy proxy — NOT installed.** RMT currently has **no LAN-facing entry
  point** (loopback + auth only). **Owner decision (2026-09-07): install Caddy.**
  Artifacts are cutover-ready (`deploy/Caddyfile` already targets the verified
  host IP `192.168.223.128`; `bind-loopback.conf` already live). Remaining:
  `sudo apt install caddy` (candidate `2.6.2`), copy the Caddyfile, `systemctl
  restart caddy`, `caddy trust` + import the CA on operator machines
  (`DEPLOY.md` §1.4). This is a root operator step — not yet run.
- **E2 — CLOSED (2026-09-07).** Owner chose **above-Core reconciliation on
  startup** over a Core fix. New `app/ops/reconcile.py`
  (`reconcile_holds_against_records`), called in the `app/main.py` lifespan
  after `register_default_adapters()`: a `pending` hold whose approval **record**
  is terminal (`approved`/`rejected`) is corrected in place and re-persisted via
  the store's atomic (E1) path. Read-only where consistent; fail-open; never
  invents a resolution. No `app/core/**` change. `app/ops/testing/
  test_reconcile.py` (9 tests); full suite **263 passed**; `import app.main`
  clean. Also covers the hold↔record half of **E6** (now PARTIAL). **Not yet
  deployed to live** — needs a `systemctl restart rmt-control-center.service`.
- **Optional:** hard-kill restart-safety test (E1 + E2 are unit-tested); re-run
  the CAP-05 LLM exercise under auth against `dozzle` to confirm the agent path
  end-to-end with tokens.
- Stray live grant `f34f62cfc626` (restart/uptime-kuma, `ragb`) from the S2-lite
  verification — single-use, 5-min TTL, self-expires; no action.
- Then P1: S3 enforcement, E3/E4/E5, D3, O1/O3, V1/V2, R1/R3.

---

## Session note — E2 close-out (above-Core startup reconciliation) + S4 decision

**Date:** 2026-09-07. Above-Core / operational. C01–C07 remain closed/frozen;
no C08. **No `app/core/**` file touched.**

### Owner decisions
- **E2** → **above-Core reconciliation on startup** (not the Core fix).
- **S4** → **install the Caddy TLS reverse proxy** (cutover still pending — a
  root operator step).

### E2 — implemented
- **New `app/ops/reconcile.py`** — `reconcile_holds_against_records()`:
  - Walks `approval_hold_storage.get_all()`. For a hold still `PENDING`, looks
    up `approval_record_storage.get_by_id(hold.approval_id)`; if the record's
    decision is terminal (`approved` / `rejected`) the record store is
    authoritative (Core updates it reliably on resolution), so the hold is
    corrected in place (`status`, and `approved_by` when unset) and the store is
    re-persisted **once** via `_persist()` (the store exposes no public
    `update()`; same atomic E1 write path `ApprovalRecordStorage.update` uses).
  - **Bounded:** acts only on a record-backed terminal contradiction. A hold
    with no record, or a still-`pending` record, is left exactly as-is — it
    never *invents* a resolution (e.g. does not reject merely-expired holds).
  - **Fail-open:** any error is logged (`rmt.ops.reconcile`) and swallowed;
    reconciliation never blocks startup.
  - Returns `{"checked", "reconciled", "ids"}` for testability.
- **`app/main.py`** — one call in the lifespan startup, right after
  `register_default_adapters()`, before the collector task.
- **New `app/ops/testing/test_reconcile.py`** — 9 tests: stale→approved and
  stale→rejected (in-memory **and** reload-from-disk), no-record untouched,
  non-terminal record untouched, already-resolved not recounted, existing
  `approved_by` preserved, mixed batch (only the stale one corrected),
  no disk write when nothing is stale, fail-open on a storage error.
- Mirrors CAP-04's existing read-side compensation
  (`operational_loop._hold_is_still_actionable`) — same record-store-authoritative
  rule, applied write-side once at boot. Also closes the hold↔record half of
  **E6** (authorization-store cross-check still open → E6 now PARTIAL, P2).

### Validation
- Full suite **263 passed** (254 + 9), `272s` (the long tail is the
  operational-loop cadence tests' real sleeps, not new work). `import app.main`
  clean. 122 frozen-Core intelligence tests unchanged.

### Not done here
- **Live deploy of E2** — needs `sudo systemctl restart
  rmt-control-center.service` on the new code. Reconciliation is a no-op on a
  clean store, so the restart is safe; it will log a `WARNING` + corrected count
  only if a stale hold is actually found.
- **S4 Caddy install** — root/LAN-facing operator step (`DEPLOY.md` §1.4). Host
  LAN IP verified as `192.168.223.128` (already in `deploy/Caddyfile`); apt
  candidate `caddy 2.6.2-6ubuntu0.24.04.3`.

### Files changed
- `projects/homelab-control-center/backend/app/ops/reconcile.py` (new)
- `projects/homelab-control-center/backend/app/ops/testing/test_reconcile.py` (new)
- `projects/homelab-control-center/backend/app/main.py` (import + 1 startup call)
- `docs/RMT_PRODUCTION_READINESS.md` (E2 → READY, E6 → PARTIAL, R1 evidence,
  status table, W2/§6/§7/§8, header blurb)
- `HANDOFF.md`, `RMT_CONTEXT.md` (state + next action)

---

## Session note — E2 committed + live; S4 Caddy proxy installed → P0 CLOSED

**Date:** 2026-09-08. Above-Core / operational. C01–C07 remain closed/frozen;
no C08. No `app/core/**` change.

### Commits
- **`b485365`** — `RMT-PROD P0 (E2): above-Core startup reconciliation of the
  approval hold store` (`app/ops/reconcile.py`, `test_reconcile.py`,
  `app/main.py`).
- **`05bab80`** — `docs: E2 closed above-Core; add above-Core opportunity
  roadmap` (`RMT_PRODUCTION_READINESS.md`, new `RMT_ABOVE_CORE_ROADMAP.md`,
  `HANDOFF.md`, `RMT_CONTEXT.md`).

### E2 — confirmed live
The prior session left E2 "not deployed". Investigation this session: the host
**rebooted 2026-09-08 08:47 UTC** (`who -b`); systemd auto-started
`rmt-control-center.service` (PID 1257) from the working tree, which already
carried the then-uncommitted `reconcile.py` + `main.py` call. The startup
reconcile ran. On-disk proof in `app/core/intelligence/actions/approval_holds.json`:
`316257fc` now `approved` (was stale `pending`), `79d6383a` now `rejected` (was
stale `pending`), and the genuinely-unresolved `54f685f6` (record decision
`manual_required`, non-terminal) correctly **left `pending`**. Re-running
`reconcile_holds_against_records()` against the live store now returns
`{"checked": 7, "reconciled": 0}` — idempotent no-op. No `*.json.tmp` residue
(E1 clean). Could not read the boot-time `WARNING` log line (`journalctl`
needs sudo; this shell has no passwordless sudo).

### S4 — Caddy TLS reverse proxy installed (owner ran the sudo steps)
- `caddy 2.6.2` installed + `systemctl enable --now caddy`; `/etc/caddy/Caddyfile`
  copied from `projects/homelab-control-center/deploy/Caddyfile` (unchanged —
  site line `rmt.homelab.lan, 192.168.223.128`, `tls internal`,
  `reverse_proxy 127.0.0.1:8000`, JSON access log to `/var/log/caddy/`).
- `caddy trust` succeeded on the host — the internal root CA is in the host
  trust store.
- **Verified on `192.168.223.128`:**
  - app `:8000` off-loopback → connection refused (bind-loopback holds).
  - `https://` → **200, CA-validated** (no `-k` needed on the host).
  - `http://` → **308** auto-redirect to `https://`.
  - `POST /homelab/loop/stop` no token → **401**; open `GET /homelab/loop/status`
    → **200**; `GET /agent/status` no token → **401** (agent routes auth-gated,
    intended).
  - CAP-04 loop healthy through the proxy (`enabled/running`, `no_remediation`,
    no cycle error).
- **Remaining housekeeping only:** import the Caddy root CA
  (`/var/lib/caddy/.local/share/caddy/pki/authorities/local/root.crt`) on other
  operator workstations. `rmt.homelab.lan` does not resolve on the host — with
  `tls internal` that is harmless (local cert issuance needs no DNS); trim the
  site line to just the IP if a clean config is wanted.

### Why S4 lagged (recorded)
The owner authorized the Caddy install on 2026-09-07, but it needs root
(`apt install`) and this shell has no passwordless sudo, so every session logged
it as "a root operator step — not yet run" and handed it forward. The other P0
sudo steps landed because the owner ran them directly from `DEPLOY.md` §1;
§1.4 (Caddy) was the one sub-step that got skipped. Closed this session once the
owner ran the install.

### P0 — FULLY CLOSED (2026-09-08)
S1, S2-lite, E1, **E2**, O2, **S4** — all live and verified.

### Docs updated this session
- `docs/RMT_PRODUCTION_READINESS.md` — S4 → READY, P0 rollup → closed, header
  blurb, §7 step 2, §8 verdict + remaining section.
- `docs/operations/DEPLOY.md` §5 — E2/S4 marked closed; added the operator-CA
  follow-up.
- `RMT_CONTEXT.md` §12 — E2 live, S4 closed, P0 fully closed, next = P1.
- `HANDOFF.md` — this note.

### Next
**P1** (none blocking on its own): S3 approver≠grantor enforcement (behind
`RMT_AUTH_SEPARATION`), **E3** (failed-execution verification evidence — the
lone remaining item that would touch frozen Core; needs its own owner decision:
Core fix vs above-Core wrapper), E4 retention/rotation, E5 RMT-store backup,
D3 systemd sandboxing, O1/O3, V1/V2, R1 (hard-kill restart test) / R3 (platform
recovery runbook). Also open: extend the E6 startup reconciliation to the
authorization store; S5 CORS to config (stale `192.168.235.128` in `main.py`).

---

## Session note — R1 hard-kill restart-safety test PASSED

**Date:** 2026-09-08. Verification only — no code change. Owner ran the root
`systemctl kill` / `restart`; assistant captured pre/post state.

### Method
Pre-kill snapshot (09:42 UTC): sha256 + record count of the six durable
governance-evidence stores, `.tmp` scan, loop status. Then
`sudo systemctl kill -s KILL rmt-control-center.service` (SIGKILL to the whole
cgroup — no graceful shutdown), then `sudo systemctl restart`. Post-restart
(09:44): new PID 6653 (`NRestarts=1`, up 09:42:46), re-checked everything.

### Result — PASS
- **All six evidence stores byte-for-byte identical** on reload (same sha256,
  same counts): `approval_holds` (n=7), `approval_records` (n=19),
  `authorizations` (n=18), `audit` (n=17), `traces` (n=17), `verifications`
  (n=13). No corruption / truncation / partial write. → **E1 proven
  empirically** against the live stores.
- **No `.tmp` residue** before or after.
- **hold ↔ record stores in agreement**; `reconcile_holds_against_records()`
  re-run = `{"checked": 7, "reconciled": 0}` (clean no-op). → **E2 confirmed**.
- CAP-04 loop restarted clean, idle at `no_remediation`, no cycle error
  (`cycle_count` resets on restart — in-memory + stateless by design; the
  persistent per-component flap/quarantine state is what matters and it's
  healthy).
- Auth intact (`/agent/status` no token → 401); Caddy proxy intact
  (`https://192.168.223.128/homelab/loop/status` → 200).

### Not captured
The E2 reconcile journal line for this boot — `journalctl` needs sudo and this
shell has no passwordless sudo. On-disk byte-identity is the stronger proof;
`sudo journalctl -u rmt-control-center.service -b | grep -i reconcile` if the
log line is wanted for the record.

### Effect on the matrix
R1: the hard-kill-restart-test clause is satisfied. R1 stays **PARTIAL** only
because the **E6** authorization-store cross-check is still open (extend
`app/ops/reconcile.py` to the authorization store). §7 step 3 re-verify list
updated (full suite 263 + restart test both done, 2026-09-08).

### Next (P1, all above-Core — owner: no Core modification / fix)
E3 as an **above-Core wrapper only** (emit a distinguishable `adapter_failure` /
`state_mismatch` evidence record when `result.success` is False — same layer as
`verify_docker_execution`; no `app/core/**` touch) **or** accept-and-record.
Then S3 approver≠grantor enforcement, E4 retention/rotation, E5 RMT-store
backup, E6 authorization cross-check (closes R1), D3 systemd sandboxing,
O1/O3, V1/V2, R3 platform-recovery runbook.

---

## Session note — E6 authorization-store integrity audit (closes E6 + R1)

**Date:** 2026-09-08. Above-Core / operational. No `app/core/**` change. Owner
directive in force: **no Core modification or fix.**

### The gap
E2 (`reconcile.py`) reconciled the hold ↔ record stores on startup but not the
**authorization** store — E6 stayed PARTIAL and kept R1 at PARTIAL.

### Design finding
The execution-authorization store is **Core-owned and effectively append-only**:
`create_manual_authorization` / `create_execution_authorization` mint an
`ExecutionAuthorization` already in its final `approved` status, and the Core
never mutates it afterwards (the execution engine only *reads* it to gate the
boundary). There is **no authoritative "true status"** to reconcile an
authorization *to* — so E6 for authorizations is a **read-only integrity audit
(log/flag)**, not a correction. That also matches the E6 required-action
wording ("log/flag divergences").

### Implemented — `app/ops/reconcile.py`
- **New `audit_authorizations()`** — walks `execution_authorization_storage`;
  for each authz with an `approval_id`, cross-checks the approval **record** and
  **hold** stores and logs (`WARNING`) any inconsistency:
  - `missing_record` — authz references an approval id with no record (orphan);
  - `contradicts_rejection` — authz exists but its record is `rejected`
    (should be impossible: rejection mints no authorization);
  - `record_not_terminal` — authz exists but its approval was never finally
    decided (`pending` / `manual_required`);
  - `hold_still_pending` — the linked hold is still `pending` after E2 ran.
  Returns `{"checked", "divergences", "details":[…]}`. **Never writes**, never
  raises (fail-open).
- **New `reconcile_governance_stores()`** — runs `reconcile_holds_against_records`
  (E2) first, then `audit_authorizations` (E6) against the now-corrected holds.
- **`app/main.py`** — startup lifespan call changed
  `reconcile_holds_against_records()` → `reconcile_governance_stores()`; comment
  updated.
- **`app/ops/testing/test_reconcile.py`** — +9 E6 tests (all-consistent,
  each of the four divergence classes, unlinked authz skipped, read-only
  (`_persist` never called), fail-open, and an E2→E6 ordering test proving the
  hold is corrected before the audit so it isn't falsely flagged). File now
  **18 tests** (9 E2 + 9 E6).

### Verified against the live stores
`reconcile_governance_stores()`: holds `{checked 7, reconciled 0}` (clean);
authorizations `{checked 18, divergences 1}` — one real historical orphan
(`14be2cb0`, approval `3df558e8`, a 2026-09-02 `test-container` authz with no
record), logged at `WARNING`. `authorizations.json` **byte-identical**
afterward (read-only confirmed).

### Validation
`test_reconcile.py` 18 passed; ops + Core-intelligence 180 passed; **full app
suite 272 passed** (263 + 9). `import app.main` clean. 122 frozen-Core
intelligence tests unchanged.

### Matrix effect
- **E6 → READY** (P2 line: "D5, E6 done").
- **R1 → READY** — E1 + E2 + E6 all closed, hard-kill restart test passed
  → a restart is provably faithful. P1 list drops R1.
- **E3** reframed to **above-Core wrapper only** (no Core-fix option) per the
  owner directive; §6 out-of-scope updated — no matrix item now touches Core.

### Not deployed to live
New/changed code (`reconcile.py`, `main.py`) — a `sudo systemctl restart
rmt-control-center.service` picks it up. Safe: the E6 audit is read-only and the
E2 half is a no-op on the current clean store (it will log the one orphan
`WARNING`).

### Next (P1, all above-Core)
E3 (above-Core execution-result wrapper: emit a distinguishable
`adapter_failure` / `state_mismatch` evidence record when `result.success` is
False — same layer as `verify_docker_execution`), S3 approver≠grantor
enforcement, E4 retention/rotation, E5 RMT-store backup, D3 systemd sandboxing,
O1/O3, V1/V2, R3 platform-recovery runbook.

---

## Session note — E3 above-Core execution-result wrapper (distinguishable adapter-failure evidence)

**Date:** 2026-09-08. Above-Core / operational. **No `app/core/**` change** (owner
directive: no Core modification or fix).

### The gap
`AGENTS.md` §11 requires five post-execution outcomes to be *distinguishable in
evidence*: blocked-before-execution / **adapter invoked and failed** /
successful execution / verification failure / unknown-or-unavailable state. When
a governed execution reached the adapter and it returned `success=False`, the
Core wrote an **audit** + **trace** record (both `status="failed"`) but **no
verification record** — every caller gates `verify_execution` /
`verify_docker_execution` on `result.success`. `verification_failure` already
means "the verifier itself failed", so adapter failure was not distinguishable
*in the verification store*.

Path-by-path (some were already covered above-Core):
- `/homelab/remediate`, `/homelab/approve` (uptime-kuma) — already wrote
  `state_mismatch` / `observation_unavailable` (no success gate in
  `remediation.py` / `continuation.py`).
- `/execute`, `/approve` (Core paths), `/agent/act*`, `/homelab/approve` for a
  non-`REMEDIATION_POLICY` component — **no record**.

### Implemented
- **New `app/ops/execution_evidence.py`** — `record_failed_execution_evidence(
  outcome, *, expected=None, source)`:
  - Fires only for a real failed execution attempt: `outcome["status"] ==
    "executed"` **and** `success is False` **and** `execution_id` present.
    Blocked-before-adapter outcomes (`manual_approval_required`,
    `policy_denied`, `no_authority`, `authorization_not_created`, `rejected`,
    `no_remediation`, `unsupported_operation`, `error`) are left alone.
  - Writes one `VerificationResult` to the **existing** `verification_storage`
    with status **`adapter_execution_failed`** (distinct from the four frozen
    `VerificationStatus` values), correlated by `execution_id`, `reason` from
    the adapter message.
  - **Idempotent** — skips if `verification_storage.get_by_execution_id(...)`
    already has a record (so paths already covered above-Core aren't
    double-written).
  - **Fail-open** — never raises.
- **New `app/ops/testing/test_execution_evidence.py`** — 19 tests (records the
  failure case; carries `expected` through; idempotent; success not recorded;
  every blocked-before-execution status left alone; no execution_id;
  non-dict/None safe; reason fallback chain; fail-open on store error).
- **`app/main.py`** — `record_failed_execution_evidence(...)` called before the
  return of `/execute` (with `action.expected_outcome`), `/approve`,
  `/homelab/remediate`, `/homelab/approve`. Import added.
- **`app/agent/adapter.py`** — the `if status == "executed":` branch gained an
  `elif not result.get("success"):` that calls the helper
  (`source="agent_adapter"`) and sets `outcome.verification_status =
  "adapter_execution_failed"`. Import added.
- **`app/agent/testing/test_agent_governance.py`** — `captured_governed`
  fixture now also mocks `record_failed_execution_evidence`; new
  `test_failed_execution_records_e3_evidence` drives `propose_and_govern` with a
  failed governed result and asserts the E3 evidence call + status, no Docker
  verify, grant still consumed, still learned.

### Validation
`test_execution_evidence.py` 19 passed; agent governance + E3 helper 33 passed;
ops + agent + homelab 148 passed; **full app suite 292 passed** (272 + 20).
`import app.main` clean. 122 frozen-Core intelligence tests unchanged.

### Matrix effect
**E3 → READY.** All five `AGENTS.md` §11 outcomes are now distinguishable in
evidence. P1 list drops E3 (D1, D2, R1, E3 done). No matrix item touches the
frozen Core.

### Not deployed to live
New/changed code (`execution_evidence.py`, `main.py`, `agent/adapter.py`) —
needs `sudo systemctl restart rmt-control-center.service`. Safe: the helper only
*adds* a record on an adapter failure that otherwise had none, is idempotent,
and is fail-open. No live exercise run this session (would write real evidence);
a controlled one: `POST /execute?operation=restart&target=<bogus>` under auth →
expect a `verifications.json` entry `status=adapter_execution_failed` correlated
by `execution_id`, plus the existing `status=failed` audit + trace.

### Next (P1, all above-Core)
S3 approver≠grantor enforcement (behind `RMT_AUTH_SEPARATION`), E4
retention/rotation, E5 RMT-store backup, D3 systemd sandboxing, O1/O3, V1/V2,
R3 platform-recovery runbook.

---

## Session note — test-isolation fix: `test_auth.py` was polluting the Core evidence stores

**Date:** 2026-09-08. Follow-up to the E3 commit. No behaviour change; test
hygiene + a one-off cleanup script.

### What surfaced
After the E3 restart, `verifications.json` on live showed 2
`adapter_execution_failed` records for target `x` ("No such container: x"),
timestamped **before** the restart. Root cause: `app/ops/testing/test_auth.py`
had **no store isolation**. Its "accepts valid token" cases
(`test_mutating_route_accepts_valid_token`, `test_apikey_header_accepted`) POST
`/execute?target=x` / `/homelab/remediate?component=x` with a real token, which
reached the **real** governed pipeline → the **real** Docker adapter (reachable
on this host) → 404 → a `failed` **trace** + **audit** record written to the
real JSON stores. The new E3 hook then also wrote an `adapter_execution_failed`
**verification** record. This has been happening since `test_auth.py` was added
in the P0 batch (2026-09-07) — **10** polluted `target: x` executions had
accumulated in `traces.json` and `audit.json` (each), 2 in `verifications.json`.

### Fix (committed)
- **`app/ops/testing/test_auth.py`** — new `isolate_stores` fixture (a
  dependency of `client`): swaps the six durable evidence stores + the E3
  `verification_storage` ref + the execution adapter registry to in-memory
  instances, mirroring `test_http_entrypoints.py::_isolate_evidence_stores`.
  Verified: a full `test_auth.py` run and a full app-suite run now leave
  `traces.json` / `audit.json` / `verifications.json` **byte-count unchanged**.
  32 auth tests pass; full app suite **292 passed**.
- **`scripts/clean_test_pollution.py`** (new, one-off) — removes every record
  whose reason/message contains `No such container: x` from the three stores.
  Dry run: `traces 21→11, audit 21→11, verifications 15→13` (22 records).

### Cleanup — owner step (NOT done)
The live service (PID 9181, started 10:39) holds these stores in memory
*including* the polluted records, so a hand-edit would be re-persisted on its
next `save()`. Run with the service stopped:

    sudo systemctl stop rmt-control-center.service
    cd /home/rmt-lab/homelab/projects/homelab-control-center/backend
    .venv/bin/python scripts/clean_test_pollution.py            # dry run
    .venv/bin/python scripts/clean_test_pollution.py --apply
    sudo systemctl start rmt-control-center.service

Purely cosmetic (bogus `target: x`, `status: failed`) — not corruption, not a
governance defect. Safe to defer to any restart window.

### Not affected
E1/E2/E6/R1 evidence and conclusions stand — the pollution is `failed`
trace/audit noise for a non-existent target, not a consistency problem. The R1
byte-identical-restart result is unaffected (it tested identity across a
restart, which held).

---

## Session note — S3 separation of duties (approver ≠ grantor for agent holds)

**Date:** 2026-09-08. Above-Core / operational. No `app/core/**` change.
Config-gated by **`RMT_AUTH_SEPARATION`** (default **off**).

### The gap
S2-lite made the granting / approving identity *recorded* (from the
authenticated operator). S3 *enforces*: for a manual-approval hold that an
**agent proposal** raised, the operator who continues it (`/approve` or
`/homelab/approve`) must not be the operator who granted the agent's authority
for it. The Core hold carries no link back to the agent grant.

### Implemented
- **New `app/ops/separation.py`**:
  - In-memory provenance map `approval_id → HoldProvenance{grant_id,
    granted_by, agent_id, recorded_at}` (like `authority_store`; entries older
    than `PROVENANCE_MAX_AGE_SECONDS = 3600` are ignored + pruned).
  - `record_hold_provenance(...)` — fail-**open** (bookkeeping).
  - `check_separation(approval_id, approver) -> (ok, reason)`:
    `separation_disabled` (toggle off) · `not_agent_originated` (no provenance)
    · `ok` · `approver_is_grantor` (deny) · `approver_is_proposer` (deny,
    approver == agent id) · `separation_check_error` (deny — fails **closed**;
    `RMT_AUTH_SEPARATION=false` is the escape hatch).
- **`app/ops/ops_config.py`** — `separation_enabled()` reads
  `RMT_AUTH_SEPARATION` (default False), dynamic.
- **`app/agent/adapter.py`** — on `manual_approval_required`, records the
  provenance (grant looked up via `authority_store.get(grant_id)` for
  `granted_by`) before the Learn record.
- **`app/main.py`** — `/approve` and `/homelab/approve` call
  `check_separation(approval_id, operator.name)` before continuing; a deny →
  `HTTPException(403, "separation of duties: <reason>")`.
- **`app/agent/api.py`** — `GET /agent/status` gains `separation_of_duties`.
- **Tests** — `app/ops/testing/test_separation.py` (14: record/get roundtrip,
  empty id, expiry + prune, disabled default, grantor blocked, other operator
  allowed, agent-id blocked, non-agent pass-through, fail-closed, and
  `/approve` + `/homelab/approve` 403 + non-grantor allowed). Agent-governance
  held test now also asserts provenance was recorded. `test_agent_governance.py`
  / `test_llm_agent.py` `_reset` fixtures also `separation.reset()`.

### Validation
`test_separation.py` + `test_agent_governance.py` 28 passed; **full app suite
306 passed** (292 + 14). `import app.main` clean. 122 frozen-Core intelligence
tests unchanged. Evidence stores unpolluted (11/11/13).

### Operational note
With a **single** operator, enabling `RMT_AUTH_SEPARATION` means agent-raised
holds can't be self-approved — you need a second operator identity. That's why
it's opt-in and off by default. Non-agent (`/execute`) holds are never affected.

### Matrix effect
**S3 → READY.** P1 drops S3 (D1, D2, R1, E3, S3 done). W1 access-control is
S1/S2-lite/S3 complete; S5/S7 remain (P2).

### Not deployed to live
New/changed code — needs `sudo systemctl restart rmt-control-center.service`.
The toggle stays **off** unless an operator adds
`Environment=RMT_AUTH_SEPARATION=true` to a drop-in.

### Unrelated
`docs/RMT_D4_PROPOSAL.md` (untracked) is a DRAFT above-Core capability proposal
(Financial/Approval Control) that depends on S3 — owner's to manage, not part
of this work.

### Next (P1, all above-Core)
E4 retention/rotation, E5 RMT-store backup, D3 systemd sandboxing, O1/O3
observability, V1/V2, R3 platform-recovery runbook.

---

## Session note — E4 evidence retention/archival + D4 proposal rev-2

**Date:** 2026-09-08. Above-Core / operational. No `app/core/**` change.

### D4 proposal rev-2 (`7dab721`)
Revised `docs/RMT_D4_PROPOSAL.md` after review: S3 (`b391293`) + E3 (`111b108`)
recorded DONE; new §3a scopes dual approval as an above-Core M-of-N layer
(Option D1); new §9 surfaces the **`ActionType`** blocker — the enum is closed
and `actions/policy.py` denies any type not in `ALLOWED_ACTION_TYPES`, so D4
needs either a 2-file behaviour-preserving Core deviation (Path A) or submit-as-
`create` + real type in parameters/`decision_id` (Path B, recommended). Sequencing
recommendation: **hold D4 until E4 + E5 close**.

### E4 — implemented (`app/ops/retention.py`)
`archive_aged_evidence()` — startup, after `reconcile_governance_stores()`:
each of the six evidence stores has records older than
`RMT_EVIDENCE_RETENTION_DAYS` (default 90; `<=0` disables) moved into an
append-only `<name>.archive.jsonl` beside it; the trimmed store is re-persisted
via the atomic (E1) path. Bounded (no/unparseable `created_at` → kept),
idempotent, fail-open per store and overall.
- `app/ops/ops_config.py` — `evidence_retention_days()`.
- `app/main.py` — one lifespan call after the reconcile; import added.
- `app/ops/testing/test_retention.py` — 10 tests.
- `docs/operations/CONFIG.md` — `RMT_EVIDENCE_RETENTION_DAYS` row.

### Validation
`test_retention.py` 10 passed; **full app suite 316 passed** (306 + 10). `import
app.main` clean. Against the live stores `archive_aged_evidence()` returns
`archived_total: 0` (oldest record 6 days old) — a safe no-op until records age
past 90 days.

### Not deployed to live
`retention.py` + `main.py` — needs a service restart. No-op on the current
stores; it will WARN + write archive files only once evidence ages past the
window.

### Next
**E5** — RMT evidence backup/restore (in progress this session).

---

## Session note — E5 RMT evidence backup / restore

**Date:** 2026-09-08. Above-Core / operational. Scripts + runbook; no app code.

### Delivered — `backend/scripts/`
- **`rmt-evidence-backup.sh`** — timestamped backup to
  `~/homelab/backups/rmt-evidence/<UTC>/`: the 6 JSON stores (`stores/`), their
  `*.archive.jsonl` (E4, `archives/`), a **`VACUUM INTO`** hot-safe
  `observability.db` snapshot, `manifest.txt` (git commit, host, per-store
  counts), `checksum.sha256`. Read-only against the live tree — safe while the
  service runs. `RMT_BACKUP_ROOT` overrides the destination.
- **`rmt_evidence_verify.py`** — **stdlib only** (runs on a bare host): every
  store parses as a list, every archive line parses, `observability.db` opens +
  `intelligence_memory` is queryable → exit 0; structural corruption → exit 1.
  Cross-store advisories (`authorization` with no record; stale `pending` hold)
  print `WARN`, never fatal. Works on a backup dir **or** a live backend tree.
- **`rmt-evidence-restore.sh <backup> [--force]`** — verify checksums → verify
  integrity → **refuse if `rmt-control-center.service` is active** (`--force`
  overrides) → move live files aside to `*.pre-restore.<ts>`, copy backup into
  place → re-verify the live tree.

### Runbook
`docs/operations/RMT_EVIDENCE_RECOVERY.md` — what's covered, backup + cron line,
verify semantics, restore procedure (service stopped), a restore-drill, and the
relationship to `RECOVERY_RUNBOOK.md` (Docker stack) and `DEPLOY.md` (service).
Pointer added from `docs/recovery/RECOVERY_RUNBOOK.md` (new "Scope" section).

### Exercised
backup → `sha256sum -c` (all OK) → `rmt_evidence_verify.py` (RESULT: OK) →
restore refusal while the service is up (exit 1) → restore abort on a tampered
checksum (exit 1). A full restore-into-a-stopped-copy drill is left as the
operator step noted in the runbook + the E5 matrix row.

### Matrix effect
**E5 → READY** (drill + cron line are the remaining operator tasks). P1 now:
D3, O1, O3, V1, V2, R3.

### Not deployed / operator tasks
Nothing to deploy (scripts). Operator: add the cron line; run one restore drill.

---

## Session note — O3 alerting (loop quarantine / cycle error / service-down)

**Date:** 2026-09-08. Above-Core / operational. No `app/core/**` change.

### Implemented
- **`app/ops/notifications.py`** — new `notify_ops(*, kind, detail, key,
  source)` over the same fail-open, de-duped, stdlib-`urllib` webhook sink as
  O2's `notify_held`. `kind` ∈ `loop_quarantine` | `loop_cycle_error`;
  `event: "ops_alert"`. De-dupe key `ops:<kind>:<key>` (per-component for
  quarantine, `run_cycle` for cycle errors) so a persistently-broken loop
  alerts ~once per `RMT_NOTIFY_MIN_INTERVAL_SECONDS`, not every 120s.
- **`app/homelab/operational_loop.py`** — `notify_ops` hooked in
  `_maybe_quarantine` (right after the `homelab_loop_quarantine` transition
  record) and in `run()`'s cycle-fault guard.
- **`app/main.py`** — new **unauthenticated** `GET /health`: `status`
  `ok`/`degraded` (degraded when `last_cycle_error` is set or any component
  quarantined) + a loop summary. Always HTTP 200 while the process answers —
  it's a liveness probe.
- **`backend/scripts/rmt-heartbeat.sh`** — cron inverted dead-man's switch:
  pings `RMT_HEARTBEAT_URL` only while `GET /health` returns 200. Service-down
  is inherently out-of-band (a dead process can't alert); the external monitor
  raises the alarm when the ping stops.

### Validation
`test_notifications.py` (+4 `notify_ops`), `test_health.py` (new, 3),
`test_operational_loop.py` (+1 cycle-error alert, +assert on quarantine alert)
— **29 passed** in that slice. Full app suite: see below. `import app.main`
clean.

### Matrix effect
**O3 → READY.** P1 now: D3, O1, V1, V2, R3. (O4 platform self-metrics is P2.)

### Operator tasks
- Set `RMT_NOTIFY_WEBHOOK_URL` in `auth.conf` (currently unset → O2 + O3 both
  log-only).
- Cron `rmt-heartbeat.sh` with a monitor URL (`CONFIG.md` → O3 section).

### Not deployed
`notifications.py` + `operational_loop.py` + `main.py` — needs a service
restart. `GET /health` is inert config-wise (no new env the app reads).

---

## Session note — V2 CI gate + resume after a power cut

**Date:** 2026-09-08. Above-Core / operational. No `app/core/**` change.

### Resume check (power cut ended the previous session after the O3 commit)
Working tree clean at `706612d`, no stash, `git fsck` clean, live service
`active` (`/health` 200). Re-ran the full suite: **324 passed** — identical to
the O3 baseline. Nothing was lost.

### V2 — implemented
- **New `backend/scripts/ci.sh`** — the CI gate, one command:
  1. build a throwaway venv strictly from `requirements.lock.txt` (reproducible
     install — this also closes the D1 open action);
  2. `ruff check .` — errors-only (`backend/ruff.toml`: `select = ["F", "E9"]`,
     `extend-exclude = ["app/core", ".venv"]`);
  3. the full backend suite (`PYTHONPATH=. pytest -q`, includes the 122
     frozen-Core tests).
  Exit non-zero on any step. `--fast` reuses `backend/.venv` for a quick local
  check.
- **New `backend/ruff.toml`** — minimal lint config. `app/core/**` is excluded
  on purpose: it is frozen and validated by its own 122-test suite, and is not
  modifiable by above-Core work, so a lint finding there could not be actioned.
- **New `.github/workflows/ci.yml`** — `runs-on: ubuntu-latest`, Python 3.12,
  `working-directory: projects/homelab-control-center/backend`, `run: scripts/ci.sh`.
  **The repo has no remote yet, so this is inert.** Once the repo is pushed to
  GitHub it gates every push / PR to `main`/`master` with no further change; add
  branch protection then.
- **7 pre-existing dead imports removed** so an errors-only lint passes clean —
  all above-Core, no `app/core/**` touch:
  `app/main.py` (duplicate `load_settings` import — F811),
  `app/docker_provider.py`, `app/engineering/service.py`,
  `app/agent/testing/test_dependency_guard.py`,
  `app/engineering/testing/test_engineering.py` (×2),
  `app/homelab/testing/test_remediation.py` (all F401).
  ruff on the frozen Core still shows ~17 F401 (mostly intentional `__init__`
  re-exports) — left untouched, and excluded from the gate.

### Validation
`scripts/ci.sh` from a clean checkout-equivalent: **ruff clean**, **324
passed** in a fresh lock-built venv. `import app.main` unaffected. 122
frozen-Core intelligence tests unchanged.

### Matrix effect
**V2 → READY.** V group now 1 READY / 3 PARTIAL / 0 GAP. P1 now: **D3, O1, V1,
R3**. D1's open action (clean-venv-from-lock build) is closed by `ci.sh`.

### Not deployed
Nothing to deploy — `ci.sh` / `ruff.toml` / the workflow are dev/CI artifacts,
not part of the running service. The earlier undeployed commits
(`b485365..HEAD`: E6, E3, S3, E4, O3 + `/health`) still need one
`sudo systemctl restart rmt-control-center.service`.

### Next (P1, all above-Core)
D3 systemd hardening, O1 structured logging, V1 real end-to-end test, R3
platform-recovery runbook. D3 and R3 are the good candidates to hand the
standby agent (DeepSeek Flash v4) as a scoped draft brief; this session stays
the sole writer and integrator.

---

## Session note — O1 structured logging

**Date:** 2026-09-08. Above-Core / operational. **No `app/core/**` change.**

### Implemented — `app/ops/logging_config.py` (new; stdlib `logging`, no dependency)
- `configure_logging()` — owns the `rmt` logger tree: one line per record to
  **stdout** (systemd → journald), `JsonFormatter` by default (`ts`, `level`,
  `logger`, `msg`, `request_id`, + inlined `extra` fields), `TextFormatter`
  when `RMT_LOG_JSON=false`. `propagate=False` so uvicorn's root does not
  double-print. **Idempotent** — one handler; level refreshed from env on each
  call. Called first thing in the `app/main.py` lifespan.
- `request_id_var` (`ContextVar`) + `RequestContextMiddleware` (added last in
  `main.py` → outermost): mints a 16-hex id per request, honours an inbound
  `X-Request-ID`, echoes it on the response, logs exactly one `http_request`
  line (method, path, status, duration_ms, principal) — including on a handler
  exception (logged at ERROR, then re-raised). Every `rmt.*` line during the
  request carries the same `request_id`.
- `log_event(logger, event, /, level=INFO, **fields)` — one structured line for
  a governed-lifecycle boundary; `None` values and reserved `LogRecord` keys
  are dropped.

### Instrumented boundaries (above-Core only)
- `app/main.py` — `_log_governed(...)` after each of the 4 governed mutations:
  `governed_execute` / `governed_approve` / `homelab_remediate` /
  `homelab_approve`, carrying `principal`, `governed_status`, `action_id`,
  `execution_id`, `approval_id`.
- `app/homelab/operational_loop.py` — `loop_remediation` (one per real
  remediation attempt), `loop_quarantine` (WARNING), `loop_cycle_error`
  (ERROR), beside the existing `notify_ops` hooks.
- `app/agent/adapter.py` — `agent_proposal_outcome` on every path that reaches
  the adapter (`no_authority`, `error`, hold, executed, deny/reject) via a
  `_log_outcome(...)` helper.
- `app/ops/auth.py` — `require_operator` gained a `request: Request` param and
  stashes `request.state.principal = identity.name` (transparent to callers)
  so the middleware can attribute the request line.

### Config (dynamic, `app/ops/ops_config.py`)
`RMT_LOG_LEVEL` (default `INFO`), `RMT_LOG_JSON` (default `true`). Rotation is
journald's job — `DEPLOY.md` §5 (`SystemMaxUse=` / `MaxRetentionSec=` drop-in);
`CONFIG.md` has the logging section.

### Validation
`test_logging_config.py` — **16 passed** (formatter shape, extra-field inlining,
request-id binding, JSON single-line, text fallback, idempotent configure,
level-from-env + refresh, `log_event` drops none/reserved + respects level,
middleware mints/echoes/honours id + one line + error path + var reset).
Regression batch (auth + ops + loop + agent + http entrypoints) **183 passed**.
Full gate below. `import app.main` clean. 122 frozen-Core tests unchanged.

### Matrix effect
**O1 → READY.** O group now 3 READY (O1/O2/O3) / 0 PARTIAL / 1 GAP (O4). P1
now: **D3, V1, R3**.

### Not deployed
`logging_config.py` + `main.py` + `operational_loop.py` + `agent/adapter.py` +
`ops/auth.py` + `ops_config.py` — needs a service restart (same restart that
picks up the earlier undeployed `b485365..HEAD` batch). Then set a journald cap
(`DEPLOY.md` §5). Default `INFO`/JSON means more journal volume than today's
uvicorn-default output — bounded by the journald cap.

---

## Session note — D3 service hardening

**Date:** 2026-09-08. Above-Core / operational. **No code change** — a systemd
drop-in + docs only. C01–C07 frozen; no C08.

### The gap
`/etc/systemd/system/rmt-control-center.service` had only `Restart=always` /
`RestartSec=5` — no sandboxing, no resource ceilings, no restart backoff.
`systemd-analyze security` scored it **9.2 UNSAFE**.

### Recon that shaped the choices
- Runs as `User=rmt-lab` (already non-root); `rmt-lab` is in `docker` (socket
  access is a supplementary group — **not** dropped by `NoNewPrivileges`).
- Evidence JSON stores are `Path(__file__).parent / *.json` **inside the
  package tree**; `observability.db` is `data/observability.db` under
  `WorkingDirectory` — both under `/home` ⇒ `ProtectHome` must stay `no`,
  `ProtectSystem` `full` not `strict`.
- **No `psutil`, no `/proc` reads** in app code (metrics come from the Docker
  API) ⇒ `ProtectProc=invisible` is safe.
- Idle RSS ~70 MB, ~7 tasks ⇒ `MemoryMax=512M` / `TasksMax=128` are generous.
- systemd 255 ⇒ `RestartSteps` / `RestartMaxDelaySec` available.

### Delivered — `projects/homelab-control-center/deploy/systemd/hardening.conf`
Drop-in (same pattern as `bind-loopback.conf`). `[Unit]`
`StartLimitIntervalSec=300` / `StartLimitBurst=5`; `[Service]`
`RestartSteps=5` / `RestartMaxDelaySec=60`; `MemoryHigh=384M` `MemoryMax=512M`
`CPUQuota=200%` `TasksMax=128`; `NoNewPrivileges` `LockPersonality`
`RestrictRealtime` `RestrictSUIDSGID` `RestrictNamespaces` `RemoveIPC`
`UMask=0077`; `ProtectSystem=full` `ProtectHome=no` `PrivateTmp=yes`;
`ProtectControlGroups/KernelTunables/KernelModules/KernelLogs/Clock/Hostname`,
`ProtectProc=invisible`; `SystemCallArchitectures=native`
`SystemCallFilter=@system-service` (`SystemCallErrorNumber=EPERM`);
`RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6 AF_NETLINK`.

### Verified (no sudo needed)
- `systemd-analyze verify` on the merged unit (base + all 4 existing drop-ins +
  hardening.conf) — **clean**, no unknown-key warnings (all directives valid
  for systemd 255).
- `systemd-analyze security --offline=true` on the merged unit —
  **9.2 UNSAFE → 4.1 OK**.
- No `.py` touched ⇒ test suite unaffected (stays at `6f39100`'s gate: ruff
  clean, 340 passed).

### Deliberately deferred (documented in `DEPLOY.md` §5.1 — apply one at a time,
`systemd-analyze security` + `/health` after each)
`ProtectSystem=strict` + `ReadWritePaths=…/backend`; `ProcSubset=pid`;
localhost-only `IPAddressAllow`/`IPAddressDeny` (once the O2/O3 notify sink is
decided). `MemoryDenyWriteExecute` — not recommended for a CPython stack.

### Docs
`DEPLOY.md` — §5 reworked into §5.1 hardening (install / verify / rollback /
deferrals) + §5.2 journald retention; §0 drop-in list + §6 follow-ups updated.
`RMT_PRODUCTION_READINESS.md` — **D3 → READY**; the §4 summary table was
**resynced** (it had drifted badly — said 1 READY for group E when all 6 are
done, etc.). Now: 24 READY / 7 PARTIAL / 3 GAP / 1 ACCEPTED. Remaining GAP:
S7, O4 (P2), R3 (P1).

### Matrix effect
**D3 → READY.** **P1 remaining: V1, R3.**

### Not deployed / operator step
Install: `sudo install -m 0644
projects/homelab-control-center/deploy/systemd/hardening.conf
/etc/systemd/system/rmt-control-center.service.d/hardening.conf && sudo
systemctl daemon-reload && sudo systemctl restart rmt-control-center.service`,
then watch the first restart per `DEPLOY.md` §5.1. Folds into the same restart
that picks up the undeployed `b485365..HEAD` code batch (E6/E3/S3/E4/O3/O1).

---

## Session note — V1 automated end-to-end test on the real Docker adapter

**Date:** 2026-09-08. Above-Core / operational. **No `app/core/**` change.**

### The gap
Every suite mocked the execution adapter. The only real end-to-end proof was
the **manual** live exercises in this file.

### Delivered
- **New `app/homelab/testing/test_e2e_docker.py`** (`pytestmark =
  pytest.mark.e2e`) — 2 tests that drive the **real** `DockerExecutionAdapter`:
  1. `test_fault_held_approved_executed_verified` — disposable `alpine`
     container → `.stop()` (fault) → `observe_container_state` sees `exited`
     → `execute_governed_action(RESTART, requires_approval=True, adapter_name=
     "docker")` → **`manual_approval_required`** (asserts nothing executed:
     container still `exited`, audit store empty) → `approve_held_action(...)`
     → **`executed` / success** → real container back to `running` →
     `verify_docker_execution(...)` → **`verified_success`** → asserts the
     correlated `ExecutionAuthorization` (linked by `approval_id`, matching
     `action_id`), audit record (`adapter == "docker"`), execution trace, and a
     `verified_success` verification record — and that the **real** JSON stores
     are untouched.
  2. `test_real_adapter_failure_records_e3_evidence` — real adapter against a
     missing container → `success is False` → `record_failed_execution_evidence`
     → **`adapter_execution_failed`** (the E3 path, end-to-end).
- **Auto-skips** (`pytest.importorskip` + `pytest.skip`) when the Docker daemon
  is unreachable or `alpine:latest` can't be obtained → safe in the default
  suite and in CI. On this host (and a Docker-capable runner) it **runs for
  real** — `ci.sh`'s lock venv includes `docker==7.2.0`.
- **New `backend/pytest.ini`** — registers the `e2e` marker.
- Isolation: all six durable stores + **every** `verification_storage`
  reference swapped to in-memory; disposable container `rmt-e2e-<hex>` (never a
  homelab component) force-removed on teardown.

### Finding (fixed this session)
`app/ops/execution_evidence.py` binds its **own** module-level
`verification_storage` name (`from … import verification_storage`), so the
first draft's isolation missed it and test 2 wrote 2 real
`adapter_execution_failed` records for `rmt-e2e-absent-*` into
`verifications.json`. Fixed by adding `execution_evidence_module` to the patch
loop; the 2 stray records were removed (15 → 13). Re-verified: a full
`test_e2e_docker.py` run now leaves all six stores **byte-identical** (md5).
(The pre-existing un-cleaned `target: x` records from the 2026-09-07
`test_auth.py` era are a separate documented owner cleanup — not touched.)

### Validation
`test_e2e_docker.py` — 2 passed (real Docker, this host). Full gate `ci.sh`
below. No `app/core/**` change; 122 frozen-Core tests unchanged.

### Matrix effect
**V1 → READY.** V group now 2 READY / 2 PARTIAL / 0 GAP. **R3 is the last open
P1.**

### Not deployed
New test files only — nothing to deploy. The e2e test runs wherever Docker is
reachable (this host, a Docker-capable CI runner) and skips elsewhere.

---

## Session note — R3 RMT platform recovery (bare-host rebuild)

**2026-09-08.** R3 was the last open P1. Above-Core / operational; no
`app/core/**` change; no code change at all (deploy artifacts + one script +
docs).

### Problem
No procedure to rebuild the RMT **service itself** on a fresh host. Two concrete
gaps found in recon:
1. The base systemd unit existed **only** at
   `/etc/systemd/system/rmt-control-center.service` — not in the repo.
2. Two live drop-ins (`cap04-loop.conf`, `cap05-agent.conf`) were on the host
   but **not** in `deploy/systemd/` — a rebuild would silently come up without
   the CAP-04 loop / agent surface.
The pieces for the evidence half (E5 `rmt-evidence-*`, `rmt_evidence_verify.py`)
and the P0/D3 install steps (`DEPLOY.md` §1) existed but were not sequenced for
a cold start.

### Delivered
- **`projects/homelab-control-center/deploy/systemd/`** — now the canonical home
  for the unit + non-secret drop-ins:
  - `rmt-control-center.service` (base unit, captured verbatim from the host +
    header)
  - `cap04-loop.conf`, `cap05-agent.conf` (previously uncaptured)
  - `bind-loopback.conf`, `hardening.conf` (were already here)
  - `README.md` — drop-in inventory + merge semantics; **`auth.conf` stays out
    of git** (secret; `auth.conf.example` is the template)
- **`backend/scripts/rmt-rebuild.sh`** — orchestrates the cold start:
  prereqs (py3.12 / git / sqlite3 / rsync / docker group / systemd / caddy —
  hard-fail on core tools, WARN on soft) → `.venv` **from
  `requirements.lock.txt`** (same reproducible install as `ci.sh`) →
  `rmt-evidence-restore.sh <E5 backup>` → `rmt_evidence_verify.py` (**aborts on
  structural failure**) → full suite → install unit + the four non-secret
  drop-ins + `daemon-reload`, then **pauses** for the manual secret/CA checklist
  (`auth.conf`, `caddy trust`, journald cap, cron) before `enable --now` + a
  `/health` poll.
  - **`--drill DIR`** — rsyncs the project into `DIR`, runs venv → restore →
    verify → suite → a throwaway `uvicorn` on `--port` (default 8001,
    `RMT_AUTH_ENABLED=false`), then tears it down. `--skip-systemd` implied;
    **zero** changes to the live host / unit / evidence.
  - other flags: `--repo`, `--port`, `--skip-systemd`, `--skip-suite`, `--yes`.
- **`docs/operations/RMT_PLATFORM_RECOVERY.md`** — the R3 runbook (fast path via
  the script, manual fallback, the drill, post-rebuild verification). References
  `DEPLOY.md` §1 and `RMT_EVIDENCE_RECOVERY.md` rather than duplicating.
- Cross-refs updated: `docs/recovery/RECOVERY_RUNBOOK.md`,
  `docs/operations/RMT_EVIDENCE_RECOVERY.md` §4, `docs/operations/DEPLOY.md`
  §0/§6, `docs/RMT_PRODUCTION_READINESS.md` (R3 row → READY, summary, verdict).
- `.gitignore` — added `backups/rmt-evidence/` (runtime evidence backups are not
  source).

### Validation — scratch-dir drill PASSED (2026-09-08)
`rmt-evidence-backup.sh` → fresh backup
`~/homelab/backups/rmt-evidence/2026-09-08T21-54-28Z`, then:

```
./scripts/rmt-rebuild.sh --evidence <that backup> --drill <scratch> --port 8011
```

- prereqs ok (user in `docker` group)
- rsync staged the project into the scratch tree
- `.venv` built from `requirements.lock.txt`
- `rmt-evidence-restore.sh` restored the 6 stores + `observability.db` into the
  copy (`--force`, nothing serving it)
- `rmt_evidence_verify.py` → **`RESULT: OK`** (only the known-benign `14be2cb0`
  orphan-authorization WARN — documented in `RMT_EVIDENCE_RECOVERY.md` §2)
- full suite → **342 passed** in 315s
- throwaway `uvicorn` on `127.0.0.1:8011` → `GET /health` → `{"status":"ok", …}`
- exit 0; **live service on `:8000` untouched** throughout (verified: pid
  unchanged, loop still cycling, no `*.pre-restore.*` / `*.tmp` residue in the
  real tree, `git status` clean apart from the new/edited files)
- scratch tree removed afterward

### Residual
A genuine from-cold rebuild on a fresh VM (no `--drill`) is still recommended
once — it exercises the systemd unit-install, Caddy, and cron steps the drill
deliberately skips. Recorded as the R3 "Required action".

### Matrix effect
**R3 → READY.** R group 3 READY / 0 PARTIAL / 0 GAP / 1 ACCEPTED. **All P0 and
P1 items closed; only P2 hardening remains** (S5, S6, S7, D4, D6, O4, V3, V4 —
none blocking).

### Not deployed
Deploy artifacts + a script + docs. The base unit + drop-ins are the canonical
copies for a future rebuild; nothing about the running service changed.

---

## Session note — P2 batch (S5, S6, S7, D4, D6, O4, V3, V4)

**2026-09-08.** Closes every remaining production-readiness item. All
above-Core; **no `app/core/**` change**; full backend suite **365 passed**;
`ruff` (F, E9) clean. Owner picked the three branching decisions as recommended
(O4 = Prometheus `/metrics`; D4 = external check + restart; S6 = document +
accept).

Landed as three commits:
1. `RMT-PROD P2 (S5 + D6)` — CORS from config; runtime capability visibility.
2. `RMT-PROD P2 (S6)` — secrets pattern documented + accepted.
3. `RMT-PROD P2 (O4, S7, D4, V3, V4)` — metrics, rate limits, watchdog, smoke,
   env-route coverage.

### Per item
- **S5** CORS: `RMT_CORS_ORIGINS` (comma-sep) → `ops_config.cors_origins()`,
  default `["http://localhost:5173"]` — the stale hardcoded
  `192.168.235.128:5173` is gone. Methods scoped to `GET, POST`, headers to
  `Authorization, X-API-Key, Content-Type, X-Request-ID` (were `["*"]`).
  `test_cors.py` (4).
- **S6** secrets: `docs/operations/SECRETS.md`. No credential exists yet (local
  Ollama, no key). Standing pattern = root-owned `0600` systemd
  `EnvironmentFile`; the `systemd`-credentials path is scoped and **mandatory
  before the first credential**. READY *by policy*. Docs only.
- **S7** rate limiting: `app/ops/ratelimit.py` — in-process fixed-window,
  keyed `(principal, bucket)`. `/execute` 30/min, `/agent/act|act/llm|
  authority/grant` 20/min per operator → **429 + Retry-After**. Dependency
  depends on `require_operator` so `request.state.principal` is set first.
  `RMT_RATELIMIT_ENABLED=false` disables. Read-only agent routes untouched.
  `test_ratelimit.py` (5).
- **D4** watchdog: `backend/scripts/rmt-watchdog.sh` — cron/timer; N consecutive
  **unreachable** `/health` polls → `systemctl restart` + alert. `degraded` is
  alert-only unless `RMT_WATCHDOG_RESTART_ON_DEGRADED=true` (a restart doesn't
  clear a quarantine). Streak in a state file. Ops tooling only.
- **D6** runtime parity: `app/ops/runtime_info.py` — `/health` gains a
  `runtime` block (`configured_engine`, `resolved_adapter`, `docker_available`,
  `git_available`, `adapter_degraded`, `notes`); a configured/resolved engine
  mismatch logs a `WARNING` at startup (`warn_on_capability_mismatch`, called
  after `register_default_adapters()`). Advisory — does **not** flip `/health`
  `status`. `docs/operations/PREREQUISITES.md`. `test_runtime_info.py` (6).
- **O4** metrics: `app/ops/metrics.py` + unauthenticated `GET /metrics`
  (Prometheus text, `text/plain; version=0.0.4`, **no dependency**). Loop
  cycles/errors/quarantine, hold queue depth by status, approval decisions,
  verification outcomes, executions by adapter, authorizations, agent grants,
  `rmt_metrics_scrape_errors_total`. Read-only from the loop status + the six
  durable stores; every read wrapped (failure → counter, never 500).
  `test_metrics.py` (4).
- **V3** env routes: `test_env_routes.py` (5) pins `/containers`,
  `/containers/{name}/stats`, `/platform/state` in **both** modes. Those three
  route bodies now return **503** (`"docker unavailable: …"` / `"git
  unavailable: …"`) instead of an unhandled 500 when the capability is absent.
- **V4** smoke: `backend/scripts/rmt-smoke.sh` — post-deploy gate: `/health`
  ok, `runtime.resolved_adapter == RMT_SMOKE_EXPECT_ADAPTER` (default `docker`)
  + not degraded, `/metrics` up with 0 scrape errors, `/execute` +
  `/agent/status` → 401 unauth, loop state, optional authed check. Verified
  against a throwaway instance (9/10; the 10th was a deliberately mis-set
  expectation on a Docker-capable box).

### Matrix effect
S group 7/7 READY, D group 6/6, O group 4/4, V group 4/4. **Total 34 READY /
0 PARTIAL / 0 GAP / 1 ACCEPTED (R4).** `RMT_PRODUCTION_READINESS.md` §4 + §8
resynced.

### Not deployed
Live service still runs the pre-P2 code. Deploying picks up: `/metrics` +
`/health.runtime` + rate limits + 503-not-500 on env routes. New env vars
(`RMT_CORS_ORIGINS`, `RMT_RATELIMIT_*`) all have safe defaults; new scripts
(`rmt-watchdog.sh`, `rmt-smoke.sh`) are cron/manual. `CONFIG.md` + `DEPLOY.md`
§6 updated.

---

## Session note — Tier 1 homelab-depth batch (T1-2, T1-3, T1-4)

**Date:** 2026-09-09. Owner selected the "T1 homelab-depth batch" from
`docs/RMT_ABOVE_CORE_ROADMAP.md` §5 (escalation driver = external script +
read-only route; short proposal doc then proceed). Above-Core / operational +
domain. **No `app/core/**` change.** No new mutation path. C01–C07 remain
closed/frozen; no C08. Proposal: `docs/RMT_T1_BATCH_PROPOSAL.md` (APPROVED).

### Recon findings
- The homelab has **no** inter-container dependency edges (portainer / dozzle /
  uptime-kuma each need only dockerd). `HOMELAB_DEPENDENCIES` + Core
  `COMPONENT_CONTEXTS` correctly all-`[]`. T1-2 therefore delivers the
  *operational* path to declare an edge, not data.
- `continuation.py:69` gated the above-Core Learn/verify closure on
  `REMEDIATION_POLICY` membership (`uptime-kuma` only) — the recorded 5B-exercise
  `dozzle` finding. All three homelab components have a `ComponentContext`.
- `notifications.py` = one generic fail-open webhook, no channel shaping, no
  escalation. **Frozen-Core constraint:** `APPROVAL_HOLD_TTL_SECONDS = 300` — a
  hold nobody approves just expires; a "still unapproved after N min" timer only
  makes sense for N < 5 min, so the escalation's real value is the
  *expired-unapproved* signal.

### T1-3 — generalized `continue_remediation` attribution (done first)
- **Modified** `app/homelab/continuation.py` — the `REMEDIATION_POLICY`
  early-return is now `get_component_context(action.component) is None`. Dropped
  the `REMEDIATION_POLICY` import; added `get_component_context`. All existing
  guards unchanged (executed + `execution_id` + `expected_outcome`; records
  evidence only, post-execution). A no-context hold (operator `POST /execute`
  flow) still passes straight through.
- **Modified** `app/homelab/testing/test_continuation.py` — `_mock_docker_observer`
  gained a `name=` param; new `_place_held_action` helper; 2 new tests (a
  `dozzle` context-component held → approved → `verified_success` +
  executed-Learn record; + a `state_mismatch` variant). The existing
  no-context negative test still passes (comment reworded).

### T1-2 — operator-declarable dependency edges
- **New** `ops_config.homelab_dependency_edges()` — parses
  `RMT_HOMELAB_DEPENDENCIES` (`"web:db,cache;api:db"`; `;` groups, `,` deps;
  malformed skipped; dedup). Docstring bullet added.
- **Modified** `app/homelab/dependencies.py` — `_merged_map()` unions the static
  all-independent map with the env edges; `dependencies_of` / `dependents_of` /
  `resolved_map` use it; new `dependency_sources()` → `{"static":…, "env":…}`.
  The static dict + its docstring are unchanged. `from app.ops import ops_config`
  (no cycle — `ops_config` imports only `os`).
- **Modified** `app/agent/dependency_guard.py` — `dependency_view()` gains
  `sources` (`static` / `env` / `core_context`) for
  `GET /agent/status.dependency_map`. The escalation **rule** is untouched.
- **New** `app/homelab/testing/test_dependencies.py` (9) + a new operator-env-edge
  case in `test_dependency_guard.py` (declare → escalates, unset → de-escalates).
- **Live exercise (dev-host modules, recorded in `RMT_CAPABILITIES_EVIDENCE.md`
  §T1-2):** unset → `escalate("portainer","start") = (False,"")`; set
  `RMT_HOMELAB_DEPENDENCIES="uptime-kuma:portainer"` → `(True, "T13: allowed op
  'start' on 'portainer' would propagate to dependent(s) ['uptime-kuma'] …")`,
  `restart` (already restricted) not double-escalated, `sources.env =
  {"uptime-kuma": ["portainer"]}`; unset → `(False,"")`.

### T1-4 — real-channel shaping + missed-approval escalation
- **New** `ops_config.notify_format()` → `RMT_NOTIFY_FORMAT`
  (`generic` default / `slack` / `ntfy`; unknown → `generic`). **Modified**
  `app/ops/notifications.py` — extracted `_post(url, payload, *, summary, tags,
  priority)`; `generic` output is byte-identical to before; `slack` →
  `{"text": summary}`; `ntfy` → plain body + `Title`/`Priority`/`Tags` headers.
  De-dupe / fail-open unchanged.
- **New** `app/ops/held_holds.py::open_holds_view()` — read-only classification
  of every PENDING hold (`age_seconds`, `expires_at`, `expired`,
  `record_decision`/`record_terminal` from the authoritative record store,
  `actionable`, S3 provenance `kind`/`granted_by`/`agent_id`). Fail-open → `[]`.
- **New** route `GET /ops/holds` in `app/main.py` (operator-authenticated,
  read-only, returns `{"holds": [...]}`).
- **New** `backend/scripts/rmt-escalate.sh` — cron/timer; reads `/ops/holds`,
  POSTs a one-time alert to `RMT_ESCALATE_WEBHOOK_URL` for a hold still
  `actionable` past `RMT_ESCALATE_AFTER_SECONDS` (default 180; warns if not
  `< 300`) **or** `expired` while never approved. Escalated-id state file
  (`rmt-watchdog.sh` pattern); no in-process task.
- **New** `app/ops/testing/test_held_holds.py` (8: classification, terminal
  record → not actionable, non-pending skipped, S3 provenance, fail-open, route
  auth-on/off + shape) + 4 new `test_notifications.py` format cases.

### Validation
- Full backend suite **389 passed** (365 baseline + 24 new). Core intelligence
  suite **122** unchanged. `import app.main` clean. All agent / loop / notify
  flags OFF / `generic` by default.
- `bash -n rmt-escalate.sh` clean. (No `ruff` in the dev `.venv`; `ci.sh`'s
  lock-venv covers lint in CI.)

### Core integrity
Diff confined to `app/homelab/**`, `app/agent/dependency_guard.py`
(`dependency_view` only), `app/ops/**`, one read-only route in `app/main.py`,
`backend/scripts/rmt-escalate.sh`, and docs. No `app/core/**` change. No new
authorization / execution path. Learning append-only / read-only. Approval
enforcement unchanged; held actions never auto-continued.

### Not deployed
New env vars have safe defaults; `GET /ops/holds` is additive; `rmt-escalate.sh`
is cron-only. A redeploy picks them up. Repeating the T1-2 edge exercise on live
`:8000` needs a `deps.conf` drop-in + restart (owner-run).

### Docs updated
`docs/RMT_T1_BATCH_PROPOSAL.md` (new), `docs/RMT_CAPABILITIES_EVIDENCE.md`
(§T1 batch + index rows), `docs/RMT_T13_DISPOSITION.md` §3c,
`docs/operations/CONFIG.md`, `docs/RMT_ABOVE_CORE_ROADMAP.md` (T1-2/3/4 ticked;
§9 sequence), `RMT_CONTEXT.md` §12.

### Next
**T1-1** (broaden `REMEDIATION_POLICY` coverage — more components + action
verbs) is the remaining Tier 1 item. Then a Tier 2 domain (D-1 Agent Governance
Gateway is the roadmap's recommended first). Nothing authorized until the owner
selects it.

---

## Session note — repo pushed to GitHub; CI gate red on first push (SQLite substrate never initialised)

**Date:** 2026-09-09. The repo got its first off-machine remote —
`origin` = `github.com/rajab2030/rmt-platform` (**private**), `master` tracks
`origin/master`. `gh` is user-space at `~/.local/bin/gh` (no sudo/apt in the
non-interactive shell); commit identity is now `rajab2030
<ragb.taleb@gmail.com>` (global + repo-local); pre-2026-09-09 commits keep
`Local Developer <local@localhost>` by choice. See memory
`rmt-git-remote-setup`.

The first push triggered `.github/workflows/ci.yml`; the run **failed in 31s**
(`8 failed, 381 passed`). Above-Core / test-infra + a latent
production-startup fix. **No `app/core/**` code change.** C01–C07 frozen; no C08.

### Root cause
`app/core/observability/storage.py::init_storage()` (table `container_metrics`)
and `app/core/intelligence/memory/storage.py::init_storage()` (table
`intelligence_memory`) — both in `data/observability.db` — are the only code
that creates the schema, and **nothing calls them**. `get_connection()` just
opens the file; `save_container_metric` / `save_memory` do a bare INSERT with no
`CREATE TABLE IF NOT EXISTS`. `data/` is gitignored, so:
- the suite is green locally only because a months-old `data/observability.db`
  with the schema persists in the working tree;
- clean CI (empty `data/`) → 8 tests that hit the real store without a
  monkeypatch fail `sqlite3.OperationalError: no such table: ...`;
- **a fresh production deploy would 500** on the first metrics write /
  intelligence-memory read for the same reason — the live `:8000` server only
  works because its `data/observability.db` predates and survives reboots.

### Fix
- **Modified `app/main.py`** — `lifespan()` now calls `init_storage()` for both
  stores right after `register_default_adapters()` (before the collector task),
  mirroring the existing `reconcile_governance_stores()` /
  `archive_aged_evidence()` "startup readies the durable substrate" steps.
  Consumes the existing public `init_storage()` functions; no Core code touched.
  Fixes the real fresh-deploy bug, not just CI.
- **Rewrote `conftest.py`** — new session-autouse fixture
  `_isolate_sqlite_stores` redirects both modules' `DB_PATH` to a
  `tmp_path_factory` file and calls both `init_storage()`. Suite is now
  hermetic: no dependency on a leftover `data/observability.db`, and it no
  longer writes one.

### Validation
- Reproduced locally by moving `data/observability.db` aside → the same 8
  failures.
- After the fix: the 8 named tests pass from an empty `data/`; `data/` stays
  empty after a storage-touching run; ambient dev DB restored.
- `scripts/ci.sh` (throwaway venv from `requirements.lock.txt`, ruff
  errors-only, full suite) — **389 passed, exit 0, 6:45** (the exact GitHub
  Actions reproduction).
- Post-commit: confirm the Actions run on `master` is green.

### Files
`projects/homelab-control-center/backend/app/main.py`,
`projects/homelab-control-center/backend/conftest.py`.

### Next
CI is now actually live and enforcing. Roadmap §9: **T0-1 (SQLite substrate)**
is #1 — this failure is direct evidence for it (the DB-bootstrap story is
fragile: one file, two tables, no migration, gitignored). Then T0-3 / T0-4 /
T0-5, then T1-1, then a Tier 2 domain (D-1).

---

## Session note — T0-1: evidence substrate JSON → SQLite (Option A)

**Date:** 2026-09-09. Owner selected T0-1 from `docs/RMT_ABOVE_CORE_ROADMAP.md`
§9 and authorised **Option A** — a bounded internal change to
`app/core/intelligence/durable_store.py` (persistence mechanism only; method
signatures, return types, pydantic models, and all governance logic unchanged)
plus an additive `ApprovalHoldStorage.update()`. Same footing as the E1
atomic-write hardening. Proposal: `docs/RMT_T0_1_PROPOSAL.md` (APPROVED). No C08;
C01–C07 untouched.

### What changed
- **`durable_store.py`** — `DurableStore` now has three backends chosen by the
  path: `None` ⇒ in-memory list (unchanged; every isolated test relies on it);
  `*.json` ⇒ the E1 atomic whole-file rewrite (unchanged; kept for the
  migration + `--reverse`); `*.db` ⇒ one table (`_table`) in a shared SQLite
  file — `save()` is a single `INSERT` (**O(1)**, no rewrite), `update()` /
  retention are per-row, crash-atomic via WAL. `self._records` stays as the
  in-memory read mirror so `get_all()` / `get_by_*` are byte-identical.
  New helpers: `_commit_update`, `_replace_records`, `_archive_path`,
  `_sql_*`. `EVIDENCE_DB_PATH` = `RMT_EVIDENCE_DB` or `data/governance_evidence.db`.
- **The six store singletons** (`approval_storage.py` ×2, `authorization_storage.py`,
  `trace_storage.py`, `execution/storage.py`, `verification/storage.py`) — set
  `_table` (+ `_key_field` where there is an id lookup) and point at
  `EVIDENCE_DB_PATH`. `ApprovalHoldStorage.update()` added (mirrors
  `ApprovalRecordStorage.update()`); both route through `_commit_update`.
- **`app/ops/retention.py`** (E4) — `store._records = keep; store._persist()`
  → `store._replace_records(keep)` (backend-aware: JSON rewrite / SQLite
  `DELETE`+re-insert); `_archive_path(store)` → `store._archive_path()` so the
  six shared-DB stores get one archive file *each* (`data/<table>.archive.jsonl`),
  not a colliding `governance_evidence.archive.jsonl`.
- **`app/ops/reconcile.py`** (E2) — the stale-hold correction now calls
  `hold_storage.update(approval_id, **fields)` (one SQLite `UPDATE`) instead of
  mutating in place + `_persist()`.
- **`conftest.py`** — sets `RMT_EVIDENCE_DB` to a throwaway file in
  `pytest_configure` (before any app import, since the singletons bind the path
  at import) so the suite never touches the working-tree stores.
- **`scripts/rmt-migrate-evidence.py`** (new) — one-shot JSON → SQLite (order
  preserved; renames each file to `<name>.json.migrated`); `--reverse` dumps
  tables back to JSON in the exact prior format; `--force` overwrites a
  non-empty table. Runs under the venv (needs pydantic + the app).
- **`scripts/rmt-evidence-backup.sh`** — now `VACUUM INTO` snapshots
  `governance_evidence.db`; still copies residual `*.json` / `*.json.migrated`
  and picks up `data/*.archive.jsonl`; manifest reports per-table counts.
- **Docs** — `docs/operations/CONFIG.md` gains an "Evidence substrate" section
  (`RMT_EVIDENCE_DB`, `RMT_EVIDENCE_RETENTION_DAYS`, migration steps).

### Validation
- New `test_durable_store_sqlite.py` (8): `save` = one INSERT (row count, exact
  `payload` bytes); reload preserves order; `get_by_id` first-match + `update`
  in place + durable, no dup row; `file_path=None` writes no `.db`; retention
  `_replace_records` → DELETE+re-insert; per-table archive paths don't collide;
  **kill -9 mid-write** leaves a clean 0..k prefix (no torn row); 150 concurrent
  appends from 3 threads all land.
- New `test_migrate_evidence.py` (2): forward → `--reverse` round-trips
  byte-for-byte (fixture written through `model_dump(mode="json")`, the same
  path the live files use); forward is idempotent; `--force` clears + re-migrates.
- Existing `test_durable_store_atomic.py`, `test_durable_stores.py`,
  `test_retention.py`, `test_reconcile.py` unchanged and green (they use
  `.json` tmp paths → JSON backend).
- `scripts/ci.sh` (throwaway venv, ruff, full suite) — **399 passed, exit 0**
  (was 389 + 10 new). GitHub Actions on `master` — green.
- Smoke: `rmt-migrate-evidence.py` against the live dev JSON (7+89+88+77+77+79
  records) migrated cleanly into all six tables; renamed back afterwards (dev
  host not actually migrated).

### Not deployed / live-host action
The running `:8000` server still holds the JSON-backed singletons (started
before this change). On the live host: `rmt-evidence-backup.sh` →
`rmt-migrate-evidence.py` → restart the service. Until then a restart would come
up with an empty `governance_evidence.db` (the `.json` files are no longer read).

### Deferred (bounded follow-up) — DONE 2026-09-09 (see next note)
`rmt-evidence-restore.sh` and `rmt_evidence_verify.py` updated for
`governance_evidence.db`.

### Next
E4/E6 are now genuinely closed (bounded DELETE; single-transaction audit).
Roadmap §9 continues: T0-3 / T0-4 / T0-5, then T1-1, then a Tier 2 domain (D-1).

---

## Session note — T0-1 follow-up: E5 restore/verify for `governance_evidence.db`

**Date:** 2026-09-09. Closes the deferred item from the T0-1 note. Above-Core
recovery tooling; no `app/core/**` change.

- **`scripts/rmt_evidence_verify.py`** — `_resolve()` now also locates
  `governance_evidence.db` (backup layout `<dir>/governance_evidence.db`; live
  layout `<backend>/data/governance_evidence.db`). New check: open it read-only,
  assert all six evidence tables are present and countable (missing/unreadable
  table ⇒ **fatal**). Cross-store advisories now read from the DB tables when
  present, falling back to any residual JSON. Still stdlib-only. "No
  `governance_evidence.db` **and** no JSON stores" ⇒ fatal.
- **`scripts/rmt-evidence-restore.sh`** — step 4 branches:
  T0-1+ backup (`governance_evidence.db` present) → copy it to
  `backend/data/` (live `-wal`/`-shm` moved aside too);
  pre-T0-1 backup (`stores/*.json` only) → restore the JSON to
  `app/core/intelligence/**`, then `.venv/bin/python
  scripts/rmt-migrate-evidence.py --force` loads them into the DB (warns to run
  by hand if no venv). Archives + `observability.db` now restore to
  `backend/data/`.
- **`test_evidence_verify.py`** (new, 5): good backup-layout db passes; good
  live-layout db passes; a dropped table is fatal (`RESULT: FAIL`); an orphan
  authorization is advisory only (`RESULT: OK`); empty backup dir is fatal.
- Tidy: dropped an unused `import pytest` from `test_durable_store_sqlite.py`
  (ruff-excluded path, but dead).
- **Docs:** `docs/operations/RMT_EVIDENCE_RECOVERY.md` (§0 table + scripts
  table, §1 layout, §2 verify wording, §3 restore branches).

### Validation
- `test_evidence_verify.py` + `test_migrate_evidence.py` + `test_retention.py` +
  `test_reconcile.py` — 35 passed.
- Live drill: `RMT_BACKUP_ROOT=/tmp/... rmt-evidence-backup.sh` →
  `rmt_evidence_verify.py <backup>` `RESULT: OK` → `sha256sum -c` OK →
  `rmt-evidence-restore.sh <backup> --force` into a scratch backend (seeded with
  a stale live db) → stale db moved to `.pre-restore.<ts>`, restored db + obs.db
  in place → re-verify `RESULT: OK`.
- `scripts/ci.sh` — **404 passed, exit 0** (399 + 5). GitHub Actions — green.

### Still deferred (unchanged)
Live-host T0-1 cutover: `rmt-evidence-backup.sh` → `rmt-migrate-evidence.py` →
restart the `:8000` service. Owner-run.

---

## Session note — T0-4: CI gate finished & hardened

**Date:** 2026-09-09. Owner authorised **Option A** (`docs/RMT_T0_4_PROPOSAL.md`).
V1/V2 were already done and green on every push since the repo went to GitHub;
this closes the DoD gaps. Tooling / CI only — no `app/**` change.

### What changed
- **`backend/scripts/ci.sh`** — new step 3: `python -c "import app.main"` (import
  smoke; catches an import-time break the suite could mask). Header rewritten:
  4 steps, ~7-minute budget documented.
- **`.github/workflows/ci.yml`** — `concurrency: ci-${{ github.ref }}` +
  `cancel-in-progress`; `actions/checkout` → `@11d5960…` (v4),
  `actions/setup-python` → `@a26af69…` (v5), pinned by SHA. Trigger stays
  `[main, master]`: an `on: push` glob of `['**']` was pushed in `4b5d549` and
  **GitHub silently stopped triggering the workflow** (no run, no check-suite,
  `actionlint` clean) — reverted in `df3d36c`, run fired immediately.
- **`.githooks/pre-push`** (new, tracked, +x) — runs `ci.sh --fast`; exit 0 →
  push; exit 2 (no `.venv`) → warn + allow; other non-zero → **refuse the push**
  (`git push --no-verify` to override). Opt in per clone:
  `git config core.hooksPath .githooks` (set in this working copy now).
- **`docs/operations/CI.md`** (new) — the gate, "green = safe to build on", the
  ~7-min budget (real-time waits: loop cadence + hold TTLs), the hook opt-in,
  reading a failed run, and the branch-protection follow-up.
- **Doc ticks** — `RMT_ABOVE_CORE_ROADMAP.md` §5/§9/§10,
  `RMT_PRODUCTION_READINESS.md` V2 row.

### Not done — enforced "blocks on red"
A *required status check* needs GitHub Pro or a public repo
(`gh api …/branches/master/protection` → 403 on this free private repo). The
Actions run is the authoritative **visible** check; the pre-push hook is local
enforcement. Follow-up: add a required-check rule on `master` if/when the repo
goes Pro or public. Recorded in `CI.md` + roadmap + readiness.

### Validation
- `ci.sh` (throwaway venv) — ruff clean, **import smoke passed**, **404 passed,
  exit 0**.
- Hook: `bash -n` clean; deliberate F401 → `git push` refused by the hook (exit
  1) → `--no-verify` bypassed → reverted. Also verified on a green tree: the
  real T0-4 push ran the hook (`ci.sh --fast`, 404 passed) then pushed.
- GitHub Actions: run `34347577477` (commit `df3d36c`) **green** — the import
  smoke step + `concurrency` + SHA-pinned actions all work. (`4b5d549`'s run
  never fired — see the `['**']` note above.)

### Next
Roadmap §9: T0-3 (lifecycle observability) and T0-5 (S4/S3/S5 security finish)
remain in the Tier 0 batch; then T1-1, then a Tier 2 domain (D-1).

---

## Session note — RMT improvement roadmap + A3 (frozen-Core debt register)

**Date:** 2026-09-10. Documentation only — **no `app/**` change**, no suite run
needed. Follows the owner directive (2026-09-08): recorded frozen-Core gap →
above-Core mitigation or accept-and-record, never a freeze deviation.

### What was produced
- **`docs/RMT_IMPROVEMENT_ROADMAP.md`** (commit `c64790b`) — prioritized Phase
  A–D list of above-Core / operational / process improvements to the RMT that
  exists today. Companion to `RMT_ABOVE_CORE_ROADMAP.md` (menu of new
  directions). Recommended sequence in §8: **A1 → A2+A3 → B3 → B1 → C1 → B2 →
  C2 → C3 → D**. A1 = T0-1 (done), A2 = T0-4 (done).
- **`docs/RMT_B1_PROPOSAL.md`** (commit `313060f`) — **DRAFT rev-2**, not
  approved. B1 "strengthen the Verify stage" scoped in full: recon R1–R11, a new
  above-Core `app/ops/verification/` package (registry / expected /
  docker_observers / service / index), swap the 3 `verify_docker_execution`
  call sites + wire `POST /execute`, `observe_container_state` gains an `absent`
  reading, effective-status index + `verification_inconclusive` notify + 4
  `/metrics` counters + `GET /ops/verifications`. Split **B1a** (observer seam)
  / **B1b** (index + surface). **Blocked on owner answers to §7 Q1–Q4.**
- **`docs/RMT_FROZEN_CORE_DEBT.md`** (**A3**, roadmap §3) — the single
  authoritative table of every recorded frozen-Core gap:
  - **D1** `approve_held_action` persists the approval record but not the hold —
    a resolved hold reads `pending` on disk after restart
    (`approval_service.py:123`; no `approval_hold_storage.save` after `:163/172/185`).
    Compensating: record store authoritative + `reconcile.py` E2 + CAP-04 guard.
  - **D2** a *failed* adapter execution produces no Core verification evidence.
    Compensating: E3 `record_failed_execution_evidence` → `adapter_execution_failed`.
  - **D3** `_resolve_trusted_observer` (`verification/service.py:49`) resolves an
    observer only for `operation == "create"` with `module_name`; everything
    else → `observation_unavailable`. Compensating: above-Core Docker observer;
    B1 generalises it. (This row is added by B1 §6.)
  - **D4** Docker-flavoured names left in Core after freeze-deviation #1
    (`get_docker_health`, `runtime_engine="docker"` defaults, `bootstrap.py`
    importing `app.docker_api`). Compensating: injected `PlatformStateProvider`;
    names are cosmetic given the seam.
  - **D5** adapter-decoupling "#2–#18" deferred — only #2 and #3 are actually
    enumerated (DECOUPING §2); #4–#18 is an un-enumerated range.
  - §4 lists the `RMT_CONTEXT.md` §14 entries that are recorded-and-closed
    (no trigger).
  - Cross-linked from `RMT_CONTEXT.md` §14 and
    `docs/RMT_CORE_ADAPTER_DECOUPING.md` §9; roadmap A3 marked **DONE**.

### Validation
Documentation only; no code, no tests. `file:line` references in
`RMT_FROZEN_CORE_DEBT.md` verified against the working tree on 2026-09-10.

### Next
- **Owner decision on B1:** answer `docs/RMT_B1_PROPOSAL.md` §7 Q1–Q4, then
  authorise **B1a** — or take the cheaper roadmap items first (**B3** threat
  model + guarantees, size S).
- Then per roadmap §8: **B1 → C1** (broaden `REMEDIATION_POLICY`, exercises B1)
  → **B2** → **C2** (second domain, the thesis proof).

---

## Session note — B3 (threat model + guarantees / non-guarantees)

**Date:** 2026-09-10. Documentation only — **no `app/**` change**, no suite run.
Roadmap item **B3** (`docs/RMT_IMPROVEMENT_ROADMAP.md` §4).

### What was produced
- **`docs/RMT_THREAT_MODEL.md`** — scope anchor (governed action gateway; the
  poor-fit list); assets A1–A7; deployment topology under threat model **(b)**
  (loopback bind + Caddy TLS, single VM, `systemd` hardening 4.1 OK, S1 auth);
  trust boundary + adversary **(b) trusted LAN, few operators** with a hostile
  operator / host / LAN explicitly out of the adversary model; an attack-surface
  table (surface · vector · control, cross-referenced to readiness S1/S4/S5/S7/
  S2/S3/E1/E6/E5/R1/S6/D1/V2/D3/D4); a residual-risk table where **every row
  traces** to a `RMT_FROZEN_CORE_DEBT.md` row (D1–D5) or a readiness decision
  (R4, S3, O2, V2) or a roadmap item (P-D, C3); a "posture (c)" escalation note.
- **`docs/RMT_GUARANTEES.md`** — §0 fit / poor-fit; then per lifecycle stage
  (Understand → Decide → Govern → Authorize → Execute → Verify → Learn) an
  **Asserts / Does not assert / Evidence** triple, in plain language; §8
  cross-cutting guarantees (correlation, atomic + hard-kill-faithful evidence,
  auth-or-refuse-start, Docker-absent parity); §9 cross-cutting non-guarantees
  (no HA, no RBAC, no rollback engine, frozen Core, journal-only alerting)
  each traced. The Verify section states plainly that outside module `create`
  the Core records `observation_unavailable` (D3) and `/execute` is unverified
  until B1.

### Cross-links added
- `README.md` — new "RMT — governed control plane" section linking GUARANTEES,
  THREAT_MODEL, FROZEN_CORE_DEBT, IMPROVEMENT_ROADMAP, RMT_CONTEXT.
- `RMT_CONTEXT.md` §5 — "External-facing explainers" note under the
  governing-documents table.
- `docs/RMT_IMPROVEMENT_ROADMAP.md` — B3 marked **DONE**.

### Validation
Documentation only; no code, no tests. Readiness / debt-register / roadmap
references checked against the tree on 2026-09-10.

### Next
Roadmap §8 order, A1/A2/A3/B3 now done: **B1** is the next build — needs owner
answers to `docs/RMT_B1_PROPOSAL.md` §7 Q1–Q4, then authorise **B1a**. After B1:
**C1** (broaden `REMEDIATION_POLICY`, exercises B1) → **B2** → **C2**.

---

## Session note — B1a: strengthen the Verify stage (above-Core observer layer)

**Date:** 2026-09-10. Owner answered `docs/RMT_B1_PROPOSAL.md` §7 Q1–Q4 (keep
5 s settling poll; `/health` minimal; delete `verify_docker_execution` now;
low-severity notify in B1b) and authorised **B1a**. **No `app/core/**` change.**

### What changed
- **New `app/ops/verification/`** — `registry.py` (`register_observer` /
  `resolve_observer`, `(adapter, operation)` → factory; miss → `None`),
  `expected.py` (`expected_state_for`: docker start/restart/create→`running`,
  stop→`exited`, remove→`absent`), `docker_observers.py` (registers
  `observe_container_state` for `docker` × 5 ops), `service.py`
  (`verify_executed_action(execution_id, *, adapter_name, operation, target,
  expected=None)` — builds `expected` from the table when omitted; settling poll
  `RMT_VERIFY_OBSERVE_TIMEOUT_S` default 5 / `0`=single-shot / ~0.5 s /
  early-return on match; frozen `verifier.verify` + `verification_storage.save`;
  `result.reason` prefixed
  `[layer=above_core adapter=… supersedes=observation_unavailable]`, the
  `supersedes=` clause only when a Core `observation_unavailable` record already
  exists for the id; no observer → returns `observation_unavailable`, writes
  nothing; `verification_storage` dereferenced through its module at call time —
  R10).
- **`app/homelab/observer.py`** — reachable-and-gone → `ObservedState(state="absent")`;
  `None` reserved for "could not observe" (docker down / lookup raised). `remove`
  is now verifiable.
- **3 call sites swapped** to `verify_executed_action(..., adapter_name="docker",
  operation=<action_type>.value, ...)`: `app/homelab/remediation.py`,
  `app/homelab/continuation.py`, `app/agent/adapter.py`. **`app/homelab/verification.py`
  deleted.**
- **`app/main.py::execute`** — after the E3 hook, an executed+successful operator
  action calls `verify_executed_action(adapter_name=_resolve_adapter_name(),
  operation=operation, target=target)`; response gains
  `above_core_verification_status` (`effective_verification_status` is B1b).
- **`conftest.py`** — `RMT_VERIFY_OBSERVE_TIMEOUT_S=0` default (suite doesn't
  spend the 5 s budget on a `state_mismatch`).
- Test churn for the deleted module + the R10 storage-module patch:
  `test_observer.py`, `test_continuation.py`, `test_integrated.py`,
  `test_e2e_docker.py`, `test_agent_governance.py`;
  `app/engineering/repo_index.py` + an `app/ops/execution_evidence.py` docstring
  re-pointed. **New:** `app/ops/verification/testing/test_service.py`,
  `test_execute_route.py`.
- Docs: `docs/operations/CONFIG.md` (new `RMT_VERIFY_OBSERVE_TIMEOUT_S` knob),
  roadmap B1 + proposal §9 completion note + `RMT_CAPABILITIES_EVIDENCE.md` B1a
  section.

### Validation
- Full backend suite **433 passed** (7 m 10 s); `ruff check app` (F, E9) clean;
  `import app.main` clean.
- Core intelligence suite **134 passed** — unchanged by this work (`git diff`
  touches no `app/core/` path).
- `test_e2e_docker.py` (real `docker restart` of a disposable container) **2
  passed** through the new `verify_executed_action`.

### Next
**B1b** (scoped, not yet authorised): effective-status index (§2.3) + startup
reconcile; `verification_inconclusive` notify (§2.4, Q4);
`rmt_executed_actions_*` `/metrics` counters; `GET /ops/verifications`;
`effective_verification_status` on the `/execute` response; the
through-`POST /execute` e2e. Then roadmap §8: **C1** (broaden
`REMEDIATION_POLICY`, exercises B1) → **B2** → **C2**.

---

## Session note — B1b reconnaissance + B1b implementation (Verify stage complete)

**Date:** 2026-09-10. Owner asked for a recon/contract-review pass before B1b,
approved the two decisions and the plan, then authorised implementation.
**No `app/core/**` change.**

### Recon (committed first, read-only)
`docs/RMT_B1b_RECON.md` — §1 retro-verified the landed B1a diff against the
frozen contracts (CLEAN: zero `app/core/` files; nothing parses
`VerificationResult.reason`; the one recorded deviation = the 3 homelab/agent
sites pass `adapter_name="docker"` literally). §2 RB-1..RB-9 against `HEAD`:
`notify_ops` real signature is `(kind, detail, key, source)` not `(event=, …)`
(RB-1); the `"executed"` result dict has **no** `action_id` (RB-2); the
"JSON-peer, migrates under A1" plan is stale now A1 is done (RB-3); `/ops/holds`
is the route template (RB-5); `rmt_verifications_total` now double-counts after
B1a (RB-6); the e2e-through-`/execute` isolation is the fiddliest bit (RB-8).

### Decisions (owner: both as recommended)
1. Index = **in-memory projection** rebuilt at startup (not a SQLite table).
2. `rmt_verifications_total` **left raw**; 4 new index-projection counters added
   alongside.

### B1b implemented
- **`app/ops/verification/index.py`** — in-memory `IndexRow` per `execution_id`;
  `effective_status` precedence per §2.3; `rebuild()` (silent, marks history
  `notified_inconclusive`), `record()`, `view(limit, effective_status)`,
  `snapshot()`, `get()`, `reset()`.
- **`service.py`** — `verify_executed_action` gains `action_id`; both branches
  update the index; `unverified` + not-yet-notified → one
  `notify_ops(kind="verification_inconclusive", key=execution_id, …)` +
  `mark_notified` (once per id).
- 4 call sites pass `action_id=`; `app/main.py` lifespan `rebuild_verification_index()`
  after `archive_aged_evidence()`; new **`GET /ops/verifications`**
  (`require_operator`, `?limit=`/`?effective_status=`, `[]` on error);
  `POST /execute` response gains `effective_verification_status`.
- **`metrics.py`** — `rmt_executed_actions_total{adapter,operation}` +
  `_verified_total`/`_unverified_total`/`_state_mismatch_total` from the index.
- Tests: `app/ops/verification/testing/` conftest (autouse index+notify reset),
  `test_index.py`, `test_ops_verifications_route.py`, additions to
  `test_service.py` / `test_execute_route.py` / `test_metrics.py`, and
  `test_e2e_docker.py::test_operator_execute_http_verified_through_index` (real
  `docker restart` through `POST /execute` → `effective_verification_status ==
  "verified_success"` + one index row).
- Docs: `RMT_B1_PROPOSAL.md` (status DONE + §10), `RMT_B1b_RECON.md` §4
  decisions locked, `RMT_IMPROVEMENT_ROADMAP.md` B1 done,
  `RMT_FROZEN_CORE_DEBT.md` D3 compensating-control rewritten,
  `RMT_CAPABILITIES_EVIDENCE.md` B1b section, `docs/operations/DEPLOY.md` §6.

### Validation
Full backend suite **455 passed** (exit 0, ~8 min); `ruff` (F, E9) clean;
`import app.main` clean; Core intelligence suite **134 passed**, unchanged
(no `app/core/` diff); e2e set (3, incl. the new through-`/execute` test)
**passed** against a real container.

### Next
Roadmap §8: A1/A2/A3/B3/B1 done. Next build **C1** — broaden
`REMEDIATION_POLICY` beyond `uptime-kuma` restart (exercises B1; T13
safe-envelope guard stays green) — then **B2** (durable approval request +
minimal view) → **C2** (second domain, the thesis proof). Each still needs a
per-item recon + owner approval before implementation.

---

## Session note — T0-6 public-showcase exercise + repository made PUBLIC

**Date:** 2026-09-12. **Note on this file:** this is the first `HANDOFF.md`
entry since the 2026-09-10 B1b note above — C1/T1-1, RMT-CAP-06, RMT-CAP-07,
the continuation-path verification-gap close, RMT-CAP-08, and T0-2/T0-3/T0-5
all happened in the interim and are **not** narrated here; they're fully
recorded in `docs/RMT_CAPABILITIES_EVIDENCE.md` (§"C1 / T1-1" through
§"T0-5") and summarized in `RMT_CONTEXT.md` §12. This note picks up from
there rather than reconstructing sessions this one didn't witness.

### Owner directive
"We are trying to publish the platform" — followed by, once a plan was
proposed, "before go public you suggest a demo that show how the platform
perform a real test dealing with an AI agent (show case)." Two decisions
were confirmed explicitly along the way: publish = make
`github.com/rajab2030/rmt-platform` **public** (not just push commits), and
proceed with a real live exercise, not a scripted/fabricated one.

### Work performed
- **Secret audit of the full git history**, before touching visibility:
  `git log --all -p` scanned for token/key/password patterns. Found only
  fixture test credentials (`alice-secret`, `bob-secret` in auth-header unit
  tests) and one committed `frontend/.env` with a private-LAN URL
  (`VITE_API_URL=http://192.168.235.128:8000`) — not a real secret. The
  actual `RMT_OPERATOR_TOKENS` values were never in git, by design (T0-5's
  own fix). Repo history judged clean for going public.
- **T0-6 — live agent-governance exercise on the production `:8000` service**
  (first time this domain ran there, not an isolated port): enabled the
  pre-existing conditional git adapter via a new `git-domain.conf` drop-in
  (`RMT_AGENT_GIT_REPO_PATH`), then ran the full lifecycle for real — grant,
  preview, propose (→ `hold`), human approval, execute, verify, in both
  directions (create + remove a tag in the dedicated scratch repo) — plus a
  refusal case (spent-grant reuse → `no_authority`) and unprompted
  risk-differentiated approval reasoning between `create` and `remove`.
  Independently corroborated outside the API: `git tag` state in the scratch
  repo, and `journalctl`'s `homelab_approve` log lines matching the API
  receipts' `action_id`/`execution_id`/`approval_id` exactly. Written up in
  `docs/RMT_CAPABILITIES_EVIDENCE.md` §"T0-6" (commit `299c746`).
- **Operational hiccup mid-exercise:** the operator token rotated in T0-5 no
  longer authenticated against the live secret file. Diagnosed without ever
  exposing plaintext in this session — first ruled out a `curl -s`
  error-swallowing red herring (fixed the demo script to use `-sS` +
  poll-for-health instead of a blind `sleep`), then confirmed a genuine
  mismatch via SHA-256 hash comparison of the typed token against every
  stored token. Owner rotated fresh and saved the new value properly.
  Recorded as an open item (no durable record of last-verified-working
  token) — not a platform defect, a runbook gap.
- **Pushed 6 pending local commits to origin** (`20f6e01..299c746..949793a`),
  each through the repo's pre-push CI gate (full 528-test backend suite,
  ~8 min, green both times).
- **Made `rajab2030/rmt-platform` PUBLIC** (`gh repo edit --visibility
  public`), confirmed via `gh repo view` (`isPrivate: false`).
- **README.md** — added a `**Repository:**` link at the top pointing back
  to the now-public GitHub URL (commit `949793a`).
- **RMT_CONTEXT.md** — added the public-repository status note to §9 and a
  T0-2/T0-3/T0-5/T0-6 + publish-sequence summary to §12, since this file had
  not been updated since the RMT-CAP-08 note (2026-09-11).

### Validation
- Git history audit: clean (no real secrets in any commit, ever).
- T0-6 exercise: all 9 steps behaved exactly as the frozen policy/risk/
  approval chain predicts; independently corroborated by two data sources
  outside the HTTP API (git state, journald).
- Both pushes: CI gate PASSED (528 passed) before landing on `origin/master`.
- Post-publish: `gh repo view` confirms `visibility: PUBLIC`.

### Next
No above-Core capability is currently in-flight. Recommended, roughly in
order of how directly each builds on what's now proven and public:
1. **Close the operator-token custody gap** — a documented step (e.g. "after
   any rotation, immediately verify with one authenticated call and record
   the date") in `docs/operations/SECRETS.md` or `DEPLOY.md` §4. Process
   fix, no code.
2. **P-B — governed-evidence console** (`docs/RMT_ABOVE_CORE_ROADMAP.md`):
   now has a real justification — a second domain (D-1) is proven, public,
   and demonstrable; there's something worth building a console to look at.
3. **A second Tier-2 domain** (D-2..D-5 in the roadmap) to further prove the
   Core's generality now that the first proof is public evidence, not just
   an internal claim.
4. **P-D — multi-operator RBAC** if the public repo brings in more than one
   real operator.
Each still needs the same per-capability recon + owner approval before
implementation — publishing changes nothing about the working method.

---

## Session note — operator-token custody gap closed (docs-only)

**Date:** 2026-09-13. Owner selected candidate (a) from the prior session's
list. Documentation-only fix, **no code change**, no `app/**` diff, no test
run needed.

### What changed
- **`docs/operations/DEPLOY.md` §4 (Token rotation)** — added a mandatory
  verify-and-record step right after every rotation: one authenticated
  `curl` against the live service confirming `200` with the new token, then
  a plaintext-only timestamp written to
  `/etc/rmt-control-center/operator_tokens.rotated_on` (mode `0600`, beside
  the secret file, outside git). This is a durable record of *when a
  rotation was last confirmed working*, distinct from the existing record
  of when the file was edited.
- **`docs/operations/SECRETS.md`** — cross-referenced the same requirement
  in the rotation bullet, and added a "Rotation-verification gap" note
  under Disposition explaining what T0-6 found and how this closes it.
- **`RMT_CONTEXT.md` §12** — the T0-6 "open item recorded, not yet actioned"
  paragraph rewritten to "CLOSED (2026-09-13, docs-only)"; the "Next action
  for a new session" candidate list re-numbered now that (a) is done.

### Why this shape
The gap was never "tokens aren't stored securely" (T0-5 already closed
that) — it was "a rotation can silently fail to take, and nothing records
whether it was ever confirmed." A one-line authenticated smoke check plus a
timestamp file closes that without introducing new code, new
infrastructure, or a new credential to manage.

### Validation
Docs only; no suite run. Manually re-read both edited runbook files for
internal consistency after editing.

### Next
Candidates unchanged except (a) removed: **P-B** (governed-evidence
console), a second Tier-2 domain (D-2..D-5), or **P-D** (multi-operator
RBAC). Owner to select; same per-capability recon + approval method
applies.
