# RMT Platform Control Center MVP v0.1

## Purpose

RMT Platform Control Center is the management layer of the RMT Platform. It provides visibility and control over infrastructure services and future applications.

The goal is to provide visibility into:
- Docker containers
- Service status
- System health

This MVP is a foundation for future platform services.

---

# MVP Scope

## Included

- Dashboard interface
- Docker container monitoring
- Service status display
- Basic system information

## Not Included

- User authentication
- Multi-user support
- Database
- Kubernetes
- Cloud deployment
- Advanced monitoring

---

# Architecture


Browser
|
|
Frontend (React)
|
|
Backend API (FastAPI)
|
|
Docker Engine API
|
|
Homelab Docker Services


---

# Technology Stack

## Frontend

React

## Backend

Python FastAPI

## Deployment

Docker Compose

## Runtime

Ubuntu + Docker

---

# First API Endpoint

GET /containers

Purpose:

Return running Docker containers and their status.

Example response:

```json
[
 {
  "name": "portainer",
  "status": "running"
 }
]
Design Principle

Build the smallest working platform component first.

Observe.
Measure.
Improve.
