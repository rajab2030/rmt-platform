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
