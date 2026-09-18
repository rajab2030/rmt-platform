# RMT — Threat Model

**Status:** LIVING RECORD, created 2026-09-10 (roadmap item **B3**,
`docs/RMT_IMPROVEMENT_ROADMAP.md` §4).
**Audience:** someone who is **not** the maintainer, deciding whether to trust
RMT with a workload. Pairs with `docs/RMT_GUARANTEES.md` (what each lifecycle
stage does and does not assert).

**2026-09-18 review:** see [security remediation](RMT_SECURITY_REMEDIATION.md)
for reproduced findings, above-Core controls, and pending deployment checks.
The earlier readiness claims below are not evidence that those new controls
are installed. In particular, direct concurrent Core approval continuation is
not atomic; the new HTTP control is limited to one backend process (DEBT D6).

This document states the assets RMT protects, the trust boundary, the assumed
adversary, the attack surface with its control, and the residual risks — each
traced to a recorded decision or gap.

---

## 1. What RMT is (scope anchor)

RMT is a **governed action gateway**: a single path
`Understand → Decide → Govern → Authorize → Execute → Verify → Learn` for
**discrete, consequential, verifiable state changes at low-to-moderate volume**,
human-in-the-loop for the risky subset. It is **not** for sub-second paths,
high-throughput fan-out, tight-loop control, or actions with no observable
outcome (`docs/RMT_ABOVE_CORE_ROADMAP.md` §2).

The RMT **Core** is frozen and validated at commit `46a4441` (C01–C07). It is
trusted by construction; the **above-Core** code (`app/ops/**`, `app/homelab/**`,
`app/agent/**`, adapters, routes) is the active attack surface and the subject
of this model.

---

## 2. Assets

| # | Asset | Why it matters |
|---|---|---|
| A1 | **The single governed mutation path** (`execute_governed_action → execution_engine.execute → adapter`) | Every real state change must go through it and nowhere else |
| A2 | **The evidence stores** — authorization / hold / approval-record / audit / trace / verification (`data/governance_evidence.db`), correlated by stable ID | Integrity + non-repudiation: "who authorized this, and was it verified?" |
| A3 | **The approval decision** for the risky subset | That a real, authenticated operator (not a spoofed body field) approved |
| A4 | **Agent authority grants** — single-use, time-limited, operation+target-scoped | An autonomous agent must not act unsupervised; capability ≠ authority |
| A5 | **The controlled targets** — today the homelab Docker containers | The thing a bypass or a bad decision actually damages |
| A6 | **Operator credentials** — bearer tokens in `RMT_OPERATOR_TOKENS` | Possession = the ability to propose / approve |
| A7 | **The host** — single Ubuntu 22.04 VM with Docker-socket access | Compromise here is game over; hardened, not eliminated |

---

## 3. Deployment topology (current — threat model (b))

- **Single** `uvicorn` process on a **single** Ubuntu 22.04 VM (no HA — R4,
  ACCEPTED).
- App binds **`127.0.0.1:8000`** only — verified unreachable off-loopback (S4).
- **Caddy 2.6.2** TLS reverse proxy on the LAN (`tls internal`, host-trusted CA)
  is the **only** network entry point (S4).
- `systemd` unit + `hardening.conf` drop-in — `systemd-analyze security`
  **4.1 OK** (was 9.2 UNSAFE) (D3).
- Auth: bearer / `X-API-Key` vs `RMT_OPERATOR_TOKENS` on **every** mutating
  route and the whole `/agent/*` router; the app **refuses to start** if auth is
  enabled but unconfigured (S1).
- Evidence: `data/governance_evidence.db` + `data/observability.db` under
  `/home`; atomic writes (E1); backup/restore tooling (E5).

---

## 4. Trust boundary and adversary

**Inside the boundary (trusted):** the RMT process and frozen Core, the evidence
DB, the `systemd` unit + drop-ins, the Caddy proxy, the operator tokens, the
Docker socket, the local model (Ollama — no credential), and the **operators**
holding a valid token on the trusted LAN.

**Outside (untrusted):** everything off the LAN; any unauthenticated caller; and
**the content of an LLM agent proposal** — treated as untrusted *input* (the
agent only proposes; it never executes).

**Chosen adversary model: (b) — Trusted LAN, one or few operators**
(`docs/RMT_PRODUCTION_READINESS.md` §2). The assumed adversary **is**:

- an unauthenticated party who reaches the LAN or the proxy;
- a confused or buggy automation / agent proposing a harmful action;
- an operator mistake (wrong target, self-approval);
- a process crash or power loss mid-write;
- a malicious dependency update.

Explicitly **out of scope** of the adversary model:

- a **hostile operator** with a valid token — separation-of-duties raises the
  bar (S3) but operators are fundamentally trusted at posture (b);
- **physical / host** compromise (root on the VM, Docker socket);
- a **hostile LAN** or **internet exposure** — that is posture (c): it requires
  the full Security group at P0/P1 and a real IAM/IdP (roadmap **P-D**) and a
  re-scope of this document.

---

## 5. Attack surface and control

| Surface | Vector | Control (readiness ref) |
|---|---|---|
| Network entry | unauthenticated mutating call | S1 — `require_operator` on all mutating routes + `/agent/*`; 401; refuses to start unconfigured |
| Network entry | plaintext / off-host reach | S4 — loopback bind + Caddy TLS; verified unreachable off-loopback |
| Cross-origin | a browser calling the API | S5 — `RMT_CORS_ORIGINS` allowlist; methods scoped to `GET, POST` |
| Expensive routes | flooding `/execute`, `/agent/act*` | S7 — fixed-window rate limit; 429 + `Retry-After` |
| Operator identity | body-spoofed `approved_by` / `granted_by` | S2-lite — identity taken from the token; body value ignored |
| Separation of duties | approver is the grantor or the proposer | S3 — `check_separation` → 403 (config-gated `RMT_AUTH_SEPARATION`) |
| Governance bypass | a second mutation path / a direct adapter call | Core anti-bypass (`RMT_CONTEXT.md` §7): one boundary; authorization bound at a single site; adapters are executors only |
| Verification spoof | adapter reports success ⇒ `verified_success` | Core — trusted internal observer, never caller-controlled; adapter success alone cannot manufacture `verified_success` |
| Agent acting unsupervised | LLM proposes a dangerous action | agent only *proposes*; every proposal runs policy/risk/approval; grants single-use / time-limited / scoped; `AGENT_DEFAULT_REQUIRES_APPROVAL` not lowered |
| Evidence tampering / loss | crash mid-write; partial write | E1 atomic writes (tmp + `fsync` + rename); E6 startup integrity cross-check; E5 backup/restore; R1 hard-kill restart proven byte-faithful |
| Secrets | a credential on disk | S6 policy — root-owned `0600` `EnvironmentFile`; **no credential exists today**; `systemd` `LoadCredential=` mandated before the first one |
| Supply chain | a malicious dependency update | D1 pinned `requirements.lock.txt`; V2 CI builds from the lock on every push |
| Host / service | crash, resource exhaustion | D3 hardening + resource ceilings; D4 `/health` watchdog; R3 cold-rebuild runbook |

---

## 6. Residual risks (each traced)

| Residual risk | Why it remains | Recorded as |
|---|---|---|
| A resolved hold reads `pending` on a **direct disk read** until the next startup reconcile | frozen Core `approve_held_action` does not persist the hold | DEBT **D1**; readiness **E2** (reconcile mitigation) |
| A failed adapter execution is a **status, not a rollback** | frozen Core verify runs on the success branch only | DEBT **D2**; readiness **E3** |
| The **Core verifier itself** asserts a post-condition only for module `create` | frozen `_resolve_trusted_observer` | DEBT **D3**; proposal **B1** |
| Docker-named fields on Core surfaces would mislead a second runtime adapter | scope of freeze-deviation #1 | DEBT **D4** |
| Deferred adapter-decoupling scope **#4–#18 is un-enumerated** | owner REDUCE-SCOPE decision | DEBT **D5** |
| **No HA** — a restart / redeploy is minutes of downtime | single process, single host, homelab scale | readiness **R4** (ACCEPTED) |
| Separation-of-duties is **off by default** | `RMT_AUTH_SEPARATION` default off | readiness **S3** |
| **No multi-operator identity / RBAC** — shared bearer tokens | posture (b), not (c) | roadmap **D2 / P-D** |
| O2 / O3 alerts **log to the journal only** until a webhook sink is set | `RMT_NOTIFY_WEBHOOK_URL` unset | readiness **O2** (open action) |
| Branch protection (required CI check) is unavailable | free private GitHub repo | readiness **V2** (follow-up) |
| The LLM agent path (5B) trusts prompt-derived proposals as **input** | mitigated (proposes only, full governance), not eliminated | roadmap **C3** |

---

## 7. If the posture changes

Moving to **(c) multi-user or internet-reachable** requires: the full Security
group at P0/P1, a real IAM / external IdP (roadmap **P-D**), per-route role
enforcement, and a re-scope of this document and `docs/RMT_GUARANTEES.md`. Do
not expose RMT beyond the trusted LAN under the current controls.
