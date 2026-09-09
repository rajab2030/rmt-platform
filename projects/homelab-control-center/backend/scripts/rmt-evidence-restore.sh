#!/usr/bin/env bash
# RMT-PROD P1 (E5) -- restore the RMT governance evidence from a backup.
#
# Usage:  rmt-evidence-restore.sh <backup-dir> [--force]
#
#   <backup-dir>   a directory made by rmt-evidence-backup.sh
#   --force        skip the "is the service stopped?" guard (you know why)
#
# Steps: verify checksums -> verify integrity -> refuse if the service is up ->
# restore into place -> re-verify the live tree. The current live files are
# moved aside to <name>.pre-restore.<ts> first.
#
# Two backup shapes are handled:
#   * T0-1+  : governance_evidence.db  -> backend/data/governance_evidence.db
#   * pre-T0-1: stores/*.json          -> backend/app/core/intelligence/**  then
#              backend/scripts/rmt-migrate-evidence.py --force loads them into
#              backend/data/governance_evidence.db (needs the venv).
# Archives (*.archive.jsonl) and observability.db restore to backend/data/.
set -euo pipefail

BACKEND="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CI="$BACKEND/app/core/intelligence"
DATA="$BACKEND/data"
SRC="${1:?usage: rmt-evidence-restore.sh <backup-dir> [--force]}"
FORCE="${2:-}"
SERVICE="rmt-control-center.service"

[ -d "$SRC" ] || { echo "FAIL: not a directory: $SRC"; exit 1; }
[ -f "$SRC/checksum.sha256" ] || { echo "FAIL: no checksum.sha256 in $SRC"; exit 1; }

echo "[1/5] Verifying checksums..."
( cd "$SRC" && sha256sum -c checksum.sha256 )

echo "[2/5] Verifying integrity of the backup..."
python3 "$BACKEND/scripts/rmt_evidence_verify.py" "$SRC" \
    || { echo "FAIL: backup failed integrity check -- aborting"; exit 1; }

echo "[3/5] Checking the service is stopped..."
if [ "$FORCE" != "--force" ] && command -v systemctl >/dev/null 2>&1; then
    if systemctl is-active --quiet "$SERVICE"; then
        echo "FAIL: $SERVICE is running. Stop it first:"
        echo "        sudo systemctl stop $SERVICE"
        echo "     (or pass --force if you are restoring into a stopped copy)"
        exit 1
    fi
fi

echo "[4/5] Restoring files..."
TS="$(date -u +%Y-%m-%dT%H-%M-%SZ)"
mkdir -p "$DATA"

if [ -f "$SRC/governance_evidence.db" ]; then
    # T0-1+ backup: restore the shared SQLite evidence db directly.
    for ext in "" "-wal" "-shm"; do
        live="$DATA/governance_evidence.db$ext"
        [ -f "$live" ] && mv "$live" "$live.pre-restore.$TS"
    done
    cp -p "$SRC/governance_evidence.db" "$DATA/governance_evidence.db"
    echo "  restored governance_evidence.db -> $DATA/"
elif compgen -G "$SRC/stores/*.json" >/dev/null 2>&1; then
    # pre-T0-1 backup: restore the JSON stores, then migrate them into the db.
    for f in "$SRC"/stores/*.json; do
        name="$(basename "$f")"
        dst="$(find "$CI" -name "$name" | head -n1)"
        [ -z "$dst" ] && dst="$(find "$CI" -name "$name.migrated" | head -n1)"
        dst="${dst%.migrated}"
        if [ -z "$dst" ]; then
            echo "  WARN: no live location for $name -- skipped"
            continue
        fi
        [ -f "$dst" ] && mv "$dst" "$dst.pre-restore.$TS"
        cp -p "$f" "$dst"
        echo "  restored $name -> $dst"
    done
    echo "  migrating restored JSON stores into governance_evidence.db..."
    if [ -x "$BACKEND/.venv/bin/python" ]; then
        [ -f "$DATA/governance_evidence.db" ] && \
            mv "$DATA/governance_evidence.db" \
               "$DATA/governance_evidence.db.pre-restore.$TS"
        "$BACKEND/.venv/bin/python" "$BACKEND/scripts/rmt-migrate-evidence.py" \
            --force
    else
        echo "  WARN: no $BACKEND/.venv -- run this yourself after restore:"
        echo "        .venv/bin/python scripts/rmt-migrate-evidence.py --force"
    fi
else
    echo "FAIL: backup has neither governance_evidence.db nor stores/*.json"
    exit 1
fi

# E4 retention archives -> backend/data/ (T0-1 location)
if [ -d "$SRC/archives" ]; then
    for f in "$SRC"/archives/*.archive.jsonl; do
        [ -e "$f" ] || continue
        live="$DATA/$(basename "$f")"
        [ -f "$live" ] && mv "$live" "$live.pre-restore.$TS"
        cp -p "$f" "$live"
        echo "  restored $(basename "$f") -> $DATA/"
    done
fi

if [ -f "$SRC/observability.db" ]; then
    [ -f "$DATA/observability.db" ] && \
        mv "$DATA/observability.db" "$DATA/observability.db.pre-restore.$TS"
    cp -p "$SRC/observability.db" "$DATA/observability.db"
    echo "  restored observability.db -> $DATA/"
fi

echo "[5/5] Verifying the restored live tree..."
python3 "$BACKEND/scripts/rmt_evidence_verify.py" "$BACKEND"

echo
echo "Done. Previous files kept as *.pre-restore.$TS -- remove once confirmed."
echo "Start the service:  sudo systemctl start $SERVICE"
