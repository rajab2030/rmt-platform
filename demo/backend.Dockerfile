# RMT backend -- TEST / EVALUATION IMAGE ONLY.
#
# Not a deployment path. Production runs under systemd + Caddy
# (projects/homelab-control-center/deploy/, docs/operations/DEPLOY.md).
# RMT does not depend on Docker; this image only packages the backend so the
# platform can be tried locally. See demo/README.md.
#
# Build context: repository root (see docker-compose.yml).
FROM python:3.12-slim

# git: required by GET /platform/state and by the git-tag showcase domain
# (docs/operations/PREREQUISITES.md).
RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --uid 10001 rmt

WORKDIR /app/backend
COPY projects/homelab-control-center/backend/requirements.lock.txt ./
RUN pip install --no-cache-dir -r requirements.lock.txt

COPY --chown=rmt:rmt projects/homelab-control-center/backend/ ./

# Disposable scratch repository for the git-tag showcase. The agent only ever
# sends a tag name; the repo path is fixed server-side (RMT_AGENT_GIT_REPO_PATH).
RUN mkdir -p /srv/rmt-showcase-repo /app/backend/data \
    && chown -R rmt:rmt /srv/rmt-showcase-repo /app/backend/data
USER rmt
RUN cd /srv/rmt-showcase-repo \
    && git init -q \
    && echo "RMT showcase scratch repository" > README \
    && git add README \
    && git -c user.email=demo@example.com -c user.name=Demo commit -qm init

EXPOSE 8000
# 0.0.0.0 inside the container network only; docker-compose.yml publishes the
# port on the host loopback (127.0.0.1) and nowhere else.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
