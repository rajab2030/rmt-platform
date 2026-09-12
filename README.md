# RMT Platform

**RMT = Risk-Mitigated Transactions.** RMT is a general-purpose intelligent
control, execution, and governance platform, not a specialized application.
The Core is domain-agnostic: it
governs services, applications, systems, and AI agents under one common
lifecycle — **Understand → Decide → Govern → Authorize → Execute → Verify →
Learn** — without embedding the rules of any particular domain. See
[`docs/RMT_MASTER_DEFINITION.md`](docs/RMT_MASTER_DEFINITION.md) for the
authoritative identity and purpose statement.

The frozen Core lives at `projects/homelab-control-center/` (validated at
commit `46a4441`; C01–C07 CLOSED, no C08). Domains built on top of it so far:
homelab operations (the platform's first, low-stakes proving ground) and a
git-tag Agent Governance Gateway (an AI agent proposes an action, RMT governs
it end-to-end) — proof that the frozen Core generalizes past its original
domain.

## Start here

- [`RMT_CONTEXT.md`](RMT_CONTEXT.md) — stable project brain / bootstrap
  context: identity, lifecycle, current status, next action.
- [`docs/RMT_MASTER_DEFINITION.md`](docs/RMT_MASTER_DEFINITION.md) — top
  architecture authority: identity, purpose, Core/domain boundary.
- [`docs/RMT_GUARANTEES.md`](docs/RMT_GUARANTEES.md) — what each lifecycle stage
  does and does **not** assert, in plain language.
- [`docs/RMT_THREAT_MODEL.md`](docs/RMT_THREAT_MODEL.md) — assets, trust
  boundary, assumed adversary, attack surface, residual risks.
- [`docs/operations/AGENT_API.md`](docs/operations/AGENT_API.md) — the
  integration guide for an external agent/caller: full lifecycle, decision
  vocabulary, the evidence-receipt contract, what's guaranteed vs. not.
- [`docs/operations/METRICS.md`](docs/operations/METRICS.md) — every
  `/metrics` signal, the PromQL for decisions/min and approval latency, and
  where RMT's own alerting already lives.
- [`docs/RMT_FROZEN_CORE_DEBT.md`](docs/RMT_FROZEN_CORE_DEBT.md) — every
  recorded frozen-Core gap, its compensating control, and its trigger to
  revisit.
- [`docs/RMT_CAPABILITIES_EVIDENCE.md`](docs/RMT_CAPABILITIES_EVIDENCE.md) —
  the evidence ledger for every capability built on the Core, including live
  exercises.
- [`docs/RMT_IMPROVEMENT_ROADMAP.md`](docs/RMT_IMPROVEMENT_ROADMAP.md) —
  prioritized improvements to the platform as it stands.

## Homelab domain (the platform's first proving ground)

Before RMT governed anything else, it was built and validated against a
real, low-stakes domain: this host's own homelab services. That domain is
still live and still governed by RMT — restarts, health checks, and remediation
all go through the same governed lifecycle as everything else — but it is
the platform's first proof, not its identity.

- Host: Windows + VMware Workstation, guest Ubuntu Server 22.04 LTS, Docker.
- Live, governed services: Portainer, Uptime Kuma, Dozzle.
- All Docker compose files and scripts are version controlled with Git;
  Docker volumes are backed up separately.
