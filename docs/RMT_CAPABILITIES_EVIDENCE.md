# RMT — Above-Core Capability Evidence Index

> **Purpose:** evidence/closure record for above-Core RMT capabilities
> (RMT-CAP-*). These are NOT Core milestones (C01–C07 remain closed/frozen; no
> C08). Each entry records completion, validation, and Core-integrity status.
> This is a coordination/evidence document, not architecture authority.

---

## RMT-CAP-01 — Homelab Operations (Learn closure)

- **Status:** COMPLETED & VERIFIED.
- **Objective:** close the missing Learn stage in the Homelab operational loop;
  demonstrate the full governed lifecycle
  `Understand → Decide → Govern → Authorize → Execute → Verify → Learn`.
- **Implementation:** above-Core only. `app/homelab/remediation.py` now records
  the remediation outcome through the existing frozen Core learning/memory
  capability (`MemoryRecord` + `remember`, append-only/read-only), tied to the
  run via `execution_id`/`approval_id`.
- **Validation:** focused Homelab integration tests pass; full C07/Core suite
  **122 passed** (no regressions); full app suite **141 passed**.
- **Core integrity:** C01–C07 untouched; governed execution semantics
  untouched; no Docker execution required (run-safe mocks).

## RMT-CAP-02 — Engineering Change-Impact & Risk Analysis

- **Status:** COMPLETED & VERIFIED.
- **Objective:** read-only, deterministic, evidence-backed engineering analysis:
  given a proposed change, identify affected components, governance boundaries,
  relevant evidence, engineering-change risk, and a recommendation — all
  traceable to repository/evidence sources.
- **Implementation:** above-Core only. New `app/engineering/` package
  (`models.py`, `repo_index.py`, `service.py`, `api.py`, `testing/`). Consumes
  frozen Core read-only primitives only (`get_modules`, `get_governed_outcomes`,
  `get_previous_failures`, `get_component_context`). Read-only `GET
  /engineering/change-impact` endpoint.
- **Validation:** **14 focused tests passed**; full app suite **155 passed**
  (141 baseline + 14 new). `app.main` imports cleanly.
- **Core integrity:** C01–C07 untouched; no frozen Core file modified; governed
  execution semantics untouched; read-only guarantee verified (no store writes,
  no execution, no authorization, no repository mutation).

### CAP-02 semantic clarification — `unknown_dependency=True`

`unknown_dependency=True` means the component's **dependency knowledge is
incomplete/unestablished** (e.g., the module registry `dependencies` list is
empty or not populated for that component). It does **NOT** mean an actual
unknown dependency was discovered. It is a conservative risk signal that
dependency information is not yet established, not evidence of a real
dependency edge. This is a deterministic, evidence-backed factor; it must not be
misread as a discovered dependency.

## RMT-CAP-03 — Homelab Remediation Approval-Continuation Learn Closure

- **Status:** COMPLETED & VERIFIED (2026-09-06).
- **Objective:** close the Learn-stage gap for **approval-continuation**
  remediations. When a Homelab remediation is held for manual approval,
  `remediate_and_verify()` records only the held state
  (`manual_approval_required`). The human continuation via the frozen Core
  `approve_held_action()` executes and runs Core verification, but nothing
  above-Core observed that executed outcome — so no Learn/`MemoryRecord` was
  written for it, and the above-Core Docker verification never ran. (Finding
  originally recorded in the 2026-09-04 live fault-injection session.)
- **Implementation:** above-Core only.
  - **New** `app/homelab/continuation.py` — `continue_remediation(approval_id,
    approved_by, approved=True)` wraps the frozen Core `approve_held_action()`
    (called unchanged); for an *executed* Homelab remediation it then runs the
    existing above-Core Docker verification (`verify_docker_execution`) and
    records the executed outcome through the existing Core learning/memory
    capability (`record_learning` → `MemoryRecord` + `remember`), correlated by
    `approval_id` / `execution_id`. Non-Homelab holds (e.g. the operator
    `POST /execute` flow) pass straight through, unchanged.
  - **Modified** `app/homelab/remediation.py` — `_record_learning` renamed to
    `record_learning` (now shared) plus clarifying comments; no behavior change.
  - **Modified** `app/main.py` — new route `POST /homelab/approve` →
    `continue_remediation`. Generic `POST /approve` left untouched.
- **Validation:** **5 focused tests passed**
  (`app/homelab/testing/test_continuation.py`); full Homelab suite **21 passed**
  (16 baseline + 5 new); full C07/Core intelligence suite **122 passed**; full
  app suite **160 passed** (155 baseline + 5 new).
- **Core integrity:** C01–C07 untouched; no frozen Core code modified (diff
  confined to `app/homelab/**` + `app/main.py`); `approve_held_action()` called,
  never modified; no new authorization or execution path (the wiring only reads
  the hold and records evidence *after* the Core executes); learning remains
  append-only / read-only.

### C07 test-artifact correction (recorded alongside CAP-03, 2026-09-06)

During CAP-03 validation, `app/core/intelligence/testing/test_http_entrypoints.py`
showed **2 failures** (`TestExecute::test_execute_low_risk_auto_allowed_records_evidence`,
`TestApprove::test_approve_valid_continuation_executes`) — reproducible at the pure
freeze commit `46a4441`, **not** caused by CAP-03. Root cause: the artifact did
not mock the execution adapter, so it implicitly depended on `docker_available()`
being False (safe `simulation` fallback). On 2026-09-04 the Docker socket was
permission-denied, so the suite recorded 122 passed. In the current shell Docker
is reachable, so `_resolve_adapter_name()` selected the real Docker adapter, which
failed on non-existent containers `web1` / `db2`; `execute_governed_action` /
`approve_held_action` skip post-execution verification when `result.success` is
False, leaving the verification store empty and failing the two `>= 1` assertions.
No Core code was wrong. **Correction (owner-approved):** mock the execution
adapter registry in that file's `_isolate_evidence_stores` helper (same pattern
as `test_integrated.py`) so the executed-path transport tests are Docker-daemon
independent. Diff confined to the one test file (+24/−1); no Core code touched;
Core intelligence suite restored to **122 passed**.

---

## RMT-CAP-04 — Continuous Homelab Operational Loop

**Date:** 2026-09-07. Above-Core capability. C01–C07 remain closed/frozen; no
C08; no frozen Core code modified. Approved scope: `docs/RMT_CAP_04_PROPOSAL.md`.

- **Objective:** run the existing single-shot Homelab governed lifecycle
  (`Understand → Decide → Govern → Authorize → Execute → Verify → Learn`) on a
  cadence, under supervision — the frozen Core as a continuous homelab control
  plane. Adds **cadence + guardrails only**, no new mutation path.
- **Implementation:** above-Core only.
  - **New** `app/homelab/operational_loop.py` — `HomelabOperationalLoop`
    (module singleton `operational_loop`). Each cycle iterates
    `REMEDIATION_POLICY` components and calls the existing
    `remediate_component(component)` entrypoint; classifies the governed
    outcome; updates per-component loop state; appends a bounded cycle record.
    Guardrails: **approval retained** (a `manual_approval_required` outcome is
    recorded, never continued — `continue_remediation` is not imported here);
    **flap guard** (N held/failed attempts within a window → component
    quarantined, read-only recovery checks only until healthy streak or manual
    clear); **cooldown** after every attempt; **duplicate-hold guard**
    (a read-only query of the approval hold store — if a `pending` hold already
    exists for the component the loop returns `awaiting_approval` instead of
    routing another remediation: no second hold, no flap count, no spurious
    quarantine of something merely waiting for a human); **single-flight**
    (cycles never overlap); **fail-safe** (per-component and per-cycle
    `try/except`; the task never raises into the app). State transitions
    (quarantine / recovery /
    manual clear) are recorded append-only through the existing Core memory
    capability (`remember` + `MemoryRecord`) with distinct `event_type`s
    (`homelab_loop_quarantine`, `homelab_loop_recovery`,
    `homelab_loop_quarantine_cleared`).
  - **New** `app/homelab/loop_config.py` — env-overridable constants
    (`LOOP_ENABLED` default **False**, interval 120s, flap window/threshold,
    cooldown, recovery streak, history cap). No `app/core/configuration/**`
    change.
  - **Modified** `app/main.py` (+52) — `lifespan` starts the loop task only
    when `LOOP_ENABLED`, and stops it on shutdown; new routes
    `GET /homelab/loop/status` (read-only), `POST /homelab/loop/start`,
    `POST /homelab/loop/stop`, `POST /homelab/loop/clear?component=`.
  - **New** `app/homelab/testing/test_operational_loop.py` — 17 run-safe tests
    (`remediate_component`, `observe_container_state`, `remember` and the
    approval hold + record stores all mocked/isolated; asyncio task never
    started).
- **Validation:** **17 focused tests passed** (11 loop behaviour + 5
  duplicate-hold guard + 1 T13 safe-envelope guard); full Homelab suite
  **38 passed** (21 baseline + 17); full C07/Core intelligence suite
  **122 passed** (unchanged); full app suite **177 passed** (160 baseline + 17).
  `import app.main` clean; loop confirmed **disabled by default**.
- **Enabled on the live server (2026-09-07):** owner-authorized. systemd
  drop-in `rmt-control-center.service.d/cap04-loop.conf`
  (`RMT_HOMELAB_LOOP_ENABLED=true`). Enablement surfaced a **frozen-Core
  hold-persistence gap** — `approve_held_action` flips `hold.status` in memory
  but does not reliably persist the approval **hold** store, so holds
  approved/rejected days ago can read `pending` on disk after a restart. The
  duplicate-hold guard was hardened (above-Core, still read-only): a PENDING
  hold blocks a new remediation only while **still-actionable** — no terminal
  decision in the reliably-persisted approval **record** store, and not past its
  `APPROVAL_HOLD_TTL_SECONDS` TTL. Recorded as a frozen-Core note (owner
  consideration only). Redeployed 2026-09-07; the live loop then sat at `no_remediation` (2 clean cycles, no errors).
- **Live demonstration (real homelab, 2026-09-07):** owner-authorized. Isolated
  second instance on :8001 (systemd :8000 untouched). Fault-injected
  `uptime-kuma` (governed stop) → loop cycle held for approval
  (`manual_approval_required`, no mutation) → cooldown/flap guard fired →
  `POST /homelab/approve` → **executed** via the `docker` adapter
  (execution `40b3dce9…`) → above-Core Docker verification **`verified_success`**
  → loop observed recovery and stood down (`no_remediation`). Full correlated
  evidence bundle (approval / authorization / trace / audit / verification /
  Learn ids 275–278) recorded in `HANDOFF.md` (session note — CAP-04 first live
  demonstration). Result: **PASS**; approval retained throughout; no
  portainer/dozzle impact; no code change.
- **Core integrity:** diff confined to `app/homelab/**` + `app/main.py`; no
  `app/core/**` file modified; no second mutation boundary (routes through
  `execute_governed_action` via the existing entrypoint only); approval
  enforcement unchanged; learning append-only / read-only.
- **MCR / T13 — disposition recorded 2026-09-07** (`docs/RMT_T13_DISPOSITION.md`):
  **ACCEPT (with constraint) + BOUND + DEFER.** T13 is a policy-completeness
  gap in the MCR-EXP-3 simulation, not a live defect in RMT Core or CAP-01..04
  (verified: no Core dependency graph / no composition; CAP-04 ships one
  independent RESTART-only, approval-gated component). CAP-04 may be **enabled**
  only inside the *safe-enablement envelope* — every `REMEDIATION_POLICY` entry
  independent (no dependency edge) and `requires_approval=True` — enforced by
  `test_remediation_policy_within_cap04_safe_envelope`. The full fix (an
  above-Core dependency-cascade escalation pre-check that forces human approval
  when an allowed op would achieve a restricted effect via dependencies) is
  **assigned to CAP-05** and is **not** required to enable CAP-04 within the
  envelope.

---

## RMT-CAP-05 (5A) — Governed Agent Surface

**Date:** 2026-09-07. Above-Core capability. C01–C07 remain closed/frozen; no
C08; no frozen Core code modified. Approved scope: `docs/RMT_CAP_05_PROPOSAL.md`
(**5A only** — the LLM agent 5B remains a separate deferred decision).

- **Objective:** implement the MCR child-contract surface (Identity, Intent,
  Authority, Proposed Action, Decision, Outcome) so an agent can **propose** a
  consequential homelab operation that is routed through the frozen Core's
  single governed boundary — the same path a Homelab remediation takes. The
  agent never executes, authorizes, approves, or continues a hold.
- **Implementation:** new `app/agent/` package (above-Core):
  - `contract.py` — `AgentIdentity` / `AgentIntent` (goal kept distinct from
    mechanism) / `AgentProposal` / `AgentOutcome`.
  - `authority.py` — `AuthorityStore`: operation+target-scoped, time-limited
    (`AGENT_GRANT_TTL_SECONDS`), **single-use** grants; capability never implies
    authority (MCR §9 / MCR-EXP-3 T8+T9). Consumed only when a proposal is
    accepted into the pipeline (executed / held), never on a pre-boundary deny.
  - `dependency_guard.py` — **T13 closure** (`docs/RMT_T13_DISPOSITION.md` §3c;
    disposition now **CLOSED**). `escalate_for_dependency_cascade(target, op)`:
    an allowed-class op (`start`/`create`) whose target has a dependent
    component is forced to `requires_approval=True`. Dependency edges are the
    **union** of the above-Core `app/homelab/dependencies.py` map (authoritative
    for the homelab; recorded 2026-09-07 as **all-independent**) and the frozen
    Core `ComponentContext.dependencies` (untouched, future-proofing). No edges
    today → escalates nothing, but live: adding any edge to either source makes
    the matching allowed op escalate automatically. Resolved map at
    `GET /agent/status` → `dependency_map`.
  - `adapter.py` — `propose_and_govern(proposal)`: disabled gate → authority
    check → T13 escalation → translate to `ActionRequest` →
    `execute_governed_action(...)` → on `executed`: above-Core Docker
    verification + `record_learning`; on `manual_approval_required`:
    `record_learning`, **never** auto-continued. Boundary exceptions are
    contained (`decision="error"`, grant intact).
  - `reference_agent.py` — deterministic agent: `HealthEvaluation` CRITICAL →
    RESTART `AgentProposal`; else `None`. No model, no network.
  - `api.py` — `POST /agent/authority/grant` (operator issues a grant),
    `POST /agent/act` (propose → governed lifecycle), read-only
    `GET /agent/status` and `GET /agent/authority`.
  - `app/main.py` — register the `app/agent` router (additive only).
  - **New route beyond the proposal's list:** `POST /agent/authority/grant` — the
    operator action that makes the surface usable (a human grants the agent its
    scoped authority; capability ≠ authority). Still no mutation path; a granted
    proposal still passes full policy / risk / approval.
- **Validation:** **20 focused tests passed** (`app/agent/testing/` —
  13 `test_agent_governance.py` + 7 `test_dependency_guard.py`); full C07/Core
  intelligence suite **122 passed** (unchanged); full Homelab suite **38 passed**
  (unchanged); full app suite **197 passed** (177 baseline + 20). `import
  app.main` clean; `RMT_AGENT_ENABLED=False` confirmed by default.
- **T13 completed 2026-09-07:** new above-Core `app/homelab/dependencies.py`
  (`HOMELAB_DEPENDENCIES`, all three services recorded independent);
  `dependency_guard.py` unions it with the Core context; `GET /agent/status`
  exposes the resolved map. `docs/RMT_T13_DISPOSITION.md` verdict moved to
  **ACCEPT + BOUND + CLOSED**.

### RMT-CAP-05 (5B) — LLM-Backed Agent Adapter

**Date:** 2026-09-07. Above-Core. Owner approved the scope
(`docs/RMT_CAP_05B_PROPOSAL.md`). C01–C07 remain closed/frozen; no C08; no
`app/core/**` change. **Disabled by default** (`RMT_AGENT_LLM_ENABLED`).

- **Objective:** a local LLM turns a natural-language goal into a structured
  `AgentProposal`, then the proposal runs the **identical 5A path**
  (`propose_and_govern` → authority → T13 → governance → human approval). The
  LLM only proposes — no execution, no tool calls, no authority, no continuation.
- **Implementation:**
  - **New** `app/agent/llm_client.py` — stdlib `urllib` Ollama client (the
    `experiments/mcr3/atlas.py` pattern; no new dependency).
  - **New** `app/agent/llm_agent.py` — `LlmAgent.propose(goal, observations,
    grant_id)`. Strict single-JSON-object parse; **fail-closed** validation:
    `target` ∈ known homelab components, `mechanism` ∈ `ActionType`,
    `confidence` int 0–100; `propose:false` / missing / non-JSON / transport
    error → `LlmProposalError(reason)` with `reason` ∈
    `{no_proposal, invalid_proposal, llm_parse_error, llm_error}` — never a
    partial or guessed proposal.
  - **Modified** `app/agent/loop_config.py` — `AGENT_LLM_ENABLED` (default
    **False**), `AGENT_LLM_MODEL` (`deepseek-v4-flash:cloud`),
    `AGENT_LLM_HOST` (`http://127.0.0.1:11434`), timeout / max-tokens /
    temperature.
  - **Modified** `app/agent/api.py` — `POST /agent/act/llm` {goal, grant_id}:
    disabled → `llm_disabled` (no model call); `LlmProposalError` → that reason;
    valid → `propose_and_govern(...)` → the 5A `AgentOutcome`. `GET /agent/status`
    gains a read-only `llm` block.
- **Validation:** **17 focused tests** (`app/agent/testing/test_llm_agent.py`) —
  parse of valid / `propose:false` / unknown target / bad mechanism / bad
  confidence / non-JSON / prose-wrapped JSON; transport error → `llm_error`;
  endpoint disabled gate; valid proposal → governed hold; no grant →
  `no_authority` (LLM does not bypass authority); invalid target never reaches
  governance; **semantic-injection shape** (structurally valid but
  goal-mismatched target) → still `hold` for human approval (documents that
  approval, not validation, is the catch). Agent suite **37** (20 + 17); Core
  **122**, Homelab **38** (both unchanged); full app **214** (197 + 17).
  `import app.main` clean; `RMT_AGENT_LLM_ENABLED=False` and
  `RMT_AGENT_ENABLED=False` by default.
- **Core integrity:** diff confined to `app/agent/**`. No second mutation
  boundary — an LLM proposal becomes an `AgentProposal` → `propose_and_govern`
  → `ActionRequest` → `execute_governed_action` only. Approval / T13 / authority
  / Learn inherited from 5A unchanged. No autonomous LLM loop (one goal → at
  most one proposal). Claim C not claimed (the LLM has no code path).
- **Deferred / not done:** enabling 5B on the live server (a further explicit
  step); wiring the LLM into the CAP-04 operational loop; any multi-step
  reasoning loop.
- **Core integrity:** diff confined to `app/agent/**` + `app/main.py` (router
  registration). No `app/core/**` change; no second mutation boundary (a
  proposal becomes an `ActionRequest` routed through `execute_governed_action`
  only); approval enforcement unchanged; held proposals never auto-continued;
  learning append-only / read-only. Disabled by default.
- **Deployed to live + controlled exercise (2026-09-07):** owner-authorized.
  `sudo systemctl restart` deployed the `/agent/*` routes to live :8000, agent
  **OFF** (`enabled: false`). Exercise on a temp `RMT_AGENT_ENABLED=true`
  instance (live loop paused for the window): no-grant → `no_authority`; grant
  issued → propose RESTART uptime-kuma → **held** for approval; replay same
  grant → `grant_consumed`; approve → **executed** via `docker` adapter
  (execution `e3f3de2d…`) → above-Core Docker verify **`verified_success`** →
  Learn `manual_approval_required` then `executed`. Authorization
  `decision_id` = `agent-reference-agent-…` (agent-surface origin). Result:
  **PASS**; capability≠authority and single-use both enforced; no
  portainer/dozzle impact; live loop resumed clean. Full bundle in `HANDOFF.md`.
- **Deferred:** 5B (LLM-backed agent adapter) — a separate owner decision;
  nothing built. Populating `ComponentContext.dependencies` (which would make
  the T13 guard load-bearing) is also a separate explicit change.

### RMT-CAP-05 (5A + 5B) — enabled on the live server + controlled LLM exercise (2026-09-07)

**Owner:** selected candidate 1 ("enable 5A / 5B on live + a controlled LLM
exercise"); "both 5A + 5B on live now"; exercise target `dozzle`. Above-Core;
**no code change** — enablement + operational exercise + this record only.

**Enablement (live :8000).** New systemd drop-in
`/etc/systemd/system/rmt-control-center.service.d/cap05-agent.conf`
(`Environment=RMT_AGENT_ENABLED=true` + `Environment=RMT_AGENT_LLM_ENABLED=true`);
`daemon-reload` + `restart`. `GET /agent/status` → `enabled: true`,
`llm.enabled: true` (`deepseek-v4-flash:cloud` @ `127.0.0.1:11434`),
`active_grants: 0`. The agent surface has **no background task** — it is inert
until an operator issues a grant *and* approves the resulting hold. CAP-04 loop
unaffected (still enabled, `no_remediation`, not quarantined). Disable = delete
that file + `daemon-reload` + `restart`.

**Controlled LLM exercise — live :8000, target `dozzle`** (not in the CAP-04
`REMEDIATION_POLICY`, so the loop neither reacts nor needs pausing;
`portainer` / `uptime-kuma` untouched throughout):

1. `POST /agent/act/llm` **no grant** → `no_authority` / `no_grant`. The LLM
   produced a valid `dozzle` proposal; it was stopped before the governed
   boundary (capability ≠ authority).
2. `POST /agent/act/llm`, healthy state + a "only act if something is broken"
   goal → `no_proposal` ("model did not propose an action") — fail-closed, no
   spurious proposal.
3. Governed fault-injection `POST /execute?operation=stop&target=dozzle` →
   execution `24b5d25f…` completed → `dozzle` `exited`.
4. `POST /agent/authority/grant` {`restart`, `dozzle`,
   `cap05-llm-exercise-operator`} → grant `0720df95…`. `POST /agent/act/llm`
   with it → `no_authority` / **`grant_scope_mismatch`** — the model proposed
   `start` (a stopped container), not `restart`; the scope check held. (Model
   mechanism choice is nondeterministic across calls; the allow-list is
   `ActionType`, the *grant* is operation-scoped.)
5. `POST /agent/authority/grant` {`start`, `dozzle`, …} → grant `6c596894…`.
   `POST /agent/act/llm` → **`decision: hold`**, `governed_status:
   manual_approval_required`, `approval_id c7b3e598…`, `escalated: false`,
   `learn_recorded: true`, `agent_id: llm-agent`, `mechanism: start`,
   `confidence: 95`. No execution.
6. `POST /agent/act/llm` **replay the same grant** → `no_authority` /
   **`grant_consumed`** (single-use enforced).
7. `POST /homelab/approve?approval_id=c7b3e598…&approved_by=cap05-llm-exercise-operator`
   → **`executed`** via the `docker` adapter: execution `37ab18bf…`, action
   `becbf4d0…`, "start on dozzle" success. Core verifier `observation_unavailable`
   (fail-safe).
8. `dozzle` `running` (restarted 11:26:29). Stray `restart` grant `0720df95…`
   self-expired at its TTL → `active_grants: 0`. CAP-04 loop `no_remediation`.

**Evidence bundle** (correlated by action `becbf4d0…` / execution `37ab18bf…`
/ approval `c7b3e598…`):

- **authorization** `33eed7bb…` — type `manual`,
  `authorized_by cap05-llm-exercise-operator`,
  **`decision_id = agent-llm-agent-3c15347d`** (proves LLM-agent-surface
  origin), single-use, 5-min TTL, status `approved`.
- **trace** `455c8db4…` — policy `allow`, risk `low`, outcome `completed`.
- **audit** — adapter `docker`, status `completed`, risk `low`.
- **verification** `94235f26…` — `observation_unavailable` (Core fail-safe).
- **approval_record** `c7b3e598…` — `decision approved`,
  `approved_by cap05-llm-exercise-operator`. (The **hold** store reads
  `pending` on disk — the known frozen-Core hold-persistence note; the record
  store is authoritative.)
- **Learn** (`intelligence_memory` id 336) — `dozzle / remediation`
  `manual_approval_required`, `approval_id c7b3e598…`, `confidence 95` — the
  held-state record, written by the agent adapter.

**Finding — recorded, not a defect.** The above-Core CAP-03 Learn-closure
(executed-outcome Learn record + above-Core Docker-observer
**`verified_success`** verification) **did not run** for this exercise, because
`continue_remediation` (`/homelab/approve`) early-returns for any component not
in `REMEDIATION_POLICY`, and that policy contains only `uptime-kuma` (the CAP-04
safe envelope). So an agent proposal approved via `/homelab/approve` gets the
full above-Core Learn/verify closure **only when its target is in
`REMEDIATION_POLICY`** — for `uptime-kuma` (the 5A exercise, 2026-09-07) it did
(`verified_success`); for `dozzle` it was skipped. The governed Core lifecycle,
durable evidence, scoped/single-use authority, and the held-state Learn record
all ran correctly for `dozzle`. **Owner consideration:** widen the above-Core
verify/Learn attribution in `continue_remediation` beyond `REMEDIATION_POLICY`
(e.g. any component with a `ComponentContext`), or accept it as scoped-by-design.

**Result: PASS.** On the live server with both agent flags enabled:
`deepseek-v4-flash:cloud` → structured `AgentProposal` → scoped single-use
authority → T13 (no-op; no edges) → governance → **human approval** → governed
`docker` execution → Core verification → correlated durable evidence.
Structural allow-list validation (`no_proposal`), grant scope
(`grant_scope_mismatch`), single-use (`grant_consumed`), and capability ≠
authority (`no_grant`) all enforced against the live LLM path. No
`portainer` / `uptime-kuma` impact; systemd service and CAP-04 loop unaffected.

---

## Tier 1 homelab-depth batch — T1-2 / T1-3 / T1-4 (2026-09-09)

**Owner:** selected the "T1 homelab-depth batch" from
`docs/RMT_ABOVE_CORE_ROADMAP.md` §5; escalation driver = external script +
read-only route. Scope: `docs/RMT_T1_BATCH_PROPOSAL.md` (APPROVED). Above-Core;
**no `app/core/**` change**; no new mutation path; no C08.

### T1-2 — Operator-declarable dependency graph → T13 activatable without a redeploy

- **New** `ops_config.homelab_dependency_edges()` parses
  `RMT_HOMELAB_DEPENDENCIES` (`"web:db;api:db,cache"`). **Modified**
  `app/homelab/dependencies.py` — the accessors (`dependencies_of` /
  `dependents_of` / `resolved_map`) union the static all-independent map with
  the env edges; new `dependency_sources()` splits `static` / `env`. **Modified**
  `app/agent/dependency_guard.py::dependency_view()` — adds `sources` to
  `GET /agent/status.dependency_map`. The T13 escalation **rule**
  (`escalate_for_dependency_cascade`) is untouched.
- Recon confirmed the real homelab has **no** inter-container edges (portainer /
  dozzle / uptime-kuma each need only the Docker daemon), so this ships unset in
  production. It removes the "edit code + redeploy" step that previously stood
  between an operator and declaring a real edge.
- **Live exercise (dev host :8000 — recorded here):**
  `RMT_HOMELAB_DEPENDENCIES` unset → `escalate_for_dependency_cascade("portainer",
  "start")` = `(False, "")`, `GET /agent/status.dependency_map.sources.env` =
  `{}`. Set `RMT_HOMELAB_DEPENDENCIES="uptime-kuma:portainer"` → the same call
  returns `(True, "T13: allowed op 'start' on 'portainer' would propagate to
  dependent(s) ['uptime-kuma'] …")`, `sources.env` =
  `{"uptime-kuma": ["portainer"]}`, and a `start portainer` agent proposal is
  forced to `manual_approval_required` (`decision: escalated_hold`). Unset again
  → back to `(False, "")`. No container mutated.
- **Tests:** `app/homelab/testing/test_dependencies.py` (9) + a new
  operator-env-edge case in `test_dependency_guard.py`.

### T1-3 — Generalized `continue_remediation` Learn/verify attribution

- **Modified** `app/homelab/continuation.py` — the above-Core Docker verify +
  executed-Learn closure now runs for **any component with a
  `ComponentContext`** (`get_component_context(...) is not None`), not only
  `REMEDIATION_POLICY` components. Closes the finding recorded in the
  CAP-05 (5A+5B) live exercise: a `dozzle`-style agent proposal approved via
  `POST /homelab/approve` now gets `verified_success` + an executed-Learn record
  correlated by `approval_id` / `execution_id`, not just the held-state record.
- A held action whose component has **no** `ComponentContext` (the operator
  `POST /execute` → hold flow) still passes through to the Core continuation
  untouched — no Learn record, no Docker verification.
- **Tests:** `test_continuation.py` — new `dozzle` context-component cases
  (`verified_success` + `state_mismatch`); the existing no-context negative
  test still passes unchanged.

### T1-4 — Held-action notification: real-channel shaping + missed-approval escalation

- **New** `RMT_NOTIFY_FORMAT` (`generic` default / `slack` / `ntfy`) in
  `ops_config` + a `_post()` shaper in `app/ops/notifications.py` — the existing
  `RMT_NOTIFY_WEBHOOK_URL` can now point straight at a Slack incoming-webhook or
  an ntfy topic. `generic` output is byte-identical to before. Still fail-open,
  de-dupe unchanged.
- **New** `app/ops/held_holds.py::open_holds_view()` (read-only) + **new**
  route `GET /ops/holds` (operator-authenticated) — classifies every PENDING
  hold: `age_seconds`, `expires_at`, `expired`, `record_terminal` (the
  authoritative approval **record** already resolved it), `actionable`, plus S3
  provenance. Derives from the durable hold + record stores; writes nothing;
  `[]` on any error.
- **New** `backend/scripts/rmt-escalate.sh` — cron/timer; reads `/ops/holds` and
  POSTs a **one-time** alert to `RMT_ESCALATE_WEBHOOK_URL` for a hold that is
  either still `actionable` past `RMT_ESCALATE_AFTER_SECONDS` (default 180; the
  script warns if it is not `< 300`, the frozen-Core hold TTL) **or** `expired`
  while never approved. Each `approval_id` escalates once (state file). Matches
  the D4 / O3 external-check pattern — **no in-process background task**.
- **Frozen-Core constraint noted, not worked around:** `APPROVAL_HOLD_TTL_SECONDS
  = 300`. A hold nobody approves simply expires; the "expired-unapproved" branch
  of the escalation is the design's answer to that.
- **Tests:** `app/ops/testing/test_held_holds.py` (12: classification + route
  auth/shape + fail-open) + `test_notifications.py` new format cases (slack /
  ntfy / generic-unchanged / unknown→generic).

**Core integrity.** Diff confined to `app/homelab/**`, `app/agent/dependency_guard.py`
(`dependency_view` only), `app/ops/**`, one read-only route in `app/main.py`, one
script, and docs. No `app/core/**` change. No new authorization or execution
path. Learning append-only / read-only. Every new knob defaults to inert.

**Validation.** Full backend suite **389 passed** (365 baseline + 24 new:
`test_dependencies.py` ×9, `test_dependency_guard.py` +1,
`test_continuation.py` +2, `test_held_holds.py` ×8, `test_notifications.py` +4).
Core intelligence suite **122** unchanged. `import app.main` clean; all agent /
loop flags OFF by default.

**Not deployed.** New env vars have safe defaults; `GET /ops/holds` is additive;
`rmt-escalate.sh` is cron-only. A redeploy picks them up. The T1-2 live edge
exercise needs a `deps.conf` drop-in + restart (owner-run) to repeat on live.

---

## Index

| Capability | Status | Validation | Core integrity |
|---|---|---|---|
| RMT-CAP-01 — Homelab Operations (Learn closure) | COMPLETED & VERIFIED | 122 Core + 141 full | C01–C07 untouched |
| RMT-CAP-02 — Engineering Change-Impact & Risk Analysis | COMPLETED & VERIFIED | 14 focused + 155 full | C01–C07 untouched |
| RMT-CAP-03 — Homelab Remediation Approval-Continuation Learn Closure | COMPLETED & VERIFIED | 5 focused + 122 Core + 160 full | C01–C07 untouched; no frozen Core code modified |
| RMT-CAP-04 — Continuous Homelab Operational Loop | COMPLETED & VERIFIED; live-demonstrated + enabled on live 2026-09-07 | 17 focused + 38 Homelab + 122 Core + 177 full; live run PASS | C01–C07 untouched; no `app/core/**` modified; T13 disposition recorded; duplicate-hold guard hardened against frozen-Core hold-persistence gap |
| RMT-CAP-05 (5A) — Governed Agent Surface | COMPLETED & VERIFIED (5A); **enabled on live 2026-09-07** + exercised | 20 focused + 122 Core + 38 Homelab + 197 full; live exercise PASS | C01–C07 untouched; diff confined to `app/agent/**` + `app/homelab/dependencies.py` + `app/main.py`; no new mutation path; **T13 CLOSED** (guard live, homelab recorded independent); every proposal human-approval-gated |
| RMT-CAP-05 (5B) — LLM-Backed Agent Adapter | COMPLETED & VERIFIED 2026-09-07; **enabled on live 2026-09-07** + controlled LLM exercise PASS | 17 focused + 37 agent + 122 Core + 38 Homelab + 214 full; live LLM exercise PASS | C01–C07 untouched; diff confined to `app/agent/**`; LLM proposes only → 5A path unchanged; no new mutation path; no autonomous loop; live exercise recorded a scoped-by-design gap in `continue_remediation` (above-Core Learn/verify closure only for `REMEDIATION_POLICY` components) |
| Tier 1 batch — T1-2 operator-declarable dependency edges | COMPLETED & VERIFIED 2026-09-09 | `test_dependencies.py` ×9 + `test_dependency_guard.py` +1 + 389 full; dev-host edge exercise PASS | no `app/core/**` change; escalation rule untouched; static map still all-independent; ships unset |
| Tier 1 batch — T1-3 generalized `continue_remediation` attribution | COMPLETED & VERIFIED 2026-09-09 | `test_continuation.py` +2 + 122 Core + 389 full | no `app/core/**` change; keyed on `ComponentContext`; no-context holds pass straight through; closes the recorded 5B `dozzle` finding |
| Tier 1 batch — T1-4 held-action channel shaping + escalation | COMPLETED & VERIFIED 2026-09-09 | `test_held_holds.py` ×8 + `test_notifications.py` +4 + 389 full | no `app/core/**` change; `generic` output byte-identical; escalation is out-of-process (`GET /ops/holds` + `rmt-escalate.sh`), no in-process timer; 300 s Core hold TTL a recorded constraint |

**Boundaries:** No C08. No Core changes. No reopening of C01–C07. Above-Core
capabilities remain subordinate to RMT's governance architecture.
