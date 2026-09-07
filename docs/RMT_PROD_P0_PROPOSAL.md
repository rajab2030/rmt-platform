# RMT — Production-Readiness P0 Batch (Proposal)

**Status:** **APPROVED 2026-09-07.** Implementation to follow this scope.
Owner decisions recorded: (1) approve P0 scope as written; (2) **authorize the
narrow frozen-Core hardening deviation** to `durable_store._persist` (E1),
documented like C07 freeze deviation #1; (3) **reverse proxy + loopback bind**
for S4 (Caddy `tls internal`, app on `127.0.0.1`); (4) agent read-only routes
go behind auth (default); (5) keep the `RMT_AUTH_ENABLED=False` local-dev escape
hatch (default).
**Classification:** Above-Core / operational. No C08. No reopening of C01–C07.
**One frozen-Core file is touched (E1)** — narrow, behaviour-preserving,
output-identical; owner-authorized.
**Threat model (owner decision, recorded):** **(b) Trusted LAN, few operators.**

Closes the blocking set from `docs/RMT_PRODUCTION_READINESS.md`:
**S1** (authentication) + **S2-lite** (operator identity), **S4** (transport /
bind), **E1** (atomic evidence writes), **O2** (held-action alerting).

**Not in this batch:** E2 (hold-store persistence) — needs the separate
"Core fix vs above-Core mitigation" decision; **S3** separation-of-duties
*enforcement* (identity is recorded here, the approver≠grantor rule is a
fast-follow toggle); E3/E4/E5 and all P1/P2 items.

---

## 1. Objective

Make the running RMT platform safe to expose on the trusted LAN and safe to run
unattended:

1. No mutating call succeeds without an authenticated operator identity.
2. That identity — not a free-text body field — is what lands in the governance
   evidence.
3. Traffic terminates TLS at a reverse proxy; the app binds loopback only.
4. A crash or two concurrent writers can no longer corrupt a governance-evidence
   file.
5. When an action is held for human approval, a human is notified.

## 2. What already exists (reused / relevant)

| Piece | Location | Relevance |
|---|---|---|
| All 10 mutating routes | `app/main.py` `@app.post(...)` | Above-Core composition root — auth dependency attaches here, no Core edit. |
| `agent_router` (POST grant/act/act.llm + GET status/authority) | `app/agent/api.py`, included in `app/main.py` | Included with the auth dependency. |
| Core routers (`intelligence_router`, `observability_router`) | `app/core/**/api.py` | **Read-only** (`GET` only) — left open, or share the dependency; owner choice. |
| `DurableStore._persist` | `app/core/intelligence/durable_store.py` | The single write primitive for all six governance-evidence JSON files. E1 is a ~6-line change here. |
| `manual_approval_required` observable sites | `app/main.py` (`/execute`, `/homelab/remediate`), `app/homelab/operational_loop.py`, `app/agent/adapter.py` | O2 hooks attach at these above-Core sites — every reachable hold is covered without touching Core. |
| stdlib `urllib` client pattern | `app/agent/llm_client.py` | Reused for the O2 webhook — no new dependency. |
| `pydantic-settings` | installed | Available for config; this batch uses plain env vars to match `loop_config.py`. |

## 3. Design

### 3.1 S1 + S2-lite — Authentication & operator identity

**New — `app/ops/__init__.py`, `app/ops/auth.py`** (above-Core).

- Config (env, read dynamically):
  - `RMT_AUTH_ENABLED` (default **True** once deployed; a documented
    `False` escape hatch for local dev only).
  - `RMT_OPERATOR_TOKENS` — comma-separated `name:token` pairs, e.g.
    `alice:2f9c…,bob:7d1a…`. Empty + `RMT_AUTH_ENABLED=True` → the app refuses
    to start (fail-closed, no silent open surface).
- `require_operator` FastAPI dependency:
  - Reads `Authorization: Bearer <token>` (also accepts `X-API-Key: <token>`).
  - Constant-time compare against the configured tokens.
  - Miss / malformed / unknown → `HTTPException(401)`.
  - Hit → returns `OperatorIdentity(name=<name>)`.
- Attach:
  - Every `@app.post` in `app/main.py` gains `dependencies=[Depends(require_operator)]`.
  - `app.include_router(agent_router, dependencies=[Depends(require_operator)])`
    (protects `/agent/*` including its two GETs — acceptable; owner may instead
    ask for GET-open).
  - Core read-only routers unchanged (owner choice to also protect them).
- **S2-lite:** handlers that today take an identity in the body
  (`/approve` `approved_by`, `/homelab/approve` `approved_by`,
  `/agent/authority/grant` `granted_by`) instead take it from the authenticated
  `OperatorIdentity`. The body field is removed (or, transitional: ignored with
  a deprecation note). The authenticated name is what reaches
  `approve_held_action` / the grant / the evidence records — so
  `authorized_by` / `approved_by` in the durable stores is now trustworthy.

No `app/core/**` change. The Core functions already accept an `approved_by`
string; we simply pass a verified one.

### 3.2 S4 — Transport security & bind

**Ops change (owner runs; I provide the files):**

- **New drop-in** `rmt-control-center.service.d/bind-loopback.conf` — override
  `ExecStart` to `--host 127.0.0.1 --port 8000`.
- **New `deploy/Caddyfile`** (repo-tracked) — a reverse proxy on the LAN
  interface, `tls internal` (Caddy's internal CA; import the root on operator
  machines) or a homelab-CA cert, `reverse_proxy 127.0.0.1:8000`. Caddy chosen
  for one-line auto-TLS; nginx config provided as an alternative on request.
- **Runbook** `docs/operations/DEPLOY.md` (new) — install proxy, trust the CA,
  verify, roll back.
- **Interim acceptable for (b):** if the owner defers the proxy, bind to the
  specific LAN IP (not `0.0.0.0`) and rely on S1 auth over plain HTTP on the
  trusted LAN — documented as a time-boxed interim, not the end state.

### 3.3 E1 — Atomic, durable evidence writes

**Modified (frozen Core, ~6 lines, behaviour-preserving) —
`app/core/intelligence/durable_store.py::_persist`:**

```
tmp = self._file_path.with_suffix(self._file_path.suffix + ".tmp")
with open(tmp, "w") as f:
    json.dump([r.model_dump(mode="json") for r in self._records], f, indent=4)
    f.flush()
    os.fsync(f.fileno())
os.replace(tmp, self._file_path)   # atomic on POSIX
```

- **No API change, no format change, no behaviour change** for any caller: same
  method signature, identical file contents, same call sites. The only
  difference is that a reader never sees a half-written file and an interrupted
  write leaves the previous good file intact.
- `_load` gains a one-line tolerance: ignore a stale `*.tmp` if present.
- **Why it must touch Core:** `DurableStore` is the sole write primitive for the
  six governance-evidence stores and is defined in a frozen file; there is no
  above-Core seam that intercepts the write without a fragile monkeypatch.
  Criterion 11 of the Core Target State ("preserve correlated evidence …
  including blocked and failed paths") is materially weakened by a non-atomic
  writer — this is a hardening of an existing Core contract, not a new
  capability.
- **Owner authorization required.** If withheld: fall back to a startup shim in
  `app/main.py` that rebinds `DurableStore._persist` (works, less clean, noted
  as a deviation of its own) — or defer E1.

### 3.4 O2 — Held-action notifications

**New — `app/ops/notifications.py`** (above-Core).

- `notify_held(*, kind, component, approval_id, detail, source)`:
  - `kind` ∈ `{"remediation", "agent_proposal", "operator_execute"}`;
    `source` = the code path (e.g. `operational_loop`, `agent_adapter`).
  - If `RMT_NOTIFY_WEBHOOK_URL` is set → POST a small JSON payload via stdlib
    `urllib`, 5 s timeout. Otherwise → structured log line only.
  - **Fail-open:** any exception is caught and logged; the notifier never raises
    into the governed path.
  - Optional `RMT_NOTIFY_MIN_INTERVAL_SECONDS` de-dupe per
    `(kind, component, approval_id)` so a loop cannot spam.
- **Call sites (all above-Core, one line each):**
  - `app/main.py` `/execute` — when the result status is `manual_approval_required`.
  - `app/main.py` `/homelab/remediate` — same.
  - `app/homelab/operational_loop.py` `_process_component` — on a held outcome.
  - `app/agent/adapter.py` `propose_and_govern` — in the
    `manual_approval_required` branch.
- Disabled-by-default in effect: no webhook configured → it only logs, so
  landing the code is safe before a sink exists.

### 3.5 New config surface (also starts D5)

`docs/operations/CONFIG.md` (new) — one table of every `RMT_*` var across
`loop_config.py`, `agent/loop_config.py`, and this batch, with default + effect
+ which drop-in sets it.

## 4. Explicitly OUT of scope

- **E2** (resolved hold not persisted to the hold store) — separate decision
  (Core fix vs above-Core reconciliation). The record store stays authoritative
  meanwhile.
- **S3 enforcement** (approver ≠ grantor/proposer) — identity is *recorded* by
  this batch; the *rule* is a small fast-follow behind a config toggle.
- **E3** failed-execution evidence, **E4** retention/rotation, **E5** evidence
  backup — P1, next.
- Any change to the governance logic, the lifecycle, the adapter contract, or
  Core behaviour beyond the E1 atomic-write hardening.
- Full IAM / SSO / RBAC — excluded for threat model (b).

## 5. Core-integrity statement

- Diff: **new** `app/ops/**`; **modified** `app/main.py`,
  `app/homelab/operational_loop.py`, `app/agent/adapter.py`; **modified (frozen
  Core, hardening only)** `app/core/intelligence/durable_store.py`; new
  `deploy/`, `docs/operations/*`, systemd drop-in; test files.
- No second mutation boundary. No change to policy / risk / approval /
  authorization / verification / learning behaviour. `execute_governed_action`
  and `approve_held_action` are called exactly as today, with a *verified*
  `approved_by`.
- E1 is byte-for-byte output-identical; it changes *when* bytes become visible,
  not *what* they are.
- Held proposals are still never auto-continued; O2 only observes and notifies.

## 6. Tests

**New**
- `app/ops/testing/test_auth.py` — no header → 401; malformed → 401; unknown
  token → 401; valid → identity resolved; every `@app.post` route rejects
  unauthenticated (parametrised); `RMT_AUTH_ENABLED=True` + empty tokens →
  startup refuses.
- `app/ops/testing/test_notifications.py` — held outcome → exactly one webhook
  POST (mocked); webhook 500 / timeout → caught, governed result unaffected;
  no `RMT_NOTIFY_WEBHOOK_URL` → log only, no HTTP; de-dupe within the interval.
- `app/core/intelligence/testing/test_durable_store_atomic.py` — interrupted
  write (simulated exception mid-dump) leaves the prior file intact and no
  partial main file; `.tmp` is cleaned / ignored on load; normal round-trip
  unchanged.

**Modified**
- Every existing `TestClient` test that calls a mutating route
  (`test_http_entrypoints.py`, agent API tests, homelab API tests) — inject a
  valid `Authorization` header via a shared fixture. Expected churn: ~6–10 test
  files, header-only.
- Any test asserting on `approved_by="…"` from a body param → assert the
  authenticated identity instead.

**Gate:** Core intelligence **122** unchanged in behaviour (the atomic-write
test is additive); full app suite green (**214 + new**); `import app.main` clean;
with `RMT_AUTH_ENABLED=False` the suite still runs for local dev.

## 7. Validation plan

1. Full suite green (Core 122 + app 214 + new).
2. `import app.main` clean; app refuses to start with auth on + no tokens.
3. Deploy to live: drop-ins (`bind-loopback.conf`, tokens), Caddy up, CA trusted.
4. Re-run the **CAP-05 LLM exercise under auth** on live `:8000` (via the proxy):
   unauthenticated `/agent/*` → 401; authenticated grant → propose → held →
   **notification fires** → approve → governed docker → verify. Evidence shows
   the real operator name in `authorized_by` / `approved_by`.
5. **Restart test:** kill -9 the service mid-cycle; on restart every evidence
   file loads clean, no `.tmp` residue, hold/record consistent (E1; E2 caveat
   still noted).
6. CAP-04 loop resumes `no_remediation`.

## 8. Risks & mitigations

| Risk | Mitigation |
|---|---|
| Auth change locks out the frontend / existing scripts | `RMT_OPERATOR_TOKENS` issued before cutover; frontend gets a token; `DEPLOY.md` covers it. |
| Token in env / journald | File-mode-restricted drop-in; tokens are opaque random; rotate by editing the drop-in + restart. Vault is P2 (S6). |
| Frozen-Core edit sets precedent | Scoped to `_persist` internals, output-identical, documented as a named deviation like C07 #1; owner authorizes explicitly or we take the shim. |
| Reverse proxy adds an operational moving part | Caddy is a single static binary + 4-line config; nginx alternative offered; interim plain-HTTP+auth path documented. |
| O2 webhook down | Fail-open + log; a missed notification never blocks or breaks a governed action. |
| Test churn introduces flakiness | Header injection is a single shared fixture; no logic change in the tests. |

## 9. Decisions for the owner

1. **Approve this P0 scope** (S1 + S2-lite + S4 + E1 + O2) as written, or adjust?
2. **E1 frozen-Core hardening** — authorize the ~6-line `durable_store._persist`
   atomic-write deviation? (Recommended.) If not: startup shim, or defer E1.
3. **S4 transport** — reverse proxy + loopback bind now (recommended), or
   interim LAN-IP bind + plain HTTP + auth, proxy as immediate follow?
4. **Agent read-only routes** (`GET /agent/status`, `/agent/authority`) — behind
   auth (simplest), or left open?
5. **`RMT_AUTH_ENABLED=False` escape hatch** — keep it for local dev
   (recommended), or no bypass at all?

---

## 10. Implementation record (2026-09-07)

**Delivered — new `app/ops/` package**
- `ops_config.py` — env reader (`RMT_AUTH_ENABLED`, `RMT_OPERATOR_TOKENS`,
  `RMT_NOTIFY_*`), read dynamically.
- `auth.py` — `OperatorIdentity`, `resolve_operator` (framework-free),
  `require_operator` (FastAPI dependency). Bearer + `X-API-Key`, constant-time
  compare, 401 on miss/bad, 503 if enabled-but-unconfigured.
- `notifications.py` — `notify_held` (stdlib `urllib` webhook, fail-open,
  per-`(kind,component,approval_id)` de-dupe; logs when no webhook set).
- `testing/test_auth.py` (auth on), `testing/test_notifications.py`.

**Modified**
- `app/main.py` — S1: `require_operator` on all 10 `@app.post` routes + the
  `/agent/*` router include; lifespan refuses to start when auth is on and no
  tokens are set. S2-lite: `/approve` + `/homelab/approve` take the identity
  from the auth dependency (`approved_by` body field now ignored, kept optional
  for transition); `/execute` threads `operator.name` into `decision_id` /
  `reason`. O2: `notify_held` on a `manual_approval_required` result from
  `/execute` and `/homelab/remediate`.
- `app/agent/api.py` — `grant_authority` takes `require_operator`; `granted_by`
  from `operator.name` (body field optional/ignored).
- `app/agent/adapter.py` — O2: `notify_held(kind="agent_proposal", …)` in the
  `manual_approval_required` branch.
- `app/homelab/operational_loop.py` — O2: `notify_held(kind="remediation", …)`
  when a cycle outcome is `manual_approval_required`.
- `app/core/intelligence/durable_store.py` — **E1** (authorized frozen-Core
  hardening): `_persist` writes `*.tmp` → `flush`/`fsync` → `os.replace`;
  `_load` discards a stale `*.tmp`. Byte-identical committed output.
- `requirements.txt` — pinned direct deps + test-only; `requirements.lock.txt`
  added (full 33-pkg `pip freeze`). **D1**.
- `conftest.py` (new, backend root) — defaults the suite to `RMT_AUTH_ENABLED
  =false`; `test_auth.py` opts back in.

**Deploy artifacts (new)** — `deploy/Caddyfile`,
`deploy/systemd/bind-loopback.conf`, `deploy/systemd/auth.conf.example`;
`docs/operations/DEPLOY.md` (**D2**), `docs/operations/CONFIG.md` (**D5**).

**Validation** — full suite **254 passed** (214 + 40 new); Core intelligence
**126** (122 unchanged + 4 atomic-write); `import app.main` clean; suite runs
with auth off, `test_auth.py` runs with auth on (per-route 401 + accept, startup
refusal, identity-reaches-grant).

**Core integrity** — one frozen-Core file touched (`durable_store.py`),
behaviour-preserving and owner-authorized; no change to policy / risk / approval
/ authorization / verification / learning behaviour; no second mutation
boundary; held proposals still never auto-continued.

**Not done here** — S4 Caddy proxy; E2; S3 enforcement; E3/E4/E5; P1/P2.

### Live deployment (2026-09-07 12:36 UTC)

- Drop-ins installed: `auth.conf` (mode 0600, two operator tokens `ragb`,
  `ops2`), `bind-loopback.conf`. `daemon-reload` + `restart`; service `active`
  on the new code.
- **Verified on live:** `POST /homelab/loop/stop` no token → 401; with token →
  200; `GET /` (open) → 200; `POST /agent/authority/grant` with body
  `granted_by:"IGNORED"` → recorded `granted_by:"ragb"`; app listens
  `127.0.0.1:8000` only, `192.168.223.128:8000` refused; 6 evidence files parse,
  no `.tmp` residue; CAP-04 loop + agent still enabled and healthy.
- **Not yet:** Caddy TLS proxy (RMT has no LAN entry point — loopback + auth
  only); restart-safety hard-kill test (E1 is unit-tested); CAP-05 LLM exercise
  re-run under auth (optional).
- **Token values are not in the repo by design** — read them with
  `sudo cat /etc/systemd/system/rmt-control-center.service.d/auth.conf`.

---

*Approved and implemented 2026-09-07; deployed to live the same day.*

🤖 Generated with [Claude Code](https://claude.com/claude-code)
