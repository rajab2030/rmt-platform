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
