"""RMT-CAP-10 -- Coding-Agent Command Governance (above-Core).

MCR applied to Claude Code itself: a small set of risky shell-command
patterns are held for a human decision instead of executing immediately, via
a project-scoped ``PreToolUse`` hook that calls this package's API. Evidence
is strictly real and checkable -- a matched risk rule, prior history for that
rule, and a situational git check -- never an LLM opinion. No
``app/core/**`` change; no new mutation path; disabled by default
(``RMT_CODING_AGENT_ENABLED``). See ``docs/RMT_CAP_10_PROPOSAL.md``.
"""
