# Govern Claude Code shell commands with RMT (RMT-CAP-10)

A Claude Code `PreToolUse` hook that sends every Bash command to RMT before it
runs. Commands that match a short list of risky patterns are held until a
person approves or rejects them. Everything else runs without delay.

You don't need to understand RMT's Core to use it: the hook is one
standard-library Python file, and the backend runs from the
[quickstart](../../quickstart/README.md).

## What gets held

| Rule | Risk | Example |
|---|---|---|
| `git-force-push` | high | `git push --force` |
| `git-hard-reset` | high | `git reset --hard` |
| `recursive-delete` | high | `rm -rf build/` (also matches `git rm -r`) |
| `git-clean-force` | medium | `git clean -fd` |
| `sudo` | medium | `sudo …` |
| `service-restart` | medium | `systemctl restart …` |

The patterns are defined in
[`risk_rules.py`](../../projects/homelab-control-center/backend/app/coding_agent/risk_rules.py).
Each hold carries a review built only from checkable evidence: the matched
rule, your recent decisions on similar commands, and read-only Git checks
(uncommitted changes, whether a force-push would discard remote commits). No
LLM opinion is used as evidence.

## Limits — read first

- **Fails open.** If RMT is unreachable, misconfigured, or doesn't answer
  in time, the command **runs**, with a warning on stderr. That includes the
  backend stopping while a command is waiting for a decision. This is
  deliberate (a guard that can brick the tool it guards is worse), but it
  means this is a safety net for a cooperating agent, not a security
  boundary.
- **Only the listed patterns.** Anything else runs without review, including
  a risky command written in a way the patterns don't match.
- **Only commands that go through the hook.** It governs Claude Code's Bash
  tool in projects where you install it. File edits, other tools, and anything
  you run yourself aren't covered.
- **Separate from Core's governed path.** These holds are an above-Core
  system; they don't go through `execute_governed_action`, and they have no
  expiry: an undecided hold stays pending.
- **Local demo settings.** With the quickstart backend, authentication is off,
  so anyone who can reach `127.0.0.1:8000` can decide a hold, and every
  decision is recorded as `local-dev`.

## Install

**1. Start RMT with the coding-agent surface on.** From a clone of this
repository:

```bash
RMT_CODING_AGENT_ENABLED=true docker compose up -d rmt
```

The backend in a container can't see your project's files, so the Git
checks are left out of the evidence (they're omitted, never guessed). To
include them, run the backend directly on your machine instead (see
[`docs/operations/CONFIG.md`](../../docs/operations/CONFIG.md)) with
`RMT_CODING_AGENT_ENABLED=true`.

**2. Copy the hook into the project you want to govern:**

```bash
mkdir -p /path/to/your-project/.claude/hooks
cp .claude/hooks/coding_agent_guard.py /path/to/your-project/.claude/hooks/
chmod +x /path/to/your-project/.claude/hooks/coding_agent_guard.py
```

**3. Register it** in `/path/to/your-project/.claude/settings.json` (merge
with any hooks you already have):

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PROJECT_DIR}/.claude/hooks/coding_agent_guard.py",
            "timeout": 1860
          }
        ]
      }
    ]
  }
}
```

Claude Code kills a hook at `timeout` seconds; keep it above the hook's own
poll timeout (1800 s by default).

**4. Check it.** In a Claude Code session in that project, ask for a harmless
command (`git status`): it runs straight away. Then ask for one that matches a
rule; the session waits and prints a `hold_id`.

## Decide a hold

```bash
# list pending holds
curl -s 'http://127.0.0.1:8000/coding-agent/holds?status=pending'

# approve (or "approved": false to reject)
curl -s -X POST http://127.0.0.1:8000/coding-agent/decide \
  -H 'Content-Type: application/json' \
  -d '{"hold_id": "<hold_id>", "approved": true}'
```

An approved command runs; a rejected one is blocked and Claude Code sees the
reason.

## Configuration

Set in the environment Claude Code runs in:

| Variable | Default | Meaning |
|---|---|---|
| `RMT_CODING_AGENT_URL` | `http://127.0.0.1:8000` | RMT backend URL |
| `RMT_CODING_AGENT_TOKEN` | *(unset)* | Operator bearer token; needed only when the backend has authentication on |
| `RMT_CODING_AGENT_POLL_TIMEOUT_S` | `1800` | How long to wait for a decision before failing open |

## More

- [Capability record and live exercises](../../docs/RMT_CAPABILITIES_EVIDENCE.md)
  (section "RMT-CAP-10")
- [Proposal and design rationale](../../docs/RMT_CAP_10_PROPOSAL.md)
