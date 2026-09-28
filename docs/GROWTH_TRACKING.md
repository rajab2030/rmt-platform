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
