# RMT-CAP-08 — Productize the Agent Governance Gateway: Stable Contract + Persistent Grants — Proposal

**Status:** APPROVED 2026-09-11 (owner directive: "building a product on a
proven foundation... keep building toward something usable"; per the
roadmap's own process rule, M+ items get a written proposal before code —
this is that record, approved by direction rather than a separate
sign-off round).
**Classification:** Above-Core / domain. No C08. No frozen Core change. No
reopening of C01–C07.

---

## 1. Objective

RMT-CAP-06/07 proved the Agent Governance Gateway *works*. This makes it
*usable by something other than a test written by the same session that
built it* — the gap between "proven" and "product," per the roadmap's own
deferred D-1 scope. Two concrete gaps, both already named and accepted as
limitations in prior evidence entries:

1. **No stable, documented external contract.** FastAPI's auto-generated
   `/docs` exists but shows shapes, not workflow — an external integrator
   has no guide to the grant → propose → preview → approve → verify → receipt
   lifecycle, the decision vocabulary, or what's actually guaranteed to stay
   stable across releases.
2. **Authority grants don't survive a restart.** `AuthorityStore` is
   in-memory only (flagged, accepted, out of scope in the CAP-06 proposal
   §4: "a real limitation... revisit before CAP-06 is offered to a real
   external team"). That team is now the point of this proposal.

## 2. What already exists (reused unchanged)

| Piece | Location | Role here |
|---|---|---|
| `DurableStore` (SQLite backend, T0-1) | `app/core/intelligence/durable_store.py` (frozen) | The exact reusable persistence extension point six evidence stores already use. Above-Core code already instantiates it directly (`app/ops/verification/index.py`'s own comment names `app/agent/authority.py` as a sibling in-memory-by-design store — this proposal changes that design choice for authority specifically, not the pattern). |
| `ApprovalHoldStorage` / `ApprovalRecordStorage` | `app/core/intelligence/actions/approval_storage.py` | The exact subclass shape (`_table`, `_key_field`, `get_by_id`, `update` via `model_copy`) this proposal mirrors for grants. |
| `EVIDENCE_DB_PATH` | `app/core/intelligence/durable_store.py` (frozen constant) | The shared SQLite file (`data/governance_evidence.db`) every evidence store already writes to — a new table in it is additive, no schema change to existing tables. |
| FastAPI auto `/docs`, `/openapi.json` | `app/main.py` (already enabled, no config change) | Stays the raw schema reference; this proposal adds the workflow guide on top, not a replacement. |

## 3. Design

### 3a. Persistent authority grants — `app/agent/authority.py`

- `AuthorityGrant` converts from a plain `@dataclass` to a Pydantic
  `BaseModel` (same fields: `grant_id`, `operation`, `target`, `granted_by`,
  `expires_at`, `consumed`, `consumed_at`, `created_at`) — required by
  `DurableStore`'s `model_dump`/`model_validate`/`model_copy` contract.
- **New** `AuthorityGrantStorage(DurableStore)` — `_table =
  "agent_authority_grants"`, `_key_field = "grant_id"`, `get_by_id` +
  `update(**fields)` via `model_copy`, exactly mirroring
  `ApprovalHoldStorage`. Module-level singleton constructed with
  `file_path=EVIDENCE_DB_PATH` — the same shared file, a new table.
- `AuthorityStore` (unchanged public API: `grant` / `check` / `consume` /
  `get` / `list_active` / `reset`) becomes a thin wrapper over
  `AuthorityGrantStorage`, reading/writing through it instead of a bare
  dict. `grant()` → `storage.save(...)`; `consume()` → `storage.update(...)`;
  `check()`/`get()`/`list_active()` → read `storage.get_all()` /
  `get_by_id()`. `reset()` → `storage._replace_records([])` (wipes the
  table — see the safety note below).
- **Safety-critical, non-negotiable part of this proposal:** every one of
  the 6 test files that currently call `authority_store.reset()` directly on
  the module-level singleton
  (`test_agent_governance.py`, `test_llm_agent.py`, `test_preview.py`,
  `test_adversarial.py`, `test_dependency_guard.py`, `test_git_domain.py`)
  must be updated to monkeypatch `app.agent.authority.authority_store` to a
  **fresh, isolated `AuthorityStore` backed by `AuthorityGrantStorage(file_path=None)`**
  (pure in-memory, DurableStore's own test-isolation mode) for the duration
  of each test — the same isolation discipline every other evidence store
  already gets (`_setup_isolation` across `test_remediation.py` /
  `test_continuation.py`). Without this, `reset()` on a persistent singleton
  would `DELETE` every row from the **real, live**
  `data/governance_evidence.db` on every test run in this checkout (it is
  the same file the live systemd service reads). This is caught by design,
  not by luck: no test in this change touches the real DB path.

### 3b. Agent Integration Guide — new `docs/operations/AGENT_API.md`

The workflow guide the raw OpenAPI schema doesn't provide:

- The full lifecycle with a worked example: `POST /agent/authority/grant` →
  `POST /agent/act/preview` (optional, no side effects) → `POST /agent/act`
  → held / executed → `POST /homelab/approve` → the evidence receipt.
- **The evidence receipt contract** — which fields of `AgentOutcome.as_dict()`
  are stable/guaranteed (`decision`, `agent_id`, `target`, `mechanism`,
  `approval_id`, `execution_id`, `verification_status`) vs. informational
  (`detail`), and the full `decision` vocabulary
  (`disabled | no_authority | deny | rejected | hold | escalated_hold |
  allow | error`) with what each one means and what it guarantees never
  happened.
- Authentication (`Authorization: Bearer <token>` / `X-API-Key`, how grants
  map to `granted_by`), rate limits (`rate_limit_agent`), and the explicit
  non-guarantees already recorded in `docs/RMT_GUARANTEES.md` /
  `docs/RMT_THREAT_MODEL.md` (single-use grants don't survive being reused;
  a hold expires at `APPROVAL_HOLD_TTL_SECONDS`; approval is never
  automatic).
- Two worked examples: the homelab domain (`operational_context: "homelab"`,
  the default) and the git-tag domain (`operational_context: "git"`), so an
  integrator sees the contract is genuinely domain-agnostic, not
  homelab-shaped with git bolted on.

## 4. Explicitly OUT of scope

- No multi-agent authority model beyond what exists (per-agent-class policy,
  bulk/pattern grants) — a bigger, more speculative design question that
  needs a real second caller before it's worth committing to a shape.
- No API versioning scheme (`/v1/agent/...`) — nothing has shipped to an
  external caller yet to need a compatibility boundary against.
- No UI/console. Phase D territory, still gated on "audience beyond owner."
- No change to `AGENT_ENABLED` / `AGENT_LLM_ENABLED` semantics, no lowering
  of `AGENT_DEFAULT_REQUIRES_APPROVAL`, no new mutation path.

## 5. Boundary

- No `app/core/**` change — `DurableStore` and `EVIDENCE_DB_PATH` reused
  exactly as six existing stores already use them; a new table via
  `CREATE TABLE IF NOT EXISTS`, no existing table touched.
- No test in this change ever opens the real `data/governance_evidence.db`.
- `docs/operations/AGENT_API.md` documents the existing contract; it does
  not change any route's behavior.

## 6. Done when

- `AuthorityStore` grants survive a process restart (real SQLite file,
  verified with a live check: grant → restart the process → grant still
  resolvable).
- Every existing agent test passes with the new isolated-storage pattern;
  none touches the real evidence DB.
- `docs/operations/AGENT_API.md` exists, is linked from `README.md`, and an
  external reader could complete the full lifecycle from it without reading
  source.
- Full backend suite green; no `app/core/**` diff.

## 7. Tests

- `app/agent/testing/test_authority_persistence.py` — grant survives a
  fresh `AuthorityStore` instance pointed at the same file (simulates
  restart); `reset()` on an isolated instance clears only that instance;
  `consume()` persists (`consumed=True` readable from a second instance
  pointed at the same file); expiry/scope-mismatch checks unchanged
  (regression).
- All 6 existing agent test files: swap direct `authority_store.reset()` for
  a `monkeypatch`-isolated fresh store, verify the full existing suite still
  passes unchanged in behavior (pure isolation-mechanism change, not a
  logic change).

## 8. Validation plan

- New tests pass; full suite (currently 515) grows and stays green.
- `ruff check .` clean; `import app.main` clean.
- A live check (not a fault-injection drill — this is a persistence proof,
  not an execution one): grant authority on the live systemd instance,
  confirm it's readable via a fresh process, without ever restarting the
  actual live service (verified via a throwaway script against the real
  file, read-only from the live service's perspective).
