#!/bin/bash

set -e

BACKUP_ROOT="$HOME/homelab/backups/daily"

DATE=$(date +%F_%H-%M)

BACKUP_DIR="$BACKUP_ROOT/$DATE"

mkdir -p "$BACKUP_DIR"

echo "====================================="
echo " HomeLab Unified Backup v1.2"
echo "====================================="

echo
echo "Backup location:"
echo "$BACKUP_DIR"


echo
echo "[1/6] Backing up Docker stacks..."

cp -r "$HOME/homelab/docker" "$BACKUP_DIR/"


echo
echo "[2/6] Backing up documentation..."

cp -r "$HOME/homelab/docs" "$BACKUP_DIR/"


echo
echo "[3/6] Backing up scripts..."

cp -r "$HOME/homelab/scripts" "$BACKUP_DIR/"


echo
echo "[4/6] Exporting Docker metadata..."

docker ps -a > "$BACKUP_DIR/docker-containers.txt"

docker images > "$BACKUP_DIR/docker-images.txt"

docker volume ls > "$BACKUP_DIR/docker-volumes.txt"


echo
echo "Configuration backup completed."

echo
echo "Current backup contents:"
tree "$BACKUP_DIR"
