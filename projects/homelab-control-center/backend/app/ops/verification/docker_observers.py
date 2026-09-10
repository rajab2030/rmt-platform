"""B1a — register the above-Core Docker container-state observer.

The observer itself is the existing `app/homelab/observer.py::observe_container_state`
(read-only). This module only adapts it to the registry's factory signature and
names the Docker lifecycle operations it covers.
"""
from app.homelab.observer import observe_container_state
from app.ops.verification.registry import register_observer

_DOCKER_OPERATIONS = ("start", "stop", "restart", "create", "remove")


def _docker_observer_factory(target: str):
    def observe():
        return observe_container_state(target)

    return observe


def register() -> None:
    for operation in _DOCKER_OPERATIONS:
        register_observer("docker", operation, _docker_observer_factory)


register()
