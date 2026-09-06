"""Above-Core Homelab/Docker container-state observer (G1).

The observer observes; the existing verification mechanism verifies.

This module provides a read-only Docker container-state observer that
produces an ObservedState for the existing RMT verification boundary. It is
Homelab/Docker-specific and above-Core.

The observer MUST NOT (and does not):
  * execute Docker mutations
  * restart containers
  * authorize execution
  * approve actions
  * bypass execution_engine
  * bypass the existing verification boundary
  * become an alternative execution path
  * weaken existing fail-safe behavior

It only reads actual container state and returns an ObservedState (or None
when the state cannot be observed, so the existing verifier fails safe with
observation_unavailable).
"""
from app.core.intelligence.verification.models import ObservedState
from app.docker_api import get_containers, docker_available


def observe_container_state(target: str):
    """Read-only observation of a Docker container's actual state.

    Returns an ObservedState (source="docker") when the container is found,
    or None when the state cannot be observed (docker unavailable, lookup
    error, or container not present). Never mutates anything.
    """
    if not docker_available():
        return None

    try:
        containers = get_containers()
    except Exception:
        return None

    for container in containers:
        if container.get("name") == target:
            return ObservedState(
                target=target,
                state=container.get("status", "unknown"),
                source="docker",
            )

    # Container not present -> state cannot be observed.
    return None
