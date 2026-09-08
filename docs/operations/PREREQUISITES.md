# RMT — Runtime Prerequisites & Environment Parity

RMT-PROD **P2 / D6**. Above-Core / operational. The host capabilities the RMT
backend needs, which are (a) easy to get wrong on a fresh box and (b) have
bitten test runs and rebuilds before.

## Required — the service will not function correctly without these

| Capability | Why | Check |
|---|---|---|
| **Python 3.12** | the venv and lockfile (`requirements.lock.txt`) are built on 3.12 | `python3 --version` |
| **A writable working tree** under `/home/rmt-lab/homelab/projects/homelab-control-center/backend` | evidence JSON stores + `data/observability.db` live inside the package tree | `test -w …/backend` |
| **`git`** on `PATH` | `GET /platform/state` shells out to git | `command -v git` |
| **`sqlite3`** | E5 backup takes a `VACUUM INTO` snapshot of `observability.db` | `command -v sqlite3` |
| **operator tokens** (`RMT_OPERATOR_TOKENS`) | with `RMT_AUTH_ENABLED=true` (the default) the app **refuses to start** without them | startup log |

## Capability-sensitive — the service runs, but behaviour changes

| Capability | Present | Absent |
|---|---|---|
| **Docker socket reachable** (`/var/run/docker.sock`, `docker` group membership) | `config.yaml runtime.engine: docker` → the real `DockerExecutionAdapter` runs governed actions | silently falls back to the **`simulation`** adapter — governed actions are no-ops. Logged as a **WARNING** at startup (D6) and shown on `/health` |
| **`caddy` ≥ 2.6** | S4 TLS entry point on the LAN | app is loopback-only; no external access |
| **`RMT_NOTIFY_WEBHOOK_URL`** set | O2/O3 held-action + ops alerts POST to a real sink | alerts are journal-only |

## Observability of the runtime mode

`GET /health` carries a `runtime` block (D6):

```json
"runtime": {
  "configured_engine": "docker",
  "resolved_adapter": "docker",
  "docker_available": true,
  "git_available": true,
  "adapter_degraded": false,
  "notes": []
}
```

- `adapter_degraded: true` with a note like `configured engine 'docker'
  unavailable -- running 'simulation'` means the host was told to drive real
  containers but cannot. It does **not** flip `/health` `status` to `degraded`
  (that is reserved for loop faults) — it is an advisory for the operator and
  the V4 smoke check.
- The same mismatch is logged once as a `WARNING` at startup
  (`app/ops/runtime_info.py::warn_on_capability_mismatch`).

## Production-mode expectation

On the live homelab host the expected steady state is:

```
configured_engine == resolved_adapter == "docker"
docker_available == git_available == true
adapter_degraded == false
```

The V4 post-deploy smoke script (`backend/scripts/rmt-smoke.sh`) asserts exactly
this, so a rebuild that comes up in simulation by mistake fails the smoke gate
instead of quietly running no-ops.

## Related

- `docs/operations/CONFIG.md` — every `RMT_*` variable
- `docs/operations/RMT_PLATFORM_RECOVERY.md` — the R3 rebuild prereq check
  (`rmt-rebuild.sh` step 1) enforces the "required" rows above
- `projects/homelab-control-center/deploy/systemd/hardening.conf` — notes on
  why `docker` group access survives `NoNewPrivileges`
