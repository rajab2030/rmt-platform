# RMT — Guarantees and Non-Guarantees

**Status:** LIVING RECORD, created 2026-09-10 (roadmap item **B3**,
`docs/RMT_IMPROVEMENT_ROADMAP.md` §4).
**Audience:** someone evaluating what RMT actually promises. Pairs with
`docs/RMT_THREAT_MODEL.md`.

Each lifecycle stage below states, in plain language, **what it asserts**, **what
it does not assert**, and **the evidence** it leaves. Every non-guarantee traces
to a recorded decision (`docs/RMT_PRODUCTION_READINESS.md`) or a recorded gap
(`docs/RMT_FROZEN_CORE_DEBT.md`).

---

## 0. Fit — before the stages

**RMT fits:** discrete, consequential, verifiable state changes at
low-to-moderate volume, with a human approver acceptable for the risky subset,
initiated by people or by supervised agents.

**RMT does not fit** (do not rely on it here): sub-second latency paths,
high-throughput fan-out (10³⁺/sec), continuous tight-loop control, or actions
with **no observable outcome** — the Verify stage would have nothing to check
(`docs/RMT_ABOVE_CORE_ROADMAP.md` §2).

---

## 1. Understand — observation + context assembly

- **Asserts:** the decision inputs (module state, prior failures, component
  context, dependency graph) are assembled from Core **read-only** primitives
  before any decision is made. A degraded adapter or an `unknown_dependency` is
  **surfaced**, not hidden (`GET /health` runtime block; V3 503 on an
  unreachable capability).
- **Does not assert:** that the observed state is complete or millisecond-fresh;
  that an external system still matches what RMT last observed.
- **Evidence:** the trace record; `/platform/state`, `/health`.

## 2. Decide — governance policy + risk rating

- **Asserts:** every action is **policy-checked** (action policy is the
  authoritative gate) and **risk-rated** (governance risk is authoritative for
  approval) before authorization. Blocked / denied / unknown paths **never reach
  an adapter**.
- **Does not assert:** that the action catalogue is complete for a domain RMT
  has not been configured for — it is finite and per-domain (e.g.
  `REMEDIATION_POLICY` covers one component today; roadmap **C1** broadens it).
- **Evidence:** the audit record (decision, policy result, risk score),
  correlated by `action_id`.

## 3. Govern — the manual-approval hold for the risky subset

- **Asserts:** an action whose risk requires approval is **held** — nothing
  executes — until an **authenticated** operator approves it (identity from the
  token, not the body — S2-lite). With `RMT_AUTH_SEPARATION` on, the approver
  **cannot** be the agent's grantor or the proposer (403 — S3).
- **Does not assert:**
  - that a hold survives past `APPROVAL_HOLD_TTL_SECONDS` (300 s) — an
    un-approved hold **expires** (roadmap **B2** adds a durable approval
    request);
  - that a resolved hold's **hold record on disk** reads `approved` before the
    next startup reconcile — the approval **record** is authoritative
    (DEBT **D1**; readiness **E2**);
  - that separation-of-duties is enforced when the flag is **off** (the default
    — readiness **S3**).
- **Evidence:** approval hold + approval record, correlated by `approval_id`;
  `GET /ops/holds`; the O2 held-action alert.

## 4. Authorize — minting the bound execution authorization

- **Asserts:** the execution authorization is created at **exactly one site**
  inside the governed chain, bound to the approved action; **no direct execution
  without a valid bound authorization**. For agents, the authority grant is
  **single-use, time-limited, and scoped to operation + target** (capability ≠
  authority).
- **Does not assert:** anything about a caller-supplied authorization — it is
  **never** caller-controlled.
- **Evidence:** the `ExecutionAuthorization` record (Core-owned, append-only);
  the E6 startup cross-check flags any authorization whose approval linkage is
  inconsistent.

## 5. Execute — the one governed mutation path

- **Asserts:** the state change passes through
  `execute_governed_action → execution_engine.execute → adapter`, and there is
  **no second unmanaged mutation path** in Core scope. Adapters are **executors
  only** — they cannot authorize, approve, override policy, redefine risk, or
  manufacture evidence. Execution policy is a **deny-only** final safety check.
- **Does not assert:**
  - general exactly-once execution. The 2026-09-18 review reproduced a race
    in direct concurrent Core approval continuation. A shared lock now
    serializes both HTTP continuation routes in the supported single-process
    deployment; deployment remains pending. Direct concurrent Core callers
    and multiple workers are outside that compensating control (DEBT **D6**);
  - that the adapter **succeeds** — it can fail; a failed adapter execution is
    recorded as the distinct status `adapter_execution_failed` (readiness
    **E3**), **not rolled back** (DEBT **D2**);
  - that the target cannot **also** be changed out-of-band by someone with host
    / Docker access — that is outside the trust boundary
    (`docs/RMT_THREAT_MODEL.md` §4).
- **Evidence:** the execution record + audit (`adapter=…`), correlated by
  `execution_id`.

## 6. Verify — post-execution post-condition check

- **Asserts:** for **module creation**, the Core's **trusted internal observer**
  asserts the post-condition. For the **wired** homelab / agent / remediation
  Docker operations, an **above-Core observer** performs a real read-only
  observation and feeds the **same frozen verifier**. Adapter success alone
  **never** manufactures `verified_success`. "Could not observe" is a real
  outcome, **not** a pass.
- **Does not assert:**
  - that **every** executed action is verified by the **Core verifier itself** —
    outside module `create` the Core records `observation_unavailable` by
    construction (DEBT **D3**);
  - that the operator `POST /execute` path is verified **today** (it is not,
    until proposal **B1**);
  - that `remove` / absent outcomes are verifiable today, or that a transient
    post-restart state won't read as a momentary mismatch (both addressed by
    **B1**).
- **Evidence:** the `VerificationResult` — status ∈ `verified_success` /
  `state_mismatch` / `verification_failure` / `observation_unavailable` /
  `adapter_execution_failed` — correlated by `execution_id`; the O4 `/metrics`
  verification-outcome counters.

## 7. Learn — history and learning

- **Asserts:** learning and history are **read-only** — they cannot invoke
  execution, mint an authorization, or mutate governance state.
- **Does not assert:** that learning changes future decisions automatically — it
  informs the Understand inputs; it is **not** a feedback controller.
- **Evidence:** governed-outcome history; the prior-failure lookups that feed
  Understand.

---

## 8. Cross-cutting guarantees

- Every governed action is **correlated** across authorization / approval /
  audit / trace / verification by stable IDs (G3).
- Evidence writes are **atomic** and survive a hard kill **byte-for-byte**
  (E1 / R1); startup **reconciles** hold ↔ record and **audits** authorizations
  (E2 / E6).
- **Auth is required** on every mutating route; the app **refuses to start** if
  auth is enabled but unconfigured (S1).
- The governed path runs **identically with a non-Docker adapter and with Docker
  absent** (resolves to `simulation`) — verified.

## 9. Cross-cutting non-guarantees

- **No high availability** — a restart / redeploy is minutes of downtime
  (readiness **R4**, ACCEPTED).
- **No multi-operator identity / RBAC** — shared bearer tokens; operators are
  trusted (threat model **(b)**; roadmap **P-D** for **(c)**).
- **No rollback engine** — safe-failure is a *recorded distinct status*, not an
  automatic revert (DEBT **D2**).
- **The Core is frozen** — a recorded Core gap gets an above-Core mitigation or
  an explicit accept-and-record, **never** a Core fix
  (`docs/RMT_FROZEN_CORE_DEBT.md`).
- **Alerting** routes to the journal only until an ops webhook sink is
  configured (readiness **O2**).
- **Not for** the poor-fit workloads in §0.
