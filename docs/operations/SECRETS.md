# RMT — Secrets Management

RMT-PROD **P2 / S6**. Above-Core / operational.

## Current state (2026-09-12)

The running RMT platform holds **one** sensitive value: the operator token map
(S1). It has **no** outbound credential — the only external dependency is a
local Ollama endpoint on the same host, which takes no API key.

## Correction (T0-5, 2026-09-12): the pre-2026-09-12 pattern had a live gap

The original pattern (below, superseded) put the token list in a
root-owned-`0600` `Environment=` drop-in and reasoned that "the `rmt-lab`
service user cannot read it." That's true of the **file**, but not of the
**resolved value**: `systemctl show -p Environment
rmt-control-center.service` prints a unit's plain environment — including
anything set via `Environment=` in a drop-in — to **any local user**, not
just root or the service's own user. File permissions on the drop-in never
protected against this; it was found live, exposing the two production
operator tokens, which were rotated immediately once found. See
`docs/RMT_T0_5_PROPOSAL.md` and `docs/RMT_CAPABILITIES_EVIDENCE.md`
§"T0-5" for the full record.

## The standing pattern (current)

The operator token list is a **systemd credential**
(`LoadCredential=RMT_OPERATOR_TOKENS:/etc/rmt-control-center/operator_tokens.secret` in
`auth.conf`) — `systemctl show -p LoadCredential` exposes only the source
*path* the same way `Environment=` exposed values, never the file's content:

- secret file: `/etc/rmt-control-center/operator_tokens.secret`, mode **`0600`**, owner
  `root`, outside git entirely (not even a template — created fresh per
  deployment, `DEPLOY.md` §1.2)
- the drop-in itself (`auth.conf`) holds **no secret** and is safe to commit
  verbatim from `deploy/systemd/auth.conf.example` — it only names the
  credential path
- `app/ops/ops_config.py::_operator_tokens_raw()` reads
  `$CREDENTIALS_DIRECTORY/RMT_OPERATOR_TOKENS` (systemd sets
  `$CREDENTIALS_DIRECTORY` automatically for a unit using `LoadCredential=`)
  in preference to the `RMT_OPERATOR_TOKENS` env var, which remains a
  fallback for local dev / tests / non-systemd runs only
- rotation = overwrite the secret file + restart (no `daemon-reload` needed —
  the unit/drop-in content didn't change) (`DEPLOY.md` §4)

This closes the gap above and is adequate for the current single-host,
single-trusted-operator posture (threat model (b) in
`docs/RMT_PRODUCTION_READINESS.md` §2).

## Required before ANY new credential

A model API key, an authenticated notification sink (`RMT_NOTIFY_WEBHOOK_URL`
with a bearer token), an IdP client secret (P-D), a cloud/K8s adapter
credential — **none may be introduced** until one of these is in place:

1. **`systemd` credentials** (`LoadCredential=` / `systemd-creds encrypt`) —
   **done for `RMT_OPERATOR_TOKENS`, T0-5, 2026-09-12** (above); the same
   `$CREDENTIALS_DIRECTORY`-first pattern extends directly to any future
   credential.
2. **`sops` + `age`** — if secrets need to live in the repo (encrypted) for
   reproducible rebuilds (R3). Decrypt in `rmt-rebuild.sh` to a `0600` drop-in.
3. **A real vault** (HashiCorp Vault, cloud secret manager) — only if the
   deployment moves to multi-user / internet-reachable (threat model (c)),
   alongside the P-D IAM work.

Whichever is chosen, the rules are fixed:

- no secret in the repo in cleartext, in a world-readable file, in a process
  argument (`ps` visible), or in a log line;
- every secret reachable only by `root` and the unit — **and note that
  `systemctl show` reads a unit's plain `Environment=`, so "reachable only by
  root and the unit" requires `LoadCredential=`, not `Environment=`, for
  anything sensitive;**
- rotation is a documented, single-command-ish step;
- the R3 rebuild path can restore or re-provision every secret.

## Disposition

**S6 → READY.** `RMT_OPERATOR_TOKENS`, the one credential the platform holds,
is now on the `LoadCredential=` pattern (T0-5, 2026-09-12). The same pattern
is pre-approved and ready to reuse the moment a new credentialed dependency
is proposed.
