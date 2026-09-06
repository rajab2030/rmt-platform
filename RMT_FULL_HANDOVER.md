# RMT — Full Project Status Reference

> Snapshot date: 2026-09-04.
> This is a consolidated **status reference** for the current agent and the
> project owner. It is a **coordination** document only — architecture
> authority lives in the governing docs listed in §3. It does not replace the
> current agent or the agent relationship; it captures verified status so the
> current agent can resume consistently after a gap. Read this first, then
> follow the resume sequence in §1.

---

## 1. Resume / read order (for the current agent)

1. This document (`RMT_FULL_HANDOVER.md`) — consolidated current status.
2. `RMT_CONTEXT.md` — stable project brain / bootstrap context (identity,
   lifecycle, boundary, decisions, milestone status, next action).
3. `HANDOFF.md` — fine-grained latest-session history/continuation context.
4. `AGENTS.md` — agent operating contract (authority hierarchy, rules).
5. Governing docs: `docs/RMT_MASTER_DEFINITION.md`,
   `docs/RMT_CORE_TARGET_STATE.md`, `docs/RMT_CORE_GAP_MATRIX.md`,
   `docs/RMT_CORE_REMAINING_ROADMAP.md`.

Do **not** reconstruct status from conversation memory — read the docs, then
verify consequential claims against the repository.

---

## 2. One-line status

**RMT Core is POST-FREEZE and complete.** Milestones C01–C07 are CLOSED, the
RMT Core Target State is ACHIEVED, the RMT Core Platform Freeze is REACHED
(freeze commit `46a4441`), the finite validation suite passes **122/122**
(re-verified on this snapshot date), and the next phase is the **First Real
RMT Capability — Homelab Operations** (not Core development; no C08).

---

## 3. Project identity and architecture

RMT is a general-purpose intelligent control, execution, and governance
platform. The **Core is domain-agnostic and finite** (not an indefinitely
expanding architecture).

- **Core lifecycle (unchanging):**
  `Understand → Decide → Govern → Authorize → Execute → Verify → Learn`
- **Single authoritative governed mutation path:**
  `execute_governed_action → execution_engine.execute → adapter`
- **Core/domain boundary:**
  - *Core:* observation, intelligence, decision, governance, risk, approval,
    authorization, controlled execution, adapter boundary, verification,
    audit/trace, learning/history, controlled evolution, self-management,
    platform validation.
  - *Above-Core/domain:* Banking Risk, Budget Control, AI Agent Governance,
    IT/Cloud Ops, Docker/provider adapters, products, integrations, apps, UI.

**Governing documents and authority:**

| Doc | Role |
|---|---|
| `docs/RMT_MASTER_DEFINITION.md` | Top authority — defines RMT and Core/domain boundary |
| `docs/RMT_CORE_TARGET_STATE.md` | Top authority — finite Target State and completion criteria |
| `docs/RMT_CORE_GAP_MATRIX.md` | Verified gaps vs Target State (status record) |
| `docs/RMT_CORE_REMAINING_ROADMAP.md` | Finite milestone roadmap + final boundary statement |
| `AGENTS.md` | Agent operating contract (authority hierarchy, rules) |
| `RMT_CONTEXT.md` / `HANDOFF.md` | Coordination/continuation (NOT architecture authority) |

Repository evidence > conversation memory; governing docs > assumptions.

### Key architectural decisions (established, fixed)
- **Single governed mutation boundary** — `execute_governed_action` is the only
  Core-scope production mutation path.
- **Action policy** is the authoritative governance gate; **execution policy**
  is a deny-only final safety check.
- **Governance risk** is authoritative for approval; **execution risk** is an
  independent final assessment.
- **Durable evidence** via JSON `DurableStore` (authorization, approval/hold,
  approval-record, audit, trace, verification), correlated by stable IDs.
- **Verification authority:** post-execution verification uses a trusted
  internal observer resolved from the execution request — never caller-controlled.
- **Evolution & self-management** validated through the governed service
  boundary (`execute_governed_change`, `execute_self_management_decision`);
  **no HTTP evolution route required**.
- **Adapters are executors only** — they cannot authorize, approve, override
  policy, redefine risk, or manufacture governance evidence.

---

## 4. Milestone status

| Milestone | Capability | Status |
|---|---|---|
| RMT-C01 | Governed Execution Boundary | CLOSED |
| RMT-C02 | Durable Governance Evidence | CLOSED |
| RMT-C03 | Post-Execution Verification | CLOSED |
| RMT-C04 | Generalized Understand → Decide Completion | CLOSED |
| RMT-C05 | Controlled Platform Self-Management | CLOSED |
| RMT-C06 | Controlled Platform Evolution | CLOSED |
| RMT-C07 | Platform Validation and Freeze | CLOSED — **Platform Freeze** |

**There is intentionally no C08.** Closed milestones must not be reopened
without evidence. A proposed Core change may enter the roadmap only if it closes
a verified gap against `RMT_CORE_TARGET_STATE.md`; otherwise it is
ABOVE-CORE/DOMAIN, FUTURE, or NOT REQUIRED.

---

## 5. Verified implementation state

Re-verified on this snapshot date:
- Full intelligence testing suite: **122 passed** (`pytest app/core/intelligence/testing -q`).
- C07 HTTP validation artifact: `app/core/intelligence/testing/test_http_entrypoints.py` (7 tests).
- D1 production fix present:
  `app/core/intelligence/service.py::calculate_platform_health` reads
  `observation.signals.get("cpu_usage", 0)` and
  `observation.signals.get("memory_usage", 0)`; regression test
  `test_deviation_branch_uses_signals_contract`.
- `GET /intelligence/health` → HTTP 200.
- G2 Core-boundary review: **PASS** (no genuine Core implementation gap after D1).
- Durable evidence stores clean under the committed HTTP artifact.

### Validated command
```bash
cd /home/rmt-lab/homelab/projects/homelab-control-center/backend
source .venv/bin/activate
PYTHONPATH=. pytest app/core/intelligence/testing -q      # -> 122 passed
```

---

## 6. Next objective (do NOT start implementation yet)

**First Real RMT Capability — Homelab Operations.** Use the frozen RMT Core as
the intelligent control plane for the real homelab and demonstrate genuine
end-to-end operational capability through:

**Understand → Decide → Govern → Authorize → Execute → Verify → Learn**

Scope notes:
- This is **above-Core / domain** work — it must not modify or reopen the frozen
  Core, and must not invent a new Core milestone.
- Already present: `app/homelab/` contains an above-Core Docker observer
  (`observer.py`), remediation wiring (`remediation.py`), and verification
  wiring (`verification.py`) that connect the frozen Core to Homelab/Docker
  services through the single governed execution boundary.
- Start with **read-only reconnaissance and contract review**. Do not modify
  files or run state-changing/system commands without explicit approval.

---

## 7. Repository layout

```
/home/rmt-lab/homelab/
├── RMT_CONTEXT.md, RMT_FULL_HANDOVER.md, HANDOFF.md   # coordination docs
├── AGENTS.md                                          # agent contract
├── README.md                                          # HomeLab overview
├── docs/                                              # authority + supporting docs
│   ├── RMT_MASTER_DEFINITION.md, RMT_CORE_TARGET_STATE.md,
│   ├── RMT_CORE_GAP_MATRIX.md, RMT_CORE_REMAINING_ROADMAP.md, BUILD_LOG.md
│   ├── architecture/ operations/ procedures/ recovery/ milestones/
├── projects/homelab-control-center/                   # application
│   ├── backend/  (FastAPI + RMT Core; own .git)       # primary codebase
│   │   └── app/core/intelligence/...            (Core)
│   │   └── app/homelab/...                       (above-Core docker wiring)
│   │   └── app/main.py                            (FastAPI entrypoint)
│   └── frontend/   (React/Vite/TS; dist/, node_modules/)
├── docker/stacks/   (per-service compose: portainer, uptime-kuma, dozzle,
│                     npm, n8n, vaultwarden)
├── scripts/   (backup, inventory, platform-health/recovery shell scripts)
├── backups/   (daily/ weekly/ monthly/ manifests/)
└── restore/
```

---

## 8. Environment caveats and tooling facts

- **Git is NOT installed** — `git status/log/tag` will not work in this shell.
  The user handles git separately. This is a tooling limitation, not a milestone.
- **Docker is NOT accessible** here (socket permission denied) — live docker
  execution and `/containers*` routes require docker; tests use mocks. Docker
  is an above-Core adapter concern.
- **`httpx2` IS installed** (test dependency) — FastAPI `TestClient` HTTP route
  tests work.
- **`~` expands incorrectly** in this shell — use explicit paths
  (`/home/rmt-lab/homelab/...`).

---

## 9. Deferred items — recorded dispositions (do not reopen)

- **`module_registry.register_module()`** — an internal governed primitive, not
  a bypass and not a missing Core requirement.
- **`execution/service.py::execute_action()`** — unreachable dead-code
  housekeeping; no C07 impact.
- Committed HTTP-route test evidence (existing public routes only) — recorded.
- G2 Core-boundary review record — recorded (PASS).

---

## 10. Working pattern that worked well

1. Read milestone contract + authority docs.
2. Read-only integrated verification against the contract.
3. Get explicit approval before implementing.
4. Implement the bounded change; add tests; run the suite.
5. Report files changed, summary, test result, deviations.

---

## 11. Do / don't checklist for the next session

- [ ] Start with read-only reconnaissance on the Homelab Operations capability.
- [ ] Do NOT reopen C01–C07; do NOT invent a C08.
- [ ] Do NOT modify frozen Core or protected authority documents without explicit
      approval and evidence that the Target State/contract is insufficient.
- [ ] Never silently convert assumptions into facts — mark FACT/DECISION/
      PROPOSAL/UNKNOWN.
- [ ] Verify claims against the repository before acting on them.
