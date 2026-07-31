#!/bin/bash

set -e

OUTPUT="$HOME/homelab/backups/manifests/platform-health.json"

mkdir -p "$(dirname "$OUTPUT")"

DOCKER_STATUS="unhealthy"

if systemctl is-active --quiet docker; then
    DOCKER_STATUS="healthy"
fi


RUNNING=$(docker ps -q | wc -l)

UNHEALTHY=$(docker ps --filter health=unhealthy -q | wc -l)


GIT_STATUS=$(git -C "$HOME/homelab" status --porcelain)

if [ -z "$GIT_STATUS" ]; then
    GIT_STATE="clean"
else
    GIT_STATE="modified"
fi


LATEST_BACKUP=$(ls -t "$HOME/homelab/backups/daily" | head -1)


cat > "$OUTPUT" <<EOF
{
  "platform": "RMT",
  "timestamp": "$(date -Iseconds)",

  "docker": {
    "status": "$DOCKER_STATUS"
  },

  "containers": {
    "running": $RUNNING,
    "unhealthy": $UNHEALTHY
  },

  "git": {
    "status": "$GIT_STATE",
    "commit": "$(git -C "$HOME/homelab" rev-parse --short HEAD)"
  },

  "backup": {
    "latest": "$LATEST_BACKUP"
  }
}
EOF

echo "Platform health generated:"
echo "$OUTPUT"1~#!/bin/bash

set -e

OUTPUT="$HOME/homelab/backups/manifests/platform-health.json"

mkdir -p "$(dirname "$OUTPUT")"

DOCKER_STATUS="unhealthy"

if systemctl is-active --quiet docker; then
    DOCKER_STATUS="healthy"
fi


RUNNING=$(docker ps -q | wc -l)

UNHEALTHY=$(docker ps --filter health=unhealthy -q | wc -l)


GIT_STATUS=$(git -C "$HOME/homelab" status --porcelain)

if [ -z "$GIT_STATUS" ]; then
    GIT_STATE="clean"
else
    GIT_STATE="modified"
fi


LATEST_BACKUP=$(ls -t "$HOME/homelab/backups/daily" | head -1)


cat > "$OUTPUT" <<EOF
{
  "platform": "RMT",
  "timestamp": "$(date -Iseconds)",

  "docker": {
    "status": "$DOCKER_STATUS"
  },

  "containers": {
    "running": $RUNNING,
    "unhealthy": $UNHEALTHY
  },

  "git": {
    "status": "$GIT_STATE",
    "commit": "$(git -C "$HOME/homelab" rev-parse --short HEAD)"
  },

  "backup": {
    "latest": "$LATEST_BACKUP"
  }
}
EOF

echo "Platform health generated:"
echo "$OUTPUT"1~#!/bin/bash

set -e

OUTPUT="$HOME/homelab/backups/manifests/platform-health.json"

mkdir -p "$(dirname "$OUTPUT")"

DOCKER_STATUS="unhealthy"

if systemctl is-active --quiet docker; then
    DOCKER_STATUS="healthy"
fi


RUNNING=$(docker ps -q | wc -l)

UNHEALTHY=$(docker ps --filter health=unhealthy -q | wc -l)


GIT_STATUS=$(git -C "$HOME/homelab" status --porcelain)

if [ -z "$GIT_STATUS" ]; then
    GIT_STATE="clean"
else
    GIT_STATE="modified"
fi


LATEST_BACKUP=$(ls -t "$HOME/homelab/backups/daily" | head -1)


cat > "$OUTPUT" <<EOF
{
  "platform": "RMT",
  "timestamp": "$(date -Iseconds)",

  "docker": {
    "status": "$DOCKER_STATUS"
  },

  "containers": {
    "running": $RUNNING,
    "unhealthy": $UNHEALTHY
  },

  "git": {
    "status": "$GIT_STATE",
    "commit": "$(git -C "$HOME/homelab" rev-parse --short HEAD)"
  },

  "backup": {
    "latest": "$LATEST_BACKUP"
  }
}
EOF

echo "Platform health generated:"
echo "$OUTPUT"
