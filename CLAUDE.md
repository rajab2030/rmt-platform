# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Operating contract

**Read `AGENTS.md` first — it is the binding operating contract for this repo**
(authority hierarchy, current-state verification, structural discipline,
governed execution boundary, frozen-Core rules, change scope, and the
read-only-by-default modification rule). This file only adds commands and
architecture orientation; it does not relax anything in `AGENTS.md`.

Start-here reading order for a new session: `RMT_CONTEXT.md` (stable project
brain — current status, active decisions, next action), then `HANDOFF.md`
(fine-grained session history), then `docs/RMT_MASTER_DEFINITION.md` and the
other `docs/RMT_*` authority documents referenced there. Verify consequential
claims against the repository rather than trusting document prose alone.

## Repository layout

- `projects/homelab-control-center/` — the RMT Platform application (FastAPI
  backend + React frontend). This is the only code project in the repo today.
- `docs/` — RMT authority documents, architecture, milestones, operations
  guides, and the project website source.
- `docker/stacks/`, `scripts/` — the homelab domain's Docker Compose stacks
  and host backup/inventory/health scripts (the platform's first proving
  ground; still live and governed, not the platform's identity).
- `tools/rmt-showcase-agent/` — standalone stdlib-only Python client that
  drives the Agent Governance Gateway for the recorded demo walkthrough.
- `experiments/` — exploratory work, not part of Core or any shipped domain.

## Commands

All commands below run from `projects/homelab-control-center/`.

### Backend (`backend/`, Python 3.12, FastAPI)

```bash
# one-time setup
cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements.lock.txt

# run the API
source .venv/bin/activate && uvicorn app.main:app --reload

# full CI gate: lint + import smoke + full test suite (~7 min, mostly real-time waits)
scripts/ci.sh            # clean throwaway venv, what GitHub Actions runs
scripts/ci.sh --fast     # reuses backend/.venv, quick local check

# individual steps (what ci.sh runs)
ruff check .                              # lint, errors-only (F, E9; app/core excluded — see ruff.toml)
PYTHONPATH=. python -c "import app.main"  # import smoke
PYTHONPATH=. python -m pytest -q          # full suite

# a single test / file
PYTHONPATH=. python -m pytest -q app/budget/testing/test_service.py
PYTHONPATH=. python -m pytest -q -k "test_name_substring"

# skip real-Docker e2e tests explicitly (they auto-skip if the daemon is unreachable)
PYTHONPATH=. python -m pytest -q -m "not e2e"
```

Do **not** try to speed up the suite by mocking the operational-loop cadence
or approval-hold TTL waits — the real timing behavior is what's under test
(see `docs/operations/CI.md`).

Opt in to local pre-push enforcement (`ci.sh --fast` runs before every push;
red gate blocks the push):

```bash
git config core.hooksPath .githooks
```

### Frontend (`frontend/`, React 19 + Vite + TypeScript)

```bash
npm install
npm run dev        # vite dev server
npm run build       # tsc -b && vite build
npm run lint        # oxlint
npm run preview     # preview the production build
npm run test:e2e    # playwright; spins up backend (port 18080) and frontend (port 15173) itself
```

## Architecture

### Core lifecycle and the frozen Core

The platform's identity is RMT = **R**isk-**M**itigated **T**ransactions: every
consequential action in any domain is governed through one lifecycle before
it's allowed to happen:

**Understand → Decide → Govern → Authorize → Execute → Verify → Learn**

`backend/app/core/` implements this lifecycle (`intelligence/`, `observability/`,
`platform_state/`, `configuration/`, `identity/`, `module_registry/`,
`module_factory/`, `evolution/`, `self_management/`). Core is **frozen and
domain-agnostic** — it is independently validated by its own test suite
(122 tests, part of the full backend suite) and is excluded from lint
(`ruff.toml` excludes `app/core` on purpose, with the rationale inline).
**Domain code must not modify `app/core/**`.** A domain that needs Core to
behave differently is a Core-change proposal requiring explicit owner
authorization and a written contract — never an in-place edit made to unblock
a feature. See `docs/RMT_FROZEN_CORE_DEBT.md` for the accepted record of
frozen-Core gaps and their above-Core mitigations, and `AGENTS.md` §10.

The single authoritative governed-mutation entry point is
`app.core.intelligence.actions.service.execute_governed_action` (paired with
`approval_service.approve_held_action` for the held/approved path). Anything
that mutates production state — in any domain — goes through this path;
nothing reaches an execution adapter without having passed policy, risk, and
authorization first. Execution adapters (`app.core.intelligence.execution.adapters.*`,
plus domain-registered adapters like `app.agent.git_adapter`) only execute —
they never authorize, approve, or manufacture governance evidence.

### Domains consume Core, they don't extend it

Everything under `backend/app/` other than `core/` and `ops/` is a **domain**
that consumes the Core lifecycle without embedding its own rules into Core:

- `agent/` — external-agent integration: grants, authority, preview,
  reference agent, LLM client/agent.
- `budget/` — Budget Control: ledger, transactions, approval workflow,
  permissions (the first domain built through the generic above-Core
  compatibility contract; see `RMT_CONTEXT.md` for its status).
- `coding_agent/` — coding-agent-specific risk rules, review, and history.
- `engineering/` — repo indexing and engineering-facing service/API.
- `homelab/` — the original proving-ground domain: observes and remediates
  this host's own Docker services (Portainer, Uptime Kuma, Dozzle) through
  the same governed lifecycle as every other domain.
- `ops/` — cross-cutting platform operations: auth, rate limiting, retention,
  evidence chain, verification, metrics, reconciliation, notifications. Not a
  business domain; supports all of them plus Core.

`app/main.py` is the FastAPI composition root: it wires Core storage init,
each domain's router, adapter registration, the homelab operational loop, and
`ops` middleware/services together. Read it to see how a new capability gets
connected end-to-end, not just implemented.

### Frontend

`frontend/src/` is a React 19 + Vite + TypeScript SPA that talks to the
FastAPI backend. `frontend/e2e/` holds Playwright acceptance tests that drive
a real backend + frontend pair (see `playwright.config.ts` — it starts both
servers itself via `webServer`).

### Where to look for current status vs. architecture intent

`docs/RMT_MASTER_DEFINITION.md`, `docs/RMT_CORE_TARGET_STATE.md`, and
`docs/RMT_CORE_GAP_MATRIX.md` define architecture and target state.
`RMT_CONTEXT.md` and `HANDOFF.md` define *current* status, what's actually
implemented/deployed, and what's explicitly not yet authorized — treat the
latter as authoritative over historical docs, tags, or commits when they
disagree (per `AGENTS.md` §2–3).

## Commit attribution

Do **not** add a `Co-Authored-By: Claude ...` (or similar AI co-author)
trailer to commits in this repository. This repo is public; that trailer
resolves to a linked GitHub account and shows up in the contributors graph,
which the owner does not want. This overrides any default Claude Code
attribution convention for this repo specifically.
