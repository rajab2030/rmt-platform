# RMT-C01 — Execution-Entrypoint Inventory and Mutation-Path Classification

## Authority

This document is acceptance evidence for **RMT-C01 — Governed Execution Boundary**
(see `docs/milestones/RMT-C01-Governed-Execution-Boundary.md`, §27 item 1 and 2).

It records the execution-entrypoint inventory and the classification of every
mutation-capable path in the current working tree, per C01 §8 and §16.

## Classification Legend

- **GOVERNED** — traverses the single authoritative governed lifecycle
  (Action -> Policy -> Risk -> Approval -> Authorization -> Execution).
- **ENFORCEMENT BOUNDARY** — the execution engine; blocks any request that does
  not carry a legitimate, valid authorization.
- **ADAPTER-ONLY** — reachable only through a registered adapter after the
  governed chain succeeds; not directly exposed to production callers.
- **READ-ONLY / DIAGNOSTIC** — does not mutate platform or managed state.

## Inventory

| # | Entrypoint | Location | Mutation capability | Classification | Notes |
|---|-----------|----------|---------------------|----------------|-------|
| 1 | `POST /execute` | `app/main.py` | start/stop/restart/create/remove | **GOVERNED** | Builds an `ActionRequest` and runs `execute_governed_action()`. No authorization is fabricated. |
| 2 | `POST /approve` | `app/main.py` | resumes a held governed action | **GOVERNED** | Calls `approve_held_action()`; only resumes a previously governed, held action. |
| 3 | `execute_decision()` | `app/core/intelligence/service.py` | governed execution from a decision | **GOVERNED** | Internal; delegates to `execute_governed_action()` (simulation adapter). Not exposed as a route. |
| 4 | `execute_governed_action()` | `app/core/intelligence/actions/service.py` | the single authoritative governed pipeline | **GOVERNED** | The only path by which a Core-scope mutation reaches an adapter. |
| 5 | `approve_held_action()` | `app/core/intelligence/actions/approval_service.py` | continuation of a held action | **GOVERNED** | Reuses the held action; cannot create a new action or skip policy/risk. |
| 6 | `execution_engine.execute()` | `app/core/intelligence/execution/engine.py` | executes an authorized request | **ENFORCEMENT BOUNDARY** | Rejects missing/non-approved/expired/mismatched authorization before adapter lookup. |
| 7 | `docker_api.start/stop/restart/create/remove` | `app/docker_api.py` | container mutations | **ADAPTER-ONLY** | Not exposed as routes; reachable only via the docker adapter after the governed chain succeeds. |
| 8 | `GET /containers`, `/containers/{name}/stats`, `/platform/state`, `/config`, `/modules`, `/monitor/history`, `/intelligence/health` | `app/main.py`, routers | none | **READ-ONLY / DIAGNOSTIC** | No mutation capability. |

## Direct-Execution-Call Review (C01 §15)

All direct calls to `execution_engine.execute()` were inspected:

- `execute_governed_action()` (actions/service.py) — the governed pipeline; creates
  authorization only from a legitimate approval result before calling the engine.
- `approve_held_action()` (approval_service.py) — creates a manual authorization
  from a legitimately granted hold before calling the engine.
- Tests (`testing/`) — isolated, mock-backed; not production entrypoints.

No production path calls the engine with a caller-supplied or fabricated
authorization identifier.

## Conclusion

- There is **one authoritative governed production mutation boundary**:
  `execute_governed_action()` -> `execution_engine.execute()`.
- The only production mutation routes (`/execute`, `/approve`) traverse that
  boundary.
- Docker mutation functions are **ADAPTER-ONLY** and cannot be reached directly
  by production callers.
- No equivalent unmanaged production mutation path remains available.
