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
echo "[5/6] Backing up Docker volumes..."

mkdir -p "$BACKUP_DIR/volumes"

for VOLUME in $(docker volume ls -q)
do
    echo "Backing up volume: $VOLUME"

    docker run --rm \
      -v "$VOLUME":/volume \
      -v "$BACKUP_DIR/volumes":/backup \
      alpine \
      tar czf "/backup/${VOLUME}.tar.gz" -C /volume .
done

echo
echo "[6/6] Generating backup manifest..."

cat > "$BACKUP_DIR/manifest.txt" <<EOF
HomeLab Backup Manifest
======================

Date:
$(date)

Hostname:
$(hostname)

Ubuntu:
$(lsb_release -ds)

Kernel:
$(uname -r)

Docker:
$(docker --version)

Containers:
$(docker ps --format '{{.Names}}')

Volumes:
$(docker volume ls -q)

EOF

echo
echo "Generating checksums..."

cd "$BACKUP_DIR"

sha256sum \
docker-containers.txt \
docker-images.txt \
docker-volumes.txt \
manifest.txt \
volumes/*.tar.gz \
> checksum.sha256

echo "Checksum generated."
echo
echo "Configuration backup completed."

echo
echo "Current backup contents:"
tree "$BACKUP_DIR"
