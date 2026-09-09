# RMT — Tier 1 Homelab-Depth Batch (T1-2 / T1-3 / T1-4) — Proposal

**Status:** APPROVED 2026-09-09 (owner selected the "T1 homelab-depth batch" from
`docs/RMT_ABOVE_CORE_ROADMAP.md`; escalation driver = external script + read-only
route; this doc written then implementation proceeds).
**Classification:** Above-Core / operational + domain. No C08. **No frozen Core
change.** No reopening of C01–C07. Consistent with the standing owner directive
(2026-09-08): recorded frozen-Core gaps get an above-Core mitigation or an
explicit accept-and-record — never a freeze deviation.

Governing refs: `docs/RMT_ABOVE_CORE_ROADMAP.md` §5, `docs/RMT_T13_DISPOSITION.md`,
`docs/RMT_CAPABILITIES_EVIDENCE.md`, `STEWARD.md` §4, `AGENTS.md`.

---

## 0. Recon findings (verified against the repository, 2026-09-09)

| # | Finding |
|---|---|
| R1 | The homelab has **no inter-container dependency edges**. `portainer`, `dozzle`, `uptime-kuma` each need only the Docker daemon. `app/homelab/dependencies.py` records all three `[]` ("established: independent"); Core `COMPONENT_CONTEXTS` likewise. The T13 guard `escalate_for_dependency_cascade` is already correct and unit-proven (`test_dependency_guard.py`) to fire when an edge is added to either source. There is nothing real to "populate". |
| R2 | `app/homelab/dependencies.py::HOMELAB_DEPENDENCIES` is a **hardcoded dict**. Adding a real edge today needs a code edit + redeploy — inconsistent with every other P0–P2 knob (all env-overridable via a systemd drop-in). |
| R3 | `app/homelab/continuation.py:69` early-returns when `action.component not in REMEDIATION_POLICY` (`{"uptime-kuma"}`). The 5B live exercise (2026-09-07, target `dozzle`) recorded the resulting scoped-by-design gap: an agent proposal approved via `/homelab/approve` gets the above-Core Docker verify + executed-Learn closure **only** for `REMEDIATION_POLICY` components. All three homelab components have a `ComponentContext`; `verify_docker_execution` already works for any target. |
| R4 | `app/ops/notifications.py` = one fail-open `urllib` webhook (`RMT_NOTIFY_WEBHOOK_URL`), per-key de-dupe (`notify_min_interval_seconds`), called from `/homelab/remediate`, the CAP-04 loop, and the agent adapter. No payload shaping for a real channel; no escalation path. |
| R5 | **Frozen-Core constraint:** `APPROVAL_HOLD_TTL_SECONDS = 300`. A hold cannot be continued (`approve_held_action`) once expired; the CAP-04 read-side guard `_hold_is_still_actionable` agrees. So a "still unapproved after N minutes" escalation is only meaningful for N < 5 min, **or** the escalation must alert on a hold that **expired while still pending** (missed the approval window). The latter is the more valuable signal and is what T1-4 implements. |
| R6 | `ApprovalHold` carries `created_at` and `expires_at` (pydantic model, `app/core/intelligence/actions/approval.py`). Open-hold age + expiry are fully derivable from the durable stores — no in-process registry needed, and it survives a restart. |

---

## T1-2 — Operator-declarable dependency graph → T13 activatable without a redeploy

### Objective
Make a real homelab dependency edge declarable by an operator (systemd drop-in,
no code change), and demonstrate end-to-end that declaring one activates the T13
escalation and removing it de-activates it.

### In scope
- **`app/ops/ops_config.py`** — new `homelab_dependency_edges()` parsing
  `RMT_HOMELAB_DEPENDENCIES` in the form `"web:db;api:db,cache"`
  (`component:dep1,dep2` groups separated by `;`). Whitespace-tolerant;
  malformed groups skipped; read dynamically (drop-in edit + restart, same as
  every other knob). Empty / unset → `{}`.
- **`app/homelab/dependencies.py`** — `dependencies_of` / `dependents_of` /
  `resolved_map` union the static `HOMELAB_DEPENDENCIES` with the env edges. A
  new `dependency_sources()` returns `{"static": {...}, "env": {...}}` for
  read-only status. The static map stays exactly as it is (all-independent,
  with its explanatory docstring).
- **`app/agent/dependency_guard.py::dependency_view()`** — add a `sources` key
  (`static` / `env` / `core_context`) so `GET /agent/status.dependency_map`
  shows where each edge came from. Guard logic (`escalate_for_dependency_cascade`,
  `_dependents_of`) is **unchanged** — it already reads through `dependencies.py`.
- **Docs** — `docs/operations/CONFIG.md` (+ `DEPLOY.md` §6) document
  `RMT_HOMELAB_DEPENDENCIES`; `docs/RMT_T13_DISPOSITION.md` §4 and
  `docs/RMT_CAPABILITIES_EVIDENCE.md` gain the live-exercise record.
- **Live exercise** on `:8000`: set `RMT_HOMELAB_DEPENDENCIES` to a throwaway
  edge for a component pair, confirm `GET /agent/status` shows it (source `env`),
  drive `/agent/act` (or a direct `escalate_for_dependency_cascade` check) to
  show the allowed op is forced to approval, then unset + restart and show
  de-escalation. `portainer` / `dozzle` / `uptime-kuma` are not mutated.

### Boundary
`app/ops/ops_config.py`, `app/homelab/dependencies.py`,
`app/agent/dependency_guard.py` (`dependency_view` only), docs. The escalation
**rule** is untouched. No `app/core/**` change. No new mutation path. No second
authority path.

### Definition of Done
- `test_dependencies.py` (new) — env parsing (valid / malformed / empty),
  union with the static map, `dependency_sources` shape.
- `test_dependency_guard.py` — a new case: an **env** edge (not a monkeypatched
  dict item) makes `escalate_for_dependency_cascade` fire; unset → no-op.
- `GET /agent/status.dependency_map.sources` renders on the live server.
- Live exercise recorded (declare → escalates → remove → de-escalates), no
  homelab-container mutation.
- Full backend suite green.

### Size
S.

---

## T1-3 — Generalize `continue_remediation` Learn/verify attribution

### Objective
Run the above-Core Docker verification + executed-Learn closure for **any**
component that has a `ComponentContext`, not only `REMEDIATION_POLICY`
components — closing the recorded 5B-exercise finding.

### In scope
- **`app/homelab/continuation.py`** — replace the
  `action.component not in REMEDIATION_POLICY` early-return with
  `get_component_context(action.component) is None`. The `ComponentContext`
  registry (`app/core/intelligence/context/registry.py`, frozen, read-only) is
  the allow-list: it is the same notion the roadmap item names, it is
  deterministic, and it does not add a Docker dependency to the decision.
- All existing guards stay verbatim: augment only when
  `result["status"] == "executed"` **and** `result["execution_id"]` **and**
  `action.expected_outcome is not None`. Still records evidence *after* the Core
  has executed; no new authorization or execution path.
- A held action whose component has **no** `ComponentContext` (the operator
  `POST /execute` → hold flow, `some-other-service` in the tests) still passes
  through untouched — no Learn record, no Docker verification.
- Update the module docstring + the `REMEDIATION_POLICY` note in
  `remediate_and_verify` to say the continuation closure now covers any
  context-bearing component.

### Boundary
`app/homelab/continuation.py` only. No `app/core/**` change. Learning stays
append-only / read-only. Approval enforcement unchanged; a held action is never
auto-continued.

### Definition of Done
- `test_continuation.py` — new case: a `dozzle`-style component (has a
  `ComponentContext`, **not** in `REMEDIATION_POLICY`) held → approved →
  `verified_success` + one executed-Learn record correlated by
  `approval_id` / `execution_id`; and a state-mismatch variant.
- The existing `test_non_homelab_held_action_gets_no_learn_or_docker_verification`
  (component `some-other-service`, no context) still passes unchanged.
- Full backend suite green.

### Size
S.

---

## T1-4 — Held-action notification: real channel shaping + missed-approval escalation

### Objective
Turn `notify_held` from a log-only generic webhook into something that reaches a
real channel, and add an escalation for a hold that goes unactioned — driven by
an **external script** against a **read-only route** (the established D4 / O3
pattern; no new in-process background task).

### In scope
- **`app/ops/notifications.py` / `ops_config.py`** — `RMT_NOTIFY_FORMAT` =
  `generic` (default) / `slack` / `ntfy`. `generic` = today's JSON payload
  unchanged. `slack` = `{"text": "..."}`. `ntfy` = plain-text body + `Title` /
  `Priority` / `Tags` headers. One transport, still fail-open, de-dupe unchanged.
- **`app/ops/held_holds.py`** (new, read-only) — `open_holds_view()`:
  walk `_approval_service.approval_hold_storage.get_all()`, and for each
  `PENDING` hold report `approval_id`, `component` (`hold.action.component`),
  `action_type`, `created_at`, `age_seconds`, `expires_at`, `expired` (now >
  `expires_at`), `record_terminal` (approval record decision ∈
  {approved, rejected}), `actionable` (pending ∧ ¬expired ∧ ¬record_terminal),
  and `kind` / `granted_by` / `agent_id` from S3 provenance when present. Pure
  read; fail-open to `[]`.
- **`app/main.py`** — `GET /ops/holds` (operator-authenticated, read-only)
  returning `open_holds_view()`. Registered next to `/health` / `/metrics`.
- **`backend/scripts/rmt-escalate.sh`** — cron/timer script: `GET /ops/holds`,
  and for any hold that is (a) `actionable` and `age_seconds >
  RMT_NOTIFY_ESCALATION_AFTER_SECONDS` (default 180; must be < the 300 s Core
  TTL — the script warns if it isn't), or (b) newly `expired` while never
  approved, POST a one-time alert to `RMT_NOTIFY_ESCALATION_WEBHOOK_URL`.
  Already-escalated `approval_id`s tracked in a state file
  (`rmt-watchdog.sh` pattern) so each hold escalates once. No-op when the
  escalation URL is unset.
- **Docs** — `docs/operations/CONFIG.md` (new env vars),
  `docs/operations/DEPLOY.md` §6 (the cron line, alongside `rmt-watchdog.sh` /
  `rmt-heartbeat.sh`).

### Boundary
`app/ops/**` + one read-only route in `app/main.py` + one script + docs. No
`app/core/**` change. A notification / escalation failure never touches the
governed path (the route only reads; the script is out-of-process). No new
in-process background task. The 300 s Core hold TTL (R5) is a frozen-Core
constraint the design works within — recorded, not worked around.

### Definition of Done
- `test_held_holds.py` (new) — `open_holds_view` classification: an actionable
  pending hold; an expired-unapproved hold; a hold whose record is terminal
  (→ not actionable); fail-open to `[]` on a store error; S3 provenance fields
  surface when present.
- `test_notifications.py` — new cases: `slack` / `ntfy` payload shaping;
  `generic` unchanged; unknown format falls back to `generic`.
- `GET /ops/holds` — auth required (401 unauth), shape assertion (extend
  `test_health.py` or a small `test_ops_holds.py`).
- `rmt-escalate.sh` — dry-run against a throwaway instance with a seeded hold
  (documented in the session note, mirroring `rmt-smoke.sh`).
- Full backend suite green.

### Size
S.

---

## Sequencing & rollout

1. **T1-3** first (smallest, self-contained, closes a recorded finding).
2. **T1-2** (config + status + docs + live exercise).
3. **T1-4** (new module + route + script + docs).
4. One `HANDOFF.md` session note per item; `RMT_CONTEXT.md` §12 resync;
   `RMT_PRODUCTION_READINESS.md` / `RMT_ABOVE_CORE_ROADMAP.md` ticks.
5. **Deploy:** all three are inert-by-default (new env vars have safe defaults;
   `GET /ops/holds` is additive; the script is cron-only). A redeploy picks them
   up; the live exercise for T1-2 needs a drop-in + restart, owner-run.

## Non-goals

- No change to the T13 escalation rule or the effect/operation model.
- No auto-approval or auto-continuation anywhere.
- No new adapter, no second mutation boundary, no in-process escalation loop.
- No frozen-Core edit; the 300 s hold TTL is not changed.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

https://claude.ai/code/session_01JdakfNFaJQJSoPMKpdFPok
