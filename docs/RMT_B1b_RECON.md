# RMT — B1b Reconnaissance & Contract Review

**Status:** COMPLETE, 2026-09-10 (read-only pass; no code written). Precedes any
B1b implementation step per `STEWARD.md` §3 (working method: recon → verify →
propose → approve → implement).
**Classification:** Above-Core / operational. No C08. **No frozen Core change.**
**Purpose:** (1) retro-verify the landed **B1a** diff against the frozen
contracts; (2) verify the **B1b** design (`docs/RMT_B1_PROPOSAL.md` §2.3–§2.4,
§5) against the repository at `HEAD`; (3) surface the mismatches and the two
owner decisions B1b needs before it starts.

Governing refs: `docs/RMT_B1_PROPOSAL.md` (APPROVED by split; §9 = B1a
completion note), `docs/RMT_IMPROVEMENT_ROADMAP.md` §4 (B1),
`docs/RMT_FROZEN_CORE_DEBT.md` D3, `STEWARD.md` §3–§4, `AGENTS.md` §11.

Verified against working tree at commit `40ec3fc` ("RMT B1a …") + the four
docs-only commits before it.

---

## 1. Retro-verification — B1a landed diff vs the frozen contracts

**Result: CLEAN.** No frozen-Core contract is touched or depended on in a new
way.

| Check | Evidence | Verdict |
|---|---|---|
| No `app/core/**` file changed | `git diff-tree --no-commit-id --name-only -r 40ec3fc \| grep app/core/` → empty | ✓ |
| `verifier.verify(execution_id, expected: ExpectedOutcome \| None, observed: ObservedState \| None)` | `app/ops/verification/service.py` calls it with exactly those types; `expected` is an `ExpectedOutcome` or `None`, `observed` an `ObservedState` or `None` | ✓ |
| `verification_storage.save(VerificationResult)` / `.get_all()` | public `DurableStore` interface, unchanged; B1a uses only these | ✓ |
| `VerificationResult.reason` token-prefix mutation is contract-safe | grep for `.reason` under `app/core/` — the only consumers are `app/core/evolution/service.py:159` and `app/core/intelligence/actions/approval_service.py:223`, **both copy it through verbatim**; nothing parses it for structure. Proposal §4's "free text, not a structural contract" holds | ✓ |
| `ObservedState(state="absent")` is a legal value | frozen `verification/models.py` — `state: str = ""`, no enum of valid states | ✓ |
| Core intelligence suite unaffected | `pytest app/core/intelligence/testing` → 134 passed, and the diff touches no `app/core/` path | ✓ |

**Recorded deviation from the proposal's letter (not its intent).** Proposal
§2.2 implied the three homelab / agent call sites pass the *resolved execution
adapter* name to `verify_executed_action`. B1a passes literal
`adapter_name="docker"` for those three (the *observation* domain — homelab
remediation always observes Docker container state) and reserves
`_resolve_adapter_name()` for the generic `POST /execute` wiring only. This
preserves the pre-B1a `verify_docker_execution` behaviour exactly (the observer
resolved unconditionally for those flows, simulation execution adapter or not).
Tighter than the text; consistent with the intent. No further action.

---

## 2. B1b reconnaissance — findings against `HEAD` (2026-09-10)

### RB-1 — `notify_ops` signature mismatch  *(blocking; small)*

Proposal §2.4: `notify_ops(event="verification_inconclusive", execution_id=…,
action_id=…, adapter=…, operation=…, target=…)`.

Actual (`app/ops/notifications.py`):
`notify_ops(*, kind: str, detail: str = "", key: str = "", source: str = "")`.

- **Map:** `kind="verification_inconclusive"`, `key=execution_id` (the de-dupe
  discriminator within the kind), `detail=` a formatted string carrying
  `action_id` / `adapter` / `operation` / `target`, `source="verify_executed_action"`.
- **De-dupe is time-windowed, not permanent.** `notify_ops` suppresses a repeat
  of the same `(kind, key)` only within `RMT_NOTIFY_MIN_INTERVAL_SECONDS`
  (default 60 s). The proposal's "fired at most once per `execution_id`"
  guarantee must come from the index's `notified_inconclusive` flag
  (proposal §2.3 already specifies it) — `notify_ops` is belt-and-suspenders.
- Fail-open and "safe before a sink exists" (logs only when
  `RMT_NOTIFY_WEBHOOK_URL` is unset) already hold — no change needed there.

### RB-2 — the `"executed"` result dict carries no `action_id`  *(blocking; small)*

`app/core/intelligence/actions/service.py:187` — the executed branch returns
`{status, execution_id, status_detail, success, message, verification_status,
verification_reason}`. **No `action_id`** (only the *non*-executed branches
return `action_id`). Proposal R11 is accurate; §2.3's index row nonetheless
needs `action_id`.

- **Fix:** add `action_id: str | None = None` to `verify_executed_action` and
  pass it from all four call sites — the `ActionRequest` (`action.action_id`)
  or `hold.action.action_id` is in scope at every one
  (`main.py::execute`, `remediation.py::remediate_and_verify`,
  `continuation.py::continue_remediation`, `agent/adapter.py::propose_and_govern`).
- Alternative (rejected): correlate via `execution_audit_storage` by
  `execution_id` — an extra store read for data already in hand at the call site.

### RB-3 — index persistence: the proposal's "JSON peer, migrates under A1" is stale  *(owner decision)*

A1 (T0-1) is **done**. `DurableStore` now selects a backend by the path suffix
handed to `__init__`: `None` → in-memory, `.json` → atomic JSON file, `.db` →
a table in the shared `governance_evidence.db`. The proposal (pre-T0-1) said
"JSON now, migrates with the other `app/ops/` stores". Given B1b's own design
("read-mostly sidecar … **rebuild the index at startup** from
`verification_storage.get_all()`"), two clean options:

| | (a) in-memory projection | (b) SQLite table |
|---|---|---|
| What | rebuilt every startup from `verification_storage` + reason-token parse + audit lookup; `notified_inconclusive` lives for the process lifetime | `DurableStore` subclass, `_table="verification_index"`, in `governance_evidence.db` |
| Precedent | `app/ops/separation.py::_provenance`, `app/agent/authority.py` (both in-memory, rebuilt/short-lived by design) | the six governance-evidence stores |
| Cost | none — no new table, no migration, no isolation-fixture change | new table; E4 retention / E5 backup / E6 audit want awareness; `RMT_EVIDENCE_DB` isolation already handled by `conftest.pytest_configure` so test churn is small |
| Loses | "already notified" across a restart | nothing |
| Mitigation for the loss | reconcile is **silent** and sets `notified_inconclusive=true` for pre-existing rows anyway (§2.3), so a restart never re-alerts on history | — |

**Recommendation: (a).** It matches B1b's own "read-mostly sidecar, rebuilt at
startup" wording and the established above-Core in-memory precedent. Revisit only
if an operator needs the inconclusive-notified history to survive a restart.

### RB-4 — startup wiring  *(no issue; placement noted)*

`app/main.py::lifespan` order: `configure_logging` → S1 unauth-surface check →
`register_default_adapters` → `init_observability_storage` /
`init_intelligence_memory_storage` → `warn_on_capability_mismatch` →
**`reconcile_governance_stores()`** → **`archive_aged_evidence()`** →
`collector_task` → (opt-in) `operational_loop.start()`.

- B1b's index rebuild slots **immediately after `archive_aged_evidence()`** —
  it needs the E2-corrected holds and should reflect the retention-trimmed live
  store.
- Must be fail-open (log + swallow, never block startup) like every sibling
  step. Reconcile of the index is **silent** (fires no notification).

### RB-5 — `GET /ops/verifications` route  *(clean template exists)*

`GET /ops/holds` (`app/main.py:270`) is the exact mirror to copy:
`@app.get("/ops/holds")`, `Depends(require_operator)`, delegates to a read-only
`open_holds_view()` in `app/ops/held_holds.py`, returns `{"holds": [...]}`,
never 500s (`[]` on any error).

- B1b: `GET /ops/verifications` → `Depends(require_operator)` →
  `open_verifications_view(limit=50, effective_status=None)` (new, in
  `app/ops/verification/`), returns `{"verifications": [...]}`, `[]` on error.
  Query params `?limit=` (default 50) and `?effective_status=` per §2.4.

### RB-6 — `/metrics` counters  *(owner decision, minor)*

`app/ops/metrics.py::render_prometheus()` builds lines via
`_line(name, value, labels)`; every store read is wrapped
(`try/except: errors += 1` → `rmt_metrics_scrape_errors_total`).

- The existing `rmt_verifications_total{status}` reads `verification_storage`
  **raw**. After B1a a wired executed action can produce **two** records for one
  `execution_id` (Core `observation_unavailable` + the above-Core record), so
  this counter now double-counts those — proposal §R9's observation.
- **Decision:** (i) leave `rmt_verifications_total` raw (both layers) and add the
  four new `rmt_executed_actions*_total{adapter,operation}` counters from the
  **index projection** alongside it; or (ii) also re-base
  `rmt_verifications_total` on the index.
- **Recommendation: (i).** Changing the meaning of an already-published metric
  is a behaviour change for any existing scraper/dashboard; the four new
  counters are the accurate "executed vs verified" view B1b is for. New code is
  one more wrapped block importing the index.

### RB-7 — `adapter_execution_failed` deferral (index precedence rule 1)  *(no issue)*

`app/ops/execution_evidence.py::record_failed_execution_evidence` writes one
`VerificationResult` with status `adapter_execution_failed` (constant
`ADAPTER_EXECUTION_FAILED`) into `verification_storage` — bounded (real
execution attempts only), idempotent, fail-open. The index rebuild reads that
status straight from `verification_storage.get_all()` and applies §2.3 rule 1:
`effective_status="adapter_execution_failed"`, `verified=False`, **not** counted
as `unverified`.

### RB-8 — e2e "through `POST /execute`"  *(feasible; highest-risk B1b item)*

`app/homelab/testing/test_e2e_docker.py` currently drives
`execute_governed_action(...)` **in-process** (Python), not the HTTP route, and
isolates evidence stores by `monkeypatch`-ing the store-module singletons.

- The B1b e2e needs `TestClient(app)` + a real disposable container +
  `POST /execute?operation=restart&target=<probe>` (the operator path sets
  `requires_approval=False`, so it executes in one call), then asserts the
  response's `effective_verification_status == "verified_success"` and one index
  row.
- **Complication:** under `TestClient` the real `lifespan` runs (reconcile,
  retention, index rebuild, optional loop) and the evidence-store singletons
  bind at import — a `monkeypatch` inside the test is too late for anything the
  lifespan touched. Isolation should lean on `RMT_EVIDENCE_DB` (conftest already
  points the whole suite at a throwaway `governance_evidence.db`) rather than
  patching singletons.
- Still `@pytest.mark.e2e` (auto-skips without Docker). This is the fiddliest
  part of B1b; budget for it.

### RB-9 — no conflict with A3 / the debt register  *(one-line follow-up)*

B1b deepens D3's compensating control (the effective-status index marks the Core
`observation_unavailable` **superseded** where an above-Core assertion exists).
`docs/RMT_FROZEN_CORE_DEBT.md` D3 already names B1; update its compensating-control
line when B1b lands.

---

## 3. Contract surfaces B1b binds to

| Surface | File | B1b use | Contract status |
|---|---|---|---|
| `verifier.verify` / `verification_storage` | `app/core/intelligence/verification/` | read `get_all()` for the index rebuild | frozen; read-only use only |
| `VerificationResult.status` / `.reason` / `.execution_id` | frozen model | rebuild parses the `[layer=above_core …]` token B1a writes into `reason` | free-text `reason`; safe (see §1) |
| `notify_ops` | `app/ops/notifications.py` | `kind="verification_inconclusive"` (see RB-1) | above-Core; adapt call to the real signature |
| `execution_audit_storage` | `app/core/…/execution/storage.py` | optional `adapter` lookup by `execution_id` for the index row | frozen; read-only |
| `execute_governed_action` result dict | `app/core/…/actions/service.py` | `action_id` NOT present on the executed branch (RB-2) | frozen; thread `action_id` from the call site instead |
| `lifespan` startup sequence | `app/main.py` | index rebuild after `archive_aged_evidence()` | above-Core; fail-open |
| `GET /ops/holds` pattern | `app/main.py` + `app/ops/held_holds.py` | template for `GET /ops/verifications` | above-Core |
| `render_prometheus` | `app/ops/metrics.py` | +4 counters from the index (RB-6) | above-Core |
| `DurableStore` backend-by-suffix | `app/core/…/durable_store.py` | only if index option (b) chosen (RB-3) | frozen; public API |
| `conftest.pytest_configure` | `backend/conftest.py` | `RMT_EVIDENCE_DB` already isolated; `RMT_VERIFY_OBSERVE_TIMEOUT_S=0` already set by B1a | — |

---

## 4. Owner decisions required before B1b starts

1. **Index persistence (RB-3):** (a) in-memory projection rebuilt at startup
   *(recommended)*, or (b) a `verification_index` SQLite table in
   `governance_evidence.db`.
2. **`rmt_verifications_total` (RB-6):** (i) leave it raw and add the four new
   `rmt_executed_actions*` counters alongside *(recommended)*, or (ii) also
   re-base it on the index projection.

Everything else in §2 is a mechanical adaptation with a clear resolution.

---

## 5. Smallest bounded B1b change (for the plan, once §4 is answered)

- **`app/ops/verification/index.py`** — the effective-status index. With RB-3(a):
  `rebuild()` (from `verification_storage` + reason-token parse + audit lookup;
  silent; marks pre-existing rows `notified_inconclusive=True`),
  `record(execution_id, …)` (per-verify update), `mark_notified(execution_id)`,
  `view(limit, effective_status)`. Precedence exactly per proposal §2.3
  (E3 deferral → above-core record → `module_change` core → else `unverified`).
- **`app/ops/verification/service.py`** — `verify_executed_action` gains
  `action_id: str | None = None`; after the save (and in the no-observer branch
  B1a left as "record nothing"), update the index; when
  `effective_status == "unverified"` and the row is not yet notified, call
  `notify_ops(kind="verification_inconclusive", key=execution_id, …)` then
  `index.mark_notified(...)`.
- **4 call sites** pass `action_id=` (`action.action_id` /
  `hold.action.action_id`).
- **`app/main.py`** — index `rebuild()` in `lifespan` after
  `archive_aged_evidence()`; new `GET /ops/verifications` route; add
  `effective_verification_status` to the `/execute` response (next to the
  B1a `above_core_verification_status`).
- **`app/ops/metrics.py`** — one wrapped block, 4
  `rmt_executed_actions*_total{adapter,operation}` counters from the index.
- **Tests:** `app/ops/verification/testing/test_index.py` (precedence table incl.
  E3 deferral + `module_change`; rebuild is silent + suppresses history alerts;
  `view` filter/limit); additions to `test_service.py` (inconclusive → exactly
  one `notify_ops` + `mark_notified` de-dup; index updated in every branch),
  `test_execute_route.py` (`effective_verification_status` key), a
  `GET /ops/verifications` auth-on/off + filter test, `test_metrics.py`
  (4 counters); the e2e-through-`/execute` test (RB-8).
- **Docs:** `docs/RMT_B1_PROPOSAL.md` §10 (B1b completion note),
  `docs/RMT_IMPROVEMENT_ROADMAP.md` B1 tick,
  `docs/RMT_FROZEN_CORE_DEBT.md` D3 line,
  `docs/RMT_CAPABILITIES_EVIDENCE.md` B1b section + the live exercise,
  `docs/operations/DEPLOY.md` §6 (new route + metrics, per proposal §5).

**Size: M** (proposal said S–M).

---

## 6. Boundary (unchanged from B1)

- No `app/core/**` change. Frozen verifier / storage / models reused unchanged.
- No second verification mechanism; the index is a read-only projection.
- No new mutation path; observers stay read-only; approval enforcement and
  learning untouched; `/health` `status` semantics unchanged (Q2: no advisory
  field).
- The Core's own `observation_unavailable` record is never suppressed or edited;
  the index marks it *superseded*, it does not delete it.
