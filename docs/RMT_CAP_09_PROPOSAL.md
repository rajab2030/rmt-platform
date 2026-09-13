# RMT-CAP-09 — Governed-Evidence Console (roadmap P-B) — Proposal

**Status:** **APPROVED 2026-09-13 (owner).** Approved as a proposal under the
platform's standing working method (an approved per-capability proposal is the
precondition before any code is written). This record describes what P-B would
build and how it would be governed. The detailed implementation draft follows in
`docs/RMT_CAP_09_IMPLEMENTATION.md`; **this approval authorizes no code to land
until the owner gives a further go-ahead on the implementation plan**.

**Classification:** Above-Core / product surface (roadmap `P-B`,
`docs/RMT_ABOVE_CORE_ROADMAP.md` §7). **No C08. No frozen Core change. No
reopening of C01–C07.** Confined to `frontend/**` + `app/ops/**` (+ a read-only
route in `app/main.py`). Does not touch the governed mutation path.

---

## 1. Objective

Make RMT *usable as a product, not just inspectable as an API*. Today every
governed action — authorization, hold, approval, execution, verification, and
its Learn record — exists as durable evidence (SQLite) and is reachable over
authenticated HTTP, but there is **no surface a human operator uses to see it**.
An operator outside the owner's head cannot see *what an agent proposed, why it
was held, who approved it, or whether it verified* without scripting API calls.

This capability ships a real, read-only web console over the authorization /
approval / hold / audit / trace / verification evidence and the loop/agent
status, with approve/reject for held items — the roadmap's own "P-B" do-the-console
once one domain is real and there is something worth looking at.

**Why now:** the two preconditions the roadmap set for P-B are both met:
(a) a real, second domain (D-1 Agent Governance Gateway) is live and public —
there is specific, non-homelab evidence to look at; (b) the repository went
public on 2026-09-12 — there is an audience beyond the owner, which is the
documented trigger for Phase D surface work. The owner directive has been "keep
building toward something usable"; the console is the missing usability layer.

## 2. What already exists (reused, not rebuilt)

| Piece | Location / route | Role here |
|---|---|---|
| React + TypeScript + Vite 8 frontend scaffold | `projects/homelab-control-center/frontend` (React 19, `tsc -b && vite build`, oxlint) | The app shell to extend. Today it is wired **only** to `/containers` start/stop/restart + `/config` + `/platform/state` — the old homelab container console, not governed evidence. |
| Open-holds view (read-only) | `GET /ops/holds` (T1-4, operator-auth) | The approval queue to render: per hold, `actionable` / `expired` / `record_decision` / `record_terminal`, S3 provenance (`granted_by`, `agent_id`), age. |
| Verification ledger (read-only) | `GET /ops/verifications` (B1b, operator-auth) | Per executed action: `effective_status` (`verified_success` / `state_mismatch` / `adapter_execution_failed` / `unverified` / `observation_unavailable`), newest-first, `?effective_status=` filter. |
| Raw lifecycle / status | `GET /health` (open), `GET /metrics` (open, Prometheus), `GET /agent/status` (operator-auth) | Loop state, agent surface, approval-latency and hold-queue metrics. |
| Approval continuation | `POST /approve?approval_id&approved` (operator-auth, generic) and `POST /homelab/approve` (operator-auth, homelab continuation + Learn closure) | The existing approve/reject path the console's buttons call. **Not modified.** |
| Durable evidence stores | `data/governance_evidence.db`, tables `authorizations, approval_records, approval_holds, audit, traces, verifications, agent_authority_grants` | The data the console reads; already correlation-keyed by `action_id` / `approval_id` / `execution_id`. |
| TLS reverse proxy | Caddy behind T0-5 (S4) | How the built frontend is served in production. |

## 3. Design (in scope)

### 3a. Frontend — evidence console views (read-only)

- **Operator token entry.** A token field (from `RMT_OPERATOR_TOKENS` /
  `auth.conf`) held client-side and sent as an `Authorization: Bearer` /
  `X-API-Key` header on authenticated calls. Explicitly **not** logged and not
  stored in the evidence. This is the one place the UI handles a credential,
  and it stays in the browser only.
- **Open-holds queue view.** Renders `GET /ops/holds`: each PENDING hold with
  its `actionable`/`expired`/`record_terminal` state and provenance, plus an
  **Approve / Reject** action that calls the existing `POST /approve` (or
  `/homelab/approve` for homelab-originated holds) with `approval_id` +
  `approved`. S3 separation-of-duties responses (403) are surfaced as-is.
- **Verification ledger.** Renders `GET /ops/verifications` with the
  `effective_status` filter, so an operator can see every executed action and
  whether it actually verified — the platform's core credibility signal.
- **Loop / agent / metrics panel.** Loop state (`/health`), agent surface
  (`/agent/status`), and live `rmt_*` metrics (`/metrics`).
- **Evidence-correlation view.** By `action_id` (and by `approval_id` /
  `execution_id`), shows the full `Govern → Verify` chain: authorization →
  approval record → hold → trace → verification (and failed-execution
  evidence) for that action, drawn from the durable stores.

### 3b. Backend — one additive read-only correlation route

The roadmap's P-B boundary forbids business logic in the frontend, so the
correlation assembly lives **server-side**: a new, read-only,
operator-authenticated route in `app/ops/**` (registered in `app/main.py`)
that resolves a supplied `action_id` / `approval_id` / `execution_id` against
the existing stores and returns the correlated evidence chain. It **writes
nothing**, is **fail-open** (returns an empty/`[]` chain on any read error,
never 500s), and mirrors the read-only derivation discipline already used by
`/ops/holds` and `/ops/verifications`.

This is the only new backend code and it is **not** on the governed mutation
path — it is a read of evidence the governed path already produced.

### 3c. Frontend plumbing

- Add Vite dev proxy entries for `/ops`, `/approve`, `/homelab/approve`,
  `/agent`, `/health`, `/metrics` (today only `/config`, `/containers`,
  `/modules`, `/monitor` are proxied). In production the built `dist/` is
  served behind Caddy (T0-5) like the current app.
- `tsc -b && vite build` clean; oxlint clean.

## 4. Explicitly OUT of scope

- **No new mutation path.** The browser may only call the existing
  `/approve` / `/homelab/approve` endpoints. No new write endpoint, no way for
  the UI to execute, continue, or bypass a hold.
- **No RBAC / multi-operator identity** — that is P-D, a separate decision,
  and only if the deployment moves past trusted-LAN few-operators.
- **No evidence export / attestation bundles** — that is P-C, a separate
  candidate (readily composable later with the same stores).
- **No policy editor** (P-A) and no new domain.
- **No `app/core/**` change, no change to any governed-lifecycle behavior,
  no change to `/metrics` semantics.**

## 5. Boundary

- No `app/core/**` change. The frozen Core and the governed mutation path are
  untouched; evidence stays the authority.
- The frontend is read-only **except** the approve/reject buttons, which call
  the existing authenticated endpoints unchanged.
- The new correlation route is read-only and fail-open; it derives from
  existing durable evidence and never writes, never invents a resolution, and
  never re-raises governance errors as 500s.
- Tokens are client-side only, never stored in evidence or logs.

## 6. Done when (Definition of Done)

**Implementation + Integration + Enforcement + Validation + Evidence**:

- The built app, served behind Caddy in production, lets an operator:
  - authenticate with an operator token,
  - see the open-holds queue with `actionable`/`expired` state and provenance,
  - approve and reject a hold from the browser through the existing endpoints
    (S3 403 surfaced correctly),
  - see the verification ledger and the loop/agent/metrics status,
  - open any `action_id` and see its full `Govern → Verify` evidence chain.
- `tsc -b && vite build` passes; oxlint clean; no `app/core/**` diff; full
  backend suite green.
- A live (owner-authorized, isolated instance) walkthrough demonstrates the
  loop: fault-inject → hold appears in the console → approve in the console →
  governed execute → `verified_success` → shown in the console.

## 7. Tests

- Backend: new tests for the read-only correlation route (resolves a chain
  from the isolated test stores; unknown id → empty; store read failure →
  `[]`, not 500; operator-auth required; no write side-effect asserted).
- Existing `/ops/holds` and `/ops/verifications` behavior unchanged (regression).
- Frontend: `tsc -b` type-check + `vite build` + oxlint as the standing gate.
- No test in this change ever writes to the real `data/governance_evidence.db`.

## 8. Validation plan

- Full backend suite green, growing by the new route tests.
- `tsc -b && vite build` clean; oxlint clean; `import app.main` clean.
- Owner-authorized live exercise on an **isolated** `:8001` instance (same
  discipline CAP-04/05/06 used): fault-inject a service, watch the hold appear
  in the console, approve from the browser, see the governed restart verify,
  confirm the evidence chain renders — then stand the isolated instance down.
  The live `:8000` service is not touched during the walkthrough.

---

*Per the standing working method: this becomes approved work only when the owner
selects it. The proposal itself is docs-only and makes no code change.*
