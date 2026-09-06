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

## Index

| Capability | Status | Validation | Core integrity |
|---|---|---|---|
| RMT-CAP-01 — Homelab Operations (Learn closure) | COMPLETED & VERIFIED | 122 Core + 141 full | C01–C07 untouched |
| RMT-CAP-02 — Engineering Change-Impact & Risk Analysis | COMPLETED & VERIFIED | 14 focused + 155 full | C01–C07 untouched |
| RMT-CAP-03 — Homelab Remediation Approval-Continuation Learn Closure | COMPLETED & VERIFIED | 5 focused + 122 Core + 160 full | C01–C07 untouched; no frozen Core code modified |

**Boundaries:** No C08. No Core changes. No reopening of C01–C07. Above-Core
capabilities remain subordinate to RMT's governance architecture.
