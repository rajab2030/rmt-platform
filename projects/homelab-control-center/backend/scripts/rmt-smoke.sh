#!/usr/bin/env bash
# RMT-PROD P2 (V4) -- post-deploy smoke check.
#
# Run after every restart / redeploy / drop-in change. Asserts the running
# service is shaped the way a production RMT should be -- routes present, auth
# on, the runtime in the expected adapter mode, metrics scrapable, the loop
# where it should be. Exit 0 = safe; non-zero = investigate before trusting it.
#
#   RMT_SMOKE_BASE_URL   default http://127.0.0.1:8000
#   RMT_SMOKE_TOKEN      optional -- an operator token; enables the authed checks
#   RMT_SMOKE_EXPECT_ADAPTER  default docker  (set to simulation for a dev box)
#   RMT_SMOKE_EXPECT_LOOP     one of: running | stopped | any   (default any)
#
# Example:
#   RMT_SMOKE_TOKEN=$(sudo grep -oP 'ragb:\K[^,]+' \
#     /etc/systemd/system/rmt-control-center.service.d/auth.conf) \
#     backend/scripts/rmt-smoke.sh
set -uo pipefail

BASE="${RMT_SMOKE_BASE_URL:-http://127.0.0.1:8000}"
TOKEN="${RMT_SMOKE_TOKEN:-}"
EXPECT_ADAPTER="${RMT_SMOKE_EXPECT_ADAPTER:-docker}"
EXPECT_LOOP="${RMT_SMOKE_EXPECT_LOOP:-any}"

fails=0
ok()   { printf '  \033[32mok\033[0m   %s\n' "$1"; }
bad()  { printf '  \033[31mFAIL\033[0m %s\n' "$1"; fails=$((fails + 1)); }
j()    { printf '%s' "$1" | python3 -c "import sys,json;d=json.load(sys.stdin);print(eval('d'+sys.argv[1]))" "$2" 2>/dev/null; }

echo "RMT smoke -> $BASE"

# 1. liveness
h="$(curl -sS -m 5 "$BASE/health" 2>/dev/null || true)"
[ -n "$h" ] && [ "$(j "$h" "['status']")" != "" ] && ok "/health answers" || bad "/health did not answer"
st="$(j "$h" "['status']")"
[ "$st" = "ok" ] && ok "/health status=ok" || bad "/health status=$st"

# 2. runtime adapter mode (D6)
ra="$(j "$h" "['runtime']['resolved_adapter']")"
deg="$(j "$h" "['runtime']['adapter_degraded']")"
[ "$ra" = "$EXPECT_ADAPTER" ] && ok "adapter=$ra" || bad "adapter=$ra, expected $EXPECT_ADAPTER"
[ "$deg" = "False" ] && ok "adapter not degraded" || bad "adapter_degraded=$deg ($(j "$h" "['runtime']['notes']"))"

# 3. metrics (O4)
m="$(curl -sS -m 5 "$BASE/metrics" 2>/dev/null || true)"
printf '%s' "$m" | grep -q '^rmt_up 1$' && ok "/metrics up" || bad "/metrics missing rmt_up"
printf '%s' "$m" | grep -q '^rmt_metrics_scrape_errors_total 0$' && ok "/metrics 0 scrape errors" \
    || bad "/metrics scrape errors: $(printf '%s' "$m" | grep rmt_metrics_scrape_errors_total)"

# 4. auth is enforced (S1)
c="$(curl -sS -m 5 -o /dev/null -w '%{http_code}' -X POST "$BASE/execute?operation=restart&target=x" 2>/dev/null)"
[ "$c" = "401" ] && ok "POST /execute unauthenticated -> 401" || bad "POST /execute unauth -> $c (expected 401)"
c="$(curl -sS -m 5 -o /dev/null -w '%{http_code}' "$BASE/agent/status" 2>/dev/null)"
[ "$c" = "401" ] && ok "GET /agent/status unauthenticated -> 401" || bad "GET /agent/status unauth -> $c"

# 5. loop state
ls="$(curl -sS -m 5 "$BASE/homelab/loop/status" 2>/dev/null || true)"
running="$(j "$ls" "['running']")"
case "$EXPECT_LOOP" in
    running) [ "$running" = "True" ] && ok "loop running" || bad "loop running=$running, expected running" ;;
    stopped) [ "$running" = "False" ] && ok "loop stopped" || bad "loop running=$running, expected stopped" ;;
    *)       ok "loop running=$running (not asserted)" ;;
esac

# 6. authed checks (optional)
if [ -n "$TOKEN" ]; then
    a="$(curl -sS -m 5 -H "Authorization: Bearer $TOKEN" "$BASE/agent/status" 2>/dev/null || true)"
    [ "$(j "$a" "['enabled']")" != "" ] && ok "authed /agent/status -> 200" || bad "authed /agent/status failed"
fi

echo
if [ "$fails" -eq 0 ]; then
    echo "SMOKE PASSED"
    exit 0
fi
echo "SMOKE FAILED ($fails check(s))"
exit 1
