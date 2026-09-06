# RMT — Core Adapter Decoupling (Work Item / Governed Directive)

> **Document type:** governed work-item directive (coordination + owner
> classification decision). This is NOT implementation authorization.
> **Status:** #1 COMPLETED & VERIFIED (C07 freeze deviation). #2–#18 DEFERRED
> under the owner REDUCE-SCOPE decision. No implementation authorized beyond #1.

---

## 1. Governing architectural invariant (owner-stated)

**RMT Core must remain adapter-agnostic. Docker is a Homelab
implementation/adapter, not a Core dependency.**

Context (owner-confirmed): RMT Core is a general governance platform; the
Homelab is the demo; Docker is just one adapter. Changing or removing an
adapter (Docker or otherwise) must not require changes to the Core. The
`execute_governed_action -> execution_engine.execute -> adapter` governed
boundary already honors this; the scope below covers coupling elsewhere in the
Core.

## 2. Reported coupling evidence (to be re-verified, not assumed)

1. `app/core/platform_state/service.py:12`
   `from app.docker_api import get_containers` — Core module imports Docker
   directly; `get_docker_health()` returns a hardcoded `DockerHealth` with a
   `"docker"` label.
2. `app/core/observability/` — semantically "container metrics":
   `save_container_metric` / `get_latest_container_metrics` and a
   `container_metrics` SQLite table.
3. `app/core/self_management/service.py:67` (`m.runtime.container`) and
   `app/core/module_registry/schema.py:8`
   (`container: Optional[str] = None`).

## 3. Owner Decision — Classification

Treat the identified Docker/container couplings as **DEFECTS requiring a
governed Core change**, not as permanently accepted couplings.

However, this is a **classification decision, not implementation
authorization**. The Core remains frozen at C07.

## 4. Required procedure (before any Core code modification)

1. **Re-verify** the three reported coupling points.
2. **Complete read-only audit** of Docker/container references under
   `app/core/`, excluding the explicitly scoped adapter/Homelab paths
   (`app/core/*/execution/adapters/`, `app/homelab/`, `app/docker_api.py`,
   `app/collector.py`, and container schema files only where intentionally
   contractual).
3. **Classify every finding** as `FACT + DEFECT` or `FACT + ACCEPTED
   COUPLING`, each with architectural justification.
4. **Demonstrate** that the existing finite C07 Target State / Core contracts
   are insufficient to preserve the adapter-agnostic Core invariant (the
   evidence required for a freeze-deviation).
5. **Produce the minimal bounded remediation scope**.
6. **STOP and request/record explicit freeze-deviation approval** before
   modifying Core code.

No implementation is authorized by this classification alone.

## 5. Hard boundaries (non-negotiable)

- Do **not** reopen C01–C07.
- Do **not** create a new Core milestone (there is no C08).
- Do **not** alter governed execution behavior
  (`execute_governed_action`, `execution_engine.execute`, policy/risk/approval/
  authorization/verification semantics, the adapter boundary itself).
- Do **not** modify `app/homelab/` or the execution adapters as part of this
  work.
- Any approved implementation must be the **smallest change** necessary to
  remove genuine Core coupling while **preserving existing externally
  observable behavior and compatibility contracts** wherever those are
  intentionally required.

## 6. Approved-implementation expectations (only after freeze-deviation approval)

- `observability`: genericize `container_metrics` to adapter-neutral `metrics`
  (naming/terminology), preserving behavior and compatibility or migrating
  deliberately with recorded rationale.
- `platform_state`: replace direct `from app.docker_api import get_containers`
  with a generic provider/observer interface; Docker becomes one injected
  implementation.
- Remove `container` from Core domain models (`self_management`,
  `module_registry/schema`) or move it to an adapter/domain extension object.
- Do **not** change governed execution behavior.
- Add tests proving the Core governed path behaves identically with a
  non-Docker adapter and with the Docker adapter absent (mocked).

## 7. Verification gate (unchanged, must remain green)

```bash
cd /home/rmt-lab/homelab/projects/homelab-control-center/backend
source .venv/bin/activate
PYTHONPATH=. pytest app/core/intelligence/testing -q   # >= 122 passed
```

## 8. Reporting requirement

Report: full audit findings (line-referenced, classified), the demonstrated
insufficiency of the finite C07 contracts, the minimal remediation scope, the
freeze-deviation approval record, files changed, test results, and any
intentional compatibility deviation. Do not implement before the step-6
approval is recorded.


---

## 9. Completion Record — #1 platform_state provider extraction (VERIFIED)

**Owner decision:** APPROVE implementation of the bounded `platform_state`
provider extraction (#1) only — an explicit C07 freeze-deviation authorization.

**Implemented (2026-09-04):**
- `app/core/platform_state/provider.py` *(new)* — generic `PlatformStateProvider`
  protocol (Core).
- `app/core/platform_state/service.py` — removed `from app.docker_api import
  get_containers`; `get_platform_state(provider)` now consumes the protocol.
- `app/docker_provider.py` *(new, outside Core)* — `DockerPlatformStateProvider`
  concrete implementation.
- `app/main.py` — composition root injects `DockerPlatformStateProvider()`.
- `app/core/platform_state/testing/test_platform_state_provider.py` *(new)* —
  3 focused regression tests.

**Dependency direction achieved:**
`Core platform_state service -> PlatformStateProvider protocol <- Docker
implementation (app/docker_provider.py)`. Core no longer imports `app.docker_api`.

**Behavior invariant:** `/platform/state` JSON contract preserved exactly
(`platform`, `git`, `containers{running,unhealthy}`, `health{status}`, `backup`).
No field renamed/removed; provider returns identical values/semantics.

**Verification:**
- Full C07 suite: **122 passed** (no regressions).
- New focused test: **3 passed**.
- `app.main` imports cleanly.

**Out-of-scope areas confirmed untouched:** observability, `RuntimeInfo.container`,
module_factory, evolution/adapters/module_change.py, self_management, verification,
intelligence observation/analysis naming, `container_metrics` persistence/table,
public HTTP contracts, `app/homelab/`, `app/docker_api.py`, `app/collector.py`,
execution adapters, `execution_engine`, policy/risk/approval/authorization/
verification semantics. No terminology renames, no data migration, no new
milestone, no reopening of C01–C07.

**Deferred (owner REDUCE-SCOPE decision):** #2–#18 remain deferred. Do not
automatically proceed to #2; reassess remaining findings against the frozen
Target State before any further authorization.
