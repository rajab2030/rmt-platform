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
reopen C01–C07. The next objective is the **First Real RMT Capability — Homelab
Operations**: use the frozen RMT Core as the intelligent control plane for the
real homelab and demonstrate a genuine end-to-end operational capability through
**Understand → Decide → Govern → Authorize → Execute → Verify → Learn**. Do not
start implementation of this capability yet.

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
  Boundary integrity ≠ policy completeness. **T13 is an open above-Core work
  item**; owner disposition pending.

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
- Continuous Homelab operational loop (observe → remediate) remains a candidate
  **CAP-04** — separate proposal, not started.
- Owner disposition still pending on: the MCR/T13 dependency-cascade policy
  finding (open above-Core work item); whether the MCR pattern informs a future
  above-Core capability (e.g. AI Agent Governance — governing a reasoning agent
  as an MCR "child"). MCR docs are recorded in `docs/` but are **not** RMT
  authority documents and do not change C01–C07.
