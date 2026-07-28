# RMT Platform Core Architecture v0.3

## Purpose

This document defines the refined architecture baseline of the RMT Platform Core.

The objective of the RMT Platform is to provide a reusable foundation for running and managing independent application modules.

The platform is responsible for module management, identity, configuration, health monitoring, and runtime control.

Applications are treated as modules running on top of the platform core.

---

# Core Architecture Principle


Applications
|
v
RMT Platform Core
|
v
Infrastructure Layer


The platform is the management layer.

Applications are not tightly coupled to infrastructure.

---

# RMT Platform Core Components


RMT Platform Core

├── Identity Service
│
├── Module Factory
│
├── Module Registry
│
├── Configuration Layer
│
├── Health Manager
│
└── Runtime Controller


---

# Implemented Components

# Identity Service

Location:


app/core/identity


Responsibility:

The Identity Service manages technical identity generation for modules.

Current responsibility:

- Generate unique module IDs
- Provide identity utilities

Example:

Input:


RMT AI Assistant


Output:


rmt-ai-assistant-e04095

# Module Factory

Location:


app/core/module_factory


Responsibility:

The Module Factory creates validated Module objects.

Responsibilities:

- Create Module instances
- Apply default runtime information
- Apply default health state
- Prepare objects before registration

Flow:


Module Request

  |

  v

Module Factory

  |

  v

Valid Module Object

  |

  v

Module Registry


Current function:


create_module()


The Identity Service does not create or register modules.

# 2. Module Registry

Location:


app/core/module_registry


Responsibility:

Maintain the catalog of platform modules.

Current storage:


modules.json


Future migration:


JSON
|
v
SQLite
|
v
Enterprise Database

The Module Registry does not create modules.

It only manages persistence and discovery of existing modules.
---

# Registry Responsibilities

The Registry handles:

- Module registration
- Module discovery
- Module retrieval
- Persistent storage

The Registry does not generate identities.

---

# Identity and Registry Separation

Design decision:

Identity creation and module registration are separate responsibilities.

Correct flow:


Create Module Identity

    |

    v

Create Module Object

    |

    v

Register Module

    |

    v

Persist Registry


---

# Module Model

Every module contains:


Identity
Runtime
Health
Configuration
Lifecycle State


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
Module Lifecycle

Defined states:

registered
     |
     v
active
     |
     v
updating
     |
     v
disabled
     |
     v
removed
Health Model

Health states:

unknown
starting
healthy
degraded
failed
disabled
Frontend Configuration Decision

Current MVP solution:

VITE_API_URL

Example:

http://server-ip:8000

This is temporary.

Future architecture:

Frontend must not depend on fixed IP addresses.

Target:

Browser

   |

Frontend Gateway

   |

Backend API

This allows deployment on:

Virtual Machines
Physical Servers
Cloud Infrastructure

without changing application code.

Technical Debt
RMT-TD-001

Frontend API endpoint configuration.

Status:

Temporary solution implemented.

Future:

Central Configuration Layer.

RMT-TD-002

Manual process management.

Current:

Manual restart / PID handling.

Future:

Runtime Controller.

RMT-TD-003

Static service references.

Example:

Test containers referenced manually.

Future:

Dynamic discovery.

RMT-TD-004

Python package execution standardization.

Future:

Proper package installation and execution model.

Current Registered Modules
Control Center
module_id:
control-center

type:
platform-service

status:
active
AI Assistant
module_id:
rmt-ai-assistant-e04095

type:
platform-service

status:
active
Next Development Milestone
RMT-009 Configuration Layer

Objectives:

Remove hard-coded:

IP addresses
Ports
Environment variables
Deployment settings

Create centralized platform configuration management.

Document Status

Version:

RMT Platform Core v0.3

Status:

Architecture Refinement Baseline

بعد الحفظ:

```bash
cat docs/architecture/RMT-Platform-Core-v0.3.md


# Design Decisions

# Refinement Decisions

## Identity Separation

Module identity generation is separated from module creation.

## Factory Pattern Introduction

Module creation is centralized through Module Factory.

## Registry Responsibility

Registry is responsible only for storage and discovery.

## Configuration Future

Environment-specific values will be moved into Configuration Layer.
