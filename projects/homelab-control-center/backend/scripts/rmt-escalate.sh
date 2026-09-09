#!/usr/bin/env bash
# RMT T1-4 -- escalate an approval hold that a human has not actioned.
#
# The frozen Core approval-hold TTL is 300 s: a hold that is never approved
# just *expires*, and `Restart=always` / the D4 watchdog say nothing about it.
# cron / a systemd timer runs this every 1-2 min; it reads the read-only
# `GET /ops/holds` route and POSTs a one-time alert to a second channel for any
# hold that is EITHER
#   (a) still `actionable` and older than RMT_ESCALATE_AFTER_SECONDS, OR
#   (b) `expired` while it was never approved (a missed approval window).
# Each `approval_id` escalates once (state file, rmt-watchdog.sh pattern).
#
#   RMT_ESCALATE_HOLDS_URL       default http://127.0.0.1:8000/ops/holds
#   RMT_ESCALATE_TOKEN           operator token for that route (required when
#                                RMT_AUTH_ENABLED=true, which is the default)
#   RMT_ESCALATE_WEBHOOK_URL     second-channel webhook (JSON POST). Unset => the
#                                script logs only and does nothing else.
#   RMT_ESCALATE_AFTER_SECONDS   default 180  (must be < the 300 s Core TTL)
#   RMT_ESCALATE_STATE           default /run/rmt-escalate (fallback /tmp)
#
# Example (every 2 minutes):
#   */2 * * * * RMT_ESCALATE_TOKEN=... RMT_ESCALATE_WEBHOOK_URL=https://chat.lan/hooks/rmt-oncall \
#     /home/rmt-lab/homelab/projects/homelab-control-center/backend/scripts/rmt-escalate.sh
set -euo pipefail

HOLDS_URL="${RMT_ESCALATE_HOLDS_URL:-http://127.0.0.1:8000/ops/holds}"
TOKEN="${RMT_ESCALATE_TOKEN:-}"
WEBHOOK="${RMT_ESCALATE_WEBHOOK_URL:-}"
AFTER="${RMT_ESCALATE_AFTER_SECONDS:-180}"
STATE_DIR="${RMT_ESCALATE_STATE:-/run/rmt-escalate}"

if [ "$AFTER" -ge 300 ]; then
    echo "rmt-escalate: WARNING RMT_ESCALATE_AFTER_SECONDS=$AFTER >= 300s Core hold TTL;" \
         "actionable holds will have expired first" >&2
fi

mkdir -p "$STATE_DIR" 2>/dev/null || STATE_DIR="/tmp/rmt-escalate"
mkdir -p "$STATE_DIR"
SEEN_FILE="$STATE_DIR/escalated_ids"
touch "$SEEN_FILE"

log() { logger -t rmt-escalate "$1" 2>/dev/null || true; echo "rmt-escalate: $1" >&2; }

auth=()
[ -n "$TOKEN" ] && auth=(-H "Authorization: Bearer $TOKEN")

body="$(curl -sS -m 5 "${auth[@]}" "$HOLDS_URL" 2>/dev/null || true)"
if [ -z "$body" ]; then
    log "could not read $HOLDS_URL (unreachable or unauthorized)"
    exit 0
fi

# Parse with python3 (stdlib only) -- emit one TSV line per hold to escalate.
printf '%s' "$body" | python3 -c '
import json, sys
try:
    holds = json.load(sys.stdin).get("holds", [])
except Exception:
    sys.exit(0)
after = float("'"$AFTER"'")
for h in holds:
    age = h.get("age_seconds") or 0
    actionable = bool(h.get("actionable"))
    expired = bool(h.get("expired"))
    terminal = bool(h.get("record_terminal"))
    # (a) still open and stale, or (b) expired without ever being resolved
    if (actionable and age >= after) or (expired and not terminal):
        why = "stale" if actionable else "expired-unapproved"
        print("\t".join(str(x) for x in (
            h.get("approval_id",""), h.get("component",""),
            h.get("kind",""), h.get("granted_by") or "",
            int(age), why,
        )))
' | while IFS=$'\t' read -r aid comp kind granted_by age why; do
    [ -z "$aid" ] && continue
    if grep -qxF "$aid" "$SEEN_FILE"; then
        continue
    fi
    msg="hold $aid ($kind, component=$comp, granted_by=${granted_by:-n/a}, age=${age}s) -- $why"
    log "escalating: $msg"
    if [ -n "$WEBHOOK" ]; then
        curl -fsS -m 5 -H 'Content-Type: application/json' \
            -d "{\"source\":\"rmt-escalate\",\"event\":\"hold_escalation\",\"approval_id\":\"$aid\",\"component\":\"$comp\",\"kind\":\"$kind\",\"granted_by\":\"$granted_by\",\"age_seconds\":$age,\"reason\":\"$why\"}" \
            "$WEBHOOK" >/dev/null 2>&1 \
            && echo "$aid" >> "$SEEN_FILE" \
            || log "escalation POST failed for $aid (will retry next run)"
    else
        # no second channel configured: record it as seen so the log alert
        # is one-shot too.
        echo "$aid" >> "$SEEN_FILE"
    fi
done

# Keep the state file bounded.
if [ "$(wc -l < "$SEEN_FILE")" -gt 500 ]; then
    tail -n 250 "$SEEN_FILE" > "$SEEN_FILE.tmp" && mv "$SEEN_FILE.tmp" "$SEEN_FILE"
fi

echo "rmt-escalate: ok"
