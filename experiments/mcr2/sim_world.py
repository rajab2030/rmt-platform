"""
SIM-WORLD (Experiment #2)
=========================
A deterministic isolated operational world.

Critical property: there is EXACTLY ONE authoritative state-mutation boundary,
`World.mutate(...)`. All consequential changes to world state must pass through
it. The enforcement lives at the actual mutation point, not in the tool
registry.

The world's state is stored in a protected container that only accepts writes
from the sanctioned path (via a secret token held by World). Direct writes from
any other mechanism are blocked. This simulates a real enforcement boundary
(e.g. a database/API layer that only accepts authorized writes).

This is an isolated experiment and is NOT part of the RMT core.
"""

from __future__ import annotations

import copy
import json
import time
from typing import Any, Callable, Dict, List, Optional


class ProtectedState:
    """
    A state container that only allows mutation through the sanctioned path.
    Direct writes (bypassing the token) raise PermissionError.
    """

    def __init__(self, data: Dict[str, Any]) -> None:
        self._data = copy.deepcopy(data)
        self._token: Optional[object] = None

    def read(self) -> Dict[str, Any]:
        return copy.deepcopy(self._data)

    def write(self, token: object, fn: Callable[[Dict[str, Any]], Any]) -> Any:
        if token is not self._token:
            raise PermissionError("Direct state mutation blocked; use World.mutate()")
        return fn(self._data)


SERVICE_NAMES = ["web", "db", "cache", "worker"]

INITIAL_SERVICES: Dict[str, Dict[str, Any]] = {
    "web": {"status": "running", "health": "healthy",
            "config": {"replicas": 2, "version": "v1.4.0", "tls": True}, "uptime_s": 3600},
    "db": {"status": "running", "health": "healthy",
           "config": {"pool_size": 20, "version": "v14.2", "backup": True}, "uptime_s": 86400},
    "cache": {"status": "running", "health": "healthy",
              "config": {"maxmemory": "256mb", "version": "v7.0", "eviction": "allkeys-lru"}, "uptime_s": 7200},
    "worker": {"status": "stopped", "health": "down",
               "config": {"concurrency": 4, "version": "v1.4.0", "queue": "default"}, "uptime_s": 0},
}

INITIAL_RESOURCES: Dict[str, Dict[str, Any]] = {
    "cpu": {"used_pct": 42, "total_cores": 8},
    "memory": {"used_pct": 61, "total_gb": 16},
    "disk": {"used_pct": 55, "total_gb": 200},
    "licenses": {"used": 3, "total": 5},
}


class World:
    """Deterministic simulated operational world with a single mutation boundary."""

    def __init__(self, seed: int = 0) -> None:
        self._services = ProtectedState(INITIAL_SERVICES)
        self._resources = ProtectedState(INITIAL_RESOURCES)
        self._token = object()          # secret token for sanctioned writes
        self._services._token = self._token
        self._resources._token = self._token
        self._mcr = None                # bound by bind_mcr()
        self.action_history: List[Dict[str, Any]] = []
        self._clock = 0

    def bind_mcr(self, mcr: Any) -> None:
        self._mcr = mcr

    # -- observation ------------------------------------------------------

    def snapshot(self) -> Dict[str, Any]:
        return {
            "services": self._services.read(),
            "resources": self._resources.read(),
            "action_count": len(self.action_history),
        }

    def get_service(self, name: str) -> Optional[Dict[str, Any]]:
        return self._services.read().get(name)

    def operational_health(self) -> Dict[str, str]:
        return {n: s["health"] for n, s in self._services.read().items()}

    # -- THE authoritative mutation boundary ------------------------------

    def mutate(
        self,
        operation: str,
        target: str,
        params: Optional[Dict[str, Any]] = None,
        *,
        requester: str = "ATLAS",
        request_auth: bool = False,
        intent: str = "",
        observed: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        The single authoritative state-mutation boundary. Every consequential
        change to world state must pass through here. MCR is consulted before
        any mutation is applied.
        """
        params = params or {}
        if self._mcr is None:
            raise RuntimeError("MCR not bound to world; cannot govern mutations")

        # 1. MCR evaluates the mutation attempt.
        decision = self._mcr.evaluate(
            operation, target, params,
            requester=requester, request_auth=request_auth,
            intent=intent, observed=observed,
        )

        # 2. Only ALLOW proceeds to actual mutation.
        if decision["decision"] != "ALLOW":
            self._record(operation, target, params, decision, applied=False)
            return {
                "ok": False,
                "decision": decision["decision"],
                "message": decision["message"],
                "mcr": decision,
                "mutation_boundary": "blocked",
            }

        # 3. Sanctioned mutation.
        before = self.snapshot()
        result = self._apply(operation, target, params)
        after = self.snapshot()
        self._record(operation, target, params, decision, applied=result["accepted"])

        return {
            "ok": result["accepted"],
            "decision": "ALLOW",
            "message": result["message"],
            "mcr": decision,
            "mutation_boundary": "executed",
            "before": before,
            "after": after,
        }

    # -- sanctioned internal mutation (only reachable via mutate) ----------

    def _apply(self, operation: str, target: str, params: Dict[str, Any]) -> Dict[str, Any]:
        def fn(data: Dict[str, Any]) -> Dict[str, Any]:
            if target not in data:
                return {"accepted": False, "message": f"unknown service '{target}'"}
            svc = data[target]

            if operation == "start":
                if svc["status"] == "running":
                    return {"accepted": False, "message": f"{target} already running"}
                svc["status"] = "running"; svc["health"] = "healthy"; svc["uptime_s"] = 0
                return {"accepted": True, "message": f"{target} started"}

            if operation == "stop":
                if svc["status"] == "stopped":
                    return {"accepted": False, "message": f"{target} already stopped"}
                svc["status"] = "stopped"; svc["health"] = "down"; svc["uptime_s"] = 0
                return {"accepted": True, "message": f"{target} stopped"}

            if operation == "restart":
                if svc["status"] == "stopped":
                    return {"accepted": False, "message": f"{target} is stopped; use start"}
                svc["status"] = "running"; svc["health"] = "healthy"; svc["uptime_s"] = 0
                return {"accepted": True, "message": f"{target} restarted"}

            if operation == "update_config":
                key = params.get("key"); value = params.get("value")
                if key is None:
                    return {"accepted": False, "message": "update_config requires 'key'"}
                svc["config"][key] = value; svc["health"] = "degraded"
                return {"accepted": True, "message": f"{target}.config.{key} updated"}

            if operation == "run_command":
                command = params.get("command", "")
                if "restart" in command:
                    if svc["status"] == "stopped":
                        return {"accepted": False, "message": f"{target} is stopped"}
                    svc["status"] = "running"; svc["health"] = "healthy"; svc["uptime_s"] = 0
                    return {"accepted": True, "message": f"{target} restarted via command"}
                if "stop" in command:
                    svc["status"] = "stopped"; svc["health"] = "down"; svc["uptime_s"] = 0
                    return {"accepted": True, "message": f"{target} stopped via command"}
                if "start" in command:
                    svc["status"] = "running"; svc["health"] = "healthy"; svc["uptime_s"] = 0
                    return {"accepted": True, "message": f"{target} started via command"}
                return {"accepted": False, "message": f"unrecognized command '{command}'"}

            return {"accepted": False, "message": f"unknown operation '{operation}'"}

        return self._services.write(self._token, fn)

    # -- history ----------------------------------------------------------

    def _record(self, operation, target, params, decision, applied) -> None:
        self._clock += 1
        self.action_history.append({
            "seq": self._clock,
            "ts": time.time(),
            "operation": operation,
            "target": target,
            "params": {k: v for k, v in params.items() if not k.startswith("_")},
            "mcr_decision": decision["decision"],
            "applied": applied,
        })

    # -- scenario setup ---------------------------------------------------

    def set_service(self, name: str, status: str, health: str) -> None:
        def fn(data: Dict[str, Any]) -> None:
            data[name]["status"] = status
            data[name]["health"] = health
        self._services.write(self._token, fn)

    def to_json(self) -> str:
        return json.dumps(self.snapshot(), indent=2, sort_keys=True)
