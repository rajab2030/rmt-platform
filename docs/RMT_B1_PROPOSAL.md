# RMT — B1: Strengthen the Verify Stage (above-Core observer layer) — Proposal

**Status:** **DONE (2026-09-10) — both slices implemented.** Owner answered §7
Q1–Q4 (recorded there); B1a and B1b were implemented against the recon in
`docs/RMT_B1b_RECON.md` (owner-approved plan, both decisions taken as
recommended: in-memory index; `rmt_verifications_total` left raw). Completion
notes: §9 (B1a), §10 (B1b). (DRAFT rev-2 history: 2026-09-09, owner selected B1
from `docs/RMT_IMPROVEMENT_ROADMAP.md` for scoping.)
**Classification:** Above-Core / operational. No C08. **No frozen Core change.**
No reopening of C01–C07. Consistent with the standing owner directive
(2026-09-08): a recorded frozen-Core gap gets an above-Core mitigation or an
explicit accept-and-record — never a freeze deviation. §6 records the gap this
exposes.

Governing refs: `docs/RMT_IMPROVEMENT_ROADMAP.md` §4 (B1),
`docs/RMT_ABOVE_CORE_ROADMAP.md`, `AGENTS.md` §11 (distinguishable outcomes),
`STEWARD.md` §4, `docs/RMT_CAPABILITIES_EVIDENCE.md`,
`docs/RMT_PRODUCTION_READINESS.md` (O4 metrics).

---

## 0. Recon findings (verified against the repository, 2026-09-09)

| # | Finding |
|---|---|
| R1 | **The Core Verify stage is wired for exactly one operation.** `app/core/intelligence/verification/service.py::_resolve_trusted_observer` returns an observer **only** when `operation == "create"` and `parameters["module_name"]` is set (the C06 module-registry authority). For every other governed operation it returns `None`, so `verifier.verify(execution_id, expected, observed=None)` returns `observation_unavailable`. By construction; the file is frozen Core. |
| R2 | **An above-Core observer already exists and feeds the same boundary.** `app/homelab/verification.py::verify_docker_execution(execution_id, expected, target)` calls the **frozen** `verifier.verify()` and the **frozen** `verification_storage.save()`, fed by `app/homelab/observer.py::observe_container_state(target)` — a read-only `get_containers()` lookup returning `ObservedState(source="docker", state=<container.status>)`, or `None` when it cannot observe. Not a parallel verification system. |
| R3 | **`container.status` is the Docker SDK status string** (`app/docker_api.py::get_containers`): one of `created`, `restarting`, `running`, `removing`, `paused`, `exited`, `dead`. The verifier compares it verbatim against `ExpectedOutcome.expected_state` (`"running"` for a restart). |
| R4 | **The above-Core observer is wired into 3 executed paths, not the generic one.** Non-test callers of `verify_docker_execution`: `app/homelab/continuation.py:92` (`/homelab/approve`), `app/agent/adapter.py:154` (agent), `app/homelab/remediation.py:174` (`/homelab/remediate`). It is **not** called from the generic governed `POST /execute` route — `app/main.py::execute` returns whatever `execute_governed_action` produced, whose only verification is the Core `verify_execution` (→ `observation_unavailable` per R1). |
| R5 | **`POST /execute` carries no `ExpectedOutcome`.** `app/main.py::execute` builds `ActionRequest(..., parameters={"image": image} if image else {})` with no `expected_outcome`; `record_failed_execution_evidence` is even called with `expected=getattr(action, "expected_outcome", None)` = `None`. `remediation.py` by contrast builds `ExpectedOutcome(target, operation, expected_state=policy["expected_state"])` from `REMEDIATION_POLICY`. So a caller supplying the expected state from operation semantics is the established pattern; `/execute` just never does it. |
| R6 | **Two verification records per executed homelab/agent action, uncorrelated.** Both layers call `verification_storage.save()` with the same `execution_id`. Nothing in the frozen `VerificationResult` model says which layer wrote a record or that one supersedes another. Dev-host `verifications.json` (79 records): `adapter_execution_failed` 66 (E3), `verification_failure` 7, `observation_unavailable` 4, `verified_success` 2. In every recorded live exercise the Core wrote `observation_unavailable` and the above-Core observer wrote `verified_success` for the same execution. |
| R7 | **`remove` cannot currently be verified.** `observe_container_state` returns `None` both when docker is unreachable **and** when the container is genuinely gone — the verifier maps `None` → `observation_unavailable`, never `verified_success`. An `absent` expected state has no distinct observed value. |
| R8 | **Post-restart transient states.** A container observed immediately after `restart`/`start` can read `created` or `restarting` for a beat before `running`, which the verifier would score `state_mismatch`. The current single-shot observation has no settling allowance. |
| R9 | **Surfacing is partial and ambiguous.** `/metrics` (O4, `app/ops/metrics.py`) counts verification outcomes straight from `verification_storage`, so the double record (R6) inflates counts and a Core `observation_unavailable` is indistinguishable from a genuinely unverified execution. No alert on an inconclusive verification; no "executed vs verified" ratio. |
| R10 | **Test-isolation lesson (V1).** `app/ops/execution_evidence.py` previously bound its own `verification_storage` reference and had to be added to the isolation fixture. Any new module MUST resolve `verification_storage` through the module at call time, not bind a local alias at import. |
| R11 | **`result` shape.** `execute_governed_action(...)` returns a dict with `execution_id`, `success`, `status`, `status_detail`, `message`, `verification_status` (the Core status), `verification_reason`. All fields B1 needs at the `/execute` site are present. |

**Problem statement.** The lifecycle diagram promises Verify. In practice the
Core asserts a post-condition only for module creation (R1); for everything else
it fails safe to `observation_unavailable`. An above-Core Docker observer does
real observation but is wired into only some paths (R4), never the operator
path (R5), cannot verify removals (R7), has no settling allowance (R8),
produces a second uncorrelated record (R6), and "couldn't verify" reaches
no-one (R9).

---

## 1. Objective

Every **successfully executed** governed action resolves an above-Core observer
that asserts its post-condition where one exists; where none exists, the
execution is explicitly recorded as **unverified** and that fact is raised to
the operator and to `/metrics` — instead of a silent `observation_unavailable`.
The frozen Core verifier, storage, and records are reused unchanged.

Out of scope: blocked / denied / held outcomes (already distinguishable via
policy, trace, approval evidence) and failed-adapter outcomes (owned by E3,
`adapter_execution_failed`).

---

## 2. Design

### 2.1 Above-Core observer registry + entrypoint — new package `app/ops/verification/`

**`registry.py`**

- `register_observer(adapter_name: str, operation: str, factory: Callable[[str], Callable[[], ObservedState | None]])`
- `resolve_observer(adapter_name: str, operation: str, target: str) -> Callable[[], ObservedState | None] | None`
- Registration is data. Unknown `(adapter, operation)` → `None` (→ `unverified`,
  §2.4), never an error.

**`expected.py`**

- `expected_state_for(adapter_name: str, operation: str) -> str | None` — the
  single source of the operation→state mapping so every above-Core call site
  agrees:

  | adapter | operation | expected_state |
  |---|---|---|
  | `docker` | `start`, `restart`, `create` | `running` |
  | `docker` | `stop` | `exited` |
  | `docker` | `remove` | `absent` |

- Callers that already build an `ExpectedOutcome` (`remediation.py`) keep
  theirs; `/execute` and the agent path use this helper.

**`docker_observers.py`**

- Registers `observe_container_state` (via a small adapter that satisfies the
  factory signature) for `adapter_name="docker"` and operations
  `start`/`stop`/`restart`/`create`/`remove`.
- **Extends `app/homelab/observer.py::observe_container_state`** (above-Core, its
  own test): when docker **is** reachable and `get_containers()` succeeded but
  the target is not in the list, return `ObservedState(target, state="absent",
  source="docker")` instead of `None`. `None` is now reserved for "could not
  observe" (docker down, lookup raised). This makes `remove` verifiable (R7)
  and does not change any existing pass/fail — a present container is
  unaffected.

**`service.py`**

```
verify_executed_action(
    execution_id: str,
    *,
    adapter_name: str,
    operation: str,
    target: str,
    expected: ExpectedOutcome | None = None,   # caller-supplied wins
) -> VerificationResult
```

- Builds `expected` from `expected_state_for(...)` when the caller passed none.
- Resolves an observer from the registry. If none: writes **no** second record;
  records `effective_status = "unverified"` in the index (§2.3) and returns the
  Core-equivalent `observation_unavailable` result **without** re-saving it
  (the Core already saved one).
- If an observer resolves: **settling poll** — call the observer up to
  `RMT_VERIFY_OBSERVE_TIMEOUT_S` (default `5`, `0` = single-shot) at ~0.5 s
  intervals, stopping as soon as `observed.state == expected.expected_state`;
  otherwise use the last observation.
- Calls the **frozen** `verifier.verify(execution_id, expected, observed)` and
  the **frozen** `verification_storage.save(result)`.
- Before saving, prefixes `result.reason` with a machine-readable token:
  `"[layer=above_core adapter=docker supersedes=observation_unavailable] "` (the
  `supersedes=` clause only when a Core record with that status exists for the
  `execution_id`). `reason` is free text, not a frozen structural field — this
  keeps a raw evidence read unambiguous even without the index.
- Updates the index (§2.3).
- `verification_storage` is imported as a module and dereferenced at call time
  (R10).

### 2.2 Wire it in

- **Replace** the 3 `verify_docker_execution(...)` calls
  (`continuation.py`, `agent/adapter.py`, `remediation.py`) with
  `verify_executed_action(...)`. Delete `verify_docker_execution` (no external
  consumers) and update the 4 test files that reference it
  (`test_observer.py`, `test_continuation.py`, `test_e2e_docker.py`,
  `test_agent_governance.py`). *(Owner Q3: keep a one-release alias instead?)*
- **Add** to `app/main.py::execute` (above-Core route code), after the E3 call,
  when `result["status"] == "executed"` and `result["success"]`:
  `verify_executed_action(result["execution_id"], adapter_name=_resolve_adapter_name(), operation=operation, target=target)`.
  Add `above_core_verification_status` and `effective_verification_status` to
  the returned dict (additive; the Core `verification_status` key is untouched).

### 2.3 Effective-status index — new `app/ops/verification/index.py`

- Read-mostly sidecar keyed by `execution_id`:
  `{execution_id, action_id, adapter, operation, target, core_status,
  above_core_status, effective_status, verified: bool, notified_inconclusive:
  bool, updated_at}`.
- `effective_status` precedence:
  1. adapter failed (`success` false / `status != "executed"`) → deferred to E3;
     `effective_status = "adapter_execution_failed"`, `verified = false`, **not**
     counted as `unverified`.
  2. an above-Core record exists → its status
     (`verified_success` / `state_mismatch`).
  3. no above-Core observer but adapter is `module_change` → the Core status
     (real there per R1); `verified = (core_status == "verified_success")`.
  4. otherwise → `"unverified"`, `verified = false`.
- Storage: JSON (peer of `app/ops/` stores) now; migrates under A1 (SQLite).
- **Reconcile at startup** (after `app/ops/reconcile.py`): rebuild the index
  from `verification_storage.get_all()`. Reconcile is **silent** — it never
  fires notifications; it may set `notified_inconclusive=true` for
  pre-existing rows so the first live pass does not alert on history.

### 2.4 Surface "inconclusive"

- **`app/ops/notifications.py`** — when `verify_executed_action` finalises an
  executed action with `effective_status == "unverified"` and the index row's
  `notified_inconclusive` is false, call `notify_ops(event="verification_inconclusive",
  execution_id=..., action_id=..., adapter=..., operation=..., target=...)`
  (same fail-open webhook sink as O2/O3; low severity), then set the flag.
  Fired at most once per `execution_id`.
- **`app/ops/metrics.py`** — new counters, values from the index projection
  (not raw records), labelled by `adapter` and `operation` only (bounded
  cardinality):
  - `rmt_executed_actions_total{adapter,operation}`
  - `rmt_executed_actions_verified_total{adapter,operation}`
  - `rmt_executed_actions_unverified_total{adapter,operation}`
  - `rmt_executed_actions_state_mismatch_total{adapter,operation}`
- **`GET /ops/verifications`** — read-only, `require_operator`, mirrors
  `GET /ops/holds` (T1-4). Returns recent index rows; query params
  `?limit=` (default 50) and `?effective_status=`.
- **`GET /health`** — *(owner Q2)* optionally add advisory
  `unverified_executions_recent: <int>` (last N). Does **not** flip `status`.

---

## 3. Definition of Done

- **Implementation:** `app/ops/verification/{__init__,registry,expected,docker_observers,service,index}.py`;
  `observe_container_state` `absent` extension; 3 call-site swaps + `/execute`
  wiring; `verification_inconclusive` in `notifications.py`; 4 counters in
  `metrics.py`; `GET /ops/verifications` in `app/main.py`; startup index
  reconcile.
- **Integration:** the index reconcile runs in the `app/main.py` lifespan after
  the existing reconcile; `import app.main` clean; loop / agent / notify flags
  default unchanged.
- **Enforcement:** the frozen verifier is the only decider; the registry only
  resolves read-only observers; no new mutation path; approval enforcement
  untouched.
- **Validation:**
  - Unit — registry hit/miss; `expected_state_for` table; `observe_container_state`
    returns `absent` when reachable-and-gone, `None` when unreachable;
    `verify_executed_action` docker `restart` → `verified_success`, `stop` →
    `verified_success` vs `exited`, `remove` → `verified_success` vs `absent`,
    unknown adapter/op → `unverified` + one `notify_ops` + counter increment;
    settling poll returns early on match and tolerates one transient
    `restarting` reading; `/execute` above-Core path adds the two result keys;
    index precedence (all four branches incl. E3 deferral and `module_change`);
    reconcile rebuilds + is silent + suppresses history alerts; `notify_ops`
    de-dup per `execution_id`; `GET /ops/verifications` auth on/off + filter.
  - Isolation — new module added to the verification-storage isolation fixture
    (R10); no stray records written to the dev-host stores.
  - **`@pytest.mark.e2e`** — real `docker restart` of a disposable container
    **through `POST /execute`**, asserting `effective_verification_status ==
    "verified_success"` and one index row. This un-skips the real
    observe→verify path (today `verified_success` exists only from manual
    demos, 2 records total).
  - Suites — full backend suite green; **Core intelligence suite 122 unchanged**;
    `ruff` (F, E9) clean.
- **Evidence:** `docs/RMT_CAPABILITIES_EVIDENCE.md` §B1 — one live exercise:
  operator `POST /execute` restart of a real container → effective
  `verified_success`, correlated by `execution_id`; plus one deliberately
  unobservable action → `verification_inconclusive` notification + counter.

---

## 4. Boundary

- **No `app/core/**` change.** Frozen and reused unchanged: `verifier.verify`,
  `verify_execution`, `_resolve_trusted_observer`, `verification_storage`, and
  the `VerificationResult` / `ExpectedOutcome` / `ObservedState` models. No
  field added to any frozen model; `VerificationResult.reason` is free text, not
  a structural contract.
- **No second verification mechanism.** Same verifier, same storage. The
  registry resolves observers only — read-only, as the Core does internally.
- **The Core's own verification is never suppressed or edited.** Its
  `observation_unavailable` record still gets written; B1 adds an above-Core
  record (where an observer exists) and an effective-status index on top.
- `observe_container_state`'s `absent` extension is above-Core, covered by its
  own test, and changes no existing present-container result.
- No new mutation path; observers stay read-only; approval enforcement and
  learning untouched; `/health` `status` semantics unchanged.

---

## 5. Sequencing & rollout

- **Depends on:** nothing hard. A3 (frozen-Core debt register) should record §6
  but need not land first. A1 (SQLite) not required — the index starts as JSON
  and migrates with the other `app/ops/` stores.
- **Splittable:**
  - **B1a (S–M)** — `registry` + `expected` + `service` + the `absent`
    extension + swap the 3 call sites + wire `/execute` + unit tests. Value:
    operator-issued Docker actions get real verification; removals become
    verifiable; one seam for future domains.
    Files: `app/ops/verification/{registry,expected,docker_observers,service}.py`,
    `app/homelab/observer.py`, `app/homelab/verification.py` (delete),
    `app/homelab/continuation.py`, `app/homelab/remediation.py`,
    `app/agent/adapter.py`, `app/main.py`, 4 test files + new tests.
  - **B1b (S–M)** — `index` + reconcile + `verification_inconclusive` +
    4 counters + `GET /ops/verifications` + the e2e test.
    Files: `app/ops/verification/index.py`, `app/main.py` (route + lifespan),
    `app/ops/notifications.py`, `app/ops/metrics.py`, tests +
    `app/homelab/testing/test_e2e_docker.py`.
- **Rollout:** additive route + metrics; no new required env
  (`RMT_VERIFY_OBSERVE_TIMEOUT_S` defaults to 5). A redeploy picks it up; no
  live behaviour change until a governed action runs. `docs/operations/CONFIG.md`
  gets the one new knob; `DEPLOY.md` §6 the new route + metrics.
- **Size:** M overall.

---

## 6. Frozen-Core gap this exposes — accept and record (A3 register row)

`_resolve_trusted_observer` (`app/core/intelligence/verification/service.py`)
resolves a trusted observer only for `operation == "create"` with a
`module_name`. Every other governed operation records `observation_unavailable`
from the Core verifier by construction.

- **Disposition:** ACCEPT — not fixed (Core is frozen).
- **Compensating control:** B1's above-Core observer layer performs the real
  post-condition observation for every wired adapter/operation; the
  effective-status index marks the Core `observation_unavailable` superseded
  where an above-Core assertion exists; the Core record is retained for audit
  continuity.
- **Residual risk:** an auditor who requires the *Core* verifier itself to
  assert the post-condition would not accept the above-Core layer.
- **Trigger to revisit (owner):** a domain whose regulator/auditor requires
  Core-level (not above-Core) post-condition assertion.

---

## 7. Open questions for the owner — ANSWERED 2026-09-10

- **Q1 — settling poll default.** **DECIDED: keep 5 s.**
  `RMT_VERIFY_OBSERVE_TIMEOUT_S = 5` (`0` = single-shot). The operator path is
  low-volume and a correct verdict matters more than latency. *(The test suite
  sets `0` in `conftest.py` so mismatch cases don't poll; the dedicated
  settling-poll unit test sets its own small non-zero value.)*
- **Q2 — `/health` advisory field.** **DECIDED: keep `/health` minimal.** The
  "unverified executions" signal lives in `/metrics` + `GET /ops/verifications`
  (both B1b).
- **Q3 — `verify_docker_execution` removal.** **DECIDED: delete now.** No
  external consumers; the alias only defers the test churn. B1a deletes
  `app/homelab/verification.py` and updates the referencing test files
  (`test_observer.py`, `test_continuation.py`, `test_integrated.py`,
  `test_e2e_docker.py`, `test_agent_governance.py`) + the
  `app/engineering/repo_index.py` curated inventory.
- **Q4 — inconclusive severity.** **DECIDED: low-severity `notify_ops` line.**
  "We executed and could not confirm" is exactly what an operator should see.
  *(Implemented in B1b, alongside the effective-status index.)*

---

## 8. Non-goals

- Fixing the Core observer resolution (frozen; §6).
- A verification mechanism separate from `verifier.verify`.
- Observers that do anything but read state.
- Verifying non-executed outcomes (blocked / denied / held) or failed-adapter
  outcomes (E3 owns `adapter_execution_failed`).
- Rewriting the ~66 historical `adapter_execution_failed` records — the index is
  built forward and by reconcile, not by rewriting history.
- New execution adapters or domains — that is roadmap C2 / D-1; B1 only builds
  the observer seam they will register into.

---

## 9. B1a completion note (2026-09-10)

Implemented. **No `app/core/**` change** (verified: `git diff` touches no
`app/core/` path). Frozen `verifier.verify`, `verification_storage`, and the
`VerificationResult` / `ExpectedOutcome` / `ObservedState` models are reused
unchanged.

**New — `app/ops/verification/`:**
- `registry.py` — `register_observer` / `resolve_observer`; `(adapter, operation)`
  → factory. Unknown pair → `None`, never an error.
- `expected.py` — `expected_state_for(adapter, operation)`; the §2.1 table
  (`docker`: start/restart/create→`running`, stop→`exited`, remove→`absent`).
- `docker_observers.py` — registers `observe_container_state` (via a factory
  adapter) for `docker` × {start, stop, restart, create, remove}.
- `service.py` — `verify_executed_action(execution_id, *, adapter_name,
  operation, target, expected=None)`: builds `expected` from the table when the
  caller passes none; resolves an observer; **settling poll**
  (`RMT_VERIFY_OBSERVE_TIMEOUT_S`, default 5, `0` = single-shot, ~0.5 s
  interval, early-return on match); calls the frozen verifier + storage;
  prefixes `result.reason` with
  `[layer=above_core adapter=<name> supersedes=observation_unavailable]` (the
  `supersedes=` clause only when a Core record with that status already exists
  for the `execution_id`). No observer → returns an `observation_unavailable`
  result and writes **nothing** (the Core already saved one). `verification_storage`
  is dereferenced through its module at call time (R10).

**Changed:**
- `app/homelab/observer.py::observe_container_state` — reachable-and-gone now
  returns `ObservedState(state="absent")`; `None` is reserved for "could not
  observe" (docker down / lookup raised). Makes `remove` verifiable (R7).
- `app/homelab/remediation.py`, `app/homelab/continuation.py`,
  `app/agent/adapter.py` — the 3 `verify_docker_execution(...)` calls now call
  `verify_executed_action(..., adapter_name="docker", operation=<action_type>,
  ...)`. `app/homelab/verification.py` **deleted** (Q3).
- `app/main.py::execute` — after the E3 call, an executed+successful operator
  action calls `verify_executed_action(adapter_name=_resolve_adapter_name(),
  operation=operation, target=target)` and the response gains
  `above_core_verification_status`. (`effective_verification_status` is B1b.)
- `conftest.py` — `RMT_VERIFY_OBSERVE_TIMEOUT_S=0` default so a suite
  `state_mismatch` case doesn't spend the 5 s budget.
- Test files updated for the deleted module + the R10 storage-module patch:
  `test_observer.py`, `test_continuation.py`, `test_integrated.py`,
  `test_e2e_docker.py`, `test_agent_governance.py`; `app/engineering/repo_index.py`
  and the `app/ops/execution_evidence.py` docstring re-pointed.
- New tests: `app/ops/verification/testing/test_service.py` (registry, table,
  `absent`, settling poll early-return + one transient reading, single-shot,
  reason token, `supersedes=`, no-observer-writes-nothing, restart/stop/remove
  `verified_success`, `state_mismatch`, caller-supplied `expected` wins) and
  `test_execute_route.py` (`/execute` surfaces the key; sim adapter writes
  nothing; failed adapter gets no above-Core verification).

**Validation:** full backend suite **433 passed** (`ruff` F/E9 clean; `import
app.main` clean); Core intelligence suite **134 passed**, unchanged by this work
(no `app/core/**` diff); `test_e2e_docker.py` (real `docker restart` of a
disposable container) **2 passed** through the new `verify_executed_action`.

**Deferred to B1b:** the effective-status index (§2.3), startup reconcile,
`verification_inconclusive` notify (§2.4, Q4), the 4 `/metrics` counters,
`GET /ops/verifications`, `effective_verification_status` on the `/execute`
response, and the through-`POST /execute` e2e.

---

## 10. B1b completion note (2026-09-10)

Implemented against `docs/RMT_B1b_RECON.md` (owner-approved plan). **No
`app/core/**` change.** Decisions taken as recommended: the index is an
**in-memory projection** (RB-3a); `rmt_verifications_total` is **left raw** and
four new index-projection counters are added alongside it (RB-6-i).

**New — `app/ops/verification/index.py`:** an in-memory, read-only projection
keyed by `execution_id` (`IndexRow`: `action_id, adapter, operation, target,
core_status, above_core_status, effective_status, verified, notified_inconclusive,
updated_at`). `effective_status` precedence exactly per §2.3 —
(1) any `adapter_execution_failed` record → deferred to E3, not `unverified`;
(2) an above-Core record → its status; (3) no above-Core + `module_change`
adapter → the Core status; (4) else → `unverified`. `rebuild()` groups
`verification_storage.get_all()` by `execution_id`, reads `adapter`/`action_id`
from the audit store, is **silent** (fires nothing) and marks every row
`notified_inconclusive=True` so history never alerts. `record()` upserts one row
from the live path; `view(limit, effective_status)` / `snapshot()` / `get()` /
`reset()`.

**`app/ops/verification/service.py`:** `verify_executed_action` gains
`action_id`; **both** branches (observer-resolved and no-observer) now end by
calling `index.record(...)` and, when the row's `effective_status == "unverified"`
and it has not been notified, firing one
`notify_ops(kind="verification_inconclusive", key=execution_id, …)` (adapted to
the real `notify_ops` signature — RB-1) then `index.mark_notified(...)` — at most
once per `execution_id`.

**Wired in:**
- the 4 call sites pass `action_id=` (RB-2 — the `"executed"` result dict has
  none);
- `app/main.py` lifespan calls `rebuild_verification_index()` after
  `archive_aged_evidence()` (fail-open);
- **`GET /ops/verifications`** — `require_operator`, `?limit=` (default 50) /
  `?effective_status=`, mirrors `GET /ops/holds`; `{"verifications": [...]}`,
  `[]` on error;
- `POST /execute` response gains `effective_verification_status` (next to B1a's
  `above_core_verification_status`);
- `app/ops/metrics.py` — 4 counters from the index snapshot:
  `rmt_executed_actions_total` / `_verified_total` / `_unverified_total` /
  `_state_mismatch_total`, labelled `{adapter, operation}`.

**Tests:** `app/ops/verification/testing/` — `conftest.py` (autouse index +
notify reset), `test_index.py` (rebuild precedence ×4 + silent/history-notified
+ `record` upsert + `view` filter/limit/order + `view` never raises),
additions to `test_service.py` (index row carries `action_id`; `unverified` →
exactly one `verification_inconclusive` + no re-notify on a second call;
`verified_success`/`state_mismatch` → no notify) and `test_execute_route.py`
(`effective_verification_status` surfaced), new `test_ops_verifications_route.py`
(auth 401/200, `?effective_status=` / `?limit=`, empty), `test_metrics.py`
addition (the 4 counters), and `test_e2e_docker.py`
`test_operator_execute_http_verified_through_index` — a real `docker restart`
through `POST /execute` → `effective_verification_status == "verified_success"`
+ one index row.

**Validation:** full backend suite **455 passed** (exit 0, ~8 min); `ruff`
(F, E9) clean; `import app.main` clean; Core intelligence suite **134 passed**,
unchanged (no `app/core/` diff); the e2e set (3 tests incl. the new
through-`/execute` one) **passed** against a real container.

**Not done (recorded B1b non-goals):** a durable SQLite index table (revisit
only if restart-durable `notified_inconclusive` is needed — RB-3);
re-basing `rmt_verifications_total`; rewriting historical records; a `success`
gate on `remediation.py`'s verify call (the index's rule 1 defers it to E3).
