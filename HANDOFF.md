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
  declared. Finite platform-validation suite passes (122 tests); G2 Core-boundary
  review passed; no reachable governance bypass.

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

**C07 — Platform Validation and Freeze: CLOSED.** The RMT Core has reached
**Platform Freeze**. There is no C08.

**Immediate next action:** post-freeze work is above-Core/domain/product/
integration/adapter/application. No new Core milestone. Any Core change requires
evidence that the finite Target State or an existing Core contract is
insufficient.

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

> RMT Core is post-freeze. C01–C07 are closed; the RMT Core has reached Platform
> Freeze; there is no C08. Read `RMT_CONTEXT.md` first, then `HANDOFF.md`, then the
> governing documents. Full suite is 122 passed; D1 resolved; G2 passed.
> register_module() is an internal governed primitive; execute_action() is
> unreachable dead-code housekeeping. Future work is above-Core/domain/product/
> integration/adapter/application. Start with read-only reconnaissance and
> contract review. Do not modify files or run system/git commands without explicit
> approval.

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
