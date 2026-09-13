# RMT-CAP-09 — Governed-Evidence Console — Detailed Implementation Plan

Companion to `docs/RMT_CAP_09_PROPOSAL.md` (APPROVED 2026-09-13). This is the
**draft implementation** the owner reviews before any code lands. No code has
been written. **Boundary (non-negotiable):** no `app/core/**` change; no new
mutation path; frontend is read-only except approve/reject via the existing
endpoints; no business logic in the UI (server computes classification); no test
in this change ever writes to the real `data/governance_evidence.db`.

---

## 1. Backend — one additive read-only correlation route

### 1a. New file `app/ops/evidence_chain.py`
Above-Core only (same discipline as `held_holds.py` / `ops/verifications`). One
pure, read-only, **fail-open** function:

```
evidence_chain(*, action_id=None, approval_id=None, execution_id=None) -> dict
```

- Reads the existing durable stores through their existing accessors:
  - `app.core.intelligence.actions.approval_storage.approval_hold_storage` (holds)
  - `...approval_record_storage` (approval records)
  - `app.core.intelligence.actions.authorization_storage.execution_authorization_storage` (authorizations)
  - `app.core.intelligence.execution.storage.execution_audit_storage` (audit)
  - `app.core.intelligence.execution.trace_storage.execution_trace_storage` (traces)
  - `app.core.intelligence.verification.storage.verification_storage` (verifications)
  - `app.agent.authority` authority store (agent grants, when an `agent-*` grant is implicated)
- Joins by the stable correlation keys already on every record:
  `action_id` ↔ `approval_id` ↔ `execution_id` (and `decision_id` / `authorization_id`).
  For an `action_id` lookup it returns the full **Govern → Verify** chain:
  authorization → approval record (decision) → hold (if held) → audit → trace →
  verification (incl. `adapter_execution_failed`), plus S3 provenance
  (`granted_by`/`agent_id`) where present.
- Lookup modes: `?action_id=`, or `?approval_id=` / `?execution_id=` which resolve
  to the same correlation group.
- **Fail-open & read-only:** any store read error is logged and contributes
  `[]` to that section, never a 500; returns a stable JSON shape
  `{"action_id", "approval", "execution", "verification", "trace", "provenance"}`.
  Writes nothing (verified by test).

### 1b. Wire in `app/main.py`
One route, operator-authenticated, mirrors `GET /ops/verifications` (B1b):

```
@app.get("/ops/evidence", dependencies=[Depends(require_operator)])
def ops_evidence(action_id: str | None = None, approval_id: str | None = None,
                 execution_id: str | None = None):
    # requires exactly one non-null identifier; 422 if none or >1
    return evidence_chain(...)
```

Read-only derivation; not on the governed mutation path.

### 1c. Backend tests — new `app/ops/testing/test_evidence_chain.py`
- resolves the full chain for a known `action_id` from the **isolated test
  stores** (`_setup_isolation` fixture pattern used across the ops tests),
- `approval_id` / `execution_id` modes resolve into the same correlation group,
- unknown id → empty sections, HTTP 200 (fail-open, no error),
- store-read failure (simulated) → `[]` sections, not 500,
- route requires operator auth (401 without token),
- **asserts no writes** occurred (store contents unchanged before/after call).
- Regression: existing `/ops/holds` and `/ops/verifications` behavior unchanged.

---

## 2. Frontend — evidence console views (read-only + approve/reject)

### 2a. Token handling — new `frontend/src/api/auth.ts`
- `getToken()` / `setToken()` / `clearToken()` over `localStorage`
  (the operator token from `RMT_OPERATOR_TOKENS` / `auth.conf`).
- `authFetch(path, init)` wraps `fetch` and attaches the token as a Bearer /
  `X-API-Key` header; on `401` it surfaces a "re-authenticate" state rather than
  echoing the token anywhere. **Token is never logged and never sent to evidence.**

### 2b. API client — new `frontend/src/api/governance.ts` (typed)
- `getHolds()` → `/ops/holds`
- `getVerifications(status?)` → `/ops/verifications?effective_status=`
- `getEvidence(actionId)` → `/ops/evidence?action_id=`
- `getSystemStatus()` → `/health`
- `getAgentStatus()` → `/agent/status`
- `getMetrics()` → `/metrics`
- `approveHold(approvalId, approved=true)` → `POST /approve`
- `approveHomelabHold(approvalId, approved=true)` → `POST /homelab/approve`
All authenticated except `/health` + `/metrics` (open), via `authFetch`.

### 2c. Types — new `frontend/src/types/governance.ts`
Reflect the backend shapes: `HeldItem` (with `actionable`/`expired`/
`record_terminal` + provenance), `VerificationRow`, `EvidenceChain`, `AgentStatus`.

### 2d. Components (in `frontend/src/components/`)
- `TokenGate.tsx` — token entry when 401 / unset; triggers `setToken`.
- `StatusPanel.tsx` — loop + agent + metrics summary (from `/health`, `/agent/status`, `/metrics`).
- `HoldsQueue.tsx` — renders `/ops/holds`; each row shows actionable/expired state,
  provenance (S3) and an **Approve / Reject** button calling `approveHold`
  (or `approveHomelabHold` for homelab-originated); surfaces S3 403 as a message.
- `VerificationLedger.tsx` — `/ops/verifications` table with `effective_status` filter.
- `EvidenceChain.tsx` — given an `action_id`, renders the full Govern→Verify chain.
- `App.tsx` — wire the above as tabs/views under `TokenGate`; keep existing
  container views on a separate tab (deprecated, not removed here).

### 2e. Plumbing
- `vite.config.ts`: add dev-proxy entries for `/ops`, `/approve`,
  `/homelab/approve`, `/agent`, `/health`, `/metrics` (today only `/config`,
  `/containers`, `/modules`, `/monitor`). Production: built `dist/` behind Caddy
  (T0-5), same origin, CORS already configured (S5).

---

## 3. Explicitly NO
- `app/core/**` change; governed mutation path; new write endpoint.
- RBAC (P-D), attestation bundles (P-C), policy editor (P-A), new domain.
- Token persistence beyond the operator's browser; token in any log/evidence.
- Business logic in the UI (classification stays on the server).

---

## 4. Definition of Done (from the proposal)
- `tsc -b && vite build` passes; oxlint clean; full backend suite green
  (grows by the new route tests); `import app.main` clean; no `app/core/**` diff.
- Operator can authenticate, see the open-holds queue, approve/reject a hold
  from the browser, see the verification ledger + status, and open any
  `action_id`'s full evidence chain.
- Owner-authorized live exercise on an **isolated `:8001`** instance:
  fault-inject → hold appears in console → approve in console → governed execute
  → `verified_success` shown; then stood down. Live `:8000` untouched.

---

## 5. Suggested commit shape (for review, not yet acted on)
Small, reviewable slices, each suite-green and each a no-`app/core` change:
1. `app/ops/evidence_chain.py` + tests.
2. `GET /ops/evidence` route + main.py registration (+ regression for holds/verifications).
3. Frontend: `auth.ts` + `governance.ts` + types + vite proxy.
4. Frontend: `StatusPanel`, `HoldsQueue`, `VerificationLedger`, `EvidenceChain`, `App.tsx` tab wiring.
5. Docs sync: README link, `docs/RMT_CAPABILITIES_EVIDENCE.md` placeholder.

---

*Draft implementation plan. Awaiting owner go-ahead before any code lands.*
