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

B1a: when docker IS reachable and the container listing succeeded but the
target is not in it, the observation is a definite ``state="absent"`` -- not an
inability to observe. This makes ``remove`` verifiable (an ``absent`` expected
state now has a distinct observed value). ``None`` is reserved for "could not
observe" (docker down, lookup raised). A present container is unaffected.
"""
from app.core.intelligence.verification.models import ObservedState
from app.docker_api import get_containers, docker_available

# B1a: the observed state for a target that is definitely gone (docker was
# reachable and the listing did not contain it).
ABSENT = "absent"


def observe_container_state(target: str):
    """Read-only observation of a Docker container's actual state.

    Returns an ObservedState (source="docker") when the container is found, an
    ObservedState with state="absent" when docker was reachable but the
    container is not present, or None when the state cannot be observed (docker
    unavailable, lookup error). Never mutates anything.
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

    # Docker was reachable and the listing succeeded: the container is
    # definitely gone. That is an observation ("absent"), not an inability to
    # observe.
    return ObservedState(target=target, state=ABSENT, source="docker")
