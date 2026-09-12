#!/usr/bin/env bash
# RMT-PROD P1 (R3) -- rebuild the RMT control-center service on a fresh host.
#
# Takes: this repository (at the canonical path) + one rmt-evidence-backup.sh
# backup.  Produces: a running, integrity-checked RMT service -- or, in --drill
# mode, the same sequence against a throwaway copy with a scratch instance on a
# spare port and nothing on the real host touched.
#
# Sequence:
#   1. prerequisites          python 3.12, git, sqlite3, rsync, docker group,
#                             (systemd + caddy unless skipped)
#   2. venv                   .venv from requirements.lock.txt  (reproducible)
#   3. evidence restore       scripts/rmt-evidence-restore.sh <backup>
#   4. integrity check        scripts/rmt_evidence_verify.py <backend>
#   5. test suite             PYTHONPATH=. pytest -q            (unless --skip-suite)
#   6a. real:  install base unit + non-secret drop-ins, daemon-reload,
#              enable --now, poll /health, print the manual (secret) checklist
#   6b. drill: launch a throwaway uvicorn on --port, poll /health, tear it down
#
# Usage:
#   rmt-rebuild.sh --evidence <backup-dir> [options]
#
#   --evidence DIR     (required) a backup made by rmt-evidence-backup.sh
#   --repo DIR         repo root            (default: /home/rmt-lab/homelab)
#   --drill DIR        DRILL MODE: rsync the project into DIR and run steps
#                      2-5 + 6b there; implies --skip-systemd; no live changes
#   --port N           drill instance port  (default: 8001)
#   --skip-systemd     stop after step 5 (no unit install / no systemctl)
#   --skip-suite       skip step 5 (faster; not recommended)
#   --yes              don't prompt before restoring into the live evidence tree
#
# Above-Core / operational.  No app/core/** dependency.
set -euo pipefail

# --------------------------------------------------------------------------- args
EVIDENCE=""
REPO="/home/rmt-lab/homelab"
DRILL=""
PORT="8001"
SKIP_SYSTEMD=0
SKIP_SUITE=0
ASSUME_YES=0

die() { echo "FAIL: $*" >&2; exit 1; }
step() { printf '\n\033[1m==> %s\033[0m\n' "$1"; }

while [ $# -gt 0 ]; do
    case "$1" in
        --evidence)     EVIDENCE="${2:?}"; shift 2 ;;
        --repo)         REPO="${2:?}"; shift 2 ;;
        --drill)        DRILL="${2:?}"; SKIP_SYSTEMD=1; shift 2 ;;
        --port)         PORT="${2:?}"; shift 2 ;;
        --skip-systemd) SKIP_SYSTEMD=1; shift ;;
        --skip-suite)   SKIP_SUITE=1; shift ;;
        --yes)          ASSUME_YES=1; shift ;;
        -h|--help)      sed -n '2,40p' "$0"; exit 0 ;;
        *)              die "unknown argument: $1" ;;
    esac
done

[ -n "$EVIDENCE" ] || die "--evidence <backup-dir> is required"
[ -d "$EVIDENCE" ] || die "not a directory: $EVIDENCE"
[ -f "$EVIDENCE/checksum.sha256" ] || die "no checksum.sha256 in $EVIDENCE -- not an rmt-evidence backup"
EVIDENCE="$(cd "$EVIDENCE" && pwd)"

PROJECT_REL="projects/homelab-control-center"
CANON_BACKEND="/home/rmt-lab/homelab/$PROJECT_REL/backend"

# --------------------------------------------------------------------- 1. prereqs
step "1/6  prerequisites"
need() { command -v "$1" >/dev/null 2>&1 || die "missing required tool: $1"; }
need python3
need git
need sqlite3
need rsync
PYVER="$(python3 -c 'import sys; print("%d.%d" % sys.version_info[:2])')"
[ "$PYVER" = "3.12" ] || echo "  WARN: python is $PYVER, the service was built on 3.12"
if id -nG 2>/dev/null | tr ' ' '\n' | grep -qx docker; then
    echo "  ok: user is in the 'docker' group (adapter can reach the socket)"
else
    echo "  WARN: user not in the 'docker' group -- the Docker adapter will fall back to simulation"
fi
if [ "$SKIP_SYSTEMD" -eq 0 ]; then
    need systemctl
    command -v caddy >/dev/null 2>&1 || echo "  WARN: caddy not installed -- S4 TLS proxy step must be done by hand (DEPLOY.md 1.4)"
fi
echo "  ok"

# ----------------------------------------------------------- 2. resolve backend dir
if [ -n "$DRILL" ]; then
    step "drill mode: staging a throwaway copy in $DRILL"
    mkdir -p "$DRILL"
    DRILL="$(cd "$DRILL" && pwd)"
    [ "$DRILL" != "$REPO" ] || die "--drill dir must not be the repo itself"
    mkdir -p "$DRILL/$PROJECT_REL"
    rsync -a --delete \
        --exclude '.venv/' --exclude '.git/' --exclude '__pycache__/' \
        --exclude '.pytest_cache/' --exclude '*.pre-restore.*' \
        "$REPO/$PROJECT_REL/" "$DRILL/$PROJECT_REL/"
    BACKEND="$DRILL/$PROJECT_REL/backend"
    echo "  staged -> $BACKEND"
else
    BACKEND="$REPO/$PROJECT_REL/backend"
    [ "$BACKEND" = "$CANON_BACKEND" ] || echo "  WARN: backend is $BACKEND, not the canonical $CANON_BACKEND -- the systemd unit hard-codes the canonical path"
fi
[ -f "$BACKEND/requirements.lock.txt" ] || die "no requirements.lock.txt under $BACKEND"
cd "$BACKEND"

# ------------------------------------------------------------------------ 2. venv
step "2/6  venv from requirements.lock.txt"
if [ -x "$BACKEND/.venv/bin/python" ]; then
    echo "  reusing existing $BACKEND/.venv"
else
    python3 -m venv "$BACKEND/.venv"
fi
"$BACKEND/.venv/bin/pip" install --quiet --upgrade pip
"$BACKEND/.venv/bin/pip" install --quiet -r "$BACKEND/requirements.lock.txt"
"$BACKEND/.venv/bin/python" --version
echo "  ok ($("$BACKEND/.venv/bin/pip" list 2>/dev/null | wc -l) packages)"

# ------------------------------------------------------------- 3. evidence restore
step "3/6  restore governance evidence from $EVIDENCE"
RESTORE_ARGS=("$EVIDENCE")
if [ -n "$DRILL" ]; then
    RESTORE_ARGS+=(--force)   # nothing is serving this copy
elif [ "$SKIP_SYSTEMD" -eq 0 ] && command -v systemctl >/dev/null 2>&1 \
        && systemctl is-active --quiet rmt-control-center.service; then
    die "rmt-control-center.service is running -- stop it first: sudo systemctl stop rmt-control-center.service"
fi
if [ -z "$DRILL" ] && [ "$ASSUME_YES" -eq 0 ]; then
    printf '  This REPLACES the live evidence under %s. Continue? [y/N] ' "$BACKEND/app/core/intelligence"
    read -r ans; [ "$ans" = "y" ] || [ "$ans" = "Y" ] || die "aborted by operator"
fi
"$BACKEND/scripts/rmt-evidence-restore.sh" "${RESTORE_ARGS[@]}"

# --------------------------------------------------------------- 4. integrity check
step "4/6  integrity check of the restored tree"
"$BACKEND/.venv/bin/python" "$BACKEND/scripts/rmt_evidence_verify.py" "$BACKEND" \
    || die "restored evidence failed the integrity check -- do not start the service"

# ----------------------------------------------------------------------- 5. suite
if [ "$SKIP_SUITE" -eq 0 ]; then
    step "5/6  test suite"
    ( cd "$BACKEND" && PYTHONPATH=. "$BACKEND/.venv/bin/python" -m pytest -q )
else
    step "5/6  test suite -- SKIPPED (--skip-suite)"
fi

# ------------------------------------------------------------- 6b. drill instance
if [ -n "$DRILL" ]; then
    step "6/6  drill: throwaway instance on 127.0.0.1:$PORT"
    LOG="$DRILL/rmt-drill-uvicorn.log"
    ( cd "$BACKEND" && PYTHONPATH=. RMT_AUTH_ENABLED=false \
        "$BACKEND/.venv/bin/uvicorn" app.main:app --host 127.0.0.1 --port "$PORT" \
        >"$LOG" 2>&1 ) &
    UVPID=$!
    trap 'kill "$UVPID" 2>/dev/null || true' EXIT
    ok=0
    for _ in $(seq 1 30); do
        if curl -sf -m2 "http://127.0.0.1:$PORT/health" >/dev/null 2>&1; then ok=1; break; fi
        sleep 1
    done
    [ "$ok" -eq 1 ] || { echo "--- uvicorn log ---"; tail -n 40 "$LOG"; die "drill instance did not answer /health on :$PORT"; }
    echo "  /health ->"
    curl -s -m5 "http://127.0.0.1:$PORT/health" | "$BACKEND/.venv/bin/python" -m json.tool
    kill "$UVPID" 2>/dev/null || true; wait "$UVPID" 2>/dev/null || true
    trap - EXIT
    echo
    echo "DRILL PASSED. Scratch tree left at $DRILL (rm -rf when done; uvicorn log: $LOG)."
    exit 0
fi

# ------------------------------------------------------- 6a. real: systemd bring-up
if [ "$SKIP_SYSTEMD" -eq 1 ]; then
    step "6/6  systemd bring-up -- SKIPPED (--skip-systemd)"
    echo "venv + evidence + suite are ready under $BACKEND. Install the unit yourself when ready."
    exit 0
fi

step "6/6  install unit + drop-ins, start the service"
DEPLOY="$REPO/$PROJECT_REL/deploy/systemd"
sudo install -m 0644 "$DEPLOY/rmt-control-center.service" /etc/systemd/system/rmt-control-center.service
sudo mkdir -p /etc/systemd/system/rmt-control-center.service.d
for c in cap04-loop.conf cap05-agent.conf bind-loopback.conf hardening.conf; do
    sudo install -m 0644 "$DEPLOY/$c" "/etc/systemd/system/rmt-control-center.service.d/$c"
    echo "  installed $c"
done
sudo systemctl daemon-reload

cat <<'MANUAL'

  ------------------------------------------------------------------
  MANUAL steps this script deliberately does NOT do (secrets / CA):
    1. operator tokens (S1/S2-lite) -- T0-5: a systemd credential, not an
       Environment= value (DEPLOY.md 1.2):
         sudo install -d -m 0700 /etc/rmt
         sudo install -m 0600 /dev/null /etc/rmt/operator_tokens.secret
         echo "alice:$(openssl rand -hex 24),bob:$(openssl rand -hex 24)" \
           | sudo tee /etc/rmt/operator_tokens.secret >/dev/null
         sudo install -m 0644 deploy/systemd/auth.conf.example \
           /etc/systemd/system/rmt-control-center.service.d/auth.conf
    2. Caddy TLS proxy (S4):  DEPLOY.md 1.4  (apt install caddy;
       cp deploy/Caddyfile /etc/caddy/Caddyfile; caddy trust)
    3. journald cap (O1):     DEPLOY.md 5.2
    4. cron: rmt-evidence-backup.sh + rmt-heartbeat.sh
       (RMT_EVIDENCE_RECOVERY.md, CONFIG.md)
  Without a populated /etc/rmt/operator_tokens.secret the app REFUSES to
  start (RMT_AUTH_ENABLED defaults on). Do this before the next line.
  ------------------------------------------------------------------

MANUAL
read -r -p "  operator tokens installed? start the service now? [y/N] " ans
[ "$ans" = "y" ] || [ "$ans" = "Y" ] || { echo "Stopped before start. Run: sudo systemctl enable --now rmt-control-center.service"; exit 0; }

sudo systemctl enable --now rmt-control-center.service
ok=0
for _ in $(seq 1 30); do
    if curl -sf -m2 http://127.0.0.1:8000/health >/dev/null 2>&1; then ok=1; break; fi
    sleep 1
done
[ "$ok" -eq 1 ] || { sudo journalctl -u rmt-control-center.service -n 40 --no-pager; die "service did not answer /health on :8000"; }
step "service healthy"
curl -s -m5 http://127.0.0.1:8000/health | "$BACKEND/.venv/bin/python" -m json.tool
echo
echo "REBUILD COMPLETE. Verify the LAN entry point (Caddy) and the cron jobs, then"
echo "confirm the CAP-04 loop: curl -s http://127.0.0.1:8000/homelab/loop/status"
