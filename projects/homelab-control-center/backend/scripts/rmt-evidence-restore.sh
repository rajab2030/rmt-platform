#!/usr/bin/env bash
# RMT-PROD P1 (E5) -- restore the RMT governance evidence from a backup.
#
# Usage:  rmt-evidence-restore.sh <backup-dir> [--force]
#
#   <backup-dir>   a directory made by rmt-evidence-backup.sh
#   --force        skip the "is the service stopped?" guard (you know why)
#
# Steps: verify checksums -> verify integrity -> refuse if the service is up ->
# copy stores + archives + observability.db into place -> re-verify the live
# tree. The current live stores are moved aside to <name>.pre-restore first.
set -euo pipefail

BACKEND="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CI="$BACKEND/app/core/intelligence"
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
for f in "$SRC"/stores/*.json; do
    name="$(basename "$f")"
    dst="$(find "$CI" -name "$name" | head -n1)"
    if [ -z "$dst" ]; then
        echo "  WARN: no live location for $name -- skipped"
        continue
    fi
    [ -f "$dst" ] && mv "$dst" "$dst.pre-restore.$TS"
    cp -p "$f" "$dst"
    echo "  restored $name -> $dst"
done
if [ -d "$SRC/archives" ]; then
    for f in "$SRC"/archives/*.archive.jsonl; do
        [ -e "$f" ] || continue
        base="$(basename "$f" .archive.jsonl).json"
        dstdir="$(dirname "$(find "$CI" -name "$base" | head -n1)")"
        [ -n "$dstdir" ] && cp -p "$f" "$dstdir/" && echo "  restored $(basename "$f")"
    done
fi
if [ -f "$SRC/observability.db" ]; then
    [ -f "$BACKEND/data/observability.db" ] && \
        mv "$BACKEND/data/observability.db" "$BACKEND/data/observability.db.pre-restore.$TS"
    cp -p "$SRC/observability.db" "$BACKEND/data/observability.db"
    echo "  restored observability.db"
fi

echo "[5/5] Verifying the restored live tree..."
python3 "$BACKEND/scripts/rmt_evidence_verify.py" "$BACKEND"

echo
echo "Done. Previous files kept as *.pre-restore.$TS -- remove once confirmed."
echo "Start the service:  sudo systemctl start $SERVICE"
