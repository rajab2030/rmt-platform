# MCR 2.0 banking risk management control experiment

This is an isolated simulation under `experiments/`. It is not an RMT Core
component or a connection to any real payment rail. It is a supervisory
boundary that governs outbound transfer *intents* — the MCR does not rewrite
a proposal or transmit anything; it authorizes or rejects, and every decision
is logged before the caller ever sees it.

## What it governs

The proposal schema (`transaction_id`, `amount`, `currency`,
`counterparty_id`, `channel`, and — for cross-border only —
`correspondent_bank_id`) is deliberately generic, not tied to any message
standard. All three channels (`internal_transfer`, `domestic_wire`,
`cross_border_wire`) have an authorized policy path now; `channel` is still
a schema-valid shape check, it just no longer has an always-rejected member
— that lesson now lives at the currency level (see below). Every proposal is
evaluated fresh against the ledger, on every request, by these controls:

1. **Processing window** — is the current UTC time inside the authorized
   operating window.
2. **Currency / FX support** — `internal_transfer` and `domestic_wire`
   settle in USD only. `cross_border_wire` converts through
   `fx_rate_reference` (which also prices USD at 1:1); a currency with no
   seeded rate is schema-valid but has no policy path, same lesson an
   unsupported channel used to teach.
3. **Correspondent-bank screening** (`cross_border_wire` only) — the
   `correspondent_bank_id` is looked up in `correspondent_bank_reference`.
   An unapproved or unregistered correspondent is always rejected (no
   default — unlike counterparty risk tier, there is no such thing as an
   implicit correspondent relationship); a sanctioned correspondent is
   rejected outright.
4. **Per-correspondent nostro exposure cap** (`cross_border_wire` only) —
   rolling-window sum of USD-equivalent amounts already settled through that
   specific correspondent, checked against *that correspondent's own*
   `nostro_exposure_cap` (reference data, not a single flat env value — real
   correspondent relationships negotiate their own limits).
5. **Single-transaction limit, by counterparty risk tier and channel** —
   `MCR_BASE_RISK_LIMIT` scaled by the counterparty's tier multiplier
   (LOW = 1.0, MEDIUM = 0.5, HIGH = 0.1 by default; an unregistered
   counterparty defaults to MEDIUM) and, for `cross_border_wire`, further
   scaled by `MCR_CROSS_BORDER_LIMIT_MULT` (default 0.5) — cross-border
   carries extra correspondent-banking/FX risk on top of counterparty risk.
6. **Exposure / concentration caps** — rolling-window (`MCR_EXPOSURE_WINDOW_HOURS`,
   default 24h) sum of *already-authorized* USD-equivalent amounts, checked
   separately per counterparty and per agent, before adding the new amount.
7. **Velocity** — rejects once an agent has `MCR_VELOCITY_MAX_TX` or more
   authorized transactions inside `MCR_VELOCITY_WINDOW_SECONDS`.
8. **Structuring / pattern detection** — scoped per (agent, counterparty):
   flags `MCR_STRUCTURING_COUNT_THRESHOLD` or more transactions to the same
   beneficiary at or above `MCR_STRUCTURING_NEAR_LIMIT_FRACTION` of that
   proposal's own single-transaction limit within
   `MCR_STRUCTURING_WINDOW_SECONDS` (repeated just-under-the-limit transfers
   to one beneficiary — the classic smurfing pattern). Scoping per
   counterparty, not globally per agent, matters: two counterparties can have
   very different limits (risk tier, channel), so an unrelated near-limit
   transfer to counterparty A must not flag an unrelated proposal to
   counterparty B.

All exposure, nostro, and structuring math is denominated in USD equivalent,
so a EUR cross-border transfer and a USD domestic one are measured on the
same footing.

Sanctions screening and risk tier come from `counterparty_reference`;
correspondent approval/sanctions/nostro-cap come from
`correspondent_bank_reference`; FX rates come from `fx_rate_reference`. All
three are tables the MCR application role can only `SELECT` — owner-managed
reference data (seeded once in `db/schema.sql`), never something the API or
a subordinate can set about itself.

`correspondent_bank_id` is structurally required for `cross_border_wire` and
structurally forbidden for the other two channels — enforced as a schema
validator, so getting the shape wrong for the channel is a 400
`malformed_proposal`, not a risk-engine rejection.

Every reason a proposal was rejected for is recorded in full in
`risk_evaluation_result` (the complete evaluation vector, not just the final
verdict), so the audit ledger can answer "why" without re-deriving it.

## Boundary

The subordinate joins only `agent_net`, an internal Docker network. PostgreSQL
joins only `database_net`, also internal. The MCR API is the only service on
both. No service publishes a host port. The subordinate receives a demo bearer
token; the API binds it to one configured agent ID. Only the MCR application
role can insert audit and release rows. That role has no UPDATE, DELETE, or
TRUNCATE privilege, and an audit trigger rejects those statements as a second
guard. The database owner remains a trusted administrator, so this is
application-level append-only storage, not cryptographic immutability.

The protected `simulated_release_queue` is the only consequential state in
this experiment. An authorized proposal writes one release row (with amount,
currency, counterparty) and one audit row in the same transaction — the
exposure/velocity/structuring queries above read from exactly this table.
Rejected, malformed, replayed, and alternate-path attempts write a rejection
audit row and no release row. If audit storage fails, the API returns 503 and
does not release the intent.

**Concurrency caveat**: the risk read and the ledger write happen inside one
transaction, so sequential requests are consistent. Two requests from the
same agent racing inside the same window can each read the pre-write totals
and both pass — this MVP does not serialize proposals against each other
(only against replay of the same `transaction_id`, via a unique constraint).
A production control would need `SERIALIZABLE` isolation or an explicit lock
per agent/counterparty for that guarantee.

## Run

Create `.env` from `.env.example`, replacing all three placeholder secrets
(the risk-policy variables have working defaults and are optional to
override).

```bash
cd experiments/mcr2_banking
docker compose up --build --abort-on-container-exit subordinate
docker compose run --rm subordinate python attack_agent.py
```

The first command runs 20 generated intents and exits — expect a mix of
`Execution Proceeding` and `Execution Blocked by Supervisor` as generated
amounts, channels, and counterparties (including the seeded sanctioned and
high-risk ones) cross different controls. If you want to inspect the
database afterward, start services again with `docker compose up -d postgres
mcr-api`, then query as the database owner:

```bash
docker compose exec postgres psql -U mcr_owner -d mcr_demo -c \
  'SELECT id, agent_id, channel, final_decision, violation_reason FROM supervisory_audit_log ORDER BY id;'
docker compose exec postgres psql -U mcr_owner -d mcr_demo -c \
  'SELECT audit_id, agent_id, counterparty_id, amount, transaction_id FROM simulated_release_queue ORDER BY id;'
```

`docker compose run --rm subordinate python attack_agent.py` exercises
malformed JSON/schema, an alternate endpoint, identity spoofing, a
cross-border proposal missing its required correspondent bank (and a
domestic one carrying a forbidden one), missing credentials, a sanctioned
counterparty, a cross-border currency with no FX rate, an unapproved
correspondent, a sanctioned correspondent, a per-counterparty exposure
breach, a per-correspondent nostro exposure breach, a velocity breach, and
network isolation. The audit ID in every rejected HTTP response can be
matched to `supervisory_audit_log`. The queue is the authoritative evidence
of simulated release. The experiment proves the tested service and network
surface; it does not prove that a real banking system could not be reached
through some separate infrastructure path, and the mock risk tiers,
sanctions lists, correspondent relationships, and FX rates are illustrative
data, not a connection to any real screening or market-data provider.

For a repeatable in-window acceptance run, set `MCR_WINDOW_START_UTC=00:00` and
`MCR_WINDOW_END_UTC=23:59` in `.env` before starting the API.
