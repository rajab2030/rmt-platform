# RMT quickstart

Run the Agent Governance Gateway walkthrough locally with one command. You
don't need Python, an LLM, secrets, or any configuration.

```bash
git clone https://github.com/rajab2030/rmt-platform.git
cd rmt-platform
docker compose run --rm showcase
```

When the walkthrough holds an action for approval, press **Enter** to approve
it as the operator. When you're done:

```bash
docker compose down
```

## What it does

`compose.yaml` builds one image from `quickstart/Dockerfile` and starts two
containers:

- **`rmt`**: the RMT backend, with the agent gateway on and authentication
  off. A disposable Git repository is created inside the image; the demo
  creates and removes tags there. The API is published on `127.0.0.1:8000`
  only.
- **`showcase`**: `tools/rmt-showcase-agent/rmt_showcase.py`, which walks an
  agent through five acts: a scoped grant, a preview, a proposal, a refused
  attempt to reuse the grant, and a separately granted removal. Every line of
  output is a real response from the `rmt` container.

The first run spends most of its time building the image. Later runs start in
a few seconds. `docker compose up` on its own starts only the backend.

## Limits of this demo

Read these before drawing conclusions from the walkthrough:

- **Trusted operator.** RMT is built for trusted-operator environments. It's
  not a defence against someone who already controls the host.
- **One credential.** Authentication is off, so every call is recorded as the
  `local-dev` operator: the same identity grants, proposes and approves. This
  doesn't demonstrate independent approver identities or separation of duties.
- **Only what goes through the gateway is governed.** Anything done directly
  on the host, or in the container, is outside RMT's boundary.
- **Disposable state.** Evidence is stored inside the `rmt` container and is
  deleted by `docker compose down`.
- **No Docker domain.** The Docker socket isn't mounted, so the homelab domain
  runs in simulation mode. Its collector errors in the `rmt` logs are expected.
- Approval depends on policy, so not every action needs a human. An absent
  verification result is not a verified success.

Full detail: [guarantees and limits](../docs/RMT_GUARANTEES.md) and the
[threat model](../docs/RMT_THREAT_MODEL.md). Never expose this port or reuse
these settings outside a local demo.

## Requirements

- Docker with Compose v2 (`docker compose version`). On Windows, use Docker
  Desktop with the WSL 2 backend and run the commands from a WSL shell or
  PowerShell.
- Network access to Docker Hub, the Debian package mirrors and PyPI for the
  first build.

Tested on Linux (Docker 29, Compose 5). The Windows/WSL path hasn't been
verified yet; if you try it, a
[setup report](https://github.com/rajab2030/rmt-platform/discussions) helps.

## Troubleshooting

- **Port 8000 is already in use.** Pick another host port:
  `RMT_QUICKSTART_PORT=8099 docker compose run --rm showcase`. On PowerShell,
  set `$env:RMT_QUICKSTART_PORT = "8099"` first.
- **`error: No interactive approval received; leaving the action held.`**
  The showcase needs an interactive terminal to read your Enter. Run it
  directly in a terminal, not through a pipe or a CI job.
- **Rebuild after changing the code:** `docker compose build`.
- **Logs:** `docker compose logs rmt`.

To run the backend without Docker, see
[the showcase README](../tools/rmt-showcase-agent/README.md).
