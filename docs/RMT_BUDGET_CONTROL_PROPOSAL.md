# RMT Budget Control — Product Proposal

**Version:** Draft 0.1, 2026-09-14.
**Status:** DRAFT — pending owner approval. No implementation authorized.
**Classification:** above-Core business application.

The owner selected Budget Control for proposal development during the session,
then authorized saving the drafts and continuation status. That authorization
does not approve implementation or a Core freeze exception.

## 1. Authority and purpose

Governed by [RMT_MASTER_DEFINITION.md](RMT_MASTER_DEFINITION.md),
[RMT_CORE_TARGET_STATE.md](RMT_CORE_TARGET_STATE.md), and [AGENTS.md](../AGENTS.md).
Budget Control is explicitly an above-Core domain. RMT remains the reusable
control platform; Docker, homelab operations, and this product do not define it.

Help a small organization control spending before it happens: request, approve,
commit, and track organizational spending. Answer what is available, what is
requested or committed, who may approve, and why each change was permitted.

## 2. First-version scope

- One organization and one configured currency.
- Department or project budgets with a defined period; no automatic rollover.
- Budget-owner and requester roles; a requester cannot approve their own purchase.
- Budget owner establishes limits and approves requests. The bootstrap and
  role-administration procedure must be defined in the implementation contract;
  the no-self-approval rule concerns purchase requests.
- Purchase requests with amount, purpose, requester, and supporting references.
- Governed commitments, one final expense per request, and cancellation of an
  unspent commitment.
- Four views: Budgets, Purchase Requests, Approvals, Spending History.

Actual payments remain manual and outside the application. Recording an expense
does not independently prove a bank transfer. No bank connections, payment
execution, credit models, multi-currency conversion, recurring purchases,
partial deliveries, or multiple invoices in this slice. AI/n8n is not required.

## 3. Example and financial rules

Budget limit 10,000; expenses 6,000; outstanding commitments 2,000; available 2,000.
A request for 1,500, once approved and successfully committed, leaves 500.
A request for 3,000 is blocked. A budget increase is a separate governed change,
not an exception silently granted by purchase approval.

- Available = limit - recorded expenses - outstanding commitments.
- Submission reserves nothing; a successfully applied commitment reserves money.
- Settlement replaces the corresponding commitment rather than counting both.
- A lower actual expense releases the remainder; a higher amount needs a revised
  request and fresh approval before being treated as approved spending.
- Cancellation releases only the unspent commitment.
- Submitted/approved versions are immutable; changes require a new reviewed version.
- Concurrent approvals cannot reserve the same funds. Repeated clicks or retries
  cannot create duplicate financial effects.
- Use exact monetary representation, never binary floating-point arithmetic.
- Preserve allocation, adjustment, commitment, settlement, cancellation, and
  correction history. Correct financial history with linked entries, not deletion.

## 4. Responsibility and technical direction

Budget Control owns financial concepts, spending policy, roles, durable business
requests, ledger transactions, UI, and financial observations. Core retains
governance enforcement, approval provenance, authorization, and the single
execution boundary. Adapters execute; observers read and verify.

Proposed records: budget/allocation history, versioned purchase request,
immutable financial instruction, assessment references, ledger entries, and
execution receipts. All monetary mutations, including allocation, adjustment,
settlement, and cancellation, need a defined governed path.

The candidate instruction freezes budget, currency, amount, purpose, requester,
request version, and applicable policy references. Authorization targets that
immutable instruction. Parameter substitution, adapter redirection, and replay
protection remain validation requirements, not established guarantees.

Long-lived requests outlast the five-minute Core hold. On a human decision,
reload current evidence, check permissions/version, reassess, and submit through
fresh Core governance. Changed review material requires fresh human review.
The related [B2 roadmap proposal](RMT_IMPROVEMENT_ROADMAP.md#b2--durable-approval-request--minimal-approval-view)
is a precedent, not an implemented facility.

An atomic domain transaction checks the instruction identity and budget version,
appends the financial entry and receipt together, or changes nothing. A stale
write condition fails; an adapter cannot approve overspending. Ledger storage
requires transactional guarantees not supplied by individual DurableStore saves.

Core evidence and financial writes are not currently one transaction. Recovery
must recognize an applied instruction from its durable receipt, avoid repeating
the mutation, and expose incomplete governance/verification evidence. It must
never reconstruct missing authorization as though it existed before execution.

The observer must read the exact entry, amount, currency, linkage, and financial
result independently. Adapter success alone is insufficient. UI outcomes must
distinguish approval, applied-but-unverified, verified success, blocked/rejected,
execution failure, and unresolved outcome.

Budget permissions must cover every reachable approval/execution route, including
generic routes, rather than only the product UI. Existing named operator tokens
and optional agent separation checks do not establish budget-specific roles.

## 5. Compatibility gate

Read-only inspection at HEAD `834ca3d` found:

1. Fixed action vocabulary and container-oriented simulation/risk assumptions.
2. Authorization does not explicitly bind the parameters dictionary; the
   immutable-instruction approach needs proof.
3. Core manual holds expire after 300 seconds.
4. Operator authentication lacks budget-specific authorization rules.
5. Existing persistence does not establish a cross-record financial transaction.

See [Budget Control–Core Compatibility Proposal](RMT_BUDGET_CONTROL_CORE_COMPATIBILITY_PROPOSAL.md).
The proposed generic assessment extension requires an explicit owner decision
against the recorded freeze restriction. No Core change is authorized.

## 6. Implementation order after approval and compatibility resolution

1. Domain records, exact calculations, permissions, request workflow and views.
2. Governed commitments, approval, atomic reservation, duplicate protection,
   independent verification.
3. Expense settlement and cancellation through defined governed paths.
4. Browser workflow, concurrency, failure, and recovery validation.

Exact files, contracts, migrations, bootstrap behavior, and tests must be specified
in an approved implementation contract before code changes.

## 7. Acceptance

- Submit and decide a purchase through the UI with authenticated attribution.
- Unauthorized, rejected, expired, or over-budget requests create no commitment.
- Changed amount/budget/version invalidates old approval.
- Concurrent requests cannot overspend; retries cannot double-count.
- Settlement and cancellation yield the correct available balance.
- Interrupted execution/restart has a recoverable, accurately classified outcome.
- Verification failure/unavailability is visible and never reported as success.
- Correlate each financial mutation to request, assessment, approval,
  authorization, execution, and verification.
- Preserve existing RMT behavior with targeted and integration regression evidence.

**Validation status:** conceptual design and static repository review only; no
Budget Control code, tests, database, deployment, or live exercise exists from
this session.
