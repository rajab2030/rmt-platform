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

## B1a — Strengthen the Verify stage: above-Core observer layer (2026-09-10)

Proposal: `docs/RMT_B1_PROPOSAL.md` (APPROVED by split; §9 completion note).
Frozen-Core gap this compensates: `docs/RMT_FROZEN_CORE_DEBT.md` **D3**
(`_resolve_trusted_observer` resolves an observer only for module `create`).

- **New `app/ops/verification/`** — an above-Core observer *registry*
  (`register_observer` / `resolve_observer`, `(adapter, operation)` → factory),
  the single `expected_state_for` table, the Docker observer registration, and
  `verify_executed_action(...)`: resolve a read-only observer, settling-poll it
  (`RMT_VERIFY_OBSERVE_TIMEOUT_S`, default 5, `0` = single-shot, early-return on
  match), feed the observation to the **frozen** `verifier.verify` +
  `verification_storage.save`, and prefix `result.reason` with
  `[layer=above_core adapter=… supersedes=observation_unavailable]`. No observer
  → returns `observation_unavailable` and writes nothing (the Core already saved
  one). `verification_storage` dereferenced through its module at call time (R10).
- **`observe_container_state`** — reachable-and-gone now returns
  `ObservedState(state="absent")`; `None` is reserved for "could not observe".
  Makes `remove` verifiable.
- **Wired in** — the 3 `verify_docker_execution` call sites
  (`remediation.py` / `continuation.py` / `agent/adapter.py`) now call
  `verify_executed_action`; `app/homelab/verification.py` deleted;
  `POST /execute` calls it after the E3 hook and returns
  `above_core_verification_status`.

**Core integrity.** No `app/core/**` change (verified: `git diff` touches no
`app/core/` path). Frozen verifier / storage / models reused unchanged; no new
mutation path; observers are read-only.

**Validation.** Full backend suite **433 passed** (`ruff` F/E9 clean; `import
app.main` clean). Core intelligence suite **134 passed**, unchanged by this work.
New: `app/ops/verification/testing/test_service.py` (registry, table, `absent`,
settling poll early-return + one transient reading, single-shot, reason token,
`supersedes=`, no-observer-writes-nothing, restart/stop/remove `verified_success`,
`state_mismatch`, caller-`expected` wins) + `test_execute_route.py` (4).
`test_e2e_docker.py` (real `docker restart` of a disposable container) **2
passed** through the new entrypoint.

---

## B1b — Verify stage: effective-status index + inconclusive surfacing (2026-09-10)

Plan: `docs/RMT_B1b_RECON.md` (owner-approved; decisions: in-memory index;
`rmt_verifications_total` left raw). `docs/RMT_B1_PROPOSAL.md` §10.

- **New `app/ops/verification/index.py`** — an in-memory, read-only projection
  keyed by `execution_id` that collapses the Core `observation_unavailable` +
  the above-Core record into one **effective status** (precedence per
  proposal §2.3: E3 `adapter_execution_failed` → deferred, not `unverified`;
  above-Core record → its status; `module_change` → Core status; else
  `unverified`). Rebuilt from the durable evidence + audit store on startup —
  **silent**, marks history `notified_inconclusive` so it never re-alerts.
- **`verify_executed_action`** now takes `action_id`, updates the index in both
  branches, and — once per `execution_id` — fires one low-severity
  `notify_ops(kind="verification_inconclusive", …)` when the effective status is
  `unverified`.
- **`GET /ops/verifications`** (operator-authenticated, `?limit=` /
  `?effective_status=`) — per executed action, whether it was verified and why
  not. **`/metrics`** gains `rmt_executed_actions_total{adapter,operation}` +
  `_verified_total` / `_unverified_total` / `_state_mismatch_total` from the
  index projection (`rmt_verifications_total` unchanged). `POST /execute`
  response gains `effective_verification_status`.

**Core integrity.** No `app/core/**` change (verified). Frozen verifier /
storage / models reused unchanged; the index is a read-only projection; no new
mutation path.

**Validation.** Full backend suite **455 passed** (exit 0); `ruff` (F, E9)
clean; `import app.main` clean; Core intelligence suite **134 passed**,
unchanged. New: `test_index.py` (rebuild precedence ×4 + silent/history +
`record` upsert + `view` filter/limit/never-raises),
`test_ops_verifications_route.py` (auth + filters), `test_service.py` /
`test_execute_route.py` / `test_metrics.py` additions.

**Live exercise (real container).**
`test_e2e_docker.py::test_operator_execute_http_verified_through_index` — a real
`docker restart` driven through `POST /execute` (operator HTTP path) →
`effective_verification_status == "verified_success"` + one index row
(`verified=True`, `adapter="docker"`, `operation="restart"`), correlated by
`execution_id`. The inconclusive path is covered by
`test_service.py::test_unverified_fires_exactly_one_inconclusive_notification`
(simulation adapter → `unverified` → one `verification_inconclusive` + counter).

---

## C1 / T1-1 — Broaden `REMEDIATION_POLICY` coverage (2026-09-11)

Plan: `docs/RMT_IMPROVEMENT_ROADMAP.md` §5 C1 (Size S — per the roadmap's own
authority rule, an S item needs owner selection only, no separate proposal
doc). Above-Core; no `app/core/**` change; no C08.

- **Modified** `app/homelab/remediation.py` — added `portainer` as a second,
  independently-governed `REMEDIATION_POLICY` entry (`RESTART` on `CRITICAL`,
  `expected_state="running"`, `requires_approval=True`) — identical shape to
  `uptime-kuma`. `portainer` was already confirmed dependency-free in
  `docs/RMT_T13_DISPOSITION.md` and already monitored by the collector, so no
  other above-Core wiring was needed. `dozzle` was deliberately **not** added:
  it is the load-bearing example — exercised by `test_continuation.py` (T1-3)
  and the CAP-05B live-exercise finding — of a component with a
  `ComponentContext` that stays outside `REMEDIATION_POLICY`, and stays that
  way.
- The operational loop (`app/homelab/operational_loop.py`) needed **zero**
  changes — it already iterates `REMEDIATION_POLICY.keys()` generically; a
  second entry is picked up automatically.
- The `start`-for-a-stopped-container verb mentioned in C1's scope was
  evaluated and **not** implemented: within the actual remediation path
  (`create_health_evaluation`), `CRITICAL` is reachable only via "component not
  running", and Docker's `restart` already starts a stopped container, so a
  separate verb would change no observable behavior today. Left as a documented
  non-change rather than speculative branching.
- **Tests:** `test_remediation.py` — `test_healthy_portainer_produces_no_remediation_action`,
  `test_critical_portainer_builds_restart_action_with_evaluation_confidence`,
  `test_portainer_remediation_reaches_governed_boundary_and_continues` (mirrors
  the existing `uptime-kuma` coverage exactly). `test_operational_loop.py` —
  `test_loop_processes_second_live_policy_component` drives the **real**
  `REMEDIATION_POLICY` (not a synthetic fixture) through one cycle, holding one
  component and clearing the other in the same pass. `test_remediation_policy_within_cap04_safe_envelope`
  (T13 guard) re-verified against the two-entry policy: still passes
  unmodified.

**Core integrity.** Diff confined to `app/homelab/remediation.py` +
`app/homelab/testing/**` (2 files). No `app/core/**` change (verified via
`git diff --stat`). No new mutation path; approval retained on every entry;
the CAP-04 T13 safe-envelope guard stays green with two components.

**Validation.** Full backend suite **459 passed** (455 baseline + 4 new);
`ruff` (F, E9) clean on changed files; `import app.main` clean. Plus the live
exercise below.

**Live exercise (real homelab, 2026-09-11).** Owner-authorized. Method
identical to the original CAP-04 demonstration: an isolated second instance of
the same tree on `:8001` (loop initially off, demo cadence
`RMT_HOMELAB_LOOP_INTERVAL_SECONDS=20` / `RMT_HOMELAB_LOOP_COOLDOWN_SECONDS=30`,
ephemeral local-only operator token); the systemd `:8000` service (old code,
loop already enabled, `uptime-kuma`-only policy in its loaded process memory)
was left untouched and stayed `active` throughout.

1. **Pre-state:** `portainer` running.
2. **Fault injection:** governed `POST /execute?operation=stop&target=portainer`
   (`:8001`) → execution `3dc398e1…` completed → container `Exited (2)`;
   above-Core Docker verification `verified_success` (stop observed).
3. **`POST /homelab/loop/start`** → `policy_components: ["uptime-kuma",
   "portainer"]` confirmed live from the real `REMEDIATION_POLICY`.
4. **Cycle 2** (08:39:33): health eval CRITICAL → remediation
   **`manual_approval_required`** — held, no mutation (approval `92027cc7…`).
   `uptime-kuma` stayed `no_remediation` throughout — no collateral effect.
5. **`POST /homelab/approve`** (`approved_by` resolves from the authenticated
   operator identity, not a free-text field) for `92027cc7…` → **executed** via
   the `docker` adapter: execution `0ff214e9…`, success true, "restart on
   portainer". Core verifier `observation_unavailable` (fail-safe); above-Core
   Docker verifier **`verified_success`**.
6. **Stale-observation orphan hold** (cycle 4, 08:40:13): the collector had not
   yet refreshed past the restart, so the loop opened a second hold
   (`f5a070f0…`) against pre-restart data — the same phenomenon recorded in the
   original CAP-04 live demo for `uptime-kuma`. Confirmed `portainer` genuinely
   healthy via `docker ps`, then **`POST /homelab/approve?approved=false`**
   rejected the orphan hold — same disposition as the precedent.
7. **Cycle 11** (08:42:44): fresh observation → **`no_remediation`** for both
   components; loop stood down on its own (`portainer healthy_streak=2`,
   `uptime-kuma healthy_streak=11`, unaffected throughout).
8. **`POST /homelab/loop/stop`**; killed the `:8001` process (clean shutdown,
   no errors in its log).
9. **Final:** `portainer` running (restarted ~08:40:03); `dozzle` /
   `uptime-kuma` untouched; `:8000` systemd service `active` throughout.

**Result:** **PASS.** The loop ran the full lifecycle
`Understand → Decide → Govern → Authorize → Execute → Verify → Learn` against
the real second component end-to-end — held, approved, executed, verified,
recovered, stood down — correlated by `execution_id 3dc398e1…` (fault) /
`92027cc7…` + `0ff214e9…` (remediation) / `f5a070f0…` (rejected orphan hold).
Approval retained throughout (loop never auto-continued a hold); no
`uptime-kuma`/`dozzle` impact; no code change during the exercise. T1-1 / C1 is
now fully done per the roadmap's "Done when" bar.

---

## RMT-CAP-06 — Second Domain End-to-End: Agent Governance Gateway (C2 / D-1) (2026-09-11)

Proposal: `docs/RMT_CAP_06_PROPOSAL.md` (APPROVED 2026-09-11). Above-Core;
no `app/core/**` change; no C08.

- **Objective:** prove the frozen Core generalises past homelab/Docker by
  routing a real, non-homelab consequential action through the identical
  governed lifecycle. Chosen target: git-tag create/remove in a dedicated
  scratch repository (`backend/data/agent_git_target/`, gitignored, never the
  project's own `.git`) — a real CI/coding-agent action (tagging a release),
  fully reversible, no network, no credentials.
- **New** `app/agent/git_adapter.py` — `GitTagAdapter(ExecutionAdapter)`
  (`create`/`remove`, fixed `git` argv, no shell interpolation,
  `cwd` pinned to the configured repo, never request-supplied) +
  `register_git_adapter()`, inert unless `RMT_AGENT_GIT_REPO_PATH` resolves to
  a real repo — same conditional-registration shape Docker's own bootstrap
  uses, called from `app/main.py` `lifespan` (not a Core file; registers into
  the Core's own `adapter_registry` singleton, the intended extension point).
- **New** `app/ops/verification/git_observers.py` — a read-only
  `git rev-parse --verify refs/tags/<name>` observer registered for
  `("git","create")`/`("git","remove")`; `expected.py` gains
  `("git","create")→"present"` / `("git","remove")→"absent"`. Zero change to
  the registry, frozen verifier, or verification storage.
- **Modified** `app/agent/contract.py`-adjacent: `app/agent/api.py`'s
  `ProposeBody` gains `operational_context` (default `"homelab"`, every
  existing caller unchanged) threaded into `AgentIdentity` — a field that
  already existed on the MCR contract but no caller had ever set.
  `app/agent/adapter.py::propose_and_govern` resolves the execution adapter
  from `proposal.identity.operational_context` instead of unconditionally
  importing homelab's `resolve_adapter_name` — fixing what was otherwise a
  hardcoded Docker-only path (including the post-execution verification call,
  previously hardcoded to `adapter_name="docker"`). Default context preserves
  the original resolution byte-for-byte (regression-tested).
- `llm_agent.py` / `reference_agent.py` / `dependency_guard.py` — **not
  touched**: the first two are homelab-specific by construction and irrelevant
  to this proof; the guard is already generic (an unrecognized target is a
  harmless no-op).
- **Tests:** `app/agent/testing/test_git_adapter.py` (12 — adapter + inert-by-
  default registration, real disposable `tmp_path` repos), `app/ops/verification/testing/test_git_observers.py`
  (5 — registry pairs, expected-state rows, present/absent), `app/agent/testing/test_git_domain.py`
  (5 — `_resolve_adapter_name` behaviour incl. the homelab-default regression
  guard, grant-scope refusal before governance, and a real end-to-end
  proposal→hold→approve→execute→verify against a real disposable repo with
  only the durable evidence stores isolated — same isolation discipline as
  `test_remediation.py`, but the adapter and observer are real, not mocked).

**Core integrity.** Diff confined to `app/agent/**`, `app/ops/verification/**`,
one import + 6 lines in `app/main.py`, and docs. No `app/core/**` change
(verified via `git diff --stat`). `AGENT_ENABLED` / `AGENT_LLM_ENABLED`
semantics unchanged; the git adapter has its own independent inert-by-default
gate; approval retained on every proposal.

**Validation.** Full backend suite **480 passed** (459 baseline + 21 new);
`ruff` (F, E9) clean; `import app.main` clean.

**Live exercise (real homelab, 2026-09-11).** Owner-authorized. Same
isolated-instance discipline as C1/CAP-04: `:8001`, `RMT_AGENT_ENABLED=true`,
`RMT_AGENT_GIT_REPO_PATH` pointed at the real scratch repo; systemd `:8000`
left untouched and active throughout.

1. Granted `create` on `v1.0.0-cap06-proof` to a benign agent → proposed via
   `POST /agent/act` (`operational_context: "git"`) → held
   (`manual_approval_required`, "Action explicitly requires approval") — no
   mutation yet. Approved via `POST /homelab/approve` → **executed** through
   the real `git` adapter (execution `97357057…`) → `git tag` confirmed
   present in the scratch repo.
2. **Over-reaching agent, attempt 1:** re-used the now-consumed grant for
   `remove` on the same tag → refused, `decision: no_authority`,
   `detail: grant_consumed` — never reached governance.
3. **Over-reaching agent, attempt 2 (cleaner signal):** a fresh grant scoped to
   `create` on a *different* tag (`v2.0.0-scoped`), then attempted `remove` on
   `v1.0.0-cap06-proof` → refused, `decision: no_authority`,
   `detail: grant_scope_mismatch` — tag untouched, never reached governance.
4. **Cleanup / rollback proof:** granted `remove` on `v1.0.0-cap06-proof` to
   the benign agent → Core's own frozen risk engine classified `remove` as
   **high-risk on its own** (`"detail": "High-risk action requires human
   approval"`, distinct from the default-approval reason in step 1) — a real,
   unprompted signal that the frozen policy/risk logic generalizes correctly
   to a resource type it has never seen, with no domain-specific code in
   Core. Approved → **executed** (execution `920c5d32…`) → tag removed;
   scratch repo back to its initial commit, nothing left behind.

**Result:** **PASS.** D-1's DoD met: two distinct external-agent calls against
the git domain, one benign end-to-end, one (twice) refused for exceeding its
grant, never reaching the governed boundary. `uptime-kuma`/`portainer`/`dozzle`
unaffected; `:8000` systemd service active throughout; no code change during
the exercise.

**Recorded finding (not fixed — out of scope, honest limitation).** Both live
executions above show `verification_status: observation_unavailable` even
though the git observer is registered and correct (proven directly in
`test_git_domain.py`). Cause: `POST /homelab/approve`'s continuation path only
auto-invokes above-Core verification for targets with a Core `ComponentContext`
(the T1-3 generalization, homelab-specific by construction) — a git-tag target
has none, so the held→approved path never calls `verify_executed_action`,
unlike the immediate (non-held) path inside `propose_and_govern` which does.
This is the same shape of gap T1-3 closed for homelab; closing it for the
agent/git domain generally is a candidate for C3 ("harden the agent surface"),
not part of this proposal's approved scope.

---

## RMT-CAP-07 — Harden the Agent Surface (C3) (2026-09-11)

Proposal: `docs/RMT_CAP_07_PROPOSAL.md` (APPROVED 2026-09-11). Above-Core; no
`app/core/**` change; no C08. Depends on A2 (done same session — CI activated
by pushing 9 pending commits; run `34585062939` green, 480 passed, 0 skipped,
real Docker e2e un-skipped on every push).

- **Objective:** an operator sees exactly what an agent proposal will do
  before approving it; the agent surface has a standing, named adversarial
  gate instead of scattered one-off coverage.
- **Key finding reused, not rebuilt:** `execute_governed_action` already calls
  `evaluate_action_policy` → `simulate_action` → `process_approval` — all
  three pure, all three already exported from frozen Core — *before* the
  first write to storage. A genuinely accurate preview was therefore a matter
  of calling the same three functions and stopping, not building a parallel
  simulation.
- **New** `app/agent/preview.py::preview_proposal` + **`POST
  /agent/act/preview`** (`app/agent/api.py`, same `require_operator` gate as
  `/agent/act`) — resolves the concrete `ActionRequest` + predicted
  `policy_allowed`/`risk_level`/`approval_mode`/`approval_reason`. Zero
  `execute_governed_action` calls, zero grant consumed, zero hold, zero
  trace/audit/verification/Learn record. `app/agent/adapter.py` gained
  `resolve_proposal()` (shared by both `propose_and_govern` and preview, so
  they can never resolve a proposal differently) — a pure refactor, no
  behavior change to the real path (regression-tested).
- **Structured rationale** — `app/homelab/remediation.py::record_learning`
  gained an optional `rationale` kwarg (`{goal, reason, mechanism,
  operational_context}`, default `None`). Closes a real, previously-silent
  gap: the Learn evidence record captured `status`/`ids`/`confidence` but
  never *why* an action was proposed. Every homelab call site (`rationale`
  omitted) is byte-identical to before (regression-tested); only
  `propose_and_govern`'s two `record_learning` calls now pass it.
- **New** `app/agent/testing/test_adversarial.py` — 20 cases, four
  categories: (1) invalid/malformed proposals never build an `ActionRequest`;
  (2) authority scope escape (wrong target, wrong operation, consumed,
  expired, and a string-injection attempt against a granted target proving
  grant matching is exact-string, never prefix/pattern) always
  `no_authority`, grant left intact; (3) LLM prompt-injection shapes (no JSON
  object, `propose:false` despite an urgent goal, unknown/path-traversal
  target, disallowed mechanism, malformed confidence, injected unsolicited
  JSON fields, goal/proposal semantic mismatch) always fail closed before
  governance or land in a human hold, never auto-allowed; (4) T13
  dependency-cascade probes — an allowed op on a declared dependency forces
  `escalated_hold` **even when the agent's own default requires-approval flag
  is off**, proving the escalation is not merely redundant with the default.
- **New** `app/agent/testing/test_preview.py` — 12 cases: disabled gate,
  structural `no_proposal`, a resolved-action case, an authority-not-gating
  case (preview still resolves and reports `authority.ok=False` rather than
  refusing), a high-risk `remove` case matching the real risk classification,
  three zero-side-effect proofs (never calls `execute_governed_action`, never
  consumes the grant, creates no hold), a **regression guard** asserting
  preview's predicted `approval_mode` matches `propose_and_govern`'s real
  `decision` for the same input, and 2 HTTP-route cases.

**Core integrity.** Diff confined to `app/agent/**`, one optional kwarg in
`app/homelab/remediation.py`, and docs. No `app/core/**` change (verified via
`git diff --stat`); `evaluate_action_policy`/`simulate_action`/
`process_approval` reused exactly as `execute_governed_action` already uses
them, called through no new code path.

**Validation.** Full backend suite **514 passed** (480 baseline + 34 new);
`ruff check .` clean (repo-wide, not just changed files); `import app.main`
clean. Already exercised for real by CI on push (A2 live) — no separate live
drill needed: preview has no side effects to demonstrate live, and the
adversarial suite's value *is* running in CI on every future change, which is
now true by construction.

**Recorded, not addressed by this proposal.** The CAP-06 finding above
(`POST /homelab/approve`'s auto-verification is `ComponentContext`-only, so a
held git-domain action doesn't auto-verify the way homelab targets do) was
flagged as a C3 candidate but was **not** in this proposal's approved scope
(§4 out of scope) and remains open. C3 hardened the *proposal* boundary
(preview, rationale, adversarial coverage), not the *post-approval
verification* boundary — a distinct, still-open item for a future pass.

---

## Continuation-path verification gap closed (2026-09-11)

Closes the finding recorded in RMT-CAP-06 and flagged again, un-addressed,
in RMT-CAP-07: `POST /homelab/approve`'s continuation path
(`app/homelab/continuation.py::continue_remediation`) only ran above-Core
verification + Learn closure for a component with a Core `ComponentContext`
(homelab), so an agent-originated hold in a non-homelab domain (the CAP-06
git-tag demo) was silently continued with no verification and no Learn
record at all. Above-Core; no `app/core/**` change; S-sized (owner selection
only, per the roadmap's own process rule — no separate proposal doc).

- **Root cause, same bug class already fixed once (C2):** verification was
  hardcoded to `adapter_name="docker"` regardless of what adapter the hold
  was actually destined for. The frozen Core's own `ApprovalHold` already
  carries `adapter_name` — "the adapter it was destined for" — set correctly
  at hold-creation time by whichever domain built the action; the
  continuation path simply never read it.
- **Modified** `app/homelab/continuation.py`:
  1. Verification now resolves the observer from `hold.adapter_name`, not a
     hardcoded string. An unresolved `(adapter, operation)` pair still
     degrades gracefully to `observation_unavailable` (B1a's existing
     behaviour) — never an error, never a false `verified_success`.
  2. The attribution gate widened from "has a `ComponentContext`" to "has a
     `ComponentContext` **or** is agent-originated" (`action.decision_id`
     starts with `"agent-"`, set only by `propose_and_govern`, regardless of
     domain). A held action that is neither — the operator `POST /execute`
     flow — is unaffected: no extra Learn record, no verification, exactly
     as before.
- **Test fixture correction (not a design change):** two existing
  `test_continuation.py` fixtures had `adapter_name="simulation"` on holds
  that were actually meant to represent real homelab Docker remediations —
  harmless before this fix (the hardcoded `"docker"` ignored the field
  entirely), incorrect after it. Corrected to `adapter_name="docker"`,
  matching what `resolve_adapter_name()` actually returns in production and
  what these tests' own mocked Docker observer represents.
- **New** `test_agent_originated_git_hold_gets_learn_and_verification` — a
  real disposable git repo, a hand-placed hold with `adapter_name="git"` and
  an `"agent-..."` `decision_id`, continued via `continue_remediation`:
  `verified_success` and a Learn record now appear where before this fix
  there would have been neither. The pre-existing narrowing guarantee
  (`test_non_homelab_held_action_gets_no_learn_or_docker_verification`) is
  unchanged and still passes — an arbitrary operator hold still gets
  nothing.

**Core integrity.** Diff confined to `app/homelab/continuation.py` +
`app/homelab/testing/test_continuation.py` (2 files). No `app/core/**`
change (verified via `git diff --stat`).

**Validation.** Full backend suite **515 passed** (514 baseline + 2 new − 1
redundant duplicate removed); `ruff check .` clean repo-wide; `import
app.main` clean.

---

## RMT-CAP-08 — Productize the Agent Governance Gateway (2026-09-11)

Proposal: `docs/RMT_CAP_08_PROPOSAL.md` (APPROVED — owner directive: "keep
building toward something usable"). Above-Core; no `app/core/**` change; no
C08.

- **Objective:** move the agent surface from "proven" to "usable by a real
  caller" — the two gaps named and accepted as limitations in the CAP-06
  proposal: no durable authority grants, no external integration
  documentation.
- **Persistent authority grants** — `app/agent/authority.py`:
  `AuthorityGrant` converts from a plain `@dataclass` to a Pydantic
  `BaseModel`; new `AuthorityGrantStorage(DurableStore)` (`_table =
  "agent_authority_grants"`) is a new table in the **same shared** SQLite
  evidence database (`data/governance_evidence.db`) six frozen-Core stores
  already write to — the exact extension point `app/ops/verification/index.py`
  already uses for its own above-Core persistence, so no `app/core/**`
  change. `AuthorityStore`'s public API (`grant`/`check`/`consume`/`get`/
  `list_active`/`reset`) is unchanged; internally it now reads/writes through
  the durable storage instead of a bare dict. A grant now survives a process
  restart.
- **Safety-critical part of this change:** all 6 test files that call
  `authority_store.reset()` directly on the module-level singleton
  (`test_agent_governance.py`, `test_llm_agent.py`, `test_preview.py`,
  `test_adversarial.py`, `test_dependency_guard.py`, `test_git_domain.py`)
  were updated to `monkeypatch` the singleton's storage to a fresh
  **in-memory** instance (`AuthorityGrantStorage(file_path=None)`) per test.
  Without this, `reset()` against the now-durable singleton would `DELETE`
  every row from the **real** evidence database on every test run — the same
  file the live systemd service reads — on every `pytest` invocation in this
  checkout. Verified directly: ran the full suite, then queried
  `agent_authority_grants` in the real `data/governance_evidence.db` —
  **0 rows**, confirming no test ever touched the real table.
- **New** `docs/operations/AGENT_API.md` — the integration guide: full
  lifecycle with worked `curl` examples (grant → preview → propose → approve
  → receipt), the complete `decision` vocabulary table, which
  `AgentOutcome.as_dict()` fields are stable vs. informational, and the
  non-guarantees already recorded elsewhere, gathered in one place an
  external integrator can actually use without reading source. Linked from
  `README.md`.
- **Tests:** `app/agent/testing/test_authority_persistence.py` (7 — grant
  survives a simulated restart via a fresh instance on the same file,
  `consume()` persists, `reset()` only clears the instance it's called on,
  scope/expiry checks unchanged, `list_active` excludes consumed).

**Core integrity.** Diff confined to `app/agent/authority.py`,
6 existing test files (isolation-mechanism change only, no logic change),
1 new test file, and docs. No `app/core/**` change (verified via
`git diff --stat`); `DurableStore` and `EVIDENCE_DB_PATH` reused exactly as
six existing stores already use them — a new table via
`CREATE TABLE IF NOT EXISTS`, no existing table touched.

**Validation.** Full backend suite **522 passed** (515 baseline + 7 new);
`ruff check .` clean repo-wide; `import app.main` clean.

**Live check (real evidence DB, 2026-09-11).** Not a fault-injection drill —
persistence has no execution side effect to demonstrate live, so this
directly exercises the real file instead: process A granted authority
against the real, default `AuthorityStore()` (pointed at the actual
`data/governance_evidence.db`); a second, independent process invocation
(simulating a restart) read the same grant back and passed a live `check()`
against it (`operation=create`, `target=cap08-live-check`) — `(True, "ok")`.
Cleaned up via `authority_store.reset()` immediately after (the table was
new and otherwise empty). The live systemd service (`:8000`) was never
restarted or touched throughout — confirmed `active` before and after.

---

## T0-2 — Genuine fresh-host rebuild (2026-09-12)

R3's tooling (`backend/scripts/rmt-rebuild.sh`, `docs/operations/
RMT_PLATFORM_RECOVERY.md`) shipped 2026-09-08 with a scratch-dir `--drill`
proof. The one open item was R3's own recorded "Required action": run it for
real, not just `--drill`, since `--drill` skips the systemd + Caddy + cron
steps entirely. Above-Core; operational; no `app/core/**` change; no code
diff except the one script fix below.

- **Fresh host:** a real, never-before-provisioned Ubuntu 24.04 LXD **system**
  container (`rmt-t02-rebuild`) — genuine `systemd` PID 1, its own filesystem,
  its own network namespace — not a Docker container (Docker containers don't
  run a real init/systemd, which the unit-install step requires). Provisioned
  from a bare `ubuntu:24.04` image; a `rmt-lab` user created to match the
  systemd unit's hard-coded `User=rmt-lab` /
  `/home/rmt-lab/homelab/projects/homelab-control-center` path.
- **Environment constraint found and worked around:** this session's network
  is sandboxed — the container had no outbound internet (confirmed: reaches
  its own gateway, not the public internet), so `apt-get`/`pip` against real
  package indexes failed. This is a property of the current execution
  sandbox, not of RMT or of a real second host (per `STEWARD.md` §2,
  environment limitations are not implementation defects). Worked around
  entirely offline: `sqlite3` / `python3.12-venv` installed from `.deb` files
  downloaded on the host (which has internet) and pushed in; the Python
  dependency set installed from an offline wheelhouse
  (`pip download -r requirements.lock.txt` on the host → pushed in → `pip
  install --no-index --find-links=<wheelhouse> -r requirements.lock.txt` in
  the container) — same lockfile, same exact pinned versions, different
  transport.
- **Full sequence run for real** (`--evidence <fresh backup>`, then step 6 by
  hand after `--skip-systemd` for review):
  1. Prerequisites — `python3.12`/`git`/`sqlite3`/`rsync` present; correctly
     `WARN`ed on no `docker` group (no Docker socket in the container).
  2. venv — populated from the offline wheelhouse (see above); the script's
     own `pip install -r requirements.lock.txt` found everything already
     satisfied and needed no network.
  3. Evidence restore — a fresh backup made by `rmt-evidence-backup.sh` on
     the live host **2026-09-12** (not the stale 2026-09-08 one), verified
     `RESULT: OK` on the host *before* transport, then restored inside the
     container and re-verified `RESULT: OK` there — twice (the restore
     script's own internal re-verify, then the rebuild script's separate
     step-4 check).
  4. Integrity check — `RESULT: OK`.
  5. Full test suite — **522 passed, 3 skipped** in the container (the 3 are
     `test_e2e_docker.py`'s Docker-adapter tests, correctly auto-skipping —
     matches the documented V1 behavior when no Docker daemon is reachable).
  6. Systemd bring-up — the real `rmt-control-center.service` + all 4
     non-secret drop-ins (`cap04-loop`, `cap05-agent`, `bind-loopback`,
     `hardening`) installed; a throwaway `auth.conf` with a freshly generated
     token (`openssl rand -hex 24`, never a production secret) installed so
     the app would start; `daemon-reload` → `enable --now`.
- **Live-verified on the fresh host:** `GET /health` → `{"status":"ok",...}`;
  listening on `127.0.0.1:8000` only (`bind-loopback.conf` confirmed, not
  `0.0.0.0`); `systemd-analyze security rmt-control-center.service` →
  **4.1 OK** (`hardening.conf` confirmed — matches the original D3 result
  exactly, proving the hardening directives are compatible with an
  unprivileged nested container, not just the original bare host); structured
  JSON logging (O1) present in the journal; CAP-04 loop and CAP-05 agent
  drop-ins both active (`loop.enabled: true`, `running: true`); Docker
  adapter correctly fell back to `simulation` with the documented D6
  `adapter_degraded: true` warning (no Docker socket) — the expected
  behavior, not a failure.
- **Found and fixed a real bug** in `rmt-rebuild.sh`'s step-2 summary line:
  `$(( "$BACKEND/.venv/bin/pip" list | wc -l ))` used an arithmetic context
  (`$(( ))`) where a command substitution (`$( )`) was meant — exactly the
  class of defect this genuine exercise exists to catch that `--drill` mode's
  repeated, fast host-side runs apparently never surfaced. One-line fix; no
  test coverage needed (a `set -euo pipefail` shell script has no pytest
  suite — this is `scripts/`, not `app/`).
- **Not exercised** (documented manual steps, unchanged): Caddy (S4) TLS
  cutover and cron wiring (`rmt-evidence-backup.sh` / `rmt-heartbeat.sh`) —
  both remain operator actions per the runbook; this drill's purpose was the
  service rebuild itself, not the LAN-facing proxy or backup scheduling.
- **Cleanup:** the container is disposable and was not torn down immediately
  in case further inspection is wanted; `lxc delete rmt-t02-rebuild --force`
  removes it completely (it consumed no live-host resources beyond the
  container itself — the live `rmt-control-center.service` on `:8000` was
  never touched, confirmed active throughout).

**Core integrity.** Diff confined to one line in
`backend/scripts/rmt-rebuild.sh`. No `app/core/**` change. No app code
change at all — this exercise validated existing tooling; it produced one
bug fix in that tooling.

**Validation.** 522 passed + 3 skipped = 525 total inside the fresh
container, matching the host's 525-passed, 0-skipped run exactly (same
commit, T0-3 included) — the only difference is environment-driven: the 3
Docker e2e tests correctly auto-skip in the container (no Docker socket)
instead of running, as documented (V1).

---

## T0-3 — Close the remaining observability gap (2026-09-12)

Proposal: `docs/RMT_T0_3_PROPOSAL.md` (APPROVED 2026-09-12). Above-Core;
operational; no `app/core/**` change.

- **Recon finding first:** T0-3's core objective (structured logs + a
  metrics endpoint) was already shipped 2026-09-08 as O1/O3/O4
  (`docs/RMT_PRODUCTION_READINESS.md` Group O), but
  `docs/RMT_ABOVE_CORE_ROADMAP.md` never cross-referenced it — a doc-sync
  gap between two governing docs, found and corrected in this change
  (doc-only edit, no code). T0-3 is now marked "substantially done
  2026-09-08" in the roadmap, with only the real remainder open.
- **Approval latency** — `app/ops/metrics.py` gained
  `rmt_approval_latency_seconds_sum` / `_count` (labelled by `decision`): for
  every `ApprovalRecord` whose `approval_id` matches an actual
  `ApprovalHold` (an auto-approval never held, so it's excluded by
  construction), sums `record.created_at − hold.created_at`. Read-only
  derivation from the same two stores `/metrics` already reads; wrapped in
  the module's existing fail-open `try/except` pattern.
- **Decisions/min deliberately NOT added as a server-computed metric** — the
  existing `rmt_approval_records_total` counter is the correct Prometheus
  shape for a rate; `rate(rmt_approval_records_total[5m]) * 60` is a
  scraper-side query, not a field RMT should compute itself. Documented
  instead of implemented.
- **New** `docs/operations/METRICS.md` — the "minimal dashboards note" named
  in T0-3's original scope: every `/metrics` signal, the PromQL for
  decisions/min and average approval latency, and a pointer to RMT's
  already-live O2/O3 alerting rather than a duplicate description. Linked
  from `README.md`.
- **Tests:** `app/ops/testing/test_metrics.py` — 3 new (`+` existing 5):
  latency computed correctly across two decisions, a record with no matching
  hold contributes to neither `_sum` nor `_count`, and the section fails
  open (a broken `approval_hold_storage` degrades only its own signals —
  correctly counted as 2 scrape errors since the store backs both the
  existing holds-by-status section and this new one).

**Core integrity.** Diff confined to `backend/app/ops/metrics.py`,
`backend/app/ops/testing/test_metrics.py`, `docs/operations/METRICS.md`,
`README.md`, and `docs/RMT_ABOVE_CORE_ROADMAP.md` (status correction only).
No `app/core/**` change. No new store, no new evidence category, no write
path — only `.get_all()` on stores `/metrics` already reads.

**Validation.** Full backend suite **525 passed** (522 baseline + 3 new);
`ruff check .` clean.

**Live check (real service, 2026-09-12).** `rmt-control-center.service`
confirmed `active`/`running` throughout (no restart); `curl
localhost:8000/metrics` on the live instance shows real data —
`rmt_approval_latency_seconds_count{decision="approved"} 3`,
`{decision="rejected"} 1` — computed from the service's actual accumulated
evidence, not a synthetic fixture.

---

## T0-5 — Security group finish + a live credential-exposure fix (2026-09-12)

Proposal: `docs/RMT_T0_5_PROPOSAL.md` (APPROVED 2026-09-12). Above-Core;
no `app/core/**` change.

- **Recon finding first (same pattern as T0-2/T0-3):** all three of T0-5's
  named items — S4 Caddy cutover, S3 separation-of-duties, S5
  CORS-from-config — were already shipped and live 2026-09-08
  (`docs/RMT_PRODUCTION_READINESS.md` Group S), never cross-referenced in
  `docs/RMT_ABOVE_CORE_ROADMAP.md`. Verified live: `systemctl is-active
  caddy` → `active` (2.6.2); S3's `RMT_AUTH_SEPARATION` code exists and is
  tested (15 tests) but confirmed still off in the live environment; S5's
  `RMT_CORS_ORIGINS` config-driven CORS already in place.
- **Unplanned, critical finding during that same recon:** `systemctl show -p
  Environment rmt-control-center.service`, run as the unprivileged
  `rmt-lab` user (no `sudo`), printed the live `RMT_OPERATOR_TOKENS` value
  in full — both production operator tokens — to this session. systemd
  exposes a unit's resolved plain environment to any local user via
  `systemctl show`, regardless of the `0600` file permission on the
  `auth.conf` drop-in that set it; `docs/operations/SECRETS.md`'s prior
  claim that those permissions meant "the `rmt-lab` service user cannot
  read it" was true of the file, not of the value systemd exposes.
- **Immediate response:** the exposure was flagged to the owner in the same
  turn it was found; both tokens were rotated by the owner (this session has
  no `sudo` and cannot touch the live `auth.conf` or restart the live
  service) via commands run in a private terminal, not through this
  session's own `!` mechanism, specifically to avoid re-exposing the *new*
  tokens into the same transcript that leaked the old ones.
- **Structural fix:** `app/ops/ops_config.py` gained
  `_operator_tokens_raw()` — prefers `$CREDENTIALS_DIRECTORY/
  RMT_OPERATOR_TOKENS` (set automatically by systemd for a unit using
  `LoadCredential=`) over the `RMT_OPERATOR_TOKENS` env var, which remains
  the fallback for local dev / tests / non-systemd runs. `operator_tokens()`
  is the single choke point already used by both call sites
  (`app/main.py`'s startup-refusal check, `app/ops/auth.py`'s auth check) —
  neither needed to change. `deploy/systemd/auth.conf.example` now uses
  `LoadCredential=RMT_OPERATOR_TOKENS:/etc/rmt-control-center/operator_tokens.secret`
  instead of `Environment=RMT_OPERATOR_TOKENS=...`; the drop-in itself holds
  no secret and no longer needs `0600`. This is exactly the pattern
  `docs/operations/SECRETS.md` had already pre-designed and pre-approved
  ("the pre-agreed next step... scoped and ready to implement the moment a
  credentialed dependency is proposed") — it had just never been triggered,
  since that doc framed the operator token map as not needing it. It does.
- **Docs updated to match:** `docs/operations/DEPLOY.md`,
  `docs/operations/CONFIG.md`, `docs/operations/SECRETS.md` (records the
  exposure, the fix, and corrects the prior claim),
  `projects/homelab-control-center/deploy/systemd/README.md`, and
  `backend/scripts/rmt-rebuild.sh`'s printed manual-steps checklist — all
  updated to the two-file `auth.conf` + `/etc/rmt-control-center/operator_tokens.secret`
  layout and the new rotation procedure (no `daemon-reload` needed, only a
  restart, since the unit/drop-in content itself doesn't change on
  rotation).
- **Raised, not bundled:** enabling `RMT_AUTH_SEPARATION=true` on the live
  deployment — the code and tests already exist, but flipping the default
  is a genuine behavior change (an agent-hold approval by the grantor starts
  returning 403), not a doc or credential-storage fix. `CONFIG.md`'s own
  "enable only when you have one [second identity]" condition is now met
  (a second operator token exists), so this is recorded as an owner
  decision, not a further build item.
- **Found, not fixed (out of T0-5 scope):** `hardening.conf` is **not**
  actually installed on the live host — contradicts D3's "DONE" framing at
  the drop-in-inventory level. A pre-existing gap, found during this
  recon, not part of T0-5's named scope; not acted on here.
- **Tests:** `app/ops/testing/test_auth.py` — 3 new (credentials-directory
  takes precedence over a conflicting env var; a missing credential file
  falls back to the env var rather than hard-failing; no
  `$CREDENTIALS_DIRECTORY` set preserves existing behavior exactly).

**Core integrity.** Diff confined to `backend/app/ops/ops_config.py`, one
test file, deploy artifacts (`auth.conf.example`,
`deploy/systemd/README.md`, `rmt-rebuild.sh`'s printed checklist), and docs.
No `app/core/**` change. No other call site of `operator_tokens()` touched.

**Validation.** Full backend suite **528 passed** (525 baseline + 3 new);
`ruff check .` clean.

**Live migration COMPLETE (owner-executed, 2026-09-12).** Token rotation and
the `auth.conf` → `LoadCredential=` migration required `sudo`, which this
session does not have; commands were provided for the owner to run in a
private terminal (not through this session, to avoid re-exposing the new
tokens into the same transcript that leaked the old ones). One path
collision was found and fixed along the way: `/etc/rmt` already existed on
this Ubuntu host as a symlink to `/usr/sbin/rmt` (the unrelated, long-lived
Unix remote-magnetic-tape utility) — the secret directory was moved to
`/etc/rmt-control-center/operator_tokens.secret` everywhere (docs, script,
`auth.conf.example`; no code change, since `app/ops/ops_config.py` never
hardcoded the path — it only reads `$CREDENTIALS_DIRECTORY`, which systemd
sets from the unit's own `LoadCredential=` directive). Owner confirmed: all
steps passed — `systemctl show -p LoadCredential` shows only the credential
name and file path, `systemctl show -p Environment` no longer shows
`RMT_OPERATOR_TOKENS`, `/health` came back healthy after the restart, and
both tokens were rotated. The exposure this item exists to fix is closed on
the live host, not just in code.

---

## T0-6 — Public-showcase live exercise: Agent Governance Gateway on the production service (2026-09-12)

**Context.** Before making the `rmt-platform` GitHub repository public, the
README's central claim — "an AI agent proposes an action, RMT governs it
end-to-end" — was exercised for real against the actual production service
on `:8000`, not an isolated test port. RMT-CAP-06's original live
demonstration (2026-09-11) ran on an isolated `:8001` instance specifically
to leave `:8000` untouched; this exercise is the first time the git-tag
Agent Governance Gateway ran on the real production service.

**Enablement (config-only, no code change).** The git adapter
(`app/agent/git_adapter.py`) is conditional-by-design — it only registers
when `RMT_AGENT_GIT_REPO_PATH` resolves to a directory containing a `.git`
(the same graceful-degradation shape Docker's own adapter registration
uses). It was never enabled on the live service until now. Owner added a new
drop-in:

```
# /etc/systemd/system/rmt-control-center.service.d/git-domain.conf
[Service]
Environment=RMT_AGENT_GIT_REPO_PATH=/home/rmt-lab/homelab/projects/homelab-control-center/backend/data/agent_git_target
```

— pointing at the dedicated scratch repository approved in
`docs/RMT_CAP_06_PROPOSAL.md` §3a/§7 (`data/agent_git_target/`, distinct
from this project's own `.git`), then `daemon-reload` + restart. No
`app/core/**` or `app/agent/**` change; this only turns on an extension
point that already existed.

**Operational hiccup, recorded for accuracy.** The operator token rotated
during T0-5 no longer matched the live `/etc/rmt-control-center/operator_tokens.secret`
by the time this exercise ran — confirmed by comparing SHA-256 hashes of the
typed token against every stored token, never the plaintext itself, in the
owner's own terminal. Root cause not established (a second undocumented
rotation, or a copy error when the T0-5 value was first saved) — owner
rotated fresh and this time saved the new value to a password manager
immediately. **Recorded as an open item:** there is no durable record of
*when* an operator token was last successfully verified working, only of
when it was set. No code or Core implication; a process gap in this
project's own runbook discipline, not the platform's.

**The exercise (real request/response, principal `alice`).** Full lifecycle
run against the scratch repo, target tag `rmt-showcase-demo`:

1. `POST /agent/authority/grant {"operation":"create","target":"rmt-showcase-demo"}`
   → `grant_id: 72459d60f443`.
2. `POST /agent/act/preview` (same body) → `decision: "preview"`,
   `predicted: {policy_allowed: true, risk_level: "medium", approval_mode:
   "manual", approval_reason: "Action explicitly requires approval"}` — the
   real policy/risk functions, zero side effects.
3. `POST /agent/act` (real proposal) → `decision: "hold"`,
   `governed_status: "manual_approval_required"`, `approval_id:
   1add5da4-5e37-4f51-a9f9-0961de47d872`. Held, not executed.
4. `POST /homelab/approve?approval_id=...&approved=true` (human/operator
   `alice`) → `status: "executed"`, `success: true`,
   `docker_verification_status: "verified_success"` (field name is a
   cross-domain artifact — shared key, not literal Docker — reason string
   correctly reads `[layer=above_core adapter=git ...]`).
5. **Independent proof, outside the API:** `git -C
   data/agent_git_target tag -l rmt-showcase-demo` → tag present.
6. **Refusal path** — re-proposed with the same, now-consumed `grant_id` →
   `decision: "no_authority"`, `detail: "grant_consumed"`. Governance refused
   before running again, as designed.
7. **Cleanup lifecycle** — fresh grant for `operation: "remove"`, proposed,
   held (this time `detail: "High-risk action requires human approval"` —
   the policy engine gave `remove` a different, more specific reason than
   `create`'s, unprompted), approved, executed, `verified_success`.
8. **Independent proof again:** `git tag -l rmt-showcase-demo` → empty. Tag
   genuinely gone.

**Corroboration from outside the API entirely.** This session independently
re-checked, without touching the operator token: the scratch repo has zero
tags after the run, and `journalctl -u rmt-control-center.service` shows two
`homelab_approve` log lines whose `action_id` / `execution_id` /
`approval_id` / `principal: "alice"` match the API responses exactly —
the receipts are not self-reported fiction, they're corroborated by a
second, independent data source (the service's own structured logs).

**Disposition.** T0-6 → DONE. First live, production-service exercise of a
second execution domain through the full governed lifecycle, including a
real refusal and risk-differentiated approval reasoning — the evidence base
for the README's agent-governance claim ahead of the repository going
public. No `app/core/**` change; config-only enablement of an existing
extension point; scratch-repo blast radius only.

## RMT-CAP-09 — Governed Operations Console (roadmap P-B) (2026-09-13)

**Status: COMPLETED & VERIFIED.** `docs/RMT_CAP_09_PROPOSAL.md` is APPROVED
(2026-09-13); `docs/RMT_CAP_09_IMPLEMENTATION.md` is the detailed plan it
follows. Backend and frontend are both implemented, tested, compiled, and
committed (5 reviewable slices); the live `:8001` isolated-instance
walkthrough (the last open Definition-of-Done item) has run and passed. This
entry records what has been built and verified, honestly, including the one
verification gap that remains (no browser in this shell).

**Objective (P-B):** the missing usability layer — a real, read-only web console
over the authorization / approval / hold / audit / trace / verification evidence
and the loop/agent status, with approve/reject for held items. Preconditions the
roadmap set for P-B (a real second domain — D-1 — and a public repo with an
audience beyond the owner) were both met.

**Back-end built:**
- `app/ops/evidence_chain.py` — read-only, **fail-open end-to-end**
  `evidence_chain(action_id|approval_id|execution_id)` returning the
  **Govern → Verify** chain: authorization → approval record (decision) → hold
  (if held) → execution audit → decision trace → verification, plus S3
  provenance. Reads the existing durable stores via their accessors; **writes
  nothing**; any store read *or* assembly error degrades to an empty chain, never
  a 500. No `app/core/**` change.
- `GET /ops/evidence` in `app/main.py` — operator-auth (`require_operator`),
  422 if no identifier; not on the governed mutation path.
- `app/ops/testing/test_evidence_chain.py` — 7 tests, all passing: full chain by
  `action_id`; resolution by `approval_id` / `execution_id`; unknown id → empty
  fail-open; store-read failure → degraded section not 500; **asserts no writes**.
  All stores are in-memory-isolated; no test touches the real evidence DB.

**Review fixes (from a deliberate review pass before this entry):**
- Holds table was reading nonexistent fields (`action` / `risk_level`) — fixed to
  the real `/ops/holds` output (`component` / `action_type`).
- Fragile approve heuristic removed — the console now routes every approval
  through `/homelab/approve`, the documented superset of `/approve` (homelab
  holds get the Learn + verify closure; non-homelab holds pass through exactly
  like `/approve`).
- `evidence_chain` made fail-open for the whole call (assembly exceptions no
  longer 500).

**Front-end built and compiled:**
- `frontend/src/types/governance.ts`, `api/auth.ts` (client-side operator token,
  never logged), `api/governance.ts` (typed read-only client),
  `components/GovernedConsole.tsx` (token gate → Holds queue with Approve/Reject →
  Verification ledger → Evidence-by-action → agent/SoD status), `App.tsx` view
  toggle (Containers / Governed Ops), `vite.config.ts` dev proxies, `index.css`
  styles.
- `tsc -b && vite build` — clean (`dist/` produced, 545ms). `oxlint` — clean.
  (A later shell in this same session had `node`/`npm` available, unlike the
  shell that originally wrote the "not yet compiled" status above.)

**Committed (2026-09-13), 5 reviewable slices, no `app/core/**` diff in any:**
1. `app/ops/evidence_chain.py` + `test_evidence_chain.py`.
2. `GET /ops/evidence` route + `app/main.py` registration.
3. Frontend `api/auth.ts` + `api/governance.ts` + `types/governance.ts` +
   `vite.config.ts` dev proxies.
4. Frontend `components/GovernedConsole.tsx` + `App.tsx` view toggle +
   `index.css`.
5. This docs sync.

**Backend regression (full suite, post-fixup):** **535 passed**; `import
app.main` clean; zero `app/core/**` diff across the whole change.

**Read-only correlation validation (against the real `data/governance_evidence.db`,
pre-commit):** from a real `action_id`, the chain resolved 1 authorization + 1
approval + 1 audit + 1 trace + 2 verifications; `approval_id` and `execution_id`
both resolved back to the same `action_id`; an unknown id returned the empty
chain (no 500); a store that raised degraded to `[]` for that section only.

**Live end-to-end walkthrough — isolated `:8001` instance, real Docker, real
`data/` evidence stores, live `:8000` untouched throughout (2026-09-13):**
1. Started a second instance on `:8001` (loop disabled, agent disabled, its own
   throwaway operator token — not the live secret) against the same real
   evidence stores and containers as `:8000`. `GET /health` → `docker_available:
   true`.
2. Fault-injected `uptime-kuma`: `POST /execute?operation=stop&target=uptime-kuma`
   → container `Exited (0)`.
3. Governed remediation: `POST /homelab/remediate?component=uptime-kuma` →
   `manual_approval_required` (action `6a083293…`, approval `c550b920…`).
4. **The hold surfaced via the exact call the console's Holds queue makes**
   (`GET /ops/holds`), with the real field names the fixed table now reads
   (`component: "uptime-kuma"`, `action_type: "restart"`, `actionable: true`) —
   confirming the earlier review fix (nonexistent `action`/`risk_level` fields
   were the bug) actually resolves against a live hold, not just in review.
5. **Approved via the exact call the console's Approve button makes**
   (`POST /homelab/approve?approval_id=c550b920…&approved=true`, the single
   path the console now uses for every hold) → `status: executed`,
   `docker_verification_status: verified_success`; container back
   `Up (health: starting)`.
6. **The full chain resolved via the exact call the console's Evidence Chain
   view makes** (`GET /ops/evidence?action_id=6a083293…`): authorization
   (`status: approved`) → approval record (`decision: approved`) → hold
   (`status: approved`) → audit (`status: completed`) → trace
   (`outcome: completed`) → both verifications (`observation_unavailable`
   Core fail-safe + `verified_success` above-Core Docker observer,
   `reason` carrying the `supersedes=observation_unavailable` provenance tag).
7. `uptime-kuma` confirmed `healthy` after; `portainer`/`dozzle` untouched
   throughout; live `:8000`'s own CAP-04 loop kept cycling normally the whole
   time (`cycle_count` advanced, no interruption); `:8001` killed cleanly and
   the throwaway token deleted.

**Result: PASS.** Every DoD item from `docs/RMT_CAP_09_IMPLEMENTATION.md` §4 is
met except one, explicitly recorded rather than silently claimed: **no browser
was available in this shell** to click through the compiled SPA visually. The
walkthrough instead drove the identical HTTP calls the console's compiled code
makes (`getHolds`/`approveHomelabHold`/`getEvidence` in `api/governance.ts`),
which is what a browser session running that same code would also produce —
but it is not the same as a human confirming the rendered UI in a real browser.

**Boundaries:** no `app/core/**` change; no new mutation path; console is
read-only + approve/reject via the existing `/homelab/approve` endpoint; no
business logic in the UI (classification stays server-side).

### Finding + fix — `GET /ops/evidence` shipped with no enable flag (2026-09-13)

**Finding:** unlike CAP-04 (`RMT_HOMELAB_LOOP_ENABLED`) and CAP-05
(`RMT_AGENT_ENABLED`), `GET /ops/evidence` was unconditionally registered —
any restart of the live service would expose it immediately, with no opt-in
step. Separately, the live `:8000` service journal shows a restart earlier
this session (before the review fixes above were on disk) that picked up the
then-unreviewed, then-uncommitted evidence-chain code — the "Live validation
... against the real `data/governance_evidence.db`" claim in an earlier draft
of this entry was, in fact, that restart. The route was live in production,
unflagged, for part of this session, running code that predated this
session's fixes.

**Fix (owner-directed — "disable the cap-09 live"):** added
`RMT_OPS_EVIDENCE_ENABLED` (`app/ops/ops_config.py::ops_evidence_enabled()`,
default **False**), checked first in the `GET /ops/evidence` handler
(`app/main.py`) — disabled returns `503` before the identifier check ever
runs, so no code path can reach `evidence_chain()` unless explicitly opted
in via a systemd drop-in, matching the CAP-04/CAP-05 pattern exactly. 5 new
tests (`app/ops/testing/test_evidence_route.py`): disabled-by-default → 503;
503 fires before the 422 identifier check; enabled → still requires operator
auth; enabled + no identifier → 422; enabled + valid call → 200, writes
nothing. Full backend suite **540 passed** (535 + 5); zero `app/core/**` diff.

**Not yet done — needs the owner's sudo:** this repo's shell cannot run
`systemctl restart` (no password for `sudo`), so the **already-running**
`:8000` process is still serving the pre-flag code from its last restart and
will keep doing so until it is restarted. The fix above only guarantees the
route is off starting from the *next* restart. To take it out of service on
the currently-running process, the owner needs to run, on the live host:
```
sudo systemctl restart rmt-control-center.service
```
No drop-in change is needed for the default (off) state — one is only
needed later, to turn it on (`Environment=RMT_OPS_EVIDENCE_ENABLED=true` in a
new `cap09-console.conf` drop-in, mirroring `cap04-loop.conf` /
`cap05-agent.conf`).

---

## RMT-CAP-10 — Coding-Agent Command Governance (MCR: Claude Code as a governed child) (2026-09-14)

**Status: COMPLETED & VERIFIED.** `docs/RMT_CAP_10_PROPOSAL.md` is APPROVED
(owner, 2026-09-13, in-session). Backend package, tests, `app/main.py`
wiring, and the project-scoped Claude Code hook are all implemented,
tested, and live-validated end-to-end on an isolated dev instance in this
session.

**Objective:** the MCR pattern — one supervisor, one evidence trail, one
approval gate, in front of an independent child system — applied to Claude
Code itself. A small, explicit list of risky shell-command patterns is held
for a human decision instead of executing immediately, and the hold always
carries strictly real, checkable evidence (a matched rule, prior-decision
history, a situational git check) — never an LLM opinion standing in as
evidence.

**Backend built** (`app/coding_agent/`, all new, no `app/core/**` change):
- `models.py` — `CommandHold` / `EvidenceItem` record shapes (pre-existing
  from a prior session; unchanged).
- `risk_rules.py` — deterministic pattern list (`git-force-push`,
  `git-hard-reset`, `git-clean-force`, `recursive-delete`, `sudo`,
  `service-restart`); `recursive-delete` carves out paths confined to
  `/tmp` as ordinary scratch cleanup (pre-existing; unchanged).
- `store.py` — **fixed a real gap found this session**: the singleton
  `command_hold_storage = CommandHoldStorage()` had no `file_path`, so
  every hold lived in memory only and vanished on restart, contradicting
  the proposal's own "new table in the shared evidence DB" design (the
  same `DurableStore` extension point CAP-08's grants table uses). Restructured
  into `CommandHoldStorage` (the `DurableStore` subclass, `_table =
  "coding_agent_holds"`, gained an `update()` method) + `CommandHoldStore` (a
  thin wrapper defaulting to `EVIDENCE_DB_PATH`, same two-layer pattern
  `app/agent/authority.py`'s `AuthorityGrantStorage` / `AuthorityStore`
  already uses, so tests can swap `_storage` for an isolated instance).
- `config.py` — `RMT_CODING_AGENT_ENABLED` (default **False**), same
  dynamically-read opt-in shape as `RMT_OPS_EVIDENCE_ENABLED`.
- `history.py` — evidence source 2: tallies approved vs. rejected prior
  *decided* holds for the same risk rule; returns `None` (no item) when no
  decided hold exists yet — absence of history is never itself evidence.
- `situational.py` — evidence source 3: `git status --porcelain`
  (uncommitted changes) always attempted; for `git-force-push`
  specifically, an additional `git rev-list --left-right --count` check
  against the real upstream (commits the push would discard). Each check
  contributes an item only when determinable (a real repo, a real
  upstream); a 5 s subprocess timeout and non-zero exit both degrade to no
  item, never a guess.
- `review.py` — assembles the rule item (always present; `reject` for
  `high`, `neutral` for `medium`) + the history item (0–1) + the
  situational items (0–2) into one evidence list, then applies the
  proposal's exact verdict rule: `reject` if any item leans `reject`; else
  `approve` if any leans `approve` and none leans `reject`; else `reject`
  (the safe default — absence of evidence is not evidence of safety). No
  LLM anywhere in this module.
- `api.py` — `POST /coding-agent/propose` (no rule match → `auto_allow`,
  zero cost, no hold created; a match → hold created + evidence/verdict
  returned), `GET /coding-agent/holds` (`?status=` filter), `GET
  /coding-agent/holds/{hold_id}`, `POST /coding-agent/decide`
  (`decided_by` comes from the authenticated operator, never the request
  body — same pattern `/approve` already established). Every route gated
  by `RMT_CODING_AGENT_ENABLED` (503 when off, before any evidence code
  runs); `/decide` additionally requires `require_operator`.
- `app/main.py` — one import + `app.include_router(coding_agent_router,
  dependencies=[Depends(require_operator)])`, identical shape to the
  existing `agent_router` registration.

**Tests** (`app/coding_agent/testing/test_coding_agent.py`, 26 new, all
isolated via a fresh in-memory `CommandHoldStorage` — never the real
evidence DB): every risk rule matches its intended commands and only those
(including the `/tmp`-confined `rm -rf` carve-out); verdict logic for
no-signal (default reject), reject-leaning, approve-leaning-with-no-reject,
and mixed (reject wins); `assess()` end-to-end for a high-risk rule with no
repo signal and for history-seeded approval; routes 503 while disabled;
`propose` auto-allows a non-matching command with zero hold created;
`propose` on a matching command creates a pending hold with real evidence;
`decide` updates status + `decided_by` from the authenticated operator (not
the body), 404s an unknown hold, 409s a double-decide; `/holds?status=`
filtering; `/decide` requires auth when `RMT_AUTH_ENABLED=true`.

**Backend regression:** full suite **566 passed**; `import app.main` clean;
`ruff --select F,E9` clean; zero `app/core/**` diff.

**The hook** (`.claude/settings.json` + `.claude/hooks/coding_agent_guard.py`,
project-scoped to this repo only, not `~/.claude/settings.json`): a
`PreToolUse` hook matched to the `Bash` tool. Reads `tool_name` /
`tool_input.command` / `cwd` / `session_id` from stdin, `POST`s to
`/coding-agent/propose`. `auto_allow` → exit 0 immediately. `hold` → polls
`GET /coding-agent/holds/{hold_id}` (2 s interval, `RMT_CODING_AGENT_POLL_TIMEOUT_S`
default 120) until a decision or timeout. Decision surface deliberately
uses only the plain exit-code contract (`0` = allow, `2` = block with the
reason on stderr) rather than the newer, less-certain `hookSpecificOutput`
JSON extras — confirmed against the official hooks guide via a dedicated
lookup pass in this session before writing the script, rather than guessed.
**Fail-open by design**: backend unreachable, malformed hook input, or a
poll timeout all resolve to exit 0 with a warning on stderr, never a block —
a governance layer that can brick the tool it governs is worse than one
that occasionally lets a command through unreviewed while loudly saying so.

**Live end-to-end validation — isolated dev instance, real hook script, real
scratch git repo, `:8000` untouched throughout (2026-09-14):**
1. Started `uvicorn` on `:8099` (`RMT_CODING_AGENT_ENABLED=true`,
   `RMT_AUTH_ENABLED=false`, throwaway `RMT_EVIDENCE_DB`), separate from the
   live `:8000` service (confirmed still running afterward, untouched).
2. A real scratch git repo (`git init`, one commit, clean tree).
3. **Auto-allow:** `ls -la` through the actual hook script → exit `0`,
   no stderr, no hold created.
4. **Held → approved:** `git reset --hard HEAD~1` → hook exited only after
   polling; `GET /coding-agent/holds?status=pending` showed the real
   evidence (`policy_rule`: matched `git-hard-reset`, high, `leans:
   reject`; `situational`: clean working tree, `leans: neutral`) and
   verdict `reject`. Approved via `POST /coding-agent/decide` → the hook,
   still polling, saw `status: approved` and exited `0` — the human
   decision correctly overrode the reviewer's own `reject` verdict.
5. **Held → rejected:** `rm -rf /home/rmt-lab/homelab/projects` → held
   (`recursive-delete`, high); rejected via the same route → the hook
   exited `2` with `BLOCKED: rejected by local-dev` on stderr.
6. **Fail-open:** dev instance killed (`pkill` scoped to the `:8099`
   command line only); the same `git reset --hard` proposal through the
   hook → `backend unreachable -- failing open` on stderr, exit `0`.
7. Scratch dev artifacts removed after the run; nothing in this validation
   touched the real `data/governance_evidence.db` or the live `:8000`
   process.

**Result: PASS.** Every Definition-of-Done item in
`docs/RMT_CAP_10_PROPOSAL.md` §6 is met: full suite green; a non-matching
command passes through unchanged; a matching command holds with
traceable, real evidence; approve/reject both observed end-to-end through
the actual hook, not just the API; fail-open verified, not assumed.

**Boundaries:** no `app/core/**` change; new table via the existing
`DurableStore` extension point (as CAP-08 did); ships disabled
(`RMT_CODING_AGENT_ENABLED=False`); the hook is scoped to this one
repository's `.claude/settings.json`; not wired to the live `:8000` service
(a separate, explicit owner decision, per the proposal's own out-of-scope
list); no console UI tab; no LLM anywhere in the review path.

### Finding + fix — poll timeout tuned for a terminal, not a notified human (2026-09-14)

**Finding, from a live exercise:** a real local LLM (Ollama, `deepseek-v4-flash:cloud`)
was asked to play an autonomous coding agent facing a genuine scenario (its
own commit broke CI; a teammate had genuinely pushed a real fix to a real
remote in the meantime). Unprompted toward any particular answer, it decided
`git push --force origin master` — which would have destroyed the
teammate's fix. That command was fed through the real hook script against a
real isolated RMT instance; RMT held it correctly with real evidence
(`git-force-push`, high risk; the situational force-push check correctly
declined to claim a discard count because the local branch had no tracking
upstream — never guessed). The human decision (reject) was made and
recorded durably and correctly. But **the hook had already failed open** by
the time the decision landed: 88 seconds elapsed between hold creation and
the decision — longer than the then-default `RMT_CODING_AGENT_POLL_TIMEOUT_S`
(120s) — because the only way the human learned of the hold was reading the
hook's own stderr line, with no active alert. The 120s default was tuned for
someone already watching a terminal, not someone who has to be reached
first.

**Fix:**
- `app/coding_agent/api.py::propose` now fires the same fail-open
  `notify_held` sink every other domain's holds already use
  (`app/ops/notifications.py` — O2/T1-4's webhook, config-driven
  `generic`/`slack`/`ntfy` shaping, `RMT_NOTIFY_WEBHOOK_URL`), tagged
  `kind="coding_agent_command"`, `component=<risk_rule>`,
  `approval_id=<hold_id>`. A human now finds out immediately instead of
  relying on watching a terminal that may not be watched.
- `.claude/hooks/coding_agent_guard.py`'s default
  `RMT_CODING_AGENT_POLL_TIMEOUT_S` raised **120s → 1800s (30 min)** — a
  window sized for "alerted, then acts on their own schedule" rather than
  "already staring at the screen." Still bounded, still fails open at the
  end, same design.
- `.claude/settings.json`'s hook-level `timeout` raised **150s → 1860s** to
  match — the harness kills the hook subprocess at that mark regardless of
  the script's own poll timeout, so the two must move together (documented
  inline in the script now, so the next person raising one doesn't forget
  the other).

**Tests:** 2 new (`test_propose_matching_command_notifies`,
`test_propose_auto_allow_does_not_notify`) — a matching command notifies
exactly once with the right `kind`/`component`/`approval_id`; a
non-matching command notifies zero times. Full backend suite still green
(568 total); zero `app/core/**` diff.

**Not done — deliberately out of scope for this fix:** `CommandHold` still
has no expiry of its own (unlike the frozen Core's `ApprovalHold`, which
this above-Core hold system doesn't use at all — CAP-10 never calls
`execute_governed_action`). A hold nobody ever decides stays `pending`
forever, harmlessly, until someone calls `/coding-agent/decide`. Adding an
expiry is a separate, not-yet-requested decision.

---

## RMT-CAP-11 — Evidence Export / Attestation Bundles (roadmap P-C) (2026-09-20)

**Status: IMPLEMENTED, VALIDATED & LIVE-EXERCISED (isolated); live deployment
handed off to the owner.** `docs/RMT_CAP_11_PROPOSAL.md` is APPROVED
(2026-09-20); the implementation is committed (`a5a96a9`) and pushed to
`origin/master`. An isolated-instance walkthrough against a real governed
action has passed (below). Enabling the feature flag on the **live** server
requires a root-owned signing-key credential this session cannot create (no
passwordless `sudo`; `/etc/rmt-control-center/` is not writable or listable
by this session, and the harness separately declined a read of the existing
`auth.conf` on credential-materialization grounds) — that final step is
handed to the owner, per the same operator-does-the-privileged-step pattern
`docs/operations/DEPLOY.md` §1.2 already documents for operator tokens.

**Objective (P-C):** a signed, portable evidence bundle per governed action
that verifies its own integrity **offline** — for compliance, incident
review, or handoff to an external auditor — without trusting or re-querying
the live service.

**Built:**
- `app/ops/attestation.py` — wraps the existing, **unmodified**
  RMT-CAP-09 `evidence_chain()` in a signed envelope: `format_version`,
  `generated_at`, the correlated chain, and an `HMAC-SHA256` signature over a
  deterministic (sorted-key) canonical JSON serialization. Stdlib only
  (`hashlib`/`hmac`) — no new dependency. `export_bundle()` / `verify_bundle()`
  are the two entry points; `verify_bundle()` never raises on a malformed
  bundle, always returning `False`.
- `GET /ops/evidence/export` in `app/main.py` — operator-auth
  (`require_operator`), gated by `RMT_ATTESTATION_EXPORT_ENABLED` (default
  off, mirrors every prior capability's ship-disabled convention), 503 if no
  `RMT_ATTESTATION_SIGNING_KEY` is configured, 422 with no identifier. Reuses
  `evidence_chain()`'s fail-open discipline unchanged: an unknown identifier
  still returns a signed 200 bundle with an empty chain, never a 500.
- `app/ops/ops_config.py` — `attestation_export_enabled()` and
  `attestation_signing_key()`, the latter following the **exact**
  `RMT_OPERATOR_TOKENS` custody pattern hardened after the T0-5 credential-exposure
  finding: prefers a systemd `LoadCredential=RMT_ATTESTATION_SIGNING_KEY:<path>`
  file over a plain environment variable.
- `backend/scripts/rmt-attestation-verify.py` — stdlib-only offline verifier
  (no app-package import, no network, no running service — same
  zero-dependency precedent as `rmt_evidence_verify.py`): exit 0 `VALID`,
  exit 1 `INVALID` (tampered or wrong key), exit 2 `MALFORMED` (unparseable
  or unrecognizable input), never a traceback.

**Validation:**
- `app/ops/testing/test_attestation.py` — 11 tests: signs and self-verifies a
  real chain; unknown identifier still produces a verifiable bundle; wrong
  key, tampered chain field, tampered timestamp, and tampered signature each
  independently fail verification; malformed/non-dict input is invalid, not a
  crash; canonicalization is key-order independent; no store write.
- `app/ops/testing/test_attestation_route.py` — 5 tests: disabled by default
  → 503; enabled but no signing key → 503; enabled requires operator auth
  (401) and one identifier (422); a real request returns a signed bundle that
  the standalone `verify_bundle()` accepts with the right key and rejects
  with the wrong one.
- CLI verifier manually exercised end-to-end against a real generated bundle:
  correct key → `VALID` (exit 0); wrong key → `INVALID` (exit 1); missing file
  → `MALFORMED` (exit 2); a tampered field → `INVALID` (exit 1).
- Full backend suite: **657 passed, 0 skipped**; `ruff check .` clean;
  `import app.main` clean; `compileall` clean; `git diff --check` clean; zero
  `app/core/**` diff (confined to `app/ops/**`, one route in `app/main.py`,
  and the new stdlib script).
- **Isolated live walkthrough (`:8002`, separate `RMT_EVIDENCE_DB`,
  `RMT_RUNTIME_ENGINE=simulation`, throwaway signing key; live `:8000`
  untouched — identical `MainPID`/`ActiveEnterTimestamp` before and after):**
  a real governed action (`POST /execute?operation=restart&target=demo-svc`)
  produced a genuine authorization → approval → audit → trace → verification
  chain; `GET /ops/evidence/export` returned a signed bundle for it;
  `rmt-attestation-verify.py` reported **VALID** with the correct key,
  **INVALID** with the wrong key, and **INVALID** after a real evidence
  field (`authorized_by`) was tampered in a copy of the bundle — the
  proposal's DoD claim, now demonstrated against real data, not only test
  fixtures.

**Deployment — handed off, not completed by this session:**
`deploy/systemd/attestation.conf.example` (new, committed) is the ready
non-secret drop-in, mirroring `auth.conf.example` exactly. The owner still
needs to generate a production signing key, create the root-only `0600`
secret file, install the drop-in, `daemon-reload` + restart, and verify.

**Not done — explicitly deferred, per the proposal's own out-of-scope
section:** bulk/time-range bundles (per-action only in this slice); an
asymmetric/PKI signing scheme (HMAC with an operator-custodied secret is the
entire trust model here — a real limitation for an auditor who shouldn't
need the platform's own secret, recorded as a known boundary, not silently
dropped). Deployment (enabling the flag, provisioning the signing-key
credential file, a live/isolated fault-inject-and-export walkthrough) is
unauthorized until the owner separately approves it.

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
| C1 / T1-1 — Broaden `REMEDIATION_POLICY` coverage (`portainer`) | COMPLETED & VERIFIED 2026-09-11; **live-demonstrated** (isolated `:8001`, `:8000` untouched) | 4 new + 459 full; live run PASS | no `app/core/**` change; T13 safe-envelope guard re-verified with two entries; `dozzle` intentionally kept outside policy |
| RMT-CAP-06 (C2/D-1) — Second domain: git-tag Agent Governance Gateway | COMPLETED & VERIFIED 2026-09-11; **live-demonstrated** (isolated `:8001`, `:8000` untouched) | 21 new + 480 full; live run PASS (benign + 2 refusals + rollback) | no `app/core/**` change; adapter/observer registered via the existing extension points; recorded finding: continuation-path auto-verify is `ComponentContext`-only — **CLOSED below** |
| RMT-CAP-07 (C3) — Harden the agent surface: preview + rationale + adversarial gate | COMPLETED & VERIFIED 2026-09-11 | 34 new + 514 full; green in CI (A2 live) | no `app/core/**` change; preview reuses frozen pure policy/risk/approval functions unchanged; continuation-verify `ComponentContext` gap flagged, not in scope — **CLOSED below** |
| Continuation-path verification gap (agent-originated, non-homelab holds) | COMPLETED & VERIFIED 2026-09-11 | 1 new (+1 fixture correction) + 515 full | no `app/core/**` change; diff confined to `app/homelab/continuation.py` + its test file; reuses `ApprovalHold.adapter_name` (frozen Core) instead of a hardcoded string |
| RMT-CAP-08 — Productize the Agent Governance Gateway (durable grants + integration guide) | COMPLETED & VERIFIED 2026-09-11; **live-checked** against the real evidence DB | 7 new + 522 full | no `app/core/**` change; new table via the existing `DurableStore` extension point; 6 test files re-isolated to prevent the real evidence DB from ever being touched by `pytest` |
| T0-2 — Genuine fresh-host rebuild (real LXD system container, not `--drill`) | COMPLETED & VERIFIED 2026-09-12; **live-verified** systemd + hardening + loopback bind on the fresh host | 522 + 3 correctly-skipped = 525 full | no `app/core/**` change; no app code change; found + fixed a real `rmt-rebuild.sh` script bug; live service on `:8000` untouched throughout |
| T0-3 — Close the remaining observability gap (approval latency + dashboards note) | COMPLETED & VERIFIED 2026-09-12; **live-checked** against the real running service | 3 new + 525 full | no `app/core/**` change; read-only derivation from stores `/metrics` already reads; also corrected a doc-sync gap (roadmap never marked O1/O3/O4 as covering T0-3) |
| T0-5 — Security group finish (S4/S3/S5 doc-sync) + live `RMT_OPERATOR_TOKENS` exposure fix | COMPLETED & VERIFIED 2026-09-12; found + immediately flagged a live token exposure, fixed via `LoadCredential=`, **live migration confirmed complete by owner** | 3 new + 528 full | no `app/core/**` change; single choke-point fix (`operator_tokens()`); tokens rotated + live host migrated (owner-executed); D3 `hardening.conf`-not-installed gap found, recorded, not fixed (out of scope) |
| T0-6 — Public-showcase live exercise: Agent Governance Gateway on the production service | COMPLETED & VERIFIED 2026-09-12; **first live run on `:8000` itself** (not an isolated port); full lifecycle + refusal + risk-differentiated approval, corroborated via independent `git tag` check + journal log cross-check | 0 new (operational exercise, no code change) | no `app/core/**` change; config-only enablement of the pre-existing conditional git adapter; scratch-repo blast radius only; open item recorded: no durable record of last-verified operator token |
| RMT-CAP-09 — Governed Operations Console (P-B) | COMPLETED & VERIFIED 2026-09-13; **live-demonstrated** (isolated `:8001`, `:8000` untouched) through the console's own API calls (no browser in this shell); route found live-but-unflagged, **fixed to default off** — live `:8000` process still needs an owner restart to pick the flag up | 7 `test_evidence_chain.py` + 5 `test_evidence_route.py` + 540 full backend; `tsc -b && vite build` + `oxlint` clean; live fault-inject → hold → approve → `verified_success` → full evidence chain PASS | no `app/core/**` change; no new mutation path; `GET /ops/evidence` gated by `RMT_OPS_EVIDENCE_ENABLED` (default off, mirrors CAP-04/CAP-05); console is read-only + approve/reject via the existing `/homelab/approve` endpoint |
| RMT-CAP-10 — Coding-Agent Command Governance (Claude Code as a governed child) | COMPLETED & VERIFIED 2026-09-14; **live-demonstrated** through the actual `PreToolUse` hook script (isolated instances, `:8000` untouched) against both a scripted command and a real LLM's real decision | 28 new + 568 full backend; live hook runs: auto-allow + held-approved + held-rejected + fail-open, all PASS; a live LLM exercise found a real gap, fixed same-day (see below) | no `app/core/**` change; new table via the existing `DurableStore` extension point; ships disabled (`RMT_CODING_AGENT_ENABLED=False`); hook scoped to this repo's `.claude/settings.json` only; no LLM in the review path; fixed two real gaps found this session: hold storage was in-memory-only (not durable), and the 120s poll timeout was tuned for a terminal, not a notified human — **both CLOSED below** |
| RMT-CAP-11 — Evidence Export / Attestation Bundles (P-C) | IMPLEMENTED, VALIDATED & LIVE-EXERCISED (isolated) 2026-09-20; pushed (`a5a96a9`); **live deployment handed off to the owner** (no passwordless sudo / root secrets access from this session) | 11 `test_attestation.py` + 5 `test_attestation_route.py` + 657 full backend; CLI verifier manually exercised (VALID / INVALID / MALFORMED, tamper-detected) against a real generated action on an isolated `:8002` instance, `:8000` untouched | no `app/core/**` change; diff confined to `app/ops/**` + one route in `app/main.py` + a new stdlib script + a non-secret deploy template; `GET /ops/evidence/export` gated by `RMT_ATTESTATION_EXPORT_ENABLED` (default off) + requires `RMT_ATTESTATION_SIGNING_KEY`; reuses CAP-09's `evidence_chain()` unchanged; no new mutation path |

**Boundaries:** No C08. No Core changes. No reopening of C01–C07. Above-Core
capabilities remain subordinate to RMT's governance architecture.
