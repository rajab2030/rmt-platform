# RMT-CAP-11 — Evidence Export / Attestation Bundles (roadmap P-C) — Proposal

**Status:** **APPROVED 2026-09-20 (owner).** Approved as a proposal under the
platform's standing working method (an approved per-capability proposal is the
precondition before any code is written; see `HANDOFF.md` §"Next-capability
shortlist review" and §"RMT-CAP-11 proposal drafted" for the selection record).
Implementation proceeds against the scope below; deployment, production
migration, restart, commit-to-push, and any live/isolated exercise remain
subject to the same separate-authorization discipline every prior capability
(CAP-04 .. CAP-10, Budget Control) followed.

**Classification:** Above-Core / product surface (roadmap `P-C`,
`docs/RMT_ABOVE_CORE_ROADMAP.md` §"P-C"). **No C08. No frozen Core change. No
reopening of C01–C07.** Confined to `app/ops/**`, one read-only route in
`app/main.py`, and a new stdlib-only verifier script. Does not touch the
governed mutation path.

---

## 1. Objective

Every governed action already has a complete, durable `Govern → Verify`
evidence chain (authorization → approval record → hold → audit → trace →
verification), reachable live over authenticated HTTP via `GET /ops/evidence`
(RMT-CAP-09 / P-B). What doesn't exist is a way to **take that evidence out of
the platform** as a self-contained artifact: something an operator can hand to
an external auditor, attach to an incident writeup, or archive for compliance,
that verifies its own integrity **offline**, without trusting the live service
or re-querying it.

This capability produces a **signed, portable evidence bundle** per governed
action, plus a small offline verification tool — the roadmap's own "P-C" once
CAP-09 gave the platform something worth exporting.

**Why now:** the one dependency the roadmap set for P-C (T0-1, the SQLite
durable-evidence substrate) closed 2026-09-09, and CAP-09 already built and
proved the exact correlation logic this reuses. The other roadmap candidates
needing no external infrastructure were narrowed to P-A and P-C
(`HANDOFF.md` §"Next-capability shortlist review"); P-C was chosen because it
sits entirely off the governed mutation path (pure read derivation, no live
production decision depends on it) and produces something externally
demonstrable, unlike P-A's internal config-tuning convenience.

## 2. What already exists (reused, not rebuilt)

| Piece | Location / route | Role here |
|---|---|---|
| Evidence-chain correlation | `app/ops/evidence_chain.py::evidence_chain()` | Already assembles the full `authorizations / approvals / holds / audit / traces / verifications / provenance` shape for one `action_id`/`approval_id`/`execution_id`, read-only, fail-open. This is the payload the bundle wraps — **not reimplemented**. |
| Existing route | `GET /ops/evidence` (operator-auth, `app/main.py`) | Proves the identical correlation logic already serves real requests; the new route is a sibling, not a fork. |
| Operator-token auth | `app/ops/auth.py`, `require_operator` | The new export route reuses the same auth dependency — no new identity model. |
| Secret-custody discipline | `RMT_OPERATOR_TOKENS` via systemd `LoadCredential=` (S1/S2-lite, hardened after the T0-5 credential-exposure finding) | The precedent the signing key must follow — see §3b. |
| Stdlib-only recovery tooling | `backend/scripts/rmt_evidence_verify.py` (E5) | The precedent for the offline verifier: stdlib-only, no new dependency, run outside the running service. |
| `DurableStore` (SQLite, T0-1) | `data/governance_evidence.db` | The source of truth the bundle is a signed snapshot *of* — never modified. |

## 3. Design (in scope)

### 3a. Backend — one additive read-only export route

A new, read-only, operator-authenticated route (e.g. `GET
/ops/evidence/export?action_id=...`) that:

1. Calls the existing `evidence_chain()` unchanged to assemble the correlated
   record set.
2. Wraps it in a small envelope: the chain payload, a bundle format version, a
   generation timestamp, the resolved identifiers, and a canonical
   (deterministic key order) JSON serialization for signing.
3. Computes an HMAC-SHA256 signature over the canonical payload using an
   operator-provisioned signing secret (stdlib `hmac`/`hashlib` — **no new
   dependency**; the codebase has no asymmetric-crypto library today and
   pulling one in for a single symmetric-signing use case is out of proportion
   to the capability's S–M size).
4. Returns the envelope + signature as a single downloadable JSON document.

This mirrors the read-only, fail-open discipline `evidence_chain()` already
uses: an assembly failure returns the existing empty-chain shape (still
signed, so "no evidence found" is itself a verifiable, non-repudiable
statement), never a 500.

### 3b. Signing key custody

The HMAC signing secret is a new operator-provisioned value, following the
**exact custody pattern already hardened for `RMT_OPERATOR_TOKENS`** after the
T0-5 finding: a systemd `LoadCredential=` secret file, never an environment
variable dump, never logged, never stored in evidence. A missing signing
secret disables the export route (503), the same fail-closed-on-missing-secret
behavior startup already enforces for operator tokens — it does not fall back
to an unsigned bundle. Key rotation follows the same
`DEPLOY.md`/`SECRETS.md` discipline already documented for operator tokens
(§ "Operator-token custody gap — CLOSED", `HANDOFF.md` 2026-09-13).

### 3c. Offline verification tool

`backend/scripts/rmt-attestation-verify.py` — stdlib-only (no network, no
running-service dependency, matching `rmt_evidence_verify.py`'s precedent):
takes a bundle file and the signing secret (or a public verification value, if
the design lands on a scheme where the verifier doesn't need the same secret
the signer used — evaluated during implementation), recomputes the canonical
serialization and HMAC, and reports **VALID** / **INVALID** / **malformed**.
Exit code reflects the result for scripting/CI use in an external auditor's
own tooling.

## 4. Explicitly OUT of scope

- **No change to stored evidence.** The bundle is a read-only derivation; nothing
  in `data/governance_evidence.db` is touched, reshaped, or deleted.
- **No time-range / bulk export in the first slice.** Per-action bundles only;
  a "per time range" bundle (mentioned as an option in the roadmap line) is a
  possible follow-up, not committed here — it multiplies the payload size and
  the canonicalization surface for no proven need yet.
- **No asymmetric signing / PKI.** HMAC with an operator-custodied secret is
  the entire trust model for this slice; a public-key scheme (so a bundle
  verifies without sharing the platform's own secret) is a real limitation an
  external auditor may eventually need, but it is a new dependency and a
  bigger key-management story — deferred, not silently dropped (recorded here
  as a known boundary).
- **No RBAC / multi-operator identity** (P-D) and **no policy editor** (P-A) —
  separate candidates.
- **No `app/core/**` change, no change to any governed-lifecycle behavior, no
  change to `/ops/evidence`'s existing response shape.**

## 5. Boundary

- No `app/core/**` change. The frozen Core and the governed mutation path are
  untouched.
- The export route is read-only and fail-open, reusing `evidence_chain()`
  unchanged.
- The signing secret follows the hardened operator-token custody pattern
  (`LoadCredential=`, fail-closed if absent, never logged/stored in evidence).
- The verifier is a standalone, stdlib-only, offline tool — it does not call
  the live service and does not require Docker/git/any adapter.

## 6. Done when (Definition of Done)

**Implementation + Integration + Enforcement + Validation + Evidence**:

- An operator can request a bundle for a real `action_id` from the live
  console/API and receive a signed JSON document containing the full
  `Govern → Verify` chain.
- `rmt-attestation-verify.py` reports **VALID** for a genuine bundle and
  **INVALID** for a bundle with any single byte of its evidence tampered,
  entirely offline (no network call, no running service).
- The export route requires operator auth, is disabled (503) when no signing
  secret is provisioned, and never writes to any evidence store.
- Full backend suite green; no `app/core/**` diff; `git diff --check` clean.

## 7. Tests

- New route: resolves and signs a real chain from isolated test stores;
  unknown id → signed empty-chain bundle (still 200, not 500); no signing
  secret configured → 503; operator-auth required (401 without a token).
- Verifier: valid bundle → exit 0 / VALID; single-field tamper (e.g. flip one
  character in a nested record) → exit 1 / INVALID; malformed JSON → a
  distinct non-crash error, not a stack trace.
- Regression: `GET /ops/evidence` (CAP-09) behavior and response shape
  unchanged.
- No test in this change ever writes to the real `data/governance_evidence.db`
  or touches the real signing secret.

## 8. Validation plan

- Full backend suite green, growing by the new route + verifier tests.
- `compileall` / import smoke / focused Ruff clean.
- Owner-authorized live exercise on an **isolated** instance (same discipline
  CAP-04/05/06/09 used): export a bundle for a real recorded action, verify it
  offline with the tool, then tamper one field in a copy of the bundle and
  confirm the verifier flags it — live `:8000` untouched throughout.

---

*Per the standing working method: this becomes approved work only when the
owner gives explicit go-ahead on this proposal. The proposal itself is
docs-only and makes no code change.*

🤖 Generated with [Claude Code](https://claude.com/claude-code)
