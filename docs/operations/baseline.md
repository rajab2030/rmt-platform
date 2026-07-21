# HomeLab Platform Baseline

Date: 2026-07-21

Purpose:
Document the known healthy state of the HomeLab platform for operational reference and future troubleshooting.

## Hardware

Platform Type:
VMware Virtual Platform

Hypervisor:
VMware

Virtualization:
Full virtualization

CPU Architecture:
x86_64

Assigned CPU:
Intel(R) Core(TM) i9-10885H CPU @ 2.40GHz

Assigned vCPUs:
4

CPU Virtualization Support:
VT-x

## Operating System

Distribution:
Ubuntu

Version:
Ubuntu 24.04.4 LTS

Codename:
noble

Kernel:
Linux 6.8.0-136-generic

Architecture:
x86-64

Hostname:
rmt-lab

Virtualization:
VMware

Hardware Model:
VMware Virtual Platform

## Docker Environment

Docker Engine:
Docker version 29.6.2

Docker Compose:
v5.3.1

Docker Service:
Active (running)

Docker Service Start Time:
Sat 2026-07-18 21:25:41 UTC

Docker Enabled at Boot:
Yes

## Docker Services

| Service | Image | Status | Ports |
|---|---|---|---|
| portainer | portainer/portainer-ce:latest | Running | 9000, 9443 |
| dozzle | amir20/dozzle:v8.13.6 | Running | 8888 -> 8080 |
| uptime-kuma | louislam/uptime-kuma:latest | Running (healthy) | 3001 |
