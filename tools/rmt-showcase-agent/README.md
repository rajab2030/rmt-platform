# RMT Agent Governance Gateway — showcase

A standalone, dependency-free client (`rmt_showcase.py`, Python 3 stdlib
only) that demonstrates RMT's governed lifecycle end-to-end, in one command,
against a real RMT instance. It is **not** part of the RMT backend — it
imports nothing from it and only speaks HTTP, exactly as any real external
agent integrating with RMT would. It follows
[`docs/operations/AGENT_API.md`](../../docs/operations/AGENT_API.md) to the
letter; that document is the authoritative contract, this is a runnable
illustration of it.

## What it shows

Five acts, narrated as they happen, using the pre-existing git-tag domain
(RMT-CAP-06 — chosen because it needs nothing but a scratch git repo, no
homelab hardware, no Docker):

1. **Get a scoped, single-use grant.** Capability ≠ authority: the agent can
   *name* any operation, but may only act on the one it holds a grant for.
2. **Preview** the action — RMT's real predicted policy/risk/approval
   outcome, with zero side effects (no grant consumed, no hold created).
3. **Propose it for real.** Inspect the returned decision. Depending on policy,
   creation can be held for approval too; execution and verification outcomes
   are reported separately.
4. **Attempt to over-reach the same grant** (a destructive operation it was
   never granted). Refused *before governance even runs* — no policy call,
   no risk assessment, no evidence write.
5. **A separately granted removal proposal.** If policy holds it, the client
   prompts for approval and displays the resulting execution evidence.

This walkthrough uses one operator credential to grant, propose, and approve.
It does not demonstrate independent approver identities, despite the client's
older narration about self-approval. Approval is policy-dependent; an absent
verification result is not verified success. Closing stdin now aborts approval.
See the [recorded outcomes and limitations](../../docs/assets/agent-governance-demo.md).

Every line of output is a real response from your RMT instance. Nothing is
scripted or mocked — if your instance's policy classifies something
differently than the story above (e.g. a different risk tier), the script
narrates whatever actually happened instead of asserting a fixed script.

## Prerequisites

1. A running RMT instance (the backend in
   `projects/homelab-control-center/backend`) with:
   - `RMT_AGENT_ENABLED=true`
   - `RMT_AGENT_GIT_REPO_PATH=/path/to/a/scratch/git/repo` — **a throwaway
     repo you create for this demo**, e.g.:
     ```bash
     mkdir -p /tmp/rmt-showcase-repo && cd /tmp/rmt-showcase-repo
     git init -q && git config user.email demo@example.com \
       && git config user.name Demo && echo hi > f && git add f \
       && git commit -qm init
     ```
     The agent only ever sends RMT a *tag name* — never a filesystem path.
     The repo location is fixed server-side, by design (no path-injection
     surface). **Do not point this at a real repository you care about.**
   - An operator token in `RMT_OPERATOR_TOKENS` (see
     `docs/operations/CONFIG.md`), or `RMT_AUTH_ENABLED=false` for a purely
     local dev run.
2. Python 3.10+ (stdlib only — nothing to `pip install`).

Example: run a throwaway dev instance for this demo only (do **not** point
this at your production RMT deployment):

```bash
cd projects/homelab-control-center/backend
RMT_AGENT_ENABLED=true \
RMT_AGENT_GIT_REPO_PATH=/tmp/rmt-showcase-repo \
RMT_AUTH_ENABLED=false \
RMT_EVIDENCE_DB=/tmp/rmt-showcase-evidence.db \
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8099
```

## Run it

```bash
cd tools/rmt-showcase-agent
RMT_URL=http://127.0.0.1:8099 RMT_TOKEN=local-dev ./rmt_showcase.py
```

(With `RMT_AUTH_ENABLED=false`, any non-empty `RMT_TOKEN` value is accepted
and every action is attributed to `local-dev` in RMT's evidence — the same
local-dev escape hatch the backend itself documents.)

### Configuration

| Env var | Default | Meaning |
|---|---|---|
| `RMT_URL` | `http://127.0.0.1:8000` | Base URL of the RMT instance |
| `RMT_TOKEN` | *(required)* | Operator bearer token |
| `RMT_SHOWCASE_AGENT_ID` | `showcase-bot` | The `agent_id` this script proposes as |
| `RMT_SHOWCASE_TAG` | `showcase-<epoch>` | Tag name to create/remove — timestamped by default so re-runs never collide |

## Why this, and not something homelab-specific

The homelab domain (Docker/systemd) needs real hardware or containers a
stranger cloning this repo won't have. The git-tag domain needs nothing but
`git` and a scratch directory, so this script is runnable end-to-end by
someone with the backend already configured — while exercising the same
governed lifecycle (policy → risk → approval → authorization → execution →
verification → evidence) as every other domain RMT governs.

## See also

- `docs/operations/AGENT_API.md` — the full integration contract.
- `docs/RMT_GUARANTEES.md` / `docs/RMT_THREAT_MODEL.md` — what RMT promises
  and where it stops.
- `docs/RMT_CAPABILITIES_EVIDENCE.md` §"RMT-CAP-06" / §"RMT-CAP-07" — the
  live exercises this contract was originally proven against.
