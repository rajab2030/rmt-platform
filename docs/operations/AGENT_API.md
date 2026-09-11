# RMT Platform — Agent Integration Guide

RMT-CAP-08. Above-Core / operational. This is the workflow guide the raw
OpenAPI schema (`GET /docs`, `GET /openapi.json` — always on) doesn't give
you: what to call, in what order, what the response actually guarantees, and
what it never will.

**The one rule that matters more than any endpoint:** an agent *proposes*.
It never executes, never holds its own authority, never approves its own
hold. Every consequential action still passes the full frozen-Core lifecycle
— policy, risk, approval, authorization, execution, verification — exactly
as if a human had typed it into `POST /execute`. Nothing described here is a
second, lighter path.

---

## 1. Authentication

Every route below requires an authenticated operator:
`Authorization: Bearer <token>` or `X-API-Key: <token>`, matched against
`RMT_OPERATOR_TOKENS`. The matched name is recorded as `granted_by` on any
grant you issue — not a free-text field, so it's trustworthy in the evidence
trail. See `docs/operations/CONFIG.md` for how tokens are provisioned.

## 2. The lifecycle

```
POST /agent/authority/grant   (operator issues a scoped, single-use grant)
        │
        ▼
POST /agent/act/preview       (optional — zero side effects, see §5)
        │
        ▼
POST /agent/act               (the agent proposes)
        │
        ├── decision: "allow"          → executed immediately, verified
        ├── decision: "hold" /
        │   "escalated_hold"           → held; a human must act next:
        │                                POST /homelab/approve
        ├── decision: "no_authority"   → refused before governance ran at all
        └── decision: "deny" / "rejected" → refused by policy/risk
```

### Step 1 — Get a grant

```bash
curl -X POST https://<host>/agent/authority/grant \
  -H "Authorization: Bearer <token>" -H "Content-Type: application/json" \
  -d '{"operation": "create", "target": "v1.0.0-release"}'
```

Returns:

```json
{
  "grant_id": "90451fad172e",
  "operation": "create",
  "target": "v1.0.0-release",
  "granted_by": "<operator name from your token>",
  "expires_at": "2026-09-11T09:19:44Z",
  "consumed": false,
  "consumed_at": null
}
```

A grant is **operation- and target-scoped** (exact string match, never a
prefix or pattern), **time-limited** (`RMT_AGENT_GRANT_TTL_SECONDS`, default
300s), and **single-use** — consumed the moment a proposal using it is
accepted into the governed pipeline (executed or held; a pre-governance
refusal leaves it untouched). Grants are durable (RMT-CAP-08) — they survive
a service restart, unlike in earlier versions of this surface.

### Step 2 — Propose

```bash
curl -X POST https://<host>/agent/act \
  -H "Authorization: Bearer <token>" -H "Content-Type: application/json" \
  -d '{
    "agent_id": "release-bot",
    "goal": "tag the v1.0.0 release",
    "target": "v1.0.0-release",
    "mechanism": "create",
    "reason": "CI pipeline requested a release tag",
    "confidence": 90,
    "expected_state": "present",
    "grant_id": "90451fad172e",
    "operational_context": "git"
  }'
```

`mechanism` must be one of: `start`, `stop`, `restart`, `create`, `remove`,
`restart_component`, `create_checkpoint`, `scale_down`, `isolate_component`
— anything else is refused before a proposal is even built
(`decision: "invalid"`). `operational_context` selects which domain/adapter
resolves the action — `"homelab"` (default) or `"git"` today; see
`docs/RMT_CAP_06_PROPOSAL.md` for what adding a domain involves.
`expected_state` is domain-specific (`"running"` for homelab, `"present"` /
`"absent"` for the git-tag domain) — get it wrong and verification will
correctly report a mismatch even on a successful execution.

### Step 3 — If held, a human approves

```bash
curl -X POST "https://<host>/homelab/approve?approval_id=<id>&approved=true" \
  -H "Authorization: Bearer <token>"
```

(Yes — `/homelab/approve`, regardless of domain. It's the one continuation
route every domain shares; the name is a historical artifact of homelab being
the first domain, not a scoping restriction.)

## 3. The decision vocabulary

`/agent/act`'s response `decision` field — the one field to branch your
calling code on:

| `decision` | Meaning | Reached governance? |
|---|---|---|
| `disabled` | The agent surface is off (`RMT_AGENT_ENABLED`) | No |
| `invalid` | Unrecognized `mechanism` | No |
| `no_authority` | No grant, wrong scope, consumed, or expired — `detail` says which | No |
| `hold` | Held for human approval (default policy) | Yes — held, not executed |
| `escalated_hold` | Held because of a T13 dependency-cascade escalation, even if your default wouldn't have required approval | Yes — held, not executed |
| `allow` | Executed and (if a verifier exists for the domain) verified | Yes — executed |
| `deny` | Refused by policy | Yes — refused |
| `rejected` | Refused by the approval/risk stage | Yes — refused |
| `error` | The surface itself failed defensively (never a 500) | — |

`/agent/act/preview`'s `decision` is `disabled` / `no_proposal` (empty goal
or target) / `preview` (resolved — see §5) / `invalid_proposal` (bad
mechanism).

## 4. The evidence receipt — what's guaranteed vs. informational

An accepted proposal's response (`AgentOutcome.as_dict()`) is the receipt.
Stable across releases: `decision`, `agent_id`, `target`, `mechanism`,
`approval_id` (when held), `execution_id` (when executed),
`verification_status` (when a verifier exists for the domain — `null`
otherwise, never fabricated), `escalated`, `learn_recorded`, `at`
(ISO-8601). `detail` is human-readable and **not** guaranteed stable —
don't pattern-match it in calling code; branch on `decision` and the fields
above.

`verification_status` of `null` or `"observation_unavailable"` means
**RMT genuinely doesn't know** whether the action's post-condition held —
never treat either as a success signal. Only `"verified_success"` is that.

## 5. Preview — see the outcome before it happens

`POST /agent/act/preview` takes the identical body as `/agent/act` and
returns the resolved action plus the **real** predicted policy/risk/approval
outcome (not a guess — it calls the same frozen decision functions
`/agent/act` itself uses, just stops before anything is written). Zero side
effects: no grant consumed, no hold created, nothing executed.

```json
{
  "decision": "preview",
  "action": {"component": "...", "action_type": "...", "requires_approval": true, ...},
  "authority": {"ok": true, "detail": "ok"},
  "escalation": {"escalated": false, "detail": ""},
  "predicted": {
    "policy_allowed": true,
    "risk_level": "medium",
    "approval_mode": "manual",
    "approval_reason": "Action explicitly requires approval"
  }
}
```

Use it to validate a proposal's shape before spending a grant on it, or to
show a human what an agent is about to ask for before they grant anything.

## 6. Non-guarantees (see `docs/RMT_GUARANTEES.md` / `docs/RMT_THREAT_MODEL.md`)

- **No autonomous loop.** Nothing here re-proposes or retries on your
  behalf; every call is one-shot.
- **Approval is never automatic** for anything the default policy or a T13
  escalation flags — there is no override.
- **A hold expires** at `APPROVAL_HOLD_TTL_SECONDS` (300s) if nobody acts on
  it.
- **This is a trusted-LAN, shared-bearer-token model** (posture "b" in the
  threat model), not per-agent cryptographic identity or a multi-tenant RBAC
  system — every token holder can grant and propose on behalf of anyone.
- **`operational_context` values are not self-service.** Adding a new domain
  is an above-Core code change (an adapter + observer), not a request
  parameter that unlocks new behavior on its own.

## 7. See also

- `docs/RMT_GUARANTEES.md` — plain-language guarantees per lifecycle stage.
- `docs/RMT_THREAT_MODEL.md` — trust boundary, assumed adversary.
- `docs/RMT_CAPABILITIES_EVIDENCE.md` §"RMT-CAP-06" / §"RMT-CAP-07" — the
  live exercises this contract was proven against.
- `GET /agent/status`, `GET /agent/authority` — read-only introspection.
