#!/bin/bash

set -e

BACKUP_ROOT="$HOME/homelab/backups/daily"
DATE=$(date +%F_%H-%M)

BACKUP_DIR="$BACKUP_ROOT/$DATE"

mkdir -p "$BACKUP_DIR"

echo "====================================="
echo " HomeLab Backup"
echo "====================================="

echo
echo "[1/6] Copying Docker Compose files..."

cp -r "$HOME/homelab/docker" "$BACKUP_DIR/"

echo
echo "[2/6] Copying documentation..."

cp -r "$HOME/homelab/docs" "$BACKUP_DIR/"

echo
echo "[3/6] Copying scripts..."

cp -r "$HOME/homelab/scripts" "$BACKUP_DIR/"

echo
echo "[4/6] Exporting container list..."

docker ps -a > "$BACKUP_DIR/docker-containers.txt"

echo
echo "[5/6] Exporting volume list..."

docker volume ls > "$BACKUP_DIR/docker-volumes.txt"

echo
echo "[6/6] Exporting image list..."

docker images > "$BACKUP_DIR/docker-images.txt"

echo
echo "Backup completed."

echo
echo "Location:"
echo "$BACKUP_DIR"
