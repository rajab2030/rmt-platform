# RMT — Frozen-Core Debt Register

**Status:** LIVING RECORD, created 2026-09-10 (roadmap item **A3**,
`docs/RMT_IMPROVEMENT_ROADMAP.md` §3).
**Classification:** documentation only. This file **tracks** frozen-Core gaps;
it is **not** a plan to modify the Core and creates no work.

---

## 1. Authority and rules

RMT Core is frozen at commit `46a4441` (C01–C07 closed; there is intentionally
no C08). Above-Core mitigation or explicit **accept-and-record** remains the
default disposition for a frozen-Core gap.

**Final owner freeze directive, 2026-09-15:** the temporary exceptional-change
procedure used for the generic domain-assessment and exact instruction/adapter-
binding amendment is closed. That amendment was implemented, passed its full
577-test gate, was accepted, and was immediately re-frozen at its approved
contract boundary. It is the sole amendment admitted under that procedure.

No future Core amendment, freeze deviation, new Core milestone, or C08 may be
proposed or implemented. A new scenario that the frozen Core cannot represent
must be preserved as evidence and handled above Core, deferred, or rejected; it
must not reopen Core. All product/domain implementation—including Budget
Control—must consume the frozen contracts without modifying `app/core/**`.
This applies the MCR admission rule in `MCR_SUPERVISORY_CONTRACT.md` §33: a
capability or domain that cannot comply with RMT's governing policies, rules,
architecture, and lifecycle does not belong to RMT.
The register's existing “trigger to revisit” fields now trigger reassessment of
the above-Core compensating control or acceptance decision only; they do not
authorize consideration of a Core change.

This register is the single place a reader can see the whole frozen-Core
liability at once: each row is a real gap, its current above-Core compensating
control, the risk that remains after that control, and the **written condition**
that would make the owner revisit it. Until such a trigger fires, every row is
**accepted as-is**.

Sources consolidated here: `RMT_CONTEXT.md` §14, `docs/RMT_CORE_ADAPTER_DECOUPING.md`
§9, `docs/RMT_B1_PROPOSAL.md` §6, `docs/RMT_IMPROVEMENT_ROADMAP.md` §7.
All `file:line` references are against the freeze commit / current working tree
and were verified on 2026-09-10.

## 2. How to read a row

| Field | Meaning |
|---|---|
| **Symptom** | the observable wrong behaviour, stated plainly |
| **Where** | frozen Core `file:line` — the code that cannot be changed |
| **Compensating control** | the above-Core code / process that makes the gap safe today, with its `file` |
| **Residual risk** | what is still wrong after the compensating control |
| **Trigger to revisit** | the concrete owner-owned condition under which this stops being "accepted" |

---

## 3. The register

### D1 — a resolved approval hold is not persisted as resolved

- **Symptom.** `approve_held_action` flips `hold.status` to `APPROVED` /
  `REJECTED` on the in-memory `ApprovalHold` and persists only the approval
  **record** store; it never writes the **hold** store back. After a process
  restart a hold that was approved or rejected reloads from the hold store as
  `pending`.
- **Where.** `app/core/intelligence/actions/approval_service.py:123`
  (`approve_held_action`); status mutated at `:163` / `:172` / `:185`;
  `approval_record_storage.update(...)` at `:173` / `:188`; **no**
  `approval_hold_storage.save(hold)` after the mutation (contrast
  `record_approval_decision` at `:118`, which does save its hold).
- **Compensating control.**
  (a) the approval **record** store is authoritative on resolution — consumers
  read the record, not the hold's `status`, for terminal state;
  (b) startup write-side reconcile
  `app/ops/reconcile.py::reconcile_holds_against_records` (E2) brings the hold
  store back into agreement with the authoritative terminal record — strictly
  bounded (it corrects a `pending` hold only when a terminal record contradicts
  it, never invents a resolution, fail-open);
  (c) the CAP-04 duplicate-hold guard cross-checks the record store + hold TTL
  read-side (`_hold_is_still_actionable`).
- **Residual risk.** Between a resolution and the next restart-plus-reconcile, a
  direct read of the hold store (`approval_holds.json`, or the `holds` table in
  `data/governance_evidence.db` after T0-1) shows `pending` for a resolved hold.
  A consumer that trusts the hold store's `status` without consulting the record
  store is wrong. Reconcile is fail-open — if it cannot run at startup, the hold
  store stays stale indefinitely.
- **Trigger to revisit (owner).** A domain where holds must be inspected
  **directly on disk** as the source of truth, or an environment where the
  startup reconcile cannot be relied on to run.

### D2 — a failed adapter execution produces no Core verification evidence

- **Symptom.** When the execution adapter itself fails, the frozen Core writes
  no `VerificationResult`. `AGENTS.md` §11 lists "executed but failed" as a
  distinguishable outcome, but the Core verify path runs only on the
  successful-execution branch.
- **Where.** `app/core/intelligence/verification/` (verify is invoked
  post-execution on the success path only). Recorded frozen-Core note,
  `RMT_CONTEXT.md` §14.
- **Compensating control.** E3 above-Core —
  `app/ops/execution_evidence.py::record_failed_execution_evidence` (`:65`)
  writes a distinct `adapter_execution_failed` status (`:53`), so a failed
  adapter execution is a first-class, queryable outcome, separate from
  `observation_unavailable` and `verification_failure`.
- **Residual risk.** `adapter_execution_failed` is a **status, not a rollback**
  — the Core does not attempt to return the target to its prior state on adapter
  failure. An auditor expecting compensating-transaction semantics on failure is
  not satisfied. Historical records predating E3 carry no evidence and are not
  rewritten (B1 non-goal).
- **Trigger to revisit (owner).** A domain that needs rollback /
  compensating-transaction semantics on adapter failure rather than a recorded
  status.

### D3 — the Core verifier resolves a trusted observer only for module `create`

- **Symptom.** `_resolve_trusted_observer` returns an observer **only** when
  `operation == "create"` and `parameters["module_name"]` is set (the C06
  module-registry authority). For every other governed operation
  `verifier.verify(execution_id, expected, observed=None)` returns
  `observation_unavailable` — by construction.
- **Where.** `app/core/intelligence/verification/service.py:49`
  (`_resolve_trusted_observer`; called at `:69`).
- **Compensating control.** **B1 (DONE 2026-09-10)** — the above-Core
  `app/ops/verification/` layer: an observer registry
  (`app/ops/verification/registry.py`) feeds `observe_container_state` to the
  **same** frozen `verifier.verify()` + `verification_storage.save()` for every
  wired `(adapter, operation)`, including the operator `POST /execute` route;
  `remove` is verifiable (`observe_container_state` now returns `absent` when
  the container is reachable-and-gone); and an in-memory **effective-status
  index** (`app/ops/verification/index.py`, `GET /ops/verifications`,
  4 `/metrics` counters) marks the Core `observation_unavailable`
  **superseded** where an above-Core assertion exists and raises a
  `verification_inconclusive` notification when nothing can be observed.
  (`app/homelab/verification.py` — the old single-path helper — was deleted.)
- **Residual risk.** The Core verifier *itself* still records
  `observation_unavailable` for every non-`create` operation; the above-Core
  layer supersedes it in the index but the raw Core record is unchanged. An
  auditor who requires the **Core verifier itself** to assert the
  post-condition would not accept the above-Core layer.
- **Trigger to revisit (owner).** A domain whose regulator / auditor requires
  **Core-level** (not above-Core) post-condition assertion.

### D4 — Docker-flavoured names remain in the frozen Core

- **Symptom.** Freeze-deviation #1 removed the Core's **concrete** Docker import
  from `platform_state`, but Docker-specific vocabulary still appears on Core
  surfaces: `PlatformStateProvider.get_docker_health()` / `DockerHealth` in the
  protocol; `runtime_engine: str = "docker"` as a default; `runtime_engine="docker"`
  hard-coded in the evolution module-change adapter; `"engine": "docker"` in the
  module-registry seed data; and the execution-adapter bootstrap still imports
  `app.docker_api`.
- **Where.**
  `app/core/platform_state/provider.py:26` (+ `:11`),
  `app/core/platform_state/service.py:80`,
  `app/core/module_factory/factory.py:14,28`,
  `app/core/evolution/adapters/module_change.py:44`,
  `app/core/module_registry/modules.json:10,34`,
  `app/core/intelligence/execution/adapters/bootstrap.py:9`
  (`from app.docker_api import ...`).
- **Compensating control.** `platform_state` consumes an **injected**
  `PlatformStateProvider` protocol — Docker is one implementation
  (`app/docker_provider.py`), swappable or absent with **no** Core edit; verified
  this session and earlier that Docker-down still boots and executes a governed
  action end-to-end (resolves to `simulation`). The remaining names are cosmetic
  given the injection seam; `bootstrap.py` is on the **adapter** side of the
  governed boundary.
- **Residual risk.** A second runtime adapter (k8s, cloud VM) would read against
  Docker-named fields — `get_docker_health()` returning that adapter's health is
  misleading, and `runtime_engine` defaulting to `"docker"` is a latent wrong
  default. The `app.docker_api` import in `bootstrap.py` names Docker in the Core
  execution-adapter registration path even when no Docker adapter is used.
- **Trigger to revisit (owner).** A second non-Docker runtime adapter where the
  naming actively misleads an operator or an auditor — at which point the D5
  decoupling scope is reopened for classification.

### D5 — adapter-decoupling coupling points "#2–#18" deferred

- **Symptom.** The owner classified the reported Core Docker/container couplings
  as **defects requiring a governed Core change**
  (`docs/RMT_CORE_ADAPTER_DECOUPING.md` §3), then under a REDUCE-SCOPE decision
  authorised only **#1** (`platform_state` provider extraction, done 2026-09-04)
  and **deferred** the rest of the range, labelled "#2–#18".
- **Where.** `docs/RMT_CORE_ADAPTER_DECOUPING.md` §9. The range is only
  **partially enumerated** in-repo — DECOUPING §2 concretely lists:
  - **#2** — `app/core/observability/`: "container metrics" naming
    (`save_container_metric` / `get_latest_container_metrics`, the
    `container_metrics` SQLite table);
  - **#3** — `app/core/self_management/service.py:67` (`m.runtime.container`) and
    `app/core/module_registry/schema.py:8` (`container: Optional[str] = None`).

  Items **#4–#18 are not written down anywhere in the repository** — "#2–#18" is
  a shorthand for "all remaining audit findings", not an enumerated list.
- **Compensating control.** The DECOUPING §5 hard boundaries hold — no C01–C07
  reopen, no C08, governed execution behaviour unchanged. The couplings are
  naming / model-shape, not behavioural; the governed
  `execute_governed_action → execution_engine.execute → adapter` boundary already
  isolates adapters. The frozen Core suite (≥122 passed) is the standing
  regression gate.
- **Residual risk.** (a) the deferred scope **cannot be fully audited** because
  #4–#18 were never enumerated — no reader can see the whole liability; (b) each
  remaining coupling is a latent obstacle the day a non-Docker adapter is added.
- **Trigger to revisit (owner).** Any deferred coupling becomes **load-bearing**
  for a new adapter — **or**, as a smaller first step, a decision to re-run the
  DECOUPING §4 read-only audit and enumerate #4–#18 so the deferred scope is
  actually knowable.

---

## 4. Recorded and closed — not debt

These `RMT_CONTEXT.md` §14 entries are listed here so every §14 note appears in
one place; they carry **no trigger** because there is nothing outstanding.

| Item | Disposition |
|---|---|
| `module_registry.register_module()` | Internal governed primitive — not a bypass, not a missing Core requirement. Recorded at C07 closure. |
| `execution/service.py::execute_action()` | Unreachable dead-code housekeeping; no C07 impact. |
| Committed HTTP-route test evidence (existing public routes only) | Recorded. |
| C07 freeze-deviation #1 — `platform_state` provider extraction | COMPLETED & verified 2026-09-04 (122 green). Residual **naming** carried forward as **D4**. |
| Final generic domain-assessment and exact instruction/adapter-binding amendment | SOLE FINAL EXCEPTION — implemented, full 577-test gate passed, accepted and re-frozen 2026-09-15. The exception procedure is closed; no future Core amendment is admissible. |
| G2 Core-boundary review record | PASS. |

---

## 5. Cross-references

- Linked from `RMT_CONTEXT.md` §14 and `docs/RMT_CORE_ADAPTER_DECOUPING.md` §9.
- Seeded by `docs/RMT_IMPROVEMENT_ROADMAP.md` §7 (A3) and `docs/RMT_B1_PROPOSAL.md`
  §6 (which adds the D3 row).
- When a new frozen-Core gap is recorded anywhere (a `HANDOFF.md` session note,
  `RMT_CONTEXT.md` §14), add a row here in the same change.
