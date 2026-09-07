# RMT-CAP-05 — Governed Agent Surface (AI Agent Governance) — Proposal

**Status:** **5A APPROVED & IMPLEMENTED 2026-09-07** (owner: "approve 5A now").
**5B (LLM agent) remains DRAFT / deferred** — a separate owner decision.
See `docs/RMT_CAPABILITIES_EVIDENCE.md` §CAP-05 for the 5A evidence record.
**Classification:** Above-Core / domain. No C08. No frozen Core change. No
reopening of C01–C07.
**Predecessors:** RMT-CAP-01/02/03/04 (completed; CAP-04 live-demonstrated
2026-09-07). MCR experiments `experiments/mcr*`;
`docs/MCR_ARCHITECTURAL_PRINCIPLE.md`, `docs/MCR_SUPERVISORY_CONTRACT.md`
(v0.1, not RMT authority docs). `docs/RMT_T13_DISPOSITION.md` (the T13
full-fix is assigned here).

---

## 1. Objective

Let an **autonomous agent** — a governed "child" in MCR terms — propose
consequential homelab operations and, when authorized, have them carried out
**only through the frozen RMT Core's single governed boundary**. CAP-05
implements the MCR child-contract surface (Identity, State, Intent, Decision,
Authority, Proposed Action, Outcome) on top of the existing governed lifecycle,
so the agent's **intent** — not just a tool name — is what governance sees and a
human approves.

Where CAP-04 drives the homelab on a timer, CAP-05 lets a *reasoning* actor
propose actions on demand under the same supervision.

**Scope is delivered in two clearly separated pieces:**
- **5A — the governed agent surface** (contract + entrypoint + authority model +
  T13 escalation), validated with a **deterministic reference agent**. This is
  the substance of the proposal.
- **5B — an optional LLM-backed agent adapter** (disabled by default, its own
  flag, uses the local Ollama already used by the MCR experiments). Governance,
  intent surfacing, authority, and T13 escalation are **identical** whichever
  agent produces the proposal — so 5B can be approved, deferred, or dropped
  without touching 5A.

Everything is **disabled by default** and opt-in.

## 2. What already exists (reused unchanged)

| Piece | Location | Role in CAP-05 |
|---|---|---|
| `execute_governed_action(action, adapter_name)` | `app/core/intelligence/actions/service.py` | The single governed mutation boundary. **The agent's proposal enters here and nowhere else.** |
| `ActionRequest` / `ActionType` / `ExpectedOutcome` | `app/core/intelligence/actions/models.py` | The governed action contract a proposal is translated into (required fields: `decision_id`, `component`, `action_type`, `reason`). |
| `resolve_adapter_name()` | `app/homelab/remediation.py` | Adapter selection (docker vs safe simulation). |
| `verify_docker_execution(...)` | `app/homelab/verification.py` | Post-execution verification against real Docker state. |
| `record_learning(...)` → `remember` | `app/homelab/remediation.py` | Append-only Learn records for agent-initiated outcomes. |
| Approval continuation | `app/homelab/continuation.py`, `POST /homelab/approve` | Held agent actions stay human-approved; never auto-continued. |
| `ComponentContext` incl. `dependencies` | `app/core/intelligence/context/` | Already carries a per-component `dependencies` list (**empty for all three homelab components today**). The T13 escalation rule reads this. |
| MCR child contract | `docs/MCR_SUPERVISORY_CONTRACT.md` §4–11 | The surface the agent layer implements. |
| CAP-04 safe-enablement envelope | `docs/RMT_T13_DISPOSITION.md` §3b | The agent operates inside the same envelope. |

**Key point:** CAP-05 adds an **agent-facing governed entrypoint and an
intent/authority surface** — it does **not** add a mutation path. A proposal is
translated into an `ActionRequest` and routed through `execute_governed_action`,
exactly like a Homelab remediation today.

## 3. Design

### New package — `app/agent/` (above-Core)

- **`app/agent/contract.py`** — the MCR child surface as dataclasses:
  - `AgentIdentity` — agent id, role, operational context, authority context.
  - `AgentIntent` — **goal** (e.g. "restore uptime-kuma availability") kept
    **separate from mechanism** (`restart` / `start` / …), plus target,
    reason, confidence.
  - `AgentProposal` — identity + intent + proposed `ActionType` + target +
    `ExpectedOutcome`.
  - `AgentOutcome` — governed result + verification + learn reference.
- **`app/agent/authority.py`** — capability ≠ authority. An in-memory grant
  store: grants are **single-use** (consumed on first ALLOW) and
  **time-limited** (TTL), scoped to operation + target. No grant → the proposal
  is denied before it reaches the governed boundary. (Mirrors MCR-EXP-3 T9.)
- **`app/agent/dependency_guard.py`** — **T13 closure.** Before routing an
  *allowed* proposal, walk `ComponentContext.dependencies`: if the proposed
  operation's effect, propagated through known dependencies, would achieve a
  *restricted* effect on another governed component, force
  `requires_approval=True` (escalate to human approval). Today every
  `dependencies` list is empty, so this is a no-op — but it is **in place**, so
  widening the homelab model later (populating `dependencies`, adding
  non-approval-gated operations) is safe by construction rather than by a
  future promise.
- **`app/agent/adapter.py`** — `propose_and_govern(proposal)`:
  1. Resolve + consume authority grant (deny if absent/expired/used).
  2. Dependency-cascade escalation (T13) — may set `requires_approval=True`.
  3. Translate `AgentProposal` → `ActionRequest` (reuse Homelab
     `ActionType` / `ExpectedOutcome`).
  4. Route through `execute_governed_action(...)` — the frozen Core boundary.
  5. On `executed`: `verify_docker_execution(...)` + `record_learning(...)`
     (same as `remediate_and_verify`). Held → recorded, **never**
     auto-continued.
- **`app/agent/reference_agent.py` (5A)** — a **deterministic** agent: given a
  component observation it emits an `AgentProposal` (RESTART when CRITICAL, else
  none). No model, no network. This is what 5A validates against.
- **`app/agent/llm_agent.py` (5B, optional, default-off)** — wraps a local
  Ollama model (the `experiments/mcr3` setup) behind `AGENT_LLM_ENABLED`.
  Produces an `AgentProposal` from a natural-language goal. **Cannot execute
  anything** — it only proposes; `propose_and_govern` does the rest. No
  arbitrary code execution; Claim C is **not** claimed.
- **`app/agent/api.py`** — routes (all opt-in):
  - `POST /agent/act` — submit an `AgentProposal` → governed lifecycle.
  - `GET /agent/status` — read-only: identity, last proposal/outcome, held items.
  - `GET /agent/authority` — read-only: current grants (what the agent may do).
- **`app/agent/loop_config.py`** — env constants, default-off: `AGENT_ENABLED`
  (`False`), `AGENT_LLM_ENABLED` (`False`), `AGENT_GRANT_TTL_SECONDS`,
  `AGENT_DEPENDENCY_ESCALATION` (`True`).

### Modified — `app/main.py`
- Register the `app/agent` router (additive only).
- No `lifespan` change beyond router registration — the agent is
  request-driven (no background task).

## 4. Explicitly OUT of scope

- No `app/core/**` change (no Core policy/effect-model change; no C08).
- No new mutation boundary — every agent action routes through
  `execute_governed_action`.
- No auto-approval or auto-continuation of held agent actions.
- No arbitrary code execution by any agent; the LLM agent only *proposes*.
- No expansion of `REMEDIATION_POLICY` / component set / operation classes
  (stays inside the CAP-04 safe envelope).
- No populating `ComponentContext.dependencies` — that is a separate, explicit
  change; CAP-05 only provides the guard that would act on it.
- No frontend, no new execution adapter, no direct Docker calls from the agent
  layer.
- 5B (LLM agent) ships **disabled**; enabling it is a separate owner decision.

## 5. Core-integrity statement

- Diff confined to `app/agent/**` + `app/main.py` (router registration).
- No second mutation boundary: a proposal becomes an `ActionRequest` routed
  through `execute_governed_action` only.
- Approval enforcement unchanged; `requires_approval=True` still holds and held
  actions are never auto-continued.
- Learning stays append-only / read-only.
- Every agent-initiated remediation produces the same governed evidence
  (trace / audit / authorization / verification / Learn) as
  `POST /homelab/remediate` today.

## 6. Relationship to the MCR / T13 finding

CAP-05 is the first capability that **operationalizes the MCR child contract**
for a reasoning actor, and it **discharges the T13 disposition**
(`docs/RMT_T13_DISPOSITION.md` §3c):

- `app/agent/dependency_guard.py` is the **above-Core dependency-cascade
  escalation rule** — when an *allowed* operation would achieve a *restricted*
  effect via `ComponentContext.dependencies`, it forces human approval.
- It changes **no Core policy or effect model**. It runs before
  `execute_governed_action`, in the agent layer.
- It is a **no-op today** (all `dependencies` lists are empty) but is now
  present, tested, and wired — so the CAP-04 safe envelope can later be widened
  deliberately (populate `dependencies`, add mixed operation classes) **with the
  T13 protection already in force**, instead of relying on the envelope guard
  test alone.
- Blast radius for the first cut stays bounded: RESTART-only, single configured
  component, human approval retained, disabled by default.

## 7. Tests — `app/agent/testing/` (run-safe, all externals mocked)

1. Agent disabled by default → `POST /agent/act` returns disabled; no mutation.
2. Allowed proposal + valid grant → governed ALLOW → executed → verified → Learn
   recorded.
3. Restricted proposal → HOLD (`manual_approval_required`); **not** continued;
   human approval required.
4. Denied proposal → DENY; no mutation; no adapter invocation.
5. Capability ≠ authority → agent has the tool but **no grant** → denied before
   the governed boundary.
6. Replay → single-use grant consumed; identical second proposal denied.
7. Grant expiry → expired grant → denied.
8. Intent ≠ mechanism → the same consequential effect proposed via a different
   `ActionType` is still governed (effect-based, not tool-name-gated).
9. **T13 escalation** — with a *seeded* dependency edge (test-only
   `ComponentContext`), an allowed op that would achieve a restricted effect via
   the dependency is escalated to `requires_approval=True`.
10. **T13 no-op today** — with the real (empty) `dependencies`, an allowed
    proposal is **not** escalated (no false positives).
11. `GET /agent/status` / `GET /agent/authority` → read-only; mutate nothing.
12. Per-proposal exception is contained → status endpoint stays alive; error
    recorded; no partial mutation.
13. Reference agent (5A) → CRITICAL observation → RESTART proposal;
    HEALTHY → no proposal.
14. (5B, only if approved) LLM agent disabled → `POST /agent/act` with a
    natural-language goal returns disabled; enabled + mocked model → produces a
    proposal that flows through the identical governed path.

## 8. Validation plan

- New focused tests pass.
- Homelab suite (**36**) and Core intelligence suite (**122**) unchanged.
- Full app suite (**175 + new**) passes.
- `import app.main` clean; `AGENT_ENABLED=False` and `AGENT_LLM_ENABLED=False`
  confirmed by default.
- Evidence-store parity: an agent-initiated executed remediation writes the
  same six evidence artifacts as a Homelab remediation.

## 9. Risks & mitigations

| Risk | Mitigation |
|---|---|
| Agent autonomy / unintended action | Governed boundary; approval retained; disabled by default; status + authority endpoints |
| T13 dependency cascade | `dependency_guard.py` escalation rule (in force, tested); envelope guard test still present |
| LLM nondeterminism / prompt injection (5B) | 5B disabled by default, own flag; agent only *proposes*; every proposal still passes policy/risk/approval; no code execution |
| LLM availability / cost (5B) | Local Ollama; 5B optional; 5A has no model dependency |
| Python boundary is convention, not guarantee (Claim C) | Documented (MCR-EXP-3 §15); agent cannot execute arbitrary Python; governed entrypoint only |
| Evidence-store growth | Bounded; Learn records on outcomes/transitions only |
| Silent autonomy | Disabled by default; every action yields governed evidence + Learn |

## 10. Decisions for the owner

1. **Scope** — approve **5A only** (governed agent surface + deterministic
   reference agent + T13 escalation) now, and treat **5B** (LLM agent) as a
   separate later decision? *(Recommended.)*
2. **Enable mechanism** — config flags default-off + `GET /agent/status` +
   `GET /agent/authority` + `POST /agent/act`.
3. **Held actions** — the agent **never** auto-continues a hold (same rule as
   CAP-04).
4. **T13 closure** — delivered as the above-Core `dependency_guard.py`
   escalation rule (no Core change); no-op until `ComponentContext.dependencies`
   is deliberately populated.
5. **Authority model** — single-use, time-limited, operation+target-scoped
   grants; capability never implies authority.
6. **Envelope** — the agent stays inside the CAP-04 safe-enablement envelope;
   widening it (dependencies, mixed operation classes) is a separate change,
   now protected by the T13 guard.

---

*Draft for owner review. No implementation begins until the owner selects the
scope (5A only, or 5A + 5B) and authorizes it.*

🤖 Generated with [Claude Code](https://claude.com/claude-code)
