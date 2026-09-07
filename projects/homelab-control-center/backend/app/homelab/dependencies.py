"""Above-Core homelab component-dependency map (RMT-CAP-05 / T13 closure).

The frozen Core's ``ComponentContext.dependencies``
(``app/core/intelligence/context/registry.py``) is left untouched. This is the
**authoritative above-Core source** of inter-component dependency edges for the
homelab domain; the T13 dependency-cascade guard
(``app/agent/dependency_guard.py``) unions this with the Core context.

An explicit empty list means "established: independent" -- distinct from the
Core default of an unpopulated list ("dependency knowledge not established",
per the CAP-02 semantic note).

Current homelab (verified 2026-09-07): the three services are independent. Each
needs only the Docker daemon, not one another:
  * ``portainer``   -- Docker management UI
  * ``dozzle``      -- Docker log viewer
  * ``uptime-kuma`` -- uptime monitor (it *observes* endpoints; it does not
                       *depend* on portainer/dozzle to run)

Add an edge here (``"web": ["db"]``) and the T13 guard immediately escalates any
allowed-class operation on the depended-upon component to human approval.
"""

HOMELAB_DEPENDENCIES: dict[str, list[str]] = {
    "portainer": [],
    "dozzle": [],
    "uptime-kuma": [],
}


def dependencies_of(component: str) -> list[str]:
    """Components that ``component`` depends on (above-Core map only)."""
    return list(HOMELAB_DEPENDENCIES.get(component, []))


def dependents_of(component: str) -> set[str]:
    """Components that depend on ``component`` (above-Core map only)."""
    return {
        name
        for name, deps in HOMELAB_DEPENDENCIES.items()
        if component in (deps or [])
    }


def resolved_map() -> dict[str, list[str]]:
    """The full above-Core map, for read-only status/observability."""
    return {k: list(v) for k, v in HOMELAB_DEPENDENCIES.items()}
