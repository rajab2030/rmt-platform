"""Generic platform-state provider protocol (Core).

Core depends on this protocol; it does not depend on any concrete
implementation (e.g. Docker). Concrete providers are supplied through the
composition/injection boundary outside the Core.
"""
from typing import Protocol

from app.schemas.platform import (
    ContainerState,
    DockerHealth,
)


class PlatformStateProvider(Protocol):
    """Provides platform container/health state to the Core service.

    Implementations are infrastructure-specific (e.g. Docker) and live
    outside the Core. The Core service consumes this protocol only.
    """

    def get_container_state(self) -> ContainerState:
        """Return the current container running/unhealthy counts."""
        ...

    def get_docker_health(self) -> DockerHealth:
        """Return the current platform health status."""
        ...
