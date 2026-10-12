# Growth Tracking

Automated weekly log of GitHub visibility/engagement stats for this repo,
appended by a scheduled Claude Code job. Each entry is a snapshot plus
week-over-week deltas versus the prior entry (first entry has no prior
baseline) and 1-2 concrete suggested actions for the human owner to take
outside GitHub.

## 2026-09-21

**Repo:** rajab2030/rmt-platform
**Description:** Policy checks, approval holds, and execution evidence for AI-agent actions. Includes a local Git-tag walkthrough.
**Last push:** 2026-09-20T18:44:17Z

| Metric | Value |
|---|---|
| Stars | 0 |
| Forks | 2 |
| Topics | agent-governance, ai-agents, ai-governance, audit-trail, control-plane, devops-automation, homelab, llm-agents, policy-engine, risk-management (all 10 expected topics present) |

Traffic stats (views/clones/referrers/popular paths) were **not available this
run** — the `gh` CLI is not installed in this environment and the connected
GitHub MCP server has no traffic-API tool, so `traffic/views`, `traffic/clones`,
`traffic/popular/referrers`, and `traffic/popular/paths` could not be pulled.
Only repo metadata (stars/forks/topics/description) reachable through the MCP
server's `search_repositories` tool is logged this week. If this gap persists,
consider giving the automation direct `gh` access so traffic data can be
tracked going forward.

**Deltas vs. prior entry:** none — this is the first tracked entry (baseline).

**Suggested next actions (outside GitHub):**

1. **Write a short technical post** (dev.to or Hashnode) about the
   evidence export/attestation bundles feature just shipped this week
   (RMT-CAP-11 — see `docs/RMT_CAPABILITIES_EVIDENCE.md` and the `feat:
   implement RMT-CAP-11 evidence export/attestation bundles` commit).
   Frame it around the concrete hook: "what does an audit trail for an
   AI agent's actions actually look like?" and link the existing
   Git-tag walkthrough GIF/transcript already in the README
   (`docs/assets/agent-governance-demo.md`) as a live example rather than
   slides.
2. **Submit the project to Console.dev's tools directory**
   (https://console.dev/submit) — it's a curated engineering-tools
   newsletter/directory with good fit for the `policy-engine` /
   `control-plane` / `ai-governance` angle, and submission needs no
   credentials beyond a public form.

## 2026-09-28

**Repo:** rajab2030/rmt-platform
**Description:** Policy checks, approval holds, and execution evidence for AI-agent actions. Includes a local Git-tag walkthrough.
**Last push:** 2026-09-26T00:53:25Z

| Metric | Value |
|---|---|
| Stars | 0 |
| Forks | 2 |
| Topics | agent-governance, ai-agents, ai-governance, audit-trail, control-plane, devops-automation, homelab, llm-agents, policy-engine, risk-management (all 10 expected topics present) |

Traffic stats (views/clones/referrers/popular paths) were again **not
available this run** — same gap as last week: no `gh` CLI and no
traffic-API tool on the connected GitHub MCP server. Only repo metadata
reachable through `search_repositories` is logged.

**Deltas vs. prior entry (2026-09-21):**

- Stars: 0 → 0 (no change)
- Forks: 2 → 2 (no change)
- Unique cloners / unique visitors: not computable — traffic data still
  unavailable both weeks.

Notably, both of last week's suggested actions were already acted on since
the last entry: `docs/promotion/technical-post-evidence-attestation.md`
(added 2026-09-26) and `docs/promotion/console-dev-submission.md` (added
2026-09-26) are finished drafts now sitting in the repo. Neither has
produced a visible star/fork bump yet, consistent with drafts that haven't
been published externally yet.

**Suggested next actions (outside GitHub):**

1. **Actually publish the two drafts already written** — post
   `docs/promotion/technical-post-evidence-attestation.md` to dev.to (or
   Hashnode), and send `docs/promotion/console-dev-submission.md` to
   Console.dev's submission form (https://console.dev/submit). Both pieces
   are finished; the writing is done, only the posting/sending is left, and
   that's the single highest-leverage action available right now.
2. **Submit a "Show HN" post** on Hacker News (https://news.ycombinator.com/submit)
   pointing at the repo, framed around the `experiments/` MCR 2.0 banking
   risk-control experiment shipped 2026-09-20 (tiered per-counterparty
   exposure/concentration caps, velocity limiting, sanctions screening, and
   an `attack_agent.py` proving 16 boundary/policy checks against a live
   stack with real accumulated ledger state) as the concrete, unusual
   technical hook — link the README's Git-tag walkthrough GIF as the "here's
   it actually running" proof rather than just prose.

## 2026-10-05

**Repo:** rajab2030/rmt-platform
**Description:** Policy checks, approval holds, and execution evidence for AI-agent actions. Includes a local Git-tag walkthrough.
**Last push:** 2026-10-05T08:43:54Z

| Metric | Value |
|---|---|
| Stars | 0 |
| Forks | 2 |
| Topics | agent-governance, ai-agents, ai-governance, audit-trail, control-plane, devops-automation, homelab, llm-agents, policy-engine, risk-management (all 10 expected topics present) |

Traffic stats (views/clones/referrers/popular paths) were again **not
available this run** — same persistent gap: no `gh` CLI and no traffic-API
tool on the connected GitHub MCP server (confirmed again this week; the MCP
server exposes repo/PR/issue/commit/file tools but nothing under
`traffic/*`). Only repo metadata reachable through `search_repositories` is
logged. This gap has now held for three consecutive weeks with no change in
environment capability.

**Deltas vs. prior entry (2026-09-28):**

- Stars: 0 → 0 (no change)
- Forks: 2 → 2 (no change)
- Unique cloners / unique visitors: not computable — traffic data still
  unavailable all three weeks.

The repo itself moved a lot this week even though stars/forks didn't: PRs #6,
#7 and #8 merged today (2026-10-05), shipping a genuine one-command local
trial — `docker compose run --rm showcase` now builds and runs the full
governed-action walkthrough with zero setup (no Python, no manual venv, no
LLM, no secrets) — plus a new plain-language `GETTING_STARTED.md` and a
reworked frontend design system. This removes what was probably the biggest
friction point for a casual visitor: previously trying RMT meant a Python
venv and manual steps. None of last week's two suggestions (publishing the
dev.to draft / Console.dev submission, or a Show HN post) show any visible
effect yet in repo-observable signals (stars/forks still flat) — but that's
expected if they haven't been posted externally yet, which this automation
has no way to verify from inside GitHub.

**Suggested next actions (outside GitHub):**

1. **Post to r/selfhosted** (https://www.reddit.com/r/selfhosted/submit) now
   that there's a true one-command Docker trial to point at — this is new as
   of this week and wasn't true when earlier suggestions were written.
   r/selfhosted's audience specifically values "clone it, run one command, no
   cloud account" and the repo already carries the `homelab` topic and a live
   homelab domain to back it up. Suggested framing: "I built a governance
   gate that holds risky actions (yours or an AI agent's) for approval before
   they run — try it with `docker compose run --rm showcase`." Link straight
   to the Getting Started guide, not just the README.
2. **Finish `docs/promotion/why-i-built-rmt.md` before posting it anywhere.**
   It's a third drafted promotion piece (alongside the two from last week)
   but unlike those it still has unfilled `[OWNER: ...]` placeholders for
   personal facts this automation can't supply — it isn't publishable as-is.
   Once the owner fills those in, Indie Hackers
   (https://www.indiehackers.com/post) is a venue not yet tried: its
   "building in public" format fits a first-person origin story better than
   dev.to or Show HN, which are already earmarked for the more technical
   pieces.

## 2026-10-12

**Repo:** rajab2030/rmt-platform
**Description:** Policy checks, approval holds, and execution evidence for AI-agent actions. Includes a local Git-tag walkthrough.
**Last push:** 2026-10-11T13:21:53Z

| Metric | Value |
|---|---|
| Stars | 0 |
| Forks | 2 |
| Topics | agent-governance, ai-agents, ai-governance, audit-trail, control-plane, devops-automation, homelab, llm-agents, policy-engine, risk-management (all 10 expected topics present) |

Traffic data was **finally reachable this run** — `gh api` worked directly
against `/traffic/views`, `/traffic/clones`, `/traffic/popular/referrers`,
and `/traffic/popular/paths` (the prior three weeks' blocker, a missing
`gh` CLI / traffic-API tool, is resolved; the GitHub MCP server's
`get_me`/`search_repositories` tools still have no traffic endpoints, but
`gh api` itself is now usable from this environment). GitHub's traffic API
only reports a trailing 14-day window, so these are 2026-09-28 through
2026-10-11 totals, not since-last-entry totals:

| Metric (trailing 14 days) | Value |
|---|---|
| Views | 2 (1 unique visitor) |
| Clones | 271 (117 unique cloners) |
| Top referrers | none recorded |
| Top popular path | `/rajab2030/rmt-platform` ("Overview"), 2 views / 1 unique |

**Deltas vs. prior entry (2026-10-05):**

- Stars: 0 → 0 (no change)
- Forks: 2 → 2 (no change)
- Unique cloners / unique visitors: not comparable to prior entries —
  this is the first week traffic data was actually available, so there is
  no like-for-like baseline yet. Next week's entry will be the first with a
  real week-over-week traffic delta.

Note on the clone number: 271 clones / 117 unique cloners over two weeks is
large relative to 0 stars and no recorded referrers. That pattern (high
clones, no stars, no referrer signal) is consistent with CI/bot/mirror
traffic (e.g. package indexers or dependency scanners cloning the repo)
rather than organic human interest, and shouldn't be read as a sign of
traction on its own — worth sanity-checking against any CI or bot activity
the owner knows about, but not something this automation can distinguish
further from GitHub's API alone.

On the repo side, `RMT-CAP-13 slice 1` shipped 2026-10-11: a read-only,
opt-in "evidence-grounded incident explainer" (`app/reasoning/`) that
generates an advisory explanation of a governed action where every claim
must cite an evidence record (uncited claims are dropped), gated behind
`RMT_REASONING_ENABLED` and operator auth, with a new "Explain this action"
card in the governed console frontend. It never touches `app/core` or any
execution path. Dependabot was also turned on this week (pip/npm/actions/
docker/compose version updates).

**Suggested next actions (outside GitHub):**

1. **Write a short piece specifically about the incident-explainer feature**
   (`RMT-CAP-13`, see `docs/RMT_CAP_13_PROPOSAL.md`) framed around the
   concrete LLM-safety angle: "how do you let an LLM explain a governance
   decision without letting it hallucinate the evidence?" — the
   cite-or-drop validation in `app/reasoning/validate.py` is a specific,
   demonstrable mechanism (not just a claim) that would land well on a
   venue like Hacker News or r/LocalLLaMA, both audiences that care about
   LLM-output grounding specifically rather than governance/DevOps framing
   used in earlier suggestions.
2. **Open a GitHub Discussion post explaining the clone-traffic anomaly
   investigation** (271 clones / 0 stars this window) as a short public
   note — even a one-paragraph "noticed higher-than-expected clone traffic,
   still figuring out the source" is a low-effort way to signal the repo is
   actively watched/maintained, and the repo already links
   `/discussions` from the README front matter.
