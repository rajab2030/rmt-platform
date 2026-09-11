# RMT-CAP-07 — Harden the Agent Surface Before Trusting It Further (C3) — Proposal

**Status:** APPROVED 2026-09-11. Implementation to follow this scope exactly.
**Classification:** Above-Core / domain. No C08. No frozen Core change. No
reopening of C01–C07.

---

## 1. Objective

`docs/RMT_IMPROVEMENT_ROADMAP.md` §5 C3: an operator sees exactly what an
agent proposal will do *before* approving it, and the agent surface is tested
against adversarial input as a standing, named gate — not the scattered
one-off coverage it has today.

**Why now:** the CAP-05 5B live exercise already hit a real
`grant_scope_mismatch` from nondeterministic LLM mechanism choice
(`HANDOFF.md`). The only guardrail today is allow-list validation *after* a
proposal is submitted. C2 (RMT-CAP-06) just added a second domain, which
doubles the space of things that can go wrong at the agent boundary — this is
the right moment to harden it before extending it further.

## 2. What already exists (reused unchanged)

| Piece | Location | Role here |
|---|---|---|
| `evaluate_action_policy` / `simulate_action` / `process_approval` | `app/core/intelligence/actions/{policy,simulation,approval_service}.py` (frozen) | **Already pure, already read-only, already exported.** `execute_governed_action` calls all three *before* anything is written to storage. This is the load-bearing discovery for this proposal: a preview can call the real frozen decision logic — not a heuristic guess — and stop before the first write. |
| `authority_store.check` | `app/agent/authority.py` | Already read-only (never consumes) — reused as-is. |
| `escalate_for_dependency_cascade` | `app/agent/dependency_guard.py` | Already read-only — reused as-is. |
| `propose_and_govern`'s `ActionRequest`-building logic | `app/agent/adapter.py` | The exact same construction, factored out so preview and the real path can never drift apart. |
| `MemoryRecord` / `remember` | `app/core/intelligence/memory/**` (frozen) | Append-only Learn capability, unchanged; the rationale addition is a new field in the `data` dict already passed to it. |
| `test_llm_semantic_injection_still_needs_approval`, `test_llm_invalid_target_never_reaches_governance`, T13 envelope guard | `app/agent/testing/**` | Existing adversarial-shaped tests, scattered across files by feature rather than gathered as a deliberate gate — this proposal consolidates and extends them. |

## 3. Design

### 3a. New — `app/agent/preview.py` (above-Core)

`preview_proposal(proposal: AgentProposal) -> dict`:

1. `AGENT_ENABLED` gate (same as `propose_and_govern`) → `"disabled"`.
2. Structural validation: empty `goal` or `target` → `"no_proposal"` (nothing
   to preview).
3. Build the exact same `ActionRequest` `propose_and_govern` would build
   (shared helper, not a duplicate).
4. Read-only authority check (`authority_store.check`, **never consumes**) and
   dependency-cascade check (`escalate_for_dependency_cascade`) — same calls
   `propose_and_govern` makes, same non-mutating guarantee.
5. Call the three pure Core functions above:
   `evaluate_action_policy(action)` → `simulate_action(action)` →
   `process_approval(action, policy_result, simulation_result)`.
6. Return the resolved `ActionRequest` fields, the authority check result, the
   escalation result, and the predicted governed outcome
   (`policy_allowed`, `risk_level`, `approval_mode` — `auto`/`manual`/`reject`
   — `approval_reason`). **Zero calls** to `execute_governed_action`,
   `hold_for_manual_approval`, `create_execution_authorization`, or any
   storage-writing function. No grant consumed. No hold. No trace/audit
   record. No Learn record.

### New route — `POST /agent/act/preview` (`app/agent/api.py`)

Same `ProposeBody` shape as `/agent/act`, same `rate_limit_agent` /
`require_operator` dependency (read-only doesn't mean unauthenticated — this
still reveals policy/risk internals about a proposal). Calls
`preview_proposal`, never `propose_and_govern`.

### 3b. Structured rationale — `app/homelab/remediation.py::record_learning`

**Finding:** today's Learn record for a remediation/proposal outcome
(`MemoryRecord.data`) captures `status` / `execution_id` / `approval_id` /
`docker_verification_status` / `confidence` — but **not** the actual reason
the action was proposed. The "why" lives only in the transient
`ActionRequest.reason` string, never in the durable evidence trail.

`record_learning` gains an optional `rationale: dict | None = None` parameter
(default `None` — every existing homelab call site unchanged). When passed
(only `app/agent/adapter.py`'s calls will pass it), `data["rationale"]` is set
to `{"goal": ..., "reason": ..., "mechanism": ..., "operational_context": ...}`
— a structured object, not a bare string, so a reader of the evidence store
can reconstruct *what was asked for and why* without cross-referencing a
separate log.

### 3c. New — `app/agent/testing/test_adversarial.py` (consolidated gate)

One parametrized suite, ~15 cases across four categories, each asserting the
outcome is a refusal or a forced hold — **never** `allow`/`executed`, and for
the refusal cases, `execute_governed_action` is asserted **never called**:

1. **Invalid mechanism / malformed proposal** — unknown mechanism string,
   empty goal, empty target → `invalid_proposal` / `no_proposal`, both via
   `/agent/act` and `/agent/act/preview`.
2. **Scope escape** — granted target A, proposed target B; granted operation
   X, proposed operation Y; grant already consumed; grant expired; a
   proposal target that string-appends onto a granted target
   (`"uptime-kuma; rm -rf /"` against a grant for `"uptime-kuma"`) proving
   the grant match is exact-string, not prefix/pattern → all `no_authority`.
3. **LLM prompt-injection shapes** (`llm_agent.py` path, model mocked) —
   prose-wrapped JSON, extra unsolicited fields, a goal string containing
   fake system/instruction markers, a target attempting path traversal
   (`../etc/passwd`), a mismatched goal/target pair (the existing semantic-
   injection case, moved here) → parse failure (`llm_error`/`invalid`) or
   still-held-for-approval, never auto-executed.
4. **Dependency-cascade probes** — an allowed op on a declared dependency of a
   restricted target, with a real edge configured → `escalated_hold`,
   `requires_approval` forced `True` even when the default would not require
   it; run at the `propose_and_govern` level (end-to-end), not just the
   guard function in isolation.

This becomes *the* named gate: `app/agent/testing/test_adversarial.py` is
what a future change to the agent surface must keep green, and it already
runs in CI on every push (A2 is done — no separate CI wiring needed).

## 4. Explicitly OUT of scope

- No change to what the LLM is allowed to do — it still only proposes.
- No autonomous loop, no new mutation path, no execution from preview.
- No new Core function, no `app/core/**` change — `evaluate_action_policy` /
  `simulate_action` / `process_approval` are reused exactly as
  `execute_governed_action` already uses them.
- No rate-limit or auth change beyond reusing the existing
  `rate_limit_agent` dependency on the new route.
- No UI. This is an API-level preview; a console is Phase D (P-B), not this.

## 5. Boundary

- `git diff --stat` confined to `app/agent/**`, `app/homelab/remediation.py`
  (the one optional new kwarg), `app/main.py` (route wiring) — no
  `app/core/**`.
- Preview never writes: no grant consumed, no hold, no authorization, no
  trace/audit/verification/Learn record.
- Existing `record_learning` call sites (homelab) byte-for-byte unchanged
  (new kwarg defaults to `None`).

## 6. Done when

- `POST /agent/act/preview` returns the resolved action + predicted outcome
  for a structurally valid proposal, and `no_proposal` / `invalid_proposal`
  for the rest (per the roadmap's literal wording).
- `app/agent/testing/test_adversarial.py` exists, is green, and runs in CI
  (already true once it's part of the suite — A2 is live).
- Full backend suite green; no `app/core/**` diff.

## 7. Tests

- `app/agent/testing/test_preview.py` — the preview function/route itself:
  matches `propose_and_govern`'s real decision for the same input (regression
  guard — preview must never drift from reality), never calls
  `execute_governed_action`/`hold_for_manual_approval`/any storage write,
  disabled-gate, structural-invalid cases.
- `app/agent/testing/test_adversarial.py` — the ~15-case consolidated gate
  described in §3c.
- `app/homelab/testing/test_remediation.py` — one regression case: the
  existing homelab `record_learning` calls produce byte-identical
  `MemoryRecord.data` (no `rationale` key) when the new kwarg is omitted.

## 8. Validation plan

- New tests pass; full suite (currently 480) grows and stays green.
- `ruff` (F, E9) clean; `import app.main` clean.
- CI run on push is green (A2's live gate — no extra step needed).
- A short live check (not a fault-injection drill — preview has no side
  effects to demonstrate live; local test coverage is the actual proof here).

## 9. Risks & mitigations

| Risk | Mitigation |
|---|---|
| Preview drifts from real decision logic over time | Both paths call the same `ActionRequest`-building helper and the same Core functions; a regression test asserts preview's predicted outcome matches `propose_and_govern`'s real one for the same input |
| Preview becomes a reconnaissance tool for an attacker probing grants | Same auth as `/agent/act` (`require_operator`); it reveals policy/risk shape, not secrets — matches the trusted-LAN-operator threat model already recorded |
| Rationale field grows into an unbounded free-for-all | Fixed, small schema (`goal`/`reason`/`mechanism`/`operational_context`); no arbitrary caller-supplied keys |
| Adversarial suite gives false confidence (covers only imagined attacks) | Explicitly scoped as a floor, not a ceiling — named, so it's the visible place to add the next real finding, not a closed box |

## 10. Decisions for the owner — APPROVED 2026-09-11

1. **Preview auth** — **APPROVED**: same `require_operator` gate as
   `/agent/act`.
2. **Rationale schema** — **APPROVED**: the fixed 4-field structured object
   in §3b.
3. **Adversarial suite scope** — **APPROVED**: the four categories in §3c as
   the initial floor, extensible later.
