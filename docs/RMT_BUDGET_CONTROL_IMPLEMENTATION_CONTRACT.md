# RMT Budget Control — Above-Core Implementation Contract

**Version:** 0.2, 2026-09-16.
**Status:** IMPLEMENTED, VALIDATED, COMMITTED, AND DEPLOYED — backend and frontend
production paths verified.
**Baseline:** `b0e732c`, tag `rmt-core-domain-compatibility-final-freeze`.
**Classification:** above-Core product/domain implementation.

Companions: [product proposal](RMT_BUDGET_CONTROL_PROPOSAL.md),
[compatibility proposal](RMT_BUDGET_CONTROL_CORE_COMPATIBILITY_PROPOSAL.md), and
[completed Core compatibility contract](RMT_BUDGET_CONTROL_COMPATIBILITY_IMPLEMENTATION_CONTRACT.md).
Authority: [Master Definition](RMT_MASTER_DEFINITION.md),
[Core Target State](RMT_CORE_TARGET_STATE.md), [frozen-Core rules](RMT_FROZEN_CORE_DEBT.md),
[MCR Supervisory Contract](MCR_SUPERVISORY_CONTRACT.md), and [AGENTS.md](../AGENTS.md).

## 1. Objective and admission rule

Deliver a small-organization Budget Control product that governs spending before
it occurs. The acceptance scenario is: from 2,000 available, an authorized owner
approves an exact request for 1,500; one atomic commitment is recorded and 500
remains available.

The product must comply with RMT unchanged. It may not modify `app/core/**`, reopen
Core, create C08, bypass the governed boundary, or transfer policy, risk, approval,
or authorization into an adapter. If this contract cannot be implemented against
the frozen interfaces, Budget Control is rejected as an RMT product rather than
used to justify another Core amendment.

Preparing or approving this contract does not authorize deployment, migration of
production data, service restart, commit, push, bank/payment integration, or work
outside this scope.

## 2. Version-one scope

- One organization and one configured ISO-4217 currency.
- Period budgets owned by a department or project.
- Bootstrap administrator, budget-owner, and requester assignments.
- Versioned purchase requests with purpose and supporting reference strings.
- Long-lived domain approval/rejection before fresh Core governance.
- Atomic commitment, one final settlement, and cancellation of an unspent
  commitment.
- Immutable allocation, adjustment, commitment, settlement, cancellation, and
  corrective ledger entries.
- Authenticated API and four UI views: Budgets, Purchase Requests, Approvals, and
  Spending History.
- Correlated Core and financial evidence with explicit unresolved outcomes.

Excluded: payment execution, bank connections, multi-currency conversion,
recurrence, partial settlement/delivery, multiple invoices, tax/accounting,
procurement integrations, AI decisions, deletion of financial history, and
general-purpose role administration.

## 3. Responsibility boundary

Budget Control owns financial models, exact calculations, business permissions,
long-lived request/approval workflow, policy and risk evaluators, adapter,
financial observer, ledger, recovery reconciliation, APIs, and UI.

Core remains the sole authority for assessment validation, authorization,
execution admission, instruction/adapter binding, execution evidence, and the
generic governed lifecycle. Budget evaluators assess and may allow, deny, or
require approval; they cannot approve, authorize, select another adapter, or
execute. The Budget adapter receives only a Core-authorized request and performs
the bound atomic transaction; it cannot waive insufficient funds or role rules.

## 4. Domain model and invariants

Money is stored as signed integer minor units plus the organization currency;
binary floating point is forbidden. IDs are opaque UUIDs. Timestamps are UTC.

Required records:

- organization configuration and bootstrap state;
- principal role assignments scoped to organization/budget;
- budget and immutable allocation/adjustment history;
- purchase request plus immutable numbered versions;
- domain approval decision bound to request version and exact instruction digest;
- append-only ledger entry;
- idempotency receipt keyed by instruction digest;
- execution correlation and financial verification result.

Invariants:

- `available = allocations + adjustments - settled expenses - open commitments`;
- submission reserves nothing; only an applied commitment reserves funds;
- settlement replaces its commitment economically, never double-counts it;
- settlement cannot exceed the approved amount; a higher amount requires a new
  request version and approval;
- cancellation releases only an open, unsettled commitment;
- accepted request versions and ledger entries are immutable;
- correction uses linked compensating entries, never update/delete;
- a requester cannot approve their own request;
- one instruction digest can produce at most one financial mutation;
- concurrent mutations cannot make available funds negative.

## 5. State machines

Purchase request: `draft → submitted → approved | rejected`; an approved request
may become `committed → settled | cancelled`. Editing a submitted/decided version
creates a new draft version; it never mutates reviewed content.

Financial execution outcome is independently classified as:
`blocked_before_execution`, `adapter_failed_no_effect`, `applied_unverified`,
`verified_success`, `verification_mismatch`, or `outcome_unknown`. UI and APIs must
not collapse these states into “success.”

Domain approvals are durable and may outlive Core's short hold. After approval,
the service reloads current request, role, budget, policy, and balance evidence and
submits a fresh action through Core. It must not revive or extend an expired Core
hold. Changed evidence or version invalidates the domain decision and requires new
review.

## 6. Persistence and transaction contract

Use a dedicated SQLite database, configured outside Core data stores, with foreign
keys enabled and schema migrations owned by `app/budget/`. All schema changes are
forward, versioned, and fail closed on unknown/newer schema versions.

Each financial mutation uses one database transaction (`BEGIN IMMEDIATE` or an
equivalent proven serialization boundary):

1. validate instruction digest and idempotency key;
2. reload request version, approval, role assignment, budget period, currency,
   and current balance inside the transaction;
3. reject stale, unauthorized, closed-period, wrong-currency, invalid-transition,
   or insufficient-funds work;
4. append ledger entry and idempotency/execution receipt atomically;
5. commit both or neither.

A repeated identical instruction returns its existing receipt without another
ledger entry. A reused key/digest with different content is rejected. Database
busy/lock, I/O, constraint, or commit uncertainty is not reported as success.

## 7. Governed integration

Register trusted domain `rmt.budget.v1`, its fixed evaluator identities/versions,
and adapter `budget-ledger` during application startup from above-Core bootstrap
code. Registration accepts only the operations required by this slice. External
callers cannot select evaluators or register domains/adapters.

Every monetary mutation constructs a server-owned `ActionRequest` whose canonical
parameters include organization, budget, request/version, currency, amount,
mutation type, related ledger/commitment identity, actor, domain approval identity,
and idempotency key. Expected outcome identifies the exact durable financial state.
The action uses the frozen instruction digest and adapter binding.

Budget policy evaluates role, separation of duties, request/version state, period,
currency, limits, and required approval. Budget risk records impact, uncertainty,
current balance evidence, and recovery semantics. Unknown, stale, missing, or
conflicting evidence denies or holds; it is never coerced to allowed.

All public and internal mutation routes call one Budget application service, which
then enters `execute_governed_action()`. No API, UI handler, job, recovery routine,
or direct database helper may provide an equivalent mutation path.

## 8. Verification and recovery

After adapter return, an independent Budget observer reads the committed receipt
and ledger rows by instruction/execution identity, recomputes the balance, and
compares currency, amount, linkages, transition, and expected available balance.
Adapter success alone is `applied_unverified` until this observation agrees.

On timeout, crash, or ambiguous response, reconciliation first queries the durable
receipt by digest. If found, it verifies the existing effect and never reapplies
it. If absent and commit absence is established, a fresh authorized retry may be
submitted under normal governance. If neither applied nor absent can be proven,
the outcome remains unknown and automation stops. Recovery never manufactures
approval, authorization, or historical evidence.

## 9. Authentication and permissions

Existing operator authentication identifies the caller; Budget authorization is
separate domain responsibility. Server-side permission checks apply consistently
to UI, product APIs, generic entrypoints, and recovery operations. Bootstrap is an
explicit one-time configured principal action, audited and disabled after success.

- requester: create/submit own requests and view permitted scope;
- budget owner: decide others' requests and view owned budgets/history;
- bootstrap administrator: initialize organization and role assignments only.

No self-approval, client-asserted role, anonymous mutation, or token-to-role
fallback is allowed. Role changes are out of this first slice after bootstrap.

## 10. API and UI surface

Expected above-Core backend location: `app/budget/` with focused modules for
models, storage/migrations, repository, permissions, workflow, evaluators, adapter,
observer/recovery, service, API, schemas, bootstrap, and tests. Startup and router
wiring may touch `app/main.py`; no `app/core/**` file may change.

Minimum API supports authenticated budget summaries/history, request create/
submit/detail, approval queue and approve/reject, commitment application,
settlement, and cancellation. Mutation responses expose domain state plus governed
status and correlated action/approval/authorization/execution/verification IDs.
HTTP conflict is used for stale version/idempotency conflict; validation,
authentication, authorization, insufficient funds, and unknown outcome remain
distinguishable.

The existing frontend may gain a Budget area containing the four specified views.
UI is a client of the API, not a permission or governance boundary. Destructive or
financial actions require confirmation and render the exact budget, amount,
currency, request version, and resulting state.

## 11. Concrete change boundary

Allowed implementation surfaces:

- new `backend/app/budget/**` domain code and tests;
- minimal router/startup registration in `backend/app/main.py`;
- dedicated Budget migration/configuration and operational documentation;
- additive frontend Budget routes/components/client/types and tests;
- requirements changes only if separately justified by a demonstrated need.

Forbidden: any `backend/app/core/**` edit; modification of existing Core evidence;
reuse of Core holds as durable business approvals; direct ledger writes outside
the adapter transaction; silent historical rewrites; unrelated refactoring;
payment execution; or deployment/configuration mutation.

## 12. Implementation sequence

1. Domain schema, migrations, exact-money helpers, repository, and invariant tests.
2. Permissions, versioned request workflow, bootstrap, and API contract tests.
3. Budget evaluators, observer, adapter, trusted registration, and contract tests.
4. Governed commitment end to end, including concurrency, retry, and recovery.
5. Governed settlement and cancellation with balance verification.
6. Four-view UI and authenticated browser workflow.
7. Full negative-path, alternate-route, migration, restart, and regression gate.

Each step must leave no reachable partially governed monetary mutation.

## 13. Required validation

- exact minor-unit calculations, period/currency and state-transition matrices;
- allocation/adjustment/commitment/settlement/cancellation balance properties;
- self-approval, missing role, forged identity, stale version, changed instruction,
  expired decision, over-budget, unsupported operation, and unknown evidence block
  before adapter invocation;
- two concurrent 1,500 commitments against 2,000 produce exactly one commitment;
- repeated/reordered requests cannot duplicate effects or misuse idempotency keys;
- adapter failure before commit leaves no ledger/receipt; ambiguous-after-commit
  recovery finds and verifies exactly one effect;
- observer mismatch/unavailable/error remains visibly unverified/unknown;
- every reachable mutation route converges on the same governed service;
- one complete evidence chain correlates domain request/decision/ledger/receipt to
  Core assessment/approval/authorization/execution/verification;
- unauthorized read/write API matrix and authenticated attribution;
- clean-database migration, restart persistence, backup/restore drill;
- UI happy path plus rejected, conflict, and unresolved states;
- existing default-domain and full backend suites remain green with no reduced
  assertions; frontend build/tests pass; diff contains no `app/core/**` changes.

## 14. Definition of Done

Completion requires implementation + integration + enforcement + validation +
evidence. Specifically:

- the 2,000 → commit 1,500 → 500 scenario passes through the complete governed
  lifecycle and independent financial verification;
- concurrent, replayed, unauthorized, changed, rejected, stale, failed, and
  unknown paths preserve invariants and never produce an ungoverned mutation;
- settlement and cancellation yield correct durable balances and evidence;
- restart/recovery never duplicates an effect or invents certainty;
- all APIs and UI states are permission-enforced and accurately classified;
- migrations and restore are demonstrated from a clean isolated environment;
- all targeted, integration, frontend, and repository regression gates pass;
- operational and evidence records are updated with exact commands/results; and
- no excluded capability or Core change is present.

Failure of any item rejects the implementation. Code existence, a passing unit
test, adapter success, or UI completion alone is insufficient.

## 15. Approval boundary

**Approval record, 2026-09-15:** the owner explicitly approved this contract and
authorized implementation within its stated surfaces and behavior, then directed
that implementation be left to the next session. No implementation was retained
in this approval session.

Owner approval of this contract authorized only the implementation surfaces
and behavior above. It would not authorize Core changes, scope expansion,
deployment, production migration, restart, commit, push, or payment execution.
Any discovered need to alter Core, weaken an invariant, add a dependency, or
expand product scope requires stopping and reporting; a Core dependency rejects
Budget Control under the final MCR admission rule.

## 16. Implementation checkpoint — 2026-09-16

The approved above-Core implementation is present under `backend/app/budget/**`
with minimal startup/router wiring in `backend/app/main.py`. It provides:

- integer-minor-unit models and a dedicated versioned SQLite schema;
- scoped bootstrap-admin, budget-owner, and requester enforcement;
- immutable request versions and durable exact-version decisions;
- append-only allocation, adjustment, correction, commitment, settlement, and
  cancellation entries;
- serialized transaction revalidation, digest-bound receipts, and idempotent
  replay/conflict handling;
- registered Budget policy/risk evaluators and the `budget-ledger` adapter;
- independent financial observation, explicit unresolved states, and recovery;
- authenticated APIs and the four specified frontend views; and
- operational guidance in `RMT_BUDGET_CONTROL_OPERATIONS.md`.

Validation evidence:

- Budget tests: **19 passed**;
- complete backend suite: **593 passed, 3 skipped** (**596 collected**), up from
  the accepted pre-Budget baseline of 574 passed, 3 skipped;
- Python compilation: pass;
- focused Ruff errors-only check: pass;
- frontend TypeScript/Vite production build: pass;
- frontend Oxlint: pass;
- isolated Chromium/Playwright acceptance: **1 passed**;
- `npm audit --omit=dev`: **0 production vulnerabilities**; full development
  audit reports two fixable transitive Vite-toolchain advisories (one moderate,
  one high), neither introduced by Playwright nor present in production deps;
- `git diff --check`: pass;
- inspected diff: no `backend/app/core/**` change and no new dependency.

The automated suite covers the 2,000 → 1,500 → 500 lifecycle, exact evidence
correlation, concurrent overspend, replay/conflict, permissions, stale evidence,
version invalidation, settlement, cancellation, append-only correction, failure
before commit, ambiguous-after-commit recovery, mismatch/unknown observation,
clean/newer migration handling, restart initialization, and isolated backup/restore.

The added test-only Playwright harness starts isolated backend/frontend processes
on dedicated ports with temporary Budget, governance-evidence, and observability
databases. Real Chromium completed the four-view workflow for the happy 2,000 →
1,500 → 500 path, rejection, two-approved stale conflict, unauthenticated access,
role denial, spending history, and unresolved-state rendering. The unresolved UI
case uses a browser-controlled ambiguous HTTP response; backend ambiguous recovery
is independently covered by the real adapter/repository tests.

All §14 evidence gates are satisfied. The implementation was committed as
`df0e039` and pushed to `origin/master` on 2026-09-16. The documented backend
deployment path was then applied to `rmt-control-center.service`. The restarted
service is active on loopback, TLS `/health` returns 200, unauthenticated Budget
access returns 401, and all 15 Budget paths are present in the live OpenAPI
document. The production Budget database initialized at schema version 1 with
zero organizations and zero budgets; no bootstrap or financial mutation occurred.

The live unit sets `RMT_BUDGET_BOOTSTRAP_PRINCIPAL=alice`. Commit `4bb73a2` adds
the production frontend contract: HTTPS clients use same-origin API calls, and
Caddy serves an immutable compiled release while proxying explicit API routes to
the loopback backend. Release `4bb73a2eb7c1` is selected by the production
`current` symlink. Live TLS checks returned 200 for HTML, its hashed JavaScript
asset, `/config`, and `/health`; unauthenticated Budget access remained 401.
Chromium loaded the Budget UI and issued all Budget GETs against the same HTTPS
origin with no request failures. The database remains unbootstrapped and payment
execution remains outside scope.
