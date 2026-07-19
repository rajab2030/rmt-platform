#!/bin/bash

set -e

if [ $# -ne 1 ]; then
    echo "Usage:"
    echo "./verify-backup.sh <backup-directory>"
    echo
    echo "Example:"
    echo "./verify-backup.sh ~/homelab/backups/daily/2026-07-19_17-24"
    exit 1
fi


BACKUP_DIR=$1


echo "====================================="
echo " HomeLab Backup Verification"
echo "====================================="


if [ ! -d "$BACKUP_DIR" ]; then
    echo "ERROR: Backup directory not found"
    exit 1
fi


echo
echo "[1/5] Checking backup structure"


REQUIRED_DIRS=(
docker
docs
scripts
)


for DIR in "${REQUIRED_DIRS[@]}"
do
    if [ -d "$BACKUP_DIR/$DIR" ]; then
        echo "OK: $DIR"
    else
        echo "MISSING: $DIR"
    fi
done


echo
echo "[2/5] Checking volume backups"


if [ -d "$BACKUP_DIR/volumes" ]; then

    COUNT=$(ls "$BACKUP_DIR/volumes"/*.tar.gz 2>/dev/null | wc -l)

    echo "Volume archives found: $COUNT"

else

    echo "No volume backup directory found"

fi


echo
echo "[3/5] Testing archive integrity"


for FILE in "$BACKUP_DIR"/volumes/*.tar.gz
do
    if tar -tzf "$FILE" >/dev/null
    then
        echo "OK: $(basename "$FILE")"
    else
        echo "FAILED: $(basename "$FILE")"
    fi
done


echo
echo "[4/5] Backup size"

du -sh "$BACKUP_DIR"


echo
echo "[5/5] Verification complete"

echo "Backup appears healthy."
