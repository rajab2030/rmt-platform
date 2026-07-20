#!/bin/bash

set -e

echo "====================================="
echo " HomeLab Recovery Verification v1.0"
echo "====================================="

echo

FAIL=0

echo "[1/5] Checking Docker availability"

if docker info >/dev/null 2>&1
then
    echo "OK: Docker available"
else
    echo "FAIL: Docker unavailable"
    FAIL=1
fi


echo
echo "[2/5] Checking recovery containers"

EXPECTED_CONTAINERS=(
"recovery-portainer"
"uptime-kuma"
"dozzle"
)

for CONTAINER in "${EXPECTED_CONTAINERS[@]}"
do
    if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER}$"
    then
        echo "OK: $CONTAINER running"
    else
        echo "FAIL: $CONTAINER missing"
        FAIL=1
    fi
done


echo
echo "[3/5] Checking published ports"

EXPECTED_PORTS=(
"9443"
"9000"
"3001"
"8888"
)

for PORT in "${EXPECTED_PORTS[@]}"
do
    if ss -tuln | grep -q ":$PORT "
    then
        echo "OK: Port $PORT listening"
    else
        echo "FAIL: Port $PORT unavailable"
        FAIL=1
    fi
done


echo
echo "[4/5] Checking Portainer HTTPS response"

if curl -k -s https://localhost:9443 | grep -q "Portainer"
then
    echo "OK: Portainer HTTPS reachable"
else
    echo "FAIL: Portainer HTTPS unreachable"
    FAIL=1
fi


echo
echo "[5/5] Recovery verification result"

if [ $FAIL -eq 0 ]
then
    echo "====================================="
    echo " RECOVERY VERIFIED SUCCESSFULLY"
    echo "====================================="
    exit 0
else
    echo "====================================="
    echo " RECOVERY VERIFICATION FAILED"
    echo "====================================="
    exit 1
fi
