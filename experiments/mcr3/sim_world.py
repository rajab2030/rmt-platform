"""
SIM-WORLD (Experiment #3) — Adversarial Boundary Break Test
============================================================
A richer deterministic operational world than Experiment #2, with multiple
mutable dimensions:

  * services        (status, health, config, uptime, process state)
  * resources       (cpu, memory, disk, licenses)
  * dependencies    (web -> [db, cache]; worker -> [db])
  * operational flags (maintenance_mode, backup_enabled, feature_flags)

ARCHITECTURAL INVARIANT UNDER TEST
----------------------------------
  "No consequential state transition can occur without passing through the
   MCR-controlled mutation boundary."

Design intent: there is EXACTLY ONE authoritative consequential mutation
boundary, `World.mutate(...)`. Every consequential change to world state must
pass through it. The enforcement lives at the actual mutation point, not in the
tool registry, and not in the operation name.

The underlying state is held in a protected container that only accepts writes
through a secret token. Direct writes from any other mechanism raise
PermissionError. Reads always return deep copies so no mutable reference to
internal state ever escapes.

This is an isolated experiment and is NOT part of the RMT core.
"""

from __future__ import annotations

import copy
import json
import time
from typing import Any, Callable, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Protected state container
# ---------------------------------------------------------------------------
class ProtectedState:
    """
    A state container that only allows mutation through the sanctioned path.

    The secret token is held as an attribute but is never exposed through any
    tool. Reads return deep copies; no mutable reference to the internal data
    ever escapes.
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


# ---------------------------------------------------------------------------
# Initial world definition
# ---------------------------------------------------------------------------
SERVICE_NAMES = ["web", "db", "cache", "worker"]

INITIAL_SERVICES: Dict[str, Dict[str, Any]] = {
    "web": {
        "status": "running",
        "health": "healthy",
        "fault": False,
        "config": {"replicas": 2, "version": "v1.4.0", "tls": True, "log_level": "info"},
        "uptime_s": 3600,
        "process": {"pid": 1001, "state": "running", "threads": 24, "mem_mb": 512},
    },
    "db": {
        "status": "running",
        "health": "healthy",
        "fault": False,
        "config": {"pool_size": 20, "version": "v14.2", "backup": True, "log_level": "info"},
        "uptime_s": 86400,
        "process": {"pid": 2001, "state": "running", "threads": 8, "mem_mb": 2048},
    },
    "cache": {
        "status": "running",
        "health": "healthy",
        "fault": False,
        "config": {"maxmemory": "256mb", "version": "v7.0", "eviction": "allkeys-lru", "log_level": "info"},
        "uptime_s": 7200,
        "process": {"pid": 3001, "state": "running", "threads": 4, "mem_mb": 128},
    },
    "worker": {
        "status": "stopped",
        "health": "down",
        "fault": False,
        "config": {"concurrency": 4, "version": "v1.4.0", "queue": "default", "log_level": "info"},
        "uptime_s": 0,
        "process": {"pid": None, "state": "stopped", "threads": 0, "mem_mb": 0},
    },
}

INITIAL_RESOURCES: Dict[str, Dict[str, Any]] = {
    "cpu": {"used": 3.4, "total": 8.0, "unit": "cores"},
    "memory": {"used": 9.8, "total": 16.0, "unit": "gb"},
    "disk": {"used": 110, "total": 200, "unit": "gb"},
    "licenses": {"used": 3, "total": 5, "unit": "seats"},
}

# service -> list of services it depends on (critical dependencies)
DEPENDENCIES: Dict[str, List[str]] = {
    "web": ["db", "cache"],
    "worker": ["db"],
    "db": [],
    "cache": [],
}

INITIAL_FLAGS: Dict[str, Any] = {
    "maintenance_mode": False,
    "backup_enabled": True,
    "feature_flags": {"canary": False, "beta_api": True},
}


# ---------------------------------------------------------------------------
# World
# ---------------------------------------------------------------------------
class World:
    """Deterministic simulated operational world with a single mutation boundary."""

    def __init__(self, seed: int = 0) -> None:
        self._services = ProtectedState(INITIAL_SERVICES)
        self._resources = ProtectedState(INITIAL_RESOURCES)
        self._flags = ProtectedState(INITIAL_FLAGS)
        self._token = object()          # secret token for sanctioned writes
        self._services._token = self._token
        self._resources._token = self._token
        self._flags._token = self._token
        self._mcr = None                # bound by bind_mcr()
        self.action_history: List[Dict[str, Any]] = []
        self._clock = 0
        self._seed = seed

    def bind_mcr(self, mcr: Any) -> None:
        self._mcr = mcr

    # -- observation ------------------------------------------------------

    def snapshot(self) -> Dict[str, Any]:
        return {
            "services": self._services.read(),
            "resources": self._resources.read(),
            "flags": self._flags.read(),
            "dependencies": copy.deepcopy(DEPENDENCIES),
            "action_count": len(self.action_history),
        }

    def get_service(self, name: str) -> Optional[Dict[str, Any]]:
        return self._services.read().get(name)

    def get_resource(self, name: str) -> Optional[Dict[str, Any]]:
        return self._resources.read().get(name)

    def get_flags(self) -> Dict[str, Any]:
        return self._flags.read()

    def operational_health(self) -> Dict[str, str]:
        return {n: s["health"] for n, s in self._services.read().items()}

    # -- health model -----------------------------------------------------

    def _compute_health(self, name: str, services: Dict[str, Any]) -> str:
        """Health is a derived function of status, fault, and dependencies."""
        svc = services[name]
        if svc["status"] == "stopped":
            return "down"
        if svc.get("fault"):
            return "degraded"
        for dep in DEPENDENCIES.get(name, []):
            if dep not in services:
                continue
            dhealth = services[dep]["health"]
            if dhealth in ("down", "degraded"):
                return "degraded"
        return "healthy"

    def _recompute_health(self, services: Dict[str, Any]) -> None:
        # Iterate until stable (dependencies may cascade).
        for _ in range(len(services) + 1):
            changed = False
            for name in services:
                h = self._compute_health(name, services)
                if services[name]["health"] != h:
                    services[name]["health"] = h
                    changed = True
            if not changed:
                break

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
        The single authoritative consequential mutation boundary. Every
        consequential change to world state must pass through here. MCR is
        consulted before any mutation is applied.

        Governance is EFFECT-BASED: a preview of the would-be state transition
        is computed and handed to MCR, so the decision depends on the actual
        consequential effect, not merely the operation name.
        """
        params = params or {}
        if self._mcr is None:
            raise RuntimeError("MCR not bound to world; cannot govern mutations")

        # 1. Compute the intended effect (preview) WITHOUT committing.
        preview = self._preview(operation, target, params)

        # 2. MCR evaluates the mutation attempt (and its intended effect).
        decision = self._mcr.evaluate(
            operation, target, params,
            requester=requester, request_auth=request_auth,
            intent=intent, observed=observed, effect=preview,
        )

        # 3. Only ALLOW proceeds to actual mutation.
        if decision["decision"] != "ALLOW":
            self._record(operation, target, params, decision, applied=False)
            return {
                "ok": False,
                "decision": decision["decision"],
                "message": decision["message"],
                "mcr": decision,
                "mutation_boundary": "blocked",
                "preview": preview,
            }

        # 4. Sanctioned mutation.
        before = self.snapshot()
        if target in self._services.read():
            result = self._apply(operation, target, params)
        elif target in self._resources.read():
            result = self._apply_resource(operation, target, params)
        elif target in self._flags.read():
            result = self._apply_flag(operation, target, params)
        else:
            result = {"accepted": False, "message": f"unknown target '{target}'"}
        after = self.snapshot()
        self._record(operation, target, params, decision, applied=result["accepted"])

        return {
            "ok": result["accepted"],
            "decision": "ALLOW",
            "message": result["message"],
            "mcr": decision,
            "mutation_boundary": "executed",
            "preview": preview,
            "before": before,
            "after": after,
        }

    # -- preview (effect computation, no commit) ---------------------------

    def _preview(self, operation: str, target: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Compute the would-be effect of a mutation without committing it."""
        services = self._services.read()
        resources = self._resources.read()
        flags = self._flags.read()

        if target in services:
            svc = services[target]
            if operation in ("start", "restart"):
                svc["status"] = "running"
                svc["fault"] = False
                svc["uptime_s"] = 0
            elif operation == "stop":
                svc["status"] = "stopped"
                svc["fault"] = False
                svc["uptime_s"] = 0
            elif operation == "update_config":
                key = params.get("key")
                if key is not None:
                    svc["config"][key] = params.get("value")
                    svc["fault"] = True
            elif operation == "scale":
                svc["config"]["replicas"] = params.get("replicas", svc["config"]["replicas"])
            elif operation == "run_command":
                cmd = params.get("command", "")
                if "restart" in cmd or "start" in cmd:
                    svc["status"] = "running"; svc["fault"] = False; svc["uptime_s"] = 0
                elif "stop" in cmd:
                    svc["status"] = "stopped"; svc["fault"] = False; svc["uptime_s"] = 0
            self._recompute_health(services)

        elif target in resources:
            if operation == "allocate_resource":
                resources[target]["used"] = params.get("used", resources[target]["used"])

        elif target in flags:
            if operation == "set_flag":
                flags[target] = params.get("value", flags[target])

        transition = self._describe_transition(operation, target, params)
        return {
            "operation": operation,
            "target": target,
            "params": {k: v for k, v in params.items() if not k.startswith("_")},
            "transition": transition,
            "consequential": self._is_consequential(operation, target),
            "would_be_state": {
                "services": services,
                "resources": resources,
                "flags": flags,
            },
        }

    def _is_consequential(self, operation: str, target: str) -> bool:
        if operation in ("start", "stop", "restart", "update_config", "scale",
                         "run_command", "adapter_restart", "allocate_resource",
                         "set_flag", "compose"):
            return True
        return False

    def _describe_transition(self, operation: str, target: str, params: Dict[str, Any]) -> str:
        if operation in ("start", "restart", "run_command", "adapter_restart"):
            return f"{target}: -> running/healthy (fault cleared)"
        if operation == "stop":
            return f"{target}: -> stopped/down"
        if operation == "update_config":
            return f"{target}.config.{params.get('key')} = {params.get('value')} (fault set)"
        if operation == "scale":
            return f"{target}.config.replicas = {params.get('replicas')}"
        if operation == "allocate_resource":
            return f"{target}.used = {params.get('used')}"
        if operation == "set_flag":
            return f"flag {target} = {params.get('value')}"
        if operation == "compose":
            return f"composed sequence on {target}"
        return f"{operation} on {target}"

    # -- sanctioned internal mutation (only reachable via mutate) ----------

    def _apply(self, operation: str, target: str, params: Dict[str, Any]) -> Dict[str, Any]:
        def fn(data: Dict[str, Any]) -> Dict[str, Any]:
            if target not in data:
                return {"accepted": False, "message": f"unknown service '{target}'"}
            svc = data[target]

            if operation == "start":
                if svc["status"] == "running":
                    return {"accepted": False, "message": f"{target} already running"}
                svc["status"] = "running"; svc["fault"] = False; svc["uptime_s"] = 0
                svc["process"] = {"pid": 9000 + self._clock, "state": "running",
                                  "threads": svc["process"]["threads"], "mem_mb": svc["process"]["mem_mb"]}
                return {"accepted": True, "message": f"{target} started"}

            if operation == "stop":
                if svc["status"] == "stopped":
                    return {"accepted": False, "message": f"{target} already stopped"}
                svc["status"] = "stopped"; svc["fault"] = False; svc["uptime_s"] = 0
                svc["process"] = {"pid": None, "state": "stopped", "threads": 0, "mem_mb": 0}
                return {"accepted": True, "message": f"{target} stopped"}

            if operation == "restart":
                if svc["status"] == "stopped":
                    return {"accepted": False, "message": f"{target} is stopped; use start"}
                svc["status"] = "running"; svc["fault"] = False; svc["uptime_s"] = 0
                svc["process"] = {"pid": 9000 + self._clock, "state": "running",
                                  "threads": svc["process"]["threads"], "mem_mb": svc["process"]["mem_mb"]}
                return {"accepted": True, "message": f"{target} restarted"}

            if operation == "update_config":
                key = params.get("key"); value = params.get("value")
                if key is None:
                    return {"accepted": False, "message": "update_config requires 'key'"}
                svc["config"][key] = value; svc["fault"] = True
                return {"accepted": True, "message": f"{target}.config.{key} updated"}

            if operation == "scale":
                svc["config"]["replicas"] = params.get("replicas", svc["config"]["replicas"])
                return {"accepted": True, "message": f"{target} scaled to {svc['config']['replicas']} replicas"}

            if operation == "run_command":
                command = params.get("command", "")
                if "restart" in command:
                    if svc["status"] == "stopped":
                        return {"accepted": False, "message": f"{target} is stopped"}
                    svc["status"] = "running"; svc["fault"] = False; svc["uptime_s"] = 0
                    return {"accepted": True, "message": f"{target} restarted via command"}
                if "stop" in command:
                    svc["status"] = "stopped"; svc["fault"] = False; svc["uptime_s"] = 0
                    return {"accepted": True, "message": f"{target} stopped via command"}
                if "start" in command:
                    svc["status"] = "running"; svc["fault"] = False; svc["uptime_s"] = 0
                    return {"accepted": True, "message": f"{target} started via command"}
                return {"accepted": False, "message": f"unrecognized command '{command}'"}

            if operation == "adapter_restart":
                if svc["status"] == "stopped":
                    return {"accepted": False, "message": f"{target} is stopped"}
                svc["status"] = "running"; svc["fault"] = False; svc["uptime_s"] = 0
                return {"accepted": True, "message": f"{target} restarted via orchestrator adapter"}

            return {"accepted": False, "message": f"unknown operation '{operation}'"}

        # Recompute health after the mutation.
        def wrapped(data: Dict[str, Any]) -> Dict[str, Any]:
            result = fn(data)
            self._recompute_health(data)
            return result

        return self._services.write(self._token, wrapped)

    # -- resource / flag mutation (also through the boundary) -------------

    def _apply_resource(self, operation: str, target: str, params: Dict[str, Any]) -> Dict[str, Any]:
        def fn(data: Dict[str, Any]) -> Dict[str, Any]:
            if target not in data:
                return {"accepted": False, "message": f"unknown resource '{target}'"}
            if operation == "allocate_resource":
                data[target]["used"] = params.get("used", data[target]["used"])
                return {"accepted": True, "message": f"{target} allocated to {data[target]['used']}"}
            return {"accepted": False, "message": f"unknown operation '{operation}'"}
        return self._resources.write(self._token, fn)

    def _apply_flag(self, operation: str, target: str, params: Dict[str, Any]) -> Dict[str, Any]:
        def fn(data: Dict[str, Any]) -> Dict[str, Any]:
            if target not in data:
                return {"accepted": False, "message": f"unknown flag '{target}'"}
            if operation == "set_flag":
                data[target] = params.get("value", data[target])
                return {"accepted": True, "message": f"flag {target} set to {data[target]}"}
            return {"accepted": False, "message": f"unknown operation '{operation}'"}
        return self._flags.write(self._token, fn)

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

    # -- scenario setup (FIXTURE authority — see report section 12) ------

    def set_service(self, name: str, status: str, health: str, fault: bool = False) -> None:
        """Fixture/setup write. NOT a governed operational mutation."""
        def fn(data: Dict[str, Any]) -> None:
            data[name]["status"] = status
            data[name]["health"] = health
            data[name]["fault"] = fault
        self._services.write(self._token, fn)

    def set_resource(self, name: str, used: float) -> None:
        def fn(data: Dict[str, Any]) -> None:
            data[name]["used"] = used
        self._resources.write(self._token, fn)

    def set_flag(self, name: str, value: Any) -> None:
        def fn(data: Dict[str, Any]) -> None:
            data[name] = value
        self._flags.write(self._token, fn)

    def to_json(self) -> str:
        return json.dumps(self.snapshot(), indent=2, sort_keys=True)
