#!/usr/bin/env bash
# RMT-PROD P1 (E5) -- back up the RMT governance evidence.
#
# Captures, into ~/homelab/backups/rmt-evidence/<UTC timestamp>/ :
#   governance_evidence.db  hot-safe VACUUM INTO snapshot of the six governance
#                      evidence stores (T0-1; was six JSON files under stores/)
#   stores/       any residual *.json / *.json.migrated evidence files (present
#                      only before the T0-1 migration has been run)
#   archives/     *.archive.jsonl companions (E4 retention archive)
#   observability.db   a hot-safe snapshot (VACUUM INTO) -- intelligence_memory
#                      is the Learn-stage evidence
#   manifest.txt  git commit, host, date, per-store record counts
#   checksum.sha256   sha256 of every file above
#
# Read-only against the live tree -- safe to run while the service is up.
# Pairs with rmt-evidence-restore.sh and rmt_evidence_verify.py.
set -euo pipefail

BACKEND="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CI="$BACKEND/app/core/intelligence"
DATA="$BACKEND/data"
DB="$DATA/observability.db"
EVID_DB="${RMT_EVIDENCE_DB:-$DATA/governance_evidence.db}"
DEST_ROOT="${RMT_BACKUP_ROOT:-$HOME/homelab/backups/rmt-evidence}"
STAMP="$(date -u +%Y-%m-%dT%H-%M-%SZ)"
DEST="$DEST_ROOT/$STAMP"

mkdir -p "$DEST/stores" "$DEST/archives"

echo "RMT evidence backup -> $DEST"

# 1. governance evidence -- hot-safe snapshot of the shared SQLite db (T0-1)
if [ -f "$EVID_DB" ]; then
    if command -v sqlite3 >/dev/null 2>&1; then
        sqlite3 "$EVID_DB" "VACUUM INTO '$DEST/governance_evidence.db'"
    else
        cp -p "$EVID_DB" "$DEST/governance_evidence.db"
        echo "WARN: sqlite3 not found -- governance_evidence.db copied raw"
    fi
fi
#    plus any residual JSON stores (pre-migration hosts only)
find "$CI" \( -name '*.json' -o -name '*.json.migrated' \) \
    -exec cp -p {} "$DEST/stores/" \; 2>/dev/null || true
rmdir "$DEST/stores" 2>/dev/null || true   # drop if empty

# 2. E4 retention archives (may be none yet) -- now beside the db, under data/
find "$CI" "$DATA" -name '*.archive.jsonl' \
    -exec cp -p {} "$DEST/archives/" \; 2>/dev/null || true
rmdir "$DEST/archives" 2>/dev/null || true   # drop if empty

# 3. observability.db -- hot-safe snapshot
if [ -f "$DB" ]; then
    if command -v sqlite3 >/dev/null 2>&1; then
        sqlite3 "$DB" "VACUUM INTO '$DEST/observability.db'"
    else
        cp -p "$DB" "$DEST/observability.db"   # last resort; may be torn
        echo "WARN: sqlite3 not found -- observability.db copied raw (may be inconsistent)"
    fi
fi

# 4. manifest
{
    echo "RMT evidence backup"
    echo "date_utc:    $STAMP"
    echo "host:        $(hostname)"
    echo "backend:     $BACKEND"
    echo "git_commit:  $(git -C "$BACKEND" rev-parse HEAD 2>/dev/null || echo unknown)"
    echo "git_branch:  $(git -C "$BACKEND" rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)"
    echo
    if [ -f "$DEST/governance_evidence.db" ] && command -v sqlite3 >/dev/null 2>&1; then
        echo "governance_evidence.db table counts:"
        for t in approval_holds approval_records authorizations traces audit verifications; do
            n="$(sqlite3 "$DEST/governance_evidence.db" \
                 "SELECT count(*) FROM \"$t\"" 2>/dev/null || echo '?')"
            printf '  %-26s %s\n' "$t" "$n"
        done
    fi
    if compgen -G "$DEST/stores/*.json" >/dev/null 2>&1; then
        echo "residual JSON store record counts:"
        for f in "$DEST"/stores/*.json; do
            printf '  %-26s %s\n' "$(basename "$f")" \
              "$(python3 -c 'import json,sys; print(len(json.load(open(sys.argv[1]))))' "$f")"
        done
    fi
    if [ -d "$DEST/archives" ]; then
        echo
        echo "archive line counts:"
        for f in "$DEST"/archives/*.archive.jsonl; do
            printf '  %-26s %s\n' "$(basename "$f")" "$(grep -c . "$f" || true)"
        done
    fi
} > "$DEST/manifest.txt"

# 5. checksums (over everything except the checksum file itself)
( cd "$DEST" && find . -type f ! -name checksum.sha256 -print0 \
    | sort -z | xargs -0 sha256sum > checksum.sha256 )

echo
echo "OK. Files:"
( cd "$DEST" && find . -type f | sort )
echo
echo "Verify:  python3 $BACKEND/scripts/rmt_evidence_verify.py $DEST"
echo "$DEST"
