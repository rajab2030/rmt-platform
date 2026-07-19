#!/bin/bash

set -e

BACKUP_ROOT="$HOME/homelab/backups/daily"
DATE=$(date +%F_%H-%M)

VOLUME_BACKUP_DIR="$BACKUP_ROOT/$DATE/volumes"

mkdir -p "$VOLUME_BACKUP_DIR"

echo "====================================="
echo " Docker Volume Backup"
echo "====================================="

VOLUMES=$(docker volume ls -q)

for VOLUME in $VOLUMES
do
    echo
    echo "Backing up volume: $VOLUME"

    docker run --rm \
      -v "$VOLUME":/volume \
      -v "$VOLUME_BACKUP_DIR":/backup \
      alpine \
      tar czf "/backup/${VOLUME}.tar.gz" -C /volume .

done

echo
echo "Volume backup completed."
echo "Location:"
echo "$VOLUME_BACKUP_DIR"
