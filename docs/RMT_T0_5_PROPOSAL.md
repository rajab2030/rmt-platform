# RMT — T0-5: Security group finish (Caddy/S3/S5 doc-sync) + a live credential-exposure fix — Proposal

**Status:** APPROVED 2026-09-12 (owner approved via explicit selection after
recon; per the roadmap's own process rule, a proposal precedes code — this
is that record).
**Classification:** Above-Core / operational. No `app/core/**` change. No C08.
No reopening of C01–C07.

Governing refs: `docs/RMT_ABOVE_CORE_ROADMAP.md` §4 T0-5,
`docs/RMT_PRODUCTION_READINESS.md` Group S, `docs/operations/SECRETS.md`,
`AGENTS.md`, `STEWARD.md`.

---

## 0. Recon findings

| # | Finding |
|---|---|
| 1 | T0-5's three named items (S4 Caddy cutover, S3 separation-of-duties, S5 CORS-from-config) were **already shipped and live**, dated 2026-09-08, under `docs/RMT_PRODUCTION_READINESS.md` Group S — the same doc-sync gap pattern already found and fixed for T0-3 and T0-2 in this session. Verified live on the actual host: `systemctl is-active caddy` → `active`, Caddy `2.6.2`; the `hardening.conf`/`bind-loopback.conf`/`cap04-loop.conf`/`cap05-agent.conf`/`auth.conf` drop-ins installed (see finding 3 for the one gap — `hardening.conf` is **not** actually installed live, contradicting D3's "DONE" framing at the drop-in-inventory level, though the drop-in itself is fully built and tested). |
| 2 | **S3** (`app/ops/separation.py`, `RMT_AUTH_SEPARATION`) is real and tested (15 tests) but **default-off**, and confirmed off on the live deployment (`systemctl show -p Environment` — see finding 4 — showed no `RMT_AUTH_SEPARATION`). `docs/operations/CONFIG.md` already notes "with one operator, agent-hold approvals need a second identity — enable only when you have one." The live deployment now has **two** operators (`ragb`, a second `ops2`), so this condition is now met. |
| 3 | `hardening.conf` is listed in `docs/operations/DEPLOY.md` §5.1 as **not yet installed** on the live host ("Required action: Install the drop-in..."), and confirmed absent from the live drop-in directory during this session's recon (`ls /etc/systemd/system/rmt-control-center.service.d/` showed `auth.conf`, `bind-loopback.conf`, `cap04-loop.conf`, `cap05-agent.conf` — no `hardening.conf`). This is a **D3** gap, not a T0-5 item; noted here because it was found during the same recon pass, not acted on in this change (out of scope — see §4). |
| 4 | **Critical, unplanned finding:** `systemctl show -p Environment rmt-control-center.service`, run as the unprivileged `rmt-lab` user (uid 1000, no sudo) during this session's recon, printed the live `RMT_OPERATOR_TOKENS` value in full plaintext — both production operator tokens. `docs/operations/SECRETS.md` (pre-2026-09-12) claimed the root-owned `0600` `auth.conf` file meant "the `rmt-lab` service user cannot read it" — true of the *file*, false of the *resolved value*, since `systemctl show` reads a unit's plain environment via systemd/D-Bus, which is not gated by the drop-in file's DAC permissions and is readable by any local user. This is exactly the scenario `docs/operations/SECRETS.md` §"Required before ANY new credential" had already pre-designed a fix for (`LoadCredential=` + a `$CREDENTIALS_DIRECTORY`-first `_cred_or_env()` reader) — pre-approved, just never triggered because the doc framed `RMT_OPERATOR_TOKENS` as not needing it. It does. |
| 5 | `app/ops/ops_config.py::operator_tokens()` is the single choke point for token parsing — `app/main.py` (startup refusal check) and `app/ops/auth.py` (the actual auth check) both call it, no other code touches `RMT_OPERATOR_TOKENS` directly. A fix at that one function closes the gap everywhere. |

## 1. Objective

1. Correct the roadmap doc-sync gap for S4/S3/S5 (finding 1) — no code change.
2. Close the live credential-exposure gap (finding 4) by moving
   `RMT_OPERATOR_TOKENS` onto the `LoadCredential=` pattern
   `docs/operations/SECRETS.md` had already pre-designed, exactly as that doc
   specifies.
3. Rotate the two exposed production tokens (owner action — requires `sudo`,
   which this session does not have; commands provided, run by the owner in
   a private terminal, not through this session's `!` mechanism, to avoid
   re-exposing the *new* tokens in the same transcript that leaked the old
   ones).

## 2. In scope

- `app/ops/ops_config.py` — new `_operator_tokens_raw()`: reads
  `$CREDENTIALS_DIRECTORY/RMT_OPERATOR_TOKENS` when `$CREDENTIALS_DIRECTORY`
  is set (systemd sets this automatically for a unit using
  `LoadCredential=`), falling back to the `RMT_OPERATOR_TOKENS` env var
  (local dev / tests / non-systemd runs). `operator_tokens()` calls it
  instead of reading the env var directly. No other function changes; no
  call-site changes (`app/main.py`, `app/ops/auth.py` are unaffected).
- `deploy/systemd/auth.conf.example` — `LoadCredential=
  RMT_OPERATOR_TOKENS:/etc/rmt/operator_tokens.secret` replaces
  `Environment=RMT_OPERATOR_TOKENS=...`. The drop-in itself now holds no
  secret and does not need `0600`.
- `docs/operations/DEPLOY.md`, `docs/operations/CONFIG.md`,
  `docs/operations/SECRETS.md`,
  `projects/homelab-control-center/deploy/systemd/README.md`,
  `backend/scripts/rmt-rebuild.sh` (its printed manual-steps checklist) —
  updated to the two-file setup (`auth.conf` + `/etc/rmt/operator_tokens.secret`)
  and rotation procedure.
- `docs/RMT_ABOVE_CORE_ROADMAP.md` — S4/S3/S5 marked done with cross-refs,
  matching the T0-2/T0-3 corrections already made this session.
- Tests: `app/ops/testing/test_auth.py` — 3 new (credentials-directory takes
  precedence over env var; missing credential file falls back to env var;
  no `$CREDENTIALS_DIRECTORY` set uses env var — the existing behavior,
  regression-covered).

## 3. Explicitly OUT of scope

- **Enabling `RMT_AUTH_SEPARATION=true` on the live deployment** (finding 2)
  — a genuine behavior change (an agent-hold approval by the grantor starts
  failing with 403), not a doc or credential-storage fix; raised to the
  owner as a separate decision, not bundled into this change.
- **Installing `hardening.conf` on the live host** (finding 3) — a D3 gap,
  not named in T0-5's scope; recorded here as found, not fixed here.
- Any change to `RMT_AUTH_SEPARATION`, `RMT_CORS_ORIGINS`, or Caddy
  configuration — S3 and S5's *code* is already correct and tested; S4's
  Caddy install is already live. Nothing about their behavior changes here.
- Generalizing `_operator_tokens_raw()` into a reusable `_cred_or_env(name)`
  helper for future credentials — only one credential exists today
  (`docs/operations/SECRETS.md`); premature to generalize before a second
  one is proposed, per the no-speculative-abstraction rule.

## 4. Boundary

- No `app/core/**` change.
- Single new choke-point function in `app/ops/ops_config.py`; every existing
  call site (`app/main.py`, `app/ops/auth.py`) is unchanged and unaware of
  the new precedence.
- No test opens `/etc/rmt/operator_tokens.secret` or any real credential —
  `tmp_path` + `monkeypatch.setenv("CREDENTIALS_DIRECTORY", ...)` throughout.
- Token rotation itself (owner-executed, not this session) touches only
  `/etc/rmt/operator_tokens.secret` and triggers one `systemctl restart` —
  no other live-host state changes.

## 5. Done when

- `docs/RMT_ABOVE_CORE_ROADMAP.md` T0-5 (and S4/S3/S5 individually) show
  `DONE`, cross-referenced to `docs/RMT_PRODUCTION_READINESS.md`.
- `operator_tokens()` prefers `$CREDENTIALS_DIRECTORY/RMT_OPERATOR_TOKENS`;
  falls back to the env var when absent; existing behavior unchanged when
  `$CREDENTIALS_DIRECTORY` is unset (the common case for tests / local dev).
- `docs/operations/SECRETS.md` records the exposure, the fix, and the
  corrected claim.
- Full backend suite green; `ruff check .` clean; no `app/core/**` diff.
- (Owner action, tracked but not executed by this session) the two exposed
  tokens rotated; the live deployment migrated to the new `auth.conf` +
  `/etc/rmt/operator_tokens.secret` layout.

## 6. Tests

- `test_credentials_directory_takes_precedence` — a `tmp_path` credential
  file wins over a conflicting env var.
- `test_credentials_directory_missing_file_falls_back_to_env` —
  `$CREDENTIALS_DIRECTORY` set but the file absent still reads the env var
  (never a hard failure — matches every other above-Core store's fail-open
  posture).
- `test_no_credentials_directory_uses_env` — regression: unchanged behavior
  when `$CREDENTIALS_DIRECTORY` is unset (every existing test in the suite
  implicitly exercises this path already; this test names it explicitly).

## 7. Validation plan

- New tests pass; `app/ops/testing/test_auth.py` full file green (35 total:
  32 baseline + 3 new); full backend suite green.
- `ruff check .` clean.
- Live check (owner-executed, this session cannot `sudo`): after migrating
  `auth.conf` to `LoadCredential=` and restarting, `systemctl show -p
  LoadCredential rmt-control-center.service` shows only the credential name
  and file *path* — never file content — closing the exposure this proposal
  was written to fix.
