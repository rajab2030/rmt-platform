#!/bin/bash

set -e

if [ $# -ne 2 ]; then
    echo "Usage:"
    echo "./restore-volume.sh <backup-file> <volume-name>"
    echo
    echo "Example:"
    echo "./restore-volume.sh lab_portainer_data.tar.gz restore_test_portainer"
    exit 1
fi

BACKUP_FILE=$1
VOLUME=$2

echo "====================================="
echo " Docker Volume Restore"
echo "====================================="

echo
echo "Backup:"
echo "$BACKUP_FILE"

echo
echo "Target volume:"
echo "$VOLUME"

echo

if ! docker volume inspect "$VOLUME" >/dev/null 2>&1
then
    echo "Creating volume $VOLUME"
    docker volume create "$VOLUME"
fi

docker run --rm \
  -v "$VOLUME":/volume \
  -v "$(pwd)":/backup \
  alpine \
  sh -c "rm -rf /volume/* && tar xzf /backup/$BACKUP_FILE -C /volume"

echo
echo "Restore completed."
