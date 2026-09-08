# RMT — Secrets Management

RMT-PROD **P2 / S6**. Above-Core / operational.

## Current state (2026-09-08)

The running RMT platform holds **one** sensitive value: the operator token map
(`RMT_OPERATOR_TOKENS`, S1). It has **no** outbound credential — the only
external dependency is a local Ollama endpoint on the same host, which takes no
API key.

## The standing pattern

Until a credentialed dependency is added, secrets live in a **root-owned systemd
`EnvironmentFile` drop-in**:

- `/etc/systemd/system/rmt-control-center.service.d/auth.conf`
- mode **`0600`**, owner `root` — the `rmt-lab` service user cannot read it;
  systemd injects the values into the process environment at start
- template: `deploy/systemd/auth.conf.example` (committed); the populated file
  is **never** committed (`deploy/systemd/README.md`)
- rotation = edit the file + `daemon-reload` + restart (`DEPLOY.md` §4)
- `ops_config.py` reads every secret from the environment, dynamically, so a
  drop-in edit is the only step

This is adequate for the current single-host, single-trusted-operator posture
(threat model (b) in `docs/RMT_PRODUCTION_READINESS.md` §2).

## Required before ANY new credential

A model API key, an authenticated notification sink (`RMT_NOTIFY_WEBHOOK_URL`
with a bearer token), an IdP client secret (P-D), a cloud/K8s adapter
credential — **none may be introduced** until one of these is in place:

1. **`systemd` credentials** (`LoadCredential=` / `systemd-creds encrypt`) — the
   secret is stored encrypted, decrypted into `%d/<name>` for the unit only,
   never in the environment or the journal. Preferred: no new dependency, no
   new service. `ops_config.py` gains a `_cred_or_env()` helper that reads
   `$CREDENTIALS_DIRECTORY/<name>` first, falling back to the env var.
2. **`sops` + `age`** — if secrets need to live in the repo (encrypted) for
   reproducible rebuilds (R3). Decrypt in `rmt-rebuild.sh` to a `0600` drop-in.
3. **A real vault** (HashiCorp Vault, cloud secret manager) — only if the
   deployment moves to multi-user / internet-reachable (threat model (c)),
   alongside the P-D IAM work.

Whichever is chosen, the rules are fixed:

- no secret in the repo in cleartext, in a world-readable file, in a process
  argument (`ps` visible), or in a log line;
- every secret reachable only by `root` and the unit;
- rotation is a documented, single-command-ish step;
- the R3 rebuild path can restore or re-provision every secret.

## Disposition

**S6 → READY (by policy).** The pattern is defined and sufficient for the
current posture; item 1 above is the pre-agreed next step, scoped and ready to
implement the moment a credentialed dependency is proposed.
