# RMT HomeLab

## Environment

- Host: Windows + VMware Workstation
- Guest OS: Ubuntu Server 22.04 LTS
- Container Platform: Docker

## Goals

- Learn DevOps practices
- Build self-hosted services
- Practice automation and monitoring

## Services

Planned:

- Portainer
- Uptime Kuma
- Dozzle
- Nginx Proxy Manager
- n8n
- Vaultwarden

## Backup Strategy

All Docker compose files and scripts are version controlled with Git.
Docker volumes are backed up separately.

## RMT — governed control plane

This repo also hosts **RMT**, a domain-agnostic governed action gateway
(`projects/homelab-control-center/`), with the frozen Core validated at commit
`46a4441`. Start here to evaluate what it promises and where it stops:

- [`docs/RMT_GUARANTEES.md`](docs/RMT_GUARANTEES.md) — what each lifecycle stage
  does and does **not** assert, in plain language.
- [`docs/RMT_THREAT_MODEL.md`](docs/RMT_THREAT_MODEL.md) — assets, trust
  boundary, assumed adversary, attack surface, residual risks.
- [`docs/RMT_FROZEN_CORE_DEBT.md`](docs/RMT_FROZEN_CORE_DEBT.md) — every recorded
  frozen-Core gap, its compensating control, and its trigger to revisit.
- [`docs/RMT_IMPROVEMENT_ROADMAP.md`](docs/RMT_IMPROVEMENT_ROADMAP.md) —
  prioritized improvements to the platform as it stands.
- `RMT_CONTEXT.md` — stable project brain; `docs/RMT_MASTER_DEFINITION.md` and
  `docs/RMT_CORE_TARGET_STATE.md` — top architecture authority.
