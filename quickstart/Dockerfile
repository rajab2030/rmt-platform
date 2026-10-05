# RMT quickstart image: the backend plus the showcase client, for a local
# demo only. Built from the repository root by ../compose.yaml.
#
# Not a production image: auth is disabled in compose.yaml, evidence lives
# inside the container, and the demo Git repository is created at build time.
FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --uid 10001 rmt

COPY projects/homelab-control-center/backend/requirements.lock.txt /tmp/requirements.lock.txt
RUN pip install --no-cache-dir -r /tmp/requirements.lock.txt

COPY --chown=rmt:rmt projects/homelab-control-center/backend/ /app/backend/
COPY --chown=rmt:rmt tools/rmt-showcase-agent/ /app/showcase/

USER rmt

# The disposable repository the git-tag domain acts on. The agent only ever
# sends a tag name; this path is fixed server-side (RMT_AGENT_GIT_REPO_PATH).
RUN git init -q /home/rmt/demo-repo \
    && cd /home/rmt/demo-repo \
    && git config user.email demo@example.com \
    && git config user.name "RMT Demo" \
    && echo "disposable repository for the RMT quickstart" > README \
    && git add README \
    && git commit -qm init

WORKDIR /app/backend
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
