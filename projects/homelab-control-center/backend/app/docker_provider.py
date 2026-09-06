"""Docker-specific PlatformStateProvider implementation (outside Core).

This is the concrete Docker implementation of the Core
`PlatformStateProvider` protocol. It lives outside the Core and is supplied
through the composition/injection boundary (app.main). The Core service never
imports this module or app.docker_api.
"""
import subprocess

from app.docker_api import get_containers

from app.schemas.platform import (
    ContainerState,
    DockerHealth,
)

from app.core.platform_state.provider import PlatformStateProvider


class DockerPlatformStateProvider:
    """Docker implementation of PlatformStateProvider."""

    def get_container_state(self) -> ContainerState:
        containers = get_containers()

        running = len(
            [
                c for c in containers
                if c["status"] == "running"
            ]
        )

        unhealthy = len(
            [
                c for c in containers
                if "unhealthy" in c["status"]
            ]
        )

        return ContainerState(
            running=running,
            unhealthy=unhealthy,
        )

    def get_docker_health(self) -> DockerHealth:
        status = "unhealthy"

        result = subprocess.run(
            [
                "systemctl",
                "is-active",
                "docker",
            ],
            capture_output=True,
            text=True,
        )

        if result.stdout.strip() == "active":
            status = "healthy"

        return DockerHealth(
            status=status
        )
