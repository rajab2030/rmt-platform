# RMT — Improvement Roadmap (prioritized)

## 1. Authority and Purpose

This document is a **prioritized list of improvements to the RMT platform as it
stands today** (post-freeze, CAP-01..05 delivered, P0/P1/P2 production-readiness
closed, Tier 1 homelab-depth batch T1-2/3/4 done). It is a companion to
`docs/RMT_ABOVE_CORE_ROADMAP.md` (the *menu of new directions*): that document
asks "what should RMT do next"; this one asks "what would make the RMT we
already have more trustworthy, more provable, and more usable".

**Classification.** Every item here is **above-Core**, **operational**, or
**process/documentation**. Nothing in this document:

- reopens or modifies C01–C07 (Core frozen at commit `46a4441`),
- creates a new Core milestone (there is no C08),
- proposes a Core fix. Per the owner directive (2026-09-08), a recorded
  frozen-Core gap gets an **above-Core mitigation** or an explicit
  **accept-and-record** — never a freeze deviation. §7 is the register of those
  gaps; it proposes tracking, not fixing.
- is authorized. Each item becomes work only when the owner selects it and, for
  anything larger than S, a per-item proposal (`docs/RMT_*_PROPOSAL.md`) is
  written and approved — the CAP-04 / CAP-05 / T1-batch pattern.

**Basis.** Drawn from a full read of the governing docs + `HANDOFF.md` session
history, corroborated this session by running the suite (397 passed, 2 e2e
skips) and a Docker-unreachable probe (app boots, resolves to `simulation`,
executes a governed action end-to-end). Where a claim rests only on a recorded
prior-session result it is marked *(recorded, not re-verified)*.

Governing references: `docs/RMT_MASTER_DEFINITION.md`,
`docs/RMT_CORE_TARGET_STATE.md`, `docs/RMT_PRODUCTION_READINESS.md`,
`docs/RMT_ABOVE_CORE_ROADMAP.md`, `AGENTS.md`, `STEWARD.md`.

---

## 2. How to read an item

- **Objective** — the one outcome it delivers.
- **Why now** — the risk or limitation it removes.
- **In scope** — what would be built or written.
- **Boundary** — always includes: no `app/core/**` change, no second mutation
  path, approval enforcement unchanged.
- **Done when** — `Implementation + Integration + Enforcement + Validation +
  Evidence` per `STEWARD.md` §4.
- **Depends on** / **Size** — S (days) / M (1–2 weeks) / L (multi-week).

Phases are priority-ordered. Phase A is the base everything else assumes;
Phase D is conditional on wanting an audience beyond the owner.

---

## 3. Phase A — Foundations (do first)

These make the platform's own operation reliable and continuously checked. They
are cheap relative to their risk reduction and every later phase assumes them.

### A1 — Finish the SQLite evidence substrate (T0-1)

- **Objective:** the six governance-evidence stores
  (authorizations / holds / records / audit / traces / verifications) move from
  file-backed JSON `DurableStore` to the single SQLite substrate already used by
  observability + intelligence-memory (`data/observability.db`), extended to
  `data/governance_evidence.db` (the working-tree `conftest.py` already assumes
  this).
- **Why now:** JSON stores are O(n) rewrites, grow unbounded, and make
  transactional reconciliation (E6) and retention (E4) awkward. Every Phase C
  domain adds volume this substrate is not sized for.
- **In scope:** `DurableStore` implementation swap behind the unchanged public
  interface; one-shot reversible migration of existing records; startup
  integrity check across hold ↔ record ↔ authorization folded in; retention /
  archival ported.
- **Boundary:** the `DurableStore` API and the on-disk record schema are
  preserved; above-Core substrate only.
- **Done when:** full suite green against SQLite; migration reversible;
  hard-kill-during-write test shows all six stores intact and mutually
  consistent on reload.
- **Depends on:** nothing. **Size:** M. *(Partly started in the working tree.)*

### A2 — Activate the CI gate + an always-on integration lane

- **Objective:** the finite-validation gate (`backend/scripts/ci.sh`,
  `.github/workflows/ci.yml`) actually runs on every change, and the real
  Docker adapter path is exercised continuously, not only in manual live demos.
- **Why now:** CI is documented as "dormant until the repo has a remote"
  (`HANDOFF.md`, V2). The `@pytest.mark.e2e` real-adapter test auto-skips
  whenever Docker is absent — today that is CI, so the executed path has **no**
  automated coverage.
- **In scope:** push to a private remote; enable the workflow; add a nightly (or
  services-container) job that runs the `e2e` marker against a disposable
  container; publish the pass/skip counts as a status badge or a
  `docs/` line kept in sync.
- **Boundary:** tooling / infra only; no code change to the governed path.
- **Done when:** a green CI run exists on the remote; the `e2e` job runs
  un-skipped on a schedule; a red suite blocks merge.
- **Depends on:** a remote (owner). **Size:** S.

### A3 — Frozen-Core debt register with explicit triggers

> **Status: DONE (2026-09-10)** — `docs/RMT_FROZEN_CORE_DEBT.md` (rows D1–D5 +
> the §14 recorded-and-closed table); cross-linked from `RMT_CONTEXT.md` §14 and
> `docs/RMT_CORE_ADAPTER_DECOUPING.md` §9.

- **Objective:** one authoritative table of every recorded frozen-Core gap, its
  current above-Core compensating control, and the written condition that would
  make the owner revisit it.
- **Why now:** the gaps (hold status not persisted → a resolved hold reads
  `pending` on disk after restart; failed-adapter verification; Docker-flavoured
  names in Core; adapter-decoupling #2–#18) are real and *are* mitigated, but
  the record is scattered across `RMT_CONTEXT.md` §14 and many `HANDOFF.md`
  session notes. A reader cannot see the whole liability in one place, nor what
  would trigger action.
- **In scope:** a new `docs/RMT_FROZEN_CORE_DEBT.md`: one row per gap —
  *symptom · where · compensating control · residual risk · trigger to
  revisit*. Cross-link from `RMT_CONTEXT.md` §14 and
  `docs/RMT_CORE_ADAPTER_DECOUPING.md`.
- **Boundary:** documentation only; explicitly **not** a plan to modify the
  Core.
- **Done when:** the file exists, every §14 note and every deferred
  adapter-decoupling item appears once, and each has a concrete trigger.
- **Depends on:** nothing. **Size:** S.

---

## 4. Phase B — Make the guarantees real

The lifecycle diagram promises Verify and human approval; today both are
thinner than they look. This phase closes the gap between the diagram and the
behaviour.

### B1 — Strengthen the Verify stage (above-Core observer layer)

> **DONE (2026-09-10)** — `docs/RMT_B1_PROPOSAL.md` (both slices; §9/§10) +
> `docs/RMT_B1b_RECON.md` (recon before B1b). **B1a:** `app/ops/verification/`
> package (registry + expected-state table + `verify_executed_action`),
> `observe_container_state` `absent` extension, 3 call sites swapped +
> `POST /execute` wired, `verify_docker_execution` deleted. **B1b:** in-memory
> effective-status index (`index.py`) rebuilt at startup;
> `verification_inconclusive` notify; `GET /ops/verifications`; 4
> `rmt_executed_actions_*{adapter,operation}` `/metrics` counters;
> `effective_verification_status` on `/execute`; e2e through `POST /execute`.
> Full suite 455 passed; Core intelligence suite 134 unchanged (no `app/core/**`
> change).

- **Objective:** every adapter has a real post-condition assertion, and
  "verification could not observe the outcome" is a first-class alerting
  condition rather than a silent pass.
- **Why now:** across every recorded live exercise the Core verifier returns
  `observation_unavailable` (fail-safe) and only the above-Core Docker observer
  returns `verified_success` *(recorded, not re-verified)*. A control plane
  whose Verify stage routinely says "couldn't tell" provides weaker assurance
  than the lifecycle implies.
- **In scope:** extend the above-Core observer set (currently
  `app/homelab/verification.py`) so each registered adapter resolves a
  post-execution observer; emit an explicit `verification_inconclusive` signal
  to the notification sink + `/metrics` when no observer can assert; a
  dashboard/report line for "actions executed vs actions verified".
- **Boundary:** the Core verifier and its trusted-internal-observer resolution
  are untouched; this adds an above-Core observer and surfacing only.
- **Done when:** a Docker restart yields `verified_success` from the above-Core
  observer in an automated test (not just manual demo); an action with no
  observer raises `verification_inconclusive` to the sink; `/metrics` exposes
  the executed/verified ratio.
- **Depends on:** A1 (clean substrate helps the report). **Size:** M.

### B2 — Durable approval request + minimal approval view

- **Objective:** a held action that needs a human survives longer than the Core
  hold and is visible somewhere better than a JSON list.
- **Why now:** `APPROVAL_HOLD_TTL_SECONDS = 300` — a hold nobody approves in
  five minutes just expires (`HANDOFF.md` T1-batch recon). T1-4 added
  `GET /ops/holds` + a cron escalation script as a workaround; there is no view
  and no way to act on a hold after it lapses except to re-run the operation.
- **In scope:** an above-Core "approval request" record that outlives the Core
  hold, carries the full proposal + evidence links, and on approval
  **re-proposes** the action through `execute_governed_action` (a fresh Core
  hold, immediately continued); a read-only single-page view of open requests
  with an approve/reject action that calls the existing endpoints.
- **Boundary:** no new mutation path — approval still runs the governed
  boundary; the view is a thin client over `/ops/holds`, `/homelab/approve`,
  `/approve`.
- **Done when:** a request approved after the original 300s hold expired still
  results in one governed, verified execution with correlated evidence; the
  view lists open requests and round-trips an approval.
- **Depends on:** A1. **Size:** M. *(Subset of roadmap P-B.)*

### B3 — External-facing threat model + "guarantees / non-guarantees"

> **Status: DONE (2026-09-10)** — `docs/RMT_THREAT_MODEL.md` +
> `docs/RMT_GUARANTEES.md`; linked from `README.md` and `RMT_CONTEXT.md` §5;
> every non-guarantee traces to a readiness decision or a `RMT_FROZEN_CORE_DEBT.md`
> row.

- **Objective:** two short documents that let someone who is not the maintainer
  evaluate what RMT actually promises and where it stops.
- **Why now:** the governing docs are excellent for a steward but there is no
  statement of the trust boundary, the assumed adversary, or the explicit
  non-guarantees (no HA; single host; trusted-LAN operators; Verify may be
  inconclusive; failed-adapter evidence is a distinct status, not a rollback).
  Writing them also forces precision on B1 and A3.
- **In scope:** `docs/RMT_THREAT_MODEL.md` (assets, trust boundary, adversary
  = the "(b) trusted LAN, few operators" model already chosen, attack surface,
  residual risks) and `docs/RMT_GUARANTEES.md` (what each lifecycle stage does
  and does **not** assert, in plain language, cross-linked to the evidence
  types).
- **Boundary:** documentation only.
- **Done when:** both files exist, are linked from `README.md` and
  `RMT_CONTEXT.md`, and every "non-guarantee" traces to a specific recorded
  decision or gap.
- **Depends on:** A3 (shares content). **Size:** S.

---

## 5. Phase C — Prove generality

The platform's whole premise is "domain-agnostic governed control plane". One
adapter with a real workload proves the plumbing; it does not prove the claim.

### C1 — Broaden `REMEDIATION_POLICY` coverage (T1-1)

- **Objective:** the supervised loop and remediation cover more than
  `uptime-kuma` restart.
- **Why now:** `REMEDIATION_POLICY` holds a single component / single verb
  (`app/homelab/remediation.py`). It is the CAP-04 safe envelope, but it also
  means the "continuous operational loop" supervises one service.
- **In scope:** add the other homelab components and additional verbs
  (`start` for a stopped container) with per-entry `remediate_on` sets and
  `requires_approval`; keep every entry inside the T13 safe-envelope guard
  (`test_remediation_policy_within_cap04_safe_envelope`).
- **Boundary:** no `app/core/**` change; approval retained for every entry; the
  envelope guard test stays green.
- **Done when:** the loop demonstrably holds-then-remediates a second component
  end-to-end (test + one live exercise), evidence correlated.
- **Depends on:** nothing. **Size:** S. *(Already the named next Tier 1 item.)*

### C2 — Second domain end-to-end: Agent Governance Gateway (D-1)

- **Objective:** a structurally different adapter runs the full lifecycle
  `Understand → … → Verify → Learn` with **zero** Core edits, proving the
  frozen Core generalises.
- **Why now:** this is the single highest-value improvement — it converts
  "architecturally general" into "demonstrably general", and it either
  validates the abstraction or exposes exactly where it leaks. D-1 extends the
  live CAP-05 agent surface rather than starting cold and has the clearest
  external demand (roadmap §9).
- **In scope:** per `docs/RMT_ABOVE_CORE_ROADMAP.md` §6 D-1 — a governed action
  catalogue for "an autonomous agent wants to take a consequential action",
  its policy + risk rules, an adapter, and a post-condition observer (feeds
  B1); one end-to-end proof against a real non-homelab target.
- **Boundary:** the standard set; plus no lowering of
  `AGENT_DEFAULT_REQUIRES_APPROVAL`.
- **Done when:** the D-1 DoD in the roadmap is met and the proof run's evidence
  bundle is recorded in `docs/RMT_CAPABILITIES_EVIDENCE.md`.
- **Depends on:** A1, B1, and an approved `docs/RMT_CAP_06_PROPOSAL.md`.
  **Size:** L.

### C3 — Harden the agent surface before trusting it further

- **Objective:** an operator sees exactly what an agent proposal will do before
  approving it, and the surface is tested against adversarial input on every
  change.
- **Why now:** the live LLM exercise hit a `grant_scope_mismatch` from
  nondeterministic mechanism choice (`HANDOFF.md` CAP-05 5B note); the primary
  guardrail is allow-list validation; the MCR adversarial work
  (`experiments/mcr*`) is a set of one-offs, not a standing gate.
- **In scope:** a "preview" step on `/agent/act*` that resolves the proposal to
  its concrete `ActionRequest` + predicted outcome and returns it **without**
  creating a hold; a structured rationale field tied to the evidence record; a
  CI suite of adversarial goals (prompt-injection shapes, scope-escape
  attempts, dependency-cascade probes) asserting each is refused before an
  `ActionRequest` exists or caught at approval.
- **Boundary:** the LLM still only proposes; no execution, no autonomous loop;
  no new mutation path.
- **Done when:** `/agent/act/preview` returns the resolved action for a valid
  goal and `no_proposal`/`invalid_proposal` for the rest; the adversarial suite
  runs in CI and is green.
- **Depends on:** A2. **Size:** M.

---

## 6. Phase D — Broaden adoption (only if that is a goal)

Do none of this for a single-owner homelab. Do all of it before anyone else
runs their own instance.

### D1 — Governed-evidence console (roadmap P-B, full)

- **Objective:** a real UI over the evidence stores and the approval workflow —
  the full version of B2's minimal view.
- **In scope:** browse correlated authorization / approval / audit / trace /
  verification by id; the open-requests queue with approve/reject; loop +
  agent + `/metrics` status; read-only.
- **Boundary:** read-only except approve/reject, which call existing endpoints;
  no new mutation path.
- **Done when:** the roadmap P-B DoD is met. **Depends on:** A1, B2.
  **Size:** L.

### D2 — Multi-operator RBAC / IAM (roadmap P-D)

- **Objective:** move past shared bearer tokens to per-operator identity with
  roles (propose / approve / admin), so separation-of-duties (S3) is enforced
  by identity, not convention.
- **In scope:** an identity provider integration or a local user store;
  role-gated routes; S3 `check_separation` keyed on real identities.
- **Boundary:** above-Core `app/ops/**`; the governed boundary is unchanged.
- **Done when:** the roadmap P-D DoD is met. **Depends on:** B3 (threat model
  drives the role set). **Size:** L.

### D3 — Packaging & onboarding

- **Objective:** someone other than the maintainer can stand up an instance in
  under an hour.
- **In scope:** a container image; a `docker compose` / systemd quickstart that
  wires Caddy + the drop-ins; a reference **adapter template** (`app/adapters/
  _template/`) with a checklist for adding a domain; generated API docs from the
  FastAPI schema.
- **Boundary:** packaging only; no change to the governed path.
- **Done when:** a from-zero install on a clean VM reaches `/health` ok and
  passes `rmt-smoke.sh` following only the quickstart.
- **Depends on:** A1, A2. **Size:** M.

---

## 7. Frozen-Core debt — tracked, not fixed

This is the seed of the A3 register. None of these is an action item to modify
the Core; each is listed so the liability is visible and has a trigger.

| Gap | Compensating control today | Trigger to revisit (owner) |
|---|---|---|
| `approve_held_action` persists the approval **record** but not the **hold** — a resolved hold reads `pending` on disk after restart | startup reconcile (`app/ops/reconcile.py`); the record store is authoritative; CAP-04 guard cross-checks it | a domain where holds must be inspected directly on disk, or a reconcile that cannot run at startup |
| A *failed* adapter execution produced no verification evidence | E3 above-Core: `record_failed_execution_evidence` writes a distinct `adapter_execution_failed` status | a domain that needs rollback semantics on adapter failure, not just a status |
| Docker-flavoured names in Core (`PlatformStateProvider.get_docker_health`, `runtime_engine="docker"` defaults, `bootstrap` importing `app.docker_api`) | injected provider; optional adapter registration; verified this session that Docker-down still boots + passes | a second runtime adapter (k8s, cloud) where the naming actively misleads |
| Adapter-decoupling items #2–#18 | DEFERRED under owner REDUCE-SCOPE (`docs/RMT_CORE_ADAPTER_DECOUPING.md` §9) | any of #2–#18 becomes load-bearing for a new adapter |

---

## 8. Recommended sequence

1. **A1** (SQLite substrate) — finish what is already started; unblocks B1, B2,
   C2, D1.
2. **A2 + A3** in parallel — turn the CI gate on; write the debt register. Both
   are S and neither depends on A1.
3. **B3** — threat model + guarantees; small, and it sharpens everything after.
4. **B1** — real Verify; the biggest single credibility gain for the platform
   as it stands.
5. **C1** — broaden `REMEDIATION_POLICY`; cheap, and it exercises B1.
6. **B2** — durable approval request + minimal view; needed before a second
   domain generates holds a human must action.
7. **C2** — the second domain (D-1). The item that actually proves the thesis.
   Do not start before A1/B1 are done.
8. **C3** — harden the agent surface alongside or just after C2.
9. **Phase D** — only if the platform is meant for an audience beyond the
   owner; D3 first, then D1, then D2.

Everything else is selected on demand.

---

## 9. What is explicitly *not* here

- Any Core modification, Core fix, or C08.
- Reopening C01–C07 or the production-readiness matrix (P0/P1/P2 are closed;
  R4 "no HA" stays ACCEPTED at homelab scale).
- New domains beyond the one proof in C2 — those live in
  `docs/RMT_ABOVE_CORE_ROADMAP.md` and are chosen on demand.
- High-throughput / sub-second / no-observable-outcome workloads — out of the
  fit profile (`docs/RMT_ABOVE_CORE_ROADMAP.md` §2).
