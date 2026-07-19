#!/bin/bash

echo "========================================="
echo "      HomeLab Infrastructure Inventory"
echo "========================================="
echo

echo "Date:"
date

echo
echo "Hostname:"
hostname

echo
echo "Ubuntu Version:"
lsb_release -d

echo
echo "Kernel:"
uname -r

echo
echo "IP Address:"
hostname -I

echo
echo "Docker Version:"
docker --version

echo
echo "Docker Compose:"
docker compose version

echo
echo "-----------------------------------------"
echo "Running Containers"
echo "-----------------------------------------"
docker ps

echo
echo "-----------------------------------------"
echo "Docker Volumes"
echo "-----------------------------------------"
docker volume ls

echo
echo "-----------------------------------------"
echo "Docker Networks"
echo "-----------------------------------------"
docker network ls

echo
echo "-----------------------------------------"
echo "Docker Images"
echo "-----------------------------------------"
docker images

echo
echo "-----------------------------------------"
echo "Disk Usage"
echo "-----------------------------------------"
df -h

echo
echo "-----------------------------------------"
echo "Memory"
echo "-----------------------------------------"
free -h

echo
echo "========================================="
echo "Inventory Complete"
echo "========================================="
