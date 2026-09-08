# RMT-D4 — Financial / Approval Control (Banking Risk · Budget Control) — Proposal

**Status:** **DRAFT rev-2 (2026-09-08) — for owner review. Not authorized. No
implementation begins until the owner approves the scope.**
**Classification:** Above-Core / domain product. No C08. No reopening of
C01–C07. See **§9** for the one open Core question (`ActionType`).
**Source:** `docs/RMT_ABOVE_CORE_ROADMAP.md` §6 **D-4** (Financial / Approval
Control). This proposal scopes that roadmap item into an implementable
capability.

**Dependency status (updated 2026-09-08):**

| Dep | State | Note for D-4 |
|---|---|---|
| **S3 — separation of duties** | **DONE** (`b391293`, above-Core, `app/ops/separation.py`) | What shipped is *approver ≠ grantor* for **agent-originated** holds. D-4 holds are **not** agent-originated → they hit `not_agent_originated` and pass straight through. **D-4 must extend S3**, not just consume it: record provenance for `/finance/propose` (proposer = the operator), and enforce *approver ≠ proposer* **and** *approver-1 ≠ approver-2*. `separation.py`'s provenance store was built generic for this. |
| **E3 — failed-execution evidence** | **DONE** (`111b108`, above-Core, `app/ops/execution_evidence.py`) | A failed adapter execution now writes a distinguishable `adapter_execution_failed` verification record. Safety-table row 3 residual is closed. D-4 inherits it for free (wire the helper into the finance adapter path). |
| **E4 / E5 — evidence retention + backup/restore** | see P1 status | For a **simulated-ledger demo**, the JSON stores are adequate. Beyond a demo, financial evidence needs E4 (bounded stores) + E5 (backup/restore) closed first — financial records carry the highest durability bar of any domain. **Hard gate for anything past the demo.** |
| **Dual approval (M-of-N)** | **does not exist** | The Core has **no** dual/M-of-N approval primitive — `approve_held_action` is single-shot. Tier 2 needs a new above-Core approval-aggregation layer. Scoped in **§3a**. This is the real new engineering in D-4. |

---

## 1. Objective

Apply the **frozen RMT governed lifecycle** to money and limit changes —
disbursements above a threshold, credit/position-limit changes,
risk-parameter / model-parameter updates, and budget allocations — so that each
is policy-checked, risk-rated, approved, authorized, executed once through the
single governed path, verified afterward, and permanently evidenced.

The proof of the freeze: **D-4 lands with zero `app/core/**` edits.** It is a
`domain module + adapter + policy set` consuming the existing governed boundary
(`execute_governed_action`).

## 2. What already exists (reused unchanged)

| Piece | Location | Role |
|---|---|---|
| `execute_governed_action` | `app/core/intelligence/...` | The single governed mutation boundary. **D-4's only execution path.** |
| `ActionRequest` / action policy / risk | Core | Policy gate + risk assessment, inherited unchanged. |
| Approval / hold / continuation | Core | Manual-hold + executable continuation for the risky subset. |
| Durable evidence (authorization / approval / audit / trace / verification / learn) | Core | The audit chain D-4 relies on. |
| `require_operator` + `OperatorIdentity` | `app/ops/auth.py` | Authenticated operator identity (S1/S2-lite, live). |
| `notify_held` | `app/ops/notifications.py` | Held-action alerting (O2, live). |
| CAP-04 / CAP-05 patterns | `app/homelab/`, `app/agent/` | The reference shape for a domain module + adapter + policy set. |

**Key point:** D-4 adds a **domain module and an adapter**, not a mutation path
and not a new governance surface. Every financial action becomes an
`ActionRequest` → `execute_governed_action` exactly like any other governed
action.

## 3. Design

### New — `app/finance/` (above-Core domain module)

- **`contract.py`** — `FinancialAction`:
  - `action_type`: `disbursement` | `limit_change` | `risk_parameter_update` |
    `budget_allocation`.
  - `amount` (decimal), `currency`, `target` (account / limit / parameter id),
    `reason`, `requested_by` (operator identity).
- **`policy.py`** — threshold-tier policy (declarative, config-driven):
  - **Tier 0 (below threshold):** auto-approve (no hold).
  - **Tier 1 (above threshold):** hold → single human approval.
  - **Tier 2 (top tier / any destroy-like or irreversible op):** hold → **dual
    approval** (2 distinct operators) **and** separation of duties
    (approver ≠ proposer, approver-1 ≠ approver-2). Dual approval is **not** a
    Core primitive — it is an above-Core aggregation layer; see **§3a**.
  - Thresholds and tiers come from config, not code (aligns with P-A
    policy-as-configuration direction).
- **`risk.py`** — risk inputs: amount, tier, irreversibility, environment tag
  (prod vs sandbox). Feeds the Core risk assessment.
- **`adapter.py`** — `FinancialLedgerAdapter`:
  - `execute` = post the entry / apply the limit change to the ledger/limit
    system.
  - `verify` = read back the posted entry / effective limit and assert it
    matches the authorized intent.
  - For the first demo, the "ledger" is a **simulated in-memory ledger** behind
    the adapter interface (same pattern as the `simulation` execution adapter),
    so the demo needs no real banking system. A real ledger/limit system can be
    swapped in behind the same adapter interface later.
- **`api.py`** — routes:
  - `POST /finance/propose` — submit a `FinancialAction` → governed lifecycle →
    returns `allow` / `hold` / `escalated_hold` / `deny`.
  - `POST /finance/approve` — approve a held financial action (authenticated,
    S3-enforced).
  - `GET /finance/status` — read-only: outstanding holds, recent decisions.
  - All mutating routes behind `require_operator` (S1, live).

### Modified
- `app/main.py` — register the `app/finance` router (one import + one
  `include_router`). No `app/core/**` change.
- `app/ops/` — S3 enforcement (approver ≠ proposer) if not already closed by
  the time D-4 lands.

### Not modified
Any `app/core/**` file — **subject to the `ActionType` question in §9.** The
Core's governed boundary, risk, approval, verification, and evidence are
inherited unchanged; D-4's *financial* policy (tier selection, single vs dual
approval) runs **above-Core** before `execute_governed_action`, exactly as the
agent surface's T13 escalation does, and the Core then applies its own generic
policy/risk pass on top.

## 3a. Dual approval (Tier 2) — above-Core aggregation

The Core resolves a hold in **one** `approve_held_action` call and the hold
TTL is **`APPROVAL_HOLD_TTL_SECONDS = 300`**. Two designs:

**Option D1 — Core hold, above-Core aggregation (recommended).**
Tier 2 `/finance/propose` → `execute_governed_action(requires_approval=True)` →
Core creates the hold. D-4 records in its own `FinancialHold` store that this
`approval_id` needs **2 distinct approvers**. First `/finance/approve` → D-4
records approver 1, does **not** call the Core continuation. Second
`/finance/approve` by a **different** operator (separation-checked) → D-4 calls
`approve_held_action` **once**. Core evidence shows one approval event; D-4's
store holds the two-approver detail, correlated by `approval_id`.
*Risk:* both approvals must land inside the 300 s window. Acceptable for
pre-coordinated high-value approvals and for the demo; a longer finance-specific
TTL would be a Core config change (rejected — see §9).

**Option D2 — pre-Core aggregation.**
Tier 2 `/finance/propose` → D-4 records a pending `FinancialHold`, does **not**
call the Core yet. Two `/finance/approve` calls → on the second, D-4 submits to
`execute_governed_action` with the approvals already obtained. *Rejected:* the
Core hold/approval evidence never exists for the risky tier — the opposite of
what D-4 is for.

**Chosen: D1.** New above-Core state: `app/finance/holds.py` (`FinancialHold`
= `{approval_id, action, tier, required_approvers, approvals: [(operator, at)],
proposed_by, created_at}`), in-memory (like `authority_store` / the S3
provenance store). Reuses `app/ops/separation.py` for the identity checks.

## 4. Explicitly OUT of scope

- **Not transaction execution on a latency path.** RMT governs the
  *authorization and record*; the ledger stays the system of record. RMT is not
  a payment rail.
- **No new mutation path** — every financial action goes through
  `execute_governed_action` only.
- **No real banking system integration in the first demo** — the ledger is
  simulated behind the adapter interface. Real integration is a later,
  separately-scoped step.
- **No `app/core/**` change; no C08.**
- **No auto-approval of the top tier** — Tier 2 always requires dual approval +
  separation of duties.
- **No high-frequency / real-time trading** — poor fit (see roadmap §2).

## 5. Core-integrity statement

- Diff confined to `app/finance/**` (+ `app/main.py` router registration) and
  the S3 work in `app/ops/**`.
- No second mutation boundary: a `FinancialAction` → `ActionRequest` →
  `execute_governed_action` only.
- The adapter is an **executor only** — it does not authorize, approve, override
  policy, redefine risk, or manufacture governance evidence.
- Approval enforcement, risk, authorization, verification, and Learn are all
  inherited from the frozen Core unchanged.
- **The zero-`app/core/**`-edit landing is the proof the freeze holds.**

## 6. Safety analysis

| Risk | Mitigation | Residual |
|---|---|---|
| **Wrong amount / wrong target approved** | Threshold tiers + human approval for the risky subset; verification reads back the posted entry and asserts it matches the authorized intent. | A human must catch a semantically wrong-but-valid approval. Acknowledged — this is the human-in-the-loop design. |
| **Same operator proposes and approves** | Separation of duties enforced for Tier 1/2 (approver ≠ proposer; Tier 2 also approver-1 ≠ approver-2). | S3 core shipped (`b391293`); D-4 must **extend** it to finance holds (proposer = operator; see dependency table). Small, generic extension. |
| **Ledger drift / failed post** | Verify stage reads back the effective state; a mismatch is `state_mismatch`, and a failed post is `adapter_execution_failed` (E3, now closed). | **Closed** — E3 shipped 2026-09-08 (`app/ops/execution_evidence.py`). |
| **Real ledger integration risk** | First demo uses a simulated ledger behind the adapter interface; no real system is touched. | None for the demo. |
| **Audit challenge** | Full authorization → approval → verification chain is durable evidence, correlated by stable IDs. | None. |

**Note on E3:** closed 2026-09-08 (`app/ops/execution_evidence.py`, above-Core
wrapper). D-4 wires `record_failed_execution_evidence` into the finance adapter
path and inherits the `adapter_execution_failed` outcome for free.

## 7. Tests — `app/finance/testing/test_finance.py` (adapter mocked / simulated)

1. Tier 0 (below threshold) → `allow` (auto-approve), executed + verified.
2. Tier 1 (above threshold) → `hold`; approve → executed + verified + learned.
3. Tier 2 (top tier) → `escalated_hold`; requires **dual** approval.
4. Tier 2 with same proposer+approver → **refused** (S3).
5. No operator token → 401 (S1).
6. Verification mismatch (posted entry ≠ authorized intent) → recorded as a
   distinguishable outcome.
7. Denied action → never reaches the adapter.
8. Full evidence chain present for a Tier 1 approval (authorization / approval /
   audit / trace / verification / learn correlated by `action_id`).
9. `import app.main` clean; 122 frozen-Core tests unchanged.

## 8. Validation plan

- New focused tests pass.
- Core intelligence (122) unchanged — proves the freeze holds.
- Full app suite passes.
- A **live demo** on the real host: propose a Tier 1 disbursement → held →
   approve → executed against the simulated ledger → verified → learned; and a
   Tier 2 op refused on same-operator approval. Recorded in
   `docs/RMT_CAPABILITIES_EVIDENCE.md`.

## 9. The one open Core question — `ActionType`

`ActionRequest.action_type` is a **closed `str, Enum`** (9 container-ops values)
and `app/core/intelligence/actions/policy.py` **denies** any `action_type` whose
`.value` is not in `ALLOWED_ACTION_TYPES` (`restart_component`, `start`, `stop`,
`restart`, `create`, `remove`). D-4's `disbursement` / `limit_change` /
`risk_parameter_update` / `budget_allocation` are in neither. Two paths:

**Path A — minimal Core deviation (cleaner evidence).**
Add the 4 members to `ActionType` **and** to `ALLOWED_ACTION_TYPES`. Two
`app/core/**` files, **additions only, no existing logic changed** — the
`simulation.py` default branch already handles an unknown type
(`risk_level="unknown"`). The Core evidence chain then carries the true
financial operation in `operation` / `action_type`. **Cost:** it is a Core edit,
and the standing owner directive is *no Core modification* — this needs the
owner to lift it for this specific behaviour-preserving case (precedent:
platform_state provider extraction, E1 atomic writes).

**Path B — zero Core edit (recommended under the current directive).**
Every financial action is submitted as **`ActionType.CREATE`** ("create a
financial-ledger / limit-change record"). `create` is allowed by Core policy, so
the full governed flow works unchanged. The **real** action type lives in
`FinancialAction`, `ActionRequest.parameters["finance_action_type"]`, `reason`,
and `decision_id` (`finance-disbursement-<id>` — the same pattern the agent
surface uses: `decision_id = agent-llm-agent-…`). The finance adapter reads
`parameters` for the true operation. **Cost:** raw Core evidence reads
`operation: create` for every financial action; the financial specificity is in
D-4's own domain records + `decision_id`, correlated by `action_id`. Documented
tradeoff; D-4's `/finance/status` is the financial view, the Core chain the
tamper-evident backing.

**Recommendation:** Path B, unless the owner wants the 2-file behaviour-preserving
deviation for self-describing Core evidence.

## 10. Decisions for the owner

1. **Proceed with D-4, or hold it?** (Recommendation below in the sequencing
   note: hold until E4 + E5 close.)
2. **`ActionType` (§9)** — Path B (zero Core edit, `create` + parameters) or
   Path A (2-file behaviour-preserving Core deviation)?
3. **Dual approval (§3a)** — confirm Option D1 (Core hold + above-Core
   aggregation, accept the 300 s two-approval window).
4. **First-demo action types** — `disbursement` + `limit_change` first
   (recommended); `risk_parameter_update` + `budget_allocation` later.
5. **Real ledger integration** — out of scope for the first demo (recommended),
   or a specific ledger/limit system to target?

### Sequencing recommendation (2026-09-08)

**Hold D-4 until E4 (evidence retention) and E5 (evidence backup/restore) are
closed.** Financial governance evidence carries the highest durability /
recoverability bar of any domain; standing it up on unbounded, un-backed-up JSON
stores is backwards. S3 and E3 are done; E4 + E5 are the remaining gate. When
those land, D-4 is a well-scoped 1–2 session build (domain module + adapter +
tier policy + the §3a dual-approval layer + the §9 Path-B mapping).

If a near-term deliverable is wanted from this proposal, the **dual-approval /
M-of-N primitive (§3a)** is the piece worth extracting and building standalone:
it is generically useful (every high-assurance approval domain in the roadmap),
it is a clean above-Core state machine, and it extends `app/ops/separation.py`.

---

*Draft rev-2 for owner review. No implementation begins until the owner
authorizes the scope. Does not reopen C01–C07. Does not create a Core milestone.
§9 Path A, if chosen, is a bounded owner-authorized freeze deviation.*

🤖 Generated with [Claude Code](https://claude.com/claude-code)
