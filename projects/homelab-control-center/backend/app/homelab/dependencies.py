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

**T1-2:** an operator can also declare an edge *without a code change* via
``RMT_HOMELAB_DEPENDENCIES`` (``"web:db;api:db,cache"``, parsed by
``app/ops/ops_config.py::homelab_dependency_edges``). The env edges are
**unioned** into the static map below by the accessors here; the static map
stays all-independent. ``dependency_sources()`` reports which edge came from
where.
"""
from app.ops import ops_config

HOMELAB_DEPENDENCIES: dict[str, list[str]] = {
    "portainer": [],
    "dozzle": [],
    "uptime-kuma": [],
}


def _merged_map() -> dict[str, list[str]]:
    """Static all-independent map unioned with operator-declared env edges
    (``RMT_HOMELAB_DEPENDENCIES``). Static entries are preserved; an env edge
    adds deps to an existing component or introduces a new one."""
    merged: dict[str, list[str]] = {
        k: list(v) for k, v in HOMELAB_DEPENDENCIES.items()
    }
    for comp, deps in ops_config.homelab_dependency_edges().items():
        bucket = merged.setdefault(comp, [])
        for d in deps:
            if d not in bucket:
                bucket.append(d)
    return merged


def dependencies_of(component: str) -> list[str]:
    """Components that ``component`` depends on (static map ∪ env edges)."""
    return list(_merged_map().get(component, []))


def dependents_of(component: str) -> set[str]:
    """Components that depend on ``component`` (static map ∪ env edges)."""
    return {
        name
        for name, deps in _merged_map().items()
        if component in (deps or [])
    }


def resolved_map() -> dict[str, list[str]]:
    """The full merged map (static ∪ env), for read-only status/observability."""
    return _merged_map()


def dependency_sources() -> dict[str, dict[str, list[str]]]:
    """Read-only: which edges are static vs operator-declared (env). For
    ``GET /agent/status`` and the T1-2 live exercise."""
    return {
        "static": {k: list(v) for k, v in HOMELAB_DEPENDENCIES.items()},
        "env": {
            k: list(v) for k, v in ops_config.homelab_dependency_edges().items()
        },
    }
