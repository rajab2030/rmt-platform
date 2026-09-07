# RMT-CAP-04 — Continuous Homelab Operational Loop (Proposal)

**Status:** APPROVED 2026-09-07. Implementation to follow this scope exactly.
**Classification:** Above-Core / domain. No C08. No frozen Core change. No
reopening of C01–C07.

---

## 1. Objective

Turn the existing single-shot Homelab governed lifecycle into a **supervised,
periodic operational loop**: the frozen Core continuously acts as the intelligent
control plane for the real homelab, running
`Understand → Decide → Govern → Authorize → Execute → Verify → Learn` on a
cadence instead of one manual HTTP call at a time.

This is the stated primary objective in `RMT_CONTEXT.md` §12 and `STEWARD.md` §5.

## 2. What already exists (reused unchanged)

| Piece | Location | Role in CAP-04 |
|---|---|---|
| `remediate_component(component)` | `app/homelab/remediation.py` | The full governed lifecycle for one component. **The loop calls this and nothing lower.** |
| `continue_remediation(...)` | `app/homelab/continuation.py` | CAP-03 approval-continuation Learn closure. **The loop never calls this** — approval stays human. |
| `observe_container_state` / `verify_docker_execution` | `app/homelab/observer.py`, `verification.py` | Already invoked inside `remediate_component`. |
| `record_learning` → `remember` | `app/homelab/remediation.py` | Already fires per remediation. Loop adds records only for state transitions (quarantine / recovery). |
| Async task pattern | `app/collector.py` + `app/main.py` `lifespan` | The loop is started/stopped the same way `collect_metrics()` is. |

**Key point:** CAP-04 adds *cadence and supervision*, not a new mutation path.
The loop's only action verb is "call the existing governed entrypoint."

## 3. Design

### New module — `app/homelab/operational_loop.py`
- One `asyncio` task, started from `lifespan`, **disabled by default** (opt-in
  flag).
- Each cycle, for each component in `REMEDIATION_POLICY` (today: `uptime-kuma`
  only):
  1. Call `remediate_component(component)`.
  2. Classify the governed outcome (`no_remediation` / `no_observation` /
     `manual_approval_required` / `executed` / error).
  3. Update per-component loop state (last outcome, attempt count in window,
     cooldown-until, quarantine flag).
  4. Append a bounded in-memory cycle record.
- **Guardrails:**
  - **Approval retained** — a `manual_approval_required` outcome is recorded and
    surfaced; the loop does **not** continue it. A human still calls
    `POST /homelab/approve`.
  - **Flap guard / backoff** — after *N* failed-or-held remediation attempts for
    a component within window *W*, the loop **quarantines** that component and
    stops attempting it until cleared (prevents restart storms).
  - **Cooldown** — after any attempt for a component, skip it for a cooldown
    period so verify/settle completes.
  - **Single-flight** — cycles run sequentially; no overlap.
  - **Fail-safe** — per-component and per-cycle `try/except`; a fault is recorded
    and the loop task stays alive. It never raises into the app.
  - **Quarantine clear** — automatic on sustained observed-healthy, plus a manual
    clear endpoint.

### New — `app/homelab/loop_config.py`
Module-level constants with env-var overrides (no Core settings-schema change):
`LOOP_ENABLED` (default `False`), `LOOP_INTERVAL_SECONDS` (default `120`),
`LOOP_FLAP_WINDOW_SECONDS`, `LOOP_MAX_ATTEMPTS_PER_WINDOW`,
`LOOP_COOLDOWN_SECONDS`.

### Modified — `app/main.py`
- `lifespan`: create/cancel the loop task alongside `collector_task`, gated on
  `LOOP_ENABLED`.
- New read-only route `GET /homelab/loop/status` — last cycle time, per-component
  state, counts.
- New routes `POST /homelab/loop/start` · `POST /homelab/loop/stop` ·
  `POST /homelab/loop/clear?component=` — operational control for demos.

## 4. Explicitly OUT of scope

- No expansion of `REMEDIATION_POLICY` (more components / non-RESTART actions) —
  separate change.
- No auto-approval or auto-continuation of held actions.
- No new adapter, no direct Docker calls, no adapter-selection logic beyond what
  `remediate_component` already does.
- No `app/core/**` change (no Core settings-schema change).
- No frontend.
- No change to decision / health / risk logic.

## 5. Core-integrity statement

- Diff confined to `app/homelab/**` + `app/main.py`.
- No second mutation boundary: the loop routes through `execute_governed_action`
  via the existing entrypoint only.
- Approval enforcement unchanged; `requires_approval=True` still holds.
- Learning stays append-only / read-only.
- Every loop-initiated remediation produces the same governed evidence (trace /
  audit / authorization / verification / Learn) as a manual
  `POST /homelab/remediate` today.

## 6. Relationship to the MCR / T13 finding

An autonomous loop is the context where T13 (a restricted effect reached via an
*allowed* dependency operation) matters most. CAP-04 **does not change the
policy/effect model** — only the cadence of invocation.

**Disposition recorded 2026-09-07** — `docs/RMT_T13_DISPOSITION.md`:
ACCEPT (with constraint) + BOUND + DEFER. T13 is not a live defect in CAP-04
(one independent RESTART-only, approval-gated component; no dependency graph).
CAP-04 may be **enabled** only inside the *safe-enablement envelope* — every
`REMEDIATION_POLICY` entry independent and `requires_approval=True` — enforced by
`test_remediation_policy_within_cap04_safe_envelope`. The full dependency-cascade
escalation fix is assigned to CAP-05. Enabling the loop within the envelope no
longer waits on a separate T13 decision.

## 7. Tests — `app/homelab/testing/test_operational_loop.py` (run-safe, all externals mocked)

1. Loop disabled by default → no task, no cycles.
2. Healthy component cycle → calls `remediate_component`, outcome
   `no_remediation`, no state change.
3. Critical + `requires_approval` → outcome `manual_approval_required`; loop
   records it, does **not** call `continue_remediation`; component enters
   cooldown.
4. Repeated held/failed outcomes exceed max attempts in window → component
   quarantined; later cycles skip it.
5. Cooldown honored → component skipped on the next in-cooldown cycle.
6. Per-component exception is caught → other components still processed, error
   recorded, task alive.
7. Recovery → quarantined component observes healthy → quarantine cleared,
   transition recorded via Learn.
8. `GET /homelab/loop/status` → read-only, returns per-component state, mutates
   nothing.
9. Single-flight → overlapping cycle invocations do not double-run.

## 8. Validation plan

- New focused tests pass.
- Full Homelab suite (21 + new) passes.
- Core intelligence suite: **122 passed** (unchanged).
- Full app suite: **160 + new** passes.
- `app.main` imports cleanly; `LOOP_ENABLED=False` confirmed by default.

## 9. Risks & mitigations

| Risk | Mitigation |
|---|---|
| Restart storm | Flap guard (quarantine after N/window) + cooldown |
| Overlapping cycles | Sequential await / single-flight |
| Loop crash takes down app | Per-component + per-cycle try/except; supervised task; never raises |
| Silent autonomy | Disabled by default; status endpoint; every attempt already yields governed evidence + Learn |
| T13 blast radius | Policy/effect model unchanged; RESTART-only, one component, approval retained |
| Evidence-store growth | Bounded in-memory cycle ring; Learn records only on state transitions |

## 10. Decisions (recorded at approval)

1. **Enable mechanism** — config flag default-off + `GET /homelab/loop/status` +
   `POST /homelab/loop/{start,stop,clear}` endpoints.
2. **Held actions** — the loop **never** auto-continues a hold; auto-execute
   happens only when the policy itself sets `requires_approval=False`, exactly as
   today.
3. **Quarantine clear** — automatic on sustained observed-healthy **and** a
   manual `POST /homelab/loop/clear` endpoint.
4. **T13** — disposition recorded (`docs/RMT_T13_DISPOSITION.md`):
   ACCEPT + BOUND + DEFER. CAP-04 enabled only within the safe-enablement
   envelope (independent + approval-gated policy entries); full fix assigned to
   CAP-05.
5. **Cadence default** — 120 s (collector refreshes metrics every 60 s).

---

🤖 Generated with [Claude Code](https://claude.com/claude-code)
