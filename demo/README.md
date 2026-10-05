# RMT local evaluation harness (test only)

A way to **try** RMT locally with one command. It is not a deployment path, and
it does not make Docker part of RMT.

- **Docker is only an adapter in RMT and can be replaced.** Here, container
  tooling is used purely to *package* the backend and control center for a local
  trial. Inside the harness RMT runs the `simulation` runtime engine, and no
  Docker socket is mounted, so RMT's own Docker execution adapter is never
  registered. The compose file also works with Podman, and the native path
  (Python venv + uvicorn, see
  [`tools/rmt-showcase-agent/README.md`](../tools/rmt-showcase-agent/README.md))
  is unchanged and equivalent.
- **Production** runs under systemd + Caddy:
  [`docs/operations/DEPLOY.md`](../docs/operations/DEPLOY.md). Nothing here
  changes that path.

## Run it

From the repository root:

```bash
docker compose up --build -d          # backend (127.0.0.1:8000) + control center (127.0.0.1:5173)
docker compose run --rm showcase      # the interactive git-tag walkthrough
docker compose down                   # stop; all demo evidence is discarded
```

Open <http://localhost:5173>. The Governed Ops and Budget Control views ask for
an operator token: use the demo token (`rmt-demo-token`, or whatever you set in
`RMT_DEMO_TOKEN`).

The showcase waits for Enter at each approval step, which is why it runs with
`docker compose run` rather than as part of `up`. The Git-tag walkthrough is
explained in [`tools/rmt-showcase-agent/README.md`](../tools/rmt-showcase-agent/README.md).

## What the harness sets, and why

| Setting | Value | Why |
|---|---|---|
| `RMT_RUNTIME_ENGINE` | `simulation` | No host containers are touched; `/health` reports the adapter as not degraded because configured == resolved |
| `RMT_HOMELAB_LOOP_ENABLED` | `false` | The homelab loop governs this project's own homelab; there is nothing to remediate here |
| `RMT_AUTH_ENABLED` | `true` | Authentication stays on, as in production |
| `RMT_OPERATOR_TOKENS` | `demo:${RMT_DEMO_TOKEN:-rmt-demo-token}` | A labelled demo identity; evidence records the operator as `demo`. Never reuse a real token |
| `RMT_AGENT_ENABLED` + `RMT_AGENT_GIT_REPO_PATH` | `true`, `/srv/rmt-showcase-repo` | The git-tag domain the showcase drives; the scratch repo is created inside the image |
| `RMT_CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | The control center calls the API from that origin |
| Published ports | `127.0.0.1:8000`, `127.0.0.1:5173` | Host loopback only |

Budget Control is left **uninitialized** (`RMT_BUDGET_BOOTSTRAP_PRINCIPAL` is not
set), matching the project decision not to seed that domain with fabricated data.

## Known limits

- The **Containers** view shows "Failed to fetch containers" and
  `/platform/state` returns 503: there is deliberately no Docker access.
- The API host port must stay **8000**. The control center reads `api_port`
  from `/config` and calls `http://<hostname>:8000` directly.
- Evidence lives inside the backend container. `docker compose down` (or
  recreating the container) discards it.
- One operator identity approves its own agent's holds. This is the same limit
  the recorded walkthrough states; it does not demonstrate separate approvers.
