# RMT — Above-Core Opportunity Roadmap

## 1. Authority and Purpose

This document is a **menu of candidate above-Core directions** for the RMT
platform, each scoped enough for the owner to select from. It is the companion
to `docs/RMT_CORE_REMAINING_ROADMAP.md` (which is **CLOSED** — C01–C07 done, Core
frozen at commit `46a4441`).

**Classification:** every item here is **above-Core / domain** or **future
backlog** in the sense of `docs/RMT_MASTER_DEFINITION.md` §"Finite Core Target
State". Nothing in this document:

- reopens or modifies C01–C07,
- creates a new Core milestone (there is no C08),
- expands the frozen Core's responsibilities,
- is authorized. **Each candidate becomes work only when the owner selects it and
  a per-capability proposal (`docs/RMT_CAP_XX_PROPOSAL.md`) is written and
  approved**, exactly as CAP-04 / CAP-05 were.

The one exception — a single item that *would* touch the frozen Core and
therefore needs an explicit freeze-deviation authorization — is isolated in §8.

Governing references: `docs/RMT_MASTER_DEFINITION.md`,
`docs/RMT_CORE_TARGET_STATE.md` §6 (out-of-scope), `docs/RMT_CORE_GAP_MATRIX.md`
§6, `docs/RMT_PRODUCTION_READINESS.md`, `AGENTS.md`.

---

## 2. What RMT governs effectively (the fit profile)

RMT is a **governed action gateway**. It fits any situation where *something or
someone decides to change real state, and that change must be policy-checked,
risk-rated, approved, authorized, executed once through a single path, verified
afterward, and permanently evidenced* — the lifecycle
`Understand → Decide → Govern → Authorize → Execute → Verify → Learn`.

### Strong fit

| Property of the workload | Why RMT fits |
|---|---|
| Discrete, consequential state changes | Each is one governed action with correlated evidence |
| A bounded catalogue of action types per domain | Maps cleanly to policy + risk rules + an adapter |
| An observable post-condition | The Verify stage has something real to check |
| A human approver acceptable for the risky subset | Manual-hold + executable continuation already exists |
| Rollback / safe-failure matters | `rollback_required` + verification classes are first-class |
| Initiated by autonomous agents that must not act unsupervised | Scoped, single-use, time-limited authority grants; capability ≠ authority |
| Auditor will later ask "who authorized this, and was it verified?" | Durable authorization / approval / audit / trace / verification records |

### Poor fit (do **not** propose these as RMT capabilities)

- Sub-second latency paths (real-time trade execution, request-path authz).
- High-throughput / massive fan-out (10³+ actions/sec).
- Continuous tight-loop control (PID-style regulation).
- Actions with no observable outcome — nothing for Verify to assert.

Sweet spot: **discrete, consequential, verifiable actions at low-to-moderate
volume, human-in-the-loop for the risky subset, initiated by people or agents.**

---

## 3. How to read a candidate

Each candidate below carries a fixed sub-structure:

- **Objective** — the one outcome it delivers.
- **In scope** — what the capability would build.
- **Boundary** — what it explicitly must not do (always includes: no
  `app/core/**` change, no second mutation path, approval enforcement
  unchanged).
- **Definition of Done** — `Implementation + Integration + Enforcement +
  Validation + Evidence` per `STEWARD.md` §4.
- **Depends on** — prerequisites (often a Tier 0 item).
- **Rough size** — S (days) / M (1–2 weeks) / L (multi-week), indicative only.

Tiers are priority-ordered for platform maturity, **not** a mandatory sequence.

---

## 4. Tier 0 — Complete operational readiness

These close the remaining P1/P2 rows of `docs/RMT_PRODUCTION_READINESS.md`. They
are not new capabilities; they are what must be true before RMT can be *relied
on* unattended or exposed beyond a single trusted host. **Most Tier 2 domains
should not go live until Tier 0 is done.**

### T0-1 — Evidence substrate: JSON → SQLite

- **Objective:** replace the six file-backed `DurableStore` JSON stores with a
  single SQLite-backed store; O(1) appends, bounded growth, transactional
  reconciliation.
- **In scope:** a `DurableStore` implementation swap behind the existing
  interface; a one-shot migration of existing JSON records; retention/rotation
  policy (closes E4); startup integrity check across hold ↔ record ↔
  authorization (finishes E6).
- **Boundary:** the `DurableStore` public API and the on-the-wire record schema
  are preserved; this is above-Core substrate (the store class already took an
  owner-authorized E1 deviation, but the interface did not change and must not).
- **DoD:** all 263+ tests green against SQLite; migration is reversible; a
  hard-kill restart test shows evidence intact and stores mutually consistent.
- **Depends on:** nothing. **Rough size:** M.
- **Why first:** it also de-risks E4, E6, and every high-volume Tier 2 domain.

### T0-2 — RMT platform recovery (R3 / E5)

- **Objective:** a tested procedure + script to rebuild the RMT service on a
  fresh host from the repo + a restored evidence set.
- **In scope:** fold the RMT stores and `data/observability.db` into the
  existing homelab backup engine and `docs/recovery/RECOVERY_RUNBOOK.md`;
  a `restore + integrity-check` script.
- **Boundary:** operational tooling only; no code change to the governed path.
- **DoD:** a from-cold rebuild on a clean VM restores service + evidence and
  passes an integrity check.
- **Depends on:** T0-1 (simpler with one DB file). **Rough size:** S–M.

### T0-3 — Observability of the governed lifecycle (O1 / O3)

- **Objective:** structured logs + a metrics endpoint for RMT's own operation
  (decisions/min, holds open, approvals latency, verification outcomes,
  adapter failures).
- **In scope:** a `/metrics` (Prometheus text) route; JSON structured logging;
  a minimal dashboards note.
- **Boundary:** read-only derivation from existing evidence; no new evidence
  category; no Core change.
- **DoD:** metrics scrapeable; a held action and a verification failure both
  show up as signals; suite green.
- **Depends on:** nothing. **Rough size:** S.

### T0-4 — CI: finite validation + clean-venv build gate (V1 / V2)

- **Objective:** the validation suite and a `requirements.lock.txt` clean-build
  run automatically on every change.
- **In scope:** a CI workflow (suite + lockfile build + `import app.main`);
  a documented "green = mergeable" gate.
- **Boundary:** CI only.
- **DoD:** CI runs on a branch and blocks on red; the 4.5-minute suite budget
  is documented (operational-loop sleeps).
- **Depends on:** nothing. **Rough size:** S.

### T0-5 — S4 Caddy cutover + S3 separation-of-duties + S5 CORS-from-config

- **Objective:** finish the Security group for threat model (b).
- **In scope:** run the `DEPLOY.md` §1.4 Caddy install (root operator step);
  enforce that the operator who *authored* a held action cannot be the one who
  *approves* it (S3); move the hardcoded CORS origin list out of `app/main.py`
  into config (S5, also fixes the stale `192.168.235.128`).
- **Boundary:** `app/ops/**` + config + deploy artifacts; no Core change.
- **DoD:** LAN TLS entry point live; a same-operator approve is refused with a
  clear error; CORS origins are configurable; suite green.
- **Depends on:** nothing (Caddy artifacts already exist). **Rough size:** S.

---

## 5. Tier 1 — Deepen the homelab capability

The live capability today: CAP-04 continuous loop + CAP-05 governed agent surface
over one Docker component (`uptime-kuma`), RESTART-only, approval-gated.

### T1-1 — Broaden `REMEDIATION_POLICY` coverage

- **Objective:** govern more components and more action types (start/stop/
  recreate, not just restart) on the real homelab.
- **In scope:** add components and action verbs to `REMEDIATION_POLICY`; extend
  the health→action decision logic; keep each entry independent + approval-gated
  unless the owner explicitly relaxes one.
- **Boundary:** stays inside the CAP-04 *safe-enablement envelope*
  (`test_remediation_policy_within_cap04_safe_envelope`); no auto-approval; no
  new adapter; no Core change.
- **DoD:** each new component demonstrated held → approved → executed → verified
  → learned on the live homelab; envelope guard test still passes.
- **Depends on:** T1-3 if any non-independent components are added. **Size:** M.

### T1-2 — Real dependency graph → activate T13 for real

- **Objective:** populate `HOMELAB_DEPENDENCIES` edges so the dependency-cascade
  escalation (`app/agent/dependency_guard.py`) escalates real actions.
- **In scope:** encode the actual homelab dependency map; verify that an
  *allowed* operation on a component with dependents auto-escalates to the
  matching restricted effect and forces approval.
- **Boundary:** data + the existing guard only; the policy/effect model is
  unchanged; no Core change.
- **DoD:** adding an edge is shown to escalate the matching op; removing it
  de-escalates; recorded as a live exercise in `RMT_CAPABILITIES_EVIDENCE.md`.
- **Depends on:** nothing. **Rough size:** S.

### T1-3 — Generalize `continue_remediation` Learn/verify attribution

- **Objective:** run the above-Core Docker verify + executed-Learn closure for
  **any** component that has a `ComponentContext`, not only `REMEDIATION_POLICY`
  components (`uptime-kuma` only today — the recorded 5B-exercise finding).
- **In scope:** widen `app/homelab/continuation.py` attribution; correlate by
  `approval_id` / `execution_id` as now.
- **Boundary:** `app/homelab/**` only; still only *records* evidence after the
  Core has executed; no new authorization or execution path; no Core change.
- **DoD:** a `dozzle`-style component (context but not in `REMEDIATION_POLICY`)
  gets `verified_success` and an executed-Learn record, not just the held-state
  record; suite green.
- **Depends on:** nothing. **Rough size:** S.

### T1-4 — Held-action notification & escalation sink

- **Objective:** turn `notify_held` (O2, log-only today) into a real
  notification path with escalation.
- **In scope:** concrete sinks (Slack / Matrix / ntfy / email); an escalation
  timer ("still unapproved after N minutes → notify a second channel");
  per-hold de-dupe already exists.
- **Boundary:** `app/ops/**` only; fail-open (a notification failure never
  touches the governed path); no Core change.
- **DoD:** a held action reaches a real channel; an un-actioned hold escalates;
  suite green with the sink mocked.
- **Depends on:** nothing. **Rough size:** S. *(Shared with P-E.)*

---

## 6. Tier 2 — New domains on the frozen Core

The Master Definition names Banking Risk Management, Budget Control, AI Agent
Governance, and IT/Cloud Operations as **products built on RMT, not Core work**.
Each domain below is a `domain module + adapter(s) + policy set` consuming the
existing governed boundary. **A domain landing with zero `app/core/**` edits is
the proof the freeze holds.**

### D-1 — AI Agent Governance Gateway (extends CAP-05)

- **Objective:** a first-class surface other teams' agents call to get their
  consequential actions governed — the productization of CAP-05 (5A/5B).
- **In scope:** a stable external API (`propose → hold → human approve →
  execute → verified result`); per-agent identity + scoped/time-limited/
  single-use grants; a multi-agent authority model; dependency-cascade
  escalation (T13); an agent-facing evidence receipt per action; optional
  policy: "agent class X may only ever propose action types {…}".
- **Effective for:** SRE/ops copilots, coding/CI agents (deploy, migrate,
  rotate secrets), customer-service agents (refunds, plan changes, resets),
  spend/procurement agents, research agents running expensive jobs.
- **Boundary:** the agent only *proposes* — never executes, holds authority
  beyond a grant, or continues its own holds; no autonomous loop unless it is a
  separate, separately-approved capability; no Core change.
- **DoD:** two distinct external agents demonstrated end-to-end (one benign,
  one attempting to exceed its grant → refused); evidence receipts verifiable;
  suite green.
- **Depends on:** T0-1 (grant/evidence volume), T0-3. **Rough size:** L.

### D-2 — Cloud / Infrastructure-as-Code Operations

- **Objective:** govern Terraform / Pulumi / CloudFormation changes to real
  cloud environments.
- **In scope:** an adapter that takes a **plan** as the proposed action; risk
  inputs = resource count, destroy count, cost delta, environment tag; approval
  required for prod / for any destroy; execute = `apply`; verify = read back
  resource state / drift; rollback = targeted or state-revert where applicable.
- **Effective for:** environment provisioning, staged prod changes, cost-gated
  resource creation, "who approved this infra change" audit.
- **Boundary:** RMT governs the *change decision and record*, not the cloud
  control plane; not a replacement for a CI/CD system — it is the approval +
  authorization + evidence step inside one; no Core change.
- **DoD:** a plan with a destroy is held, approved, applied, and verified
  against real state in a sandbox account; a cost-over-threshold plan escalates.
- **Depends on:** T0-1, T0-2. **Rough size:** L.

### D-3 — Kubernetes Operations

- **Objective:** govern human- or agent-initiated cluster changes (deploys,
  scaling, node drains, PDB/secret edits, rollouts).
- **In scope:** an adapter over the k8s API; risk = namespace criticality,
  replica delta, whether it touches a singleton / PDB; approval for prod
  namespaces; verify = rollout status / ready replicas; rollback = revision
  rollback.
- **Boundary:** **not** a per-pod reconcile loop (too high-frequency — poor
  fit); it governs discrete change requests, not the controller runtime; no
  Core change.
- **DoD:** a prod deploy is held → approved → applied → verified healthy →
  learned; a bad rollout is caught by verification and rolled back.
- **Depends on:** T0-1, T0-3. **Rough size:** M–L.

### D-4 — Financial / Approval Control (Budget Control · Banking Risk)

- **Objective:** apply the governed lifecycle to money and limit changes —
  disbursements above a threshold, credit/position-limit changes, risk-parameter
  or model-parameter updates, budget allocations.
- **In scope:** a domain module where the "action" is a financial operation;
  policy = threshold tiers, separation of duties (needs T0-5 / S3), dual
  approval for the top tier; execute = call the ledger/limit system via an
  adapter; verify = read back the posted entry / effective limit; evidence =
  the full authorization + approval + verification chain for audit.
- **Effective for:** payment release, procurement/vendor approval, cloud-spend
  authorization, trading limit adjustments (the *limit change*, not the trades),
  entitlement/credential provisioning.
- **Boundary:** **not** transaction execution on a latency path — RMT governs
  the *authorization and record*, the ledger stays the system of record; no
  Core change.
- **DoD:** a below-threshold op auto-approves; an above-threshold op requires
  the correct distinct approver(s); a same-operator approval is refused;
  auditor can reconstruct any decision from evidence alone.
- **Depends on:** T0-1, T0-5 (S3). **Rough size:** L.

### D-5 — Data & ML Operations

- **Objective:** govern consequential data / model changes.
- **In scope:** actions = model promotion/deploy, prod pipeline config change,
  data backfill, GDPR erasure, schema change on a shared dataset, expensive
  training-run authorization; risk = rows affected, irreversibility, cost,
  downstream consumers; verify = serving metrics / row counts / job status;
  rollback = previous model version / restore.
- **Effective for:** MLOps promotion gates, data-deletion approvals with proof,
  GPU budget control.
- **Boundary:** governs the change decision + record, not the training/serving
  runtime; no Core change.
- **DoD:** a model promotion is held → approved → deployed → verified on serving
  metrics → learned; an erasure request produces an auditable completion
  record.
- **Depends on:** T0-1. **Rough size:** M–L.

---

## 7. Tier 3 — Platform & product surface

Cross-cutting enablers that make every Tier 1/2 item cheaper and more usable.

### P-A — Policy-as-configuration

- **Objective:** author approval/risk policy declaratively instead of in code
  (`REMEDIATION_POLICY`, approval policy, dependency map).
- **In scope:** a validated config schema + loader for policy tiers, thresholds,
  approver roles, dependency edges; hot-reload optional.
- **Boundary:** above-Core config only; the *evaluation* engine is unchanged; no
  Core settings-schema change.
- **DoD:** an operator changes a threshold via config + restart with no code
  edit; invalid policy is rejected at load; suite green.
- **Depends on:** nothing. **Rough size:** M.

### P-B — Governed-evidence console (frontend)

- **Objective:** a real read-only web console over the authorization / approval /
  hold / audit / trace / verification evidence and the loop/agent status.
- **In scope:** wire the existing Vite/React app (`projects/homelab-control-
  center/frontend`, dev-config only today) to the read-only routes behind auth;
  an approve/reject action for held items (calls the existing authenticated
  endpoints); correlation view by `action_id`.
- **Boundary:** read + the existing approve/reject endpoints only; no new
  mutation path; no business logic in the frontend; served behind Caddy (T0-5).
- **DoD:** an operator can see every governed action and its evidence chain, and
  approve a hold, from the browser; no new backend capability.
- **Depends on:** T0-5. **Rough size:** M.

### P-C — Evidence export / attestation bundles

- **Objective:** a signed, portable bundle per action (or per time range) for
  compliance, incident review, or handoff to an external auditor.
- **In scope:** a `GET` that assembles the correlated records for an
  `action_id` into a single signed document; a verification tool.
- **Boundary:** read-only derivation; no change to stored evidence; signing key
  management is an operator concern.
- **DoD:** a bundle for a real action verifies offline and contains the full
  `Govern→Verify` chain.
- **Depends on:** T0-1. **Rough size:** S–M.

### P-D — Multi-operator RBAC / IAM integration

- **Objective:** replace the flat `RMT_OPERATOR_TOKENS` map with real
  identities, roles, and (for threat model (c)) an external IdP.
- **In scope:** operator roles (proposer / approver / admin), per-route role
  requirements, OIDC/SAML integration behind the existing `require_operator`
  seam.
- **Boundary:** `app/ops/**` only; the governed path consumes an identity as it
  does now; no Core change. **Only needed if the deployment moves to (c)
  multi-user / internet-reachable.**
- **DoD:** roles enforced per route; an SSO login yields an operator identity in
  the evidence; token map still works as a fallback.
- **Depends on:** T0-5. **Rough size:** M–L.

### P-E — Notification & escalation service

- The Tier 1 item **T1-4** generalized across domains (agent proposals,
  financial holds, infra holds) with per-domain routing and escalation policy.
  Same boundary and DoD shape. **Rough size:** S–M.

---

## 8. Core-change candidate (needs a freeze-deviation authorization)

Everything above is above-Core. **This one is not**, and is listed separately so
it is never bundled into an above-Core proposal by default.

### C-1 — Distinguishable failed-execution verification evidence (E3)

- **Problem:** a *failed* adapter execution currently produces **no**
  verification record — not even `verification_failure` / `state_mismatch` —
  though `AGENTS.md` §11 lists "adapter invoked and failed" as an outcome that
  should be distinguishable. Recorded frozen-Core note.
- **Two paths:**
  1. **Above-Core wrapper** — an `app/ops/` layer that observes the execution
     result and emits a distinguishable above-Core evidence record on failure.
     No freeze deviation. Preferred first attempt.
  2. **Bounded Core fix** — emit the record inside the Core verification path.
     Requires an explicit, separately-authorized freeze deviation with evidence
     that path 1 is insufficient — the same bar E1 met.
- **DoD:** a forced adapter failure yields a durable, queryable record that a
  consumer can tell apart from "verified success" and "observation
  unavailable"; 122 frozen-Core tests unchanged (path 1) or a recorded
  deviation + updated Core suite (path 2).
- **Depends on:** owner decision on path. **Rough size:** S (path 1) / M (path 2).

---

## 9. Recommended sequence

1. **T0-1** (SQLite substrate) — unblocks scale, closes E4/E6, de-risks every
   domain.
2. **T0-3, T0-4, T0-5** in parallel — observability, CI gate, security finish.
3. **T0-2** — platform recovery.
4. **T1-2, T1-3, T1-4** — cheap homelab depth; each is S.
5. Pick **one Tier 2 domain** and prove it end-to-end with zero Core edits.
   `D-1` (Agent Governance Gateway) is the natural first — it extends a live
   capability rather than starting cold, and it is the domain with the clearest
   external demand.
6. **P-B** (evidence console) once one domain is real and there is something
   worth looking at.
7. **C-1 path 1** whenever a domain needs failed-execution evidence; escalate to
   path 2 only with evidence.

Everything else is selected on demand.

---

## 10. Classification summary

| Item | Class | Touches Core? | Prereq |
|---|---|---|---|
| T0-1 SQLite substrate | above-Core substrate | interface unchanged | — |
| T0-2 Platform recovery | operational | no | T0-1 |
| T0-3 Lifecycle observability | above-Core | no | — |
| T0-4 CI gate | tooling | no | — |
| T0-5 S4/S3/S5 finish | above-Core | no | — |
| T1-1 Broaden remediation policy | above-Core / domain | no | T1-3* |
| T1-2 Real dependency graph | above-Core / domain data | no | — |
| T1-3 Generalize continuation Learn | above-Core / domain | no | — |
| T1-4 Held-action notification sink | above-Core | no | — |
| D-1 Agent Governance Gateway | above-Core / domain product | no | T0-1, T0-3 |
| D-2 Cloud / IaC Operations | above-Core / domain product | no | T0-1, T0-2 |
| D-3 Kubernetes Operations | above-Core / domain product | no | T0-1, T0-3 |
| D-4 Financial / Approval Control | above-Core / domain product | no | T0-1, T0-5 |
| D-5 Data & ML Operations | above-Core / domain product | no | T0-1 |
| P-A Policy-as-configuration | above-Core | no | — |
| P-B Governed-evidence console | above-Core / product | no | T0-5 |
| P-C Evidence export / attestation | above-Core / product | no | T0-1 |
| P-D Multi-operator RBAC / IAM | above-Core | no | T0-5 |
| P-E Notification & escalation service | above-Core | no | — |
| **C-1 Failed-execution evidence (E3)** | **Core-adjacent** | **path 1 no / path 2 yes** | owner decision |

---

*Above-Core opportunity roadmap. Does not reopen or modify C01–C07. Does not
create a Core milestone. No item is authorized until the owner selects it and an
approved per-capability proposal exists.*

🤖 Generated with [Claude Code](https://claude.com/claude-code)
