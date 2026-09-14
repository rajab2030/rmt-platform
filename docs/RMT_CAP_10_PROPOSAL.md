# RMT-CAP-10 — Coding-Agent Command Governance (MCR: Claude Code as a governed child) — Proposal

**Status: APPROVED 2026-09-13 (owner, in-session — "write it up as a proposal
doc and start implementing it on you right away").** Per the platform's
standing working method this record exists so the decision and its boundary
are on the record before code lands, even though approval and implementation
happen in the same session this time.

**Classification:** Above-Core / new domain. **No C08. No frozen Core
change. No reopening of C01–C07.** Confined to a new `app/coding_agent/`
package + one `app/main.py` registration + a project-scoped Claude Code hook
(`.claude/settings.json` + a hook script) in this repository only. Does not
touch the homelab/git/agent domains or the governed mutation path they use.

---

## 1. Objective

Every above-Core domain so far (Homelab Docker ops, the git-tag Agent
Governance Gateway) governs some *external* system. This capability turns the
same MCR pattern — one supervisor, one evidence trail, one approval gate, in
front of an independent child system — on **Claude Code itself**: before a
Claude Code session in this repository runs a command matching a small,
explicit list of risky patterns (force-push, hard reset, recursive delete,
sudo, service restarts, …), it is held for a human decision instead of
executing immediately.

**The specific requirement that shapes this proposal (owner, this session):**
the hold must never be a blind yes/no. It must carry an explanation the human
can actually evaluate, and that explanation must be **strictly real,
checkable evidence — never an LLM opinion standing in as evidence.** A
recommendation is only as trustworthy as what it cites.

## 2. What already exists (reused, not rebuilt)

| Piece | Location | Role here |
|---|---|---|
| `DurableStore` extension point | `app/core/intelligence/durable_store.py` | New table (`coding_agent_holds`) in the same shared evidence DB, same pattern `app/agent/authority.py`'s grants table already uses. No `app/core/**` change. |
| `require_operator` + `RMT_OPERATOR_TOKENS` | `app/ops/auth.py` | Every new route is operator-authenticated, same as every other mutation-adjacent route. |
| Opt-in, disabled-by-default flag pattern | `RMT_HOMELAB_LOOP_ENABLED`, `RMT_AGENT_ENABLED`, `RMT_OPS_EVIDENCE_ENABLED` | This domain gets its own `RMT_CODING_AGENT_ENABLED` (default **False**), same shape. |
| Governed Operations Console | `frontend/src/components/GovernedConsole.tsx` (RMT-CAP-09) | Not extended in this slice (kept to backend + hook so the first version is small and provable); a console tab is natural fast-follow, not built here. |
| Claude Code `PreToolUse` hooks | `.claude/settings.json` (project-scoped) | The mechanism that lets an external process (this platform) see a proposed tool call before it runs and block on a decision. |

## 3. Design

### 3a. Risk classification (deterministic, not an LLM)

`app/coding_agent/risk_rules.py` — a small, explicit, reviewable pattern list.
A command matching **none** of these is never intercepted at all (auto-allow,
zero overhead, zero false positives on the other 99% of commands):

| Rule | Pattern (illustrative) | Risk | Why |
|---|---|---|---|
| `git-force-push` | `git push ... --force` / `-f` | high | irreversible remote history rewrite |
| `git-hard-reset` | `git reset --hard` | high | discards local work irreversibly |
| `git-clean-force` | `git clean -f...` | medium | irreversibly deletes untracked files |
| `recursive-delete` | `rm -rf ...` (outside `/tmp`, a scratchpad dir) | high | unrecoverable deletion |
| `sudo` | `sudo ...` | medium | elevated privilege |
| `service-restart` | `systemctl stop\|restart ...` | medium | affects a running service |

Starting list only — adding a rule is a one-line, reviewable diff, same
spirit as `REMEDIATION_POLICY`.

### 3b. Evidence — exactly three sources, nothing else counted

`app/coding_agent/review.py` builds a list of `EvidenceItem {source, claim,
leans: approve|reject|neutral}` from:

1. **The rule that matched** (`risk_rules.py`) — always present when a hold
   exists; `leans=reject` for `high`, `neutral` for `medium`.
2. **History** (`app/coding_agent/history.py`) — prior holds for the *same
   rule*, tallied approved vs. rejected from the durable store. Present only
   when history exists; absence of history is never treated as either kind of
   evidence (fail-open honesty, same discipline as `evidence_chain.py`).
3. **A situational check** (`app/coding_agent/situational.py`) — cheap,
   read-only, git-specific for v1: uncommitted changes present
   (`git status --porcelain`), and for a force-push specifically, whether the
   remote has commits the operation would discard
   (`git rev-list --left-right --count`). Present only when determinable
   (real git repo, real upstream); never guessed.

**Verdict:** `reject` if any evidence item leans `reject`; else `approve` if
any leans `approve` and none lean `reject`; else `reject` (the safe default
when there is no real signal either way — absence of evidence is not evidence
of safety). The reviewer never adds a fourth, opinion-based item; if a source
has nothing to say, it contributes nothing, not a filler claim.

### 3c. Hold + API

`app/coding_agent/store.py` (`CommandHoldStorage(DurableStore)`, table
`coding_agent_holds`) persists `{hold_id, command, cwd, reason, session_id,
risk_rule, risk_level, evidence, verdict, status, created_at, decided_at,
decided_by}`. Routes (`app/coding_agent/api.py`, `require_operator` on all):

- `POST /coding-agent/propose` `{command, cwd, reason, session_id}` → the
  hook's call. No rule match → `{"decision": "auto_allow"}` (no hold created,
  no evidence computed — zero cost on the common path). A match → hold
  created, `{"decision": "hold", "hold_id", "review"}` returned.
- `GET /coding-agent/holds?status=pending` — for the hook's poll and manual
  inspection (a console tab can call the same route later).
- `GET /coding-agent/holds/{hold_id}` — single-hold poll.
- `POST /coding-agent/decide` `{hold_id, approved}` — the human decision;
  `decided_by` comes from the authenticated operator, not the request body
  (same pattern S1/S2-lite already established for `/approve`).

### 3d. The hook (Claude Code side)

A `PreToolUse` hook scoped to **this repository only**
(`.claude/settings.json` at the repo root, not the user's global config),
matching the `Bash` tool: extracts the proposed command, calls
`POST /coding-agent/propose`. `auto_allow` → the command runs immediately,
unchanged from today. `hold` → the hook polls until a decision or a bounded
timeout, then allows or blocks accordingly.

**Fail-open by design, not by accident:** if the backend is unreachable, or
the poll times out, the hook allows the command through and logs a warning,
rather than blocking Claude Code's ability to do anything (including fixing
the hook itself) indefinitely. This mirrors `evidence_chain.py`'s own
fail-open discipline — a governance layer that can brick the thing it
governs is worse than one that occasionally lets a command through unreviewed
while loudly saying so.

## 4. Explicitly OUT of scope (this slice)

- **No console UI tab** — approve/reject via `curl`/API for now, same as this
  session's own CAP-09 live walkthrough; a console tab is a natural, small
  fast-follow once the mechanism is proven.
- **No LLM anywhere in the review path.** The reviewer only tallies the three
  evidence sources above; it does not phrase, summarize, or add judgment.
- **Not wired to the live `:8000` service by default** — validated first on
  an isolated dev instance in this session; whether to point the hook at a
  persistent, always-on instance is a separate, explicit owner decision once
  the mechanism is proven end-to-end.
- **No expansion of the risk-rule list beyond §3a** in this slice.
- **No `app/core/**` change; no change to the homelab/git/agent domains.**

## 5. Boundary

- No `app/core/**` change. New table via the existing `DurableStore`
  extension point, exactly as CAP-08 did for agent grants.
- Ships disabled (`RMT_CODING_AGENT_ENABLED=False`); the hook itself is
  scoped to this one repository's `.claude/settings.json`, not global.
- Fail-open on any backend/timeout failure — a broken governance layer must
  never be able to lock out the very tool it's meant to keep honest.
- Evidence is real or absent, never fabricated; the verdict is fully
  reconstructable from the evidence list shown alongside it.

## 6. Done when (Definition of Done)

- Full backend suite green, growing by the new package's tests; `import
  app.main` clean; zero `app/core/**` diff.
- A command matching no rule passes through with no observable change.
- A command matching a rule is held, with a `review` payload whose evidence
  items are each traceable to a real, checkable source — verified against a
  real git repo, not a mock.
- Approving a held command lets it proceed; rejecting blocks it; both
  observable end-to-end through the actual Claude Code hook, not just the API.
- The hook fails open (command proceeds, warning logged) when the backend is
  unreachable — verified, not assumed.

## 7. Tests

- `risk_rules.py` — each rule matches its intended commands and only those.
- `review.py` — evidence assembly and verdict logic for: no evidence (default
  reject), reject-leaning evidence present, approve-leaning evidence with no
  reject signal, mixed (reject wins).
- `store.py` / `api.py` — isolated store (never the real evidence DB); auth
  required on every route; `propose` auto-allows a non-matching command
  without creating a hold; `decide` updates status and `decided_by` from the
  authenticated operator, not the request body.

## 8. Validation plan

- Full backend suite green.
- Isolated dev instance (same discipline as every prior live exercise): a
  real repository, a real risky command, the actual hook script — not a
  simulation — proposed → held → evidence shown → approved via `curl` →
  command proceeds; a second command rejected → command blocked; a third
  with the backend stopped → fails open.

---

*Implementation follows immediately in this session per the owner's
instruction; this document is the record of what was authorized and why.*
