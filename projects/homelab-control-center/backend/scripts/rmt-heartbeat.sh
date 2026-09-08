#!/usr/bin/env bash
# RMT-PROD P1 (O3) -- external service-down alerting (inverted dead-man's switch).
#
# A down process cannot alert on itself. Cron this every 1-5 min: it pings
# RMT_HEARTBEAT_URL *only* when the local GET /health answers 200. If the
# service is down (or unreachable), the ping stops and the external monitor
# (healthchecks.io, Uptime Kuma push, cronitor, ...) alerts after its grace
# period.
#
# The "degraded" case (loop cycle error / quarantine) is handled in-band by
# app/ops/notifications.py::notify_ops -- this script only cares that the
# process is answering.
#
#   RMT_HEARTBEAT_URL   (required)  the monitor's ping URL
#   RMT_HEALTH_URL      (optional)  default http://127.0.0.1:8000/health
#
# Example crontab line (every 3 minutes):
#   */3 * * * * RMT_HEARTBEAT_URL=https://hc-ping.com/<uuid> \
#     /home/rmt-lab/homelab/projects/homelab-control-center/backend/scripts/rmt-heartbeat.sh
set -euo pipefail

HEALTH="${RMT_HEALTH_URL:-http://127.0.0.1:8000/health}"
PING="${RMT_HEARTBEAT_URL:-}"

[ -n "$PING" ] || { echo "RMT_HEARTBEAT_URL not set" >&2; exit 2; }

code="$(curl -sS -m 5 -o /dev/null -w '%{http_code}' "$HEALTH" 2>/dev/null || echo 000)"
if [ "$code" != "200" ]; then
    echo "health check failed (HTTP $code) -- not pinging $PING" >&2
    exit 1
fi

curl -fsS -m 5 "$PING" >/dev/null
echo "heartbeat ok"
