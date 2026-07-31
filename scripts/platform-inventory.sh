#!/bin/bash

set -e

OUTPUT="$HOME/homelab/backups/manifests/platform-inventory.json"

mkdir -p "$(dirname "$OUTPUT")"

cat > "$OUTPUT" <<EOF
{
  "platform": "RMT",
  "timestamp": "$(date -Iseconds)",
  "hostname": "$(hostname)",
  "os": "$(lsb_release -ds)",
  "kernel": "$(uname -r)",
  "docker": "$(docker --version)",
  "git": {
    "branch": "$(git -C "$HOME/homelab" branch --show-current)",
    "commit": "$(git -C "$HOME/homelab" rev-parse --short HEAD)"
  },
  "containers": [
$(docker ps --format '    {"name":"{{.Names}}","status":"{{.Status}}"}' | paste -sd, -)
  ]
}
EOF

echo "Platform inventory generated:"
echo "$OUTPUT"
