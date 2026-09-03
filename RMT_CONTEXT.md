# RMT — Project Context (Stable Project Brain)

> **Purpose:** This is the stable bootstrap/context document for the RMT project.
> A new technical session reads this FIRST, then `HANDOFF.md` (fine-grained
> session history), then the governing documents, and verifies consequential
> claims against the repository.
>
> `RMT_CONTEXT.md` = stable project brain / bootstrap context.
> `HANDOFF.md` = fine-grained session history / continuation context.

---

## 1. RMT identity and purpose

RMT is a general-purpose intelligent control, execution, and governance
platform. The Core is domain-agnostic: it governs services, applications,
systems, and AI agents without embedding the rules of any particular domain.

The Core is a **finite** capability set. It is not an indefinitely expanding
architecture.

## 2. Core lifecycle

**Understand → Decide → Govern → Authorize → Execute → Verify → Learn**

The single authoritative governed mutation path is:

`execute_governed_action` → `execution_engine.execute` → adapter

## 3. Core/domain boundary

- **Core:** generic platform capability (observation, intelligence, decision,
  governance, risk, approval, authorization, controlled execution, adapter
  boundary, verification, audit/trace, learning/history, self-management,
  controlled evolution, platform validation).
- **Above-Core / domain:** Banking Risk Management, Budget Control, AI Agent
  Governance, IT/Cloud Operations, concrete Docker/provider adapters, products,
  integrations, applications, UI.
- A useful capability is **not** automatically a Core requirement.

## 4. Finite Core Target-State principle

The Target State is a **completion boundary**, not an implementation plan.
The Core is complete when one governed lifecycle is real, connected, enforced,
observable, verifiable, and evidenced. A class/module/isolated test is not
completion evidence by itself.

## 5. Governing documents and their authority

| Document | Role |
|---|---|
| `docs/RMT_MASTER_DEFINITION.md` | Top authority — defines RMT and Core/domain boundary |
| `docs/RMT_CORE_TARGET_STATE.md` | Top authority — finite Core Target State and completion criteria |
| `docs/RMT_CORE_GAP_MATRIX.md` | Verified gaps vs Target State (status record) |
| `docs/RMT_CORE_REMAINING_ROADMAP.md` | Finite implementation roadmap and milestone status |
| `AGENTS.md` | Agent operating contract (authority hierarchy, rules) |
| `RMT_CONTEXT.md` / `HANDOFF.md` | Coordination/continuation (not architecture authority) |

Governing documents take precedence over assumptions. Repository evidence takes
precedence over conversation memory.

## 6. Major established architectural decisions

- **Single governed mutation boundary:** `execute_governed_action` is the only
  Core-scope production mutation path; no equivalent unmanaged path remains.
- **Policy relationship:** action policy is the authoritative governance gate;
  execution policy is a deny-only final safety check.
- **Risk relationship:** governance risk is authoritative for approval;
  execution risk is a final independent assessment, consistent and traceable.
- **Durable evidence:** authorization, approval/hold, approval-record, audit,
  trace, and verification are durable via JSON `DurableStore`, correlated by
  stable identifiers.
- **Verification authority:** post-execution verification uses a trusted
  internal observer resolved from the execution request; it is never
  caller-controlled (B3/B4). Adapter success alone cannot manufacture
  `verified_success`.
- **Evolution & self-management:** validated through the governed service
  boundary (`execute_governed_change`, `execute_self_management_decision`).
  No HTTP evolution route is required.
- **Adapters are executors only:** they do not authorize, approve, override
  policy, redefine risk, or manufacture governance evidence.

## 7. Architectural boundaries and anti-bypass principles

- No second mutation boundary.
- No direct execution without a valid, bound authorization.
- Authorization is created at a single site inside the governed chain.
- Approval continuation stays within the governed path.
- Adapter selection/redirection is constrained (e.g., evolution is bound to the
  `module_change` adapter).
- Learning/history is read-only and cannot invoke execution, mint
  authorization, or mutate governance state.
- Blocked/denied/unknown paths never reach an adapter.

## 8. Completed milestones and status

| Milestone | Capability | Status |
|---|---|---|
| RMT-C01 | Governed Execution Boundary | CLOSED |
| RMT-C02 | Durable Governance Evidence | CLOSED |
| RMT-C03 | Post-Execution Verification | CLOSED |
| RMT-C04 | Generalized Understand → Decide Completion | CLOSED |
| RMT-C05 | Controlled Platform Self-Management | CLOSED |
| RMT-C06 | Controlled Platform Evolution | CLOSED |
| RMT-C07 | Platform Validation and Freeze | CLOSED — Platform Freeze |

Closed milestones must not be reopened without evidence.

## 9. Current milestone / status

**C07 — Platform Validation and Freeze: CLOSED.** The RMT Core has reached
**Platform Freeze**. There is intentionally **no C08**. Future work is
above-Core/domain/product/integration/adapter/application.

## 10. Current verified implementation state

- Full intelligence testing suite: **122 passed** (verified).
- C07 HTTP validation artifact exists:
  `app/core/intelligence/testing/test_http_entrypoints.py` (7 tests).
- D1 production correction applied (`app/core/intelligence/service.py`:
  `calculate_platform_health` reads `observation.signals.get("cpu_usage", 0)` /
  `.get("memory_usage", 0)`), with a focused regression test
  (`test_deviation_branch_uses_signals_contract`).
- `GET /intelligence/health` returns HTTP 200.
- G2 Core-boundary review: **PASS** (no genuine Core implementation gap after D1).
- Durable evidence stores are clean under the committed HTTP artifact.

## 11. Current remaining work

- No remaining Core work. The finite Core Target State is validated and the RMT
  Core is frozen.
- Future work is above-Core/domain/product/integration/adapter/application.
- Any Core change requires evidence that the finite Target State or an existing
  Core contract is insufficient.

## 12. Current immediate next action

Post-freeze: pursue above-Core/domain/product/integration/adapter/application
work. Do not begin new Core work. Do not invent a new Core milestone (no C08).

## 13. Environment limitations vs genuine implementation gaps

- **Git is NOT installed** — a tooling/environment limitation, **not** a new
  RMT milestone. The user handles git separately.
- **Docker is NOT accessible** (socket permission denied) — an environment
  limitation; Docker is an above-Core adapter concern.
- **`httpx2` is installed** (test dependency) — HTTP route tests are possible.
- Environment limitations must **not** automatically be classified as
  implementation defects.

## 14. Deferred issues — disposition recorded

- **`module_registry.register_module()`** — an **internal governed primitive**, not
  a bypass and not a missing Core requirement. Disposition recorded at C07 closure.
- **`execution/service.py::execute_action()`** — **unreachable dead-code
  housekeeping**, no C07 impact.
- Committed HTTP-route test evidence (existing public routes only) — recorded.
- G2 Core-boundary review record — recorded (PASS).

## 15. Rules for distinguishing FACT / DECISION / PROPOSAL / UNKNOWN

- **FACT:** established by repository/evidence (code, tests, recorded results).
- **DECISION:** a recorded architectural/scope decision (e.g., no HTTP evolution
  route; deny-only execution policy).
- **PROPOSAL:** a suggested change not yet accepted.
- **UNKNOWN:** not yet established by evidence; state it as unverified.
- Never silently convert assumptions into facts.

## 16. Rules for evaluating proposed Core changes

A proposed change may enter the remaining Core roadmap only if it closes a
verified gap against `RMT_CORE_TARGET_STATE.md`. Otherwise it is classified as
**ABOVE-CORE / DOMAIN**, **FUTURE**, or **NOT REQUIRED**. There is no C08; after
C07 the Core is complete or frozen.

## 17. Working / coordination method with the user

1. Read-only reconnaissance and contract review.
2. Verify claims against the repository and governing documents.
3. Propose the smallest bounded change; get explicit approval.
4. Implement; add tests; run the suite; report evidence.
5. Report files changed, results, deviations, and any conflicts.

## 18. Bootstrap instructions for a new technical session

1. Read `RMT_CONTEXT.md` first.
2. Read `HANDOFF.md` second.
3. Read the relevant governing documents.
4. Verify consequential claims against the repository.
5. Do NOT ask the user to reconstruct project status if the documents already
   establish it.
6. Do NOT ask "where are we?" or "what is next?" as the default.
7. State the verified understanding briefly.
8. Continue from the established next action.
9. If evidence conflicts with context, identify the conflict and resolve it
   using the governing documents/repository evidence.
10. Never silently convert assumptions into facts.

---

## Final boundary statements

- **Do not invent another Core milestone after C07.** C07 is the final finite
  Core validation/freeze stage. There is intentionally **no C08**.
- **Platform Freeze** occurs only after the Target State has been validated.
- Future work after Core Freeze is primarily above-Core/domain/product/
  integration/adapter/application work.
- Closed milestones must not be reopened without evidence.
- A useful capability is not automatically a Core requirement.
- Environment limitations must not automatically be classified as
  implementation defects.
- Repository evidence takes precedence over conversation memory.
- Governing documents take precedence over assumptions.
