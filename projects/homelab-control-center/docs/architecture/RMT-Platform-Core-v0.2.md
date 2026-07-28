# RMT Platform Core Architecture v0.2

## Document Purpose

This document defines the architecture baseline of the RMT Platform Core.

The purpose of the platform is not to build isolated applications, but to create a flexible and reusable foundation capable of hosting, managing, and operating different applications as independent modules.

The platform is designed to remain independent from specific hardware, operating systems, deployment environments, or application domains.

---

# Vision

RMT Platform is a modular platform where applications are treated as managed components running on top of a common operational foundation.

Future examples of platform modules:

- Banking Risk Management Platform
- French Language Learning Platform
- Budget Management Application
- AI Assistant Module
- Future business and technical services

Applications are not the core.

The platform core is the foundation that manages applications.

---

# Core Architecture Principle

The architecture follows the principle:


Applications are Modules.

Modules run on the Platform Core.

The Platform Core manages Identity, Runtime, Health, and Configuration.


---

# High-Level Architecture


+--------------------------------+
| RMT Applications |
| |
| Risk Management Module |
| Language Learning Module |
| Budget Module |
| AI Assistant Module |
+---------------+----------------+
|
|
v
+--------------------------------+
| RMT Platform Core |
| |
| Module Registry |
| Identity Service |
| Configuration Layer |
| Health Management |
| Runtime Controller |
+---------------+----------------+
|
|
v
+--------------------------------+
| Infrastructure Layer |
| |
| Docker |
| Ubuntu Server |
| Virtual Machines |
| Cloud Infrastructure |
+--------------------------------+


---

# Current Implementation Status

## RMT Platform Core v0.2

Implemented components:

- Module Registry
- Module Schema Definition
- Automatic Module Identity Generation
- Module Registration Flow
- Persistent Module Storage using JSON

---

# Core Components

## 1. Module Registry

Location:


app/core/module_registry


Purpose:

The Module Registry is the central catalog of all registered platform modules.

Responsibilities:

- Store module definitions
- Retrieve registered modules
- Provide module discovery
- Maintain module metadata

Current storage:


modules.json


Future migration:


JSON
|
v
SQLite
|
v
Distributed Database


---

# 2. Module Schema

Each registered module follows a defined structure.

Example:

```json
{
    "module_id": "",
    "name": "",
    "version": "",
    "type": "",
    "status": "",
    "runtime": {},
    "health": {}
}

A module must contain:

Identity Information

Example:

module_id
name
version
type
Runtime Information

Example:

engine
container
ports
Health Information

Example:

status
endpoint
last_check
3. Identity Service

Location:

app/core/identity

Purpose:

The Identity Service provides automatic technical identity generation for modules.

Manual module IDs are avoided.

Example:

Input:

RMT AI Assistant

Generated identity:

rmt-ai-assistant-e04095

Identity format:

module-name + unique identifier
4. Module Registration Flow

Current registration process:

New Module
     |
     v
Generate Module Identity
     |
     v
Create Module Object
     |
     v
Validate Module Schema
     |
     v
Register Module
     |
     v
Persist Registry
     |
     v
modules.json
Current Registered Modules
Control Center Module
Module ID:
control-center

Name:
RMT Platform Control Center

Type:
platform-service

Runtime:
Docker

Status:
Active

Health:
Healthy
AI Assistant Module
Module ID:
rmt-ai-assistant-e04095

Name:
RMT AI Assistant

Type:
platform-service

Runtime:
Docker

Status:
Active

Health:
Unknown

Note:

The AI Assistant is currently registered as a platform module definition.

The runtime implementation will be developed in future phases.

API Integration

Current API endpoint:

GET /modules

Purpose:

Expose registered modules through the platform API.

Example response:

[
    {
        "module_id": "control-center",
        "name": "RMT Platform Control Center"
    },
    {
        "module_id": "rmt-ai-assistant-e04095",
        "name": "RMT AI Assistant"
    }
]
Architectural Decisions
Decision 1 — Modular Architecture

Applications are developed as independent modules.

The platform provides the common management foundation.

Decision 2 — Automatic Identity Generation

Module identities are generated automatically.

Reason:

Prevent duplication
Enable scalability
Support distributed environments
Decision 3 — JSON Registry Storage

The initial registry uses JSON.

Reasons:

Simple implementation
Easy debugging
Human readable
Suitable for MVP validation

Migration path:

JSON Registry

      |

      v

SQLite Registry

      |

      v

Enterprise Database
Known Technical Debt
RMT-TD-001

Configuration values are still partially hard-coded.

Examples:

IP addresses
Ports
CORS origins

Solution:

Configuration Layer.

RMT-TD-002

Manual process management during development.

Current:

kill PID
restart service

Future:

Runtime Controller.

RMT-TD-003

Collector contains old test references.

Example:

rmt-test-nginx

Solution:

Dynamic service discovery.

Future Core Components
Configuration Layer

Purpose:

Centralize:

Environment settings
Network configuration
Runtime parameters
Health Manager

Purpose:

Monitor:

Module availability
Service health
Runtime status
Runtime Controller

Purpose:

Manage:

Start
Stop
Restart
Deployment lifecycle
AI Assistant Module

AI will be implemented as a first-class platform module.

Capabilities:

Assistance
Automation
Code support
Analysis
Platform interaction
Next Milestone
RMT-009

Configuration Layer Implementation

Goal:

Remove environment-specific values from application code and make the platform portable across:

Local Server
Virtual Machine
Physical Hardware
Cloud Infrastructure
Document Status

Version:

RMT Platform Core v0.2

Status:

Architecture Foundation Established

بعد حفظ الملف، ستكون هذه أول وثيقة Architecture رسمية للـ **RMT Platform Core**، وبعدها ننتقل إلى RMT-009.
