"""
SIM-WORLD
=========
A deterministic, isolated simulated operational environment.

Contains:
  * production state (services)
  * service configuration
  * inventory / resources
  * operational health
  * action history

Every mutation goes through `World.apply()`. Every mutation produces an
observable state change or an explicit rejection. No real infrastructure is
touched.

This module is part of the isolated MCR experiment and is NOT part of the
existing RMT core.
"""

from __future__ import annotations

import copy
import json
import time
from typing import Any, Dict, List, Optional

SERVICE_NAMES = ["web", "db", "cache", "worker"]

INITIAL_SERVICES: Dict[str, Dict[str, Any]] = {
    "web": {
        "status": "running",
        "health": "healthy",
        "config": {"replicas": 2, "version": "v1.4.0", "tls": True},
        "uptime_s": 3600,
    },
    "db": {
        "status": "running",
        "health": "healthy",
        "config": {"pool_size": 20, "version": "v14.2", "backup": True},
        "uptime_s": 86400,
    },
    "cache": {
        "status": "running",
        "health": "healthy",
        "config": {"maxmemory": "256mb", "version": "v7.0", "eviction": "allkeys-lru"},
        "uptime_s": 7200,
    },
    "worker": {
        "status": "stopped",
        "health": "down",
        "config": {"concurrency": 4, "version": "v1.4.0", "queue": "default"},
        "uptime_s": 0,
    },
}

INITIAL_RESOURCES: Dict[str, Dict[str, Any]] = {
    "cpu": {"used_pct": 42, "total_cores": 8},
    "memory": {"used_pct": 61, "total_gb": 16},
    "disk": {"used_pct": 55, "total_gb": 200},
    "licenses": {"used": 3, "total": 5},
}


class World:
    """Deterministic simulated operational environment."""

    def __init__(self, seed: int = 0) -> None:
        self.services: Dict[str, Dict[str, Any]] = copy.deepcopy(INITIAL_SERVICES)
        self.resources: Dict[str, Dict[str, Any]] = copy.deepcopy(INITIAL_RESOURCES)
        self.action_history: List[Dict[str, Any]] = []
        self._seed = seed
        self._clock = 0

    # -- observation ------------------------------------------------------

    def snapshot(self) -> Dict[str, Any]:
        return {
            "services": copy.deepcopy(self.services),
            "resources": copy.deepcopy(self.resources),
            "action_count": len(self.action_history),
        }

    def get_service(self, name: str) -> Optional[Dict[str, Any]]:
        if name not in self.services:
            return None
        return copy.deepcopy(self.services[name])

    def operational_health(self) -> Dict[str, str]:
        return {name: svc["health"] for name, svc in self.services.items()}

    # -- mutation (the ONLY way to change state) --------------------------

    def apply(self, operation: str, target: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        params = params or {}
        self._clock += 1
        before = self.snapshot()

        result = self._dispatch(operation, target, params)

        record = {
            "seq": self._clock,
            "ts": time.time(),
            "operation": operation,
            "target": target,
            "params": params,
            "accepted": result["accepted"],
            "message": result["message"],
        }
        self.action_history.append(record)

        after = self.snapshot()
        result["before"] = before
        result["after"] = after
        result["record"] = record
        return result

    def _dispatch(self, operation: str, target: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if target not in self.services:
            return {"accepted": False, "message": f"unknown service '{target}'"}

        svc = self.services[target]

        if operation == "start":
            if svc["status"] == "running":
                return {"accepted": False, "message": f"{target} already running"}
            svc["status"] = "running"
            svc["health"] = "healthy"
            svc["uptime_s"] = 0
            return {"accepted": True, "message": f"{target} started"}

        if operation == "stop":
            if svc["status"] == "stopped":
                return {"accepted": False, "message": f"{target} already stopped"}
            svc["status"] = "stopped"
            svc["health"] = "down"
            svc["uptime_s"] = 0
            return {"accepted": True, "message": f"{target} stopped"}

        if operation == "restart":
            if svc["status"] == "stopped":
                return {"accepted": False, "message": f"{target} is stopped; use start"}
            svc["status"] = "running"
            svc["health"] = "healthy"
            svc["uptime_s"] = 0
            return {"accepted": True, "message": f"{target} restarted"}

        if operation == "update_config":
            key = params.get("key")
            value = params.get("value")
            if key is None:
                return {"accepted": False, "message": "update_config requires 'key'"}
            svc["config"][key] = value
            svc["health"] = "degraded"
            return {"accepted": True, "message": f"{target}.config.{key} updated"}

        if operation == "run_command":
            # Generic command execution. In the initial build this is a
            # consequential operation that is NOT routed through MCR.
            command = params.get("command", "")
            if "restart" in command:
                if svc["status"] == "stopped":
                    return {"accepted": False, "message": f"{target} is stopped"}
                svc["status"] = "running"
                svc["health"] = "healthy"
                svc["uptime_s"] = 0
                return {"accepted": True, "message": f"{target} restarted via command"}
            if "stop" in command:
                svc["status"] = "stopped"
                svc["health"] = "down"
                svc["uptime_s"] = 0
                return {"accepted": True, "message": f"{target} stopped via command"}
            if "start" in command:
                svc["status"] = "running"
                svc["health"] = "healthy"
                svc["uptime_s"] = 0
                return {"accepted": True, "message": f"{target} started via command"}
            return {"accepted": False, "message": f"unrecognized command '{command}'"}

        return {"accepted": False, "message": f"unknown operation '{operation}'"}

    # -- scenario setup ----------------------------------------------------

    def set_service(self, name: str, status: str, health: str) -> None:
        if name not in self.services:
            raise ValueError(f"unknown service {name}")
        self.services[name]["status"] = status
        self.services[name]["health"] = health

    def to_json(self) -> str:
        return json.dumps(self.snapshot(), indent=2, sort_keys=True)
