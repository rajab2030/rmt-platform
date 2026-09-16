# RMT Budget Control — Operations

**Status:** operational guidance and verified deployment record, 2026-09-16.
**Scope:** the above-Core Budget Control product defined by
`RMT_BUDGET_CONTROL_IMPLEMENTATION_CONTRACT.md`.

Release `df0e039` is pushed to `origin/master` and deployed through the documented
`rmt-control-center.service` backend path. The live database is initialized at
schema version 1 but remains unbootstrapped. No organization, budget, ledger
entry, payment execution, or other financial mutation was created by deployment.
Frontend deployment commit `4bb73a2` is also pushed and live through Caddy. The
immutable release `4bb73a2eb7c1` is selected under
`/var/lib/rmt-control-center/frontend/current`; HTTPS UI, static asset, same-origin
API proxy, authentication boundary, and browser request routing are verified.

## Configuration

Budget Control uses the existing RMT operator authentication boundary and adds
domain roles stored in its own database.

- `RMT_BUDGET_DB`: dedicated SQLite path. Default:
  `projects/homelab-control-center/backend/data/budget.db`.
- `RMT_BUDGET_BOOTSTRAP_PRINCIPAL`: required authenticated principal for the
  one-time bootstrap operation. There is no permissive production default.
- `RMT_AUTH_ENABLED` and `RMT_OPERATOR_TOKENS`: existing operator authentication.

Startup creates or forward-migrates only the configured Budget database. A schema
newer than the application supports aborts startup. Core evidence and observability
databases are not reused.

## One-time bootstrap

Bootstrap is an authenticated, governed operation. It creates one organization,
one period budget, the initial allocation, and fixed bootstrap-admin, budget-owner,
and requester assignments. Owner and requester must differ. Bootstrap is disabled
by durable state after the first success.

Example request (replace host, token, principals, dates, and amounts):

```bash
curl -X POST http://HOST:8000/budget/bootstrap \
  -H 'Authorization: Bearer TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{
    "organization_name":"Example Org",
    "budget_name":"Operations",
    "owner_type":"department",
    "owner_name":"Operations",
    "period_start":"2026-01-01",
    "period_end":"2026-12-31",
    "currency":"USD",
    "allocation_minor":200000,
    "owner_principal":"budget-owner",
    "requester_principal":"requester",
    "idempotency_key":"bootstrap-example-org-v1"
  }'
```

Amounts are integer minor units. Floating-point money is rejected.

## Governed workflow

1. A requester creates and submits a purchase request.
2. A budget owner other than the requester approves or rejects its exact version.
3. Approval stores the immutable Core instruction and current balance evidence.
4. The deciding owner applies the commitment through the governed lifecycle.
5. The serialized adapter transaction rechecks role, version, decision, period,
   currency, balance, digest, and idempotency before appending the ledger entry.
6. The independent Budget observer reads the receipt and ledger, recomputes the
   balance at the receipt timestamp, and records the financial verification.
7. An owner may make one final settlement or cancel an open commitment.

All financial responses expose `financial_status`. Treat only
`verified_success` as verified completion. `applied_unverified`,
`verification_mismatch`, and `outcome_unknown` require investigation and must not
be automatically replayed.

## Recovery

For an ambiguous response, query:

```text
POST /budget/reconcile/{instruction_digest}
```

Reconciliation reads the durable receipt. If present, it verifies the existing
effect and never reapplies it. If absence is established it reports
`adapter_failed_no_effect`. If evidence cannot be read it remains
`outcome_unknown`; automation stops.

Changing a submitted or decided request creates a new immutable draft version.
The former decision cannot be applied. If balance evidence changes after domain
approval, the commitment is blocked and requires a fresh version and review.

## Backup and restore

Use SQLite's online backup API or a deployment-approved equivalent against the
configured `RMT_BUDGET_DB`. Do not copy a database during an uncontrolled write.
After restore into an isolated path:

1. configure `RMT_BUDGET_DB` to the restored copy;
2. start an isolated application instance under normal change control;
3. confirm schema acceptance;
4. compare budget summaries, ledger entry counts, receipts, and verification rows;
5. reconcile representative instruction digests without executing new mutations.

The automated validation copies and reopens an isolated database and confirms the
2,000-unit balance survives migration initialization and restore. It does not
constitute a production backup or restore.

## Browser acceptance

The test-only Playwright harness uses dedicated ports and temporary databases; it
does not reuse a running service or production data:

```bash
cd projects/homelab-control-center/frontend
npm run test:e2e
```

The harness validates all four views, authenticated and role-denied states, the
2,000 → 1,500 → 500 path, rejection, stale conflict, history, and unresolved
rendering. Chromium must first be installed with `npx playwright install chromium`.

## Security and exclusions

The operator token identifies the caller but never grants a Budget role by itself.
Every read and write route performs domain permission checks. There is no runtime
role-administration API, payment or bank connection, multi-currency conversion,
partial delivery, deletion, or ledger update path. Corrections are separately
governed compensating entries linked to an allocation or adjustment; commitments
use settlement or cancellation.
