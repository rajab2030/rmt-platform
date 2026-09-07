# RMT — Above-Core Capability Evidence Index

> **Purpose:** evidence/closure record for above-Core RMT capabilities
> (RMT-CAP-*). These are NOT Core milestones (C01–C07 remain closed/frozen; no
> C08). Each entry records completion, validation, and Core-integrity status.
> This is a coordination/evidence document, not architecture authority.

---

## RMT-CAP-01 — Homelab Operations (Learn closure)

- **Status:** COMPLETED & VERIFIED.
- **Objective:** close the missing Learn stage in the Homelab operational loop;
  demonstrate the full governed lifecycle
  `Understand → Decide → Govern → Authorize → Execute → Verify → Learn`.
- **Implementation:** above-Core only. `app/homelab/remediation.py` now records
  the remediation outcome through the existing frozen Core learning/memory
  capability (`MemoryRecord` + `remember`, append-only/read-only), tied to the
  run via `execution_id`/`approval_id`.
- **Validation:** focused Homelab integration tests pass; full C07/Core suite
  **122 passed** (no regressions); full app suite **141 passed**.
- **Core integrity:** C01–C07 untouched; governed execution semantics
  untouched; no Docker execution required (run-safe mocks).

## RMT-CAP-02 — Engineering Change-Impact & Risk Analysis

- **Status:** COMPLETED & VERIFIED.
- **Objective:** read-only, deterministic, evidence-backed engineering analysis:
  given a proposed change, identify affected components, governance boundaries,
  relevant evidence, engineering-change risk, and a recommendation — all
  traceable to repository/evidence sources.
- **Implementation:** above-Core only. New `app/engineering/` package
  (`models.py`, `repo_index.py`, `service.py`, `api.py`, `testing/`). Consumes
  frozen Core read-only primitives only (`get_modules`, `get_governed_outcomes`,
  `get_previous_failures`, `get_component_context`). Read-only `GET
  /engineering/change-impact` endpoint.
- **Validation:** **14 focused tests passed**; full app suite **155 passed**
  (141 baseline + 14 new). `app.main` imports cleanly.
- **Core integrity:** C01–C07 untouched; no frozen Core file modified; governed
  execution semantics untouched; read-only guarantee verified (no store writes,
  no execution, no authorization, no repository mutation).

### CAP-02 semantic clarification — `unknown_dependency=True`

`unknown_dependency=True` means the component's **dependency knowledge is
incomplete/unestablished** (e.g., the module registry `dependencies` list is
empty or not populated for that component). It does **NOT** mean an actual
unknown dependency was discovered. It is a conservative risk signal that
dependency information is not yet established, not evidence of a real
dependency edge. This is a deterministic, evidence-backed factor; it must not be
misread as a discovered dependency.

## RMT-CAP-03 — Homelab Remediation Approval-Continuation Learn Closure

- **Status:** COMPLETED & VERIFIED (2026-09-06).
- **Objective:** close the Learn-stage gap for **approval-continuation**
  remediations. When a Homelab remediation is held for manual approval,
  `remediate_and_verify()` records only the held state
  (`manual_approval_required`). The human continuation via the frozen Core
  `approve_held_action()` executes and runs Core verification, but nothing
  above-Core observed that executed outcome — so no Learn/`MemoryRecord` was
  written for it, and the above-Core Docker verification never ran. (Finding
  originally recorded in the 2026-09-04 live fault-injection session.)
- **Implementation:** above-Core only.
  - **New** `app/homelab/continuation.py` — `continue_remediation(approval_id,
    approved_by, approved=True)` wraps the frozen Core `approve_held_action()`
    (called unchanged); for an *executed* Homelab remediation it then runs the
    existing above-Core Docker verification (`verify_docker_execution`) and
    records the executed outcome through the existing Core learning/memory
    capability (`record_learning` → `MemoryRecord` + `remember`), correlated by
    `approval_id` / `execution_id`. Non-Homelab holds (e.g. the operator
    `POST /execute` flow) pass straight through, unchanged.
  - **Modified** `app/homelab/remediation.py` — `_record_learning` renamed to
    `record_learning` (now shared) plus clarifying comments; no behavior change.
  - **Modified** `app/main.py` — new route `POST /homelab/approve` →
    `continue_remediation`. Generic `POST /approve` left untouched.
- **Validation:** **5 focused tests passed**
  (`app/homelab/testing/test_continuation.py`); full Homelab suite **21 passed**
  (16 baseline + 5 new); full C07/Core intelligence suite **122 passed**; full
  app suite **160 passed** (155 baseline + 5 new).
- **Core integrity:** C01–C07 untouched; no frozen Core code modified (diff
  confined to `app/homelab/**` + `app/main.py`); `approve_held_action()` called,
  never modified; no new authorization or execution path (the wiring only reads
  the hold and records evidence *after* the Core executes); learning remains
  append-only / read-only.

### C07 test-artifact correction (recorded alongside CAP-03, 2026-09-06)

During CAP-03 validation, `app/core/intelligence/testing/test_http_entrypoints.py`
showed **2 failures** (`TestExecute::test_execute_low_risk_auto_allowed_records_evidence`,
`TestApprove::test_approve_valid_continuation_executes`) — reproducible at the pure
freeze commit `46a4441`, **not** caused by CAP-03. Root cause: the artifact did
not mock the execution adapter, so it implicitly depended on `docker_available()`
being False (safe `simulation` fallback). On 2026-09-04 the Docker socket was
permission-denied, so the suite recorded 122 passed. In the current shell Docker
is reachable, so `_resolve_adapter_name()` selected the real Docker adapter, which
failed on non-existent containers `web1` / `db2`; `execute_governed_action` /
`approve_held_action` skip post-execution verification when `result.success` is
False, leaving the verification store empty and failing the two `>= 1` assertions.
No Core code was wrong. **Correction (owner-approved):** mock the execution
adapter registry in that file's `_isolate_evidence_stores` helper (same pattern
as `test_integrated.py`) so the executed-path transport tests are Docker-daemon
independent. Diff confined to the one test file (+24/−1); no Core code touched;
Core intelligence suite restored to **122 passed**.

---

## RMT-CAP-04 — Continuous Homelab Operational Loop

**Date:** 2026-09-07. Above-Core capability. C01–C07 remain closed/frozen; no
C08; no frozen Core code modified. Approved scope: `docs/RMT_CAP_04_PROPOSAL.md`.

- **Objective:** run the existing single-shot Homelab governed lifecycle
  (`Understand → Decide → Govern → Authorize → Execute → Verify → Learn`) on a
  cadence, under supervision — the frozen Core as a continuous homelab control
  plane. Adds **cadence + guardrails only**, no new mutation path.
- **Implementation:** above-Core only.
  - **New** `app/homelab/operational_loop.py` — `HomelabOperationalLoop`
    (module singleton `operational_loop`). Each cycle iterates
    `REMEDIATION_POLICY` components and calls the existing
    `remediate_component(component)` entrypoint; classifies the governed
    outcome; updates per-component loop state; appends a bounded cycle record.
    Guardrails: **approval retained** (a `manual_approval_required` outcome is
    recorded, never continued — `continue_remediation` is not imported here);
    **flap guard** (N held/failed attempts within a window → component
    quarantined, read-only recovery checks only until healthy streak or manual
    clear); **cooldown** after every attempt; **duplicate-hold guard**
    (a read-only query of the approval hold store — if a `pending` hold already
    exists for the component the loop returns `awaiting_approval` instead of
    routing another remediation: no second hold, no flap count, no spurious
    quarantine of something merely waiting for a human); **single-flight**
    (cycles never overlap); **fail-safe** (per-component and per-cycle
    `try/except`; the task never raises into the app). State transitions
    (quarantine / recovery /
    manual clear) are recorded append-only through the existing Core memory
    capability (`remember` + `MemoryRecord`) with distinct `event_type`s
    (`homelab_loop_quarantine`, `homelab_loop_recovery`,
    `homelab_loop_quarantine_cleared`).
  - **New** `app/homelab/loop_config.py` — env-overridable constants
    (`LOOP_ENABLED` default **False**, interval 120s, flap window/threshold,
    cooldown, recovery streak, history cap). No `app/core/configuration/**`
    change.
  - **Modified** `app/main.py` (+52) — `lifespan` starts the loop task only
    when `LOOP_ENABLED`, and stops it on shutdown; new routes
    `GET /homelab/loop/status` (read-only), `POST /homelab/loop/start`,
    `POST /homelab/loop/stop`, `POST /homelab/loop/clear?component=`.
  - **New** `app/homelab/testing/test_operational_loop.py` — 17 run-safe tests
    (`remediate_component`, `observe_container_state`, `remember` and the
    approval hold + record stores all mocked/isolated; asyncio task never
    started).
- **Validation:** **17 focused tests passed** (11 loop behaviour + 5
  duplicate-hold guard + 1 T13 safe-envelope guard); full Homelab suite
  **38 passed** (21 baseline + 17); full C07/Core intelligence suite
  **122 passed** (unchanged); full app suite **177 passed** (160 baseline + 17).
  `import app.main` clean; loop confirmed **disabled by default**.
- **Enabled on the live server (2026-09-07):** owner-authorized. systemd
  drop-in `rmt-control-center.service.d/cap04-loop.conf`
  (`RMT_HOMELAB_LOOP_ENABLED=true`). Enablement surfaced a **frozen-Core
  hold-persistence gap** — `approve_held_action` flips `hold.status` in memory
  but does not reliably persist the approval **hold** store, so holds
  approved/rejected days ago can read `pending` on disk after a restart. The
  duplicate-hold guard was hardened (above-Core, still read-only): a PENDING
  hold blocks a new remediation only while **still-actionable** — no terminal
  decision in the reliably-persisted approval **record** store, and not past its
  `APPROVAL_HOLD_TTL_SECONDS` TTL. Recorded as a frozen-Core note (owner
  consideration only). Redeployed 2026-09-07; the live loop then sat at `no_remediation` (2 clean cycles, no errors).
- **Live demonstration (real homelab, 2026-09-07):** owner-authorized. Isolated
  second instance on :8001 (systemd :8000 untouched). Fault-injected
  `uptime-kuma` (governed stop) → loop cycle held for approval
  (`manual_approval_required`, no mutation) → cooldown/flap guard fired →
  `POST /homelab/approve` → **executed** via the `docker` adapter
  (execution `40b3dce9…`) → above-Core Docker verification **`verified_success`**
  → loop observed recovery and stood down (`no_remediation`). Full correlated
  evidence bundle (approval / authorization / trace / audit / verification /
  Learn ids 275–278) recorded in `HANDOFF.md` (session note — CAP-04 first live
  demonstration). Result: **PASS**; approval retained throughout; no
  portainer/dozzle impact; no code change.
- **Core integrity:** diff confined to `app/homelab/**` + `app/main.py`; no
  `app/core/**` file modified; no second mutation boundary (routes through
  `execute_governed_action` via the existing entrypoint only); approval
  enforcement unchanged; learning append-only / read-only.
- **MCR / T13 — disposition recorded 2026-09-07** (`docs/RMT_T13_DISPOSITION.md`):
  **ACCEPT (with constraint) + BOUND + DEFER.** T13 is a policy-completeness
  gap in the MCR-EXP-3 simulation, not a live defect in RMT Core or CAP-01..04
  (verified: no Core dependency graph / no composition; CAP-04 ships one
  independent RESTART-only, approval-gated component). CAP-04 may be **enabled**
  only inside the *safe-enablement envelope* — every `REMEDIATION_POLICY` entry
  independent (no dependency edge) and `requires_approval=True` — enforced by
  `test_remediation_policy_within_cap04_safe_envelope`. The full fix (an
  above-Core dependency-cascade escalation pre-check that forces human approval
  when an allowed op would achieve a restricted effect via dependencies) is
  **assigned to CAP-05** and is **not** required to enable CAP-04 within the
  envelope.

---

## Index

| Capability | Status | Validation | Core integrity |
|---|---|---|---|
| RMT-CAP-01 — Homelab Operations (Learn closure) | COMPLETED & VERIFIED | 122 Core + 141 full | C01–C07 untouched |
| RMT-CAP-02 — Engineering Change-Impact & Risk Analysis | COMPLETED & VERIFIED | 14 focused + 155 full | C01–C07 untouched |
| RMT-CAP-03 — Homelab Remediation Approval-Continuation Learn Closure | COMPLETED & VERIFIED | 5 focused + 122 Core + 160 full | C01–C07 untouched; no frozen Core code modified |
| RMT-CAP-04 — Continuous Homelab Operational Loop | COMPLETED & VERIFIED; live-demonstrated + enabled on live 2026-09-07 | 17 focused + 38 Homelab + 122 Core + 177 full; live run PASS | C01–C07 untouched; no `app/core/**` modified; T13 disposition recorded; duplicate-hold guard hardened against frozen-Core hold-persistence gap |

**Boundaries:** No C08. No Core changes. No reopening of C01–C07. Above-Core
capabilities remain subordinate to RMT's governance architecture.
