#!/usr/bin/env bash
# RMT-PROD P2 (D4) -- act on the health probe.
#
# `Restart=always` in the unit only restarts on process *exit*. A process that
# is up but wedged (deadlock, event-loop stall) never exits, so systemd never
# acts. This script closes that gap: cron / a systemd timer runs it every
# 1-2 min; it polls GET /health and, after N consecutive *unreachable* results,
# restarts the service and fires an ops alert.
#
# Sustained `status: degraded` (CAP-04 loop cycle error / quarantine) is
# alert-only by default -- a restart does not clear a quarantine and could
# cause a restart loop. Set RMT_WATCHDOG_RESTART_ON_DEGRADED=true to include it.
#
#   RMT_WATCHDOG_HEALTH_URL           default http://127.0.0.1:8000/health
#   RMT_WATCHDOG_FAILS_BEFORE_RESTART default 3   (consecutive bad polls)
#   RMT_WATCHDOG_RESTART_ON_DEGRADED  default false
#   RMT_WATCHDOG_SERVICE             default rmt-control-center.service
#   RMT_WATCHDOG_NOTIFY_URL          optional  webhook for the alert (JSON POST)
#   RMT_WATCHDOG_STATE              default /run/rmt-watchdog (fallback /tmp)
#
# Example (every 2 minutes):
#   */2 * * * * RMT_WATCHDOG_NOTIFY_URL=https://chat.lan/hooks/rmt \
#     /home/rmt-lab/homelab/projects/homelab-control-center/backend/scripts/rmt-watchdog.sh
set -euo pipefail

HEALTH="${RMT_WATCHDOG_HEALTH_URL:-http://127.0.0.1:8000/health}"
LIMIT="${RMT_WATCHDOG_FAILS_BEFORE_RESTART:-3}"
ON_DEGRADED="${RMT_WATCHDOG_RESTART_ON_DEGRADED:-false}"
SERVICE="${RMT_WATCHDOG_SERVICE:-rmt-control-center.service}"
NOTIFY="${RMT_WATCHDOG_NOTIFY_URL:-}"
STATE_DIR="${RMT_WATCHDOG_STATE:-/run/rmt-watchdog}"

mkdir -p "$STATE_DIR" 2>/dev/null || STATE_DIR="/tmp/rmt-watchdog"
mkdir -p "$STATE_DIR"
COUNT_FILE="$STATE_DIR/consecutive_failures"
count="$(cat "$COUNT_FILE" 2>/dev/null || echo 0)"

notify() {
    local msg="$1"
    logger -t rmt-watchdog "$msg" 2>/dev/null || true
    echo "rmt-watchdog: $msg" >&2
    [ -n "$NOTIFY" ] && curl -fsS -m 5 -H 'Content-Type: application/json' \
        -d "{\"source\":\"rmt-watchdog\",\"service\":\"$SERVICE\",\"message\":\"$msg\"}" \
        "$NOTIFY" >/dev/null 2>&1 || true
}

body="$(curl -sS -m 5 "$HEALTH" 2>/dev/null || true)"
code="$(curl -sS -m 5 -o /dev/null -w '%{http_code}' "$HEALTH" 2>/dev/null || echo 000)"

bad=0
reason=""
if [ "$code" != "200" ]; then
    bad=1; reason="unreachable (HTTP $code)"
elif printf '%s' "$body" | grep -q '"status"[[:space:]]*:[[:space:]]*"degraded"'; then
    if [ "$ON_DEGRADED" = "true" ]; then
        bad=1; reason="degraded"
    else
        notify "health is degraded (alert-only; RESTART_ON_DEGRADED=false)"
    fi
fi

if [ "$bad" -eq 0 ]; then
    [ "$count" -ne 0 ] && echo 0 > "$COUNT_FILE"
    echo "rmt-watchdog: ok"
    exit 0
fi

count=$((count + 1))
echo "$count" > "$COUNT_FILE"
notify "health bad ($reason) -- consecutive failure $count/$LIMIT"

if [ "$count" -ge "$LIMIT" ]; then
    notify "restarting $SERVICE after $count consecutive failures ($reason)"
    if systemctl restart "$SERVICE"; then
        notify "restart issued"
        echo 0 > "$COUNT_FILE"
    else
        notify "RESTART FAILED -- manual intervention needed"
        exit 1
    fi
fi
