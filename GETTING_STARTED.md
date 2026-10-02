# Getting started with RMT

## What is RMT?

RMT is a safety layer for important actions, especially actions taken by AI
agents. Before an action happens, RMT checks it. If it is risky, RMT holds it
until a person approves. Afterwards, RMT checks that it really worked and keeps
a record of everything.

## Why use it?

- **Nothing risky happens by surprise.** Risky actions wait for a person to say yes.
- **Agents only get the permission they need.** A permission covers one action on
  one target, can be used once, and expires.
- **You can see what really happened.** RMT checks the result after the action.
  "Could not check" is reported honestly, never shown as success.
- **You get a complete record.** Every step is saved and linked together, so you
  can answer "who did what, why, and did it work?"

RMT is built for important actions that happen now and then, like releases,
deployments, restarts and payments. It is not built for thousands of actions per
second.

## Try it in about 5 minutes

You will run RMT on your own computer, then watch an example agent ask to
create and remove a Git tag. RMT checks each request, holds the risky ones for
you, and shows you the result. Nothing outside your computer is touched.

### Option A: with Docker (easiest)

You need [Git](https://git-scm.com/downloads) and
[Docker Desktop](https://www.docker.com/products/docker-desktop/) (or Podman).

1. Download RMT:
   ```bash
   git clone https://github.com/rajab2030/rmt-platform.git
   cd rmt-platform
   ```
2. Start RMT:
   ```bash
   docker compose up --build -d
   ```
3. Run the example agent:
   ```bash
   docker compose run --rm showcase
   ```
   When it says **"Press Enter to approve"**, you are the person approving.
   Press Enter within 5 minutes; after that the request expires.
4. Open the control center at <http://localhost:5173> and click
   **Governed Ops** to see the record of what happened. When it asks for a
   token, enter `rmt-demo-token`.
5. When you are done:
   ```bash
   docker compose down
   ```

Docker is only used here to make the trial easy. RMT itself does not need
Docker. Option B shows the same thing without it.

### Option B: without Docker

You need Git and Python 3.12 (check with `python3 --version`). The commands
are for macOS or Linux.

1. Download RMT and install what it needs:
   ```bash
   git clone https://github.com/rajab2030/rmt-platform.git
   cd rmt-platform/projects/homelab-control-center/backend
   python3 -m venv .venv
   .venv/bin/pip install -r requirements.lock.txt
   ```
2. Create a throwaway Git repository for the example to work on:
   ```bash
   mkdir -p /tmp/rmt-demo-repo
   git -C /tmp/rmt-demo-repo init -q
   git -C /tmp/rmt-demo-repo -c user.email=demo@example.com -c user.name=Demo \
       commit -q --allow-empty -m init
   ```
3. Start RMT (leave this terminal open):
   ```bash
   RMT_RUNTIME_ENGINE=simulation \
   RMT_OPERATOR_TOKENS=demo:rmt-demo-token \
   RMT_AGENT_ENABLED=true \
   RMT_AGENT_GIT_REPO_PATH=/tmp/rmt-demo-repo \
   .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
   ```
4. In a **second** terminal, from the `rmt-platform` folder, run the example agent:
   ```bash
   cd tools/rmt-showcase-agent
   RMT_URL=http://127.0.0.1:8000 RMT_TOKEN=rmt-demo-token python3 rmt_showcase.py
   ```
   Press Enter when it asks you to approve.
5. When you are done, press `Ctrl+C` in the first terminal.

## What you just saw

1. **A permission:** the agent received permission to create one specific tag.
2. **A preview:** RMT showed how it would treat the request before anything happened.
3. **A hold:** RMT paused the request until you approved it.
4. **A refusal:** the agent tried to reuse its permission for something else, and RMT refused.
5. **A result:** after approval, RMT ran the action, checked the result, and recorded it.

## Where to go next

- **Ask a question or share feedback:**
  [GitHub Discussions](https://github.com/rajab2030/rmt-platform/discussions)
- **Help out:** tell us which step was confusing, or pick a
  [starter issue](https://github.com/rajab2030/rmt-platform/contribute)
- **Connect your own agent:** [Agent API guide](docs/operations/AGENT_API.md)
- **What RMT promises, and what it doesn't:** [Guarantees and limits](docs/RMT_GUARANTEES.md)

## Good to know

- This trial uses one demo token, so you approve your own agent's requests. In
  real use, separate people can hold these roles.
- The **Containers** page in the control center shows "Failed to fetch
  containers" during the trial. That is expected: the trial doesn't give RMT
  access to Docker.
- Use the trial token only for the trial. Never put a real token in it.
