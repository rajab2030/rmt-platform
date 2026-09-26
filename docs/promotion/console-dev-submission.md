# Console.dev submission (email draft)

Drafted 2026-09-26, per the suggested action in `docs/GROWTH_TRACKING.md`
(2026-09-21 entry). This is copy only, not evidence that it was sent.

The `https://console.dev/submit` form referenced in the growth log returns
404 as of 2026-09-26, and `https://console.dev/selection-criteria` blocks
requests from this host (HTTP 403), so the criteria could not be checked
from here. The only submission route visible on the site is the contact
address. Read the selection-criteria page in a normal browser before sending
and trim or adjust the email if anything below conflicts with it.

**To:** hello@console.dev
**Subject:** Tool suggestion: RMT Platform — policy checks, approval holds, and signed evidence for AI-agent actions

## Body

Hi Console team,

I'd like to suggest RMT Platform for review:
https://github.com/rajab2030/rmt-platform

RMT Platform is an open-source governance layer that sits between an AI
agent and the tools it calls. Every consequential action the agent proposes
goes through one lifecycle before it is allowed to run: a policy check, risk
classification, an approval hold where required, execution, post-execution
verification, and a durable evidence record.

What might interest your readers:

- **Agent Governance Gateway**: agents get scoped grants and can't reach an
  execution adapter without passing policy, risk, and authorization first.
- **Approval holds**: high-risk actions wait for a human decision instead
  of failing or silently running.
- **Signed evidence export**: any governed action can be exported as an
  HMAC-SHA256-signed bundle and verified offline with a small stdlib-only
  script. No running service or database access is needed.
- **Disabled by default**: every capability is opt-in.

Stack: Python 3.12 / FastAPI backend, React + TypeScript frontend,
self-hosted (systemd + Caddy). It's a solo project, free, and
MIT-licensed.

Recorded walkthrough (an agent proposing a Git tag, held for approval, then
executed and verified): https://rajab2030.github.io/rmt-platform/agent-action-audit-trail.html

Thanks for considering it.

https://github.com/rajab2030

## Notes before sending

- Sign the email with your own name; the draft ends with the GitHub profile
  link only.
