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

# Only a file in the current backup directory and a named Docker volume are
# valid inputs. In particular, a volume argument must never become a host bind.
case "$BACKUP_FILE" in
    ""|*/*|.|..) echo "Backup must be a filename in the current directory." >&2; exit 1 ;;
esac
if [ ! -f "$BACKUP_FILE" ]; then
    echo "Backup file does not exist." >&2
    exit 1
fi
if [[ ! "$VOLUME" =~ ^[a-zA-Z0-9][a-zA-Z0-9_.-]+$ ]]; then
    echo "Target must be a named Docker volume." >&2
    exit 1
fi

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
  -v "$(pwd)":/backup:ro \
  alpine \
  sh -c 'tar tzf "/backup/$1" >/dev/null && rm -rf /volume/* && tar xzf "/backup/$1" -C /volume' \
  restore-volume "$BACKUP_FILE"

echo
echo "Restore completed."
