"""Focused regression coverage for the platform_state provider boundary.

Proves the C07 freeze-deviation (#1):
  * Core platform_state operates through a generic provider protocol.
  * The Docker-specific implementation is supplied externally (outside Core).
  * The Core service has no direct app.docker_api dependency.
  * The resulting /platform/state output remains contract-compatible.
"""
from pathlib import Path

from app.schemas.platform import (
    PlatformState,
    GitState,
    ContainerState,
    DockerHealth,
    BackupState,
)

import app.core.platform_state.service as platform_state_service
from app.core.platform_state.provider import PlatformStateProvider


class _FakeProvider:
    """Minimal generic provider used to prove the Core consumes the protocol."""

    def get_container_state(self) -> ContainerState:
        return ContainerState(running=2, unhealthy=1)

    def get_docker_health(self) -> DockerHealth:
        return DockerHealth(status="healthy")


def test_core_platform_state_operates_through_generic_provider(monkeypatch):
    # git is absent in this environment; pin git/backup so the provider-driven
    # fields are what we assert (mirrors the documented /platform/state
    # environment limitation).
    monkeypatch.setattr(
        platform_state_service,
        "get_git_state",
        lambda: GitState(branch="main", commit="abc1234"),
    )
    monkeypatch.setattr(
        platform_state_service,
        "get_backup_state",
        lambda: BackupState(latest="2026-09-04"),
    )

    state = platform_state_service.get_platform_state(_FakeProvider())

    assert isinstance(state, PlatformState)
    # Provider-driven fields come from the injected provider.
    assert state.containers.running == 2
    assert state.containers.unhealthy == 1
    assert state.health.status == "healthy"
    # Non-provider fields still produced by the Core service.
    assert state.platform == "RMT"
    assert state.git.branch == "main"
    assert state.git.commit == "abc1234"
    assert state.backup.latest == "2026-09-04"


def test_core_service_has_no_direct_docker_api_dependency():
    # The Core service must not import or reference app.docker_api.
    source = Path(platform_state_service.__file__).read_text()
    assert "docker_api" not in source
    assert "app.docker_api" not in source
    # And the module must not expose it as an attribute.
    assert not hasattr(platform_state_service, "docker_api")


def test_docker_implementation_is_supplied_externally():
    # The Docker implementation lives outside the Core (app.docker_provider),
    # not under app/core, and implements the provider protocol surface.
    from app.docker_provider import DockerPlatformStateProvider

    provider = DockerPlatformStateProvider()
    assert hasattr(provider, "get_container_state")
    assert hasattr(provider, "get_docker_health")
    # It is not part of the Core package.
    assert not DockerPlatformStateProvider.__module__.startswith("app.core")
